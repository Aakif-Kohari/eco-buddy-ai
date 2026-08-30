"""
P2P Energy Trading.
Handles the matching logic, pricing dynamics, and transaction recording of simulated local energy trades.
"""

from typing import Dict, Any, List
from microgrid_simulator import MicrogridSimulator


class P2PEnergyTrading:
    """Manages peer-to-peer energy transactions within a microgrid."""

    def __init__(self, grid_import_price: float = 0.25, p2p_price: float = 0.15):
        """
        Args:
            grid_import_price: Cost to buy from the main grid ($/kWh).
            p2p_price: Price for local P2P energy trades ($/kWh).
        """
        self.simulator = MicrogridSimulator()
        self.grid_import_price = grid_import_price
        self.p2p_price = p2p_price
        self.transactions: List[Dict[str, Any]] = []

    def execute_hourly_trades(self, hour_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Matches excess generation with local deficits for a specific hour.

        Args:
            hour_profile: The output from MicrogridSimulator.generate_hourly_profile().

        Returns:
            Summary of trades executed during this hour.
        """
        hour = hour_profile["hour"]
        households = hour_profile["household_details"]

        # Separate into suppliers (net > 0) and consumers (net < 0)
        suppliers = {
            h_id: data["net_kw"]
            for h_id, data in households.items()
            if data["net_kw"] > 0
        }
        consumers = {
            h_id: abs(data["net_kw"])
            for h_id, data in households.items()
            if data["net_kw"] < 0
        }

        total_p2p_volume_kwh = 0.0
        hour_transactions = []

        # Simple matching algorithm: fulfill consumer demand from available suppliers
        for consumer_id, deficit in consumers.items():
            remaining_deficit = deficit

            for supplier_id, surplus in list(suppliers.items()):
                if remaining_deficit <= 0 or surplus <= 0:
                    continue

                trade_volume = min(remaining_deficit, surplus)

                # Record transaction
                transaction = {
                    "hour": hour,
                    "supplier_id": supplier_id,
                    "consumer_id": consumer_id,
                    "volume_kwh": round(trade_volume, 3),
                    "price_per_kwh": self.p2p_price,
                    "total_cost": round(trade_volume * self.p2p_price, 3),
                }
                hour_transactions.append(transaction)
                self.transactions.append(transaction)

                total_p2p_volume_kwh += trade_volume
                remaining_deficit -= trade_volume
                suppliers[supplier_id] -= trade_volume  # Update remaining surplus

        # Calculate financial metrics for this hour
        total_demand = hour_profile["total_demand_kw"]
        total_local_gen = hour_profile["total_generation_kw"]

        # Money saved by buying P2P instead of from grid
        money_saved = total_p2p_volume_kwh * (self.grid_import_price - self.p2p_price)

        # Carbon avoided (mock grid intensity: 0.4 kg/kWh, local solar: 0.0 kg/kWh)
        carbon_avoided_kg = total_p2p_volume_kwh * 0.4

        return {
            "hour": hour,
            "total_p2p_volume_kwh": round(total_p2p_volume_kwh, 3),
            "money_saved_usd": round(money_saved, 3),
            "carbon_avoided_kg": round(carbon_avoided_kg, 3),
            "transactions": hour_transactions,
        }

    def simulate_and_trade_full_day(self) -> Dict[str, Any]:
        """Runs a full day simulation and executes P2P trades for each hour."""
        daily_profile = self.simulator.simulate_full_day()
        daily_trades = []

        total_volume = 0.0
        total_savings = 0.0
        total_carbon_avoided = 0.0

        for hour_data in daily_profile:
            trade_result = self.execute_hourly_trades(hour_data)
            daily_trades.append(trade_result)

            total_volume += trade_result["total_p2p_volume_kwh"]
            total_savings += trade_result["money_saved_usd"]
            total_carbon_avoided += trade_result["carbon_avoided_kg"]

        independence = self.simulator.calculate_grid_independence(daily_profile)

        return {
            "daily_profile": daily_profile,
            "hourly_trades": daily_trades,
            "summary": {
                "total_p2p_volume_kwh": round(total_volume, 3),
                "total_money_saved_usd": round(total_savings, 3),
                "total_carbon_avoided_kg": round(total_carbon_avoided, 3),
                "grid_independence_pct": independence,
            },
        }
