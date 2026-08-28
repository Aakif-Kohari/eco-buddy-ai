"""
Personal Carbon Allowance (PCA) Trading Engine.
Handles allowance allocation, trade matching logic, and portfolio balance updates.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


class PCATradingEngine:
    """Manages personal carbon allowance balances and peer-to-peer trades."""

    DEFAULT_MONTHLY_ALLOWANCE = 500.0  # kg CO2e

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.balances: Dict[str, float] = {}
        self.trade_history: List[Dict[str, Any]] = []

    def initialize_allowance(self, amount: float = DEFAULT_MONTHLY_ALLOWANCE) -> float:
        """Initializes or resets the monthly carbon allowance for a user."""
        self.balances[self.user_id] = amount
        return self.balances[self.user_id]

    def get_balance(self, user_id: str) -> float:
        """Retrieves the current carbon allowance balance for a user."""
        return self.balances.get(user_id, 0.0)

    def decrement_balance(self, user_id: str, amount: float) -> bool:
        """Decrements balance due to logged activities. Returns True if successful."""
        if self.get_balance(user_id) >= amount:
            self.balances[user_id] -= amount
            return True
        return False

    def execute_trade(
        self, buyer_id: str, seller_id: str, amount: float, price_per_tonne: float
    ) -> Dict[str, Any]:
        """
        Executes a peer-to-peer carbon allowance trade.
        Validates balances and updates both parties.
        """
        if amount <= 0:
            raise ValueError("Trade amount must be positive.")
        if self.get_balance(seller_id) < amount:
            raise ValueError("Seller has insufficient carbon allowance to sell.")

        # Execute transfer
        self.balances[seller_id] -= amount
        self.balances[buyer_id] = self.get_balance(buyer_id) + amount

        trade_record = {
            "trade_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "buyer_id": buyer_id,
            "seller_id": seller_id,
            "amount_kg": amount,
            "price_per_tonne_usd": price_per_tonne,
            "total_cost_usd": round((amount / 1000.0) * price_per_tonne, 2),
            "status": "completed",
        }
        self.trade_history.append(trade_record)
        return trade_record

    def get_trade_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieves all trades involving a specific user."""
        return [
            trade
            for trade in self.trade_history
            if trade["buyer_id"] == user_id or trade["seller_id"] == user_id
        ]
