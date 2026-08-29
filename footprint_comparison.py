"""Carbon Footprint Comparison & Peer Benchmarking Engine.

Provides rich comparison analytics that let users benchmark their personal
carbon footprint against national averages, IPCC targets, lifestyle archetypes,
and community peer groups.  Includes percentile ranking, category deep-dives,
reduction pathway projections, and a green readiness score.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


# ──────────────────────────────────────────────────────────────────────────────
# Constants & Benchmark Data
# ──────────────────────────────────────────────────────────────────────────────

# Per-capita annual CO2 (tonnes) by country/region
COUNTRY_AVERAGES: dict[str, dict[str, Any]] = {
    "USA":        {"total_tonnes": 14.7, "transport": 4.5, "electricity": 3.8, "diet": 2.5, "flights": 3.9},
    "Australia":  {"total_tonnes": 15.0, "transport": 4.0, "electricity": 4.2, "diet": 2.3, "flights": 4.5},
    "Canada":     {"total_tonnes": 14.2, "transport": 4.3, "electricity": 3.5, "diet": 2.2, "flights": 4.2},
    "Germany":    {"total_tonnes": 8.1,  "transport": 2.4, "electricity": 2.1, "diet": 1.8, "flights": 1.8},
    "UK":         {"total_tonnes": 5.5,  "transport": 1.8, "electricity": 1.4, "diet": 1.5, "flights": 0.8},
    "Japan":      {"total_tonnes": 8.5,  "transport": 1.9, "electricity": 3.0, "diet": 1.6, "flights": 2.0},
    "India":      {"total_tonnes": 1.8,  "transport": 0.5, "electricity": 0.7, "diet": 0.5, "flights": 0.1},
    "China":      {"total_tonnes": 7.4,  "transport": 1.5, "electricity": 3.2, "diet": 1.2, "flights": 1.5},
    "Brazil":     {"total_tonnes": 2.0,  "transport": 0.7, "electricity": 0.6, "diet": 0.6, "flights": 0.1},
    "EU":         {"total_tonnes": 6.4,  "transport": 2.0, "electricity": 1.7, "diet": 1.6, "flights": 1.1},
    "Global":     {"total_tonnes": 4.7,  "transport": 1.4, "electricity": 1.3, "diet": 1.0, "flights": 1.0},
}

# IPCC-aligned reduction targets (kg CO2 per year)
IPCC_TARGETS: dict[str, dict[str, Any]] = {
    "2030": {
        "description": "IPCC 2030 43% reduction target",
        "target_kg": 2700.0,
        "from_baseline_kg": 4700.0,
        "source": "IPCC AR6 WG3, Chapter 3",
    },
    "2050_net_zero": {
        "description": "IPCC 2050 Net-Zero target",
        "target_kg": 400.0,
        "from_baseline_kg": 4700.0,
        "source": "IPCC AR6 WG3, Chapter 3",
    },
    "15C_pathway": {
        "description": "Well-below 2°C pathway (2030)",
        "target_kg": 3200.0,
        "from_baseline_kg": 4700.0,
        "source": "IPCC AR6 WG3, Chapter 3",
    },
}

# Lifestyle archetype definitions
LIFESTYLE_ARCHETYPES: dict[str, dict[str, Any]] = {
    "Minimalist Vegan": {
        "description": "Walks/bikes everywhere, fully plant-based, no flights, renewable energy",
        "typical_kg": 800.0,
        "categories": {"transport": 100.0, "electricity": 200.0, "diet": 150.0, "flights": 0.0},
        "avatar": "🌿",
    },
    "Eco-Conscious Urbanite": {
        "description": "Public transit, vegetarian, occasional flights, moderate energy use",
        "typical_kg": 2200.0,
        "categories": {"transport": 500.0, "electricity": 600.0, "diet": 300.0, "flights": 800.0},
        "avatar": "🏙️",
    },
    "Average Suburban": {
        "description": "Car commuter, standard diet, annual vacation flights",
        "typical_kg": 5000.0,
        "categories": {"transport": 1600.0, "electricity": 1200.0, "diet": 900.0, "flights": 1300.0},
        "avatar": "🏘️",
    },
    "Heavy Consumer": {
        "description": "Multiple vehicles, high energy use, frequent flyers, meat-heavy diet",
        "typical_kg": 9500.0,
        "categories": {"transport": 3000.0, "electricity": 2500.0, "diet": 1500.0, "flights": 2500.0},
        "avatar": "🚗",
    },
    "Off-Grid Homesteader": {
        "description": "Solar powered, garden-grown food, minimal transport, self-sufficient",
        "typical_kg": 1200.0,
        "categories": {"transport": 200.0, "electricity": 500.0, "diet": 400.0, "flights": 100.0},
        "avatar": "🏡",
    },
    "Digital Nomad": {
        "description": "Frequent flights, co-working spaces, varied diet, moderate energy",
        "typical_kg": 6500.0,
        "categories": {"transport": 800.0, "electricity": 1000.0, "diet": 700.0, "flights": 4000.0},
        "avatar": "💻",
    },
}

# Category names and their typical weight in eco-score
CATEGORY_META: dict[str, dict[str, Any]] = {
    "transport":    {"label": "🚗 Transport", "color": "#3b82f6", "icon": "🚗"},
    "electricity":  {"label": "⚡ Electricity", "color": "#f59e0b", "icon": "⚡"},
    "diet":         {"label": "🥗 Diet", "color": "#10b981", "icon": "🥗"},
    "flights":      {"label": "✈️ Flights", "color": "#ef4444", "icon": "✈️"},
}

# Green readiness score tiers
READINESS_TIERS: list[tuple[int, str, str, str]] = [
    (90, "🌱 Climate Leader",   "#22c55e", "You are leading the way in sustainability!"),
    (70, "🌿 Green Advocate",   "#84cc16", "Strong sustainability habits — keep pushing!"),
    (50, "🍃 Eco Explorer",     "#eab308", "Good progress; high-impact changes still possible."),
    (30, "🍂 Carbon Consumer",  "#f97316", "Significant room for improvement in key areas."),
    (0,  "🔴 High Impact",     "#ef4444", "Action needed — consider the top recommendations below."),
]


# ──────────────────────────────────────────────────────────────────────────────
# Data Classes
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class CategoryComparison:
    """Comparison result for a single emission category."""
    name: str
    user_kg: float
    benchmark_kg: float
    difference_kg: float
    percent_of_benchmark: float
    rating: str  # "excellent", "good", "average", "poor", "critical"

@dataclass
class PercentileResult:
    """Percentile ranking of a user's footprint."""
    percentile: float
    rank_label: str
    better_than_pct: float
    worse_than_pct: float
    context: str

