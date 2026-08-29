"""
Sustainability Resource Consumption Forecasting Engine (#1297).

This module provides a deterministic, dependency-light forecasting layer over
EcoBuddy's existing assessment history.  It forecasts the resources already
captured by assessments (travel distance, electricity consumption, flights and
carbon footprint) without mutating assessment data or inventing observations.

The engine intentionally treats an assessment as an observation rather than
assuming that an assessment represents a fixed calendar period.  Forecasts
therefore operate on elapsed days between observations and report the basis of
the forecast, confidence, and data-quality limitations alongside every value.

Supported methods
-----------------
* linear: least-squares trend over the available observations
* moving_average: trailing-window average, useful when a trend is noisy
* exponential: simple exponential smoothing with configurable alpha

A forecast is refused when the input history is insufficient, timestamps are
invalid, or a requested resource is unavailable.  This is preferable to
showing fabricated precision to a user.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import statistics
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping, Sequence


ENGINE_VERSION = "1.0"
DEFAULT_HORIZON = 6
MAX_HORIZON = 60
MIN_LINEAR_POINTS = 2
MIN_CONFIDENCE_POINTS = 3
DEFAULT_WINDOW = 3
DEFAULT_ALPHA = 0.35

RESOURCE_DISTANCE = "distance_km"
RESOURCE_ELECTRICITY = "electricity_kwh"
RESOURCE_FLIGHTS = "flights"
RESOURCE_FOOTPRINT = "footprint_kg_co2e"

RESOURCE_LABELS = {
    RESOURCE_DISTANCE: "Travel distance",
    RESOURCE_ELECTRICITY: "Electricity",
    RESOURCE_FLIGHTS: "Flights",
    RESOURCE_FOOTPRINT: "Carbon footprint",
}

RESOURCE_UNITS = {
    RESOURCE_DISTANCE: "km",
    RESOURCE_ELECTRICITY: "kWh",
    RESOURCE_FLIGHTS: "flights",
    RESOURCE_FOOTPRINT: "kg CO2e",
}

METHOD_LINEAR = "linear"
METHOD_MOVING_AVERAGE = "moving_average"
METHOD_EXPONENTIAL = "exponential"
SUPPORTED_METHODS = (METHOD_LINEAR, METHOD_MOVING_AVERAGE, METHOD_EXPONENTIAL)


class ForecastValidationError(ValueError):
    """Raised when forecast input or configuration is invalid."""


class ForecastUnavailableError(ForecastValidationError):
    """Raised when there is not enough trustworthy history to forecast."""


@dataclass(frozen=True)
class ResourceObservation:
    """One normalized resource observation from an assessment."""

    assessment_id: int
    timestamp: dt.datetime
    distance_km: float | None
    electricity_kwh: float | None
    flights: float | None
    footprint_kg_co2e: float | None
    eco_score: float | None = None
    source: str = "assessment"

    def value_for(self, resource: str) -> float | None:
        """Return the normalized numeric value for a supported resource."""
        if resource not in RESOURCE_LABELS:
            raise ForecastValidationError(f"Unsupported resource: {resource}")
        return getattr(self, resource)


@dataclass(frozen=True)
class ForecastPoint:
    """One projected point with transparent uncertainty metadata."""

    period: int
    target_date: str
    value: float
    lower: float | None
    upper: float | None


@dataclass(frozen=True)
class ForecastResult:
    """Complete forecast result for one resource and method."""

    resource: str
    label: str
    unit: str
    method: str
    horizon: int
    generated_at: str
    data_points: int
    first_observation: str
    last_observation: str
    forecast: tuple[ForecastPoint, ...]
    baseline: float
    end_value: float
    change_absolute: float
    change_percent: float | None
    confidence_level: float
    residual_std: float | None
    quality: str
    limitations: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""
        data = asdict(self)
        data["forecast"] = [asdict(point) for point in self.forecast]
        data["limitations"] = list(self.limitations)
        return data


@dataclass(frozen=True)
class ForecastComparison:
    """Comparison between two forecast methods for one resource."""

    resource: str
    methods: tuple[str, ...]
    end_values: dict[str, float]
    spread: float
    agreement: str


@dataclass(frozen=True)
class ForecastReport:
    """Dashboard-ready report containing observations and forecasts."""

    user_id: int
    generated_at: str
    horizon: int
    method: str
    observations: tuple[ResourceObservation, ...]
    results: tuple[ForecastResult, ...]
    unavailable: dict[str, str]
    engine_version: str = ENGINE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_version": self.engine_version,
            "user_id": self.user_id,
            "generated_at": self.generated_at,
            "horizon": self.horizon,
            "method": self.method,
            "observations": [asdict(item) for item in self.observations],
            "results": [item.to_dict() for item in self.results],
            "unavailable": dict(self.unavailable),
        }


# ---------------------------------------------------------------------------
# Validation and normalization
# ---------------------------------------------------------------------------


def _finite_number(value: Any, field_name: str) -> float | None:
    """Normalize nullable numeric values and reject non-finite numbers."""
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ForecastValidationError(f"{field_name} must be numeric") from exc
    if not math.isfinite(number):
        raise ForecastValidationError(f"{field_name} must be finite")
    return number


def _parse_datetime(value: Any, field_name: str = "timestamp") -> dt.datetime:
    """Parse SQLite timestamps, ISO timestamps, dates, and datetimes."""
    if isinstance(value, dt.datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, dt.date):
        return dt.datetime.combine(value, dt.time.min)
    if value is None:
        raise ForecastValidationError(f"{field_name} is required")
    text = str(value).strip()
    if not text:
        raise ForecastValidationError(f"{field_name} is required")
    text = text.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError as exc:
        raise ForecastValidationError(
            f"{field_name} must be an ISO-8601 timestamp: {value!r}"
        ) from exc
    return parsed.replace(tzinfo=None)


def _row_value(row: Any, index: int, key: str) -> Any:
    """Read either the repository's assessment tuple or a mapping."""
    if isinstance(row, Mapping):
        return row.get(key)
    try:
        return row[index]
    except (IndexError, KeyError, TypeError):
        return None


