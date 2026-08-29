from typing import Any

# GHG Protocol Scope 3 Categories Mapping
SCOPE3_CATEGORIES = {
    "software_cloud": {
        "category_id": 1,
        "category_name": "Purchased Goods and Services",
        "emission_factor_kg_per_usd": 0.35,
        "description": "Emissions from software subscriptions, cloud hosting, and IT services.",
    },
    "business_travel_air": {
        "category_id": 6,
        "category_name": "Business Travel",
        "emission_factor_kg_per_unit": 0.255,  # kg CO2e per passenger-km
        "unit": "km",
        "description": "Emissions from employee air travel for business purposes.",
    },
    "business_travel_ground": {
        "category_id": 6,
        "category_name": "Business Travel",
        "emission_factor_kg_per_unit": 0.192,  # kg CO2e per passenger-km
        "unit": "km",
        "description": "Emissions from employee ground travel (car, train) for business.",
    },
    "office_supplies": {
        "category_id": 1,
        "category_name": "Purchased Goods and Services",
        "emission_factor_kg_per_usd": 0.50,
        "description": "Emissions from procurement of physical office supplies and equipment.",
    },
    "employee_commuting": {
        "category_id": 7,
        "category_name": "Employee Commuting",
        "emission_factor_kg_per_unit": 0.150,  # kg CO2e per passenger-km
        "unit": "km",
        "description": "Emissions from employees commuting to and from work.",
    },
    "waste_generated": {
        "category_id": 5,
        "category_name": "Waste Generated in Operations",
        "emission_factor_kg_per_kg": 0.5,  # kg CO2e per kg of waste
        "unit": "kg",
        "description": "Emissions from disposal of waste generated in business operations.",
    },
}


def categorize_business_expense(
    expense_type: str, amount: float, unit: str = "usd"
) -> dict[str, Any]:
    """
    Categorizes a business expense into a Scope 3 category and calculates src.carbon.emissions.
    """
    if expense_type not in SCOPE3_CATEGORIES:
        raise ValueError(f"Unknown expense type: {expense_type}")

    category_info = SCOPE3_CATEGORIES[expense_type]

    if "per_usd" in str(category_info.get("emission_factor_kg_per_usd", "")):
        factor = category_info["emission_factor_kg_per_usd"]
        emissions = amount * factor
    elif "per_unit" in str(category_info.get("emission_factor_kg_per_unit", "")):
        factor = category_info["emission_factor_kg_per_unit"]
        emissions = amount * factor
    else:
        raise ValueError("Invalid emission factor configuration for category.")

    return {
        "expense_type": expense_type,
        "category_id": category_info["category_id"],
        "category_name": category_info["category_name"],
        "amount": amount,
        "unit": unit,
        "emissions_kg_co2e": round(emissions, 2),
        "description": category_info["description"],
    }


def get_all_scope3_categories() -> list[dict[str, Any]]:
    """Returns a list of all available Scope 3 categories for UI selection."""
    unique_categories = {}
    for info in SCOPE3_CATEGORIES.values():
        cat_id = info["category_id"]
        if cat_id not in unique_categories:
            unique_categories[cat_id] = {
                "id": cat_id,
                "name": info["category_name"],
                "description": f"Category {cat_id}: {info['category_name']}",
            }
    return list(unique_categories.values())