@dataclass
class ArchetypeMatch:
    """Result of matching a user against lifestyle archetypes."""
    archetype_name: str
    avatar: str
    description: str
    similarity_score: float  # 0-1, higher is more similar
    typical_kg: float
    user_kg: float

@dataclass
class ReductionTarget:
    """A specific reduction target the user can aim for."""
    name: str
    description: str
    target_kg: float
    current_kg: float
    gap_kg: float
    reduction_needed_pct: float
    feasible: bool
    source: str

@dataclass
class ReadinessScore:
    """Green readiness evaluation."""
    score: int
    tier_name: str
    tier_color: str
    description: str
    breakdown: dict[str, float]
    recommendations: list[str]

@dataclass
class ComparisonReport:
    """Full comparison report for a user's footprint."""
    user_footprint_kg: float
    user_eco_score: int
    category_comparisons: list[CategoryComparison]
    country_percentile: PercentileResult
    archetype_matches: list[ArchetypeMatch]
    reduction_targets: list[ReductionTarget]
    readiness: ReadinessScore
    peer_group_avg_kg: float
    potential_savings_kg: float
    generated_at: str


# ──────────────────────────────────────────────────────────────────────────────
# Core Comparison Functions
# ──────────────────────────────────────────────────────────────────────────────

def compare_categories(
    user_contributors: dict[str, float],
    benchmark_contributors: dict[str, float],
) -> list[CategoryComparison]:
    """Compare user's per-category emissions against a benchmark.

    Args:
        user_contributors: e.g. {"transport": 1200, "electricity": 800, ...} in kg
        benchmark_contributors: same structure for benchmark

    Returns:
        List of CategoryComparison objects
    """
    comparisons = []
    for cat_key, meta in CATEGORY_META.items():
        user_val = user_contributors.get(cat_key, 0.0)
        bench_val = benchmark_contributors.get(cat_key, 0.0)

        diff = user_val - bench_val
        pct_of = (user_val / bench_val * 100) if bench_val > 0 else 0.0

        # Rating based on relative performance
        if pct_of <= 30:
            rating = "excellent"
        elif pct_of <= 60:
            rating = "good"
        elif pct_of <= 100:
            rating = "average"
        elif pct_of <= 150:
            rating = "poor"
        else:
            rating = "critical"

        comparisons.append(CategoryComparison(
            name=meta["label"],
            user_kg=round(user_val, 2),
            benchmark_kg=round(bench_val, 2),
            difference_kg=round(diff, 2),
            percent_of_benchmark=round(pct_of, 1),
            rating=rating,
        ))

    return comparisons


