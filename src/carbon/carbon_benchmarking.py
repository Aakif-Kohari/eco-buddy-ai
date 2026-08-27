"""Carbon Footprint Comparison & Benchmarking Engine for EcoBuddy AI.

Provides peer-group comparison, country/global benchmarks, personal history
trend analysis, community leaderboard ranking, and AI-generated comparative
insights so users understand exactly how their footprint stacks up.
"""

from __future__ import annotations

import math
import sqlite3
import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

# ── Benchmark Data ───────────────────────────────────────────────────────────

# Annual kg CO2 per capita by country / region (approximate 2023 figures)
COUNTRY_BENCHMARKS: dict[str, dict[str, Any]] = {
    "US": {
        "name": "United States",
        "continent": "North America",
        "per_capita_kg": 14900,
        "population_millions": 331,
        "category_breakdown": {
            "Transport": 4500,
            "Electricity": 3800,
            "Diet": 3200,
            "Flights": 2800,
        },
    },
    "UK": {
        "name": "United Kingdom",
        "continent": "Europe",
        "per_capita_kg": 5200,
        "population_millions": 67,
        "category_breakdown": {
            "Transport": 1400,
            "Electricity": 1600,
            "Diet": 1200,
            "Flights": 900,
        },
    },
    "EU": {
        "name": "European Union (avg)",
        "continent": "Europe",
        "per_capita_kg": 6200,
        "population_millions": 447,
        "category_breakdown": {
            "Transport": 1800,
            "Electricity": 1800,
            "Diet": 1500,
            "Flights": 1100,
        },
    },
    "India": {
        "name": "India",
        "continent": "Asia",
        "per_capita_kg": 1900,
        "population_millions": 1428,
        "category_breakdown": {
            "Transport": 450,
            "Electricity": 700,
            "Diet": 500,
            "Flights": 150,
        },
    },
    "China": {
        "name": "China",
        "continent": "Asia",
        "per_capita_kg": 7400,
        "population_millions": 1412,
        "category_breakdown": {
            "Transport": 1500,
            "Electricity": 3200,
            "Diet": 1600,
            "Flights": 700,
        },
    },
    "Brazil": {
        "name": "Brazil",
        "continent": "South America",
        "per_capita_kg": 2300,
        "population_millions": 214,
        "category_breakdown": {
            "Transport": 700,
            "Electricity": 500,
            "Diet": 700,
            "Flights": 200,
        },
    },
    "Japan": {
        "name": "Japan",
        "continent": "Asia",
        "per_capita_kg": 8500,
        "population_millions": 125,
        "category_breakdown": {
            "Transport": 1800,
            "Electricity": 2800,
            "Diet": 1700,
            "Flights": 1200,
        },
    },
    "Australia": {
        "name": "Australia",
        "continent": "Oceania",
        "per_capita_kg": 15400,
        "population_millions": 26,
        "category_breakdown": {
            "Transport": 4200,
            "Electricity": 4600,
            "Diet": 3400,
            "Flights": 2600,
        },
    },
    "Nigeria": {
        "name": "Nigeria",
        "continent": "Africa",
        "per_capita_kg": 550,
        "population_millions": 223,
        "category_breakdown": {
            "Transport": 120,
            "Electricity": 200,
            "Diet": 150,
            "Flights": 50,
        },
    },
    "Global": {
        "name": "Global Average",
        "continent": "World",
        "per_capita_kg": 4700,
        "population_millions": 8000,
        "category_breakdown": {
            "Transport": 1300,
            "Electricity": 1500,
            "Diet": 1100,
            "Flights": 600,
        },
    },
    "Paris_Agreement_Target": {
        "name": "Paris Agreement 2°C Target",
        "continent": "Policy",
        "per_capita_kg": 2000,
        "population_millions": 8000,
        "category_breakdown": {
            "Transport": 500,
            "Electricity": 600,
            "Diet": 500,
            "Flights": 300,
        },
    },
    "Net_Zero_2050_Target": {
        "name": "Net-Zero 2050 Pathway",
        "continent": "Policy",
        "per_capita_kg": 1000,
        "population_millions": 8000,
        "category_breakdown": {
            "Transport": 250,
            "Electricity": 300,
            "Diet": 250,
            "Flights": 100,
        },
    },
}

