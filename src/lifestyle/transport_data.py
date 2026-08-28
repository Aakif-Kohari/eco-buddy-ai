"""Mock data generator and calculations for the Green Transportation Planner."""

import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from src.lifestyle.transport_types import (
    TransportMode, Route, TripPlan, TripLog, Vehicle, CommuteStats,
    TransportStats, EmissionComparison, TripCategory, VehicleType,
    EMISSION_FACTORS, AVG_SPEEDS, COST_PER_KM, CALORIES_PER_KM,
    MODE_ICONS, MODE_COLORS,
)


def generate_id(prefix: str, seed: int = None) -> str:
    """Generate a deterministic ID."""
    if seed is not None:
        h = hashlib.md5(f"{prefix}_{seed}".encode()).hexdigest()[:8]
    else:
        h = hashlib.md5(f"{prefix}_{random.random()}".encode()).hexdigest()[:8]
    return f"{prefix}_{h}"


def calculate_route(
    origin: str, destination: str,
    distance_km: float, mode: TransportMode
) -> Route:
    """Calculate route details for a given mode."""
    emission = distance_km * EMISSION_FACTORS.get(mode, 0.19)
    duration = (distance_km / AVG_SPEEDS.get(mode, 30)) * 60
    cost = distance_km * COST_PER_KM.get(mode, 0.25)
    calories = distance_km * CALORIES_PER_KM.get(mode, 3.0)

    steps = [
        {"instruction": f"Head towards {destination}", "detail": f"Travel {distance_km:.1f} km by {mode.value}"},
        {"instruction": "Follow the recommended path", "detail": f"Estimated {duration:.0f} minutes"},
        {"instruction": f"Arrive at {destination}", "detail": f"Emit {emission:.2f} kg CO₂"},
    ]

    return Route(
        route_id=generate_id("route"),
        origin=origin,
        destination=destination,
        distance_km=round(distance_km, 2),
        duration_minutes=round(duration, 1),
        mode=mode,
        emission_kg=round(emission, 3),
        cost_usd=round(cost, 2),
        calories_burned=round(calories, 0),
        steps=steps,
        preference_score=round(random.uniform(0.6, 1.0), 2),
    )


def generate_route_options(
    origin: str, destination: str, distance_km: float
) -> List[Route]:
    """Generate route options for different transport modes."""
    modes = [TransportMode.WALKING, TransportMode.CYCLING, TransportMode.BUS,
             TransportMode.CAR, TransportMode.ELECTRIC_CAR, TransportMode.TRAIN]

    if distance_km > 3:
        modes = [m for m in modes if m != TransportMode.WALKING]
    if distance_km > 2:
        modes = [m for m in modes if m != TransportMode.WALKING]

    routes = []
    for mode in modes:
        route = calculate_route(origin, destination, distance_km, mode)
        routes.append(route)

    if routes:
        greenest = min(routes, key=lambda r: r.emission_kg)
        greenest.is_recommended = True

    return sorted(routes, key=lambda r: r.emission_kg)


