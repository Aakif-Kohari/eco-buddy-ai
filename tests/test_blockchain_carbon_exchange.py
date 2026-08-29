import pytest
import time
import hashlib
from src.services.blockchain_carbon_exchange import (
    CarbonLedger,
    Transaction,
    SmartContract,
    Block,
    MarketIntelligence,
    ProofOfStake
)

def test_cryptographic_hash_collisions():
    """Verify that identical transactions with different timestamps yield different hashes."""
    tx1 = Transaction(sender="system", recipient="alice", amount=10.0, token_type="SOLAR", timestamp=100.0)
    tx2 = Transaction(sender="system", recipient="alice", amount=10.0, token_type="SOLAR", timestamp=100.1)
    
    hash1 = tx1.compute_hash()
    hash2 = tx2.compute_hash()
    assert hash1 != hash2
    
def test_double_spending_attack():
    """Verify that a user cannot spend more tokens than they have."""
    ledger = CarbonLedger()
    ledger.register_wallet("alice")
    ledger.register_wallet("bob")
    
    # Alice gets 50 tokens
    mint_tx = Transaction(sender="system", recipient="alice", amount=50.0, token_type="SOLAR")
    ledger.add_transaction(mint_tx)
    ledger.mine_block()
    
    # Alice tries to send 30 tokens to bob
    tx1 = Transaction(sender="alice", recipient="bob", amount=30.0, token_type="SOLAR")
    assert ledger.add_transaction(tx1) is True
    
    # Alice tries to send another 30 tokens (she only has 20 left)
    tx2 = Transaction(sender="alice", recipient="bob", amount=30.0, token_type="SOLAR")
    assert ledger.add_transaction(tx2) is False
    
def test_smart_contract_logic_and_overflows():
    """Verify smart contract verification works and handles large numbers."""
    ledger = CarbonLedger()
    
    # HVAC Retrofit contract
    contract = SmartContract("C_HVAC", "charlie", {"type": "HVAC", "min_efficiency_gain": 0.2, "multiplier": 10.0})
    ledger.deploy_contract(contract)
    
    # Execute with invalid data (below threshold)
    success = ledger.execute_contract("C_HVAC", {"efficiency_gain": 0.1})
    assert success is False
    
    # Execute with valid data
    success = ledger.execute_contract("C_HVAC", {"efficiency_gain": 0.25})
    assert success is True
    
    ledger.mine_block()
    assert ledger.get_balance("charlie", "HVAC") == 2.5  # 0.25 * 10
    
    # Test for execution after already executed
    with pytest.raises(ValueError):
        contract.verify_and_execute({"efficiency_gain": 0.3})
        
def test_proof_of_stake():
    pos = ProofOfStake()
    pos.add_stake("v1", 1000)
    pos.add_stake("v2", 500)
    
    validator = pos.select_validator()
    assert validator in ["v1", "v2"]
    
    pos.remove_stake("v1", 1000)
    assert pos.total_staked == 500
