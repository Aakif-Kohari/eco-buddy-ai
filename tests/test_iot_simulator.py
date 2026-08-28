import pytest

from src.core.config import HOURS_PER_DAY
from src.utils.device_registry import get_all_devices, get_device_by_id
from src.utils.iot_simulator import calculate_iot_savings, simulate_iot_energy_stream


def test_get_all_devices():
    devices = get_all_devices()
    assert len(devices) > 0
    assert all("id" in d and "name" in d for d in devices)


def test_get_device_by_id_valid():
    device = get_device_by_id("smart_thermostat")
    assert device["name"] == "Smart Thermostat"
    assert device["base_power_watts"] == 5.0


def test_get_device_by_id_invalid():
    with pytest.raises(ValueError, match="not found in catalog"):
        get_device_by_id("nonexistent_device")


def test_simulate_iot_energy_stream_length():
    readings = simulate_iot_energy_stream("smart_led_bulb", days=2)
    assert len(readings) == 2 * HOURS_PER_DAY
    assert all("power_watts" in r and "energy_kwh" in r for r in readings)
    assert all(r["power_watts"] >= 0 for r in readings)


def test_calculate_iot_savings_positive():
    # Simulate a device using 1 kWh total over 1 day
    readings = [
        {"hour_index": i, "power_watts": 0, "energy_kwh": 1.0 / 24} for i in range(24)
    ]
    baseline_daily = 5.0

    savings = calculate_iot_savings(readings, baseline_daily, days=1)
    assert savings["simulated_total_kwh"] == 1.0
    assert savings["baseline_total_kwh"] == 5.0
    assert savings["savings_kwh"] == 4.0
    assert savings["savings_pct"] == 80.0


def test_calculate_iot_savings_negative():
    # Simulate a device using 10 kWh total over 1 day (worse than baseline)
    readings = [
        {"hour_index": i, "power_watts": 0, "energy_kwh": 10.0 / 24} for i in range(24)
    ]
    baseline_daily = 5.0

    savings = calculate_iot_savings(readings, baseline_daily, days=1)
    assert savings["savings_kwh"] == 0.0  # Max function should clamp to 0
    assert savings["savings_pct"] == 0.0
