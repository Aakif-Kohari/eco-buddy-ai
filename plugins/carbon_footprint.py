"""
Carbon Footprint Calculator Plugin

This plugin estimates annual carbon emissions based on:
- Transport mode
- Daily travel distance (km)
- Monthly electricity consumption (kWh)
- Diet type
- Annual flights
- Region

Example Input:
{
    "transport": "Car",
    "distance": 20.0,
    "electricity": 250.0,
    "diet": "Vegetarian",
    "flights": 2,
    "region": "Global"
}

Returns:
CalcResult containing:
- total annual emissions (kg CO₂/year)
- emission contributors
- eco score
- audit log
"""

def calculate(self, inputs: dict) -> CalcResult:
    """
    Calculate the user's annual carbon footprint.

    Parameters
    ----------
    inputs : dict
        transport : str
            Primary transport mode.
        distance : float
            Daily travel distance in kilometers.
        electricity : float
            Monthly electricity usage in kWh.
        diet : str
            Vegetarian or Non-Vegetarian.
        flights : int
            Number of flights per year.
        region : str
            Emission factor region.

    Returns
    -------
    CalcResult
        Carbon footprint calculation result with metadata.
    """
from plugins.base import CalculatorPlugin, InputField, CalcResult
from emissions import calculate_footprint, calculate_eco_score, generate_full_audit_log
from recommendations import generate_recommendations
from config import DIET_TYPES, TRANSPORT_EMISSION_FACTORS, VALID_REGIONS


class CarbonFootprintPlugin(CalculatorPlugin):

    @property
    def name(self) -> str:
        return "carbon_footprint"

    @property
    def description(self) -> str:
        return "Estimate your annual carbon footprint from transport, electricity, diet, and flights."

    @property
    def category(self) -> str:
        return "Emissions"

    def get_input_fields(self) -> list[InputField]:
        return [
            InputField(
                name="transport",
                label="Primary Transport Mode",
                type="select",
                default="Car",
                options=tuple(sorted(TRANSPORT_EMISSION_FACTORS.keys())),
            ),
            InputField(
                name="distance",
                label="Daily Commute Distance (km)",
                type="number",
                default=20.0,
                min_val=0.0,
                max_val=500.0,
            ),
            InputField(
                name="electricity",
                label="Monthly Electricity Usage (kWh)",
                type="number",
                default=250.0,
                min_val=0.0,
                max_val=10000.0,
            ),
            InputField(
                name="diet",
                label="Diet Type",
                type="select",
                default="Vegetarian",
                options=tuple(DIET_TYPES),
            ),
            InputField(
                name="flights",
                label="Flights Per Year",
                type="number",
                default=0,
                min_val=0,
                max_val=365,
            ),
            InputField(
                name="region",
                label="Region",
                type="select",
                default="Global",
                options=tuple(sorted(VALID_REGIONS)),
            ),
        ]

    def calculate(self, inputs: dict) -> CalcResult:
        transport = inputs["transport"]
        distance = inputs["distance"]
        electricity = inputs["electricity"]
        diet = inputs["diet"]
        flights = inputs["flights"]
        region = inputs.get("region", "Global")

        total_kg, contributors, audit_log = calculate_footprint(
            transport=transport,
            distance=distance,
            electricity=electricity,
            diet=diet,
            flights=flights,
            region=region,
            return_audit=True
        )
        eco_score = calculate_eco_score(total_kg, contributors)
        full_audit = generate_full_audit_log(transport, distance, electricity, diet, flights, region)

        return CalcResult(
            total=total_kg,
            unit="kg CO2/year",
            contributors=contributors,
            metadata={
                "eco_score": eco_score,
                "transport": transport,
                "distance": distance,
                "electricity": electricity,
                "diet": diet,
                "flights": flights,
                "region": region,
                "audit_log": full_audit
            },
        )

    def get_recommendations(self, result: CalcResult) -> list[str]:
        meta = result.metadata
        _, recs = generate_recommendations(
            transport=meta.get("transport", ""),
            electricity=meta.get("electricity", 0),
            diet=meta.get("diet", ""),
            flights=meta.get("flights", 0),
            contributors=result.contributors,
        )
        return recs