# Lifestyles / archetypes for peer comparison
LIFESTYLE_ARCHETYPES: dict[str, dict[str, Any]] = {
    "urban_eco_warrior": {
        "name": "Urban Eco Warrior",
        "description": "City dweller, bikes to work, plant-based diet, minimal flying",
        "footprint_kg": 2200,
        "category_breakdown": {
            "Transport": 200,
            "Electricity": 900,
            "Diet": 500,
            "Flights": 100,
        },
    },
    "suburban_commuter": {
        "name": "Suburban Commuter",
        "description": "Drives to work daily, moderate electricity use, mixed diet",
        "footprint_kg": 5800,
        "category_breakdown": {
            "Transport": 2400,
            "Electricity": 1800,
            "Diet": 1200,
            "Flights": 400,
        },
    },
    "digital_nomad": {
        "name": "Digital Nomad",
        "description": "Works remotely, travels frequently, moderate digital usage",
        "footprint_kg": 4500,
        "category_breakdown": {
            "Transport": 500,
            "Electricity": 1200,
            "Diet": 1000,
            "Flights": 1800,
        },
    },
    "family_household": {
        "name": "Family Household",
        "description": "Average family, two cars, moderate everything",
        "footprint_kg": 7200,
        "category_breakdown": {
            "Transport": 2800,
            "Electricity": 2200,
            "Diet": 1400,
            "Flights": 800,
        },
    },
    "minimalist_rural": {
        "name": "Minimalist Rural",
        "description": "Small home, local food, limited transport needs",
        "footprint_kg": 2800,
        "category_breakdown": {
            "Transport": 800,
            "Electricity": 1000,
            "Diet": 600,
            "Flights": 100,
        },
    },
    "luxury_high_emitter": {
        "name": "High Emitter",
        "description": "Multiple vehicles, large home, frequent flights, heavy diet",
        "footprint_kg": 16000,
        "category_breakdown": {
            "Transport": 5000,
            "Electricity": 4500,
            "Diet": 3000,
            "Flights": 3500,
        },
    },
    "student": {
        "name": "Student",
        "description": "Shared housing, public transport, budget-conscious",
        "footprint_kg": 3000,
        "category_breakdown": {
            "Transport": 600,
            "Electricity": 800,
            "Diet": 900,
            "Flights": 400,
        },
    },
    "senior_retiree": {
        "name": "Senior Retiree",
        "description": "Reduced commuting, smaller home, moderate travel",
        "footprint_kg": 3500,
        "category_breakdown": {
            "Transport": 600,
            "Electricity": 1300,
            "Diet": 900,
            "Flights": 400,
        },
    },
}

# Percentile breakpoints: maps percentile → annual kg CO2
GLOBAL_PERCENTILE_DISTRIBUTION: dict[int, float] = {
    1: 500,
    5: 900,
    10: 1400,
    20: 2200,
    30: 3000,
    40: 3700,
    50: 4700,
    60: 5800,
    70: 7000,
    80: 8500,
    90: 11000,
    95: 14000,
    99: 20000,
}


# ── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class BenchmarkResult:
    """A single benchmark comparison against one reference."""
    reference_name: str
    reference_kg: float
    user_kg: float
    delta_kg: float
    delta_pct: float
    percentile_if_available: int | None = None
    is_below: bool = False  # True when user emits less than reference
    category_deltas: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        self.delta_kg = round(self.user_kg - self.reference_kg, 2)
        self.delta_pct = (
            round((self.delta_kg / self.reference_kg) * 100, 1)
            if self.reference_kg > 0
            else 0.0
        )
        self.is_below = self.user_kg < self.reference_kg


