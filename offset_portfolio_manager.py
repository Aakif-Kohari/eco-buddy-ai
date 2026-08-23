"""
Offset Portfolio Manager.
Handles portfolio allocation, diversification scoring, and rebalancing logic for carbon offsets.
"""

from typing import Dict, List, Any, Optional
import math


class OffsetPortfolioManager:
    """Manages a user's carbon offset portfolio and provides rebalancing recommendations."""

    # Target allocation percentages for a balanced, high-impact portfolio
    TARGET_ALLOCATION = {
        "reforestation": 0.40,
        "renewable_energy": 0.30,
        "methane_capture": 0.15,
        "direct_air_capture": 0.15,
    }

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.holdings: List[Dict[str, Any]] = []

    def add_holding(
        self,
        project_id: str,
        project_type: str,
        region: str,
        standard: str,
        tonnes: float,
        cost_per_tonne: float,
    ) -> None:
        """Adds a new offset project to the portfolio."""
        self.holdings.append(
            {
                "project_id": project_id,
                "project_type": project_type,
                "region": region,
                "standard": standard,
                "tonnes": tonnes,
                "cost_per_tonne": cost_per_tonne,
                "total_cost": round(tonnes * cost_per_tonne, 2),
            }
        )

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Aggregates portfolio holdings into a summary."""
        total_tonnes = sum(h["tonnes"] for h in self.holdings)
        total_cost = sum(h["total_cost"] for h in self.holdings)

        type_breakdown = {}
        region_breakdown = {}
        standard_breakdown = {}

        for h in self.holdings:
            p_type = h["project_type"]
            region = h["region"]
            standard = h["standard"]

            type_breakdown[p_type] = type_breakdown.get(p_type, 0) + h["tonnes"]
            region_breakdown[region] = region_breakdown.get(region, 0) + h["tonnes"]
            standard_breakdown[standard] = (
                standard_breakdown.get(standard, 0) + h["tonnes"]
            )

        return {
            "total_tonnes": round(total_tonnes, 2),
            "total_cost": round(total_cost, 2),
            "average_cost_per_tonne": round(total_cost / total_tonnes, 2)
            if total_tonnes > 0
            else 0.0,
            "type_breakdown": {k: round(v, 2) for k, v in type_breakdown.items()},
            "region_breakdown": {k: round(v, 2) for k, v in region_breakdown.items()},
            "standard_breakdown": {
                k: round(v, 2) for k, v in standard_breakdown.items()
            },
            "holding_count": len(self.holdings),
        }

    def calculate_rebalancing_trades(self) -> List[Dict[str, Any]]:
        """Calculates the trades needed to reach the target allocation."""
        summary = self.get_portfolio_summary()
        total_tonnes = summary["total_tonnes"]
        if total_tonnes == 0:
            return []

        trades = []
        current_type_tonnes = summary["type_breakdown"]

        for p_type, target_pct in self.TARGET_ALLOCATION.items():
            target_tonnes = total_tonnes * target_pct
            current_tonnes = current_type_tonnes.get(p_type, 0.0)
            difference = target_tonnes - current_tonnes

            if abs(difference) > 0.1:  # Threshold to avoid micro-trades
                action = "buy" if difference > 0 else "sell"
                trades.append(
                    {
                        "project_type": p_type,
                        "action": action,
                        "tonnes": round(abs(difference), 2),
                        "current_allocation_pct": round(
                            (current_tonnes / total_tonnes) * 100, 1
                        ),
                        "target_allocation_pct": round(target_pct * 100, 1),
                    }
                )

        return trades
