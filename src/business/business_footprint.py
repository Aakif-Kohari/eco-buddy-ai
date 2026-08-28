from typing import Any

from src.carbon.scope3_screener import categorize_business_expense


def calculate_business_footprint(expenses: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Aggregates business expenses into a comprehensive Scope 3 footprint src.reporting.report.
    """
    total_emissions = 0.0
    category_breakdown = {}
    categorized_expenses = []

    for expense in expenses:
        try:
            categorized = categorize_business_expense(
                expense["type"], expense["amount"], expense.get("unit", "usd")
            )
            categorized_expenses.append(categorized)
            total_emissions += categorized["emissions_kg_co2e"]

            cat_name = categorized["category_name"]
            if cat_name not in category_breakdown:
                category_breakdown[cat_name] = 0.0
            category_breakdown[cat_name] += categorized["emissions_kg_co2e"]

        except ValueError as e:
            categorized_expenses.append(
                {
                    "expense_type": expense["type"],
                    "error": str(e),
                    "emissions_kg_co2e": 0.0,
                }
            )

    # Calculate a simple Business Eco-Score (0-100, lower emissions = higher score)
    # Baseline: 1000 kg CO2e is considered a "neutral" starting point for small businesses
    baseline = 1000.0
    eco_score = max(0, min(100, 100 - (total_emissions / baseline) * 50))

    return {
        "total_emissions_kg": round(total_emissions, 2),
        "category_breakdown": {k: round(v, 2) for k, v in category_breakdown.items()},
        "categorized_expenses": categorized_expenses,
        "business_eco_score": round(eco_score, 1),
        "expense_count": len(expenses),
    }


def generate_b2b_recommendations(footprint: dict[str, Any]) -> list[str]:
    """Generates B2B-specific sustainability src.ai.recommendations."""
    recommendations = []
    breakdown = footprint["category_breakdown"]

    if (
        "Purchased Goods and Services" in breakdown
        and breakdown["Purchased Goods and Services"] > 100
    ):
        src.ai.recommendations.append(
            "🖥️ **IT & Procurement:** Consider switching to green web hosting providers and purchasing refurbished office equipment to reduce Category 1 src.carbon.emissions."
        )

    if "Business Travel" in breakdown and breakdown["Business Travel"] > 200:
        src.ai.recommendations.append(
            "✈️ **Travel Policy:** Implement a 'virtual-first' meeting policy and prioritize rail travel over short-haul flights for Category 6 reductions."
        )

    if "Employee Commuting" in breakdown and breakdown["Employee Commuting"] > 150:
        src.ai.recommendations.append(
            "🚲 **Commuting:** Offer incentives for public transit, carpooling, or remote work days to lower Category 7 src.carbon.emissions."
        )

    if footprint["business_eco_score"] > 80:
        src.ai.recommendations.append(
            "🏆 **Leadership:** Your business footprint is excellent! Consider publishing a sustainability report to showcase your commitment to stakeholders."
        )
    elif not recommendations:
        src.ai.recommendations.append(
            "📊 **Baseline:** Start by tracking your expenses in the app to identify your largest emission hotspots."
        )

    return recommendations
