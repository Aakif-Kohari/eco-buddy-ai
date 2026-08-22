from typing import Any

# Keyword mapping for emission categories
CATEGORY_KEYWORDS = {
    "electricity": ["power", "light", "electric", "kwh", "energy", "utility"],
    "water": ["water", "sewer", "H2O"],
    "transportation": ["gas", "fuel", "uber", "lyft", "transit", "airline"],
    "diet": ["grocery", "market", "food", "restaurant", "beef", "vegetables"],
}


def categorize_bill(parsed_data: dict[str, Any]) -> dict[str, Any]:
    """
    Classifies the extracted data into existing emission categories using keyword matching.
    """
    raw_text = parsed_data.get("raw_text", "").lower()
    vendor = parsed_data.get("vendor", "").lower()
    combined_text = f"{raw_text} {vendor}"

    detected_categories = []
    primary_category = "general"

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in combined_text for keyword in keywords):
            detected_categories.append(category)

    if detected_categories:
        # Prioritize electricity if kWh is present
        if (
            parsed_data.get("energy_kwh") is not None
            and "electricity" in detected_categories
        ):
            primary_category = "electricity"
        else:
            primary_category = detected_categories[0]

    return {
        **parsed_data,
        "detected_categories": detected_categories,
        "primary_category": primary_category,
        "confidence": "high" if len(detected_categories) == 1 else "medium",
    }


def get_available_categories() -> list[str]:
    """Returns a list of valid emission categories for manual override."""
    return list(CATEGORY_KEYWORDS.keys()) + ["general"]
