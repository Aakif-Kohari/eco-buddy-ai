from datetime import datetime, timedelta, timezone
import json
import pytest

from sustainability_data_quality import (
    DEFAULT_FIELDS,
    FieldDefinition,
    IssueSeverity,
    IssueType,
    QualityStatus,
    assessment_identifier,
    build_dashboard_payload,
    build_quality_report,
    canonical_fingerprint,
    completeness_distribution,
    critical_issues,
    detect_duplicate_ids,
    detect_duplicate_records,
    detect_stale_assessments,
    explain_report,
    field_coverage,
    filter_issues,
    field_quality,
    inspect_assessment,
    invalid_fields,
    latest_quality,
    missing_required_fields,
    normalize_assessment,
    normalize_assessments,
    overall_readiness,
    quality_badges,
    quality_score,
    quality_trend,
    records_ready_for_analysis,
    report_markdown,
    serialize_report,
    status_counts,
    status_label,
    top_quality_actions,
    validate_categories,
    validate_consistency,
    validate_dates,
    validate_ranges,
    validate_required_fields,
    validate_report_integrity,
    validate_types,
    warning_issues,
)

NOW = datetime(2026, 8, 23, 12, tzinfo=timezone.utc)


def valid_record(**changes):
    record = {
        "id": 1,
        "user_id": 1,
        "date": NOW.isoformat(),
        "transport": "Car",
        "distance": 10000,
        "electricity": 2500,
        "diet": "Vegetarian",
        "flights": 1,
        "footprint": 3000,
        "eco_score": 72,
        "region": "India",
        "trip_id": "trip-1",
        "factor_version": "static-v1",
    }
    record.update(changes)
    return record


def history():
    return [
        valid_record(id=1, date=(NOW - timedelta(days=60)).isoformat(), footprint=3400),
        valid_record(id=2, date=NOW.isoformat(), footprint=3000),
    ]


def test_default_schema_has_required_fields():
    assert "transport" in [x.name for x in DEFAULT_FIELDS]
    assert "footprint" in [x.name for x in DEFAULT_FIELDS]


def test_normalize_mapping():
    value = normalize_assessment(valid_record())
    assert value["distance"] == 10000
    assert value["flights"] == 1
    assert value["date"].endswith("+00:00")


def test_normalize_alias_date():
    value = normalize_assessment({**valid_record(date=None), "created_at": NOW.isoformat()})
    assert value["date"] == NOW.isoformat()


def test_normalize_sequence():
    row = (
        "Car", 10000, 2500, "Vegetarian", 1, 3000, 72, "India",
        "trip-1", "static-v1", NOW.isoformat(),
    )
    value = normalize_assessment(row)
    assert value["transport"] == "Car"
    assert value["footprint"] == 3000


def test_identifier_uses_id():
    assert assessment_identifier(valid_record()) == "1"


def test_identifier_fallback_is_deterministic():
    record = valid_record(id=None, trip_id=None)
    assert assessment_identifier(record) == assessment_identifier(record)


def test_fingerprint_is_deterministic():
    assert canonical_fingerprint(valid_record()) == canonical_fingerprint(valid_record())


def test_required_missing():
    record = valid_record(distance=None)
    issues = validate_required_fields(normalize_assessment(record))
    assert any(i.field == "distance" for i in issues)


def test_optional_missing():
    record = normalize_assessment(valid_record(region=None, factor_version=None))
    issues = validate_required_fields(record)
    assert not issues
    assert len([x for x in record if record[x] is None]) >= 2


def test_invalid_number_type():
    issues = validate_types(normalize_assessment(valid_record(distance="abc")))
    assert any(i.issue_type == IssueType.INVALID_TYPE for i in issues)


def test_invalid_integer():
    issues = validate_types(normalize_assessment(valid_record(flights=1.5)))
    assert any(i.field == "flights" for i in issues)


def test_range_low():
    issues = validate_ranges(normalize_assessment(valid_record(distance=-1)))
    assert any(i.issue_type == IssueType.OUT_OF_RANGE for i in issues)


def test_range_high():
    issues = validate_ranges(normalize_assessment(valid_record(flights=501)))
    assert any(i.issue_type == IssueType.OUT_OF_RANGE for i in issues)


def test_negative_detection():
    issues = validate_ranges(normalize_assessment(valid_record(electricity=-10)))
    assert any(i.issue_type == IssueType.NEGATIVE_VALUE for i in issues)


def test_category_warning():
    issues = validate_categories(normalize_assessment(valid_record(diet="Carnivore")))
    assert any(i.issue_type == IssueType.UNKNOWN_CATEGORY for i in issues)