def compute_percentile(user_kg: float, population_mean_kg: float = 4700.0,
                       population_std_kg: float = 2500.0) -> PercentileResult:
    """Compute a user's percentile rank assuming a log-normal distribution.

    Most countries' per-capita emissions follow a roughly log-normal
    distribution.  We approximate the CDF using the normal CDF on
    log-transformed values.
    """
    if user_kg <= 0:
        user_kg = 0.01

    log_user = math.log(user_kg)
    log_mean = math.log(population_mean_kg)
    log_std = max(math.log(1 + population_std_kg / population_mean_kg), 0.01)

    z = (log_user - log_mean) / log_std
    # Approximation of the standard normal CDF
    percentile = _normal_cdf(z) * 100

    # Invert: lower emissions = higher (better) percentile
    better_pct = 100 - percentile
    worse_pct = percentile

    if better_pct >= 90:
        label = "Top 10% Globally"
        context = "Exceptionally low emissions — among the most sustainable."
    elif better_pct >= 75:
        label = "Top 25% Globally"
        context = "Below average — solid sustainability performance."
    elif better_pct >= 50:
        label = "Above Average"
        context = "Slightly below the global mean — room to improve."
    elif better_pct >= 25:
        label = "Below Average"
        context = "Above the global mean — consider targeted reductions."
    else:
        label = "Bottom Quartile"
        context = "Significantly above average — high reduction priority."

    return PercentileResult(
        percentile=round(better_pct, 1),
        rank_label=label,
        better_than_pct=round(better_pct, 1),
        worse_than_pct=round(worse_pct, 1),
        context=context,
    )


def _normal_cdf(z: float) -> float:
    """Approximation of the standard normal CDF using the error function."""
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def match_archetypes(
    user_contributors: dict[str, float],
    user_total_kg: float,
) -> list[ArchetypeMatch]:
    """Match a user's footprint profile against known lifestyle archetypes.

    Returns a list sorted by similarity (most similar first).
    """
    matches: list[ArchetypeMatch] = []
    cats = ["transport", "electricity", "diet", "flights"]

    for name, archetype in LIFESTYLE_ARCHETYPES.items():
        # Compute weighted distance (Euclidean in category space)
        dist = 0.0
        for cat in cats:
            u_val = user_contributors.get(cat, 0.0)
            a_val = archetype["categories"].get(cat, 0.0)
            # Normalize by archetype value to handle scale differences
            norm = max(a_val, 1.0)
            dist += ((u_val - a_val) / norm) ** 2

        # Also factor in total footprint difference
        total_dist = abs(user_total_kg - archetype["typical_kg"]) / max(archetype["typical_kg"], 1.0)
        combined_dist = math.sqrt(dist / len(cats) + (total_dist ** 2) * 0.3)

        # Convert distance to similarity (0-1 scale, 1 = identical)
        similarity = max(0.0, 1.0 / (1.0 + combined_dist))

        matches.append(ArchetypeMatch(
            archetype_name=name,
            avatar=archetype["avatar"],
            description=archetype["description"],
            similarity_score=round(similarity, 4),
            typical_kg=archetype["typical_kg"],
            user_kg=round(user_total_kg, 2),
        ))

    matches.sort(key=lambda m: m.similarity_score, reverse=True)
    return matches


