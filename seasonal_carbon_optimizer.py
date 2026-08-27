"""Seasonal Carbon Optimizer — time-aware carbon footprint analysis for EcoBuddy AI.

Provides seasonal adjustment factors, weather-aware scoring, actionable optimization
recommendations, and report generation that account for monthly / quarterly climate
patterns.  Designed to integrate cleanly with the existing ``emissions``,
``recommendations``, and ``water`` modules.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ── Season Definitions ───────────────────────────────────────────────────────

MONTHS = list(range(1, 13))

HEMISPHERES = ("northern", "southern")

SEASON_MONTHS: dict[str, dict[str, list[int]]] = {
    "northern": {
        "winter": [12, 1, 2],
        "spring": [3, 4, 5],
        "summer": [6, 7, 8],
        "autumn": [9, 10, 11],
    },
    "southern": {
        "summer": [12, 1, 2],
        "autumn": [3, 4, 5],
        "winter": [6, 7, 8],
        "spring": [9, 10, 11],
    },
}

QUARTER_MONTHS: dict[int, list[int]] = {
    1: [1, 2, 3],
    2: [4, 5, 6],
    3: [7, 8, 9],
    4: [10, 11, 12],
}


# ── Emission Adjustment Factors ─────────────────────────────────────────────
# These represent *relative* multipliers applied to the base category
# emissions to account for seasonal behavioural / climate changes.

# Heating & cooling adjustments (electricity-dominated)
HEATING_COOLING_ADJUSTMENTS: dict[str, dict[str, float]] = {
    "northern": {
        "winter": 1.45,   # heavy heating demand
        "spring": 0.90,   # mild → less HVAC
        "summer": 1.15,   # air-conditioning surge
        "autumn": 0.85,   # mild transition
    },
    "southern": {
        "summer": 1.45,
        "autumn": 0.90,
        "winter": 0.85,
        "spring": 1.15,
    },
}

# Transport adjustments (e.g., more car use in winter / rainy season)
TRANSPORT_ADJUSTMENTS: dict[str, dict[str, float]] = {
    "northern": {
        "winter": 1.20,   # cold weather → more driving
        "spring": 0.95,
        "summer": 0.90,   # pleasant weather → cycling/walking
        "autumn": 1.00,
    },
    "southern": {
        "summer": 1.20,
        "autumn": 0.95,
        "winter": 0.90,
        "spring": 1.00,
    },
}

# Diet adjustments (seasonal produce availability, holiday feasts)
DIET_ADJUSTMENTS: dict[str, dict[str, float]] = {
    "northern": {
        "winter": 1.10,   # heavier meals, holidays
        "spring": 0.95,
        "summer": 0.90,   # lighter, local produce
        "autumn": 1.00,
    },
    "southern": {
        "summer": 1.10,
        "autumn": 0.95,
        "winter": 0.90,
        "spring": 1.00,
    },
}

# Flight adjustments (peak travel seasons)
FLIGHT_ADJUSTMENTS: dict[str, dict[str, float]] = {
    "northern": {
        "winter": 1.30,   # holiday travel
        "spring": 0.90,
        "summer": 1.25,   # summer holidays
        "autumn": 0.85,
    },
    "southern": {
        "summer": 1.30,
        "autumn": 0.90,
        "winter": 1.25,
        "spring": 0.85,
    },
}

# Water adjustments (irrigation, seasonal demand)
WATER_ADJUSTMENTS: dict[str, dict[str, float]] = {
    "northern": {
        "winter": 0.70,   # no garden watering
        "spring": 1.00,
        "summer": 1.50,   # peak irrigation
        "autumn": 0.85,
    },
    "southern": {
        "summer": 0.70,
        "autumn": 1.00,
        "winter": 1.50,
        "spring": 0.85,
    },
}

ALL_CATEGORY_ADJUSTMENTS: dict[str, dict[str, dict[str, float]]] = {
    "electricity": HEATING_COOLING_ADJUSTMENTS,
    "transport": TRANSPORT_ADJUSTMENTS,
    "diet": DIET_ADJUSTMENTS,
    "flights": FLIGHT_ADJUSTMENTS,
    "water": WATER_ADJUSTMENTS,
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_season(month: int, hemisphere: str = "northern") -> str:
    """Return the season name for *month* (1–12) in the given hemisphere."""
    hemisphere = hemisphere.lower().strip()
    if hemisphere not in HEMISPHERES:
        raise ValueError(
            f"Unknown hemisphere '{hemisphere}'. Must be one of {HEMISPHERES}"
        )
    for season, months in SEASON_MONTHS[hemisphere].items():
        if month in months:
            return season
    raise ValueError(f"Invalid month {month}")


def get_seasonal_adjustment(
    category: str,
    month: int | None = None,
    hemisphere: str = "northern",
) -> float:
    """Return the seasonal emission adjustment multiplier for *category*.

    Parameters
    ----------
    category : str
        One of ``"electricity"``, ``"transport"``, ``"diet"``,
        ``"flights"``, ``"water"``.
    month : int | None
        1–12. Defaults to the current month if *None*.
    hemisphere : str
        ``"northern"`` (default) or ``"southern"``.

    Returns
    -------
    float
        Multiplier ≥ 0. 1.0 means no seasonal adjustment.
    """
    if category not in ALL_CATEGORY_ADJUSTMENTS:
        raise ValueError(
            f"Unknown category '{category}'. "
            f"Valid: {sorted(ALL_CATEGORY_ADJUSTMENTS)}"
        )
    if month is None:
        month = datetime.now().month
    if not (1 <= month <= 12):
        raise ValueError(f"month must be 1–12, got {month}")

    season = _get_season(month, hemisphere)
    adjustments = ALL_CATEGORY_ADJUSTMENTS[category]
    return adjustments[hemisphere][season]


def get_all_adjustments(
    month: int | None = None,
    hemisphere: str = "northern",
) -> dict[str, float]:
    """Return seasonal adjustments for *every* tracked category."""
    return {
        cat: get_seasonal_adjustment(cat, month, hemisphere)
        for cat in ALL_CATEGORY_ADJUSTMENTS
    }


# ── Seasonal Footprint ──────────────────────────────────────────────────────


@dataclass
class SeasonalFootprintResult:
    """Container for a seasonally-adjusted footprint calculation."""
    raw_footprint_kg: float
    adjusted_footprint_kg: float
    adjustment_factor: float
    month: int
    season: str
    hemisphere: str
    category_breakdown: dict[str, float] = field(default_factory=dict)
    adjusted_breakdown: dict[str, float] = field(default_factory=dict)

    @property
    def delta_kg(self) -> float:
        """Difference between adjusted and raw (positive = worse)."""
        return round(self.adjusted_footprint_kg - self.raw_footprint_kg, 2)

    @property
    def delta_pct(self) -> float:
        """Percentage change (positive = worse)."""
        if self.raw_footprint_kg == 0:
            return 0.0
        return round(
            (self.delta_kg / self.raw_footprint_kg) * 100.0, 2
        )


def calculate_seasonal_footprint(
    raw_footprint_kg: float,
    contributors: dict[str, float],
    month: int | None = None,
    hemisphere: str = "northern",
) -> SeasonalFootprintResult:
    """Apply seasonal adjustments to a baseline footprint.

    Parameters
    ----------
    raw_footprint_kg : float
        The annual-equivalent or raw footprint in kg CO₂.
    contributors : dict[str, float]
        Category-level emissions (e.g. ``{"Transport": 1200, ...}``).
    month : int | None
        Target month (1–12). Defaults to current month.
    hemisphere : str
        ``"northern"`` or ``"southern"``.

    Returns
    -------
    SeasonalFootprintResult
    """
    if month is None:
        month = datetime.now().month
    season = _get_season(month, hemisphere)

    # Map contributor keys to adjustment category names
    _key_map: dict[str, str] = {
        "Transport": "transport",
        "Electricity": "electricity",
        "Diet": "diet",
        "Flights": "flights",
        "Water": "water",
    }

    adjusted_breakdown: dict[str, float] = {}
    total_adjusted = 0.0

    for cat_key, cat_val in contributors.items():
        adj_category = _key_map.get(cat_key)
        if adj_category is None:
            # Unknown category → no adjustment
            adjusted_breakdown[cat_key] = round(cat_val, 2)
            total_adjusted += cat_val
            continue
        adj_factor = get_seasonal_adjustment(adj_category, month, hemisphere)
        adjusted = cat_val * adj_factor
        adjusted_breakdown[cat_key] = round(adjusted, 2)
        total_adjusted += adjusted

    # Compute a blended overall factor
    blend_factor = (
        total_adjusted / raw_footprint_kg
        if raw_footprint_kg > 0
        else 1.0
    )

    return SeasonalFootprintResult(
        raw_footprint_kg=raw_footprint_kg,
        adjusted_footprint_kg=round(total_adjusted, 2),
        adjustment_factor=round(blend_factor, 4),
        month=month,
        season=season,
        hemisphere=hemisphere,
        category_breakdown={k: round(v, 2) for k, v in contributors.items()},
        adjusted_breakdown=adjusted_breakdown,
    )


# ── Seasonal Score ──────────────────────────────────────────────────────────

# Benchmarks (kg CO₂ / year) by season for scoring purposes
SEASONAL_BENCHMARKS: dict[str, float] = {
    "winter": 4200.0,
    "spring": 3800.0,
    "summer": 4000.0,
    "autumn": 3600.0,
}


def seasonal_eco_score(
    adjusted_footprint_kg: float,
    month: int | None = None,
    hemisphere: str = "northern",
) -> dict[str, Any]:
    """Compute an eco score adjusted for seasonal context.

    Returns a dict with keys:
    ``score`` (0–100), ``grade``, ``season``, ``benchmark_kg``,
    ``vs_benchmark_pct``, ``status``, ``color``.
    """
    if month is None:
        month = datetime.now().month
    season = _get_season(month, hemisphere)
    benchmark = SEASONAL_BENCHMARKS.get(season, 4000.0)

    ratio = adjusted_footprint_kg / benchmark if benchmark > 0 else 1.0
    vs_benchmark = ((adjusted_footprint_kg - benchmark) / benchmark) * 100.0

    # Sigmoid-based score centred on the seasonal benchmark
    sensitivity = 1000.0
    raw_score = 100.0 / (1.0 + math.exp((adjusted_footprint_kg - benchmark) / sensitivity))
    score = int(round(max(0.0, min(100.0, raw_score))))

    if score >= 80:
        grade, status, color = "A", "Excellent – below seasonal benchmark", "#22c55e"
    elif score >= 60:
        grade, status, color = "B", "Good – near seasonal benchmark", "#38bdf8"
    elif score >= 40:
        grade, status, color = "C", "Moderate – slightly above benchmark", "#facc15"
    elif score >= 20:
        grade, status, color = "D", "Needs improvement – well above benchmark", "#fb923c"
    else:
        grade, status, color = "F", "Critical – far above benchmark", "#ef4444"

    return {
        "score": score,
        "grade": grade,
        "season": season,
        "hemisphere": hemisphere,
        "month": month,
        "benchmark_kg": benchmark,
        "adjusted_footprint_kg": round(adjusted_footprint_kg, 2),
        "vs_benchmark_pct": round(vs_benchmark, 2),
        "status": status,
        "color": color,
    }


# ── Optimization Recommendations ───────────────────────────────────────────

# Tip templates keyed by (season, category)
_TIPS: dict[tuple[str, str], list[dict[str, str]]] = {
    # ── Winter ──
    ("winter", "electricity"): [
        {
            "action": "Lower thermostat by 2°C and wear warmer layers",
            "impact_kg_year": 320,
            "difficulty": "easy",
            "tip": "Each 1°C reduction saves ~5–10% on heating energy.",
        },
        {
            "action": "Use a programmable thermostat to reduce overnight heating",
            "impact_kg_year": 210,
            "difficulty": "easy",
            "tip": "Automatic setbacks avoid heating an empty or sleeping home.",
        },
    ],
    ("winter", "transport"): [
        {
            "action": "Carpool for winter commutes to share heating energy",
            "impact_kg_year": 180,
            "difficulty": "medium",
            "tip": "Shared rides reduce per-person fuel burn significantly.",
        },
        {
            "action": "Use public transit instead of driving in bad weather",
            "impact_kg_year": 260,
            "difficulty": "medium",
            "tip": "Buses and trains are far more efficient per passenger-mile.",
        },
    ],
    ("winter", "diet"): [
        {
            "action": "Replace 1 red-meat meal per week with seasonal root vegetables",
            "impact_kg_year": 150,
            "difficulty": "easy",
            "tip": "Root vegetables are in season and require less processing.",
        },
    ],
    ("winter", "flights"): [
        {
            "action": "Replace one holiday flight with train travel where possible",
            "impact_kg_year": 250,
            "difficulty": "hard",
            "tip": "European rail produces ~1/10th the CO₂ of an equivalent flight.",
        },
    ],
    ("winter", "water"): [
        {
            "action": "Fix dripping taps — cold weather increases freeze-burst risk",
            "impact_kg_year": 40,
            "difficulty": "easy",
            "tip": "A dripping tap wastes ~20 litres per day.",
        },
    ],
    # ── Spring ──
    ("spring", "electricity"): [
        {
            "action": "Open windows for natural ventilation instead of AC",
            "impact_kg_year": 120,
            "difficulty": "easy",
            "tip": "Spring temperatures allow free cooling for most of the day.",
        },
    ],
    ("spring", "transport"): [
        {
            "action": "Start cycling to work as weather improves",
            "impact_kg_year": 350,
            "difficulty": "medium",
            "tip": "A 5km cycle commute saves ~1 tonne CO₂/year vs driving.",
        },
    ],
    ("spring", "diet"): [
        {
            "action": "Eat local spring produce (asparagus, peas, greens)",
            "impact_kg_year": 90,
            "difficulty": "easy",
            "tip": "Local seasonal produce avoids cold-storage and long-haul transport.",
        },
    ],
    ("spring", "water"): [
        {
            "action": "Start a rainwater collection system for garden use",
            "impact_kg_year": 60,
            "difficulty": "medium",
            "tip": "Spring rains provide free irrigation water.",
        },
    ],
    # ── Summer ──
    ("summer", "electricity"): [
        {
            "action": "Use fans before turning on AC — set AC to 25°C not 20°C",
            "impact_kg_year": 280,
            "difficulty": "easy",
            "tip": "Each degree of AC cooling costs ~6–8% more energy.",
        },
        {
            "action": "Close blinds and curtains during peak afternoon sun",
            "impact_kg_year": 140,
            "difficulty": "easy",
            "tip": "Blocking solar heat reduces cooling load by up to 30%.",
        },
    ],
    ("summer", "transport"): [
        {
            "action": "Walk or cycle for trips under 3 km",
            "impact_kg_year": 200,
            "difficulty": "easy",
            "tip": "Summer weather is ideal for active transport.",
        },
    ],
    ("summer", "diet"): [
        {
            "action": "Eat raw salads and light meals to reduce cooking energy",
            "impact_kg_year": 70,
            "difficulty": "easy",
            "tip": "No-cook meals save both energy and keep the home cooler.",
        },
    ],
    ("summer", "water"): [
        {
            "action": "Water garden early morning to reduce evaporation",
            "impact_kg_year": 90,
            "difficulty": "easy",
            "tip": "Morning watering wastes 30–50% less than midday.",
        },
        {
            "action": "Use drip irrigation instead of sprinklers",
            "impact_kg_year": 130,
            "difficulty": "medium",
            "tip": "Drip systems deliver water directly to roots, cutting waste.",
        },
    ],
    # ── Autumn ──
    ("autumn", "electricity"): [
        {
            "action": "Switch to LED seasonal lighting and turn off early",
            "impact_kg_year": 80,
            "difficulty": "easy",
            "tip": "LEDs use 75% less energy than incandescent bulbs.",
        },
    ],
    ("autumn", "transport"): [
        {
            "action": "Combine errands into a single trip to save fuel",
            "impact_kg_year": 150,
            "difficulty": "easy",
            "tip": "A warm engine is more efficient — consolidated trips help.",
        },
    ],
    ("autumn", "diet"): [
        {
            "action": "Use autumn harvest soups and stews (bulk cooking)",
            "impact_kg_year": 100,
            "difficulty": "easy",
            "tip": "Batch cooking is more energy-efficient than daily meal prep.",
        },
    ],
    ("autumn", "flights"): [
        {
            "action": "Offset any end-of-year business travel",
            "impact_kg_year": 200,
            "difficulty": "medium",
            "tip": "Verified offset programmes neutralise flight emissions.",
        },
    ],
    ("autumn", "water"): [
        {
            "action": "Winterise outdoor taps to prevent pipe freeze waste",
            "impact_kg_year": 30,
            "difficulty": "easy",
            "tip": "Frozen-burst pipes cause massive water waste.",
        },
    ],
}


def generate_seasonal_recommendations(
    month: int | None = None,
    hemisphere: str = "northern",
    categories: list[str] | None = None,
    difficulty_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Return season-appropriate optimization recommendations.

    Parameters
    ----------
    month : int | None
        Target month. Defaults to current month.
    hemisphere : str
        ``"northern"`` or ``"southern"``.
    categories : list[str] | None
        Filter to specific categories (e.g. ``["electricity", "water"]``).
        If *None*, returns all categories for the season.
    difficulty_filter : str | None
        If set (``"easy"``, ``"medium"``, ``"hard"``), filter by difficulty.

    Returns
    -------
    list[dict]
        Each dict has keys: ``action``, ``impact_kg_year``, ``difficulty``,
        ``tip``, ``category``, ``season``.
    """
    if month is None:
        month = datetime.now().month
    season = _get_season(month, hemisphere)

    results: list[dict[str, Any]] = []
    for (s, cat), tips in _TIPS.items():
        if s != season:
            continue
        if categories and cat not in categories:
            continue
        for tip in tips:
            if difficulty_filter and tip["difficulty"] != difficulty_filter:
                continue
            results.append({
                **tip,
                "category": cat,
                "season": season,
            })

    # Sort by impact descending
    results.sort(key=lambda t: t["impact_kg_year"], reverse=True)
    return results


