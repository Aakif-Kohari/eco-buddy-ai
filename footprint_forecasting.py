"""Footprint Trend Forecasting Engine.

Analyses historical assessment data to detect trends, seasonal patterns,
anomalies, and project future emissions.  Provides actionable insights
on trajectory and forecasted milestones.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional


# ──────────────────────────────────────────────────────────────────────────────
# Data Classes
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class TrendPoint:
    """A single data point in a time series."""
    timestamp: str
    footprint_kg: float
    eco_score: int
    category: Optional[str] = None

@dataclass
class TrendResult:
    """Result of a linear trend analysis."""
    slope_kg_per_day: float
    slope_kg_per_month: float
    direction: str  # "improving", "worsening", "stable"
    r_squared: float
    confidence: str  # "high", "medium", "low"
    summary: str

@dataclass
class SeasonalPattern:
    """Detected seasonal pattern in emissions."""
    period_months: int
    amplitude_kg: float
    peak_month: str
    trough_month: str
    description: str

@dataclass
class Anomaly:
    """A detected anomaly in the assessment history."""
    timestamp: str
    footprint_kg: float
    expected_kg: float
    deviation_kg: float
    severity: str  # "mild", "moderate", "severe"
    direction: str  # "spike" or "dip"
    description: str

@dataclass
class ForecastResult:
    """A single forecast prediction."""
    months_ahead: int
    predicted_kg: float
    confidence_low_kg: float
    confidence_high_kg: float
    trend_basis: str

@dataclass
class MilestonePrediction:
    """Prediction of when a target will be reached."""
    target_kg: float
    months_to_reach: Optional[float]
    date_reached: Optional[str]
    achievable: bool
    description: str

@dataclass
class ForecastReport:
    """Full forecasting report combining all analyses."""
    data_points: int
    date_range: tuple[str, str]
    trend: TrendResult
    seasonal: Optional[SeasonalPattern]
    anomalies: list[Anomaly]
    forecasts: list[ForecastResult]
    milestones: list[MilestonePrediction]
    current_trajectory_kg: float
    generated_at: str


# ──────────────────────────────────────────────────────────────────────────────
# Core Functions
# ──────────────────────────────────────────────────────────────────────────────

def parse_assessment_rows(rows: list[tuple]) -> list[TrendPoint]:
    """Convert raw database assessment rows to TrendPoint objects.

    Expected row format: (id, date, created_at, transport, distance,
    electricity, diet, flights, footprint, eco_score, ...)
    """
    points = []
    for row in rows:
        try:
            footprint = float(row[8]) if row[8] is not None else None
            eco_score = int(row[9]) if row[9] is not None else 0
            ts = str(row[2]) if row[2] else str(row[1])
            if footprint is not None and footprint > 0:
                points.append(TrendPoint(
                    timestamp=ts, footprint_kg=footprint, eco_score=eco_score
                ))
        except (IndexError, ValueError, TypeError):
            continue
    points.sort(key=lambda p: p.timestamp)
    return points


def _timestamp_to_days(timestamp: str) -> float:
    """Convert a timestamp string to a fractional day value for regression."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(timestamp[:19], fmt)
            return (dt - datetime(2000, 1, 1)).total_seconds() / 86400.0
        except ValueError:
            continue
    return 0.0


def _parse_month(timestamp: str) -> int:
    """Extract month (1-12) from a timestamp string."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(timestamp[:19], fmt).month
        except ValueError:
            continue
    return 1


# ──────────────────────────────────────────────────────────────────────────────
# Linear Regression Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _linear_regression(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Simple linear regression. Returns (slope, intercept, r_squared)."""
    n = len(xs)
    if n < 2:
        return 0.0, ys[0] if ys else 0.0, 0.0

    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)
    sum_y2 = sum(y * y for y in ys)

    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-12:
        return 0.0, sum_y / n, 0.0

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n

    # R-squared
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    mean_y = sum_y / n
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return slope, intercept, max(0.0, min(1.0, r_squared))


# ──────────────────────────────────────────────────────────────────────────────
# Trend Analysis
# ──────────────────────────────────────────────────────────────────────────────

