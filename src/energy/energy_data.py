"""Mock data generator and calculations for the Energy Monitoring Dashboard."""

import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict
from src.energy.energy_types import (
    EnergyReading, Appliance, EnergyDevice, EnergyAlert, EnergyGoal,
    EnergyBill, EnergyInsight, EnergyStats,
    EnergySource, ApplianceCategory, AlertType, EnergyGoalType,
    GRID_EMISSION_FACTOR, SOLAR_EMISSION_FACTOR, APPLIANCE_ICONS,
)


def generate_id(prefix: str, seed: int = None) -> str:
    """Generate a deterministic ID."""
    if seed is not None:
        h = hashlib.md5(f"{prefix}_{seed}".encode()).hexdigest()[:8]
    else:
        h = hashlib.md5(f"{prefix}_{random.random()}".encode()).hexdigest()[:8]
    return f"{prefix}_{h}"


def calculate_energy_cost(kwh: float, source: EnergySource) -> float:
    """Calculate energy cost based on source."""
    rates = {
        EnergySource.SOLAR: 0.03, EnergySource.WIND: 0.04,
        EnergySource.GRID: 0.12, EnergySource.BATTERY: 0.08,
        EnergySource.GAS: 0.10, EnergySource.OIL: 0.15, EnergySource.HYDRO: 0.05,
    }
    return round(kwh * rates.get(source, 0.12), 4)


def calculate_carbon(kwh: float, source: EnergySource) -> float:
    """Calculate carbon emission from energy consumption."""
    factors = {
        EnergySource.SOLAR: SOLAR_EMISSION_FACTOR, EnergySource.WIND: 0.01,
        EnergySource.GRID: GRID_EMISSION_FACTOR, EnergySource.BATTERY: 0.05,
        EnergySource.GAS: 0.18, EnergySource.OIL: 0.27, EnergySource.HYDRO: 0.01,
    }
    return round(kwh * factors.get(source, GRID_EMISSION_FACTOR), 4)


def generate_mock_appliances() -> List[Appliance]:
    """Generate mock household appliances."""
    appliances_data = [
        ("Central AC", ApplianceCategory.COOLING, 3500, 12.0, 43.2, "B", 8.0),
        ("Electric Heater", ApplianceCategory.HEATING, 2000, 8.0, 28.8, "C", 6.0),
        ("LED Lights (All)", ApplianceCategory.LIGHTING, 150, 1.2, 4.3, "A++", 10.0),
        ("Refrigerator", ApplianceCategory.KITCHEN, 150, 3.6, 13.0, "A+", 24.0),
        ("Washing Machine", ApplianceCategory.LAUNDRY, 2000, 1.5, 5.4, "A", 1.0),
        ("Dryer", ApplianceCategory.LAUNDRY, 3000, 2.0, 7.2, "B", 1.0),
        ("Dishwasher", ApplianceCategory.KITCHEN, 1800, 1.2, 4.3, "A", 1.0),
        ("TV + Sound System", ApplianceCategory.ENTERTAINMENT, 300, 2.0, 7.2, "A", 6.0),
        ("Desktop Computer", ApplianceCategory.OFFICE, 400, 2.4, 8.6, "B", 8.0),
        ("Water Heater", ApplianceCategory.WATER_HEATER, 4500, 6.0, 21.6, "B", 3.0),
        ("Oven", ApplianceCategory.KITCHEN, 2500, 1.5, 5.4, "A", 1.5),
        ("Microwave", ApplianceCategory.KITCHEN, 1000, 0.3, 1.1, "A", 0.5),
        ("Router + Modem", ApplianceCategory.OFFICE, 30, 0.72, 2.6, "A++", 24.0),
        ("Ceiling Fan", ApplianceCategory.COOLING, 75, 0.5, 1.8, "A++", 12.0),
        ("Iron", ApplianceCategory.LAUNDRY, 1200, 0.4, 1.4, "B", 0.5),
    ]

    appliances = []
    for i, (name, cat, power, daily_kwh, monthly_cost, eff, hours) in enumerate(appliances_data):
        appliances.append(Appliance(
            appliance_id=generate_id("app", i),
            name=name,
            category=cat,
            rated_power_watts=power,
            avg_daily_kwh=daily_kwh,
            monthly_cost_usd=round(monthly_cost, 2),
            efficiency_rating=eff,
            is_active=random.random() > 0.1,
            last_used=(datetime.now() - timedelta(hours=random.randint(0, 48))).strftime("%Y-%m-%d %H:%M"),
            usage_hours_daily=hours,
        ))

    return appliances