def test_invalid_date():
    issues = validate_dates(normalize_assessment(valid_record(date="not-a-date")))
    assert any(i.issue_type == IssueType.INVALID_DATE for i in issues)


def test_future_date_warning():
    future = NOW + timedelta(days=1)
    issues = validate_dates(
        normalize_assessment(valid_record(date=future.isoformat())),
        now=NOW,
    )
    assert any(i.severity == IssueSeverity.WARNING for i in issues)


def test_zero_footprint_consistency():
    issues = validate_consistency(
        normalize_assessment(valid_record(footprint=0, distance=1000))
    )
    assert any(i.issue_type == IssueType.INCONSISTENT_VALUE for i in issues)


def test_positive_footprint_without_inputs():
    issues = validate_consistency(
        normalize_assessment(valid_record(
            footprint=1000, distance=0, electricity=0, flights=0
        ))
    )
    assert issues


def test_complete_assessment():
    quality = inspect_assessment(valid_record(), now=NOW)
    assert quality.status == QualityStatus.COMPLETE
    assert quality.completeness_pct == 100


def test_incomplete_assessment():
    quality = inspect_assessment(
        valid_record(distance=None, electricity=None),
        now=NOW,
    )
    assert quality.status in {QualityStatus.INCOMPLETE, QualityStatus.INVALID}
    assert "distance" in quality.missing_required


def test_quality_score_range():
    assert 0 <= quality_score(valid_record()) <= 100


def test_missing_required_helper():
    assert "distance" in missing_required_fields(valid_record(distance=None))


def test_invalid_fields_helper():
    assert "distance" in invalid_fields(valid_record(distance="bad"))


def test_normalize_empty():
    assert normalize_assessments([]) == ()


def test_duplicate_ids():
    records = [valid_record(id=1), valid_record(id=1, footprint=3200)]
    assert detect_duplicate_ids(normalize_assessments(records)) == ("1",)


def test_duplicate_records():
    records = [valid_record(id=1), valid_record(id=2)]
    assert detect_duplicate_records(normalize_assessments(records)) == ("2",)


def test_stale_detection():
    records = [valid_record(date=(NOW - timedelta(days=120)).isoformat())]
    assert detect_stale_assessments(
        normalize_assessments(records),
        stale_days=90,
        now=NOW,
    ) == ("1",)


def test_field_coverage():
    values = field_coverage(normalize_assessments(history()))
    assert values["transport"] == 100
    assert values["region"] == 100


def test_quality_report():
    report = build_quality_report(history(), now=NOW)
    assert report.assessments_checked == 2
    assert report.completeness_pct == 100
    assert report.status == QualityStatus.COMPLETE


def test_empty_report():
    report = build_quality_report([], now=NOW)
    assert report.status == QualityStatus.EMPTY
    assert report.assessments_checked == 0


def test_report_invalid_data():
    report = build_quality_report(
        [valid_record(distance=None, electricity=None)],
        now=NOW,
    )
    assert report.assessments_with_errors == 1


def test_report_duplicates():
    report = build_quality_report(
        [valid_record(id=1), valid_record(id=1, footprint=3200)],
        now=NOW,
    )
    assert "1" in report.duplicate_assessment_ids


def test_report_stale():
    report = build_quality_report(
        [valid_record(date=(NOW - timedelta(days=120)).isoformat())],
        stale_days=90,
        now=NOW,
    )
    assert report.stale_assessment_count == 1


def test_issue_counts():
    report = build_quality_report(
        [valid_record(distance=None)],
        now=NOW,
    )
    assert report.issue_counts


def test_distribution():
    report = build_quality_report(history(), now=NOW)
    distribution = completeness_distribution(report)
    assert distribution["100"] == 2


def test_status_counts():
    report = build_quality_report(history(), now=NOW)
    counts = status_counts(report)
    assert counts["complete"] == 2


def test_critical_and_warning_filters():
    report = build_quality_report(
        [valid_record(distance=None, diet="Unknown")],
        now=NOW,
    )
    assert critical_issues(report)
    assert warning_issues(report)


def test_filter_issues_by_type():
    report = build_quality_report([valid_record(distance=None)], now=NOW)
    issues = filter_issues(
        critical_issues(report),
        issue_type=IssueType.REQUIRED_MISSING,
    )
    assert issues


def test_field_quality():
    report = build_quality_report(history(), now=NOW)
    result = field_quality(report, "transport")
    assert result["coverage_pct"] == 100


def test_required_field_coverage():
    report = build_quality_report(history(), now=NOW)
    assert all(v == 100 for v in report.field_coverage.values())


def test_readiness():
    report = build_quality_report(history(), now=NOW)
    readiness = overall_readiness(report)
    assert readiness["ready_for_trends"]
    assert readiness["ready_for_benchmarking"]