def normalize_assessment(row: Any) -> ResourceObservation:
    """Convert an assessment tuple/dict into a normalized observation."""
    assessment_id = _row_value(row, 0, "id")
    if assessment_id is None:
        raise ForecastValidationError("assessment id is required")
    try:
        assessment_id = int(assessment_id)
    except (TypeError, ValueError) as exc:
        raise ForecastValidationError("assessment id must be an integer") from exc

    timestamp = _row_value(row, 1, "date")
    if timestamp is None:
        timestamp = _row_value(row, 2, "created_at")

    return ResourceObservation(
        assessment_id=assessment_id,
        timestamp=_parse_datetime(timestamp),
        distance_km=_finite_number(_row_value(row, 4, "distance"), "distance"),
        electricity_kwh=_finite_number(
            _row_value(row, 5, "electricity"), "electricity"
        ),
        flights=_finite_number(_row_value(row, 7, "flights"), "flights"),
        footprint_kg_co2e=_finite_number(
            _row_value(row, 8, "footprint"), "footprint"
        ),
        eco_score=_finite_number(_row_value(row, 9, "eco_score"), "eco_score"),
    )


def normalize_assessments(rows: Iterable[Any]) -> list[ResourceObservation]:
    """Normalize, de-duplicate, and chronologically sort assessments."""
    normalized: list[ResourceObservation] = []
    seen: set[int] = set()
    for row in rows:
        observation = normalize_assessment(row)
        if observation.assessment_id in seen:
            continue
        seen.add(observation.assessment_id)
        normalized.append(observation)
    normalized.sort(key=lambda item: (item.timestamp, item.assessment_id))
    return normalized


def validate_resource(resource: str) -> str:
    resource = str(resource).strip()
    if resource not in RESOURCE_LABELS:
        raise ForecastValidationError(f"Unsupported resource: {resource}")
    return resource