def compute_reduction_targets(
    user_total_kg: float,
    user_contributors: dict[str, float],
) -> list[ReductionTarget]:
    """Compute actionable reduction targets aligned with IPCC pathways."""
    targets: list[ReductionTarget] = []

    for pathway_name, pathway in IPCC_TARGETS.items():
        target_kg = pathway["target_kg"]
        gap = max(0.0, user_total_kg - target_kg)
        reduction_pct = (gap / user_total_kg * 100) if user_total_kg > 0 else 0.0
        feasible = user_total_kg > target_kg * 1.1  # Must be at least 10% above target

        targets.append(ReductionTarget(
            name=pathway_name,
            description=pathway["description"],
            target_kg=target_kg,
            current_kg=round(user_total_kg, 2),
            gap_kg=round(gap, 2),
            reduction_needed_pct=round(reduction_pct, 1),
            feasible=feasible,
            source=pathway["source"],
        ))

    # Sort by gap (most actionable first)
    targets.sort(key=lambda t: t.gap_kg)
    return targets


def compute_readiness_score(
    user_total_kg: float,
    user_contributors: dict[str, float],
) -> ReadinessScore:
    """Compute a green readiness score (0-100) with breakdown and recommendations.

    The score is derived from:
      - Overall footprint vs global average (40 points)
      - Category-level performance (40 points, 10 each)
      - Diet sustainability (20 points)
    """
    breakdown: dict[str, float] = {}
    recommendations: list[str] = []

    # 1. Overall footprint component (0-40)
    global_avg = COUNTRY_AVERAGES["Global"]["total_tonnes"] * 1000  # convert to kg
    if user_total_kg <= 0:
        overall_score = 40.0
    else:
        ratio = global_avg / max(user_total_kg, 1.0)
        overall_score = min(40.0, max(0.0, ratio * 20))
    breakdown["overall"] = round(overall_score, 1)

    # 2. Category scores (0-10 each = 0-40 total)
    cat_benchmarks = COUNTRY_AVERAGES["EU"]  # Use EU as aspirational benchmark
    for cat_key, meta in CATEGORY_META.items():
        user_val = user_contributors.get(cat_key, 0.0)
        bench_val = cat_benchmarks.get(cat_key, 1.0) * 1000  # convert to kg
        if bench_val <= 0:
            bench_val = 1.0

        cat_ratio = bench_val / max(user_val, 1.0)
        cat_score = min(10.0, max(0.0, cat_ratio * 5))
        breakdown[cat_key] = round(cat_score, 1)

        # Generate recommendations for poor performers
        if user_val > bench_val * 1.5:
            if cat_key == "transport":
                recommendations.append(
                    f"🚗 Your transport emissions ({user_val:.0f} kg) exceed the EU average "
                    f"({bench_val:.0f} kg). Consider public transit, cycling, or an EV."
                )
            elif cat_key == "electricity":
                recommendations.append(
                    f"⚡ Your electricity emissions ({user_val:.0f} kg) are high. "
                    "Switch to renewable energy or improve home insulation."
                )
            elif cat_key == "diet":
                recommendations.append(
                    f"🥗 Your diet emissions ({user_val:.0f} kg) are above average. "
                    "Reducing meat consumption can significantly lower this."
                )
            elif cat_key == "flights":
                recommendations.append(
                    f"✈️ Flight emissions ({user_val:.0f} kg) are your largest category. "
                    "Consider train travel or carbon offsets for necessary flights."
                )

    # 3. Total score
    total_score = sum(breakdown.values())
    total_score = min(100, max(0, total_score))
    total_score_int = int(round(total_score))

    # Determine tier
    tier_name, tier_color, tier_desc = READINESS_TIERS[-1]
    for min_score, name, color, desc in READINESS_TIERS:
        if total_score_int >= min_score:
            tier_name = name
            tier_color = color
            tier_desc = desc
            break

    # Add general recommendations if few specific ones
    if len(recommendations) == 0 and total_score_int < 70:
        recommendations.append(
            "💡 Your overall footprint is near average. Small changes across "
            "multiple categories can compound into significant reductions."
        )
    if total_score_int >= 90:
        recommendations.append(
            "🌟 Outstanding! Consider mentoring others or advocating for "
            "policy changes to multiply your positive impact."
        )

    return ReadinessScore(
        score=total_score_int,
        tier_name=tier_name,
        tier_color=tier_color,
        description=tier_desc,
        breakdown=breakdown,
        recommendations=recommendations,
    )


