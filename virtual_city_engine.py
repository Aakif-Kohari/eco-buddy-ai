from typing import Dict, Any, List
from database import get_virtual_city_state, save_virtual_city_state

class VirtualCityEngine:
    """
    Manages the virtual city state, unlocking 3D assets based on carbon savings.
    """
    # Define the mapping between carbon saved (kg) and 3D assets
    ASSET_THRESHOLDS = [
        (0, {"id": "grass", "name": "Green Grass", "type": "terrain"}),
        (50, {"id": "tree_small", "name": "Small Tree", "type": "flora"}),
        (150, {"id": "tree_large", "name": "Large Tree", "type": "flora"}),
        (300, {"id": "solar_panel", "name": "Solar Panel", "type": "energy"}),
        (600, {"id": "wind_turbine", "name": "Wind Turbine", "type": "energy"}),
        (1000, {"id": "eco_house", "name": "Eco House", "type": "building"}),
        (2000, {"id": "smart_grid", "name": "Smart Grid Hub", "type": "building"}),
        (5000, {"id": "vertical_farm", "name": "Vertical Farm", "type": "building"}),
    ]

    def __init__(self, user_id: int):
        self.user_id = user_id

    def get_state(self) -> Dict[str, Any]:
        """Returns the current state of the virtual city for the user."""
        return get_virtual_city_state(self.user_id)

    def calculate_unlocked_assets(self, total_carbon_saved_kg: float) -> List[Dict[str, str]]:
        """Calculates which assets should be unlocked based on total carbon saved."""
        unlocked = []
        for threshold, asset in self.ASSET_THRESHOLDS:
            if total_carbon_saved_kg >= threshold:
                unlocked.append(asset)
        return unlocked

    def update_city_state(self, total_carbon_saved_kg: float) -> Dict[str, Any]:
        """
        Updates the city state with a new carbon saved total,
        unlocking new assets if thresholds are met.
        """
        current_state = self.get_state()
        new_unlocked_assets = self.calculate_unlocked_assets(total_carbon_saved_kg)
        
        # In a more advanced version, we could auto-place new items into layout_state
        # For now, layout_state can remain untouched if not specifically updated
        layout_state = current_state.get("layout_state", {})
        
        save_virtual_city_state(
            user_id=self.user_id,
            carbon_saved_kg=total_carbon_saved_kg,
            unlocked_assets=new_unlocked_assets,
            layout_state=layout_state
        )
        
        return self.get_state()
