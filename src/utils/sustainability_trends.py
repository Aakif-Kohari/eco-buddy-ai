"""Personal Sustainability Benchmark and Trend Analyzer.

Pure analytics layer for EcoBuddy assessment history.  It never rewrites
historical assessments and does not introduce a second emissions taxonomy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from math import isfinite
from statistics import mean, median, pstdev
from typing import Any, Iterable, Mapping, Sequence
import json


DEFAULT_PERIOD_DAYS = {
    "7 days": 7,
    "30 days": 30,
    "90 days": 90,
    "6 months": 183,
    "1 year": 365,
    "All time": None,
}
DEFAULT_MOVING_AVERAGE_WINDOW = 3
DEFAULT_STABLE_CHANGE_PERCENT = 2.0
DEFAULT_SIGNIFICANT_CHANGE_PERCENT = 10.0
SUPPORTED_DIRECTIONS = ("IMPROVING", "STABLE", "WORSENING", "INSUFFICIENT_DATA")


@dataclass(frozen=True)
class AssessmentRecord:
    id: int
    date: datetime
    footprint: float
    eco_score: float | None = None
    transport: str | None = None
    distance: float | None = None
    electricity: float | None = None
    diet: str | None = None
    flights: int | None = None
    factor_version: str | None = None
    user_id: int | None = None
    created_at: datetime | None = None
    trip_id: str | None = None
    categories: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class AssessmentTrend:
    period: str
    starting_footprint: float | None
    ending_footprint: float | None
    absolute_change: float | None
    percentage_change: float | None
    direction: str
    average_footprint: float | None
    median_footprint: float | None
    minimum_footprint: float | None
    maximum_footprint: float | None
    assessment_count: int
    first_assessment_id: int | None = None
    latest_assessment_id: int | None = None


@dataclass(frozen=True)
class CategoryTrend:
    category: str
    starting_value: float | None
    ending_value: float | None
    absolute_change: float | None
    percentage_change: float | None
    direction: str
    average_value: float | None
    minimum_value: float | None
    maximum_value: float | None
    assessment_count: int


@dataclass(frozen=True)
class BenchmarkSnapshot:
    current_footprint: float | None
    historical_average: float | None
    historical_median: float | None
    best_footprint: float | None
    worst_footprint: float | None
    current_vs_average: float | None
    current_vs_best: float | None
    current_vs_worst: float | None
    current_percentile: float | None
    assessment_count: int
    latest_assessment_id: int | None
    best_assessment_id: int | None
    worst_assessment_id: int | None


@dataclass(frozen=True)
class SignificantChange:
    assessment_id: int
    previous_assessment_id: int
    absolute_change: float
    percentage_change: float | None
    direction: str
    magnitude: str


@dataclass(frozen=True)
class PeriodComparison:
    first_period: str
    second_period: str
    first_average: float | None
    second_average: float | None
    absolute_change: float | None
    percentage_change: float | None
    direction: str
    first_count: int
    second_count: int


@dataclass(frozen=True)
class TrendSummary:
    overall: AssessmentTrend
    benchmark: BenchmarkSnapshot
    category_trends: tuple[CategoryTrend, ...]
    moving_average: tuple[float | None, ...]
    significant_changes: tuple[SignificantChange, ...]
    best_period: AssessmentRecord | None
    worst_period: AssessmentRecord | None
    most_improved_category: CategoryTrend | None
    most_worsened_category: CategoryTrend | None


class TrendValidationError(ValueError):
    """Raised when assessment data cannot safely be analyzed."""


def _to_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if value is None:
        raise TrendValidationError("Assessment date is required")
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.strptime(text, "%Y-%m-%d")
        except ValueError as exc:
            raise TrendValidationError(f"Invalid assessment date: {value!r}") from exc


def _finite_number(value: Any, field_name: str, *, allow_none: bool = True) -> float | None:
    if value is None or value == "":
        if allow_none:
            return None
        raise TrendValidationError(f"{field_name} is required")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TrendValidationError(f"{field_name} must be numeric") from exc
    if not isfinite(number):
        raise TrendValidationError(f"{field_name} must be finite")
    return number


def _non_negative(value: Any, field_name: str, *, allow_none: bool = True) -> float | None:
    number = _finite_number(value, field_name, allow_none=allow_none)
    if number is not None and number < 0:
        raise TrendValidationError(f"{field_name} cannot be negative")
    return number


def _mapping_get(raw: Any, key: str, default: Any = None) -> Any:
    if isinstance(raw, Mapping):
        return raw.get(key, default)
    return default


def normalize_assessment(raw: Any, *, index: int = 0) -> AssessmentRecord:
    """Normalize an assessment dict or the repository's 13-column tuple."""
    if isinstance(raw, AssessmentRecord):
        return raw
    if isinstance(raw, Mapping):
        assessment_id = _mapping_get(raw, "id", index + 1)
        date_value = _mapping_get(raw, "date", _mapping_get(raw, "created_at"))
        footprint = _non_negative(_mapping_get(raw, "footprint"), "footprint", allow_none=False)
        eco_score = _finite_number(_mapping_get(raw, "eco_score"), "eco_score")
        categories = _mapping_get(raw, "categories", {}) or {}
        return AssessmentRecord(
            id=int(assessment_id),
            date=_to_datetime(date_value),
            footprint=float(footprint),
            eco_score=eco_score,
            transport=_mapping_get(raw, "transport"),
            distance=_non_negative(_mapping_get(raw, "distance"), "distance"),
            electricity=_non_negative(_mapping_get(raw, "electricity"), "electricity"),
            diet=_mapping_get(raw, "diet"),
            flights=_non_negative(_mapping_get(raw, "flights"), "flights"),
            factor_version=_mapping_get(raw, "factor_version"),
            user_id=int(_mapping_get(raw, "user_id")) if _mapping_get(raw, "user_id") is not None else None,
            created_at=_to_datetime(_mapping_get(raw, "created_at")) if _mapping_get(raw, "created_at") else None,
            trip_id=_mapping_get(raw, "trip_id"),
            categories=_normalize_categories(categories),
        )
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
        values = list(raw)
        if len(values) < 10:
            raise TrendValidationError("Assessment tuple must contain at least 10 columns")
        # Current get_assessments schema: id,user_id,date,created_at,transport,
        # distance,electricity,diet,flights,footprint,eco_score,trip_id,factor_version.
        return AssessmentRecord(
            id=int(values[0]),
            user_id=int(values[1]) if values[1] is not None else None,
            date=_to_datetime(values[2]),
            created_at=_to_datetime(values[3]) if values[3] else None,
            transport=values[4],
            distance=_non_negative(values[5], "distance"),
            electricity=_non_negative(values[6], "electricity"),
            diet=values[7],
            flights=_non_negative(values[8], "flights"),
            footprint=float(_non_negative(values[9], "footprint", allow_none=False)),
            eco_score=_finite_number(values[10], "eco_score") if len(values) > 10 else None,
            trip_id=values[11] if len(values) > 11 else None,
            factor_version=values[12] if len(values) > 12 else None,
        )
    raise TrendValidationError(f"Unsupported assessment type: {type(raw).__name__}")


