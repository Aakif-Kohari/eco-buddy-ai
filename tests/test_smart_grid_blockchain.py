import pytest
from plugins.smart_grid.blockchain_ledger import SmartGridLedger, Transaction, Block

def test_ledger_initialization():
    ledger = SmartGridLedger(difficulty=1)
    assert len(ledger.chain) == 1
    assert ledger.chain[0].index == 0
    assert ledger.is_chain_valid() is True

def test_wallet_registration():
    ledger = SmartGridLedger(difficulty=1)
    ledger.register_wallet("home_a", 5000.0)
    ledger.register_wallet("home_b", 1000.0)
    
    assert ledger.get_balance("home_a") == 5000.0
    assert ledger.get_balance("home_b") == 1000.0

def test_transaction_submission_and_mining():
    ledger = SmartGridLedger(difficulty=1)
    ledger.register_wallet("home_a", 5000.0)
    ledger.register_wallet("home_b", 1000.0)
    
    # Home A sells 10 kWh to Home B at 15 cents/kWh (Cost: 150 cents)
    tx = Transaction("home_b", "home_a", amount_kwh=10.0, rate_cents_kwh=15.0)
    tx.sign("private_key_b")
    
    success = ledger.submit_transaction(tx)
    assert success is True
    assert len(ledger.pending_transactions) == 1
    
    # Mine the block
    ledger.mine_pending_transactions("miner_1")
    
    assert len(ledger.pending_transactions) == 0
    assert len(ledger.chain) == 2
    
    # Verify balances
    # Home B spent 150 cents. Should have 850
    assert ledger.get_balance("home_b") == 850.0
    
    # Home A received 150 cents. Should have 5150
    assert ledger.get_balance("home_a") == 5150.0

def test_invalid_transaction_rejected():
    ledger = SmartGridLedger(difficulty=1)
    ledger.register_wallet("broke_home", 50.0)
    
    # Tries to spend 100 cents
    tx = Transaction("broke_home", "other", amount_kwh=10.0, rate_cents_kwh=10.0)
    tx.sign("key")
    
    success = ledger.submit_transaction(tx)
    assert success is False
    assert len(ledger.pending_transactions) == 0

def test_chain_validation():
    ledger = SmartGridLedger(difficulty=1)
    ledger.register_wallet("a", 1000)
    
    tx = Transaction("a", "b", 5.0, 10.0)
    tx.sign("key")
    ledger.submit_transaction(tx)
    ledger.mine_pending_transactions("miner")
    
    assert ledger.is_chain_valid() is True
    
    # Tamper with the chain
    ledger.chain[1].transactions[0].amount_kwh = 100.0
    
    assert ledger.is_chain_valid() is False