@dataclass
class PeerGroupMatch:
    """The closest archetype match for a user."""
    archetype_key: str
    archetype_name: str
    description: str
    archetype_kg: float
    user_kg: float
    similarity_score: float  # 0–100, higher = more similar
    category_distances: dict[str, float] = field(default_factory=dict)


@dataclass
class TrendEntry:
    """One point in a historical footprint trend."""
    date: str
    footprint_kg: float
    eco_score: int | None = None
    label: str = ""


@dataclass
class TrendAnalysis:
    """Result of analysing a user's historical footprint trend."""
    entries: list[TrendEntry]
    total_change_kg: float = 0.0
    total_change_pct: float = 0.0
    direction: str = "stable"  # "improving", "worsening", "stable"
    avg_footprint_kg: float = 0.0
    best_kg: float = 0.0
    worst_kg: float = 0.0
    months_of_data: int = 0
    streak_improving: int = 0  # consecutive months of improvement
    streak_worsening: int = 0


@dataclass
class LeaderboardEntry:
    """A single row on the community leaderboard."""
    rank: int
    user_id: int
    username: str
    eco_score: int
    footprint_kg: float
    badge: str
    streak_days: int = 0
    is_anonymous: bool = False


@dataclass
class FullBenchmarkReport:
    """Complete benchmarking report for a user."""
    user_id: int
    footprint_kg: float
    eco_score: int
    contributors: dict[str, float]
    country_benchmarks: list[BenchmarkResult]
    lifestyle_match: PeerGroupMatch | None
    global_percentile: int
    trend: TrendAnalysis | None
    insights: list[str]
    improvement_actions: list[dict[str, Any]]
    comparison_date: str = ""


# ── Benchmark Comparison Engine ──────────────────────────────────────────────


def compare_against_country(
    user_kg: float,
    contributors: dict[str, float],
    country_code: str,
) -> BenchmarkResult:
    """Compare a user's footprint against a country average."""
    country = COUNTRY_BENCHMARKS.get(country_code)
    if country is None:
        raise ValueError(
            f"Unknown country '{country_code}'. Available: {sorted(COUNTRY_BENCHMARKS)}"
        )

    ref_kg = country["per_capita_kg"]
    ref_breakdown = country.get("category_breakdown", {})

    category_deltas = {}
    for cat in contributors:
        user_val = contributors[cat]
        ref_val = ref_breakdown.get(cat, 0)
        category_deltas[cat] = round(user_val - ref_val, 2)

    return BenchmarkResult(
        reference_name=country["name"],
        reference_kg=ref_kg,
        user_kg=user_kg,
        delta_kg=0,  # computed in __post_init__
        delta_pct=0,
        category_deltas=category_deltas,
    )


def compare_against_all_countries(
    user_kg: float,
    contributors: dict[str, float],
) -> list[BenchmarkResult]:
    """Compare against every available country benchmark."""
    results = []
    for code in COUNTRY_BENCHMARKS:
        results.append(compare_against_country(user_kg, contributors, code))
    # Sort by delta — user is best vs lowest benchmarks
    results.sort(key=lambda r: r.delta_kg)
    return results


def compute_global_percentile(user_kg: float) -> int:
    """Estimate the user's global percentile from the distribution table.

    A lower percentile means the user emits less than more people — which
    is the *good* direction for carbon src.carbon.emissions.
    """
    sorted_percentiles = sorted(GLOBAL_PERCENTILE_DISTRIBUTION.items())
    for pct, kg in sorted_percentiles:
        if user_kg <= kg:
            return pct
    return 99


# ── Peer Group / Lifestyle Matching ─────────────────────────────────────────


def _category_distance(
    user_cats: dict[str, float],
    archetype_cats: dict[str, float],
) -> dict[str, float]:
    """Euclidean-ish per-category distance (normalised by archetype value)."""
    distances = {}
    all_cats = set(user_cats) | set(archetype_cats)
    for cat in all_cats:
        u = user_cats.get(cat, 0.0)
        a = archetype_cats.get(cat, 0.0)
        norm = abs(u - a) / max(a, 1.0)
        distances[cat] = round(norm * 100, 1)  # as percentage
    return distances