# ── Seasonal Report ─────────────────────────────────────────────────────────

@dataclass
class SeasonalReport:
    """Structured quarterly / monthly report for the user."""
    month: int
    quarter: int
    season: str
    hemisphere: str
    footprint_result: SeasonalFootprintResult
    score_data: dict[str, Any]
    recommendations: list[dict[str, Any]]
    monthly_savings_potential_kg: float = 0.0
    annualised_savings_potential_kg: float = 0.0
    summary_text: str = ""

    def __post_init__(self):
        self.monthly_savings_potential_kg = round(
            sum(r["impact_kg_year"] for r in self.recommendations) / 12.0, 2
        )
        self.annualised_savings_potential_kg = round(
            sum(r["impact_kg_year"] for r in self.recommendations), 2
        )
        self.summary_text = self._build_summary()

    def _build_summary(self) -> str:
        s = self.score_data
        return (
            f"Season: {self.season.title()} ({self.hemisphere.title()} Hemisphere) "
            f"| Month: {self.month} | Quarter: Q{self.quarter}\n"
            f"Adjusted Footprint: {s['adjusted_footprint_kg']:.0f} kg CO₂  "
            f"(vs {s['benchmark_kg']:.0f} kg benchmark)\n"
            f"Eco Score: {s['score']}/100 ({s['grade']}) — {s['status']}\n"
            f"Potential Monthly Savings: {self.monthly_savings_potential_kg:.0f} kg CO₂\n"
            f"Potential Annual Savings: {self.annualised_savings_potential_kg:.0f} kg CO₂\n"
            f"Top Recommendations: {len(self.recommendations)}"
        )


