# Dictionary of common items and their contamination risks in specific streams
CONTAMINATION_RULES = {
    "pizza box": {
        "recycling": "Grease contaminates paper recycling. Compost or landfill instead."
    },
    "plastic bag": {
        "recycling": "Tangles in sorting machinery. Return to store drop-off."
    },
    "styrofoam": {"recycling": "Not recyclable in most municipal systems. Landfill."},
    "glass window": {
        "recycling": "Different melting point than bottle glass. Landfill or special facility."
    },
    "battery": {
        "recycling": "Fire hazard in recycling trucks. Must go to hazardous src.environment.waste."
    },
    "electronics": {
        "recycling": "Contains hazardous materials. Must go to e-waste/hazardous."
    },
    "soiled paper": {
        "recycling": "Food residue contaminates paper. Compost or landfill."
    },
    "coffee cup": {
        "recycling": "Plastic lining makes it non-recyclable. Landfill (or compost if certified)."
    },
}


def check_contamination(item_name: str, intended_stream: str) -> tuple[bool, str]:
    """
    Checks if an item is contaminated in the intended waste stream.
    Returns (is_contaminated: bool, reason: str)
    """
    item_lower = item_name.lower()

    for keyword, rules in CONTAMINATION_RULES.items():
        if keyword in item_lower and intended_stream in rules:
            return True, rules[intended_stream]

    return False, ""


def get_contamination_penalty(contamination_ratio: float) -> float:
    """
    Calculates a penalty score (0-100) based on the ratio of contaminated weight
    to total intended recycling weight.
    """
    if contamination_ratio <= 0.05:
        return 0.0  # <5% contamination: Excellent
    elif contamination_ratio <= 0.15:
        return 15.0  # 5-15%: Good, minor issues
    elif contamination_ratio <= 0.30:
        return 40.0  # 15-30%: Fair, needs improvement
    else:
        return 80.0  # >30%: Poor, high contamination
