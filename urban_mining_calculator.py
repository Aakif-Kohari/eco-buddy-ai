"""
Urban Mining Calculator.
Estimates the weight and type of critical minerals in consumer electronics and quantifies recycling benefits.
"""

from typing import Dict, Any, List
from critical_mineral_db import CriticalMineralDB


class UrbanMiningCalculator:
    """Calculates the urban mining value and carbon avoidance of recycling electronics."""

    def __init__(self):
        self.db = CriticalMineralDB()
        self.logged_devices: List[Dict[str, Any]] = []

    def add_device(self, device_key: str, quantity: int = 1) -> bool:
        """Adds a device to the user's end-of-life inventory."""
        profile = self.db.get_device_profile(device_key)
        if not profile:
            return False

        self.logged_devices.append(
            {
                "device_key": device_key,
                "device_name": profile["name"],
                "quantity": quantity,
            }
        )
        return True

    def calculate_recovery_value(self) -> Dict[str, Any]:
        """Calculates the total mineral recovery value and carbon avoidance."""
        total_minerals_g = {}
        total_carbon_avoided_kg = 0.0
        total_devices = 0

        for item in self.logged_devices:
            device_key = item["device_key"]
            quantity = item["quantity"]
            total_devices += quantity

            profile = self.db.get_device_profile(device_key)
            for mineral, data in profile["minerals"].items():
                weight_per_device = data["weight_g"]
                virgin_carbon = data["virgin_carbon_kg_per_g"]
                recovery_rate = data["recovery_rate_pct"] / 100.0

                total_weight = weight_per_device * quantity
                recovered_weight = total_weight * recovery_rate
                carbon_avoided = recovered_weight * virgin_carbon

                if mineral not in total_minerals_g:
                    total_minerals_g[mineral] = 0.0

                total_minerals_g[mineral] += recovered_weight
                total_carbon_avoided_kg += carbon_avoided

        return {
            "total_devices": total_devices,
            "recovered_minerals_g": {
                k: round(v, 3) for k, v in total_minerals_g.items()
            },
            "total_carbon_avoided_kg": round(total_carbon_avoided_kg, 3),
            "urban_mining_score": self._calculate_score(
                total_devices, total_carbon_avoided_kg
            ),
        }

    def _calculate_score(self, devices: int, carbon_avoided: float) -> int:
        """Calculates a simple 0-100 'Urban Mining Value' score."""
        # Base score on carbon avoided, scaled reasonably
        # e.g., 1 kg avoided = 10 points, max 100
        score = min(100, int(carbon_avoided * 10))
        return max(0, score)

    def get_recycling_recommendations(self) -> List[str]:
        """Provides actionable steps for responsible device end-of-life management."""
        if not self.logged_devices:
            return ["Log some devices to see recycling recommendations."]

        recs = [
            "♻️ **Certified Recyclers:** Look for e-Stewards or R2 certified recycling facilities to ensure safe, ethical processing.",
            "📱 **Manufacturer Take-Back:** Many major brands (Apple, Samsung, Dell) offer free mail-in recycling programs.",
            "🔋 **Battery Safety:** Never dispose of devices with swollen or damaged batteries in regular trash. Tape terminals before recycling.",
        ]
        return recs

    def clear_inventory(self) -> None:
        """Clears all logged devices."""
        self.logged_devices = []