def validate_horizon(horizon: int) -> int:
    try:
        value = int(horizon)
    except (TypeError, ValueError) as exc:
        raise ForecastValidationError("horizon must be an integer") from exc
    if value < 1 or value > MAX_HORIZON:
        raise ForecastValidationError(f"horizon must be between 1 and {MAX_HORIZON}")
    return value


def validate_method(method: str) -> str:
    method = str(method).strip().lower()
    if method not in SUPPORTED_METHODS:
        raise ForecastValidationError(
            f"Unsupported method {method!r}; choose from {', '.join(SUPPORTED_METHODS)}"
        )
    return method


def validate_alpha(alpha: float) -> float:
    try:
        value = float(alpha)
    except (TypeError, ValueError) as exc:
        raise ForecastValidationError("alpha must be numeric") from exc
    if not 0 < value <= 1:
        raise ForecastValidationError("alpha must be greater than 0 and at most 1")
    return value


def validate_window(window: int) -> int:
    try:
        value = int(window)
    except (TypeError, ValueError) as exc:
        raise ForecastValidationError("window must be an integer") from exc
    if value < 1:
        raise ForecastValidationError("window must be at least 1")
    return value


# ---------------------------------------------------------------------------
# History loading and resource extraction
# ---------------------------------------------------------------------------


def load_user_observations(user_id: int, rows: Iterable[Any] | None = None) -> list[ResourceObservation]:
    """Load and normalize a user's assessment history."""
    if user_id is None:
        raise ForecastValidationError("user_id is required")
    try:
        normalized_user_id = int(user_id)
    except (TypeError, ValueError) as exc:
        raise ForecastValidationError("user_id must be an integer") from exc
    if normalized_user_id < 1:
        raise ForecastValidationError("user_id must be positive")
    if rows is None:
        # Keep database import lazy so the pure forecasting engine remains
        # importable in validation tools even when an unrelated legacy module
        # has a syntax/configuration problem.
        from database import get_assessments
        source = get_assessments(normalized_user_id)
    else:
        source = rows
    return normalize_assessments(source)


def resource_series(
    observations: Sequence[ResourceObservation], resource: str
) -> list[tuple[dt.datetime, float]]:
    """Return timestamp/value pairs for observations containing a resource."""
    resource = validate_resource(resource)
    series: list[tuple[dt.datetime, float]] = []
    for observation in observations:
        value = observation.value_for(resource)
        if value is None:
            continue
        if value < 0:
            raise ForecastValidationError(
                f"{RESOURCE_LABELS[resource]} contains a negative value in assessment "
                f"{observation.assessment_id}"
            )
        series.append((observation.timestamp, value))
    return series


def available_resources(observations: Sequence[ResourceObservation]) -> dict[str, int]:
    """Count observations available for each resource."""
    return {
        resource: len(resource_series(observations, resource))
        for resource in RESOURCE_LABELS
    }


def describe_data_quality(
    observations: Sequence[ResourceObservation], resource: str
) -> dict[str, Any]:
    """Summarize data sufficiency and gaps before forecasting."""
    resource = validate_resource(resource)
    series = resource_series(observations, resource)
    if not series:
        return {
            "resource": resource,
            "observations": 0,
            "quality": "unavailable",
            "message": "No observations are available for this resource.",
        }
    dates = [item[0] for item in series]
    gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
    quality = "high" if len(series) >= 6 else "medium" if len(series) >= 3 else "low"
    return {
        "resource": resource,
        "observations": len(series),
        "quality": quality,
        "first_date": dates[0].isoformat(),
        "last_date": dates[-1].isoformat(),
        "median_gap_days": statistics.median(gaps) if gaps else None,
        "max_gap_days": max(gaps) if gaps else 0,
        "message": (
            "Forecast quality improves with more regularly spaced observations."
            if len(series) < 6
            else "Sufficient history for a more stable trend estimate."
        ),
    }


# ---------------------------------------------------------------------------
# Forecast mathematics
# ---------------------------------------------------------------------------


def _days_from_start(dates: Sequence[dt.datetime]) -> list[float]:
    start = dates[0]
    return [(date - start).total_seconds() / 86400.0 for date in dates]


