import random
from typing import Any

from src.core.config import HOURS_PER_DAY

# Base carbon intensity profiles (kg CO2e / kWh) for different grid types
GRID_PROFILES = {
    "coal_heavy": [
        0.80,
        0.85,
        0.82,
        0.80,
        0.78,
        0.75,
        0.70,
        0.65,
        0.60,
        0.55,
        0.50,
        0.48,
        0.45,
        0.42,
        0.40,
        0.45,
        0.55,
        0.65,
        0.75,
        0.80,
        0.82,
        0.85,
        0.88,
        0.85,
    ],
    "mixed": [
        0.40,
        0.38,
        0.35,
        0.32,
        0.30,
        0.28,
        0.25,
        0.22,
        0.20,
        0.18,
        0.15,
        0.14,
        0.15,
        0.18,
        0.22,
        0.28,
        0.35,
        0.42,
        0.48,
        0.50,
        0.48,
        0.45,
        0.42,
        0.40,
    ],
    "renewable_heavy": [
        0.15,
        0.12,
        0.10,
        0.08,
        0.05,
        0.04,
        0.03,
        0.02,
        0.01,
        0.01,
        0.02,
        0.03,
        0.04,
        0.05,
        0.08,
        0.12,
        0.18,
        0.22,
        0.25,
        0.20,
        0.18,
        0.16,
        0.15,
        0.14,
    ],
}

# Dynamic pricing profiles ($ / kWh)
PRICING_PROFILES = {
    "flat": [0.15] * HOURS_PER_DAY,
    "time_of_use": [
        0.12,
        0.11,
        0.10,
        0.09,
        0.08,
        0.08,
        0.10,
        0.15,
        0.20,
        0.25,
        0.28,
        0.30,
        0.32,
        0.30,
        0.28,
        0.25,
        0.22,
        0.25,
        0.30,
        0.35,
        0.32,
        0.28,
        0.20,
        0.15,
    ],
}


def generate_grid_intensity_profile(
    grid_type: str = "mixed", variance: float = 0.05
) -> list[float]:
    """Generates a 24-hour grid carbon intensity profile with optional random variance."""
    if grid_type not in GRID_PROFILES:
        grid_type = "mixed"

    base_profile = GRID_PROFILES[grid_type]
    profile = []
    for intensity in base_profile:
        noisy_intensity = intensity + random.uniform(-variance, variance)
        profile.append(max(0.0, round(noisy_intensity, 4)))
    return profile


def generate_pricing_profile(
    pricing_type: str = "time_of_use", variance: float = 0.01
) -> list[float]:
    """Generates a 24-hour electricity pricing profile with optional random variance."""
    if pricing_type not in PRICING_PROFILES:
        pricing_type = "time_of_use"

    base_profile = PRICING_PROFILES[pricing_type]
    profile = []
    for price in base_profile:
        noisy_price = price + random.uniform(-variance, variance)
        profile.append(max(0.01, round(noisy_price, 4)))
    return profile


def get_grid_profile_metadata() -> dict[str, Any]:
    """Returns metadata about available grid profiles for UI display."""
    return {
        "coal_heavy": {
            "name": "Coal-Heavy Grid",
            "description": "Grid heavily reliant on fossil fuels, high baseline carbon intensity.",
            "avg_intensity": round(sum(GRID_PROFILES["coal_heavy"]) / HOURS_PER_DAY, 3),
        },
        "mixed": {
            "name": "Mixed Grid",
            "description": "Balanced grid with a mix of fossil fuels and renewables.",
            "avg_intensity": round(sum(GRID_PROFILES["mixed"]) / HOURS_PER_DAY, 3),
        },
        "renewable_heavy": {
            "name": "Renewable-Heavy Grid",
            "description": "Grid dominated by solar, wind, and hydroelectric power.",
            "avg_intensity": round(
                sum(GRID_PROFILES["renewable_heavy"]) / HOURS_PER_DAY, 3
            ),
        },
    }