def find_closest_lifestyle(
    user_kg: float,
    contributors: dict[str, float],
) -> PeerGroupMatch:
    """Find the lifestyle archetype most similar to the user's footprint."""
    best_score = 0.0
    best_match = None

    for key, arch in LIFESTYLE_ARCHETYPES.items():
        # Score = 100 minus normalised total-distance
        total_kg_diff = abs(user_kg - arch["footprint_kg"])
        cat_diffs = _category_distance(contributors, arch["category_breakdown"])
        avg_cat_diff = (
            sum(cat_diffs.values()) / len(cat_diffs) if cat_diffs else 50.0
        )

        # Blend: 60% total footprint closeness, 40% category shape closeness
        max_expected_diff = 20000.0
        total_score = max(0, 100 - (total_kg_diff / max_expected_diff * 100))
        shape_score = max(0, 100 - avg_cat_diff)
        similarity = 0.6 * total_score + 0.4 * shape_score

        if similarity > best_score:
            best_score = similarity
            best_match = PeerGroupMatch(
                archetype_key=key,
                archetype_name=arch["name"],
                description=arch["description"],
                archetype_kg=arch["footprint_kg"],
                user_kg=user_kg,
                similarity_score=round(similarity, 1),
                category_distances=cat_diffs,
            )

    return best_match  # type: ignore[return-value]


# ── Historical Trend Analysis ───────────────────────────────────────────────