def _linear_fit(values: Sequence[float], x: Sequence[float]) -> tuple[float, float, list[float]]:
    """Return slope, intercept, and fitted values for least-squares regression."""
    if len(values) != len(x) or len(values) < 2:
        raise ForecastUnavailableError("At least two observations are required")
    mean_x = statistics.fmean(x)
    mean_y = statistics.fmean(values)
    denominator = sum((item - mean_x) ** 2 for item in x)
    if denominator <= 0:
        raise ForecastUnavailableError("Observation dates must not all be identical")
    slope = sum((xv - mean_x) * (yv - mean_y) for xv, yv in zip(x, values)) / denominator
    intercept = mean_y - slope * mean_x
    fitted = [intercept + slope * item for item in x]
    return slope, intercept, fitted


def _residual_std(values: Sequence[float], fitted: Sequence[float]) -> float | None:
    """Estimate residual standard deviation without overclaiming precision."""
    if len(values) < 3:
        return None
    residuals = [actual - predicted for actual, predicted in zip(values, fitted)]
    return math.sqrt(sum(residual * residual for residual in residuals) / (len(residuals) - 2))


def _confidence_bounds(value: float, residual_std: float | None, level: float) -> tuple[float | None, float | None]:
    if residual_std is None:
        return None, None
    # Conservative normal approximation. The result is explicitly described
    # as an uncertainty band rather than a statistical guarantee.
    z = 1.645 if level >= 0.90 else 1.282
    margin = z * residual_std
    return max(0.0, value - margin), max(0.0, value + margin)


def linear_forecast(
    series: Sequence[tuple[dt.datetime, float]], horizon: int
) -> tuple[list[float], float | None]:
    """Forecast using a time-aware least-squares linear trend."""
    if len(series) < MIN_LINEAR_POINTS:
        raise ForecastUnavailableError("Linear forecasting needs at least two observations")
    horizon = validate_horizon(horizon)
    dates = [item[0] for item in series]
    values = [item[1] for item in series]
    x = _days_from_start(dates)
    slope, intercept, fitted = _linear_fit(values, x)
    last_x = x[-1]
    interval = statistics.median([x[i] - x[i - 1] for i in range(1, len(x))]) if len(x) > 1 else 30.0
    interval = max(interval, 1.0)
    predictions = [max(0.0, intercept + slope * (last_x + interval * step)) for step in range(1, horizon + 1)]
    return predictions, _residual_std(values, fitted)


def moving_average_forecast(
    series: Sequence[tuple[dt.datetime, float]], horizon: int, window: int = DEFAULT_WINDOW
) -> tuple[list[float], float | None]:
    """Forecast using a recursive trailing moving average."""
    if not series:
        raise ForecastUnavailableError("Moving-average forecasting needs observations")
    horizon = validate_horizon(horizon)
    window = min(validate_window(window), len(series))
    history = [value for _, value in series]
    predictions: list[float] = []
    for _ in range(horizon):
        value = statistics.fmean(history[-window:])
        value = max(0.0, value)
        predictions.append(value)
        history.append(value)
    residuals = []
    if len(series) > window:
        for index in range(window, len(series)):
            predicted = statistics.fmean(history[index - window:index])
            residuals.append(series[index][1] - predicted)
    residual_std = statistics.stdev(residuals) if len(residuals) >= 2 else None
    return predictions, residual_std


def exponential_forecast(
    series: Sequence[tuple[dt.datetime, float]], horizon: int, alpha: float = DEFAULT_ALPHA
) -> tuple[list[float], float | None]:
    """Forecast using simple exponential smoothing."""
    if not series:
        raise ForecastUnavailableError("Exponential forecasting needs observations")
    horizon = validate_horizon(horizon)
    alpha = validate_alpha(alpha)
    level = series[0][1]
    fitted: list[float] = [level]
    residuals: list[float] = []
    for _, value in series[1:]:
        residuals.append(value - level)
        level = alpha * value + (1 - alpha) * level
        fitted.append(level)
    predictions = [max(0.0, level) for _ in range(horizon)]
    residual_std = statistics.stdev(residuals) if len(residuals) >= 2 else None
    return predictions, residual_std


