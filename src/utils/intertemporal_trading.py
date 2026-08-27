"""
Intertemporal Trading Module.
Calculates interest accrual, decay rates on banked carbon, and penalties for excessive borrowing.
"""

from typing import Dict, Any


class IntertemporalTrading:
    """Manages the financial-like mechanics of carbon banking over time."""

    def __init__(self, decay_rate_pct: float = 5.0, interest_rate_pct: float = 10.0):
        # Banked carbon decays (e.g., inflation of carbon budget)
        self.decay_rate_pct = decay_rate_pct
        # Borrowed carbon accrues interest (penalty for borrowing)
        self.interest_rate_pct = interest_rate_pct

    def apply_decay_to_banked(self, banked_amount: float, months_held: int) -> float:
        """
        Applies a decay rate to banked carbon for each month it is held.
        Simulates the decreasing value of old carbon savings.
        """
        if months_held <= 0:
            return banked_amount

        decay_multiplier = (1 - (self.decay_rate_pct / 100.0)) ** months_held
        decayed_amount = banked_amount * decay_multiplier

        return round(decayed_amount, 2)

    def calculate_borrowing_penalty(
        self, borrowed_amount: float, months_until_due: int
    ) -> Dict[str, float]:
        """
        Calculates the total amount owed when borrowing from the future,
        including compounding interest penalties.
        """
        if months_until_due <= 0:
            return {
                "principal": borrowed_amount,
                "interest": 0.0,
                "total_owed": borrowed_amount,
            }

        interest_multiplier = (1 + (self.interest_rate_pct / 100.0)) ** months_until_due
        total_owed = borrowed_amount * interest_multiplier
        interest_accrued = total_owed - borrowed_amount

        return {
            "principal": round(borrowed_amount, 2),
            "interest": round(interest_accrued, 2),
            "total_owed": round(total_owed, 2),
        }

    def evaluate_banking_strategy(
        self, current_surplus: float, projected_deficit: float
    ) -> Dict[str, Any]:
        """
        Evaluates whether it is better to bank current surplus or borrow against future deficit.
        """
        if current_surplus <= 0 and projected_deficit <= 0:
            return {"recommendation": "No action needed", "net_impact": 0.0}

        if current_surplus > 0:
            decayed_surplus = self.apply_decay_to_banked(current_surplus, 1)
            return {
                "recommendation": "Bank Surplus",
                "original_amount": current_surplus,
                "value_next_month": decayed_surplus,
                "loss_to_decay": round(current_surplus - decayed_surplus, 2),
            }
        else:
            penalty = self.calculate_borrowing_penalty(abs(projected_deficit), 1)
            return {
                "recommendation": "Borrow with Caution",
                "amount_needed": abs(projected_deficit),
                "total_repayment_next_month": penalty["total_owed"],
                "penalty_cost": penalty["interest"],
            }