def generate_mock_trip_logs(count: int = 40) -> List[TripLog]:
    """Generate mock trip log entries."""
    locations = [
        "Home", "Office", "University", "Shopping Mall", "Gym",
        "Park", "Restaurant", "Airport", "Hospital", "Library",
        "Coffee Shop", "Supermarket", "Beach", "Museum", "Station",
    ]
    modes = list(TransportMode)
    categories = list(TripCategory)

    logs = []
    for i in range(count):
        origin = random.choice(locations)
        dest = random.choice([l for l in locations if l != origin])
        mode = random.choice(modes)
        distance = round(random.uniform(0.5, 25.0), 1)
        duration = round((distance / AVG_SPEEDS.get(mode, 30)) * 60, 0)
        emission = round(distance * EMISSION_FACTORS.get(mode, 0.19), 3)
        cost = round(distance * COST_PER_KM.get(mode, 0.25), 2)
        days_ago = random.randint(0, 60)

        logs.append(TripLog(
            log_id=generate_id("log", i),
            user_id="user_001",
            origin=origin,
            destination=dest,
            distance_km=distance,
            mode=mode,
            duration_minutes=duration,
            emission_kg=emission,
            cost_usd=cost,
            date=(datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
            category=random.choice(categories),
            notes=random.choice(["", "Quick trip", "Rush hour", "Smooth ride", ""]),
        ))

    return sorted(logs, key=lambda l: l.date, reverse=True)


def generate_mock_vehicles() -> List[Vehicle]:
    """Generate mock personal vehicles."""
    return [
        Vehicle("v1", "My Car", VehicleType.GASOLINE, 12.0, 0.19, 2020, "Toyota", "Corolla", True),
        Vehicle("v2", "Work Van", VehicleType.DIESEL, 8.5, 0.22, 2018, "Ford", "Transit", False),
        Vehicle("v3", "Electric", VehicleType.ELECTRIC, 6.5, 0.053, 2023, "Tesla", "Model 3", False),
    ]


def generate_mock_commute_stats() -> CommuteStats:
    """Generate mock commute statistics."""
    return CommuteStats(
        avg_daily_distance_km=round(random.uniform(8, 20), 1),
        avg_daily_emission_kg=round(random.uniform(1.5, 5.0), 2),
        avg_daily_cost_usd=round(random.uniform(3, 12), 2),
        total_monthly_trips=random.randint(30, 60),
        most_used_mode=random.choice([TransportMode.CAR, TransportMode.BUS, TransportMode.TRAIN]),
        greenest_day="Wednesday",
        worst_day="Monday",
        monthly_savings_usd=round(random.uniform(20, 80), 2),
        monthly_co2_saved_kg=round(random.uniform(5, 25), 1),
    )


def generate_mock_transport_stats(logs: List[TripLog]) -> TransportStats:
    """Generate aggregate transport statistics."""
    total_dist = sum(l.distance_km for l in logs)
    total_emission = sum(l.emission_kg for l in logs)
    total_cost = sum(l.cost_usd for l in logs)
    total_calories = sum(l.distance_km * CALORIES_PER_KM.get(l.mode, 3.0) for l in logs)

    mode_counts = {}
    for l in logs:
        m = l.mode.value
        mode_counts[m] = mode_counts.get(m, 0) + 1

    most_used = max(mode_counts, key=mode_counts.get) if mode_counts else "car"
    greenest = TransportMode.WALKING

    car_emission = sum(l.distance_km * EMISSION_FACTORS[TransportMode.CAR] for l in logs)
    actual_emission = total_emission
    avoided = max(car_emission - actual_emission, 0)

    monthly = []
    for m in range(6):
        date = (datetime.now() - timedelta(days=30 * (5 - m))).strftime("%Y-%m")
        month_logs = [l for l in logs if l.date.startswith(date)]
        monthly.append({
            "period": date,
            "trips": len(month_logs),
            "distance": round(sum(l.distance_km for l in month_logs), 1),
            "emission": round(sum(l.emission_kg for l in month_logs), 2),
            "cost": round(sum(l.cost_usd for l in month_logs), 2),
        })

    return TransportStats(
        total_trips=len(logs),
        total_distance_km=round(total_dist, 1),
        total_emission_kg=round(total_emission, 2),
        total_cost_usd=round(total_cost, 2),
        total_calories=round(total_calories, 0),
        avg_emission_per_trip=round(total_emission / max(len(logs), 1), 3),
        greenest_mode=greenest,
        most_used_mode=TransportMode(most_used) if most_used in [m.value for m in TransportMode] else TransportMode.CAR,
        monthly_trend=monthly,
        mode_distribution=mode_counts,
        co2_avoided_kg=round(avoided, 2),
        trees_equivalent=int(avoided / 21.77),
    )


def generate_emission_comparison(distance_km: float) -> List[EmissionComparison]:
    """Generate emission comparison across all modes."""
    comparisons = []
    car_emission = distance_km * EMISSION_FACTORS[TransportMode.CAR]

    for mode in TransportMode:
        emission = distance_km * EMISSION_FACTORS.get(mode, 0.19)
        duration = (distance_km / AVG_SPEEDS.get(mode, 30)) * 60
        cost = distance_km * COST_PER_KM.get(mode, 0.25)
        calories = distance_km * CALORIES_PER_KM.get(mode, 3.0)
        savings = max(car_emission - emission, 0)

        comparisons.append(EmissionComparison(
            mode=mode,
            mode_name=mode.value.replace("_", " ").title(),
            emission_kg=round(emission, 3),
            time_minutes=round(duration, 1),
            cost_usd=round(cost, 2),
            calories=round(calories, 0),
            is_greenest=False,
            savings_vs_car_kg=round(savings, 3),
        ))

    if comparisons:
        greenest = min(comparisons, key=lambda c: c.emission_kg)
        greenest.is_greenest = True

    return sorted(comparisons, key=lambda c: c.emission_kg)
