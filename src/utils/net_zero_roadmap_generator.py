"""
Net-Zero Roadmap Generator.
Builds a phased reduction plan, suggesting specific interventions mapped to specific years.
"""

from typing import Dict, Any, List
from src.carbon.emissions_gap_analyzer import EmissionsGapAnalyzer


class NetZeroRoadmapGenerator:
    """Generates a year-by-year actionable roadmap to bridge the emissions gap."""

    # Library of interventions with typical reduction potential (%) and required scope
    INTERVENTIONS = {
        "led_lighting": {
            "name": "LED Lighting Retrofit",
            "reduction_pct": 2.0,
            "target_scope": 2,
            "year_earliest": 1,
        },
        "smart_hvac": {
            "name": "Smart HVAC Optimization",
            "reduction_pct": 5.0,
            "target_scope": 2,
            "year_earliest": 1,
        },
        "fleet_electrification_25": {
            "name": "Electrify 25% of Fleet",
            "reduction_pct": 8.0,
            "target_scope": 1,
            "year_earliest": 2,
        },
        "fleet_electrification_100": {
            "name": "Electrify 100% of Fleet",
            "reduction_pct": 15.0,
            "target_scope": 1,
            "year_earliest": 4,
        },
        "renewable_energy_50": {
            "name": "Procure 50% Renewable Energy",
            "reduction_pct": 10.0,
            "target_scope": 2,
            "year_earliest": 2,
        },
        "renewable_energy_100": {
            "name": "Procure 100% Renewable Energy",
            "reduction_pct": 20.0,
            "target_scope": 2,
            "year_earliest": 4,
        },
        "supplier_engagement": {
            "name": "Top 20% Supplier Engagement",
            "reduction_pct": 5.0,
            "target_scope": 3,
            "year_earliest": 2,
        },
        "circular_packaging": {
            "name": "Transition to Circular Packaging",
            "reduction_pct": 3.0,
            "target_scope": 3,
            "year_earliest": 3,
        },
        "carbon_removal": {
            "name": "High-Quality Carbon Removal Offsets",
            "reduction_pct": 10.0,
            "target_scope": "all",
            "year_earliest": 5,
        },
    }

    def __init__(self, analyzer: EmissionsGapAnalyzer):
        self.analyzer = analyzer

    def generate_roadmap(self) -> Dict[str, Any]:
        """Generates a sequenced, year-by-year reduction roadmap."""
        gap_analysis = self.analyzer.calculate_required_reduction_rate()

        if gap_analysis["status"] != "valid":
            return {"error": gap_analysis["message"]}

        scope_breakdown = self.analyzer.get_scope_breakdown()
        required_rate = gap_analysis["required_annual_reduction_pct"]
        years = gap_analysis["years_remaining"]

        roadmap = []
        cumulative_reduction = 0.0
        current_emissions = self.analyzer.total_current

        for year_offset in range(1, years + 1):
            target_year = self.analyzer.current_year + year_offset
            year_interventions = []
            year_reduction = 0.0

            # Select interventions appropriate for this year and scope
            for key, intervention in self.INTERVENTIONS.items():
                if intervention["year_earliest"] <= year_offset:
                    # Check if this intervention targets the dominant scope
                    if (
                        intervention["target_scope"] == "all"
                        or (
                            intervention["target_scope"] == 1
                            and scope_breakdown["scope1_pct"] > 20
                        )
                        or (
                            intervention["target_scope"] == 2
                            and scope_breakdown["scope2_pct"] > 20
                        )
                        or (
                            intervention["target_scope"] == 3
                            and scope_breakdown["scope3_pct"] > 20
                        )
                    ):
                        # Avoid duplicate interventions
                        if not any(i["key"] == key for i in roadmap):
                            year_interventions.append(
                                {
                                    "key": key,
                                    "name": intervention["name"],
                                    "reduction_pct": intervention["reduction_pct"],
                                }
                            )
                            year_reduction += intervention["reduction_pct"]

            # Cap annual reduction to realistic maximum (e.g., 15% per year)
            year_reduction = min(year_reduction, 15.0)
            cumulative_reduction += year_reduction

            # Calculate projected emissions for this year
            # Using a simplified linear-ish decay based on cumulative interventions
            projected_emissions = current_emissions * (
                1 - (cumulative_reduction / 100.0)
            )
            projected_emissions = max(
                self.analyzer.total_current * 0.01, projected_emissions
            )  # Floor at 1%

            roadmap.append(
                {
                    "year": target_year,
                    "year_offset": year_offset,
                    "interventions": year_interventions,
                    "projected_annual_reduction_pct": round(year_reduction, 1),
                    "cumulative_reduction_pct": round(cumulative_reduction, 1),
                    "projected_emissions": round(projected_emissions, 2),
                }
            )

        return {
            "gap_analysis": gap_analysis,
            "scope_breakdown": scope_breakdown,
            "roadmap": roadmap,
            "final_projected_emissions": roadmap[-1]["projected_emissions"]
            if roadmap
            else 0.0,
            "target_met": (
                roadmap[-1]["projected_emissions"] <= self.analyzer.total_current * 0.01
            )
            if roadmap
            else False,
        }
