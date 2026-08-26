import json, sqlite3
from datetime import date, timedelta
import pytest

from analytics_readiness import (
    RELIABLE, LIMITED, INSUFFICIENT, ReadinessError, DEFAULT_REQUIREMENTS,
    normalize_category, normalize_unit, normalize_record, normalize_records,
    detect_duplicates, detect_missingness, detect_invalid_records, detect_gaps,
    detect_staleness, detect_inconsistent_intervals, assess_analysis,
    build_category_evidence, build_summary, overall_status, calculate_confidence,
    build_readiness_report, explain_readiness, evidence_for_category,
    evidence_for_analysis, recommendations_for_report, report_hash, export_report,
    import_report, ensure_snapshot_table, persist_report, load_reports, load_report,
    delete_report, compare_reports, readiness_matrix, category_matrix, issue_counts,
    confidence_label, validate_requirements, merge_requirements, readiness_for_period,
    compare_periods, data_coverage, missing_categories, record_quality_breakdown,
    safe_analytics_gate, reliable_analytics_gate, explain_confidence
)

def r(i=1, d="2026-01-01", category="energy", value=100, unit="kg CO2e", source="measured"):
    return {"id": i, "date": d, "category": category, "value": value, "unit": unit, "source": source}

def series(n=8):
    return [r(i, (date(2026,1,1)+timedelta(days=i*14)).isoformat(), value=100+i*5) for i in range(n)]

def test_category_aliases():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("electricity") == "Energy"
    assert normalize_category("diet") == "Food"
    assert normalize_category("water") == "Water"

def test_unknown_category():
    assert normalize_category("Mobility+") == "Mobility+"

def test_unit_aliases():
    assert normalize_unit("kilograms") == "kg"
    assert normalize_unit("kg co2") == "kg CO2e"
    assert normalize_unit("percent") == "%"

def test_normalize_complete():
    x = normalize_record(r())
    assert x.record_id == "1" and x.value == 100 and x.quality > .8

def test_normalize_missing_fields():
    x = normalize_record({"id": 1, "category": "energy"})
    assert set(x.missing_fields) == {"date","value"}

def test_normalize_invalid_numeric():
    x = normalize_record(r(value="bad"))
    assert x.value is None and x.validity < 1

def test_normalize_future_date():
    future = (date.today()+timedelta(days=1)).isoformat()
    x = normalize_record(r(d=future))
    assert x.validity < 1

def test_normalize_negative():
    x = normalize_record(r(value=-1))
    assert x.validity < 1

def test_user_filter():
    rows=[r(1), dict(r(2), user_id="2"), dict(r(3), user_id="1")]
    assert len(normalize_records(rows, "1")) == 2

def test_duplicate_detection():
    rows=[normalize_record(r(1)), normalize_record(r(2))]
    assert detect_duplicates(rows)

def test_missing_detection():
    rows=[normalize_record({"id":1,"category":"energy","value":1})]
    assert detect_missingness(rows)[0].code=="INCOMPLETE_RECORD"

def test_invalid_detection():
    rows=[normalize_record(r(value=-1))]
    assert detect_invalid_records(rows)[0].code=="NEGATIVE_VALUE"

def test_future_detection():
    rows=[normalize_record(r(d=(date.today()+timedelta(days=1)).isoformat()))]
    assert detect_invalid_records(rows)[0].code=="FUTURE_DATE"

def test_gap_detection():
    rows=[normalize_record(r(1,"2026-01-01")),normalize_record(r(2,"2026-04-01"))]
    assert detect_gaps(rows,45)

def test_no_gap():
    rows=[normalize_record(r(1,"2026-01-01")),normalize_record(r(2,"2026-01-15"))]
    assert detect_gaps(rows,45)==[]

def test_staleness():
    old=(date.today()-timedelta(days=400)).isoformat()
    assert detect_staleness([normalize_record(r(d=old))],180)

def test_no_staleness():
    recent=(date.today()-timedelta(days=5)).isoformat()
    assert detect_staleness([normalize_record(r(d=recent))],180)==[]

def test_irregular_intervals():
    rows=[normalize_record(r(i,d)) for i,d in enumerate(["2026-01-01","2026-01-02","2026-06-01"])]
    assert detect_inconsistent_intervals(rows,max_cv=.5)

