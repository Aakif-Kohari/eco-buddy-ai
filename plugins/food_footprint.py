"""
Food Footprint Calculator Plugin for EcoBuddy AI
Provides detailed lifecycle carbon and water footprint analysis across dietary components.
"""

from typing import Dict, Any, List
from plugins.base import CalculatorPlugin, InputField, CalcResult
from src.lifestyle.meal_planner import INGREDIENTS, impact_tier


# Diet type consumption defaults (servings / grams per day approximations)
DIET_PROFILES = {
    "Heavy Meat": {
        "Beef": 150.0,
        "Pork": 100.0,
        "Chicken": 100.0,
        "Dairy": 250.0,
        "Grains": 300.0,
        "Vegetables": 200.0,
    },
    "Omnivore": {
        "Chicken": 120.0,
        "Eggs": 60.0,
        "Dairy": 200.0,
        "Grains": 300.0,
        "Vegetables": 300.0,
    },
    "Pescatarian": {
        "Farmed fish": 120.0,
        "Eggs": 60.0,
        "Dairy": 200.0,
        "Grains": 300.0,
        "Vegetables": 350.0,
    },
    "Vegetarian": {
        "Eggs": 60.0,
        "Dairy": 250.0,
        "Tofu": 100.0,
        "Lentils": 150.0,
        "Grains": 350.0,
        "Vegetables": 400.0,
    },
    "Vegan": {
        "Tofu": 150.0,
        "Tempeh": 100.0,
        "Lentils": 200.0,
        "Chickpeas": 150.0,
        "Grains": 400.0,
        "Vegetables": 500.0,
    }
}