def generate_seasonal_report(
    raw_footprint_kg: float,
    contributors: dict[str, float],
    month: int | None = None,
    hemisphere: str = "northern",
    max_recommendations: int = 5,
) -> SeasonalReport:
    """Generate a comprehensive seasonal report.

    Parameters
    ----------
    raw_footprint_kg : float
        Baseline annual footprint in kg CO₂.
    contributors : dict[str, float]
        Per-category emissions.
    month : int | None
        Defaults to current month.
    hemisphere : str
        ``"northern"`` or ``"southern"``.
    max_recommendations : int
        Maximum recommendations to include.

    Returns
    -------
    SeasonalReport
    """
    if month is None:
        month = datetime.now().month

    footprint_result = calculate_seasonal_footprint(
        raw_footprint_kg, contributors, month, hemisphere,
    )
    score_data = seasonal_eco_score(
        footprint_result.adjusted_footprint_kg, month, hemisphere,
    )
    recs = generate_seasonal_recommendations(month, hemisphere)
    recs = recs[:max_recommendations]

    quarter = (month - 1) // 3 + 1
    season = _get_season(month, hemisphere)

    return SeasonalReport(
        month=month,
        quarter=quarter,
        season=season,
        hemisphere=hemisphere,
        footprint_result=footprint_result,
        score_data=score_data,
        recommendations=recs,
    )