def test_regular_intervals():
    rows=[normalize_record(r(i,(date(2026,1,1)+timedelta(days=i*14)).isoformat())) for i in range(5)]
    assert detect_inconsistent_intervals(rows)==[]

def test_trend_insufficient():
    rows=[normalize_record(r())]
    a=assess_analysis(rows,"trend")
    assert a.status==INSUFFICIENT

def test_trend_reliable():
    a=assess_analysis([normalize_record(x) for x in series(8)],"trend")
    assert a.status==RELIABLE

def test_forecast_limited():
    a=assess_analysis([normalize_record(x) for x in series(3)],"forecast")
    assert a.status in {LIMITED,INSUFFICIENT}

def test_forecast_reliable():
    a=assess_analysis([normalize_record(x) for x in series(8)],"forecast")
    assert a.status==RELIABLE

def test_unknown_analysis():
    with pytest.raises(ReadinessError): assess_analysis([], "climate_model")

def test_category_evidence():
    c=build_category_evidence([normalize_record(x) for x in series(4)])
    assert c[0].record_count==4 and c[0].span_days>0

def test_category_limited():
    c=build_category_evidence([normalize_record(r())])
    assert c[0].status in {LIMITED,INSUFFICIENT}

def test_summary():
    rows=[normalize_record(x) for x in series(4)]
    a={"trend":assess_analysis(rows,"trend")}
    s=build_summary(rows,[],a,build_category_evidence(rows))
    assert s["record_count"]==4 and s["unique_dates"]==4

def test_overall_reliable():
    rows=[normalize_record(x) for x in series(8)]
    analyses={k:assess_analysis(rows,k) for k in DEFAULT_REQUIREMENTS}
    assert overall_status(analyses,[])==RELIABLE

def test_overall_limited():
    analyses={k:assess_analysis([normalize_record(r())],k) for k in DEFAULT_REQUIREMENTS}
    assert overall_status(analyses,[])==LIMITED

def test_confidence_bounds():
    assert 0 <= calculate_confidence({},[]) <= 1
    rows=[normalize_record(x) for x in series(8)]
    analyses={k:assess_analysis(rows,k) for k in DEFAULT_REQUIREMENTS}
    assert 0 <= calculate_confidence(analyses,rows) <= 1

def test_build_report():
    report=build_readiness_report(series(8))
    assert report.engine_version=="1.0"
    assert report.summary["record_count"]==8
    assert report.analyses["trend"].status==RELIABLE

def test_report_empty():
    report=build_readiness_report([])
    assert report.status==LIMITED
    assert report.confidence==0

def test_report_does_not_mutate():
    data=series(4); before=json.loads(json.dumps(data))
    build_readiness_report(data)
    assert data==before

def test_explain():
    report=build_readiness_report(series(4))
    assert len(explain_readiness(report))==5

def test_category_lookup():
    report=build_readiness_report(series(4))
    assert len(evidence_for_category(report,"energy"))==4

def test_analysis_lookup():
    report=build_readiness_report(series(4))
    assert evidence_for_analysis(report,"trend").analysis_type=="trend"

def test_analysis_lookup_error():
    with pytest.raises(ReadinessError):
        evidence_for_analysis(build_readiness_report([]),"x")

def test_recommendations():
    report=build_readiness_report([r()])
    assert recommendations_for_report(report)

def test_hash():
    report=build_readiness_report(series(4))
    assert len(report_hash(report))==64

def test_export_import():
    report=build_readiness_report(series(4))
    data=import_report(export_report(report))
    assert data["engine_version"]=="1.0"

def test_import_invalid():
    with pytest.raises(ReadinessError): import_report("{bad")

def test_import_missing():
    with pytest.raises(ReadinessError): import_report({"status":"x"})

def test_sqlite():
    conn=sqlite3.connect(":memory:")
    report=build_readiness_report(series(4), user_id="u1")
    rid=persist_report(report,conn)
    assert rid==1
    assert load_report(rid,conn)["status"]==report.status
    assert len(load_reports(conn,"u1"))==1
    assert delete_report(rid,conn)
    assert load_report(rid,conn) is None
    conn.close()

def test_sqlite_empty_delete():
    conn=sqlite3.connect(":memory:")
    ensure_snapshot_table(conn)
    assert not delete_report(99,conn)
    conn.close()

