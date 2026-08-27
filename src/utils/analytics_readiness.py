"""Sustainability analytics readiness and evidence-confidence engine.

This module is intentionally read-only with respect to source sustainability
records.  It converts assessment/history-like records into evidence profiles,
evaluates whether common analytics are supportable, and explains confidence
limitations without inventing data.

The public API accepts plain Python mappings/lists so it can be used with the
project's existing SQLite/data-access layer without introducing a second
persistence model.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from hashlib import sha256
import json
import math
import sqlite3
from typing import Any, Iterable, Mapping, Sequence


ENGINE_VERSION = "1.0"
RELIABLE = "RELIABLE"
LIMITED = "LIMITED"
INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
UNKNOWN = "UNKNOWN"

SEVERITY_CRITICAL = "critical"
SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

DEFAULT_REQUIREMENTS = {
    "trend": {"min_records": 3, "min_span_days": 14, "min_quality": 0.70},
    "comparison": {"min_records": 2, "min_span_days": 7, "min_quality": 0.65},
    "forecast": {"min_records": 6, "min_span_days": 30, "min_quality": 0.80},
    "recommendation": {"min_records": 2, "min_span_days": 7, "min_quality": 0.60},
    "benchmark": {"min_records": 3, "min_span_days": 14, "min_quality": 0.70},
}

CATEGORY_ALIASES = {
    "transport": "Transportation",
    "transportation": "Transportation",
    "energy": "Energy",
    "electricity": "Energy",
    "food": "Food",
    "diet": "Food",
    "water": "Water",
    "waste": "Waste",
    "shopping": "Shopping",
    "lifestyle": "General lifestyle",
    "general": "General lifestyle",
}

DATE_FIELDS = ("date", "assessment_date", "created_at", "timestamp", "recorded_at", "completed_at")
VALUE_FIELDS = ("value", "footprint", "score", "total", "amount", "emissions", "carbon_footprint")
CATEGORY_FIELDS = ("category", "area", "domain", "metric_category")
ID_FIELDS = ("id", "assessment_id", "record_id", "uuid")


class ReadinessError(ValueError):
    """Raised for invalid engine input."""


@dataclass(frozen=True)
class EvidenceRecord:
    record_id: str
    date: date | None
    category: str
    metric: str
    value: float | None
    unit: str
    source: str
    completeness: float
    consistency: float
    recency: float
    validity: float
    user_id: str | None = None
    duplicate: bool = False
    missing_fields: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def quality(self) -> float:
        return round(
            max(0.0, min(1.0, (
                self.completeness * 0.30
                + self.consistency * 0.25
                + self.recency * 0.15
                + self.validity * 0.30
            ))),
            4,
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["date"] = self.date.isoformat() if self.date else None
        result["quality"] = self.quality
        result["missing_fields"] = list(self.missing_fields)
        return result


@dataclass(frozen=True)
class EvidenceIssue:
    code: str
    severity: str
    message: str
    record_ids: tuple[str, ...] = ()
    category: str | None = None
    recommendation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "record_ids": list(self.record_ids),
            "category": self.category,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class AnalyticsReadiness:
    analysis_type: str
    status: str
    confidence: float
    record_count: int
    unique_dates: int
    span_days: int
    quality: float
    missingness: float
    reasons: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {
            "reasons": list(self.reasons),
            "blockers": list(self.blockers),
            "recommendations": list(self.recommendations),
        }


@dataclass(frozen=True)
class CategoryEvidence:
    category: str
    record_count: int
    unique_dates: int
    span_days: int
    quality: float
    confidence: float
    status: str
    missingness: float
    latest_date: str | None
    issues: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"issues": list(self.issues)}


@dataclass
class ReadinessReport:
    generated_at: str
    engine_version: str
    status: str
    confidence: float
    records: list[EvidenceRecord]
    issues: list[EvidenceIssue]
    analyses: dict[str, AnalyticsReadiness]
    categories: list[CategoryEvidence]
    summary: dict[str, Any]
    user_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "engine_version": self.engine_version,
            "status": self.status,
            "confidence": self.confidence,
            "user_id": self.user_id,
            "records": [x.to_dict() for x in self.records],
            "issues": [x.to_dict() for x in self.issues],
            "analyses": {k: v.to_dict() for k, v in self.analyses.items()},
            "categories": [x.to_dict() for x in self.categories],
            "summary": self.summary,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, default=str)


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    for candidate in (raw, raw.replace("Z", "+00:00")):
        try:
            return datetime.fromisoformat(candidate).date()
        except ValueError:
            pass
    for fmt in ("%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return None


def _numeric(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _first(mapping: Mapping[str, Any], names: Sequence[str], default: Any = None) -> Any:
    for name in names:
        if name in mapping and mapping[name] not in (None, ""):
            return mapping[name]
    return default


def normalize_category(value: Any) -> str:
    key = _clean_text(value, "Uncategorized").lower().replace("-", " ").replace("_", " ")
    return CATEGORY_ALIASES.get(key, _clean_text(value, "Uncategorized"))


def normalize_unit(value: Any) -> str:
    raw = _clean_text(value, "unspecified").lower()
    aliases = {
        "kg co2": "kg CO2e",
        "kg co2e": "kg CO2e",
        "kgs": "kg",
        "kilograms": "kg",
        "kilometer": "km",
        "kilometers": "km",
        "kilometre": "km",
        "kilometres": "km",
        "percent": "%",
        "percentage": "%",
    }
    return aliases.get(raw, raw)


def _source_quality(source: str) -> float:
    key = source.lower()
    if key in {"verified", "measured", "meter", "device"}:
        return 1.0
    if key in {"imported", "recorded", "manual"}:
        return 0.85
    if key in {"estimated", "calculated"}:
        return 0.70
    if key in {"default", "inferred", "unknown"}:
        return 0.50
    return 0.75 if source else 0.55


def _expected_fields(record: Mapping[str, Any]) -> tuple[str, ...]:
    missing = []
    if _first(record, DATE_FIELDS) is None:
        missing.append("date")
    if _first(record, VALUE_FIELDS) is None:
        missing.append("value")
    if _first(record, CATEGORY_FIELDS) is None:
        missing.append("category")
    if _first(record, ID_FIELDS) is None:
        missing.append("id")
    return tuple(missing)


def normalize_record(raw: Mapping[str, Any], index: int = 0, today: date | None = None) -> EvidenceRecord:
    if not isinstance(raw, Mapping):
        raise ReadinessError(f"record {index} is not an object")
    today = today or date.today()
    record_id = _clean_text(_first(raw, ID_FIELDS), f"row-{index}")
    record_date = _parse_date(_first(raw, DATE_FIELDS))
    value = _numeric(_first(raw, VALUE_FIELDS))
    category = normalize_category(_first(raw, CATEGORY_FIELDS))
    metric = _clean_text(_first(raw, ("metric", "metric_name", "name", "assessment_type")), "sustainability")
    unit = normalize_unit(_first(raw, ("unit", "value_unit", "emission_unit"), "unspecified"))
    source = _clean_text(_first(raw, ("source", "data_source", "origin")), "unknown")
    user_id = _clean_text(_first(raw, ("user_id", "owner_id", "profile_id")), "") or None
    missing = _expected_fields(raw)

    completeness = 1.0 - len(missing) / 4
    validity = 1.0
    if record_date is None:
        validity -= 0.35
    if value is None:
        validity -= 0.45
    elif value < 0:
        validity -= 0.25
    if record_date and record_date > today:
        validity -= 0.35
    validity = max(0.0, min(1.0, validity))
    recency = 0.0 if record_date is None else max(
        0.0, min(1.0, 1.0 - (today - record_date).days / 730)
    )
    consistency = _source_quality(source)
    return EvidenceRecord(
        record_id=record_id,
        date=record_date,
        category=category,
        metric=metric,
        value=value,
        unit=unit,
        source=source,
        completeness=round(completeness, 4),
        consistency=round(consistency, 4),
        recency=round(recency, 4),
        validity=round(validity, 4),
        user_id=user_id,
        missing_fields=missing,
        metadata=dict(raw),
    )


def normalize_records(records: Iterable[Mapping[str, Any]], user_id: Any = None) -> list[EvidenceRecord]:
    result = []
    requested_user = _clean_text(user_id, "") or None
    for index, raw in enumerate(records):
        rec = normalize_record(raw, index)
        if requested_user is not None and rec.user_id not in (None, requested_user):
            continue
        result.append(rec)
    return result


def detect_duplicates(records: Sequence[EvidenceRecord]) -> list[EvidenceIssue]:
    groups: dict[tuple[Any, ...], list[EvidenceRecord]] = {}
    for rec in records:
        key = (
            rec.user_id, rec.date, rec.category, rec.metric,
            rec.value, rec.unit,
        )
        groups.setdefault(key, []).append(rec)
    issues = []
    for group in groups.values():
        if len(group) > 1:
            ids = tuple(x.record_id for x in group)
            issues.append(EvidenceIssue(
                "DUPLICATE_EVIDENCE", SEVERITY_WARNING,
                f"Found {len(group)} records with the same evidence identity.",
                ids, group[0].category,
                "Remove duplicates or mark the canonical record before analysis.",
            ))
    return issues


def detect_missingness(records: Sequence[EvidenceRecord]) -> list[EvidenceIssue]:
    issues = []
    for rec in records:
        if rec.missing_fields:
            issues.append(EvidenceIssue(
                "INCOMPLETE_RECORD", SEVERITY_WARNING,
                f"Record is missing: {', '.join(rec.missing_fields)}.",
                (rec.record_id,), rec.category,
                "Complete the missing fields before relying on this record.",
            ))
    return issues


def detect_invalid_records(records: Sequence[EvidenceRecord], today: date | None = None) -> list[EvidenceIssue]:
    today = today or date.today()
    issues = []
    for rec in records:
        if rec.value is not None and rec.value < 0:
            issues.append(EvidenceIssue(
                "NEGATIVE_VALUE", SEVERITY_ERROR,
                "A negative sustainability metric was supplied where a non-negative value is expected.",
                (rec.record_id,), rec.category,
                "Verify the source value and unit.",
            ))
        if rec.date and rec.date > today:
            issues.append(EvidenceIssue(
                "FUTURE_DATE", SEVERITY_ERROR,
                "Evidence is dated in the future and cannot support historical analytics.",
                (rec.record_id,), rec.category,
                "Correct the timestamp before using this record.",
            ))
    return issues


def detect_gaps(records: Sequence[EvidenceRecord], gap_days: int = 45) -> list[EvidenceIssue]:
    by_category: dict[str, list[date]] = {}
    for rec in records:
        if rec.date:
            by_category.setdefault(rec.category, []).append(rec.date)
    issues = []
    for category, dates in by_category.items():
        dates = sorted(set(dates))
        for previous, current in zip(dates, dates[1:]):
            gap = (current - previous).days
            if gap > gap_days:
                issues.append(EvidenceIssue(
                    "HISTORICAL_GAP", SEVERITY_WARNING,
                    f"{gap}-day gap detected between dated evidence records.",
                    category=category,
                    recommendation="Collect more regular assessments to strengthen trend analysis.",
                ))
    return issues


def _span(records: Sequence[EvidenceRecord]) -> int:
    dates = [r.date for r in records if r.date]
    return 0 if len(dates) < 2 else (max(dates) - min(dates)).days


def _unique_dates(records: Sequence[EvidenceRecord]) -> int:
    return len({r.date for r in records if r.date})


def _quality(records: Sequence[EvidenceRecord]) -> float:
    return round(sum(r.quality for r in records) / len(records), 4) if records else 0.0


def _missingness(records: Sequence[EvidenceRecord]) -> float:
    return round(sum(1.0 - r.completeness for r in records) / len(records), 4) if records else 1.0


def _status(confidence: float, blockers: Sequence[str]) -> str:
    if blockers and confidence < 0.60:
        return INSUFFICIENT
    if confidence >= 0.78 and not blockers:
        return RELIABLE
    return LIMITED


def _confidence(records: Sequence[EvidenceRecord], req: Mapping[str, Any]) -> float:
    if not records:
        return 0.0
    count_score = min(1.0, len(records) / max(1, req["min_records"]))
    date_score = min(1.0, _unique_dates(records) / max(1, req["min_records"]))
    span_score = min(1.0, _span(records) / max(1, req["min_span_days"]))
    quality = _quality(records)
    completeness = 1.0 - _missingness(records)
    return round(
        max(0.0, min(1.0,
            count_score * 0.25
            + date_score * 0.15
            + span_score * 0.25
            + quality * 0.25
            + completeness * 0.10
        )), 4
    )


def assess_analysis(
    records: Sequence[EvidenceRecord],
    analysis_type: str,
    requirements: Mapping[str, Mapping[str, Any]] | None = None,
) -> AnalyticsReadiness:
    requirements = requirements or DEFAULT_REQUIREMENTS
    key = analysis_type.lower().strip()
    if key not in requirements:
        raise ReadinessError(f"Unsupported analysis type: {analysis_type}")
    req = requirements[key]
    count = len(records)
    dates = _unique_dates(records)
    span = _span(records)
    quality = _quality(records)
    missingness = _missingness(records)
    blockers = []
    reasons = []
    recommendations = []

    if count < req["min_records"]:
        blockers.append(f"Requires at least {req['min_records']} records; {count} available.")
    else:
        reasons.append(f"Record count meets the minimum of {req['min_records']}.")
    if dates < req["min_records"]:
        blockers.append(f"Requires {req['min_records']} distinct dates; {dates} available.")
    if span < req["min_span_days"]:
        blockers.append(f"Requires {req['min_span_days']} days of history; {span} available.")
    else:
        reasons.append(f"Historical span is {span} days.")
    if quality < req["min_quality"]:
        blockers.append(f"Evidence quality {quality:.0%} is below {req['min_quality']:.0%}.")
    else:
        reasons.append(f"Evidence quality is {quality:.0%}.")
    if missingness > 0.25:
        src.ai.recommendations.append("Complete missing fields before using high-confidence analytics.")
    if span < 90 and key == "forecast":
        src.ai.recommendations.append("Collect a longer history before relying on forecasting.")
    if key == "comparison" and count == 2:
        src.ai.recommendations.append("Add more assessments to make comparisons less sensitive to one record.")
    if not records:
        blockers.append("No evidence records are available.")
    confidence = _confidence(records, req)
    status = _status(confidence, blockers)
    return AnalyticsReadiness(
        analysis_type=key,
        status=status,
        confidence=confidence,
        record_count=count,
        unique_dates=dates,
        span_days=span,
        quality=quality,
        missingness=missingness,
        reasons=tuple(reasons),
        blockers=tuple(blockers),
        recommendations=tuple(dict.fromkeys(recommendations)),
    )


def build_category_evidence(records: Sequence[EvidenceRecord]) -> list[CategoryEvidence]:
    grouped: dict[str, list[EvidenceRecord]] = {}
    for rec in records:
        grouped.setdefault(rec.category, []).append(rec)
    result = []
    for category, items in sorted(grouped.items()):
        quality = _quality(items)
        confidence = round(quality * min(1.0, len(items) / 3), 4)
        blockers = []
        if len(items) < 2:
            blockers.append("Only one evidence record is available.")
        if _unique_dates(items) < 2:
            blockers.append("No multi-date evidence is available.")
        status = RELIABLE if confidence >= 0.78 and not blockers else LIMITED
        if confidence < 0.50:
            status = INSUFFICIENT
        latest = max((x.date for x in items if x.date), default=None)
        result.append(CategoryEvidence(
            category=category,
            record_count=len(items),
            unique_dates=_unique_dates(items),
            span_days=_span(items),
            quality=quality,
            confidence=confidence,
            status=status,
            missingness=_missingness(items),
            latest_date=latest.isoformat() if latest else None,
            issues=tuple(blockers),
        ))
    return result


def detect_staleness(records: Sequence[EvidenceRecord], stale_days: int = 180) -> list[EvidenceIssue]:
    today = date.today()
    issues = []
    for rec in records:
        if rec.date and (today - rec.date).days > stale_days:
            issues.append(EvidenceIssue(
                "STALE_EVIDENCE", SEVERITY_INFO,
                f"Evidence is {(today - rec.date).days} days old.",
                (rec.record_id,), rec.category,
                "Refresh the assessment to improve recency confidence.",
            ))
    return issues


def detect_inconsistent_intervals(records: Sequence[EvidenceRecord], max_cv: float = 1.5) -> list[EvidenceIssue]:
    dates = sorted({r.date for r in records if r.date})
    if len(dates) < 3:
        return []
    gaps = [(b - a).days for a, b in zip(dates, dates[1:]) if (b - a).days > 0]
    if not gaps:
        return []
    mean = sum(gaps) / len(gaps)
    variance = sum((x - mean) ** 2 for x in gaps) / len(gaps)
    cv = math.sqrt(variance) / mean if mean else 0.0
    if cv > max_cv:
        return [EvidenceIssue(
            "IRREGULAR_SAMPLING", SEVERITY_WARNING,
            "Assessment intervals are highly irregular, reducing confidence in trend analysis.",
            recommendation="Use a more consistent assessment schedule.",
        )]
    return []


def build_summary(
    records: Sequence[EvidenceRecord],
    issues: Sequence[EvidenceIssue],
    analyses: Mapping[str, AnalyticsReadiness],
    categories: Sequence[CategoryEvidence],
) -> dict[str, Any]:
    severity_counts = {x: 0 for x in (SEVERITY_CRITICAL, SEVERITY_ERROR, SEVERITY_WARNING, SEVERITY_INFO)}
    for issue in issues:
        severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
    reliable = sum(x.status == RELIABLE for x in analyses.values())
    limited = sum(x.status == LIMITED for x in analyses.values())
    insufficient = sum(x.status == INSUFFICIENT for x in analyses.values())
    return {
        "record_count": len(records),
        "dated_records": sum(r.date is not None for r in records),
        "unique_dates": _unique_dates(records),
        "history_span_days": _span(records),
        "average_quality": _quality(records),
        "missingness": _missingness(records),
        "category_count": len(categories),
        "analyses_reliable": reliable,
        "analyses_limited": limited,
        "analyses_insufficient": insufficient,
        "severity_counts": severity_counts,
        "issue_count": len(issues),
    }


def overall_status(analyses: Mapping[str, AnalyticsReadiness], issues: Sequence[EvidenceIssue]) -> str:
    if not analyses:
        return INSUFFICIENT
    if all(x.status == RELIABLE for x in analyses.values()) and not any(
        x.severity in {SEVERITY_ERROR, SEVERITY_CRITICAL} for x in issues
    ):
        return RELIABLE
    if any(x.status == INSUFFICIENT for x in analyses.values()):
        return LIMITED
    return LIMITED


def calculate_confidence(analyses: Mapping[str, AnalyticsReadiness], records: Sequence[EvidenceRecord]) -> float:
    if not analyses:
        return 0.0
    weights = {"trend": 1.2, "comparison": 1.0, "forecast": 0.8, "recommendation": 1.0, "benchmark": 0.9}
    total = sum(weights.get(k, 1.0) for k in analyses)
    score = sum(v.confidence * weights.get(k, 1.0) for k, v in analyses.items()) / total
    if any(r.duplicate for r in records):
        score *= 0.90
    return round(max(0.0, min(1.0, score)), 4)


def build_readiness_report(
    records: Iterable[Mapping[str, Any]],
    user_id: Any = None,
    requirements: Mapping[str, Mapping[str, Any]] | None = None,
) -> ReadinessReport:
    normalized = normalize_records(records, user_id)
    issues = []
    issues.extend(detect_duplicates(normalized))
    issues.extend(detect_missingness(normalized))
    issues.extend(detect_invalid_records(normalized))
    issues.extend(detect_gaps(normalized))
    issues.extend(detect_staleness(normalized))
    issues.extend(detect_inconsistent_intervals(normalized))
    analyses = {
        key: assess_analysis(normalized, key, requirements)
        for key in (requirements or DEFAULT_REQUIREMENTS)
    }
    categories = build_category_evidence(normalized)
    confidence = calculate_confidence(analyses, normalized)
    status = overall_status(analyses, issues)
    summary = build_summary(normalized, issues, analyses, categories)
    return ReadinessReport(
        generated_at=datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        engine_version=ENGINE_VERSION,
        status=status,
        confidence=confidence,
        records=normalized,
        issues=issues,
        analyses=analyses,
        categories=categories,
        summary=summary,
        user_id=_clean_text(user_id, "") or None,
    )


def explain_readiness(report: ReadinessReport) -> list[str]:
    messages = []
    for name, analysis in src.reporting.report.analyses.items():
        if analysis.status == RELIABLE:
            messages.append(f"{name.title()} analysis is supported by the available evidence.")
        elif analysis.status == LIMITED:
            messages.append(f"{name.title()} analysis is possible with limitations: " + "; ".join(analysis.blockers))
        else:
            messages.append(f"{name.title()} analysis is not sufficiently supported: " + "; ".join(analysis.blockers))
    return messages


def evidence_for_category(report: ReadinessReport, category: str) -> list[EvidenceRecord]:
    target = normalize_category(category)
    return [x for x in src.reporting.report.records if x.category == target]


def evidence_for_analysis(report: ReadinessReport, analysis_type: str) -> AnalyticsReadiness:
    key = analysis_type.lower().strip()
    if key not in src.reporting.report.analyses:
        raise ReadinessError(f"Unsupported analysis type: {analysis_type}")
    return src.reporting.report.analyses[key]


def recommendations_for_report(report: ReadinessReport) -> list[str]:
    values = []
    for analysis in src.reporting.report.analyses.values():
        values.extend(analysis.recommendations)
    for issue in src.reporting.report.issues:
        if issue.recommendation:
            values.append(issue.recommendation)
    return list(dict.fromkeys(values))


def report_hash(report: ReadinessReport) -> str:
    payload = json.dumps(src.reporting.report.to_dict(), sort_keys=True, default=str).encode()
    return sha256(payload).hexdigest()


def export_report(report: ReadinessReport) -> str:
    return src.reporting.report.to_json()


def import_report(payload: str | Mapping[str, Any]) -> dict[str, Any]:
    try:
        data = json.loads(payload) if isinstance(payload, str) else dict(payload)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ReadinessError("Invalid readiness report JSON.") from exc
    required = {"generated_at", "engine_version", "status", "confidence", "summary"}
    missing = required - set(data)
    if missing:
        raise ReadinessError("Missing report fields: " + ", ".join(sorted(missing)))
    return data


def ensure_snapshot_table(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS analytics_readiness_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            generated_at TEXT NOT NULL,
            engine_version TEXT NOT NULL,
            status TEXT NOT NULL,
            confidence REAL NOT NULL,
            report_hash TEXT NOT NULL,
            report_json TEXT NOT NULL
        )
    """)
    connection.commit()