def analyse_trend(points: list[TrendPoint]) -> TrendResult:
    """Perform linear regression on footprint history to detect trend.

    Args:
        points: List of TrendPoint objects sorted by timestamp.

    Returns:
        TrendResult with slope, direction, confidence, etc.
    """
    if len(points) < 2:
        return TrendResult(
            slope_kg_per_day=0.0, slope_kg_per_month=0.0,
            direction="stable", r_squared=0.0, confidence="low",
            summary="Insufficient data for trend analysis (need ≥2 assessments)."
        )

    xs = [_timestamp_to_days(p.timestamp) for p in points]
    ys = [p.footprint_kg for p in points]

    slope, intercept, r_squared = _linear_regression(xs, ys)

    slope_per_month = slope * 30.44  # avg days per month

    # Direction classification
    if slope_per_month < -50:
        direction = "improving"
    elif slope_per_month > 50:
        direction = "worsening"
    else:
        direction = "stable"

    # Confidence based on R-squared and data points
    if r_squared >= 0.7 and len(points) >= 6:
        confidence = "high"
    elif r_squared >= 0.4 and len(points) >= 4:
        confidence = "medium"
    else:
        confidence = "low"

    # Summary text
    avg_footprint = sum(ys) / len(ys)
    if direction == "improving":
        summary = (
            f"Your footprint is decreasing by ~{abs(slope_per_month):.0f} kg/month "
            f"(R²={r_squared:.2f}). Keep up the great work!"
        )
    elif direction == "worsening":
        summary = (
            f"Your footprint is increasing by ~{abs(slope_per_month):.0f} kg/month "
            f"(R²={r_squared:.2f}). Consider reviewing your recent changes."
        )
    else:
        summary = (
            f"Your footprint is relatively stable around {avg_footprint:.0f} kg "
            f"(R²={r_squared:.2f})."
        )

    return TrendResult(
        slope_kg_per_day=round(slope, 4),
        slope_kg_per_month=round(slope_per_month, 2),
        direction=direction,
        r_squared=round(r_squared, 4),
        confidence=confidence,
        summary=summary,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Seasonal Pattern Detection
# ──────────────────────────────────────────────────────────────────────────────

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def detect_seasonal_pattern(points: list[TrendPoint]) -> Optional[SeasonalPattern]:
    """Detect if there's a seasonal pattern in emissions by month.

    Requires at least 12 data points spanning multiple months.
    """
    if len(points) < 8:
        return None

    # Group by month
    month_data: dict[int, list[float]] = {}
    for p in points:
        month = _parse_month(p.timestamp)
        month_data.setdefault(month, []).append(p.footprint_kg)

    # Need at least 4 different months with data
    months_with_data = {m for m, vals in month_data.items() if len(vals) >= 1}
    if len(months_with_data) < 4:
        return None

    # Calculate monthly averages
    month_avgs = {}
    for m, vals in month_data.items():
        month_avgs[m] = sum(vals) / len(vals)

    overall_avg = sum(v for v in month_avgs.values()) / len(month_avgs)

    # Find peak and trough
    peak_month = max(month_avgs, key=month_avgs.get)
    trough_month = min(month_avgs, key=month_avgs.get)
    amplitude = (month_avgs[peak_month] - month_avgs[trough_month]) / 2

    # Determine if pattern is significant
    overall_range = max(month_avgs.values()) - min(month_avgs.values())
    if overall_range < overall_avg * 0.1:
        return None  # Not a meaningful seasonal pattern

    return SeasonalPattern(
        period_months=12,
        amplitude_kg=round(amplitude, 1),
        peak_month=MONTH_NAMES[peak_month],
        trough_month=MONTH_NAMES[trough_month],
        description=(
            f"Your emissions peak in {MONTH_NAMES[peak_month]} "
            f"(~{month_avgs[peak_month]:.0f} kg) and dip in "
            f"{MONTH_NAMES[trough_month]} (~{month_avgs[trough_month]:.0f} kg), "
            f"with a seasonal swing of ~{amplitude:.0f} kg."
        ),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Anomaly Detection
# ──────────────────────────────────────────────────────────────────────────────

def detect_anomalies(
    points: list[TrendPoint],
    threshold_std: float = 2.0,
) -> list[Anomaly]:
    """Detect anomalies using z-score on residuals from linear regression.

    An anomaly is a data point that deviates more than `threshold_std`
    standard deviations from the regression line.
    """
    if len(points) < 4:
        return []

    xs = [_timestamp_to_days(p.timestamp) for p in points]
    ys = [p.footprint_kg for p in points]

    slope, intercept, _ = _linear_regression(xs, ys)

    # Calculate residuals
    residuals = [y - (slope * x + intercept) for x, y in zip(xs, ys)]
    mean_res = sum(residuals) / len(residuals)
    std_res = math.sqrt(sum((r - mean_res) ** 2 for r in residuals) / len(residuals))

    if std_res < 1e-6:
        return []

    anomalies = []
    for i, (p, residual) in enumerate(zip(points, residuals)):
        z_score = (residual - mean_res) / std_res
        if abs(z_score) > threshold_std:
            expected = slope * xs[i] + intercept
            deviation = p.footprint_kg - expected

            # Severity classification
            abs_z = abs(z_score)
            if abs_z > 3.5:
                severity = "severe"
            elif abs_z > 2.5:
                severity = "moderate"
            else:
                severity = "mild"

            direction = "spike" if deviation > 0 else "dip"

            if direction == "spike":
                desc = (
                    f"Unusual spike: {p.footprint_kg:.0f} kg vs expected "
                    f"{expected:.0f} kg (+{deviation:.0f} kg)"
                )
            else:
                desc = (
                    f"Notable dip: {p.footprint_kg:.0f} kg vs expected "
                    f"{expected:.0f} kg ({deviation:.0f} kg)"
                )

            anomalies.append(Anomaly(
                timestamp=p.timestamp,
                footprint_kg=p.footprint_kg,
                expected_kg=round(expected, 1),
                deviation_kg=round(deviation, 1),
                severity=severity,
                direction=direction,
                description=desc,
            ))

    return anomalies


# ──────────────────────────────────────────────────────────────────────────────
# Forecasting
# ──────────────────────────────────────────────────────────────────────────────

def project_forecast(
    points: list[TrendPoint],
    months_ahead: list[int] | None = None,
) -> list[ForecastResult]:
    """Project future footprint based on linear trend.

    Args:
        points: Historical trend points.
        months_ahead: List of months to project (default: 3,6,12,24).

    Returns:
        List of ForecastResult objects.
    """
    if months_ahead is None:
        months_ahead = [3, 6, 12, 24]

    if len(points) < 2:
        return [
            ForecastResult(
                months_ahead=m, predicted_kg=0.0,
                confidence_low_kg=0.0, confidence_high_kg=0.0,
                trend_basis="insufficient_data",
            )
            for m in months_ahead
        ]

    xs = [_timestamp_to_days(p.timestamp) for p in points]
    ys = [p.footprint_kg for p in points]

    slope, intercept, r_squared = _linear_regression(xs, ys)

    # Standard error of estimate for confidence intervals
    n = len(xs)
    residuals = [y - (slope * x + intercept) for x, y in zip(xs, ys)]
    se = math.sqrt(sum(r ** 2 for r in residuals) / max(n - 2, 1))

    last_day = xs[-1]
    forecasts = []

    for m in months_ahead:
        future_days = m * 30.44
        predicted = slope * (last_day + future_days) + intercept
        predicted = max(0.0, predicted)

        # Widening confidence interval with time
        t_factor = 1 + m * 0.05  # uncertainty grows with time
        ci_half = 1.96 * se * t_factor

        ci_low = max(0.0, predicted - ci_half)
        ci_high = predicted + ci_half

        basis = "linear_trend" if r_squared > 0.3 else "weak_trend"

        forecasts.append(ForecastResult(
            months_ahead=m,
            predicted_kg=round(predicted, 1),
            confidence_low_kg=round(ci_low, 1),
            confidence_high_kg=round(ci_high, 1),
            trend_basis=basis,
        ))

    return forecasts


def predict_milestones(
    points: list[TrendPoint],
    targets: list[float] | None = None,
) -> list[MilestonePrediction]:
    """Predict when the user will reach specific footprint targets.

    Args:
        points: Historical trend points.
        targets: List of target kg values (defaults to common milestones).

    Returns:
        List of MilestonePrediction objects.
    """
    if targets is None:
        targets = [3000.0, 2000.0, 1000.0, 500.0, 0.0]

    if len(points) < 2:
        return [
            MilestonePrediction(
                target_kg=t, months_to_reach=None, date_reached=None,
                achievable=False, description="Insufficient data for prediction.",
            )
            for t in targets
        ]

    xs = [_timestamp_to_days(p.timestamp) for p in points]
    ys = [p.footprint_kg for p in points]
    slope, intercept, r_squared = _linear_regression(xs, ys)

    current_day = xs[-1]
    current_kg = slope * current_day + intercept
    milestones = []

    for target in targets:
        if slope >= 0 and current_kg > target:
            # Trend is flat or worsening and current > target
            milestones.append(MilestonePrediction(
                target_kg=target, months_to_reach=None, date_reached=None,
                achievable=False,
                description=f"Target {target:.0f} kg is not reachable on current trajectory.",
            ))
            continue

        if current_kg <= target:
            milestones.append(MilestonePrediction(
                target_kg=target, months_to_reach=0.0,
                date_reached=datetime.now().strftime("%Y-%m-%d"),
                achievable=True,
                description=f"Already achieved! Current: {current_kg:.0f} kg.",
            ))
            continue

        # Calculate months to reach target
        kg_to_reduce = current_kg - target
        if abs(slope) < 1e-6:
            months_needed = None
            achievable = False
            desc = "Trend is flat — cannot predict when target will be reached."
        else:
            days_needed = kg_to_reduce / abs(slope)
            months_needed = days_needed / 30.44
            achievable = months_needed <= 60  # Only if within 5 years
            target_date = datetime.now() + timedelta(days=days_needed)
            desc = (
                f"Projected in ~{months_needed:.0f} months "
                f"({target_date.strftime('%b %Y')})"
                if achievable else
                f"Would take ~{months_needed:.0f} months — consider accelerating reductions."
            )
            milestones.append(MilestonePrediction(
                target_kg=target, months_to_reach=round(months_needed, 1),
                date_reached=target_date.strftime("%Y-%m-%d"),
                achievable=achievable, description=desc,
            ))
            continue

        milestones.append(MilestonePrediction(
            target_kg=target, months_to_reach=None, date_reached=None,
            achievable=False, description=desc,
        ))

    return milestones


# ──────────────────────────────────────────────────────────────────────────────
# Trajectory Assessment
# ──────────────────────────────────────────────────────────────────────────────

def assess_trajectory(
    points: list[TrendPoint],
    target_kg: float = 2700.0,
) -> dict[str, Any]:
    """Assess the user's current trajectory against a target.

    Returns a dict with trajectory assessment info.
    """
    if not points:
        return {"status": "no_data", "message": "No assessment data available."}

    current_kg = points[-1].footprint_kg
    diff = current_kg - target_kg
    pct_diff = (diff / target_kg * 100) if target_kg > 0 else 0

    if diff <= 0:
        status = "on_track"
        message = f"On track! Currently at {current_kg:.0f} kg, target is {target_kg:.0f} kg."
    elif diff <= target_kg * 0.2:
        status = "close"
        message = f"Close — {diff:.0f} kg above target ({pct_diff:.0f}% over)."
    elif diff <= target_kg * 0.5:
        status = "behind"
        message = f"Behind — {diff:.0f} kg above target ({pct_diff:.0f}% over)."
    else:
        status = "far_behind"
        message = f"Significantly above target — {diff:.0f} kg to reduce ({pct_diff:.0f}% over)."

    # Average monthly change if enough data
    avg_monthly_change = None
    if len(points) >= 2:
        total_change = points[-1].footprint_kg - points[0].footprint_kg
        days_span = _timestamp_to_days(points[-1].timestamp) - _timestamp_to_days(points[0].timestamp)
        if days_span > 0:
            avg_monthly_change = (total_change / days_span) * 30.44

    return {
        "status": status,
        "message": message,
        "current_kg": round(current_kg, 1),
        "target_kg": target_kg,
        "gap_kg": round(diff, 1),
        "gap_pct": round(pct_diff, 1),
        "avg_monthly_change_kg": round(avg_monthly_change, 2) if avg_monthly_change is not None else None,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Report Builder
# ──────────────────────────────────────────────────────────────────────────────

def build_forecast_report(
    assessment_rows: list[tuple],
    user_id: Optional[int] = None,
) -> ForecastReport:
    """Build a comprehensive forecast report from assessment data.

    This is the main entry point that orchestrates all forecasting
    analyses and returns a single ForecastReport dataclass.
    """
    points = parse_assessment_rows(assessment_rows)

    if not points:
        return ForecastReport(
            data_points=0,
            date_range=("", ""),
            trend=TrendResult(0.0, 0.0, "stable", 0.0, "low", "No data available."),
            seasonal=None,
            anomalies=[],
            forecasts=[],
            milestones=[],
            current_trajectory_kg=0.0,
            generated_at=datetime.utcnow().isoformat(),
        )

    trend = analyse_trend(points)
    seasonal = detect_seasonal_pattern(points)
    anomalies = detect_anomalies(points)
    forecasts = project_forecast(points)
    milestones = predict_milestones(points)

    current = points[-1].footprint_kg

    return ForecastReport(
        data_points=len(points),
        date_range=(points[0].timestamp, points[-1].timestamp),
        trend=trend,
        seasonal=seasonal,
        anomalies=anomalies,
        forecasts=forecasts,
        milestones=milestones,
        current_trajectory_kg=round(current, 1),
        generated_at=datetime.utcnow().isoformat(),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Utility Helpers
# ──────────────────────────────────────────────────────────────────────────────

def trend_arrow(direction: str) -> str:
    """Return an emoji arrow for the trend direction."""
    return {"improving": "📉", "worsening": "📈", "stable": "➡️"}.get(direction, "❓")

def severity_color(severity: str) -> str:
    """Return a hex color for anomaly severity."""
    return {"mild": "#f59e0b", "moderate": "#f97316", "severe": "#ef4444"}.get(severity, "#6b7280")

def confidence_color(confidence: str) -> str:
    """Return a hex color for trend confidence."""
    return {"high": "#22c55e", "medium": "#eab308", "low": "#ef4444"}.get(confidence, "#6b7280")

def format_months(months: Optional[float]) -> str:
    """Format months to a human-readable string."""
    if months is None:
        return "Unknown"
    if months == 0:
        return "Now"
    if months < 1:
        return f"{months * 30:.0f} days"
    if months < 12:
        return f"{months:.0f} months"
    years = months / 12
    return f"{years:.1f} years"
