"""Mock data generator and calculation utilities for eco impact dashboard."""

import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from eco_impact_types import (
    ImpactRecord, UserProfile, CommunityStats, ImpactTrend,
    ComparisonResult, EcoChallenge, GoalProgress,
    ImpactCategory, ComparisonPeriod, TrendDirection, BadgeLevel,
    EMISSION_FACTORS, WATER_FACTORS, WASTE_FACTORS, ECO_SCORE_WEIGHTS,
    BADGE_THRESHOLDS, REGIONAL_BENCHMARKS,
)


def generate_id(prefix: str, seed: int = None) -> str:
    """Generate a deterministic ID from prefix and optional seed."""
    if seed is not None:
        h = hashlib.md5(f"{prefix}_{seed}".encode()).hexdigest()[:8]
    else:
        h = hashlib.md5(f"{prefix}_{random.random()}".encode()).hexdigest()[:8]
    return f"{prefix}_{h}"


def calculate_carbon_footprint(
    transport: str, distance_km: float,
    electricity_kwh: float, diet: str,
    flights: int, region: str
) -> Dict[str, float]:
    """Calculate detailed carbon footprint breakdown."""
    transport_factor = EMISSION_FACTORS["transport"].get(transport, 0.19)
    daily_transport = transport_factor * distance_km
    annual_transport = daily_transport * 365

    energy_factor = EMISSION_FACTORS["energy"].get(region, 0.475)
    annual_energy = electricity_kwh * 12 * energy_factor

    diet_factor = EMISSION_FACTORS["diet"].get(diet, 2.0)
    annual_food = diet_factor * 365

    annual_flights = flights * 250.0

    total_annual = annual_transport + annual_energy + annual_food + annual_flights

    return {
        "transport_kg": round(annual_transport, 2),
        "energy_kg": round(annual_energy, 2),
        "food_kg": round(annual_food, 2),
        "flights_kg": round(annual_flights, 2),
        "total_kg": round(total_annual, 2),
        "transport_percent": round((annual_transport / total_annual) * 100, 1) if total_annual > 0 else 0,
        "energy_percent": round((annual_energy / total_annual) * 100, 1) if total_annual > 0 else 0,
        "food_percent": round((annual_food / total_annual) * 100, 1) if total_annual > 0 else 0,
        "flights_percent": round((annual_flights / total_annual) * 100, 1) if total_annual > 0 else 0,
    }


def calculate_water_footprint(
    shower_min: float, laundry_loads: float,
    dishwasher_runs: float, garden_min: float,
    diet: str
) -> Dict[str, float]:
    """Calculate detailed water footprint breakdown."""
    daily_shower = shower_min * WATER_FACTORS["shower_minutes_daily"]
    weekly_laundry = laundry_loads * WATER_FACTORS["laundry_loads_weekly"]
    weekly_dishwasher = dishwasher_runs * WATER_FACTORS["dishwasher_runs_weekly"]
    daily_garden = garden_min * WATER_FACTORS["garden_minutes_daily"]

    annual_direct = (daily_shower + daily_garden) * 365
    annual_laundry = weekly_laundry * 52
    annual_dishwasher = weekly_dishwasher * 52

    virtual_water = WATER_FACTORS["virtual_water_diet_kg"].get(diet, 2000) * 365
    total_annual = annual_direct + annual_laundry + annual_dishwasher + virtual_water

    return {
        "shower_liters": round(annual_direct, 1),
        "laundry_liters": round(annual_laundry, 1),
        "dishwasher_liters": round(annual_dishwasher, 1),
        "virtual_liters": round(virtual_water, 1),
        "total_liters": round(total_annual, 1),
    }


def calculate_eco_score(carbon_kg: float, water_l: float, energy_kwh: float) -> float:
    """Calculate composite eco score (0-100)."""
    benchmark = REGIONAL_BENCHMARKS.get("Global", REGIONAL_BENCHMARKS["Global"])

    carbon_score = max(0, 100 - (carbon_kg / benchmark["avg_carbon_kg_year"]) * 50)
    water_score = max(0, 100 - (water_l / (benchmark["avg_water_l_day"] * 365)) * 50)
    energy_score = max(0, 100 - (energy_kwh / benchmark["avg_energy_kwh_month"]) * 50)

    weighted = (
        carbon_score * ECO_SCORE_WEIGHTS[ImpactCategory.CARBON]
        + water_score * ECO_SCORE_WEIGHTS[ImpactCategory.WATER]
        + energy_score * ECO_SCORE_WEIGHTS[ImpactCategory.ENERGY]
        + 70 * ECO_SCORE_WEIGHTS[ImpactCategory.WASTE]
        + 80 * ECO_SCORE_WEIGHTS[ImpactCategory.TRANSPORT]
        + 75 * ECO_SCORE_WEIGHTS[ImpactCategory.FOOD]
    )

    return round(min(max(weighted, 0), 100), 1)


def get_badge_level(eco_score: float, carbon_saved: float) -> BadgeLevel:
    """Determine badge level based on eco score and carbon saved."""
    for level in reversed(list(BadgeLevel)):
        thresholds = BADGE_THRESHOLDS[level]
        if eco_score >= thresholds["eco_score"] and carbon_saved >= thresholds["carbon_saved"]:
            return level
    return BadgeLevel.BRONZE