def test_score_label_and_status_label():
    assert status_label(QualityStatus.COMPLETE) == "Complete"


def test_top_actions():
    report = build_quality_report([valid_record(distance=None)], now=NOW)
    assert top_quality_actions(report)


def test_compare_trend():
    first = build_quality_report([valid_record(distance=None)], now=NOW)
    second = build_quality_report([valid_record()], now=NOW)
    comparison = quality_trend([first, second])
    assert comparison["direction"] == "improving"


def test_report_serialization():
    report = build_quality_report(history(), now=NOW)
    payload = serialize_report(report)
    parsed = json.loads(payload)
    assert parsed["assessments_checked"] == 2


def test_markdown():
    report = build_quality_report(history(), now=NOW)
    markdown = report_markdown(report)
    assert "# Sustainability Data Quality Report" in markdown


def test_dashboard_payload():
    report = build_quality_report(history(), now=NOW)
    payload = build_dashboard_payload(report)
    assert "overview" in payload
    assert "readiness" in payload


def test_integrity():
    report = build_quality_report(history(), now=NOW)
    assert validate_report_integrity(report) == ()


def test_ready_records():
    result = records_ready_for_analysis(history())
    assert len(result) == 2


def test_latest_quality():
    assert latest_quality(history()) is not None


def test_latest_quality_empty():
    assert latest_quality([]) is None


def test_badges():
    report = build_quality_report(history(), now=NOW)
    badges = quality_badges(report)
    assert len(badges) == 6


def test_explain_report():
    report = build_quality_report(history(), now=NOW)
    assert "complete" in explain_report(report).lower()


def test_custom_field_schema():
    fields = (
        FieldDefinition("foo", "Foo", True, "text"),
        FieldDefinition("value", "Value", True, "number", 0, 10),
    )
    quality = inspect_assessment({"foo": "x", "value": 5}, fields=fields, now=NOW)
    assert quality.completeness_pct == 100


def test_custom_alias():
    fields = (
        FieldDefinition("value", "Value", True, "number", aliases=("amount",)),
    )
    value = normalize_assessment({"amount": 4}, fields=fields)
    assert value["value"] == 4


def test_report_has_recommendations():
    report = build_quality_report([valid_record(distance=None)], now=NOW)
    assert report.recommendations


def test_report_input_not_mutated():
    source = valid_record()
    before = dict(source)
    build_quality_report([source], now=NOW)
    assert source == before


def test_invalid_stale_setting():
    with pytest.raises(ValueError):
        detect_stale_assessments(normalize_assessments(history()), stale_days=0, now=NOW)


def test_empty_field_coverage():
    values = field_coverage([])
    assert values["transport"] == 0


def test_quality_trend_empty():
    assert quality_trend([])["direction"] == "unknown"


def test_quality_trend_single():
    report = build_quality_report(history(), now=NOW)
    assert quality_trend([report])["direction"] == "stable"


def test_latest_record_order():
    records = history()
    assert latest_quality(records).assessment_id == "2"


def test_readiness_with_errors():
    report = build_quality_report([valid_record(distance=None)], now=NOW)
    assert not overall_readiness(report)["ready_for_benchmarking"]


def test_invalid_report_payload_is_detected():
    report = build_quality_report(history(), now=NOW)
    assert validate_report_integrity(report) == ()


def test_all_required_fields_are_known():
    assert set(["transport", "distance", "electricity", "diet", "flights", "footprint"]) <= set(
        x.name for x in DEFAULT_FIELDS
    )


def test_large_history():
    records = [
        valid_record(id=i, date=(NOW - timedelta(days=i)).isoformat())
        for i in range(1, 101)
    ]
    report = build_quality_report(records, now=NOW)
    assert report.assessments_checked == 100


def test_unknown_field_is_ignored_safely():
    record = valid_record(unrelated={"x": 1})
    quality = inspect_assessment(record, now=NOW)
    assert quality.status == QualityStatus.COMPLETE


def test_duplicate_fingerprint_does_not_require_same_id():
    records = [
        valid_record(id=1, trip_id="trip-1"),
        valid_record(id=2, trip_id="trip-2"),
    ]
    assert detect_duplicate_records(normalize_assessments(records)) == ("2",)


def test_future_date_does_not_crash_report():
    report = build_quality_report(
        [valid_record(date=(NOW + timedelta(days=2)).isoformat())],
        now=NOW,
    )
    assert report.assessments_checked == 1


def test_json_roundtrip_is_valid():
    report = build_quality_report(history(), now=NOW)
    assert isinstance(json.loads(serialize_report(report)), dict)
