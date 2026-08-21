from typing import Any

# Catalog of virtual smart appliances with predefined characteristics
SMART_DEVICE_CATALOG = {
    "smart_thermostat": {
        "name": "Smart Thermostat",
        "category": "HVAC",
        "base_power_watts": 5.0,
        "peak_power_watts": 15.0,
        "typical_daily_hours": 24.0,
        "description": "Learns your schedule to optimize heating and cooling.",
    },
    "smart_plug_monitor": {
        "name": "Smart Plug with Energy Monitor",
        "category": "General",
        "base_power_watts": 1.0,
        "peak_power_watts": 1800.0,  # Pass-through max
        "typical_daily_hours": 12.0,
        "description": "Monitors and controls power to any plugged-in appliance.",
    },
    "smart_led_bulb": {
        "name": "Smart LED Light Bulb",
        "category": "Lighting",
        "base_power_watts": 0.5,
        "peak_power_watts": 9.0,
        "typical_daily_hours": 6.0,
        "description": "Dimmable, color-changing LED with scheduling.",
    },
    "smart_washer": {
        "name": "Smart Washing Machine",
        "category": "Appliance",
        "base_power_watts": 2.0,
        "peak_power_watts": 500.0,
        "typical_daily_hours": 1.0,
        "description": "High-efficiency washer with remote start and cycle monitoring.",
    },
    "ev_charger_level2": {
        "name": "Level 2 EV Charger",
        "category": "Transport",
        "base_power_watts": 5.0,
        "peak_power_watts": 7400.0,
        "typical_daily_hours": 4.0,
        "description": "Smart home electric vehicle charging station.",
    },
}


def get_all_devices() -> list[dict[str, Any]]:
    """Returns a list of all available smart devices for UI selection."""
    devices = []
    for key, info in SMART_DEVICE_CATALOG.items():
        devices.append({"id": key, **info})
    return devices


def get_device_by_id(device_id: str) -> dict[str, Any]:
    """Retrieves a specific device's specifications by its ID."""
    if device_id in SMART_DEVICE_CATALOG:
        return {"id": device_id, **SMART_DEVICE_CATALOG[device_id]}
    raise ValueError(f"Device ID '{device_id}' not found in catalog.")
