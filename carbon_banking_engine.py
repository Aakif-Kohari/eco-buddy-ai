"""
Carbon Banking Engine.
Manages monthly allowance allocations, rollover logic, and borrowing limits.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta


class CarbonBankingEngine:
    """Handles the logic for banking and borrowing carbon allowances."""

    def __init__(self, user_id: str, base_monthly_allowance: float = 500.0):
        self.user_id = user_id
        self.base_monthly_allowance = base_monthly_allowance
        self.accounts: Dict[str, Dict[str, float]] = {}

    def initialize_account(self, month: str) -> None:
        """Initializes a new monthly account if it doesn't exist."""
        if month not in self.accounts:
            self.accounts[month] = {
                "base_allowance": self.base_monthly_allowance,
                "banked_from_previous": 0.0,
                "borrowed_from_future": 0.0,
                "total_available": self.base_monthly_allowance,
                "used": 0.0,
                "remaining": self.base_monthly_allowance,
            }

    def get_account(self, month: str) -> Dict[str, float]:
        """Retrieves the account details for a specific month."""
        self.initialize_account(month)
        return self.accounts[month]

    def rollover_unused_allowance(
        self, from_month: str, to_month: str, rollover_pct: float
    ) -> float:
        """
        Rolls over a percentage of unused allowance from one month to the next.
        Returns the amount successfully rolled over.
        """
        from_account = self.get_account(from_month)
        to_account = self.get_account(to_month)

        unused = from_account["remaining"]
        if unused <= 0:
            return 0.0

        rollover_amount = unused * (rollover_pct / 100.0)

        # Deduct from previous month's remaining (conceptual, as it's already passed)
        from_account["remaining"] -= rollover_amount

        # Add to next month's banked allowance
        to_account["banked_from_previous"] += rollover_amount
        to_account["total_available"] += rollover_amount
        to_account["remaining"] += rollover_amount

        return round(rollover_amount, 2)

    def borrow_from_future(
        self, current_month: str, future_month: str, amount: float
    ) -> bool:
        """
        Borrows a specific amount from a future month's allowance.
        Returns True if successful, False if limits are exceeded.
        """
        current_account = self.get_account(current_month)
        future_account = self.get_account(future_month)

        # Limit borrowing to 50% of future month's base allowance
        max_borrow = future_account["base_allowance"] * 0.5
        if amount > max_borrow:
            return False

        current_account["borrowed_from_future"] += amount
        current_account["total_available"] += amount
        current_account["remaining"] += amount

        future_account["base_allowance"] -= amount
        future_account["total_available"] -= amount
        future_account["remaining"] -= amount

        return True

    def log_usage(self, month: str, amount: float) -> None:
        """Logs carbon usage against the current month's allowance."""
        account = self.get_account(month)
        account["used"] += amount
        account["remaining"] = account["total_available"] - account["used"]