def estimate_peer_group_average(user_id: Optional[int] = None) -> float:
    """Estimate peer group average from community assessment data.

    Falls back to global average if no database data is available.
    """
    try:
        from database import get_assessments
        assessments = get_assessments(user_id or 1)
        if not assessments:
            return COUNTRY_AVERAGES["Global"]["total_tonnes"] * 1000

        footprints = [a[8] for a in assessments if a[8] is not None and a[8] > 0]
        if not footprints:
            return COUNTRY_AVERAGES["Global"]["total_tonnes"] * 1000

        return sum(footprints) / len(footprints)
    except Exception:
        return COUNTRY_AVERAGES["Global"]["total_tonnes"] * 1000


def generate_category_deep_dive(
    user_contributors: dict[str, float],
) -> dict[str, dict[str, Any]]:
    """Generate a detailed deep-dive analysis for each emission category.

    Returns a dict keyed by category name, each containing benchmark
    comparisons, improvement potential, and actionable tips.
    """
    eu_bench = COUNTRY_AVERAGES["EU"]
    global_bench = COUNTRY_AVERAGES["Global"]
    deep_dive: dict[str, dict[str, Any]] = {}

    category_tips: dict[str, list[str]] = {
        "transport": [
            "Switch to public transport or cycling for daily commutes",
            "Consider an electric vehicle for your next car purchase",
            "Work from home when possible to eliminate commute emissions",
            "Combine errands to reduce total driving distance",
            "Join a carpool program with coworkers or neighbors",
        ],
        "electricity": [
            "Switch to a green energy tariff from your utility provider",
            "Install solar panels — payback is typically 5-8 years",
            "Replace old appliances with energy-efficient models (A+++ rated)",
            "Improve home insulation to reduce heating/cooling energy",
            "Use smart thermostats to optimize energy consumption",
        ],
        "diet": [
            "Reduce meat consumption — try Meatless Mondays",
            "Choose locally-sourced, seasonal produce",
            "Reduce food waste by planning meals and composting",
            "Try plant-based alternatives for dairy and protein",
            "Buy in bulk to reduce packaging and transportation emissions",
        ],
        "flights": [
            "Choose train travel for journeys under 800 km",
            "Fly economy class — business class has 3x the footprint",
            "Purchase high-quality carbon offsets for necessary flights",
            "Combine multiple trips to reduce total flights per year",
            "Consider video conferencing as an alternative to business travel",
        ],
    }

    for cat_key, meta in CATEGORY_META.items():
        user_val = user_contributors.get(cat_key, 0.0)
        eu_val = eu_bench.get(cat_key, 0) * 1000
        global_val = global_bench.get(cat_key, 0) * 1000

        improvement_potential = max(0.0, user_val - eu_val)
        if user_val > 0:
            improvement_pct = (improvement_potential / user_val) * 100
        else:
            improvement_pct = 0.0

        deep_dive[meta["label"]] = {
            "category_key": cat_key,
            "user_kg": round(user_val, 2),
            "eu_average_kg": round(eu_val, 2),
            "global_average_kg": round(global_val, 2),
            "vs_eu_difference_kg": round(user_val - eu_val, 2),
            "vs_global_difference_kg": round(user_val - global_val, 2),
            "improvement_potential_kg": round(improvement_potential, 2),
            "improvement_potential_pct": round(improvement_pct, 1),
            "color": meta["color"],
            "tips": category_tips.get(cat_key, []),
        }

    return deep_dive


def compute_projection_timeline(
    user_total_kg: float,
    annual_reduction_pct: float = 5.0,
    years: int = 10,
) -> list[dict[str, Any]]:
    """Project the user's footprint over multiple years at a given reduction rate.

    Args:
        user_total_kg: Current annual footprint in kg
        annual_reduction_pct: Yearly reduction percentage (e.g. 5.0 = 5%/year)
        years: Number of years to project

    Returns:
        List of dicts with year, projected_kg, cumulative_saved_kg
    """
    timeline: list[dict[str, Any]] = []
    current = user_total_kg
    cumulative_saved = 0.0

    for yr in range(years + 1):
        saved = 0.0
        if yr > 0:
            reduction = current * (annual_reduction_pct / 100)
            current = max(0.0, current - reduction)
            saved = user_total_kg - current

        cumulative_saved += (user_total_kg - current) if yr > 0 else 0.0

        timeline.append({
            "year": yr,
            "projected_kg": round(current, 2),
            "cumulative_saved_kg": round(cumulative_saved, 2),
            "annual_reduction_kg": round(
                (user_total_kg * annual_reduction_pct / 100) * (1.048 ** yr), 2
            ) if yr > 0 else 0.0,
        })

    return timeline