def forecast_values(
    series: Sequence[tuple[dt.datetime, float]],
    horizon: int,
    method: str = METHOD_LINEAR,
    *,
    window: int = DEFAULT_WINDOW,
    alpha: float = DEFAULT_ALPHA,
) -> tuple[list[float], float | None]:
    """Dispatch to a supported forecast method."""
    method = validate_method(method)
    if method == METHOD_LINEAR:
        return linear_forecast(series, horizon)
    if method == METHOD_MOVING_AVERAGE:
        return moving_average_forecast(series, horizon, window)
    return exponential_forecast(series, horizon, alpha)


def forecast_dates(
    series: Sequence[tuple[dt.datetime, float]], horizon: int
) -> list[dt.datetime]:
    """Generate future dates using the median observed interval."""
    if not series:
        raise ForecastUnavailableError("Cannot generate dates without observations")
    horizon = validate_horizon(horizon)
    dates = [item[0] for item in series]
    if len(dates) > 1:
        gaps = [(dates[i] - dates[i - 1]).total_seconds() for i in range(1, len(dates))]
        interval_seconds = max(statistics.median(gaps), 86400.0)
    else:
        interval_seconds = 30.0 * 86400.0
    last = dates[-1]
    return [last + dt.timedelta(seconds=interval_seconds * step) for step in range(1, horizon + 1)]


# ---------------------------------------------------------------------------
# Result construction and comparisons
# ---------------------------------------------------------------------------


def _quality_for_count(count: int, residual_std: float | None) -> tuple[str, list[str]]:
    limitations: list[str] = []
    if count < 3:
        limitations.append("Fewer than three observations are available; uncertainty bands are omitted.")
        return "low", limitations
    if count < 6:
        limitations.append("Forecast is based on a short history and may be sensitive to individual assessments.")
        return "medium", limitations
    if residual_std is not None and residual_std > 0:
        return "high", limitations
    limitations.append("Observed history has little variation; treat a flat forecast as a baseline, not a guarantee.")
    return "high", limitations


def build_forecast_result(
    observations: Sequence[ResourceObservation],
    resource: str,
    horizon: int,
    method: str = METHOD_LINEAR,
    *,
    window: int = DEFAULT_WINDOW,
    alpha: float = DEFAULT_ALPHA,
    confidence_level: float = 0.90,
    generated_at: dt.datetime | None = None,
) -> ForecastResult:
    """Build a fully described forecast result for one resource."""
    resource = validate_resource(resource)
    horizon = validate_horizon(horizon)
    method = validate_method(method)
    series = resource_series(observations, resource)
    if not series:
        raise ForecastUnavailableError(f"No {RESOURCE_LABELS[resource].lower()} observations are available")
    if not 0.80 <= confidence_level <= 0.99:
        raise ForecastValidationError("confidence_level must be between 0.80 and 0.99")
    values, residual_std = forecast_values(series, horizon, method, window=window, alpha=alpha)
    dates = forecast_dates(series, horizon)
    lower_upper = [_confidence_bounds(value, residual_std, confidence_level) for value in values]
    points = tuple(
        ForecastPoint(
            period=index + 1,
            target_date=target_date.date().isoformat(),
            value=round(value, 4),
            lower=None if bounds[0] is None else round(bounds[0], 4),
            upper=None if bounds[1] is None else round(bounds[1], 4),
        )
        for index, (target_date, value, bounds) in enumerate(zip(dates, values, lower_upper))
    )
    baseline = series[-1][1]
    end_value = points[-1].value
    change = end_value - baseline
    change_pct = None if baseline == 0 else (change / baseline) * 100.0
    quality, limitations = _quality_for_count(len(series), residual_std)
    if len(series) < MIN_CONFIDENCE_POINTS:
        residual_std = None
    return ForecastResult(
        resource=resource,
        label=RESOURCE_LABELS[resource],
        unit=RESOURCE_UNITS[resource],
        method=method,
        horizon=horizon,
        generated_at=(generated_at or dt.datetime.now(dt.timezone.utc)).isoformat(),
        data_points=len(series),
        first_observation=series[0][0].isoformat(),
        last_observation=series[-1][0].isoformat(),
        forecast=points,
        baseline=round(baseline, 4),
        end_value=round(end_value, 4),
        change_absolute=round(change, 4),
        change_percent=None if change_pct is None else round(change_pct, 2),
        confidence_level=confidence_level,
        residual_std=None if residual_std is None else round(residual_std, 4),
        quality=quality,
        limitations=tuple(limitations),
    )