def get_user_assessment_history(user_id: int, limit: int = 24) -> list[dict[str, Any]]:
    """Load a user's assessment history from the src.core.database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, user_id, transport, distance, electricity, diet, flights,
                   region, total_emission, eco_score, factor_version, created_at
            FROM assessments
            WHERE user_id = ?
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        logger.error("Failed to load assessment history: %s", exc)
        return []
    finally:
        if conn:
            conn.close()


def analyse_trend(history: list[dict[str, Any]]) -> TrendAnalysis:
    """Analyse a chronological list of assessments for trends."""
    if not history:
        return TrendAnalysis(entries=[], direction="no_data")

    # Reverse so oldest is first
    sorted_history = list(reversed(history))

    entries: list[TrendEntry] = []
    for record in sorted_history:
        entries.append(
            TrendEntry(
                date=str(record.get("created_at", "")),
                footprint_kg=float(record.get("total_emission", 0)),
                eco_score=int(record.get("eco_score", 0)),
            )
        )

    footprints = [e.footprint_kg for e in entries]
    avg_fp = sum(footprints) / len(footprints) if footprints else 0
    best = min(footprints) if footprints else 0
    worst = max(footprints) if footprints else 0

    total_change = 0.0
    total_pct = 0.0
    direction = "stable"
    streak_improving = 0
    streak_worsening = 0
    current_streak_type = None
    current_streak_count = 0

    if len(footprints) >= 2:
        total_change = footprints[-1] - footprints[0]
        total_pct = (
            round((total_change / footprints[0]) * 100, 1)
            if footprints[0] > 0
            else 0.0
        )
        if total_change < -50:
            direction = "improving"
        elif total_change > 50:
            direction = "worsening"

        # Count consecutive improving/worsening months
        for i in range(len(footprints) - 1, 0, -1):
            improved = footprints[i] < footprints[i - 1]
            worsened = footprints[i] > footprints[i - 1]

            if current_streak_type is None:
                if improved:
                    current_streak_type = "improving"
                    current_streak_count = 1
                elif worsened:
                    current_streak_type = "worsening"
                    current_streak_count = 1
                else:
                    break
            elif current_streak_type == "improving" and improved:
                current_streak_count += 1
            elif current_streak_type == "worsening" and worsened:
                current_streak_count += 1
            else:
                break

        if current_streak_type == "improving":
            streak_improving = current_streak_count
        elif current_streak_type == "worsening":
            streak_worsening = current_streak_count

    return TrendAnalysis(
        entries=entries,
        total_change_kg=round(total_change, 2),
        total_change_pct=total_pct,
        direction=direction,
        avg_footprint_kg=round(avg_fp, 2),
        best_kg=round(best, 2),
        worst_kg=round(worst, 2),
        months_of_data=len(entries),
        streak_improving=streak_improving,
        streak_worsening=streak_worsening,
    )


# ── Community Leaderboard ───────────────────────────────────────────────────


def get_leaderboard(
    limit: int = 20,
    user_id: int | None = None,
    include_surrounding: bool = True,
    surrounding_range: int = 5,
) -> list[LeaderboardEntry]:
    """Get the community leaderboard ranked by eco score (descending).

    If *include_surrounding* and *user_id* are given, ensures the user's
    own position plus *surrounding_range* entries above and below are
    included even if they fall outside *limit*.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT u.id AS user_id, u.username, u.anonymous_leaderboard,
                   a.eco_score, a.total_emission
            FROM users u
            INNER JOIN (
                SELECT user_id, eco_score, total_emission,
                       ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY id DESC) AS rn
                FROM assessments
            ) a ON u.id = a.user_id AND a.rn = 1
            ORDER BY a.eco_score DESC
            """
        ).fetchall()

        entries: list[LeaderboardEntry] = []
        for idx, row in enumerate(rows):
            display_name = "Anonymous" if row["anonymous_leaderboard"] else row["username"]
            score = int(row["eco_score"] or 0)
            badge = _score_to_badge(score)

            entries.append(
                LeaderboardEntry(
                    rank=idx + 1,
                    user_id=row["user_id"],
                    username=display_name,
                    eco_score=score,
                    footprint_kg=float(row["total_emission"] or 0),
                    badge=badge,
                    is_anonymous=bool(row["anonymous_leaderboard"]),
                )
            )

        if user_id is not None and include_surrounding:
            user_rank = None
            for entry in entries:
                if entry.user_id == user_id:
                    user_rank = entry.rank
                    break

            if user_rank is not None:
                start = max(0, user_rank - surrounding_range - 1)
                end = min(len(entries), user_rank + surrounding_range)
                surrounding = entries[start:end]
                return surrounding

        return entries[:limit]

    except sqlite3.Error as exc:
        logger.error("Leaderboard query failed: %s", exc)
        return []
    finally:
        if conn:
            conn.close()


def _score_to_badge(score: int) -> str:
    """Map an eco score to a badge emoji."""
    if score >= 85:
        return "🏆"
    elif score >= 70:
        return "🌟"
    elif score >= 50:
        return "🌿"
    elif score >= 30:
        return "🌱"
    else:
        return "🍃"


def get_user_rank(user_id: int) -> dict[str, Any]:
    """Get a specific user's rank and percentile in the leaderboard."""
    all_entries = get_leaderboard(limit=10000, include_surrounding=False)

    if not all_entries:
        return {"rank": 0, "total_users": 0, "percentile": 0}

    total = len(all_entries)
    user_rank = 0
    for entry in all_entries:
        if entry.user_id == user_id:
            user_rank = entry.rank
            break

    if user_rank == 0:
        return {"rank": total + 1, "total_users": total, "percentile": 100}

    percentile = round(((total - user_rank) / total) * 100) if total > 0 else 0

    return {
        "rank": user_rank,
        "total_users": total,
        "eco_score": all_entries[user_rank - 1].eco_score,
        "percentile": max(0, min(100, percentile)),
        "badge": all_entries[user_rank - 1].badge,
    }


# ── Insight Generation ──────────────────────────────────────────────────────