def generate_mock_users(count: int = 20) -> List[UserProfile]:
    """Generate mock user profiles for comparison."""
    names = [
        ("alex_r", "Alex Rivera"), ("beatrix_v", "Beatrix Vance"),
        ("chloe_l", "Chloe Laurent"), ("daniel_k", "Daniel Kim"),
        ("elena_r", "Elena Rostova"), ("fujita_s", "Fujita Sato"),
        ("grace_w", "Grace Wang"), ("hassan_m", "Hassan Mohammed"),
        ("iris_c", "Iris Chen"), ("james_t", "James Thompson"),
        ("kira_n", "Kira Nakamura"), ("leo_p", "Leo Park"),
        ("maya_s", "Maya Singh"), ("noah_b", "Noah Brown"),
        ("olivia_j", "Olivia Jackson"), ("priya_d", "Priya Desai"),
        ("quinn_f", "Quinn Fischer"), ("rachel_m", "Rachel Miller"),
        ("samuel_o", "Samuel Okafor"), ("tara_g", "Tara Gupta"),
    ]
    regions = ["Global", "US", "UK", "EU", "India"]
    diets = ["Vegan", "Vegetarian", "Omnivore", "Heavy Meat"]
    transports = ["Car", "Public Transport", "Bike", "Walking", "Electric Car"]
    badge_levels = ["Bronze", "Silver", "Gold", "Platinum", "Diamond"]

    users = []
    for i, (username, display_name) in enumerate(names[:count]):
        eco_score = round(random.uniform(30, 95), 1)
        carbon_saved = round(random.uniform(5, 300), 1)
        water_saved = round(random.uniform(1000, 50000), 0)
        trees_eq = round(carbon_saved / 21.77, 1)

        users.append(UserProfile(
            user_id=generate_id("user", i),
            username=username,
            display_name=display_name,
            avatar_url=None,
            joined_date=(datetime.now() - timedelta(days=random.randint(30, 365))).strftime("%Y-%m-%d"),
            total_assessments=random.randint(3, 50),
            eco_score=eco_score,
            carbon_saved_kg=carbon_saved,
            water_saved_liters=water_saved,
            trees_equivalent=trees_eq,
            badges=[random.choice(badge_levels) for _ in range(random.randint(1, 4))],
            region=random.choice(regions),
            diet_type=random.choice(diets),
            primary_transport=random.choice(transports),
        ))

    return users


def generate_community_stats(users: List[UserProfile]) -> CommunityStats:
    """Generate aggregate community statistics from user list."""
    if not users:
        return CommunityStats(
            total_users=0, active_users_30d=0, avg_eco_score=0,
            total_carbon_saved_tons=0, total_water_saved_megaliters=0,
            total_trees_equivalent=0,
        )

    avg_score = sum(u.eco_score for u in users) / len(users)
    total_carbon = sum(u.carbon_saved_kg for u in users)
    total_water = sum(u.water_saved_liters for u in users)
    total_trees = sum(u.trees_equivalent for u in users)

    sorted_users = sorted(users, key=lambda u: u.eco_score, reverse=True)

    regional_avgs = {}
    for region in ["Global", "US", "UK", "EU", "India"]:
        region_users = [u for u in users if u.region == region]
        if region_users:
            regional_avgs[region] = round(
                sum(u.eco_score for u in region_users) / len(region_users), 1
            )

    return CommunityStats(
        total_users=len(users),
        active_users_30d=max(1, int(len(users) * 0.65)),
        avg_eco_score=round(avg_score, 1),
        total_carbon_saved_tons=round(total_carbon / 1000, 2),
        total_water_saved_megaliters=round(total_water / 1_000_000, 3),
        total_trees_equivalent=int(total_trees),
        top_performers=sorted_users[:5],
        regional_averages=regional_avgs,
    )


def generate_impact_trends(
    user_id: str, months: int = 6
) -> Dict[ImpactCategory, ImpactTrend]:
    """Generate mock impact trend data over time."""
    trends = {}
    for category in ImpactCategory:
        base_value = random.uniform(50, 200)
        direction = random.choice(list(TrendDirection))
        data_points = []

        for m in range(months):
            date = (datetime.now() - timedelta(days=30 * (months - m))).strftime("%Y-%m")
            if direction == TrendDirection.IMPROVING:
                value = base_value * (1 - 0.05 * m) + random.uniform(-5, 5)
            elif direction == TrendDirection.WORSENING:
                value = base_value * (1 + 0.05 * m) + random.uniform(-5, 5)
            else:
                value = base_value + random.uniform(-10, 10)
            data_points.append({"period": date, "value": round(max(value, 10), 2)})

        values = [d["value"] for d in data_points]
        change = ((values[-1] - values[0]) / values[0]) * 100 if values[0] != 0 else 0
        best_idx = values.index(min(values))
        worst_idx = values.index(max(values))

        trends[category] = ImpactTrend(
            category=category,
            period=ComparisonPeriod.MONTHLY,
            data_points=data_points,
            direction=direction,
            change_percent=round(change, 1),
            best_period=data_points[best_idx]["period"],
            worst_period=data_points[worst_idx]["period"],
        )

    return trends