# ── Quarterly Comparison ───────────────────────────────────────────────────

@dataclass
class QuarterlyComparison:
    """Side-by-side comparison of a footprint across all four quarters."""
    raw_footprint_kg: float
    contributors: dict[str, float]
    hemisphere: str
    quarters: dict[int, dict[str, Any]] = field(default_factory=dict)

    @property
    def best_quarter(self) -> int:
        """Quarter with the lowest adjusted footprint."""
        return min(self.quarters, key=lambda q: self.quarters[q]["adjusted_kg"])

    @property
    def worst_quarter(self) -> int:
        """Quarter with the highest adjusted footprint."""
        return max(self.quarters, key=lambda q: self.quarters[q]["adjusted_kg"])

    @property
    def annual_adjusted_kg(self) -> float:
        """Sum of mid-month adjusted footprints across 4 quarters."""
        return round(
            sum(q["adjusted_kg"] for q in self.quarters.values()), 2
        )


def generate_quarterly_comparison(
    raw_footprint_kg: float,
    contributors: dict[str, float],
    hemisphere: str = "northern",
) -> QuarterlyComparison:
    """Compare footprint across all four calendar quarters.

    Uses the middle month of each quarter as the representative month.
    """
    comp = QuarterlyComparison(
        raw_footprint_kg=raw_footprint_kg,
        contributors=contributors,
        hemisphere=hemisphere,
    )

    for q_num, months in QUARTER_MONTHS.items():
        mid_month = months[1]  # middle month
        fp = calculate_seasonal_footprint(
            raw_footprint_kg, contributors, mid_month, hemisphere,
        )
        sc = seasonal_eco_score(fp.adjusted_footprint_kg, mid_month, hemisphere)
        recs = generate_seasonal_recommendations(mid_month, hemisphere)
        comp.quarters[q_num] = {
            "quarter": q_num,
            "mid_month": mid_month,
            "season": fp.season,
            "raw_kg": fp.raw_footprint_kg,
            "adjusted_kg": fp.adjusted_footprint_kg,
            "delta_kg": fp.delta_kg,
            "delta_pct": fp.delta_pct,
            "score": sc["score"],
            "grade": sc["grade"],
            "recommendation_count": len(recs),
        }

    return comp


