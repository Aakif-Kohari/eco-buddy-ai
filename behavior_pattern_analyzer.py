"""Sustainability behavior pattern and habit correlation analysis.

The module is intentionally read-only: it normalizes habit-tracker history into
an analysis model, calculates descriptive correlations, and produces evidence-
based insights. Correlation is never presented as causation.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import date, datetime, timedelta
from itertools import combinations
from math import sqrt
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import json
import re

SCHEMA_VERSION = "1.0"
MIN_OBSERVATIONS = 3
DEFAULT_WINDOW_DAYS = 90
MAX_WINDOW_DAYS = 730


@dataclass(frozen=True)
class HabitObservation:
    habit: str
    day: date
    completed: bool = True
    category: Optional[str] = None
    value: float = 1.0


@dataclass(frozen=True)
class HabitStats:
    habit: str
    category: str
    observations: int
    completions: int
    completion_rate: float
    active_days: int
    longest_streak: int
    current_streak: int
    first_day: Optional[str]
    last_day: Optional[str]


@dataclass(frozen=True)
class CorrelationResult:
    left: str
    right: str
    coefficient: float
    observations: int
    direction: str
    strength: str
    p_proxy: Optional[float] = None


@dataclass(frozen=True)
class PatternFinding:
    kind: str
    title: str
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    confidence: str = "low"


@dataclass(frozen=True)
class BehaviorReport:
    schema_version: str
    generated_at: str
    window_start: Optional[str]
    window_end: Optional[str]
    total_observations: int
    habit_stats: List[HabitStats]
    correlations: List[CorrelationResult]
    co_occurrence: Dict[str, Dict[str, int]]
    weekday_rates: Dict[str, Dict[str, float]]
    streak_distribution: Dict[str, Dict[str, float]]
    findings: List[PatternFinding]
    limitations: List[str]


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _to_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _clean_name(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text


def _category_for(habit: str, supplied: Any = None) -> str:
    if supplied:
        return _clean_name(supplied) or "Uncategorized"
    lowered = habit.lower()
    mapping = {
        "transport": ("bike", "walk", "carpool", "transit", "drive", "commute", "bus"),
        "energy": ("light", "energy", "thermostat", "electric", "unplug", "appliance"),
        "food": ("meat", "plant", "food", "meal", "local", "waste day"),
        "waste": ("recycle", "compost", "reusable", "waste", "bag"),
        "water": ("shower", "water", "faucet", "rainwater", "loads"),
    }
    for category, terms in mapping.items():
        if any(term in lowered for term in terms):
            return category.title()
    return "Uncategorized"


def normalize_observations(source: Any) -> List[HabitObservation]:
    """Normalize common HabitTracker data shapes into dated observations.

    Accepted inputs include a list of records, a mapping of habit -> history,
    and the ``HabitTracker.data`` dictionary used by the existing application.
    """
    if source is None:
        return []
    records: List[HabitObservation] = []

    def add(habit: Any, raw: Any, category: Any = None) -> None:
        name = _clean_name(habit)
        if not name:
            return
        if isinstance(raw, Mapping):
            day = _to_date(raw.get("date") or raw.get("day") or raw.get("completed_at"))
            completed = bool(raw.get("completed", raw.get("done", True)))
            value = raw.get("value", raw.get("count", 1))
            cat = raw.get("category", category)
        else:
            day = _to_date(raw)
            completed = True
            value = 1
            cat = category
        if day is None:
            return
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = 1.0
        records.append(HabitObservation(name, day, completed, _category_for(name, cat), numeric))

    if isinstance(source, Mapping):
        history = source.get("history") if "history" in source else None
        if isinstance(history, Mapping):
            for habit, entries in history.items():
                if isinstance(entries, Iterable) and not isinstance(entries, (str, bytes, Mapping)):
                    for entry in entries:
                        add(habit, entry)
                elif entries:
                    add(habit, entries)
        # Also support {habit: [{date: ...}, ...]} directly.
        if history is None:
            for habit, entries in source.items():
                if habit in {"active_habits", "completed_today", "streaks", "best_streaks", "last_completed", "last_active_date"}:
                    continue
                if isinstance(entries, Iterable) and not isinstance(entries, (str, bytes, Mapping)):
                    for entry in entries:
                        add(habit, entry)
        # completed_today is useful when callers provide only a current snapshot.
        today = date.today()
        for habit in source.get("completed_today", []) or []:
            add(habit, today)
    elif isinstance(source, Iterable) and not isinstance(source, (str, bytes)):
        for item in source:
            if isinstance(item, HabitObservation):
                records.append(item)
            elif isinstance(item, Mapping):
                add(item.get("habit") or item.get("name"), item, item.get("category"))
            elif isinstance(item, (tuple, list)) and len(item) >= 2:
                add(item[0], item[1])
    return sorted(records, key=lambda x: (x.day, x.habit))


def filter_window(observations: Sequence[HabitObservation], days: int = DEFAULT_WINDOW_DAYS,
                  end: Optional[date] = None) -> List[HabitObservation]:
    if days <= 0 or days > MAX_WINDOW_DAYS:
        raise ValueError(f"days must be between 1 and {MAX_WINDOW_DAYS}")
    if not observations:
        return []
    end_day = end or max(o.day for o in observations)
    start = end_day - timedelta(days=days - 1)
    return [o for o in observations if start <= o.day <= end_day]


# ---------------------------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------------------------

def _binary_series(observations: Sequence[HabitObservation]) -> Dict[str, Dict[date, float]]:
    series: Dict[str, Dict[date, float]] = {}
    for obs in observations:
        series.setdefault(obs.habit, {})[obs.day] = max(0.0, obs.value) if obs.completed else 0.0
        if obs.completed:
            series[obs.habit][obs.day] = 1.0
    return series


def _streaks(days: Iterable[date]) -> Tuple[int, int]:
    unique = sorted(set(days))
    if not unique:
        return 0, 0
    longest = current = 1
    for previous, current_day in zip(unique, unique[1:]):
        if (current_day - previous).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    today = max(unique)
    tail = 1
    for idx in range(len(unique) - 2, -1, -1):
        if (unique[idx + 1] - unique[idx]).days == 1:
            tail += 1
        else:
            break
    return longest, tail if today >= max(unique) else 0


def habit_statistics(observations: Sequence[HabitObservation]) -> List[HabitStats]:
    grouped: Dict[str, List[HabitObservation]] = {}
    for obs in observations:
        grouped.setdefault(obs.habit, []).append(obs)
    result = []
    for habit, entries in sorted(grouped.items()):
        completed = [e.day for e in entries if e.completed]
        category = next((e.category for e in entries if e.category), "Uncategorized")
        longest, current = _streaks(completed)
        unique_days = len(set(e.day for e in entries))
        result.append(HabitStats(
            habit=habit,
            category=category,
            observations=len(entries),
            completions=len(completed),
            completion_rate=round(100 * len(completed) / len(entries), 2) if entries else 0.0,
            active_days=unique_days,
            longest_streak=longest,
            current_streak=current,
            first_day=min(e.day for e in entries).isoformat() if entries else None,
            last_day=max(e.day for e in entries).isoformat() if entries else None,
        ))
    return result


def _pearson(x: Sequence[float], y: Sequence[float]) -> Optional[float]:
    if len(x) != len(y) or len(x) < MIN_OBSERVATIONS:
        return None
    mx, my = mean(x), mean(y)
    dx = [v - mx for v in x]
    dy = [v - my for v in y]
    denominator = sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    if denominator == 0:
        return None
    return sum(a * b for a, b in zip(dx, dy)) / denominator


def _strength(coef: float) -> str:
    magnitude = abs(coef)
    if magnitude >= 0.8:
        return "very strong"
    if magnitude >= 0.6:
        return "strong"
    if magnitude >= 0.4:
        return "moderate"
    if magnitude >= 0.2:
        return "weak"
    return "very weak"


def _direction(coef: float) -> str:
    if coef > 0.05:
        return "positive"
    if coef < -0.05:
        return "negative"
    return "near-zero"


def correlation_matrix(observations: Sequence[HabitObservation]) -> List[CorrelationResult]:
    series = _binary_series(observations)
    habits = sorted(series)
    all_days = sorted({o.day for o in observations})
    results: List[CorrelationResult] = []
    for left, right in combinations(habits, 2):
        x = [series[left].get(day, 0.0) for day in all_days]
        y = [series[right].get(day, 0.0) for day in all_days]
        coef = _pearson(x, y)
        if coef is None:
            continue
        results.append(CorrelationResult(left, right, round(coef, 4), len(all_days), _direction(coef), _strength(coef)))
    return sorted(results, key=lambda r: (-abs(r.coefficient), r.left, r.right))


def lagged_correlation(observations: Sequence[HabitObservation], left: str, right: str,
                       lag_days: int = 1) -> Optional[CorrelationResult]:
    if not left or not right or lag_days < 0:
        raise ValueError("habit names must be supplied and lag_days must be non-negative")
    series = _binary_series(observations)
    days = sorted({o.day for o in observations})
    x, y = [], []
    for day in days:
        target = day + timedelta(days=lag_days)
        if target in days:
            x.append(series.get(left, {}).get(day, 0.0))
            y.append(series.get(right, {}).get(target, 0.0))
    coef = _pearson(x, y)
    if coef is None:
        return None
    return CorrelationResult(left, right, round(coef, 4), len(x), _direction(coef), _strength(coef))


def co_occurrence(observations: Sequence[HabitObservation]) -> Dict[str, Dict[str, int]]:
    by_day: Dict[date, set] = {}
    for obs in observations:
        if obs.completed:
            by_day.setdefault(obs.day, set()).add(obs.habit)
    habits = sorted({o.habit for o in observations})
    matrix = {h: {other: 0 for other in habits} for h in habits}
    for names in by_day.values():
        for left, right in combinations(sorted(names), 2):
            matrix[left][right] += 1
            matrix[right][left] += 1
        for name in names:
            matrix[name][name] += 1
    return matrix


def weekday_rates(observations: Sequence[HabitObservation]) -> Dict[str, Dict[str, float]]:
    names = sorted({o.habit for o in observations})
    result: Dict[str, Dict[str, float]] = {}
    for name in names:
        entries = [o for o in observations if o.habit == name]
        buckets: Dict[int, List[bool]] = {i: [] for i in range(7)}
        for entry in entries:
            buckets[entry.day.weekday()].append(entry.completed)
        result[name] = {
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][i]: round(100 * mean(v), 2) if v else 0.0
            for i, v in buckets.items()
        }
    return result


def streak_distribution(observations: Sequence[HabitObservation]) -> Dict[str, Dict[str, float]]:
    result: Dict[str, Dict[str, float]] = {}
    for stats in habit_statistics(observations):
        completed = sorted({o.day for o in observations if o.habit == stats.habit and o.completed})
        lengths: List[int] = []
        run = 0
        previous = None
        for day in completed:
            if previous is not None and (day - previous).days == 1:
                run += 1
            else:
                if run:
                    lengths.append(run)
                run = 1
            previous = day
        if run:
            lengths.append(run)
        result[stats.habit] = {
            "count": float(len(lengths)),
            "mean": round(mean(lengths), 2) if lengths else 0.0,
            "median": float(median(lengths)) if lengths else 0.0,
            "max": float(max(lengths)) if lengths else 0.0,
        }
    return result


# ---------------------------------------------------------------------------
# Evidence-based pattern detection
# ---------------------------------------------------------------------------

def detect_patterns(observations: Sequence[HabitObservation],
                     correlations: Optional[Sequence[CorrelationResult]] = None) -> List[PatternFinding]:
    stats = habit_statistics(observations)
    findings: List[PatternFinding] = []
    if not stats:
        return [PatternFinding("empty", "No habit history", "There is not enough recorded behavior to identify patterns.", {}, "low")]
    best = max(stats, key=lambda s: s.completion_rate)
    worst = min(stats, key=lambda s: s.completion_rate)
    if best.completion_rate - worst.completion_rate >= 20:
        findings.append(PatternFinding(
            "completion_gap", "Completion rates differ across habits",
            f"{best.habit} is completed more consistently than {worst.habit} in the observed history.",
            {"highest": best.completion_rate, "lowest": worst.completion_rate, "difference": round(best.completion_rate - worst.completion_rate, 2)},
            "medium"))
    for item in stats:
        if item.longest_streak >= 7:
            findings.append(PatternFinding(
                "streak", f"Sustained streak: {item.habit}",
                f"The habit reached a {item.longest_streak}-day consecutive completion streak.",
                {"longest_streak": item.longest_streak, "completion_rate": item.completion_rate}, "medium"))
    if correlations:
        for corr in correlations[:5]:
            if abs(corr.coefficient) >= 0.4:
                findings.append(PatternFinding(
                    "correlation", f"{corr.strength.title()} {corr.direction} association",
                    f"{corr.left} and {corr.right} tend to co-occur in the observed dates. This is an association, not proof of causation.",
                    {"coefficient": corr.coefficient, "observations": corr.observations},
                    "medium" if corr.observations >= 14 else "low"))
    rates = weekday_rates(observations)
    for habit, by_day in rates.items():
        if by_day:
            high_day = max(by_day, key=by_day.get)
            low_day = min(by_day, key=by_day.get)
            if by_day[high_day] - by_day[low_day] >= 30:
                findings.append(PatternFinding(
                    "weekday", f"Weekday variation: {habit}",
                    f"Completion is highest on {high_day} and lowest on {low_day} in this dataset.",
                    {"highest_day": high_day, "highest_rate": by_day[high_day], "lowest_day": low_day, "lowest_rate": by_day[low_day]}, "low"))
    return findings


def build_report(observations: Any, days: int = DEFAULT_WINDOW_DAYS,
                 end: Optional[date] = None) -> BehaviorReport:
    normalized = filter_window(normalize_observations(observations), days, end)
    correlations = correlation_matrix(normalized)
    if normalized:
        start, finish = min(o.day for o in normalized), max(o.day for o in normalized)
        window_start, window_end = start.isoformat(), finish.isoformat()
    else:
        window_start = window_end = None
    limitations = [
        "Correlation does not establish causation.",
        "Unrecorded days are treated as non-completions only for pairwise date alignment; missing logging can bias results.",
        "Small samples can produce unstable correlations; use more observations before making behavioral decisions.",
        "Habit values are normalized to completion indicators for correlation analysis.",
    ]
    return BehaviorReport(
        schema_version=SCHEMA_VERSION,
        generated_at=datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        window_start=window_start,
        window_end=window_end,
        total_observations=len(normalized),
        habit_stats=habit_statistics(normalized),
        correlations=correlations,
        co_occurrence=co_occurrence(normalized),
        weekday_rates=weekday_rates(normalized),
        streak_distribution=streak_distribution(normalized),
        findings=detect_patterns(normalized, correlations),
        limitations=limitations,
    )


# ---------------------------------------------------------------------------
# Public convenience and serialization APIs
# ---------------------------------------------------------------------------

def top_correlations(report: BehaviorReport, limit: int = 10, minimum: float = 0.2) -> List[CorrelationResult]:
    if limit < 1:
        raise ValueError("limit must be positive")
    return [c for c in report.correlations if abs(c.coefficient) >= minimum][:limit]


def habit_pair_history(observations: Any, left: str, right: str) -> List[Dict[str, Any]]:
    normalized = normalize_observations(observations)
    series = _binary_series(normalized)
    days = sorted({o.day for o in normalized})
    return [{"date": day.isoformat(), left: bool(series.get(left, {}).get(day, 0)), right: bool(series.get(right, {}).get(day, 0))} for day in days]


def summarize_report(report: BehaviorReport) -> Dict[str, Any]:
    stats = report.habit_stats
    return {
        "habits_tracked": len(stats),
        "observations": report.total_observations,
        "best_completion_rate": max((s.completion_rate for s in stats), default=0.0),
        "average_completion_rate": round(mean(s.completion_rate for s in stats), 2) if stats else 0.0,
        "strongest_associations": [asdict(c) for c in top_correlations(report, 3, 0.4)],
        "findings": len(report.findings),
    }


def serialize_report(report: BehaviorReport, pretty: bool = False) -> str:
    payload = asdict(report)
    return json.dumps(payload, indent=2 if pretty else None, sort_keys=True, default=str)


def report_to_dict(report: BehaviorReport) -> Dict[str, Any]:
    return json.loads(serialize_report(report))


def validate_report_payload(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("Unsupported or missing schema_version")
    for field_name in ("habit_stats", "correlations", "findings", "limitations"):
        if field_name not in payload:
            errors.append(f"Missing field: {field_name}")
        elif not isinstance(payload[field_name], list):
            errors.append(f"Field must be a list: {field_name}")
    if payload.get("total_observations", 0) < 0:
        errors.append("total_observations cannot be negative")
    return errors


def export_report(report: BehaviorReport, path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(serialize_report(report, pretty=True))


def analyze_habit_data(source: Any, days: int = DEFAULT_WINDOW_DAYS,
                      end: Optional[date] = None) -> BehaviorReport:
    """Primary entry point for application pages and future integrations."""
    return build_report(source, days=days, end=end)


__all__ = [
    "SCHEMA_VERSION", "MIN_OBSERVATIONS", "HabitObservation", "HabitStats",
    "CorrelationResult", "PatternFinding", "BehaviorReport", "normalize_observations",
    "filter_window", "habit_statistics", "correlation_matrix", "lagged_correlation",
    "co_occurrence", "weekday_rates", "streak_distribution", "detect_patterns",
    "build_report", "top_correlations", "habit_pair_history", "summarize_report",
    "serialize_report", "report_to_dict", "validate_report_payload", "export_report",
    "analyze_habit_data",
]
