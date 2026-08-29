"""
Peer-to-Peer Energy Trading Blockchain Ledger.
Simulates a decentralized ledger where Smart Homes can trade their surplus solar energy
with neighbors using cryptographic signatures and Proof of Stake concepts.
"""

import hashlib
import json
import time
import uuid
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class Transaction:
    """Represents a single energy trade between two wallets (homes)."""
    def __init__(self, sender: str, receiver: str, amount_kwh: float, rate_cents_kwh: float):
        self.tx_id = str(uuid.uuid4())
        self.sender = sender
        self.receiver = receiver
        self.amount_kwh = amount_kwh
        self.rate_cents_kwh = rate_cents_kwh
        self.timestamp = time.time()
        self.signature = None
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "amount_kwh": self.amount_kwh,
            "rate_cents_kwh": self.rate_cents_kwh,
            "timestamp": self.timestamp,
            "signature": self.signature
        }
        
    def sign(self, private_key: str):
        """Simulates cryptographic signing of the transaction payload."""
        payload = f"{self.sender}{self.receiver}{self.amount_kwh}{self.timestamp}{private_key}"
        self.signature = hashlib.sha256(payload.encode()).hexdigest()
        
    def is_valid(self) -> bool:
        """Verifies the transaction signature and payload limits."""
        if not self.signature:
            return False
        if self.amount_kwh <= 0 or self.rate_cents_kwh < 0:
            return False
        # In a real blockchain, we would verify the signature against the sender's public key
        # Here we just assume it's valid if it exists for the simulation
        return True


class Block:
    """A collection of energy transactions secured via cryptographic hashing."""
    def __init__(self, index: int, transactions: List[Transaction], previous_hash: str):
        self.index = index
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.timestamp = time.time()
        self.nonce = 0
        self.hash = self.calculate_hash()
        
    def calculate_hash(self) -> str:
        """Computes the SHA-256 hash of the block contents."""
        tx_data = json.dumps([tx.to_dict() for tx in self.transactions], sort_keys=True)
        block_content = f"{self.index}{tx_data}{self.previous_hash}{self.timestamp}{self.nonce}"
        return hashlib.sha256(block_content.encode()).hexdigest()
        
    def mine_block(self, difficulty: int):
        """Proof of Work implementation (simplified for simulation speed)."""
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
        logger.info(f"Block {self.index} mined with hash: {self.hash}")


class SmartGridLedger:
    """
    The main Blockchain managing the decentralized energy trading network.
    Maintains wallet balances, validates transactions, and mints new blocks.
    """
    def __init__(self, difficulty: int = 2):
        self.chain: List[Block] = [self._create_genesis_block()]
        self.pending_transactions: List[Transaction] = []
        self.difficulty = difficulty
        self.mining_reward_kwh = 5.0 # Reward for securing the network
        self.wallets: Dict[str, float] = {} # Maps wallet ID to balance in Cents
        
    def _create_genesis_block(self) -> Block:
        """The first block in the chain."""
        return Block(0, [], "0")
        
    def get_latest_block(self) -> Block:
        return self.chain[-1]
        
    def register_wallet(self, wallet_id: str, initial_balance_cents: float = 1000.0):
        if wallet_id not in self.wallets:
            self.wallets[wallet_id] = initial_balance_cents
            logger.info(f"Wallet registered: {wallet_id} with {initial_balance_cents} cents.")
            
    def get_balance(self, wallet_id: str) -> float:
        """Calculates balance by traversing the entire blockchain history."""
        # Start with initial state
        balance = self.wallets.get(wallet_id, 0.0)
        
        # Traverse chain
        for block in self.chain:
            for tx in block.transactions:
                cost = tx.amount_kwh * tx.rate_cents_kwh
                if tx.sender == wallet_id:
                    balance -= cost
                if tx.receiver == wallet_id:
                    balance += cost
                    
        return balance
        
    def submit_transaction(self, tx: Transaction) -> bool:
        """Validates and adds a transaction to the mempool."""
        if not tx.is_valid():
            logger.error("Invalid transaction rejected.")
            return False
            
        # Check if sender has enough funds
        sender_balance = self.get_balance(tx.sender)
        tx_cost = tx.amount_kwh * tx.rate_cents_kwh
        
        # We allow grid providers (like "GRID_MAIN") to have infinite balance
        if tx.sender != "GRID_MAIN" and sender_balance < tx_cost:
            logger.error(f"Insufficient funds for wallet {tx.sender}. Has {sender_balance}, needs {tx_cost}")
            return False
            
        self.pending_transactions.append(tx)
        logger.debug(f"Transaction {tx.tx_id} queued for mining.")
        return True
        
    def mine_pending_transactions(self, miner_address: str):
        """Packages pending transactions into a new block and adds it to the chain."""
        if not self.pending_transactions:
            return
            
        # Create reward tx for the miner
        reward_tx = Transaction("GRID_MAIN", miner_address, self.mining_reward_kwh, 0.0)
        reward_tx.sign("system_key")
        self.pending_transactions.append(reward_tx)
        
        # Package block
        new_block = Block(
            index=len(self.chain),
            transactions=self.pending_transactions,
            previous_hash=self.get_latest_block().hash
        )
        
        # Mine it
        new_block.mine_block(self.difficulty)
        
        # Add to chain and clear mempool
        self.chain.append(new_block)
        self.pending_transactions = []
        logger.info(f"Block {new_block.index} successfully added to chain.")
        
    def is_chain_valid(self) -> bool:
        """Verifies cryptographic integrity of the entire blockchain."""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Recalculate hash to ensure no tampering
            if current_block.hash != current_block.calculate_hash():
                return False
                
            # Verify chain links
            if current_block.previous_hash != previous_block.hash:
                return False
                
        return True

    def export_chain(self) -> List[Dict[str, Any]]:
        """Exports the ledger state for API or UI consumption."""
        export = []
        for block in self.chain:
            export.append({
                "index": block.index,
                "timestamp": block.timestamp,
                "hash": block.hash,
                "previous_hash": block.previous_hash,
                "nonce": block.nonce,
                "transactions": [tx.to_dict() for tx in block.transactions]
            })
        return export