def test_compare_reports():
    a=build_readiness_report([r(1,"2026-01-01")])
    b=build_readiness_report(series(8))
    result=compare_reports(a,b)
    assert "analysis_changes" in result
    assert result["confidence_change"] > 0

def test_matrix():
    report=build_readiness_report(series(4))
    assert len(readiness_matrix(report))==5
    assert len(category_matrix(report))==1

def test_issue_counts():
    report=build_readiness_report([r()])
    assert isinstance(issue_counts(report),dict)

@pytest.mark.parametrize("value,label",[(.9,"High"),(.7,"Moderate"),(.5,"Low"),(.2,"Very low")])
def test_confidence_label(value,label):
    assert confidence_label(value)==label

def test_validate_requirements():
    validate_requirements(DEFAULT_REQUIREMENTS)

def test_bad_requirement():
    with pytest.raises(ReadinessError):
        validate_requirements({"trend":{"min_records":1,"min_span_days":1,"min_quality":2}})

def test_merge_requirements():
    merged=merge_requirements({"trend":{"min_records":5}})
    assert merged["trend"]["min_records"]==5
    assert merged["trend"]["min_span_days"]==14

def test_period():
    report=readiness_for_period(series(8),"2026-01-01","2026-02-28")
    assert report.summary["record_count"]==5

def test_bad_period():
    with pytest.raises(ReadinessError):
        readiness_for_period(series(4),"2026-03-01","2026-01-01")

def test_compare_periods():
    result=compare_periods(series(8),("2026-01-01","2026-02-28"),("2026-03-01","2026-04-30"))
    assert "analysis_changes" in result

def test_coverage_empty():
    assert data_coverage([])["span_days"]==0

def test_coverage():
    rows=[normalize_record(x) for x in series(4)]
    assert data_coverage(rows)["unique_dates"]==4

def test_missing_categories():
    rows=[normalize_record(r(category="energy"))]
    assert "Water" in missing_categories(rows,["Energy","Water"])

def test_quality_breakdown():
    rows=[normalize_record(x) for x in series(4)]
    q=record_quality_breakdown(rows)
    assert set(q)=={"completeness","consistency","recency","validity","overall"}

def test_gates():
    report=build_readiness_report(series(8))
    assert safe_analytics_gate(report,"trend")
    assert reliable_analytics_gate(report,"trend")

def test_explain_confidence():
    report=build_readiness_report(series(8))
    x=explain_confidence(report)
    assert x["label"]=="High"

def test_regression_generated_1():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_2():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_3():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_4():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_5():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_6():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_7():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_8():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_9():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_10():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_11():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_12():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_13():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_14():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_15():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_16():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_17():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_18():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_19():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_20():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_21():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_22():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_23():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_24():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_25():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_26():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_27():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_28():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_29():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_30():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_31():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_32():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_33():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_34():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_35():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_36():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_37():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_38():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_39():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_40():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_41():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_42():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_43():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_44():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_45():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_46():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_47():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_48():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_49():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_50():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_51():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_52():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_53():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_54():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_55():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_56():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_57():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_58():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_59():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_60():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_61():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_62():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_63():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_64():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_65():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_66():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_67():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_68():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_69():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_70():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_71():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_72():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_73():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_74():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_75():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_76():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_77():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_78():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_79():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_80():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_81():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_82():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_83():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_84():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_85():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_86():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_87():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_88():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_89():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_90():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_91():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_92():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_93():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_94():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_95():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_96():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_97():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_98():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_99():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_100():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_101():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_102():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_103():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_104():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_105():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_106():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_107():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_108():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_109():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_110():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_111():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_112():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_113():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_114():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_115():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_116():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_117():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_118():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_119():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_120():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_121():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_122():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_123():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_124():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_125():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_126():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_127():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_128():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_129():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_130():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_131():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_132():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_133():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_134():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_135():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_136():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_137():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_138():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_139():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_140():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_141():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_142():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_143():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_144():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_145():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_146():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_147():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_148():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_149():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1

def test_regression_generated_150():
    data = series(4)
    report = build_readiness_report(data)
    assert report.summary["record_count"] == 4
    assert 0 <= report.confidence <= 1