# ── Month-by-Month Forecast ────────────────────────────────────────────────

def generate_monthly_forecast(
    raw_footprint_kg: float,
    contributors: dict[str, float],
    hemisphere: str = "northern",
) -> list[dict[str, Any]]:
    """Produce a 12-month seasonal footprint forecast.

    Returns a list of dicts sorted by month, each with keys:
    ``month``, ``month_name``, ``season``, ``adjusted_kg``, ``score``,
    ``grade``, ``delta_pct``.
    """
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    forecast: list[dict[str, Any]] = []
    for m in MONTHS:
        fp = calculate_seasonal_footprint(
            raw_footprint_kg, contributors, m, hemisphere,
        )
        sc = seasonal_eco_score(fp.adjusted_footprint_kg, m, hemisphere)
        forecast.append({
            "month": m,
            "month_name": month_names[m - 1],
            "season": fp.season,
            "adjusted_kg": fp.adjusted_footprint_kg,
            "score": sc["score"],
            "grade": sc["grade"],
            "color": sc["color"],
            "delta_pct": fp.delta_pct,
        })

    return forecast


# ── Streaminglit Integration Helper ────────────────────────────────────────

def render_seasonal_section(
    raw_footprint_kg: float,
    contributors: dict[str, float],
    month: int | None = None,
    hemisphere: str = "northern",
) -> None:
    """Render the seasonal optimizer section inside a Streamlit page.

    This is a convenience wrapper so pages can call a single function.
    Import inside the page to keep app.py dependency-light::

        from seasonal_carbon_optimizer import render_seasonal_section
    """
    import streamlit as st

    if month is None:
        month = datetime.now().month

    report = generate_seasonal_report(
        raw_footprint_kg, contributors, month, hemisphere,
    )

    st.markdown("#### 🌦️ Seasonal Carbon Optimiser")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Season",
        report.season.title(),
        help=f"{report.hemisphere.title()} hemisphere, Month {report.month}",
    )
    col2.metric(
        "Eco Score",
        f"{report.score_data['score']}/100",
        delta=f"Grade {report.score_data['grade']}",
    )
    col3.metric(
        "Adjusted Footprint",
        f"{report.score_data['adjusted_footprint_kg']:.0f} kg",
        delta=f"{report.footprint_result.delta_pct:+.1f}% vs baseline",
        delta_color="inverse",
    )
    col4.metric(
        "Monthly Savings",
        f"{report.monthly_savings_potential_kg:.0f} kg",
        help="Total potential CO₂ savings from all recommendations",
    )

    if report.recommendations:
        st.markdown("**🎯 Seasonal Recommendations**")
        for rec in report.recommendations:
            diff_badge = {
                "easy": "🟢",
                "medium": "🟡",
                "hard": "🔴",
            }.get(rec["difficulty"], "⚪")
            st.markdown(
                f"- {diff_badge} **{rec['action']}** "
                f"(saves ~{rec['impact_kg_year']} kg/year) — {rec['tip']}"
            )

    with st.expander("📊 12-Month Seasonal Forecast", expanded=False):
        forecast = generate_monthly_forecast(
            raw_footprint_kg, contributors, hemisphere,
        )
        try:
            import pandas as pd
            df = pd.DataFrame(forecast)
            st.dataframe(
                df[["month_name", "season", "adjusted_kg", "score", "grade", "delta_pct"]],
                use_container_width=True,
                hide_index=True,
            )
        except ImportError:
            for entry in forecast:
                st.write(
                    f"{entry['month_name']}: {entry['adjusted_kg']:.0f} kg "
                    f"(Score {entry['score']}, {entry['grade']})"
                )

    with st.expander("🗺️ Quarterly Comparison", expanded=False):
        comp = generate_quarterly_comparison(
            raw_footprint_kg, contributors, hemisphere,
        )
        for q_num, q_data in comp.quarters.items():
            st.markdown(
                f"**Q{q_num} ({q_data['season'].title()})**: "
                f"{q_data['adjusted_kg']:.0f} kg CO₂ | "
                f"Score {q_data['score']}/100 ({q_data['grade']}) | "
                f"Δ {q_data['delta_pct']:+.1f}%"
            )
        st.info(
            f"Best quarter: Q{comp.best_quarter} | "
            f"Worst quarter: Q{comp.worst_quarter} | "
            f"Annual adjusted total: {comp.annual_adjusted_kg:.0f} kg"
        )