def compute_equivalents(co2_kg: float) -> dict[str, float]:
    """Convert CO2 kg into relatable equivalencies."""
    if co2_kg <= 0:
        return {
            "trees_needed": 0,
            "driving_km": 0,
            "smartphone_charges": 0,
            "meals_equivalent": 0,
            "liters_water": 0,
        }
    return {
        "trees_needed": round(co2_kg / 21.0, 1),       # ~21 kg CO2 absorbed/tree/year
        "driving_km": round(co2_kg / 0.21, 0),          # ~0.21 kg CO2/km
        "smartphone_charges": round(co2_kg / 0.008, 0),  # ~8g per charge
        "meals_equivalent": round(co2_kg / 3.3, 1),     # ~3.3 kg per average meal
        "liters_water": round(co2_kg * 3.5, 0),         # ~3.5 L water per kg CO2
    }


def build_full_comparison_report(
    user_footprint_kg: float,
    user_eco_score: int,
    user_contributors: dict[str, float],
    user_id: Optional[int] = None,
) -> ComparisonReport:
    """Build a comprehensive comparison report for a user.

    This is the main entry point that orchestrates all comparison
    analyses and returns a single ComparisonReport dataclass.
    """
    # 1. Category comparisons against EU average
    eu_contributors = {
        k: v * 1000 for k, v in COUNTRY_AVERAGES["EU"].items() if k != "total_tonnes"
    }
    cat_comparisons = compare_categories(user_contributors, eu_contributors)

    # 2. Percentile ranking
    percentile = compute_percentile(
        user_footprint_kg,
        population_mean_kg=COUNTRY_AVERAGES["Global"]["total_tonnes"] * 1000,
    )

    # 3. Archetype matching
    archetypes = match_archetypes(user_contributors, user_footprint_kg)

    # 4. Reduction targets
    targets = compute_reduction_targets(user_footprint_kg, user_contributors)

    # 5. Readiness score
    readiness = compute_readiness_score(user_footprint_kg, user_contributors)

    # 6. Peer group average
    peer_avg = estimate_peer_group_average(user_id)

    # 7. Potential savings
    potential_savings = sum(
        max(0.0, c.user_kg - c.benchmark_kg) for c in cat_comparisons
    )

    return ComparisonReport(
        user_footprint_kg=round(user_footprint_kg, 2),
        user_eco_score=user_eco_score,
        category_comparisons=cat_comparisons,
        country_percentile=percentile,
        archetype_matches=archetypes,
        reduction_targets=targets,
        readiness=readiness,
        peer_group_avg_kg=round(peer_avg, 2),
        potential_savings_kg=round(potential_savings, 2),
        generated_at=datetime.utcnow().isoformat(),
    )


def get_country_list() -> list[str]:
    """Return sorted list of available country benchmarks."""
    return sorted(COUNTRY_AVERAGES.keys())


def get_archetype_list() -> list[dict[str, str]]:
    """Return all lifestyle archetypes with key info."""
    return [
        {
            "name": name,
            "avatar": data["avatar"],
            "description": data["description"],
            "typical_kg": str(data["typical_kg"]),
        }
        for name, data in LIFESTYLE_ARCHETYPES.items()
    ]


def get_ipcc_target_list() -> list[dict[str, str]]:
    """Return all IPCC-aligned targets."""
    return [
        {
            "name": name,
            "description": data["description"],
            "target_kg": str(data["target_kg"]),
            "source": data["source"],
        }
        for name, data in IPCC_TARGETS.items()
    ]


def format_kg_to_tonnes(kg: float) -> str:
    """Format kg value as tonnes with 2 decimal places."""
    return f"{kg / 1000:.2f} t"


def rating_color(rating: str) -> str:
    """Return a hex color for a category rating."""
    return {
        "excellent": "#22c55e",
        "good": "#84cc16",
        "average": "#eab308",
        "poor": "#f97316",
        "critical": "#ef4444",
    }.get(rating, "#6b7280")


def get_benchmark_country(country: str) -> dict[str, Any]:
    """Get benchmark data for a specific country."""
    return COUNTRY_AVERAGES.get(country, COUNTRY_AVERAGES["Global"])