def compare_forecasts(results: Sequence[ForecastResult]) -> ForecastComparison:
    """Compare the terminal values of multiple forecasts for one resource."""
    if not results:
        raise ForecastValidationError("At least one forecast is required")
    resources = {result.resource for result in results}
    if len(resources) != 1:
        raise ForecastValidationError("All forecasts must target the same resource")
    end_values = {result.method: result.end_value for result in results}
    values = list(end_values.values())
    spread = max(values) - min(values) if values else 0.0
    relative = spread / max(abs(statistics.fmean(values)), 1.0)
    agreement = "high" if relative <= 0.05 else "moderate" if relative <= 0.15 else "low"
    return ForecastComparison(
        resource=results[0].resource,
        methods=tuple(end_values),
        end_values=end_values,
        spread=round(spread, 4),
        agreement=agreement,
    )


def forecast_resource(
    observations: Sequence[ResourceObservation],
    resource: str,
    horizon: int = DEFAULT_HORIZON,
    method: str = METHOD_LINEAR,
    **kwargs: Any,
) -> ForecastResult:
    """Public convenience wrapper for one resource."""
    return build_forecast_result(observations, resource, horizon, method, **kwargs)


def forecast_all_resources(
    observations: Sequence[ResourceObservation],
    horizon: int = DEFAULT_HORIZON,
    method: str = METHOD_LINEAR,
    **kwargs: Any,
) -> tuple[list[ForecastResult], dict[str, str]]:
    """Forecast every supported resource and explain unavailable resources."""
    results: list[ForecastResult] = []
    unavailable: dict[str, str] = {}
    for resource in RESOURCE_LABELS:
        try:
            results.append(
                build_forecast_result(observations, resource, horizon, method, **kwargs)
            )
        except ForecastUnavailableError as exc:
            unavailable[resource] = str(exc)
    return results, unavailable


def build_forecast_report(
    user_id: int,
    observations: Sequence[ResourceObservation],
    horizon: int = DEFAULT_HORIZON,
    method: str = METHOD_LINEAR,
    **kwargs: Any,
) -> ForecastReport:
    """Create a dashboard/report payload without changing persisted data."""
    horizon = validate_horizon(horizon)
    method = validate_method(method)
    results, unavailable = forecast_all_resources(observations, horizon, method, **kwargs)
    return ForecastReport(
        user_id=int(user_id),
        generated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        horizon=horizon,
        method=method,
        observations=tuple(observations),
        results=tuple(results),
        unavailable=unavailable,
    )


def generate_scenario(
    result: ForecastResult,
    multiplier: float,
    label: str | None = None,
) -> ForecastResult:
    """Apply a transparent planning multiplier to a forecast, not to history."""
    try:
        multiplier = float(multiplier)
    except (TypeError, ValueError) as exc:
        raise ForecastValidationError("multiplier must be numeric") from exc
    if not math.isfinite(multiplier) or multiplier < 0:
        raise ForecastValidationError("multiplier must be a finite non-negative number")
    points = tuple(
        ForecastPoint(
            period=point.period,
            target_date=point.target_date,
            value=round(point.value * multiplier, 4),
            lower=None if point.lower is None else round(point.lower * multiplier, 4),
            upper=None if point.upper is None else round(point.upper * multiplier, 4),
        )
        for point in result.forecast
    )
    end_value = points[-1].value if points else result.end_value * multiplier
    baseline = result.baseline * multiplier
    change = end_value - baseline
    change_pct = None if baseline == 0 else change / baseline * 100.0
    limitations = list(result.limitations)
    limitations.append(label or f"Planning scenario applies a {multiplier:.2f}x multiplier; it is not a forecast of behavior.")
    return ForecastResult(
        resource=result.resource,
        label=result.label,
        unit=result.unit,
        method=f"{result.method}:scenario",
        horizon=result.horizon,
        generated_at=result.generated_at,
        data_points=result.data_points,
        first_observation=result.first_observation,
        last_observation=result.last_observation,
        forecast=points,
        baseline=round(baseline, 4),
        end_value=round(end_value, 4),
        change_absolute=round(change, 4),
        change_percent=None if change_pct is None else round(change_pct, 2),
        confidence_level=result.confidence_level,
        residual_std=None if result.residual_std is None else round(result.residual_std * multiplier, 4),
        quality=result.quality,
        limitations=tuple(limitations),
    )