def generate_comparison_results(
    user_id: str, users: List[UserProfile]
) -> List[ComparisonResult]:
    """Generate comparison results for user against community."""
    results = []
    categories = [
        (ImpactCategory.CARBON, "carbon_saved_kg"),
        (ImpactCategory.WATER, "water_saved_liters"),
    ]

    user = next((u for u in users if u.user_id == user_id), users[0])

    for category, attr in categories:
        user_val = getattr(user, attr)
        all_vals = sorted([getattr(u, attr) for u in users])
        avg_val = sum(all_vals) / len(all_vals) if all_vals else 0
        median_val = all_vals[len(all_vals) // 2] if all_vals else 0
        rank = sum(1 for v in all_vals if v > user_val) + 1
        percentile = ((len(all_vals) - rank) / len(all_vals)) * 100 if all_vals else 0

        results.append(ComparisonResult(
            user_id=user_id,
            category=category,
            user_value=round(user_val, 2),
            community_avg=round(avg_val, 2),
            community_median=round(median_val, 2),
            percentile=round(percentile, 1),
            rank=rank,
            total_participants=len(all_vals),
            is_above_average=user_val > avg_val,
            improvement_potential_kg=round(max(avg_val - user_val, 0), 2),
        ))

    return results


def generate_mock_challenges() -> List[EcoChallenge]:
    """Generate mock environmental challenges."""
    challenges_data = [
        ("Meatless Monday Marathon", "Go vegetarian every Monday for 4 weeks", ImpactCategory.FOOD, 28, 15.0, 850, 2000),
        ("Bike to Work Week", "Use cycling as primary transport for 7 days", ImpactCategory.TRANSPORT, 7, 25.0, 420, 1000),
        ("Zero Waste Challenge", "Produce zero landfill waste for 30 days", ImpactCategory.WASTE, 30, 40.0, 310, 500),
        ("Cold Shower Streak", "Take cold showers for 21 days straight", ImpactCategory.WATER, 21, 10.0, 1200, 3000),
        ("Energy Detox", "Reduce electricity usage by 30% for 14 days", ImpactCategory.ENERGY, 14, 30.0, 670, 1500),
        ("Carbon Neutral Week", "Achieve zero net carbon for 7 days", ImpactCategory.CARBON, 7, 50.0, 280, 800),
    ]

    challenges = []
    for i, (title, desc, cat, days, target, parts, max_p) in enumerate(challenges_data):
        start = datetime.now() - timedelta(days=random.randint(0, 14))
        challenges.append(EcoChallenge(
            challenge_id=generate_id("ch", i),
            title=title,
            description=desc,
            category=cat,
            duration_days=days,
            target_reduction_percent=target,
            participants=parts,
            max_participants=max_p,
            start_date=start.strftime("%Y-%m-%d"),
            end_date=(start + timedelta(days=days)).strftime("%Y-%m-%d"),
            is_active=True,
            reward_badge=f"{cat.value.title()} Champion",
        ))

    return challenges


def generate_mock_goals(user_id: str) -> List[GoalProgress]:
    """Generate mock goal progress for a user."""
    goals_data = [
        ("Reduce Carbon by 20%", ImpactCategory.CARBON, 200, 156, "kg", "2026-12-31"),
        ("Save 10,000 Liters Water", ImpactCategory.WATER, 10000, 6800, "liters", "2026-11-30"),
        ("30 Days of Cycling", ImpactCategory.TRANSPORT, 30, 18, "days", "2026-10-15"),
        ("Zero Food Waste Month", ImpactCategory.WASTE, 30, 22, "days", "2026-09-30"),
        ("Halve Energy Usage", ImpactCategory.ENERGY, 50, 35, "%", "2026-12-31"),
    ]

    goals = []
    for i, (title, cat, target, current, unit, deadline) in enumerate(goals_data):
        goals.append(GoalProgress(
            goal_id=generate_id("goal", i),
            user_id=user_id,
            title=title,
            category=cat,
            target_value=float(target),
            current_value=float(current),
            unit=unit,
            deadline=deadline,
            created_at=(datetime.now() - timedelta(days=random.randint(10, 60))).strftime("%Y-%m-%d"),
            is_completed=current >= target,
        ))

    return goals


def generate_monthly_comparison_data(months: int = 6) -> List[Dict]:
    """Generate monthly comparison data for charts."""
    data = []
    for m in range(months):
        date = (datetime.now() - timedelta(days=30 * (months - m - 1))).strftime("%Y-%m")
        user_carbon = round(random.uniform(80, 200), 1)
        community_avg = round(random.uniform(120, 180), 1)
        data.append({
            "period": date,
            "user_carbon": user_carbon,
            "community_avg": community_avg,
            "user_water": round(random.uniform(3000, 8000), 0),
            "community_water_avg": round(random.uniform(4000, 7000), 0),
        })
    return data
