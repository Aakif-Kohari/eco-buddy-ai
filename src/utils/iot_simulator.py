import random
from typing import Any

from src.core.config import HOURS_PER_DAY
from src.utils.device_registry import get_device_by_id


def simulate_iot_energy_stream(
    device_id: str, days: int = 1, variance: float = 0.1
) -> list[dict[str, Any]]:
    """
    Generates a mock time-series energy consumption stream for a connected device.
    Returns a list of hourly readings.
    """
    device = get_device_by_id(device_id)
    base_watts = device["base_power_watts"]
    peak_watts = device["peak_power_watts"]
    typical_hours = device["typical_daily_hours"]

    readings = []
    total_hours = days * HOURS_PER_DAY

    # Determine how many hours the device will be in "peak" usage mode
    peak_hours_total = int(typical_hours * days)
    peak_hours_indices = random.sample(range(total_hours), peak_hours_total)

    for hour in range(total_hours):
        if hour in peak_hours_indices:
            # Peak usage with some variance
            current_watts = peak_watts * random.uniform(1.0 - variance, 1.0 + variance)
        else:
            # Standby/base usage
            current_watts = base_watts * random.uniform(1.0 - variance, 1.0 + variance)

        current_watts = max(0.0, current_watts)
        energy_kwh = current_watts / 1000.0  # Convert to kWh for the hour

        readings.append(
            {
                "hour_index": hour,
                "power_watts": round(current_watts, 2),
                "energy_kwh": round(energy_kwh, 4),
            }
        )

    return readings


def calculate_iot_savings(
    simulated_readings: list[dict[str, Any]], baseline_daily_kwh: float, days: int
) -> dict[str, Any]:
    """
    Compares simulated IoT usage against a user's historical baseline.
    """
    total_simulated_kwh = sum(r["energy_kwh"] for r in simulated_readings)
    total_baseline_kwh = baseline_daily_kwh * days

    savings_kwh = max(0.0, total_baseline_kwh - total_simulated_kwh)
    savings_pct = (
        (savings_kwh / total_baseline_kwh * 100) if total_baseline_kwh > 0 else 0.0
    )

    return {
        "simulated_total_kwh": round(total_simulated_kwh, 2),
        "baseline_total_kwh": round(total_baseline_kwh, 2),
        "savings_kwh": round(savings_kwh, 2),
        "savings_pct": round(savings_pct, 1),
    }