def generate_benchmark_insights(
    user_kg: float,
    eco_score: int,
    contributors: dict[str, float],
    country_code: str = "Global",
) -> list[str]:
    """Generate human-readable comparative insights."""
    insights: list[str] = []

    # Country comparison
    country_result = compare_against_country(
        user_kg, contributors, country_code,
    )
    if country_result.is_below:
        insights.append(
            f"✅ You emit {abs(country_result.delta_pct):.0f}% LESS than the "
            f"{country_result.reference_name} average "
            f"({country_result.reference_kg:,.0f} kg CO₂/year)."
        )
    else:
        insights.append(
            f"⚠️ You emit {country_result.delta_pct:.0f}% MORE than the "
            f"{country_result.reference_name} average "
            f"({country_result.reference_kg:,.0f} kg CO₂/year)."
        )

    # Paris agreement check
    paris = COUNTRY_BENCHMARKS["Paris_Agreement_Target"]
    if user_kg <= paris["per_capita_kg"]:
        insights.append(
            "🌍 Excellent! Your footprint is within the Paris Agreement "
            "2°C target of 2,000 kg CO₂/year."
        )
    elif user_kg <= paris["per_capita_kg"] * 1.5:
        gap = user_kg - paris["per_capita_kg"]
        insights.append(
            f"🌍 You're {gap:,.0f} kg away from meeting the Paris Agreement "
            f"2°C target. A few small changes could get you there!"
        )
    else:
        insights.append(
            f"🌍 Your footprint is {user_kg - paris['per_capita_kg']:,.0f} kg "
            f"above the Paris Agreement target. Focus on your biggest category."
        )

    # Percentile insight
    percentile = compute_global_percentile(user_kg)
    if percentile <= 20:
        insights.append(
            f"📊 You're in the top {percentile}% of lowest emitters globally. "
            f"Keep up the amazing work!"
        )
    elif percentile <= 50:
        insights.append(
            f"📊 You're in the top {percentile}% globally. You're doing well, "
            f"but there's room to improve."
        )
    else:
        insights.append(
            f"📊 You're in the top {100 - percentile}% of highest emitters. "
            f"Focus on your biggest emission categories."
        )

    # Top contributor insight
    if contributors:
        top_cat = max(contributors, key=contributors.get)
        top_val = contributors[top_cat]
        pct_of_total = (
            (top_val / user_kg * 100) if user_kg > 0 else 0
        )
        insights.append(
            f"🔍 Your biggest emission source is {top_cat} at "
            f"{top_val:,.0f} kg CO₂/year ({pct_of_total:.0f}% of total). "
            f"Reducing this will have the most impact."
        )

    # Lifestyle archetype insight
    match = find_closest_lifestyle(user_kg, contributors)
    if match and match.similarity_score > 40:
        insights.append(
            f"👤 Your closest lifestyle archetype is '{match.archetype_name}' "
            f"({match.archetype_kg:,.0f} kg/year). "
            f"Similarity: {match.similarity_score:.0f}%."
        )

    return insights


