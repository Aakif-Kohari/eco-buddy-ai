"""
Local Exchange Market Simulator.
Simulates a dynamic market with fluctuating carbon prices based on supply and demand.
"""

import random
import math
from typing import Dict, Any, List


class LocalExchangeMarket:
    """Simulates carbon allowance market dynamics."""

    BASE_PRICE_PER_TONNE = 50.0  # USD
    VOLATILITY = 0.05  # 5% random walk

    def __init__(self):
        self.current_price = self.BASE_PRICE_PER_TONNE
        self.historical_prices: List[float] = [self.current_price]
        self.market_depth = {"supply": 10000.0, "demand": 10000.0}  # in kg

    def update_market_conditions(self, net_demand_change_kg: float) -> float:
        """
        Updates market price based on net demand changes.
        Positive net demand increases price, negative decreases it.
        """
        self.market_depth["demand"] += max(0, net_demand_change_kg)
        self.market_depth["supply"] += max(0, -net_demand_change_kg)

        # Price impact model: logarithmic impact based on order book imbalance
        imbalance = (
            self.market_depth["demand"] - self.market_depth["supply"]
        ) / 10000.0
        impact_factor = math.tanh(imbalance * 0.1)  # Bounded between -1 and 1

        # Add random walk volatility
        random_shock = random.uniform(-self.VOLATILITY, self.VOLATILITY)

        # Calculate new price
        multiplier = 1.0 + impact_factor + random_shock
        self.current_price = max(
            5.0, self.current_price * multiplier
        )  # Floor at $5/tonne
        self.historical_prices.append(self.current_price)

        return round(self.current_price, 2)

    def get_market_snapshot(self) -> Dict[str, Any]:
        """Returns current market state."""
        return {
            "current_price_per_tonne_usd": round(self.current_price, 2),
            "total_supply_kg": round(self.market_depth["supply"], 2),
            "total_demand_kg": round(self.market_depth["demand"], 2),
            "price_trend": "up"
            if len(self.historical_prices) > 1
            and self.historical_prices[-1] > self.historical_prices[-2]
            else "down",
            "volatility_index": round(self.VOLATILITY * 100, 1),
        }

    def simulate_trading_day(self, steps: int = 24) -> List[float]:
        """Simulates a day of trading to generate price history for charts."""
        prices = []
        for _ in range(steps):
            net_demand = random.uniform(-500, 500)
            prices.append(self.update_market_conditions(net_demand))
        return prices