class FoodFootprintPlugin(CalculatorPlugin):
    """
    Plugin for computing annual food carbon and water footprint
    based on meal frequency, meat intake, and food waste percentages.
    """

    @property
    def name(self) -> str:
        return "food_footprint"

    @property
    def description(self) -> str:
        return "Calculate annual dietary greenhouse emissions and virtual water footprints from eating habits."

    @property
    def category(self) -> str:
        return "Food & Agriculture"

    def get_input_fields(self) -> List[InputField]:
        return [
            InputField(
                name="diet_pattern",
                label="Dietary Pattern",
                type="select",
                default="Omnivore",
                options=tuple(sorted(DIET_PROFILES.keys())),
                help_text="Primary baseline dietary preference."
            ),
            InputField(
                name="red_meat_meals_per_week",
                label="Red Meat Meals Per Week",
                type="number",
                default=3.0,
                min_val=0.0,
                max_val=21.0,
                help_text="Number of meals per week featuring beef, lamb, or pork."
            ),
            InputField(
                name="dairy_servings_per_day",
                label="Dairy Servings Per Day",
                type="number",
                default=2.0,
                min_val=0.0,
                max_val=10.0,
                help_text="Daily portions of cheese, milk, or yogurt."
            ),
            InputField(
                name="food_waste_pct",
                label="Estimated Food Waste (%)",
                type="number",
                default=15.0,
                min_val=0.0,
                max_val=80.0,
                help_text="Estimated portion of purchased food discarded uneaten."
            ),
            InputField(
                name="organic_local_pct",
                label="Local / Seasonal / Plant-rich Share (%)",
                type="number",
                default=20.0,
                min_val=0.0,
                max_val=100.0,
                help_text="Share of diet sourced locally, seasonally, or organically."
            )
        ]

    def calculate(self, inputs: Dict[str, Any]) -> CalcResult:
        diet_pattern = inputs.get("diet_pattern", "Omnivore")
        if diet_pattern not in DIET_PROFILES:
            diet_pattern = "Omnivore"

        red_meat_meals = float(inputs.get("red_meat_meals_per_week", 3.0))
        dairy_servings = float(inputs.get("dairy_servings_per_day", 2.0))
        food_waste_pct = float(inputs.get("food_waste_pct", 15.0))
        organic_local_pct = float(inputs.get("organic_local_pct", 20.0))

        # Baseline annual calculation
        # Beef factor: 60.0 kg CO2 / kg food. Typical serving = 0.15 kg
        # 1 meal = 0.15 kg * 60 = 9 kg CO2
        red_meat_co2 = red_meat_meals * 52 * 0.15 * 45.0  # weighted red meat mix
        red_meat_water = red_meat_meals * 52 * 0.15 * 12000.0

        # Dairy: ~1.8 kg CO2 and 1000 L water per serving (250g milk / 40g cheese eq)
        dairy_co2 = dairy_servings * 365 * 0.25 * 3.2
        dairy_water = dairy_servings * 365 * 0.25 * 2500.0

        # Other baseline items based on diet pattern
        base_co2_kg = {
            "Vegan": 600.0,
            "Vegetarian": 950.0,
            "Pescatarian": 1300.0,
            "Omnivore": 1700.0,
            "Heavy Meat": 2500.0,
        }.get(diet_pattern, 1700.0)

        base_water_l = {
            "Vegan": 2000.0 * 365,
            "Vegetarian": 2500.0 * 365,
            "Pescatarian": 3200.0 * 365,
            "Omnivore": 4000.0 * 365,
            "Heavy Meat": 5000.0 * 365,
        }.get(diet_pattern, 4000.0 * 365)

        total_co2_raw = (base_co2_kg * 0.4) + red_meat_co2 + dairy_co2
        total_water_raw = (base_water_l * 0.4) + red_meat_water + dairy_water

        # Adjust for local/seasonal reduction (up to 12% benefit)
        local_savings_factor = 1.0 - (organic_local_pct / 100.0 * 0.12)
        total_co2_adjusted = total_co2_raw * local_savings_factor

        # Adjust for food waste inflation
        waste_multiplier = 1.0 + (food_waste_pct / 100.0)
        final_co2_kg = round(total_co2_adjusted * waste_multiplier, 2)
        final_water_l = round(total_water_raw * waste_multiplier, 1)

        contributors = {
            "Red Meat": round(red_meat_co2 * waste_multiplier, 2),
            "Dairy & Eggs": round(dairy_co2 * waste_multiplier, 2),
            "Plant & Grain Baseline": round(base_co2_kg * 0.4 * local_savings_factor * waste_multiplier, 2),
            "Food Waste Burden": round(total_co2_adjusted * (food_waste_pct / 100.0), 2)
        }

        metadata = {
            "annual_water_liters": final_water_l,
            "daily_co2_kg": round(final_co2_kg / 365.0, 2),
            "diet_pattern": diet_pattern,
            "food_waste_kg_co2": round(total_co2_adjusted * (food_waste_pct / 100.0), 2),
            "trees_to_offset": round(final_co2_kg / 22.0, 1),
            "impact_rating": impact_tier(final_co2_kg / 1000.0)
        }

        return CalcResult(
            total=final_co2_kg,
            unit="kg CO2e/year",
            contributors=contributors,
            metadata=metadata
        )

    def get_recommendations(self, result: CalcResult) -> List[str]:
        recs = []
        contributors = result.contributors
        metadata = result.metadata

        if contributors.get("Red Meat", 0) > 400.0:
            recs.append("🥩 Swap 2 red meat meals per week for lentils, beans, or tofu to cut ~400 kg CO2/year.")
        if contributors.get("Food Waste Burden", 0) > 100.0:
            recs.append("🗑️ Plan weekly meals and freeze leftovers to eliminate food waste src.carbon.emissions.")
        if contributors.get("Dairy & Eggs", 0) > 300.0:
            recs.append("🥛 Explore oat, soy, or almond milk alternatives for daily coffee or cooking.")
        if metadata.get("annual_water_liters", 0) > 1200000.0:
            recs.append("💧 Shift towards seasonal legumes to significantly reduce indirect virtual water usage.")

        if not recs:
            recs.append("🌱 Outstanding food choices! Your dietary footprint is in the top eco-efficient tier.")

        return recs