def persist_report(report: ReadinessReport, connection: sqlite3.Connection) -> int:
    ensure_snapshot_table(connection)
    cursor = connection.execute(
        """INSERT INTO analytics_readiness_reports
           (user_id, generated_at, engine_version, status, confidence, report_hash, report_json)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            src.reporting.report.user_id, src.reporting.report.generated_at, src.reporting.report.engine_version,
            src.reporting.report.status, src.reporting.report.confidence, report_hash(report), src.reporting.report.to_json(),
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def load_reports(connection: sqlite3.Connection, user_id: Any = None, limit: int = 50) -> list[dict[str, Any]]:
    ensure_snapshot_table(connection)
    if user_id is None:
        rows = connection.execute(
            "SELECT id,user_id,generated_at,engine_version,status,confidence,report_hash FROM analytics_readiness_reports ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT id,user_id,generated_at,engine_version,status,confidence,report_hash FROM analytics_readiness_reports WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (_clean_text(user_id), limit),
        ).fetchall()
    keys = ("id", "user_id", "generated_at", "engine_version", "status", "confidence", "report_hash")
    return [dict(zip(keys, row)) for row in rows]


def load_report(report_id: int, connection: sqlite3.Connection) -> dict[str, Any] | None:
    ensure_snapshot_table(connection)
    row = connection.execute(
        "SELECT report_json FROM analytics_readiness_reports WHERE id=?", (int(report_id),)
    ).fetchone()
    return json.loads(row[0]) if row else None


def delete_report(report_id: int, connection: sqlite3.Connection) -> bool:
    ensure_snapshot_table(connection)
    cursor = connection.execute("DELETE FROM analytics_readiness_reports WHERE id=?", (int(report_id),))
    connection.commit()
    return cursor.rowcount > 0


def compare_reports(previous: ReadinessReport | Mapping[str, Any], current: ReadinessReport | Mapping[str, Any]) -> dict[str, Any]:
    a = previous.to_dict() if isinstance(previous, ReadinessReport) else dict(previous)
    b = current.to_dict() if isinstance(current, ReadinessReport) else dict(current)
    previous_analyses = a.get("analyses", {})
    current_analyses = b.get("analyses", {})
    changes = {}
    for key in sorted(set(previous_analyses) | set(current_analyses)):
        old = previous_analyses.get(key, {})
        new = current_analyses.get(key, {})
        changes[key] = {
            "previous_status": old.get("status"),
            "current_status": new.get("status"),
            "confidence_change": round((new.get("confidence") or 0) - (old.get("confidence") or 0), 4),
            "record_change": (new.get("record_count") or 0) - (old.get("record_count") or 0),
            "span_change_days": (new.get("span_days") or 0) - (old.get("span_days") or 0),
        }
    return {
        "previous_status": a.get("status"),
        "current_status": b.get("status"),
        "confidence_change": round((b.get("confidence") or 0) - (a.get("confidence") or 0), 4),
        "analysis_changes": changes,
    }


def readiness_matrix(report: ReadinessReport) -> list[dict[str, Any]]:
    return [
        {
            "analysis": key,
            "status": value.status,
            "confidence": value.confidence,
            "records": value.record_count,
            "dates": value.unique_dates,
            "span_days": value.span_days,
            "quality": value.quality,
        }
        for key, value in src.reporting.report.analyses.items()
    ]


def category_matrix(report: ReadinessReport) -> list[dict[str, Any]]:
    return [x.to_dict() for x in src.reporting.report.categories]


def issue_counts(report: ReadinessReport) -> dict[str, int]:
    result: dict[str, int] = {}
    for issue in src.reporting.report.issues:
        result[issue.code] = result.get(issue.code, 0) + 1
    return result


def confidence_label(value: float) -> str:
    if value >= 0.80:
        return "High"
    if value >= 0.60:
        return "Moderate"
    if value >= 0.40:
        return "Low"
    return "Very low"


def validate_requirements(requirements: Mapping[str, Mapping[str, Any]]) -> None:
    for name, values in requirements.items():
        if not isinstance(values, Mapping):
            raise ReadinessError(f"Requirements for {name} must be an object.")
        for key in ("min_records", "min_span_days", "min_quality"):
            if key not in values:
                raise ReadinessError(f"Requirement {name} is missing {key}.")
            if float(values[key]) < 0:
                raise ReadinessError(f"Requirement {name}.{key} cannot be negative.")
        if float(values["min_quality"]) > 1:
            raise ReadinessError(f"Requirement {name}.min_quality must be <= 1.")


def merge_requirements(overrides: Mapping[str, Mapping[str, Any]] | None) -> dict[str, dict[str, Any]]:
    result = {k: dict(v) for k, v in DEFAULT_REQUIREMENTS.items()}
    if overrides:
        for name, values in overrides.items():
            if not isinstance(values, Mapping):
                raise ReadinessError(f"Requirements for {name} must be an object.")
            merged = dict(result.get(name, {}))
            merged.update(values)
            result[name] = merged
        validate_requirements(result)
    return result


def readiness_for_period(records: Iterable[Mapping[str, Any]], start: Any, end: Any) -> ReadinessReport:
    start_date = _parse_date(start)
    end_date = _parse_date(end)
    if not start_date or not end_date or start_date > end_date:
        raise ReadinessError("Invalid readiness period.")
    filtered = []
    for raw in records:
        rec = normalize_record(raw)
        if rec.date and start_date <= rec.date <= end_date:
            filtered.append(raw)
    return build_readiness_report(filtered)


def compare_periods(
    records: Iterable[Mapping[str, Any]],
    first: tuple[Any, Any],
    second: tuple[Any, Any],
) -> dict[str, Any]:
    a = readiness_for_period(records, *first)
    b = readiness_for_period(records, *second)
    return compare_reports(a, b)


def data_coverage(records: Sequence[EvidenceRecord]) -> dict[str, Any]:
    dates = sorted({r.date for r in records if r.date})
    if not dates:
        return {"start": None, "end": None, "span_days": 0, "unique_dates": 0}
    return {
        "start": dates[0].isoformat(),
        "end": dates[-1].isoformat(),
        "span_days": (dates[-1] - dates[0]).days,
        "unique_dates": len(dates),
    }


def missing_categories(records: Sequence[EvidenceRecord], expected: Iterable[str]) -> list[str]:
    present = {normalize_category(x.category) for x in records}
    return [normalize_category(x) for x in expected if normalize_category(x) not in present]


def record_quality_breakdown(records: Sequence[EvidenceRecord]) -> dict[str, float]:
    if not records:
        return {"completeness": 0.0, "consistency": 0.0, "recency": 0.0, "validity": 0.0, "overall": 0.0}
    return {
        "completeness": round(sum(x.completeness for x in records) / len(records), 4),
        "consistency": round(sum(x.consistency for x in records) / len(records), 4),
        "recency": round(sum(x.recency for x in records) / len(records), 4),
        "validity": round(sum(x.validity for x in records) / len(records), 4),
        "overall": _quality(records),
    }


def safe_analytics_gate(report: ReadinessReport, analysis_type: str) -> bool:
    return evidence_for_analysis(report, analysis_type).status != INSUFFICIENT


def reliable_analytics_gate(report: ReadinessReport, analysis_type: str) -> bool:
    return evidence_for_analysis(report, analysis_type).status == RELIABLE


def explain_confidence(report: ReadinessReport) -> dict[str, Any]:
    return {
        "label": confidence_label(src.reporting.report.confidence),
        "score": src.reporting.report.confidence,
        "overall_status": src.reporting.report.status,
        "quality_breakdown": record_quality_breakdown(src.reporting.report.records),
        "coverage": data_coverage(src.reporting.report.records),
        "reasons": explain_readiness(report),
        "recommendations": recommendations_for_report(report),
    }


__all__ = [
    "ENGINE_VERSION", "RELIABLE", "LIMITED", "INSUFFICIENT", "UNKNOWN",
    "SEVERITY_CRITICAL", "SEVERITY_ERROR", "SEVERITY_WARNING", "SEVERITY_INFO",
    "ReadinessError", "EvidenceRecord", "EvidenceIssue", "AnalyticsReadiness",
    "CategoryEvidence", "ReadinessReport", "DEFAULT_REQUIREMENTS",
    "normalize_category", "normalize_unit", "normalize_record", "normalize_records",
    "detect_duplicates", "detect_missingness", "detect_invalid_records", "detect_gaps",
    "detect_staleness", "detect_inconsistent_intervals", "assess_analysis",
    "build_category_evidence", "build_summary", "overall_status", "calculate_confidence",
    "build_readiness_report", "explain_readiness", "evidence_for_category",
    "evidence_for_analysis", "recommendations_for_report", "report_hash",
    "export_report", "import_report", "ensure_snapshot_table", "persist_report",
    "load_reports", "load_report", "delete_report", "compare_reports",
    "readiness_matrix", "category_matrix", "issue_counts", "confidence_label",
    "validate_requirements", "merge_requirements", "readiness_for_period",
    "compare_periods", "data_coverage", "missing_categories",
    "record_quality_breakdown", "safe_analytics_gate", "reliable_analytics_gate",
    "explain_confidence",
]