def serialize_report(report: ForecastReport, *, indent: int = 2) -> str:
    """Serialize a report for download or API consumption."""
    return json.dumps(report.to_dict(), indent=indent, default=str, sort_keys=True)


def forecast_from_rows(
    user_id: int,
    rows: Iterable[Any],
    horizon: int = DEFAULT_HORIZON,
    method: str = METHOD_LINEAR,
    **kwargs: Any,
) -> ForecastReport:
    """Build a report from supplied rows, useful for tests and integrations."""
    observations = normalize_assessments(rows)
    return build_forecast_report(user_id, observations, horizon, method, **kwargs)


def trend_direction(result: ForecastResult, tolerance_percent: float = 1.0) -> str:
    """Classify the projected terminal change."""
    if result.change_percent is None:
        return "stable"
    if abs(result.change_percent) <= tolerance_percent:
        return "stable"
    return "increasing" if result.change_percent > 0 else "decreasing"


def format_change(result: ForecastResult) -> str:
    """Produce a concise user-facing change description."""
    direction = trend_direction(result)
    if result.change_percent is None:
        return f"{direction.title()} from {result.baseline:g} {result.unit}"
    sign = "+" if result.change_absolute > 0 else ""
    return f"{sign}{result.change_absolute:g} {result.unit} ({sign}{result.change_percent:.1f}%)"


def explain_forecast(result: ForecastResult) -> list[str]:
    """Return plain-language reasons and caveats for a forecast."""
    explanations = [
        f"Method: {result.method} using {result.data_points} historical observations.",
        f"Latest observed value: {result.baseline:g} {result.unit}.",
        f"Projected value after {result.horizon} periods: {result.end_value:g} {result.unit}.",
    ]
    if result.residual_std is not None:
        explanations.append(
            f"Approximate historical residual spread: {result.residual_std:g} {result.unit}."
        )
    explanations.extend(result.limitations)
    return explanations


__all__ = [
    "ENGINE_VERSION",
    "RESOURCE_DISTANCE",
    "RESOURCE_ELECTRICITY",
    "RESOURCE_FLIGHTS",
    "RESOURCE_FOOTPRINT",
    "RESOURCE_LABELS",
    "RESOURCE_UNITS",
    "METHOD_LINEAR",
    "METHOD_MOVING_AVERAGE",
    "METHOD_EXPONENTIAL",
    "SUPPORTED_METHODS",
    "ForecastValidationError",
    "ForecastUnavailableError",
    "ResourceObservation",
    "ForecastPoint",
    "ForecastResult",
    "ForecastComparison",
    "ForecastReport",
    "normalize_assessment",
    "normalize_assessments",
    "load_user_observations",
    "resource_series",
    "available_resources",
    "describe_data_quality",
    "linear_forecast",
    "moving_average_forecast",
    "exponential_forecast",
    "forecast_values",
    "forecast_dates",
    "build_forecast_result",
    "compare_forecasts",
    "forecast_resource",
    "forecast_all_resources",
    "build_forecast_report",
    "generate_scenario",
    "serialize_report",
    "forecast_from_rows",
    "trend_direction",
    "format_change",
    "explain_forecast",
]
