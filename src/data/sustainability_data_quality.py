"""Sustainability assessment data-quality and completeness engine.

This module is deliberately read-only. It inspects assessment-like mappings/rows,
normalizes values, identifies missing or suspicious fields, and produces a
deterministic quality report suitable for the EcoBuddy Streamlit UI.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import math
from typing import Any, Iterable, Mapping, Sequence


class QualityStatus(str, Enum):
    COMPLETE = "complete"
    GOOD = "good"
    NEEDS_REVIEW = "needs_review"
    INCOMPLETE = "incomplete"
    INVALID = "invalid"
    EMPTY = "empty"


class IssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueType(str, Enum):
    REQUIRED_MISSING = "required_missing"
    OPTIONAL_MISSING = "optional_missing"
    INVALID_TYPE = "invalid_type"
    INVALID_VALUE = "invalid_value"
    OUT_OF_RANGE = "out_of_range"
    INVALID_DATE = "invalid_date"
    DUPLICATE_ID = "duplicate_id"
    DUPLICATE_ASSESSMENT = "duplicate_assessment"
    STALE_RECORD = "stale_record"
    NEGATIVE_VALUE = "negative_value"
    INCONSISTENT_VALUE = "inconsistent_value"
    UNKNOWN_CATEGORY = "unknown_category"
    LOW_COVERAGE = "low_coverage"
    MISSING_HISTORY = "missing_history"
    MISSING_USER_ID = "missing_user_id"


@dataclass(frozen=True)
class QualityIssue:
    code: str
    issue_type: IssueType
    severity: IssueSeverity
    field: str | None
    message: str
    recommendation: str
    assessment_id: str | None = None
    evidence: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["issue_type"] = self.issue_type.value
        value["severity"] = self.severity.value
        return value


@dataclass(frozen=True)
class FieldDefinition:
    name: str
    label: str
    required: bool
    kind: str
    min_value: float | None = None
    max_value: float | None = None
    allowed_values: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()

    def all_names(self) -> tuple[str, ...]:
        return (self.name,) + self.aliases


@dataclass(frozen=True)
class AssessmentQuality:
    assessment_id: str
    status: QualityStatus
    score: float
    completeness_pct: float
    valid_field_count: int
    expected_field_count: int
    issues: tuple[QualityIssue, ...]
    missing_required: tuple[str, ...]
    missing_optional: tuple[str, ...]
    invalid_fields: tuple[str, ...]
    warnings: int
    errors: int

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        value["issues"] = [x.to_dict() for x in self.issues]
        return value


@dataclass(frozen=True)
class QualityReport:
    generated_at: str
    status: QualityStatus
    score: float
    completeness_pct: float
    assessments_checked: int
    valid_assessments: int
    assessments_with_errors: int
    assessments_needing_review: int
    missing_required_fields: tuple[str, ...]
    missing_optional_fields: tuple[str, ...]
    issue_counts: dict[str, int]
    field_coverage: dict[str, float]
    assessments: tuple[AssessmentQuality, ...]
    duplicate_assessment_ids: tuple[str, ...]
    stale_assessment_count: int
    recommendations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        value["assessments"] = [x.to_dict() for x in self.assessments]
        return value


DEFAULT_FIELDS = (
    FieldDefinition("transport", "Transportation mode", True, "text"),
    FieldDefinition("distance", "Annual travel distance", True, "number", 0, 2_000_000),
    FieldDefinition("electricity", "Electricity consumption", True, "number", 0, 100_000),
    FieldDefinition(
        "diet",
        "Diet",
        True,
        "category",
        allowed_values=(
            "vegan", "vegetarian", "omnivore", "pescatarian",
            "Vegan", "Vegetarian", "Omnivore", "Pescatarian",
        ),
    ),
    FieldDefinition("flights", "Annual flights", True, "integer", 0, 500),
    FieldDefinition("footprint", "Calculated footprint", True, "number", 0, 1_000_000),
    FieldDefinition("eco_score", "Eco score", False, "number", 0, 100),
    FieldDefinition("region", "Region", False, "text"),
    FieldDefinition("trip_id", "Trip identifier", False, "text"),
    FieldDefinition("factor_version", "Emission factor version", False, "text"),
    FieldDefinition("date", "Assessment date", False, "date", aliases=("created_at",)),
)

REQUIRED_FIELD_NAMES = tuple(x.name for x in DEFAULT_FIELDS if x.required)


def _is_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _number(value: Any) -> float | None:
    if not _is_finite(value):
        return None
    return float(value)


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or not number.is_integer():
        return None
    return int(number)


def _parse_date(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif not value:
        return None
    else:
        text = str(value).strip().replace("Z", "+00:00")
        parsed = None
        for parser in (
            lambda x: datetime.fromisoformat(x),
            lambda x: datetime.strptime(x, "%Y-%m-%d"),
            lambda x: datetime.strptime(x, "%Y/%m/%d"),
            lambda x: datetime.strptime(x, "%d-%m-%Y"),
        ):
            try:
                parsed = parser(text)
                break
            except (ValueError, TypeError):
                continue
        if parsed is None:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat() if value else None


def _missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _slug(value: Any) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value)).strip("_")


def _issue_id(*parts: Any) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def field_definitions(custom: Sequence[FieldDefinition] | None = None) -> tuple[FieldDefinition, ...]:
    return tuple(custom or DEFAULT_FIELDS)


def field_definition(name: str, fields: Sequence[FieldDefinition] | None = None) -> FieldDefinition | None:
    lowered = str(name).lower()
    for definition in field_definitions(fields):
        if lowered in {x.lower() for x in definition.all_names()}:
            return definition
    return None


def normalize_assessment(
    record: Mapping[str, Any] | Sequence[Any],
    *,
    fields: Sequence[FieldDefinition] | None = None,
) -> dict[str, Any]:
    definitions = field_definitions(fields)
    if isinstance(record, Mapping):
        raw = dict(record)
    else:
        names = [x.name for x in definitions]
        raw = {name: value for name, value in zip(names, record)}

    result: dict[str, Any] = {}
    for definition in definitions:
        found = False
        for candidate in definition.all_names():
            if candidate in raw and not _missing(raw[candidate]):
                result[definition.name] = raw[candidate]
                found = True
                break
        if not found:
            for candidate in definition.all_names():
                if candidate in raw:
                    result[definition.name] = raw[candidate]
                    found = True
                    break
        if not found:
            result[definition.name] = None

    if isinstance(record, Mapping):
        if record.get("id") not in (None, ""):
            result["id"] = record.get("id")
        if record.get("assessment_id") not in (None, ""):
            result["assessment_id"] = record.get("assessment_id")
        if record.get("user_id") not in (None, ""):
            result["user_id"] = record.get("user_id")
    if result.get("date") is not None:
        parsed_date = _parse_date(result["date"])
        if parsed_date is not None:
            result["date"] = _iso(parsed_date)
    for numeric_name in ("distance", "electricity", "footprint", "eco_score"):
        if result.get(numeric_name) is not None:
            converted = _number(result[numeric_name])
            if converted is not None:
                result[numeric_name] = converted
    if result.get("flights") is not None:
        converted_flights = _integer(result["flights"])
        if converted_flights is not None:
            result["flights"] = converted_flights
    return result


def assessment_identifier(record: Mapping[str, Any], index: int = 0) -> str:
    for key in ("id", "assessment_id", "trip_id"):
        if record.get(key) not in (None, ""):
            return str(record[key])
    fingerprint = _issue_id(
        record.get("date"),
        record.get("transport"),
        record.get("distance"),
        record.get("electricity"),
        record.get("diet"),
        record.get("flights"),
        record.get("footprint"),
        index,
    )
    return f"row-{fingerprint}"


def canonical_fingerprint(record: Mapping[str, Any]) -> str:
    payload = {
        key: record.get(key)
        for key in (
            "transport", "distance", "electricity", "diet",
            "flights", "footprint", "eco_score", "region",
        )
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def validate_required_fields(
    record: Mapping[str, Any],
    *,
    fields: Sequence[FieldDefinition] | None = None,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    aid = assessment_identifier(record)
    for definition in field_definitions(fields):
        if not definition.required:
            continue
        if _missing(record.get(definition.name)):
            issues.append(
                QualityIssue(
                    _issue_id(aid, "required", definition.name),
                    IssueType.REQUIRED_MISSING,
                    IssueSeverity.ERROR,
                    definition.name,
                    f"{definition.label} is missing.",
                    f"Provide {definition.label.lower()} before treating this assessment as complete.",
                    aid,
                    {"required": True},
                )
            )
    return issues


def validate_optional_fields(
    record: Mapping[str, Any],
    *,
    fields: Sequence[FieldDefinition] | None = None,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    aid = assessment_identifier(record)
    for definition in field_definitions(fields):
        if definition.required or _missing(record.get(definition.name)):
            continue
        if definition.kind == "text" and not str(record[definition.name]).strip():
            issues.append(
                QualityIssue(
                    _issue_id(aid, "optional", definition.name),
                    IssueType.OPTIONAL_MISSING,
                    IssueSeverity.INFO,
                    definition.name,
                    f"{definition.label} is empty.",
                    f"Add {definition.label.lower()} if it is available.",
                    aid,
                )
            )
    return issues


def validate_types(
    record: Mapping[str, Any],
    *,
    fields: Sequence[FieldDefinition] | None = None,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    aid = assessment_identifier(record)
    for definition in field_definitions(fields):
        value = record.get(definition.name)
        if _missing(value):
            continue
        valid = True
        if definition.kind == "number":
            valid = _number(value) is not None
        elif definition.kind == "integer":
            valid = _integer(value) is not None
        elif definition.kind == "date":
            valid = _parse_date(value) is not None
        elif definition.kind in {"text", "category"}:
            valid = isinstance(value, str)
        if not valid:
            issues.append(
                QualityIssue(
                    _issue_id(aid, "type", definition.name),
                    IssueType.INVALID_TYPE,
                    IssueSeverity.ERROR,
                    definition.name,
                    f"{definition.label} has an invalid type or format.",
                    f"Store {definition.label.lower()} using the expected {definition.kind} format.",
                    aid,
                    {"expected_kind": definition.kind, "value_type": type(value).__name__},
                )
            )
    return issues


def validate_ranges(
    record: Mapping[str, Any],
    *,
    fields: Sequence[FieldDefinition] | None = None,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    aid = assessment_identifier(record)
    for definition in field_definitions(fields):
        value = record.get(definition.name)
        if _missing(value):
            continue
        number = _number(value)
        if number is None or definition.kind not in {"number", "integer"}:
            continue
        if definition.min_value is not None and number < definition.min_value:
            issues.append(
                QualityIssue(
                    _issue_id(aid, "min", definition.name),
                    IssueType.OUT_OF_RANGE,
                    IssueSeverity.ERROR,
                    definition.name,
                    f"{definition.label} is below the allowed minimum.",
                    f"Use a value at least {definition.min_value:g}.",
                    aid,
                    {"value": number, "minimum": definition.min_value},
                )
            )
        if definition.max_value is not None and number > definition.max_value:
            issues.append(
                QualityIssue(
                    _issue_id(aid, "max", definition.name),
                    IssueType.OUT_OF_RANGE,
                    IssueSeverity.ERROR,
                    definition.name,
                    f"{definition.label} exceeds the allowed maximum.",
                    f"Use a value no greater than {definition.max_value:g}.",
                    aid,
                    {"value": number, "maximum": definition.max_value},
                )
            )
        if number < 0:
            issues.append(
                QualityIssue(
                    _issue_id(aid, "negative", definition.name),
                    IssueType.NEGATIVE_VALUE,
                    IssueSeverity.ERROR,
                    definition.name,
                    f"{definition.label} cannot be negative.",
                    f"Correct the {definition.label.lower()} value.",
                    aid,
                    {"value": number},
                )
            )
    return issues


def validate_categories(
    record: Mapping[str, Any],
    *,
    fields: Sequence[FieldDefinition] | None = None,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    aid = assessment_identifier(record)
    for definition in field_definitions(fields):
        if definition.kind != "category" or _missing(record.get(definition.name)):
            continue
        if definition.allowed_values and str(record[definition.name]) not in definition.allowed_values:
            issues.append(
                QualityIssue(
                    _issue_id(aid, "category", definition.name),
                    IssueType.UNKNOWN_CATEGORY,
                    IssueSeverity.WARNING,
                    definition.name,
                    f"{definition.label} uses an unrecognized category.",
                    "Choose a supported category or extend the category configuration explicitly.",
                    aid,
                    {"value": record[definition.name], "allowed_values": definition.allowed_values},
                )
            )
    return issues


def validate_dates(
    record: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    aid = assessment_identifier(record)
    if _missing(record.get("date")):
        return issues
    parsed = _parse_date(record.get("date"))
    if parsed is None:
        issues.append(
            QualityIssue(
                _issue_id(aid, "date"),
                IssueType.INVALID_DATE,
                IssueSeverity.ERROR,
                "date",
                "Assessment date is invalid.",
                "Use an ISO-compatible assessment date.",
                aid,
                {"value": record.get("date")},
            )
        )
        return issues
    current = now or datetime.now(timezone.utc)
    if parsed > current:
        issues.append(
            QualityIssue(
                _issue_id(aid, "future_date"),
                IssueType.INVALID_DATE,
                IssueSeverity.WARNING,
                "date",
                "Assessment date is in the future.",
                "Confirm that the assessment date is correct.",
                aid,
                {"date": _iso(parsed), "now": _iso(current)},
            )
        )
    return issues


def validate_consistency(record: Mapping[str, Any]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    aid = assessment_identifier(record)
    footprint = _number(record.get("footprint"))
    distance = _number(record.get("distance"))
    electricity = _number(record.get("electricity"))
    flights = _integer(record.get("flights"))
    if footprint == 0 and any(x and x > 0 for x in (distance, electricity, flights)):
        issues.append(
            QualityIssue(
                _issue_id(aid, "zero_footprint"),
                IssueType.INCONSISTENT_VALUE,
                IssueSeverity.WARNING,
                "footprint",
                "The footprint is zero while activity inputs are non-zero.",
                "Review the calculation result and source inputs.",
                aid,
                {"footprint": footprint, "distance": distance, "electricity": electricity, "flights": flights},
            )
        )
    if footprint is not None and footprint > 0 and all(
        x in (None, 0) for x in (distance, electricity, flights)
    ):
        issues.append(
            QualityIssue(
                _issue_id(aid, "missing_activity"),
                IssueType.INCONSISTENT_VALUE,
                IssueSeverity.WARNING,
                "footprint",
                "A positive footprint exists but the main activity inputs are empty.",
                "Verify that the source activity data was retained.",
                aid,
                {"footprint": footprint},
            )
        )
    return issues


def inspect_assessment(
    record: Mapping[str, Any] | Sequence[Any],
    *,
    index: int = 0,
    fields: Sequence[FieldDefinition] | None = None,
    now: datetime | None = None,
) -> AssessmentQuality:
    normalized = normalize_assessment(record, fields=fields)
    aid = assessment_identifier({**normalized, **({"id": record.get("id")} if isinstance(record, Mapping) and record.get("id") else {})}, index)
    required = validate_required_fields(normalized, fields=fields)
    optional = validate_optional_fields(normalized, fields=fields)
    type_issues = validate_types(normalized, fields=fields)
    range_issues = validate_ranges(normalized, fields=fields)
    category_issues = validate_categories(normalized, fields=fields)
    date_issues = validate_dates(normalized, now=now)
    consistency = validate_consistency(normalized)
    issues = tuple(required + optional + type_issues + range_issues + category_issues + date_issues + consistency)

    missing_required = tuple(
        x.field for x in required if x.field
    )
    missing_optional = tuple(
        definition.name
        for definition in field_definitions(fields)
        if not definition.required and _missing(normalized.get(definition.name))
    )
    invalid_fields = tuple(
        sorted({
            x.field for x in issues
            if x.field and x.severity == IssueSeverity.ERROR
        })
    )
    expected = len(field_definitions(fields))
    present_valid = sum(
        not _missing(normalized.get(x.name))
        and not any(i.field == x.name and i.severity == IssueSeverity.ERROR for i in issues)
        for x in field_definitions(fields)
    )
    completeness = round(present_valid / expected * 100, 2) if expected else 100.0
    errors = sum(x.severity == IssueSeverity.ERROR for x in issues)
    warnings = sum(x.severity == IssueSeverity.WARNING for x in issues)

    if not any(not _missing(normalized.get(x.name)) for x in field_definitions(fields)):
        status = QualityStatus.EMPTY
    elif errors:
        status = QualityStatus.INVALID if len(invalid_fields) >= 2 else QualityStatus.INCOMPLETE
    elif warnings:
        status = QualityStatus.NEEDS_REVIEW
    elif completeness >= 100:
        status = QualityStatus.COMPLETE
    elif completeness >= 80:
        status = QualityStatus.GOOD
    else:
        status = QualityStatus.INCOMPLETE

    score = max(0.0, min(100.0, completeness - errors * 15 - warnings * 4))
    return AssessmentQuality(
        str(aid), status, round(score, 2), completeness, present_valid, expected,
        issues, missing_required, missing_optional, invalid_fields, warnings, errors,
    )


def normalize_assessments(
    records: Iterable[Mapping[str, Any] | Sequence[Any]] | None,
    *,
    fields: Sequence[FieldDefinition] | None = None,
) -> tuple[dict[str, Any], ...]:
    if not records:
        return ()
    return tuple(normalize_assessment(record, fields=fields) for record in records)


def detect_duplicate_ids(records: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for index, record in enumerate(records):
        aid = assessment_identifier(record, index)
        if aid in seen:
            duplicates.add(aid)
        seen.add(aid)
    return tuple(sorted(duplicates))


def detect_duplicate_records(records: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    seen: dict[str, int] = {}
    duplicates: set[str] = set()
    for index, record in enumerate(records):
        fingerprint = canonical_fingerprint(record)
        if fingerprint in seen:
            duplicates.add(assessment_identifier(record, index))
        else:
            seen[fingerprint] = index
    return tuple(sorted(duplicates))


def detect_stale_assessments(
    records: Sequence[Mapping[str, Any]],
    *,
    stale_days: int = 90,
    now: datetime | None = None,
) -> tuple[str, ...]:
    if stale_days < 1:
        raise ValueError("stale_days must be positive")
    current = now or datetime.now(timezone.utc)
    result: list[str] = []
    for index, record in enumerate(records):
        date = _parse_date(record.get("date"))
        if date and (current - date).days > stale_days:
            result.append(assessment_identifier(record, index))
    return tuple(result)


def field_coverage(
    records: Sequence[Mapping[str, Any]],
    *,
    fields: Sequence[FieldDefinition] | None = None,
) -> dict[str, float]:
    definitions = field_definitions(fields)
    if not records:
        return {x.name: 0.0 for x in definitions}
    return {
        definition.name: round(
            sum(not _missing(record.get(definition.name)) for record in records)
            / len(records) * 100,
            2,
        )
        for definition in definitions
    }


def issue_counts(issues: Iterable[QualityIssue]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for issue in issues:
        key = issue.issue_type.value
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def quality_recommendations(
    report_or_assessments: QualityReport | Sequence[AssessmentQuality],
) -> tuple[str, ...]:
    assessments = (
        report_or_assessments.assessments
        if isinstance(report_or_assessments, QualityReport)
        else tuple(report_or_assessments)
    )
    messages: list[str] = []
    if any(x.missing_required for x in assessments):
        messages.append("Complete missing required assessment inputs before using the data for comparisons.")
    if any(x.invalid_fields for x in assessments):
        messages.append("Correct invalid or out-of-range values before relying on the affected assessment.")
    if any(
        issue.issue_type == IssueType.DUPLICATE_ASSESSMENT
        for assessment in assessments
        for issue in assessment.issues
    ):
        messages.append("Review duplicate assessment records so the same observation is not counted twice.")
    if any(x.status == QualityStatus.NEEDS_REVIEW for x in assessments):
        messages.append("Review warnings before treating the dataset as fully trustworthy.")
    if not messages:
        messages.append("Assessment data passes the configured quality checks.")
    return tuple(dict.fromkeys(messages))


def build_quality_report(
    records: Iterable[Mapping[str, Any] | Sequence[Any]] | None,
    *,
    fields: Sequence[FieldDefinition] | None = None,
    stale_days: int = 90,
    now: datetime | None = None,
) -> QualityReport:
    definitions = field_definitions(fields)
    normalized = normalize_assessments(records, fields=definitions)
    current = now or datetime.now(timezone.utc)
    if not normalized:
        return QualityReport(
            _iso(current) or "",
            QualityStatus.EMPTY,
            0.0,
            0.0,
            0,
            0,
            0,
            0,
            (),
            (),
            {},
            {x.name: 0.0 for x in definitions},
            (),
            (),
            0,
            ("Complete an assessment to establish a usable baseline.",),
        )

    duplicates = detect_duplicate_ids(normalized)
    duplicate_records = detect_duplicate_records(normalized)
    stale = detect_stale_assessments(normalized, stale_days=stale_days, now=current)
    qualities: list[AssessmentQuality] = []

    for index, record in enumerate(normalized):
        quality = inspect_assessment(record, index=index, fields=definitions, now=current)
        extra: list[QualityIssue] = []
        aid = assessment_identifier(record, index)
        if aid in duplicates:
            extra.append(QualityIssue(
                _issue_id(aid, "duplicate_id"),
                IssueType.DUPLICATE_ID,
                IssueSeverity.ERROR,
                "id",
                "The assessment identifier is duplicated.",
                "Keep a stable unique identifier for each assessment.",
                aid,
                {"assessment_id": aid},
            ))
        if aid in duplicate_records:
            extra.append(QualityIssue(
                _issue_id(aid, "duplicate_record"),
                IssueType.DUPLICATE_ASSESSMENT,
                IssueSeverity.WARNING,
                None,
                "This assessment appears to duplicate another assessment.",
                "Review the records and remove or explain the duplicate.",
                aid,
                {"fingerprint": canonical_fingerprint(record)},
            ))
        if aid in stale:
            extra.append(QualityIssue(
                _issue_id(aid, "stale"),
                IssueType.STALE_RECORD,
                IssueSeverity.INFO,
                "date",
                f"This assessment is older than {stale_days} days.",
                "Refresh the assessment if the user's circumstances have changed.",
                aid,
                {"stale_days": stale_days},
            ))
        if extra:
            merged = tuple(list(quality.issues) + extra)
            warnings = sum(x.severity == IssueSeverity.WARNING for x in merged)
            errors = sum(x.severity == IssueSeverity.ERROR for x in merged)
            status = (
                QualityStatus.INVALID if errors else
                QualityStatus.NEEDS_REVIEW if warnings else quality.status
            )
            score = max(0.0, quality.score - errors * 10 - warnings * 2)
            quality = AssessmentQuality(
                quality.assessment_id, status, round(score, 2),
                quality.completeness_pct, quality.valid_field_count,
                quality.expected_field_count, merged, quality.missing_required,
                quality.missing_optional, quality.invalid_fields, warnings, errors,
            )
        qualities.append(quality)

    all_issues = [issue for assessment in qualities for issue in assessment.issues]
    missing_required = tuple(sorted({
        field for assessment in qualities for field in assessment.missing_required
    }))
    missing_optional = tuple(sorted({
        field for assessment in qualities for field in assessment.missing_optional
    }))
    errors = sum(x.errors for x in qualities)
    review = sum(x.status == QualityStatus.NEEDS_REVIEW for x in qualities)
    valid = sum(x.status in {QualityStatus.COMPLETE, QualityStatus.GOOD} for x in qualities)
    completeness = round(
        sum(x.completeness_pct for x in qualities) / len(qualities), 2
    )
    score = round(sum(x.score for x in qualities) / len(qualities), 2)
    if errors:
        status = QualityStatus.INVALID
    elif review:
        status = QualityStatus.NEEDS_REVIEW
    elif completeness >= 100:
        status = QualityStatus.COMPLETE
    elif completeness >= 80:
        status = QualityStatus.GOOD
    else:
        status = QualityStatus.INCOMPLETE

    report = QualityReport(
        _iso(current) or "",
        status,
        score,
        completeness,
        len(qualities),
        valid,
        sum(x.errors > 0 for x in qualities),
        review,
        missing_required,
        missing_optional,
        issue_counts(all_issues),
        field_coverage(normalized, fields=definitions),
        tuple(qualities),
        duplicates,
        len(stale),
        (),
    )
    return QualityReport(
        generated_at=report.generated_at,
        status=report.status,
        score=report.score,
        completeness_pct=report.completeness_pct,
        assessments_checked=report.assessments_checked,
        valid_assessments=report.valid_assessments,
        assessments_with_errors=report.assessments_with_errors,
        assessments_needing_review=report.assessments_needing_review,
        missing_required_fields=report.missing_required_fields,
        missing_optional_fields=report.missing_optional_fields,
        issue_counts=report.issue_counts,
        field_coverage=report.field_coverage,
        assessments=report.assessments,
        duplicate_assessment_ids=report.duplicate_assessment_ids,
        stale_assessment_count=report.stale_assessment_count,
        recommendations=quality_recommendations(report),
    )


def filter_issues(
    issues: Iterable[QualityIssue],
    *,
    severity: IssueSeverity | str | None = None,
    issue_type: IssueType | str | None = None,
    field: str | None = None,
) -> tuple[QualityIssue, ...]:
    severity_value = severity.value if isinstance(severity, Enum) else severity
    type_value = issue_type.value if isinstance(issue_type, Enum) else issue_type
    return tuple(
        issue for issue in issues
        if (severity_value is None or issue.severity.value == severity_value)
        and (type_value is None or issue.issue_type.value == type_value)
        and (field is None or issue.field == field)
    )


def all_report_issues(report: QualityReport) -> tuple[QualityIssue, ...]:
    return tuple(issue for assessment in report.assessments for issue in assessment.issues)


def report_issue_summary(report: QualityReport) -> list[dict[str, Any]]:
    counts = issue_counts(all_report_issues(report))
    return [
        {"issue_type": key, "count": value}
        for key, value in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def missing_field_summary(report: QualityReport) -> list[dict[str, Any]]:
    values = []
    for field, coverage in sorted(report.field_coverage.items(), key=lambda item: item[1]):
        values.append({
            "field": field,
            "coverage_pct": coverage,
            "missing_pct": round(100 - coverage, 2),
        })
    return values


def completeness_distribution(report: QualityReport) -> dict[str, int]:
    buckets = {"0-49": 0, "50-79": 0, "80-99": 0, "100": 0}
    for assessment in report.assessments:
        value = assessment.completeness_pct
        if value >= 100:
            buckets["100"] += 1
        elif value >= 80:
            buckets["80-99"] += 1
        elif value >= 50:
            buckets["50-79"] += 1
        else:
            buckets["0-49"] += 1
    return buckets


def status_counts(report: QualityReport) -> dict[str, int]:
    counts = {status.value: 0 for status in QualityStatus}
    for assessment in report.assessments:
        counts[assessment.status.value] += 1
    return counts


def critical_issues(report: QualityReport) -> tuple[QualityIssue, ...]:
    return filter_issues(all_report_issues(report), severity=IssueSeverity.ERROR)


def warning_issues(report: QualityReport) -> tuple[QualityIssue, ...]:
    return filter_issues(all_report_issues(report), severity=IssueSeverity.WARNING)


def informational_issues(report: QualityReport) -> tuple[QualityIssue, ...]:
    return filter_issues(all_report_issues(report), severity=IssueSeverity.INFO)


def assessment_quality_by_id(report: QualityReport, assessment_id: str) -> AssessmentQuality | None:
    for assessment in report.assessments:
        if assessment.assessment_id == str(assessment_id):
            return assessment
    return None


def field_quality(report: QualityReport, field: str) -> dict[str, Any]:
    definition = field_definition(field)
    issues = filter_issues(all_report_issues(report), field=field)
    return {
        "field": field,
        "label": definition.label if definition else field.replace("_", " ").title(),
        "required": definition.required if definition else False,
        "coverage_pct": report.field_coverage.get(field, 0.0),
        "issue_count": len(issues),
        "errors": sum(x.severity == IssueSeverity.ERROR for x in issues),
        "warnings": sum(x.severity == IssueSeverity.WARNING for x in issues),
    }


def required_field_coverage(report: QualityReport) -> dict[str, float]:
    return {
        field: report.field_coverage.get(field, 0.0)
        for field in REQUIRED_FIELD_NAMES
    }


def overall_readiness(report: QualityReport) -> dict[str, Any]:
    return {
        "ready_for_trends": report.status in {
            QualityStatus.COMPLETE, QualityStatus.GOOD, QualityStatus.NEEDS_REVIEW
        } and report.assessments_checked >= 2 and report.assessments_with_errors == 0,
        "ready_for_benchmarking": report.status in {
            QualityStatus.COMPLETE, QualityStatus.GOOD
        },
        "ready_for_export": report.assessments_with_errors == 0,
        "reason": (
            "The dataset has enough valid observations for trend analysis."
            if report.assessments_checked >= 2 and report.assessments_with_errors == 0
            else "Resolve required data-quality errors and/or add another valid assessment."
        ),
    }


def score_label(score: float) -> str:
    if score >= 95:
        return "Excellent"
    if score >= 85:
        return "Good"
    if score >= 70:
        return "Needs review"
    if score >= 50:
        return "Incomplete"
    return "Poor"


def status_label(status: QualityStatus | str) -> str:
    value = status.value if isinstance(status, Enum) else str(status)
    return {
        "complete": "Complete",
        "good": "Good",
        "needs_review": "Needs review",
        "incomplete": "Incomplete",
        "invalid": "Invalid",
        "empty": "Empty",
    }.get(value, value.replace("_", " ").title())


def issue_priority_rank(issue: QualityIssue) -> int:
    return {
        IssueSeverity.ERROR: 0,
        IssueSeverity.WARNING: 1,
        IssueSeverity.INFO: 2,
    }[issue.severity]


def sorted_issues(issues: Iterable[QualityIssue]) -> tuple[QualityIssue, ...]:
    return tuple(sorted(
        issues,
        key=lambda issue: (
            issue_priority_rank(issue),
            issue.field or "",
            issue.code,
        ),
    ))


def top_quality_actions(report: QualityReport, limit: int = 5) -> tuple[str, ...]:
    if limit < 1:
        raise ValueError("limit must be positive")
    actions: list[str] = []
    for issue in sorted_issues(all_report_issues(report)):
        if issue.recommendation not in actions:
            actions.append(issue.recommendation)
        if len(actions) >= limit:
            break
    return tuple(actions)


def compare_quality_reports(
    previous: QualityReport,
    current: QualityReport,
) -> dict[str, Any]:
    return {
        "score_change": round(current.score - previous.score, 2),
        "completeness_change": round(
            current.completeness_pct - previous.completeness_pct, 2
        ),
        "error_change": current.assessments_with_errors - previous.assessments_with_errors,
        "review_change": current.assessments_needing_review - previous.assessments_needing_review,
        "field_coverage_change": {
            field: round(
                current.field_coverage.get(field, 0.0)
                - previous.field_coverage.get(field, 0.0),
                2,
            )
            for field in sorted(set(previous.field_coverage) | set(current.field_coverage))
        },
    }


def quality_trend(
    reports: Sequence[QualityReport],
) -> dict[str, Any]:
    if not reports:
        return {"direction": "unknown", "score_change": 0.0, "completeness_change": 0.0}
    if len(reports) == 1:
        return {"direction": "stable", "score_change": 0.0, "completeness_change": 0.0}
    first, last = reports[0], reports[-1]
    score_change = round(last.score - first.score, 2)
    completeness_change = round(last.completeness_pct - first.completeness_pct, 2)
    if score_change > 2 or completeness_change > 2:
        direction = "improving"
    elif score_change < -2 or completeness_change < -2:
        direction = "declining"
    else:
        direction = "stable"
    return {
        "direction": direction,
        "score_change": score_change,
        "completeness_change": completeness_change,
    }


def serialize_report(report: QualityReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True, ensure_ascii=False)


def serialize_assessment_quality(quality: AssessmentQuality) -> str:
    return json.dumps(quality.to_dict(), indent=2, sort_keys=True, ensure_ascii=False)


def export_quality_csv_rows(report: QualityReport) -> list[dict[str, Any]]:
    rows = []
    for assessment in report.assessments:
        rows.append({
            "assessment_id": assessment.assessment_id,
            "status": assessment.status.value,
            "score": assessment.score,
            "completeness_pct": assessment.completeness_pct,
            "missing_required": ", ".join(assessment.missing_required),
            "missing_optional": ", ".join(assessment.missing_optional),
            "invalid_fields": ", ".join(assessment.invalid_fields),
            "warnings": assessment.warnings,
            "errors": assessment.errors,
        })
    return rows


def report_markdown(report: QualityReport) -> str:
    lines = [
        "# Sustainability Data Quality Report",
        "",
        f"**Status:** {status_label(report.status)}",
        f"**Quality score:** {report.score:.1f}/100",
        f"**Completeness:** {report.completeness_pct:.1f}%",
        f"**Assessments checked:** {report.assessments_checked}",
        "",
        "## Field coverage",
        "",
        "| Field | Coverage |",
        "|---|---:|",
    ]
    for field, coverage in report.field_coverage.items():
        lines.append(f"| {field} | {coverage:.1f}% |")
    lines.extend(["", "## Recommendations", ""])
    for recommendation in report.recommendations:
        lines.append(f"- {recommendation}")
    return "\n".join(lines)


def validate_report_integrity(report: QualityReport) -> tuple[str, ...]:
    problems: list[str] = []
    if not 0 <= report.score <= 100:
        problems.append("Report score is outside 0-100.")
    if not 0 <= report.completeness_pct <= 100:
        problems.append("Report completeness is outside 0-100.")
    if report.assessments_checked != len(report.assessments):
        problems.append("Assessment count does not match report records.")
    if report.valid_assessments > report.assessments_checked:
        problems.append("Valid assessment count exceeds checked count.")
    for field, coverage in report.field_coverage.items():
        if not 0 <= coverage <= 100:
            problems.append(f"Field coverage for {field} is outside 0-100.")
    return tuple(problems)


def build_dashboard_payload(report: QualityReport) -> dict[str, Any]:
    return {
        "overview": {
            "status": report.status.value,
            "status_label": status_label(report.status),
            "score": report.score,
            "score_label": score_label(report.score),
            "completeness_pct": report.completeness_pct,
        },
        "counts": {
            "assessments_checked": report.assessments_checked,
            "valid_assessments": report.valid_assessments,
            "errors": report.assessments_with_errors,
            "needs_review": report.assessments_needing_review,
            "stale": report.stale_assessment_count,
        },
        "field_coverage": missing_field_summary(report),
        "issue_summary": report_issue_summary(report),
        "distribution": completeness_distribution(report),
        "status_counts": status_counts(report),
        "readiness": overall_readiness(report),
        "recommendations": list(report.recommendations),
    }


def merge_quality_reports(reports: Sequence[QualityReport]) -> QualityReport:
    if not reports:
        raise ValueError("At least one report is required")
    assessments: list[AssessmentQuality] = []
    seen: set[str] = set()
    for report in reports:
        for assessment in report.assessments:
            if assessment.assessment_id not in seen:
                assessments.append(assessment)
                seen.add(assessment.assessment_id)
    fields = sorted({
        field
        for report in reports
        for field in report.field_coverage
    })
    coverage = {
        field: round(
            sum(report.field_coverage.get(field, 0.0) for report in reports)
            / len(reports),
            2,
        )
        for field in fields
    }
    score = round(sum(x.score for x in reports) / len(reports), 2)
    completeness = round(sum(x.completeness_pct for x in reports) / len(reports), 2)
    errors = sum(x.errors > 0 for x in assessments)
    review = sum(x.status == QualityStatus.NEEDS_REVIEW for x in assessments)
    status = (
        QualityStatus.INVALID if errors
        else QualityStatus.NEEDS_REVIEW if review
        else QualityStatus.COMPLETE if completeness >= 100
        else QualityStatus.GOOD if completeness >= 80
        else QualityStatus.INCOMPLETE
    )
    return QualityReport(
        reports[-1].generated_at,
        status,
        score,
        completeness,
        len(assessments),
        sum(x.status in {QualityStatus.COMPLETE, QualityStatus.GOOD} for x in assessments),
        errors,
        review,
        tuple(sorted({f for x in assessments for f in x.missing_required})),
        tuple(sorted({f for x in assessments for f in x.missing_optional})),
        issue_counts(issue for x in assessments for issue in x.issues),
        coverage,
        tuple(assessments),
        tuple(sorted({x for r in reports for x in r.duplicate_assessment_ids})),
        sum(r.stale_assessment_count for r in reports),
        (),
    )


def records_ready_for_analysis(
    records: Iterable[Mapping[str, Any] | Sequence[Any]],
    *,
    minimum_score: float = 70,
) -> tuple[dict[str, Any], ...]:
    ready: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        normalized = normalize_assessment(raw)
        quality = inspect_assessment(normalized, index=index)
        if quality.score >= minimum_score and quality.errors == 0:
            ready.append(normalized)
    return tuple(ready)


def completeness_percent(record: Mapping[str, Any]) -> float:
    quality = inspect_assessment(record)
    return quality.completeness_pct


def quality_score(record: Mapping[str, Any]) -> float:
    return inspect_assessment(record).score


def explain_issue(issue: QualityIssue) -> str:
    evidence = issue.evidence or {}
    suffix = f" Evidence: {json.dumps(evidence, sort_keys=True, default=str)}." if evidence else ""
    return f"{issue.message} {issue.recommendation}{suffix}"


def explain_report(report: QualityReport) -> str:
    if report.status == QualityStatus.EMPTY:
        return "No usable assessments were found."
    if report.status == QualityStatus.INVALID:
        return "The dataset contains errors that should be corrected before analysis."
    if report.status == QualityStatus.INCOMPLETE:
        return "The dataset is usable only after completing missing required fields."
    if report.status == QualityStatus.NEEDS_REVIEW:
        return "The dataset is mostly complete but contains warnings that should be reviewed."
    if report.status == QualityStatus.GOOD:
        return "The dataset is in good shape for analysis."
    return "The dataset is complete and passes the configured quality checks."


def latest_quality(
    records: Sequence[Mapping[str, Any] | Sequence[Any]],
) -> AssessmentQuality | None:
    if not records:
        return None
    normalized = normalize_assessments(records)
    if not normalized:
        return None
    return inspect_assessment(normalized[-1], index=len(normalized) - 1)


def missing_required_fields(record: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        issue.field for issue in validate_required_fields(record) if issue.field
    )


def invalid_fields(record: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(sorted({
        issue.field
        for issue in (
            validate_types(record)
            + validate_ranges(record)
            + validate_dates(record)
        )
        if issue.field
    }))


def quality_badges(report: QualityReport) -> tuple[dict[str, str], ...]:
    return (
        {"label": "Status", "value": status_label(report.status)},
        {"label": "Score", "value": f"{report.score:.1f}/100"},
        {"label": "Completeness", "value": f"{report.completeness_pct:.1f}%"},
        {"label": "Assessments", "value": str(report.assessments_checked)},
        {"label": "Errors", "value": str(report.assessments_with_errors)},
        {"label": "Needs review", "value": str(report.assessments_needing_review)},
    )


def quality_center_text(report: QualityReport) -> str:
    actions = top_quality_actions(report, limit=3)
    lines = [
        explain_report(report),
        f"Quality score: {report.score:.1f}/100.",
        f"Average completeness: {report.completeness_pct:.1f}%.",
    ]
    if actions:
        lines.append("Priority actions: " + " ".join(actions))
    return " ".join(lines)