def generate_improvement_actions(
    user_kg: float,
    contributors: dict[str, float],
    country_code: str = "Global",
) -> list[dict[str, Any]]:
    """Generate prioritised improvement actions based on benchmarks."""
    actions: list[dict[str, Any]] = []

    country = COUNTRY_BENCHMARKS.get(country_code, COUNTRY_BENCHMARKS["Global"])
    ref_breakdown = country.get("category_breakdown", {})

    for cat, user_val in sorted(contributors.items(), key=lambda x: x[1], reverse=True):
        ref_val = ref_breakdown.get(cat, 0)
        if user_val <= ref_val:
            continue  # Already at or below benchmark

        excess = user_val - ref_val
        pct_over = (excess / ref_val * 100) if ref_val > 0 else 0

        if cat == "Transport":
            if excess > 2000:
                actions.append({
                    "category": cat,
                    "action": "Switch to public transport or carpool for daily commute",
                    "potential_savings_kg": round(excess * 0.6, 0),
                    "difficulty": "medium",
                    "impact": "high",
                })
            if excess > 1000:
                actions.append({
                    "category": cat,
                    "action": "Walk or cycle for trips under 3 km",
                    "potential_savings_kg": round(excess * 0.3, 0),
                    "difficulty": "easy",
                    "impact": "medium",
                })

        elif cat == "Electricity":
            if excess > 1500:
                actions.append({
                    "category": cat,
                    "action": "Switch to renewable energy provider or install solar panels",
                    "potential_savings_kg": round(excess * 0.5, 0),
                    "difficulty": "hard",
                    "impact": "high",
                })
            if excess > 500:
                actions.append({
                    "category": cat,
                    "action": "Replace all bulbs with LEDs and use smart power strips",
                    "potential_savings_kg": round(excess * 0.2, 0),
                    "difficulty": "easy",
                    "impact": "medium",
                })

        elif cat == "Diet":
            if excess > 1000:
                actions.append({
                    "category": cat,
                    "action": "Replace 3+ meat meals per week with plant-based alternatives",
                    "potential_savings_kg": round(excess * 0.5, 0),
                    "difficulty": "medium",
                    "impact": "high",
                })
            if excess > 200:
                actions.append({
                    "category": cat,
                    "action": "Buy local and seasonal produce to reduce food miles",
                    "potential_savings_kg": round(excess * 0.15, 0),
                    "difficulty": "easy",
                    "impact": "low",
                })

        elif cat == "Flights":
            if excess > 1000:
                actions.append({
                    "category": cat,
                    "action": "Replace one flight per year with train travel",
                    "potential_savings_kg": round(excess * 0.4, 0),
                    "difficulty": "hard",
                    "impact": "high",
                })
            if excess > 300:
                actions.append({
                    "category": cat,
                    "action": "Offset remaining flight emissions through verified programmes",
                    "potential_savings_kg": round(excess * 0.3, 0),
                    "difficulty": "easy",
                    "impact": "medium",
                })

    actions.sort(key=lambda a: a["potential_savings_kg"], reverse=True)
    return actions


# ── Full Report Builder ─────────────────────────────────────────────────────


def build_full_benchmark_report(
    user_id: int,
    footprint_kg: float,
    eco_score: int,
    contributors: dict[str, float],
    country_code: str = "Global",
) -> FullBenchmarkReport:
    """Build a comprehensive benchmarking report for a user."""
    # Country comparisons
    country_results = compare_against_all_countries(user_kg=footprint_kg, contributors=contributors)

    # Lifestyle match
    lifestyle_match = find_closest_lifestyle(user_kg=footprint_kg, contributors=contributors)

    # Global percentile
    global_percentile = compute_global_percentile(user_kg=footprint_kg)

    # Trend analysis
    history = get_user_assessment_history(user_id, limit=24)
    trend = analyse_trend(history) if history else None

    # Insights
    insights = generate_benchmark_insights(
        footprint_kg, eco_score, contributors, country_code,
    )

    # Improvement actions
    improvement_actions = generate_improvement_actions(
        footprint_kg, contributors, country_code,
    )

    return FullBenchmarkReport(
        user_id=user_id,
        footprint_kg=footprint_kg,
        eco_score=eco_score,
        contributors=contributors,
        country_benchmarks=country_results,
        lifestyle_match=lifestyle_match,
        global_percentile=global_percentile,
        trend=trend,
        insights=insights,
        improvement_actions=improvement_actions,
        comparison_date=datetime.now(timezone.utc).isoformat(),
    )


# ── Country List Helper ──────────────────────────────────────────────────────


def list_available_countries() -> list[dict[str, str]]:
    """Return a list of available country benchmarks for UI dropdowns."""
    countries = []
    for code, info in COUNTRY_BENCHMARKS.items():
        countries.append({
            "code": code,
            "name": info["name"],
            "continent": info["continent"],
            "per_capita_kg": info["per_capita_kg"],
        })
    countries.sort(key=lambda c: c["per_capita_kg"])
    return countries


def list_lifestyle_archetypes() -> list[dict[str, Any]]:
    """Return all lifestyle archetypes for UI display."""
    return [
        {
            "key": key,
            "name": info["name"],
            "description": info["description"],
            "footprint_kg": info["footprint_kg"],
        }
        for key, info in LIFESTYLE_ARCHETYPES.items()
    ]