def generate_mock_devices() -> List[EnergyDevice]:
    """Generate mock smart energy devices."""
    return [
        EnergyDevice("d1", "Main Meter", "Utility Room", True, 2450, 18.5, "v2.1.4", datetime.now().strftime("%Y-%m-%d %H:%M")),
        EnergyDevice("d2", "Solar Inverter", "Rooftop", True, 3200, 12.8, "v3.0.2", datetime.now().strftime("%Y-%m-%d %H:%M")),
        EnergyDevice("d3", "EV Charger", "Garage", True, 7400, 0.0, "v1.5.0", datetime.now().strftime("%Y-%m-%d %H:%M")),
        EnergyDevice("d4", "Battery Pack", "Utility Room", True, 0, 5.2, "v2.3.1", datetime.now().strftime("%Y-%m-%d %H:%M")),
        EnergyDevice("d5", "Smart Thermostat", "Living Room", True, 0, 0.0, "v4.1.0", datetime.now().strftime("%Y-%m-%d %H:%M")),
        EnergyDevice("d6", "Heat Pump", "Exterior", False, 0, 0.0, "v1.2.3", (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")),
    ]


def generate_mock_alerts() -> List[EnergyAlert]:
    """Generate mock energy alerts."""
    alerts_data = [
        (AlertType.HIGH_CONSUMPTION, "High Consumption Detected", "AC unit consuming 40% more than usual. Check thermostat settings.", "high", "Central AC", "Reduce thermostat by 2°C"),
        (AlertType.PEAK_DEMAND, "Peak Demand Warning", "Current demand exceeds 5kW threshold. Consider delaying high-power appliances.", "medium", "Main Meter", "Delay dryer and dishwasher"),
        (AlertType.ANOMALY, "Nighttime Anomaly", "Unusual 3.2kWh consumption detected between 2-4 AM.", "high", "Unknown", "Check for phantom loads"),
        (AlertType.SAVINGS_OPPORTUNITY, "Solar Export Opportunity", "Grid price is high. Consider using battery instead of exporting solar.", "low", "Solar Inverter", "Switch to battery mode"),
        (AlertType.DEVICE_OFFLINE, "Device Offline", "Heat Pump has been offline for 48 hours.", "medium", "Heat Pump", "Check device connection"),
        (AlertType.BATTERY_LOW, "Battery Low", "Home battery at 15% charge. Grid power will be used.", "low", "Battery Pack", "Schedule charging during off-peak"),
    ]

    return [
        EnergyAlert(
            alert_id=generate_id("alert", i),
            alert_type=at, title=t, message=m, severity=s,
            timestamp=(datetime.now() - timedelta(hours=random.randint(1, 48))).strftime("%Y-%m-%d %H:%M"),
            is_read=random.random() > 0.5,
            device_name=d, recommended_action=a,
        )
        for i, (at, t, m, s, d, a) in enumerate(alerts_data)
    ]


def generate_mock_goals() -> List[EnergyGoal]:
    """Generate mock energy goals."""
    goals_data = [
        (EnergyGoalType.REDUCE_CONSUMPTION, "Reduce Monthly Usage", 350, 312, "kWh", "2026-12-31"),
        (EnergyGoalType.INCREASE_SUSTAINABLE, "50% Renewable Energy", 50, 38, "%", "2026-12-31"),
        (EnergyGoalType.REDUCE_COST, "Cut Energy Bill", 100, 82, "% of original", "2026-10-31"),
        (EnergyGoalType.NET_ZERO, "Net Zero Month", 1, 0, "months", "2026-12-31"),
    ]

    return [
        EnergyGoal(
            goal_id=generate_id("goal", i),
            goal_type=gt, title=t, target_value=tv, current_value=cv,
            unit=u, deadline=dl,
            created_at=(datetime.now() - timedelta(days=random.randint(30, 90))).strftime("%Y-%m-%d"),
            is_completed=cv >= tv,
        )
        for i, (gt, t, tv, cv, u, dl) in enumerate(goals_data)
    ]


def generate_mock_bills() -> List[EnergyBill]:
    """Generate mock monthly energy bills."""
    bills = []
    for m in range(6):
        date = datetime.now() - timedelta(days=30 * (5 - m))
        total = round(random.uniform(280, 420), 1)
        peak = round(total * random.uniform(0.5, 0.7), 1)
        off_peak = round(total - peak, 1)
        renewable = round(total * random.uniform(0.25, 0.45), 1)

        bills.append(EnergyBill(
            bill_id=generate_id("bill", m),
            month=date.strftime("%Y-%m"),
            total_kwh=total,
            total_cost_usd=round(total * 0.12, 2),
            peak_kwh=peak,
            off_peak_kwh=off_peak,
            renewable_kwh=renewable,
            carbon_kg=round(total * GRID_EMISSION_FACTOR, 1),
            days=30,
            avg_daily_kwh=round(total / 30, 1),
        ))

    return bills


def generate_mock_insights() -> List[EnergyInsight]:
    """Generate AI energy insights."""
    return [
        EnergyInsight("i1", "Optimize AC Schedule", "Your AC runs 2 hours longer than needed during off-peak hours. Setting a schedule could save significant energy.", "scheduling", 45.0, 5.40, 21.4, 0.92, ["Set AC timer to turn off at 11 PM", "Use programmable thermostat"]),
        EnergyInsight("i2", "Replace Old Fridge", "Your refrigerator uses 40% more energy than modern A++ models. Upgrading could pay for itself in 3 years.", "upgrade", 1200.0, 144.0, 570.0, 0.85, ["Consider A++ rated refrigerator", "Check rebate programs"]),
        EnergyInsight("i3", "Maximize Solar Usage", "You're exporting 60% of solar production. Using more during peak hours saves grid costs.", "optimization", 80.0, 9.60, 38.0, 0.88, ["Run laundry during solar peak", "Charge EV at midday"]),
        EnergyInsight("i4", "Phantom Load Detection", "Standby devices consume 2.1kWh daily. Smart plugs could eliminate this waste.", "efficiency", 63.0, 7.56, 29.9, 0.78, ["Install smart plugs", "Use power strips with switches"]),
    ]


def generate_mock_readings(count: int = 48) -> List[EnergyReading]:
    """Generate mock hourly energy readings."""
    readings = []
    sources = list(EnergySource)
    categories = list(ApplianceCategory)

    for i in range(count):
        hours_ago = count - i
        ts = datetime.now() - timedelta(hours=hours_ago)
        hour = ts.hour
        source = random.choice(sources)
        category = random.choice(categories)

        base = 2.0 + (1.5 if 8 <= hour <= 20 else 0.5)
        kwh = round(base * random.uniform(0.5, 1.5), 3)

        readings.append(EnergyReading(
            reading_id=generate_id("read", i),
            timestamp=ts.strftime("%Y-%m-%d %H:%M"),
            consumption_kwh=kwh,
            source=source,
            cost_usd=calculate_energy_cost(kwh, source),
            carbon_kg=calculate_carbon(kwh, source),
            appliance_category=category,
            device_name=f"Device_{category.value}",
            is_peak=8 <= hour <= 20,
        ))

    return readings


def generate_mock_stats(bills: List[EnergyBill], appliances: List[Appliance], alerts: List[EnergyAlert]) -> EnergyStats:
    """Generate aggregate energy statistics."""
    latest = bills[-1] if bills else None
    prev = bills[-2] if len(bills) >= 2 else None

    total_kwh = latest.total_kwh if latest else 350
    total_cost = latest.total_cost_usd if latest else 42.0
    total_carbon = latest.carbon_kg if latest else 166.0
    avg_daily = latest.avg_daily_kwh if latest else 11.7
    renewable_pct = latest.renewable_percent if latest else 35.0
    cost_per_kwh = total_cost / total_kwh if total_kwh > 0 else 0.12

    change = 0
    if prev and prev.total_kwh > 0:
        change = ((total_kwh - prev.total_kwh) / prev.total_kwh) * 100

    cat_breakdown = {}
    for a in appliances:
        cat = a.category.value
        cat_breakdown[cat] = cat_breakdown.get(cat, 0) + a.avg_daily_kwh

    source_breakdown = {"solar": 35, "grid": 45, "battery": 12, "wind": 8}

    hourly = [{"hour": h, "kwh": round(random.uniform(0.5, 4.0) + (2.0 if 8 <= h <= 20 else 0), 2)} for h in range(24)]

    monthly = []
    for b in bills:
        monthly.append({"period": b.month, "kwh": b.total_kwh, "cost": b.total_cost_usd, "carbon": b.carbon_kg, "renewable": b.renewable_kwh})

    return EnergyStats(
        total_kwh_month=total_kwh,
        total_cost_month=total_cost,
        total_carbon_month=total_carbon,
        avg_daily_kwh=avg_daily,
        peak_kwh_today=round(avg_daily * 1.3, 1),
        renewable_percent=round(renewable_pct, 1),
        cost_per_kwh=round(cost_per_kwh, 4),
        comparison_last_month_percent=round(change, 1),
        total_devices=len(appliances),
        active_devices=sum(1 for a in appliances if a.is_active),
        alerts_count=sum(1 for a in alerts if not a.is_read),
        savings_this_month_usd=round(random.uniform(8, 35), 2),
        monthly_trend=monthly,
        category_breakdown=cat_breakdown,
        source_breakdown=source_breakdown,
        hourly_pattern=hourly,
    )