def _normalize_categories(categories: Mapping[str, Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    for key, value in categories.items():
        if value is None:
            continue
        number = _finite_number(value, f"category {key}")
        if number is not None:
            result[str(key)] = number
    return result


def normalize_assessments(raw_assessments: Iterable[Any]) -> list[AssessmentRecord]:
    """Normalize, validate and deterministically sort assessment history."""
    records = [normalize_assessment(raw, index=i) for i, raw in enumerate(raw_assessments)]
    records.sort(key=lambda item: (item.date, item.id))
    seen: set[int] = set()
    unique: list[AssessmentRecord] = []
    for record in records:
        if record.id in seen:
            continue
        seen.add(record.id)
        unique.append(record)
    return unique


def filter_by_period(
    assessments: Iterable[AssessmentRecord],
    period: str,
    *,
    as_of: datetime | date | None = None,
) -> list[AssessmentRecord]:
    records = list(assessments)
    if period not in DEFAULT_PERIOD_DAYS:
        raise ValueError(f"Unsupported period: {period}")
    days = DEFAULT_PERIOD_DAYS[period]
    if days is None:
        return records
    end = _to_datetime(as_of or datetime.now())
    start = end - timedelta(days=days)
    return [record for record in records if start <= record.date <= end]


def _percentage_change(start: float | None, end: float | None) -> float | None:
    if start is None or end is None:
        return None
    if start == 0:
        if end == 0:
            return 0.0
        return None
    return ((end - start) / abs(start)) * 100.0


def classify_direction(
    percentage_change: float | None,
    *,
    stable_threshold: float = DEFAULT_STABLE_CHANGE_PERCENT,
) -> str:
    if percentage_change is None:
        return "INSUFFICIENT_DATA"
    if abs(percentage_change) <= abs(stable_threshold):
        return "STABLE"
    return "IMPROVING" if percentage_change < 0 else "WORSENING"


def calculate_average_footprint(assessments: Iterable[AssessmentRecord]) -> float | None:
    values = [record.footprint for record in assessments]
    return mean(values) if values else None


def calculate_median_footprint(assessments: Iterable[AssessmentRecord]) -> float | None:
    values = [record.footprint for record in assessments]
    return median(values) if values else None


def calculate_minimum_footprint(assessments: Iterable[AssessmentRecord]) -> float | None:
    values = [record.footprint for record in assessments]
    return min(values) if values else None


def calculate_maximum_footprint(assessments: Iterable[AssessmentRecord]) -> float | None:
    values = [record.footprint for record in assessments]
    return max(values) if values else None


def calculate_change(starting: float | None, ending: float | None) -> float | None:
    if starting is None or ending is None:
        return None
    return ending - starting


def calculate_percentage_change(starting: float | None, ending: float | None) -> float | None:
    return _percentage_change(starting, ending)


def calculate_trend(
    assessments: Iterable[AssessmentRecord],
    *,
    period: str = "All time",
    stable_threshold: float = DEFAULT_STABLE_CHANGE_PERCENT,
) -> AssessmentTrend:
    records = list(assessments)
    if not records:
        return AssessmentTrend(period, None, None, None, None, "INSUFFICIENT_DATA", None, None, None, None, 0)
    start = records[0].footprint
    end = records[-1].footprint
    change = calculate_change(start, end)
    percentage = calculate_percentage_change(start, end)
    return AssessmentTrend(
        period=period,
        starting_footprint=start,
        ending_footprint=end,
        absolute_change=change,
        percentage_change=percentage,
        direction=classify_direction(percentage, stable_threshold=stable_threshold),
        average_footprint=calculate_average_footprint(records),
        median_footprint=calculate_median_footprint(records),
        minimum_footprint=calculate_minimum_footprint(records),
        maximum_footprint=calculate_maximum_footprint(records),
        assessment_count=len(records),
        first_assessment_id=records[0].id,
        latest_assessment_id=records[-1].id,
    )


def _category_value(record: AssessmentRecord, category: str) -> float | None:
    if category in record.categories:
        return record.categories[category]
    aliases = {
        "transportation": "transportation",
        "transport": "transportation",
        "energy": "energy",
        "electricity": "energy",
        "food": "food",
        "diet": "food",
        "flights": "flights",
    }
    normalized = aliases.get(category.lower(), category)
    return record.categories.get(normalized)


def available_categories(assessments: Iterable[AssessmentRecord]) -> tuple[str, ...]:
    categories: set[str] = set()
    for record in assessments:
        categories.update(record.categories.keys())
    return tuple(sorted(categories, key=str.casefold))


def calculate_category_trend(
    assessments: Iterable[AssessmentRecord],
    category: str,
    *,
    stable_threshold: float = DEFAULT_STABLE_CHANGE_PERCENT,
) -> CategoryTrend:
    values = [(record, _category_value(record, category)) for record in assessments]
    values = [(record, value) for record, value in values if value is not None]
    if not values:
        return CategoryTrend(category, None, None, None, None, "INSUFFICIENT_DATA", None, None, None, 0)
    numbers = [value for _, value in values]
    start = numbers[0]
    end = numbers[-1]
    pct = calculate_percentage_change(start, end)
    return CategoryTrend(
        category=category,
        starting_value=start,
        ending_value=end,
        absolute_change=end - start,
        percentage_change=pct,
        direction=classify_direction(pct, stable_threshold=stable_threshold),
        average_value=mean(numbers),
        minimum_value=min(numbers),
        maximum_value=max(numbers),
        assessment_count=len(numbers),
    )


def calculate_category_trends(
    assessments: Iterable[AssessmentRecord],
    categories: Iterable[str] | None = None,
    *,
    stable_threshold: float = DEFAULT_STABLE_CHANGE_PERCENT,
) -> list[CategoryTrend]:
    records = list(assessments)
    names = list(categories) if categories is not None else list(available_categories(records))
    return [calculate_category_trend(records, name, stable_threshold=stable_threshold) for name in names]


def calculate_moving_average(
    assessments: Iterable[AssessmentRecord],
    window: int = DEFAULT_MOVING_AVERAGE_WINDOW,
) -> list[float | None]:
    if window < 1:
        raise ValueError("Moving-average window must be at least 1")
    records = list(assessments)
    result: list[float | None] = []
    for index in range(len(records)):
        if index + 1 < window:
            result.append(None)
            continue
        values = [record.footprint for record in records[index + 1 - window : index + 1]]
        result.append(mean(values))
    return result


def calculate_current_percentile(assessments: Iterable[AssessmentRecord]) -> float | None:
    records = list(assessments)
    if not records:
        return None
    current = records[-1].footprint
    below_or_equal = sum(record.footprint <= current for record in records)
    return (below_or_equal / len(records)) * 100.0


def build_benchmark(assessments: Iterable[AssessmentRecord]) -> BenchmarkSnapshot:
    records = list(assessments)
    if not records:
        return BenchmarkSnapshot(None, None, None, None, None, None, None, None, None, 0, None, None, None)
    current = records[-1].footprint
    best = min(records, key=lambda record: (record.footprint, record.date, record.id))
    worst = max(records, key=lambda record: (record.footprint, record.date, record.id))
    average = calculate_average_footprint(records)
    return BenchmarkSnapshot(
        current_footprint=current,
        historical_average=average,
        historical_median=calculate_median_footprint(records),
        best_footprint=best.footprint,
        worst_footprint=worst.footprint,
        current_vs_average=calculate_percentage_change(average, current),
        current_vs_best=calculate_percentage_change(best.footprint, current),
        current_vs_worst=calculate_percentage_change(worst.footprint, current),
        current_percentile=calculate_current_percentile(records),
        assessment_count=len(records),
        latest_assessment_id=records[-1].id,
        best_assessment_id=best.id,
        worst_assessment_id=worst.id,
    )


def find_best_assessment(assessments: Iterable[AssessmentRecord]) -> AssessmentRecord | None:
    records = list(assessments)
    return min(records, key=lambda record: (record.footprint, record.date, record.id)) if records else None


def find_worst_assessment(assessments: Iterable[AssessmentRecord]) -> AssessmentRecord | None:
    records = list(assessments)
    return max(records, key=lambda record: (record.footprint, record.date, record.id)) if records else None


def detect_significant_changes(
    assessments: Iterable[AssessmentRecord],
    *,
    threshold_percent: float = DEFAULT_SIGNIFICANT_CHANGE_PERCENT,
) -> list[SignificantChange]:
    if threshold_percent < 0:
        raise ValueError("Significant-change threshold cannot be negative")
    records = list(assessments)
    changes: list[SignificantChange] = []
    for previous, current in zip(records, records[1:]):
        pct = calculate_percentage_change(previous.footprint, current.footprint)
        absolute = current.footprint - previous.footprint
        if pct is None or abs(pct) < threshold_percent:
            continue
        magnitude = "MAJOR" if abs(pct) >= threshold_percent * 2 else "SIGNIFICANT"
        changes.append(SignificantChange(
            assessment_id=current.id,
            previous_assessment_id=previous.id,
            absolute_change=absolute,
            percentage_change=pct,
            direction="IMPROVING" if absolute < 0 else "WORSENING",
            magnitude=magnitude,
        ))
    return changes


def compare_periods(
    first: Iterable[AssessmentRecord],
    second: Iterable[AssessmentRecord],
    *,
    first_label: str = "First period",
    second_label: str = "Second period",
    stable_threshold: float = DEFAULT_STABLE_CHANGE_PERCENT,
) -> PeriodComparison:
    first_records = list(first)
    second_records = list(second)
    first_average = calculate_average_footprint(first_records)
    second_average = calculate_average_footprint(second_records)
    pct = calculate_percentage_change(first_average, second_average)
    return PeriodComparison(
        first_period=first_label,
        second_period=second_label,
        first_average=first_average,
        second_average=second_average,
        absolute_change=calculate_change(first_average, second_average),
        percentage_change=pct,
        direction=classify_direction(pct, stable_threshold=stable_threshold),
        first_count=len(first_records),
        second_count=len(second_records),
    )


def compare_named_periods(
    assessments: Iterable[AssessmentRecord],
    first_period: str,
    second_period: str,
    *,
    as_of: datetime | date | None = None,
) -> PeriodComparison:
    records = list(assessments)
    first = filter_by_period(records, first_period, as_of=as_of)
    second = filter_by_period(records, second_period, as_of=as_of)
    return compare_periods(first, second, first_label=first_period, second_label=second_period)


def build_trend_summary(
    assessments: Iterable[Any],
    *,
    period: str = "All time",
    categories: Iterable[str] | None = None,
    moving_average_window: int = DEFAULT_MOVING_AVERAGE_WINDOW,
    significant_change_threshold: float = DEFAULT_SIGNIFICANT_CHANGE_PERCENT,
    stable_threshold: float = DEFAULT_STABLE_CHANGE_PERCENT,
    as_of: datetime | date | None = None,
) -> TrendSummary:
    records = normalize_assessments(assessments)
    scoped = filter_by_period(records, period, as_of=as_of)
    overall = calculate_trend(scoped, period=period, stable_threshold=stable_threshold)
    benchmark = build_benchmark(scoped)
    category_trends = calculate_category_trends(scoped, categories, stable_threshold=stable_threshold)
    category_trends = [item for item in category_trends if item.assessment_count]
    category_trends.sort(key=lambda item: (item.absolute_change if item.absolute_change is not None else 0, item.category.casefold()))
    improved = [item for item in category_trends if item.absolute_change is not None and item.absolute_change < 0]
    worsened = [item for item in category_trends if item.absolute_change is not None and item.absolute_change > 0]
    most_improved = min(improved, key=lambda item: (item.absolute_change, item.category.casefold())) if improved else None
    most_worsened = max(worsened, key=lambda item: (item.absolute_change, item.category.casefold())) if worsened else None
    return TrendSummary(
        overall=overall,
        benchmark=benchmark,
        category_trends=tuple(category_trends),
        moving_average=tuple(calculate_moving_average(scoped, moving_average_window)),
        significant_changes=tuple(detect_significant_changes(scoped, threshold_percent=significant_change_threshold)),
        best_period=find_best_assessment(scoped),
        worst_period=find_worst_assessment(scoped),
        most_improved_category=most_improved,
        most_worsened_category=most_worsened,
    )


def build_period_snapshot(
    assessments: Iterable[Any],
    *,
    period: str,
    as_of: datetime | date | None = None,
) -> AssessmentTrend:
    records = normalize_assessments(assessments)
    scoped = filter_by_period(records, period, as_of=as_of)
    return calculate_trend(scoped, period=period)


def calculate_period_over_period(
    assessments: Iterable[Any],
    *,
    days: int = 30,
    as_of: datetime | date | None = None,
) -> PeriodComparison:
    if days < 1:
        raise ValueError("Comparison period must be positive")
    records = normalize_assessments(assessments)
    end = _to_datetime(as_of or datetime.now())
    current = [r for r in records if end - timedelta(days=days) <= r.date <= end]
    previous_start = end - timedelta(days=days * 2)
    previous = [r for r in records if previous_start <= r.date < end - timedelta(days=days)]
    return compare_periods(previous, current, first_label=f"Previous {days} days", second_label=f"Current {days} days")


def calculate_consistency_score(assessments: Iterable[AssessmentRecord]) -> float | None:
    values = [record.footprint for record in assessments]
    if not values:
        return None
    average = mean(values)
    if average == 0:
        return 100.0
    deviation = pstdev(values) if len(values) > 1 else 0.0
    score = 100.0 - min(100.0, (deviation / average) * 100.0)
    return round(score, 2)


def calculate_improvement_rate(assessments: Iterable[AssessmentRecord]) -> float | None:
    records = list(assessments)
    if len(records) < 2:
        return None
    first, last = records[0], records[-1]
    days = (last.date - first.date).total_seconds() / 86400
    if days <= 0:
        return None
    return (last.footprint - first.footprint) / days


def describe_trend(trend: AssessmentTrend) -> str:
    if trend.direction == "INSUFFICIENT_DATA":
        return "Not enough assessment history to determine a trend."
    if trend.direction == "STABLE":
        return "Your footprint is broadly stable over this period."
    if trend.direction == "IMPROVING":
        return "Your footprint is decreasing over this period."
    return "Your footprint is increasing over this period."


def benchmark_label(benchmark: BenchmarkSnapshot) -> str:
    if benchmark.current_footprint is None:
        return "No assessment history available."
    if benchmark.current_vs_average is None:
        return "Historical average is unavailable."
    if benchmark.current_vs_average < -DEFAULT_STABLE_CHANGE_PERCENT:
        return "Below your historical average."
    if benchmark.current_vs_average > DEFAULT_STABLE_CHANGE_PERCENT:
        return "Above your historical average."
    return "Close to your historical average."


def to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    return value


def serialize_summary(summary: TrendSummary, *, indent: int = 2) -> str:
    return json.dumps(to_jsonable(summary), indent=indent, sort_keys=True)


def serialize_assessments(assessments: Iterable[AssessmentRecord], *, indent: int = 2) -> str:
    return json.dumps(to_jsonable(list(assessments)), indent=indent, sort_keys=True)


def validate_period(period: str) -> str:
    if period not in DEFAULT_PERIOD_DAYS:
        raise ValueError(f"Unsupported period: {period}")
    return period


def available_periods() -> tuple[str, ...]:
    return tuple(DEFAULT_PERIOD_DAYS.keys())


def trend_direction_options() -> tuple[str, ...]:
    return SUPPORTED_DIRECTIONS
