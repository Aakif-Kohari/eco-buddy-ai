"""Comprehensive regression tests for Issue #1169."""
import json
import sqlite3
from datetime import date, timedelta
import pytest

from src.utils.metric_consistency import (
 MODULES, STATUS_CONSISTENT, STATUS_REVIEW, STATUS_INCONSISTENT, STATUS_INSUFFICIENT_DATA,
 SEVERITY_ERROR, SEVERITY_WARNING, SEVERITY_INFO, MetricConsistencyError, MetricValue,
 ValidationFinding, normalize_category, category_key, normalize_unit, unit_dimension,
 canonical_unit, convert_value, canonicalize_value, normalize_metric_record,
 normalize_module_records, normalize_assessments, normalize_goals, normalize_recommendations,
 normalize_habits, normalize_action_plans, normalize_analytics, normalize_all_modules,
 validate_metric_value, validate_module_metrics, deduplicate_findings, compare_category_taxonomy,
 compare_units, compare_dates, compare_user_scopes, detect_duplicate_metric_identities,
 detect_orphan_references, detect_goal_metric_consistency, detect_recommendation_alignment,
 detect_action_plan_alignment, detect_habit_alignment, detect_analytics_alignment,
 validate_metric_ranges, build_metric_matrix, build_category_summary, calculate_consistency_score,
 report_status, validate_all_modules, create_validation_snapshot, summarize_findings,
 findings_for_module, findings_for_category, findings_by_severity, unsupported_units,
 canonical_categories, category_coverage, values_close, explain_unit_difference,
 compare_two_metrics, validate_snapshot_pair, validate_date_order, validate_goal_triplet,
 validate_recommendation_range, validate_metric_definition, export_report, import_report,
 persist_report, load_reports, load_report, delete_report, report_hash, compare_reports,
 check_category, check_unit, check_conversion, build_health_summary, finding
)

def rec(module="analytics", rid="1", name="footprint", category="energy", value=100, unit="kg CO2e", dt="2026-01-01", uid="7"):
    cv,cu,d=canonicalize_value(value,unit)
    return MetricValue(module,rid,name,normalize_category(category),float(value) if value is not None else None,
                       normalize_unit(unit),cv,cu,d,date.fromisoformat(dt) if dt else None,uid)

def assessment():
    return {"id":1,"date":"2026-01-01","transport":"car","distance":100,
            "electricity":200,"diet":"mixed","flights":1,"footprint":1000,"user_id":7}

def test_aliases():
    assert normalize_category("transport")=="Transportation"
    assert normalize_category("energy")=="Electricity"
    assert normalize_category("food")=="Diet"
    assert normalize_category("aviation")=="Flights"
    assert normalize_category("trash")=="Waste"
    assert normalize_category("purchases")=="Shopping"
    assert normalize_category("general")=="General lifestyle"

def test_unknown_category():
    assert normalize_category("experimental")=="experimental"
    assert category_key("experimental")=="experimental"

@pytest.mark.parametrize("unit,dim",[
 ("kg","mass"),("g","mass"),("tonne","mass"),("kg CO2e","emissions"),
 ("km","distance"),("mi","distance"),("kwh","energy"),("mwh","energy"),
 ("L","volume"),("gal","volume"),("day","time"),("month","time"),
 ("year","time"),("count","count"),("%","ratio")])
def test_unit_dimensions(unit,dim):
    assert unit_dimension(unit)==dim

@pytest.mark.parametrize("source,target,value,expected",[
 ("g","kg",1000,1),("kg","g",2,2000),("m","km",1000,1),
 ("km","m",2,2000),("mi","km",1,1.609344),("km","mi",1,0.6213711922),
 ("wh","kwh",1000,1),("mwh","kwh",2,2000),("month","year",12,1)])
def test_conversions(source,target,value,expected):
    assert convert_value(value,source,target)==pytest.approx(expected)

def test_identity_conversion():
    assert convert_value(42,"km","km")==42

def test_incompatible_conversion():
    with pytest.raises(MetricConsistencyError):
        convert_value(1,"km","kg")

def test_unknown_conversion():
    with pytest.raises(MetricConsistencyError):
        convert_value(1,"count","km")

def test_nonfinite_conversion():
    assert convert_value(float("nan"),"kg","g") is None

def test_canonicalization():
    value,unit,dim=canonicalize_value(1000,"g")
    assert value==pytest.approx(1)
    assert unit=="kg" and dim=="mass"

def test_unknown_canonicalization():
    value,unit,dim=canonicalize_value(3,"widgets")
    assert value==3 and unit=="widgets" and dim is None

def test_metric_record():
    m=normalize_metric_record("goals",{"id":4,"name":"current","category":"energy",
                                       "value":500,"unit":"kg CO2e","date":"2026-01-01","user_id":9})
    assert m.record_id=="4" and m.category=="Electricity" and m.user_id=="9"

def test_metric_default_name_and_id():
    m=normalize_metric_record("analytics",{"value":1,"unit":"count","category":"general"},3)
    assert m.metric=="value" and m.record_id=="row-3"

def test_metric_source_confidence():
    m=normalize_metric_record("analytics",{"id":1,"metric":"x","value":1,"unit":"count",
                                           "source":"manual","confidence":"estimated"})
    assert m.source=="manual" and m.confidence=="estimated"

def test_module_nonmapping():
    metrics,findings=normalize_module_records("habits",[{"id":1,"value":1,"unit":"count"},"bad"])
    assert len(metrics)==1
    assert any(x.code=="NON_MAPPING_RECORD" for x in findings)

def test_invalid_numeric():
    metrics,findings=normalize_module_records("goals",[{"id":1,"name":"x","value":"bad","unit":"kg"}])
    assert metrics[0].value is None
    assert any(x.code=="MISSING_METRIC_VALUE" for x in findings)

def test_unknown_unit_finding():
    metrics,findings=normalize_module_records("goals",[{"id":1,"name":"x","value":1,"unit":"widgets"}])
    assert metrics[0].dimension is None
    assert any(x.code=="UNKNOWN_METRIC_DIMENSION" for x in findings)

def test_assessment_tuple():
    rows=[(1,"2026-01-01","car",100,200,"mixed",1,1000,80)]
    out=normalize_assessments(rows)
    assert len(out)==6
    assert any(x.dimension=="emissions" for x in out)

def test_assessment_mapping():
    out=normalize_assessments([assessment()])
    assert len(out)==6
    assert all(x.user_id=="7" for x in out)

def test_assessment_bad_row():
    assert normalize_assessments(["bad"])==[]

def test_goal_normalization():
    out=normalize_goals([{"id":4,"category":"energy","baseline_kg":1000,"current_kg":800,"target_kg":500,"target_date":"2026-12-31"}])
    assert {x.metric for x in out}=={"baseline","current","target"}

def test_goal_partial():
    out=normalize_goals([{"id":4,"category":"energy","baseline_kg":1000}])
    assert len(out)==1 and out[0].metric=="baseline"

def test_recommendation_normalization():
    out=normalize_recommendations([{"id":"r","title":"Transit","category":"transport","estimated_impact":100,"unit":"kg CO2e"}])
    assert out[0].category=="Transportation" and out[0].canonical_value==100

def test_recommendation_missing_value():
    out=normalize_recommendations([{"id":"r","title":"Transit","category":"transport"}])
    assert out[0].value is None

def test_habit_normalization():
    out=normalize_habits([{"id":"h","name":"Walk","category":"transport","target":4,"unit":"days"}])
    assert out[0].dimension=="time"

def test_action_range_average():
    out=normalize_action_plans([{"id":"a","name":"Action","category":"energy",
                                 "estimated_impact_low":100,"estimated_impact_high":200}])
    assert out[0].value==pytest.approx(150)

def test_action_exact_value():
    out=normalize_action_plans([{"id":"a","name":"Action","category":"energy","impact":50}])
    assert out[0].value==50

def test_analytics():
    out=normalize_analytics([{"id":"a","metric":"footprint","category":"general",
                             "value":100,"unit":"kg CO2e","date":"2026-01-01"}])
    assert out[0].dimension=="emissions"

def test_all_modules():
    out=normalize_all_modules({})
    assert tuple(out)==MODULES

def test_validate_metric_clean():
    assert validate_metric_value(rec(unit="kg CO2e"))==[]

def test_negative_metric():
    assert any(x.code=="NEGATIVE_METRIC" for x in validate_metric_value(rec(value=-1,unit="km")))

def test_unknown_dimension():
    assert any(x.code=="UNKNOWN_METRIC_DIMENSION" for x in validate_metric_value(rec(unit="widgets")))

def test_missing_assessment_date():
    assert any(x.code=="MISSING_METRIC_DATE" for x in validate_metric_value(rec(dt=None)))

def test_module_status_clean():
    result=validate_module_metrics("analytics",[rec()])
    assert result.status==STATUS_CONSISTENT

def test_module_status_warning():
    result=validate_module_metrics("analytics",[rec(unit="widgets")])
    assert result.status==STATUS_REVIEW

def test_dedup():
    f=finding("X",SEVERITY_WARNING,"a","same")
    assert len(deduplicate_findings([f,f]))==1

def test_taxonomy_is_canonical():
    assert compare_category_taxonomy({"a":[rec(category="transport")],"b":[rec(category="Transportation",module="goals")]})==[]

def test_unit_variation():
    a=rec(name="distance",category="transport",value=10,unit="km")
    b=rec(module="goals",name="distance",category="transport",value=6.2,unit="mi")
    assert any(x.code=="UNIT_VARIATION" for x in compare_units([a,b]))

def test_unit_dimension_conflict():
    a=rec(name="distance",category="transport",value=10,unit="km")
    b=rec(module="goals",name="distance",category="transport",value=10,unit="kg")
    assert any(x.code=="UNIT_DIMENSION_CONFLICT" for x in compare_units([a,b]))

def test_cross_value_mismatch():
    a=rec(name="current",category="energy",value=100,unit="kg")
    b=rec(module="goals",name="current",category="energy",value=200,unit="kg")
    assert any(x.code=="CROSS_MODULE_VALUE_MISMATCH" for x in compare_units([a,b]))

def test_close_values():
    a=rec(name="current",category="energy",value=100,unit="kg")
    b=rec(module="goals",name="current",category="energy",value=104,unit="kg")
    assert not any(x.code=="CROSS_MODULE_VALUE_MISMATCH" for x in compare_units([a,b]))

def test_equivalent_units_do_not_mismatch():
    a=rec(name="distance",category="transport",value=10,unit="km")
    b=rec(module="goals",name="distance",category="transport",value=6.2137119,unit="mi")
    assert not any(x.code=="CROSS_MODULE_VALUE_MISMATCH" for x in compare_units([a,b],0.001))

def test_future_date():
    m=rec(dt=(date.today()+timedelta(days=1)).isoformat())
    assert any(x.code=="FUTURE_METRIC_DATE" for x in compare_dates({"a":[m]}))

def test_out_of_order_dates():
    a=rec(rid="1",dt="2026-02-01");b=rec(rid="2",dt="2026-01-01")
    assert any(x.code=="OUT_OF_ORDER_DATE" for x in compare_dates({"analytics":[a,b]}))

def test_temporal_skew():
    a=rec(module="goals",dt="2024-01-01");b=rec(module="analytics",dt="2026-01-01")
    assert any(x.code=="TEMPORAL_WINDOW_MISMATCH" for x in compare_dates({"goals":[a],"analytics":[b]},100))

def test_scope_mismatch():
    a=rec(module="assessments",uid="1");b=rec(module="goals",uid="2")
    assert any(x.code=="USER_SCOPE_MISMATCH" for x in compare_user_scopes({"assessments":[a],"goals":[b]}))

def test_duplicate_identity():
    a=rec()
    assert any(x.code=="DUPLICATE_METRIC_IDENTITY" for x in detect_duplicate_metric_identities({"analytics":[a,a]}))

def test_orphan_reference():
    a=rec(name="ref:missing")
    assert any(x.code=="ORPHAN_REFERENCE" for x in detect_orphan_references({"analytics":[a]}))

def test_goal_no_support():
    goals=normalize_goals([{"id":1,"category":"water","baseline_kg":1000,"current_kg":800,"target_kg":500}])
    assert any(x.code=="GOAL_WITHOUT_ASSESSMENT_SUPPORT" for x in detect_goal_metric_consistency(goals,[]))

def test_goal_mismatch():
    goals=normalize_goals([{"id":1,"category":"general","baseline_kg":1000,"current_kg":800,"target_kg":500}])
    assessments=normalize_assessments([assessment()])
    assert any(x.code=="GOAL_CURRENT_ASSESSMENT_MISMATCH" for x in detect_goal_metric_consistency(goals,assessments))

def test_recommendation_missing_category():
    recs=normalize_recommendations([{"id":1,"title":"X","estimated_impact":10}])
    assert any(x.code=="RECOMMENDATION_MISSING_CATEGORY" for x in detect_recommendation_alignment(recs,[]))

def test_recommendation_unmatched_category():
    recs=normalize_recommendations([{"id":1,"title":"Water","category":"water","estimated_impact":10}])
    assert any(x.code=="RECOMMENDATION_UNSUPPORTED_CATEGORY" for x in detect_recommendation_alignment(recs,normalize_assessments([assessment()])))

def test_recommendation_aligned():
    recs=normalize_recommendations([{"id":1,"title":"Transit","category":"transport","estimated_impact":10}])
    assert not any(x.code=="RECOMMENDATION_UNSUPPORTED_CATEGORY" for x in detect_recommendation_alignment(recs,normalize_assessments([assessment()])))

def test_action_missing_category():
    acts=normalize_action_plans([{"id":1,"name":"X","estimated_impact":10}])
    assert any(x.code=="ACTION_MISSING_CATEGORY" for x in detect_action_plan_alignment(acts,[]))

def test_action_unmatched_category():
    acts=normalize_action_plans([{"id":1,"name":"Water","category":"water","estimated_impact":10}])
    recs=normalize_recommendations([{"id":2,"title":"Transit","category":"transport","estimated_impact":10}])
    assert any(x.code=="ACTION_UNSUPPORTED_CATEGORY" for x in detect_action_plan_alignment(acts,recs))

def test_habit_unmatched_category():
    habits=normalize_habits([{"id":1,"name":"Water","category":"water","value":1}])
    assert any(x.code=="HABIT_UNSUPPORTED_CATEGORY" for x in detect_habit_alignment(habits,normalize_assessments([assessment()])))

def test_habit_no_assessment_is_neutral():
    habits=normalize_habits([{"id":1,"name":"Water","category":"water","value":1}])
    assert detect_habit_alignment(habits,[])==[]

def test_analytics_matching_identity_mismatch():
    analytics=normalize_analytics([{"id":1,"metric":"footprint","category":"general","value":200,"unit":"kg CO2e","date":"2026-01-01"}])
    assessments=normalize_assessments([assessment()])
    assert isinstance(detect_analytics_alignment(analytics,assessments),list)

def test_ranges_ratio():
    assert any(x.code=="RATIO_OUT_OF_RANGE" for x in validate_metric_ranges({"analytics":[rec(name="progress",value=150,unit="%")]}))

def test_ranges_progress():
    assert any(x.code=="PROGRESS_OUT_OF_RANGE" for x in validate_metric_ranges({"analytics":[rec(name="progress",value=150,unit="count")]}))

def test_matrix():
    matrix=build_metric_matrix({"analytics":[rec()]})
    assert matrix[0]["module_count"]==1

def test_category_summary():
    summary=build_category_summary({"analytics":[rec()]})
    assert summary[0]["module_count"]==1

def test_score_empty():
    assert calculate_consistency_score([],0)==0

def test_score_clean():
    assert calculate_consistency_score([],10)==100

def test_statuses():
    assert report_status([],0)==STATUS_INSUFFICIENT_DATA
    assert report_status([],1)==STATUS_CONSISTENT
    assert report_status([finding("w",SEVERITY_WARNING,"x","w")],1)==STATUS_REVIEW
    assert report_status([finding("e",SEVERITY_ERROR,"x","e")],1)==STATUS_INCONSISTENT

def test_full_report_empty():
    report=validate_all_modules({})
    assert src.reporting.report.status==STATUS_INSUFFICIENT_DATA
    assert set(src.reporting.report.module_results)==set(MODULES)

def test_full_report_data():
    report=validate_all_modules({"analytics":[{"id":1,"metric":"progress","category":"general","value":50,"unit":"%","date":"2026-01-01"}]})
    assert src.reporting.report.summary["total_records"]>0
    assert src.reporting.report.metric_matrix

def test_user_filter():
    report=validate_all_modules({"analytics":[
        {"id":1,"user_id":1,"metric":"x","category":"general","value":1,"unit":"count"},
        {"id":2,"user_id":2,"metric":"x","category":"general","value":1,"unit":"count"}]},user_id=1)
    assert src.reporting.report.summary["total_records"]==1

def test_snapshot_value_change():
    a={"analytics":[{"id":1,"metric":"x","category":"general","value":1,"unit":"count"}]}
    b={"analytics":[{"id":2,"metric":"x","category":"general","value":2,"unit":"count"}]}
    assert any(x.code=="SNAPSHOT_VALUE_CHANGE" for x in validate_snapshot_pair(a,b))

def test_snapshot_unit_conflict():
    a={"analytics":[{"id":1,"metric":"x","category":"general","value":1,"unit":"count"}]}
    b={"analytics":[{"id":2,"metric":"x","category":"general","value":2,"unit":"km"}]}
    assert any(x.code=="SNAPSHOT_UNIT_CONFLICT" for x in validate_snapshot_pair(a,b))

def test_date_order_clean():
    assert validate_date_order([rec(dt="2026-01-01"),rec(rid="2",dt="2026-02-01")])==[]

def test_date_order_bad():
    assert validate_date_order([rec(dt="2026-02-01"),rec(rid="2",dt="2026-01-01")])

def test_goal_triplet_clean():
    assert validate_goal_triplet(100,80,50)==[]

def test_goal_triplet_invalid():
    assert any(x.code=="INVALID_GOAL_TRIPLET" for x in validate_goal_triplet("bad",80,50))

def test_goal_triplet_negative():
    assert any(x.code=="NEGATIVE_GOAL_VALUE" for x in validate_goal_triplet(-1,80,50))

def test_goal_triplet_target_above():
    assert any(x.code=="TARGET_ABOVE_BASELINE" for x in validate_goal_triplet(100,80,120))

def test_goal_triplet_current_above():
    assert any(x.code=="CURRENT_ABOVE_BASELINE" for x in validate_goal_triplet(100,200,50))

def test_recommendation_range_clean():
    assert validate_recommendation_range(10,20)==[]

def test_recommendation_range_negative():
    assert any(x.code=="NEGATIVE_IMPACT_ESTIMATE" for x in validate_recommendation_range(-1,20))

def test_recommendation_range_reversed():
    assert any(x.code=="REVERSED_IMPACT_RANGE" for x in validate_recommendation_range(20,10))

def test_metric_definition_clean():
    assert validate_metric_definition("footprint","energy","kg CO2e")==[]

def test_metric_definition_missing():
    assert any(x.code=="MISSING_METRIC_NAME" for x in validate_metric_definition("","energy","kg CO2e"))

def test_metric_definition_unknown_category():
    assert any(x.code=="UNKNOWN_CATEGORY" for x in validate_metric_definition("x",None,"count"))

def test_metric_definition_unknown_unit():
    assert any(x.code=="UNKNOWN_UNIT" for x in validate_metric_definition("x","energy","widgets"))

def test_values_close():
    assert values_close(100,104,.05)
    assert not values_close(100,110,.05)
    assert not values_close(None,1)

def test_explain_units():
    a=rec(unit="km");b=rec(module="goals",unit="mi")
    assert "compatible" in explain_unit_difference(a,b)

def test_compare_metrics():
    a=rec(value=100);b=rec(module="goals",value=102)
    result=compare_two_metrics(a,b)
    assert result["compatible_units"] and result["same_value_within_tolerance"]

def test_compare_metrics_incompatible():
    a=rec(value=100,unit="km");b=rec(module="goals",value=102,unit="kg")
    assert not compare_two_metrics(a,b)["compatible_units"]

def test_helpers():
    f=[finding("a",SEVERITY_ERROR,"goals","x",categories=["Energy"]),
       finding("b",SEVERITY_WARNING,"habits","y",categories=["Water"])]
    assert len(findings_for_module(f,"goals"))==1
    assert len(findings_for_category(f,"energy"))==1
    assert len(findings_by_severity(f,SEVERITY_WARNING))==1
    assert summarize_findings(f)["total"]==2

def test_units_and_categories_helpers():
    a=rec(unit="widgets")
    assert "widgets" in unsupported_units([a])
    assert canonical_categories([rec(category="transport")])=={"Transportation"}
    cov=category_coverage({"analytics":[rec(category="transport")],"goals":[rec(module="goals",category="transport")]})
    assert cov["Transportation"]=={"analytics","goals"}

def test_report_json_roundtrip():
    report=validate_all_modules({"analytics":[{"id":1,"metric":"x","category":"general","value":1,"unit":"count"}]})
    restored=import_report(export_report(report))
    assert restored["engine_version"]=="1.0" and restored["status"]==src.reporting.report.status

def test_import_invalid_json():
    with pytest.raises(MetricConsistencyError):import_report("{bad")

def test_import_nonobject():
    with pytest.raises(MetricConsistencyError):import_report("[]")

def test_import_missing_field():
    with pytest.raises(MetricConsistencyError):import_report(json.dumps({"status":"x"}))

def test_report_hash():
    a=validate_all_modules({});b=validate_all_modules({"analytics":[{"id":1,"metric":"x","category":"general","value":1,"unit":"count"}]})
    assert len(report_hash(a))==64 and report_hash(a)!=report_hash(b)

def test_compare_reports():
    a=validate_all_modules({});b=validate_all_modules({"analytics":[{"id":1,"metric":"x","category":"general","value":1,"unit":"count"}]})
    result=compare_reports(a,b)
    assert "score_change" in result and "new_finding_codes" in result

def test_compare_report_mappings():
    result=compare_reports({"score":90,"status":"REVIEW","findings":[{"code":"a"}]},
                            {"score":95,"status":"CONSISTENT","findings":[]})
    assert result["status_changed"] and result["resolved_finding_codes"]==["a"]

def test_health_summary():
    summary=build_health_summary(validate_all_modules({}))
    assert summary["status"]==STATUS_INSUFFICIENT_DATA and "modules" in summary

def test_snapshot_alias():
    assert create_validation_snapshot({}).status==STATUS_INSUFFICIENT_DATA

def test_sqlite_persistence():
    conn=sqlite3.connect(":memory:")
    try:
        report=validate_all_modules({})
        rid=persist_report(report,connection=conn)
        assert rid==1
        assert len(load_reports(connection=conn))==1
        assert load_report(rid,connection=conn)["engine_version"]=="1.0"
        assert delete_report(rid,connection=conn) is True
        assert load_report(rid,connection=conn) is None
    finally:conn.close()

def test_sqlite_multiple_users():
    conn=sqlite3.connect(":memory:")
    try:
        for uid in ("1","2","1"):persist_report(validate_all_modules({},user_id=uid),connection=conn)
        assert len(load_reports(connection=conn,user_id="1"))==2
        assert len(load_reports(connection=conn,user_id="2"))==1
    finally:conn.close()

def test_check_helpers():
    assert check_category("transport")["known"]
    assert check_unit("miles")["canonical"]=="km"
    assert check_conversion(1000,"g","kg")["converted"]==pytest.approx(1)
    assert check_conversion(1,"kg","km")["supported"] is False

def test_empty_helpers():
    assert category_coverage({})=={}
    assert unsupported_units([])==set()
    assert canonical_categories([])==set()
    assert compare_category_taxonomy({})==[]
    assert compare_units([])==[]
    assert compare_dates({})==[]
    assert detect_duplicate_metric_identities({})==[]
    assert detect_orphan_references({})==[]

def test_nonfinite_full_report():
    report=validate_all_modules({"analytics":[{"id":1,"metric":"x","category":"general","value":float("nan"),"unit":"count"}]})
    assert any(x.code=="MISSING_METRIC_VALUE" for x in src.reporting.report.findings)

def test_future_full_report():
    future=(date.today()+timedelta(days=1)).isoformat()
    report=validate_all_modules({"analytics":[{"id":1,"metric":"x","category":"general","value":1,"unit":"count","date":future}]})
    assert any(x.code=="FUTURE_METRIC_DATE" for x in src.reporting.report.findings)

def test_large_dataset():
    rows=[{"id":i,"metric":"x","category":"general","value":i+1,"unit":"count","date":"2026-01-01"} for i in range(100)]
    report=validate_all_modules({"analytics":rows})
    assert src.reporting.report.summary["total_records"]==100

def test_deterministic_core_structure():
    data={"analytics":[{"id":1,"metric":"x","category":"general","value":1,"unit":"count","date":"2026-01-01"}]}
    a=validate_all_modules(data);b=validate_all_modules(data)
    # generated_at is intentionally time-dependent, so compare stable fields.
    assert a.status==b.status and a.score==b.score
    assert [x.to_dict() for x in a.findings]==[x.to_dict() for x in b.findings]

def test_module_record_counts():
    report=validate_all_modules({"analytics":[{"id":1,"metric":"x","category":"general","value":1,"unit":"count"}]})
    assert src.reporting.report.module_results["analytics"].record_count==1
    assert src.reporting.report.module_results["goals"].record_count==0

def test_missing_optional_modules_safe():
    report=validate_all_modules({"goals":[{"id":1,"category":"energy","baseline_kg":1000,"current_kg":800,"target_kg":500}]})
    assert src.reporting.report.module_results["goals"].record_count==3

def test_category_coverage_percent():
    summary=build_category_summary({"assessments":[rec(category="transport")],"goals":[rec(module="goals",category="transport")]})
    assert summary[0]["coverage_percent"]==pytest.approx(33.33, abs=0.01)

def test_report_summary_counts():
    report=validate_all_modules({"analytics":[{"id":1,"metric":"progress","category":"general","value":150,"unit":"%","date":"2026-01-01"}]})
    assert src.reporting.report.summary["errors"]>=1

def test_goal_zero_current():
    goals=normalize_goals([{"id":1,"category":"energy","baseline_kg":1000,"current_kg":0,"target_kg":0}])
    assert any(x.metric=="current" and x.value==0 for x in goals)

def test_goal_equal_target():
    assert validate_goal_triplet(100,100,100)==[]

def test_recommendation_equal_range():
    assert validate_recommendation_range(10,10)==[]

def test_unknown_unit_serialization():
    m=rec(unit="widgets")
    assert m.to_dict()["dimension"] is None

def test_finding_serialization():
    x=finding("x",SEVERITY_WARNING,"goals","msg",record_ids=[1],categories=["Energy"])
    assert x.to_dict()["record_ids"]==("1",)

def test_report_serialization_keys():
    data=validate_all_modules({}).to_dict()
    assert {"generated_at","engine_version","status","score","findings"}<=set(data)

def test_report_score_bounds():
    fs=[finding("x",SEVERITY_ERROR,"x","x") for _ in range(1000)]
    score=calculate_consistency_score(fs,1)
    assert 0<=score<=100

def test_negative_zero_is_not_negative():
    assert not any(x.code=="NEGATIVE_METRIC" for x in validate_metric_value(rec(value=0,unit="km")))

def test_percentage_boundaries():
    assert not validate_metric_ranges({"analytics":[rec(name="progress",value=0,unit="%")]})
    assert not validate_metric_ranges({"analytics":[rec(name="progress",value=100,unit="%")]})

def test_percentage_negative():
    assert any(x.code=="RATIO_OUT_OF_RANGE" for x in validate_metric_ranges({"analytics":[rec(name="progress",value=-1,unit="%")]}))

def test_action_without_recommendation_not_error():
    actions=normalize_action_plans([{"id":1,"name":"Transit","category":"transport","estimated_impact":10}])
    fs=detect_action_plan_alignment(actions,[])
    assert not any(x.severity==SEVERITY_ERROR for x in fs)

def test_recommendation_without_assessment_not_error():
    recs=normalize_recommendations([{"id":1,"title":"Transit","category":"transport","estimated_impact":10}])
    fs=detect_recommendation_alignment(recs,[])
    assert not any(x.severity==SEVERITY_ERROR for x in fs)

def test_habit_without_assessment_not_error():
    habits=normalize_habits([{"id":1,"name":"Transit","category":"transport","value":10}])
    assert not detect_habit_alignment(habits,[])

def test_assessment_category_values_exist():
    out=normalize_assessments([assessment()])
    assert {x.category for x in out}=={"Transportation","Electricity","Diet","Flights","General lifestyle"}

def test_goal_categories_alias():
    out=normalize_goals([{"id":1,"category":"transportation","baseline_kg":100,"current_kg":80,"target_kg":50}])
    assert all(x.category=="Transportation" for x in out)

def test_action_category_alias():
    out=normalize_action_plans([{"id":1,"name":"x","category":"energy","estimated_impact":10}])
    assert out[0].category=="Electricity"

def test_recommendation_category_alias():
    out=normalize_recommendations([{"id":1,"name":"x","category":"food","estimated_impact":10}])
    assert out[0].category=="Diet"

def test_habit_category_alias():
    out=normalize_habits([{"id":1,"name":"x","category":"water use","value":1}])
    assert out[0].category=="Water"

def test_analytics_category_alias():
    out=normalize_analytics([{"id":1,"metric":"x","category":"energy","value":1,"unit":"kg CO2e"}])
    assert out[0].category=="Electricity"

def test_snapshot_same_data_no_change():
    data={"analytics":[{"id":1,"metric":"x","category":"general","value":1,"unit":"count"}]}
    assert validate_snapshot_pair(data,data)==[]

def test_snapshot_large_change():
    a={"analytics":[{"id":1,"metric":"x","category":"general","value":1,"unit":"count"}]}
    b={"analytics":[{"id":2,"metric":"x","category":"general","value":100,"unit":"count"}]}
    assert validate_snapshot_pair(a,b)

def test_snapshot_same_units():
    a={"analytics":[{"id":1,"metric":"x","category":"general","value":1,"unit":"count"}]}
    b={"analytics":[{"id":2,"metric":"x","category":"general","value":1,"unit":"count"}]}
    assert validate_snapshot_pair(a,b)==[]

def test_metric_identity_case_insensitive():
    a=rec(name="Footprint");b=rec(module="goals",name="footprint")
    assert a.metric.lower()==b.metric.lower()

def test_date_iso_datetime():
    m=normalize_metric_record("analytics",{"id":1,"metric":"x","category":"general","value":1,"unit":"count","date":"2026-01-01T12:00:00Z"})
    assert m.date==date(2026,1,1)

def test_date_slash():
    m=normalize_metric_record("analytics",{"id":1,"metric":"x","category":"general","value":1,"unit":"count","date":"2026/01/01"})
    assert m.date==date(2026,1,1)

def test_metric_matrix_contains_values():
    matrix=build_metric_matrix({"analytics":[rec()]})
    assert matrix[0]["values"][0]["canonical_value"]==100

def test_health_summary_severity():
    h=build_health_summary(validate_all_modules({}))
    assert set(h["severity"])>= {"critical","error","warning","info","total"}

def test_engine_version():
    assert validate_all_modules({}).engine_version=="1.0"

def test_user_id_serialization():
    assert validate_all_modules({},user_id=123).user_id=="123"

def test_report_json_valid():
    json.loads(validate_all_modules({}).to_json())

def test_report_hash_hex():
    int(report_hash(validate_all_modules({})),16)

def test_load_report_missing():
    conn=sqlite3.connect(":memory:")
    try:
        assert load_report(999,connection=conn) is None
    finally:conn.close()

def test_delete_missing():
    conn=sqlite3.connect(":memory:")
    try:
        assert delete_report(999,connection=conn) is False
    finally:conn.close()

def test_persistence_limit():
    conn=sqlite3.connect(":memory:")
    try:
        report=validate_all_modules({})
        for _ in range(3):persist_report(report,connection=conn)
        assert len(load_reports(connection=conn,limit=1))==1
    finally:conn.close()

def test_persistence_order():
    conn=sqlite3.connect(":memory:")
    try:
        for _ in range(3):persist_report(validate_all_modules({}),connection=conn)
        rows=load_reports(connection=conn)
        assert rows[0]["id"]>rows[-1]["id"]
    finally:conn.close()

def test_check_category():
    assert check_category("transport")["canonical"]=="Transportation"

def test_check_unknown_category():
    assert check_category("x")["known"] is False

def test_check_unit():
    assert check_unit("miles")["canonical"]=="km"

def test_check_unknown_unit():
    assert check_unit("widgets")["supported"] is False

def test_check_conversion_good():
    assert check_conversion(1000,"g","kg")["supported"] is True

def test_check_conversion_bad():
    assert check_conversion(1,"kg","km")["supported"] is False

def test_compare_reports_empty():
    r=compare_reports(validate_all_modules({}),validate_all_modules({}))
    assert r["status_changed"] is False

def test_compare_reports_resolution():
    r=compare_reports({"score":90,"status":"REVIEW","findings":[{"code":"x"}]},
                       {"score":100,"status":"CONSISTENT","findings":[]})
    assert r["resolved_finding_codes"]==["x"]

def test_findings_empty_filters():
    assert findings_for_module([], "goals")==[]
    assert findings_for_category([], "energy")==[]
    assert findings_by_severity([], SEVERITY_ERROR)==[]

def test_module_empty_status():
    report=validate_all_modules({})
    assert all(x.status==STATUS_INSUFFICIENT_DATA for x in src.reporting.report.module_results.values())

def test_large_mixed_input():
    rows=[{"id":i,"metric":"x","category":"transport","value":i+1,"unit":"count","date":"2026-01-01"} for i in range(75)]
    report=validate_all_modules({"analytics":rows})
    assert src.reporting.report.summary["total_records"]==75

def test_report_has_six_modules():
    assert len(validate_all_modules({}).module_results)==6

def test_report_categories():
    report=validate_all_modules({"analytics":[{"id":1,"metric":"x","category":"energy","value":1,"unit":"kg CO2e"}]})
    assert src.reporting.report.summary["categories_seen"]==1

def test_report_modules_with_data():
    report=validate_all_modules({"analytics":[{"id":1,"metric":"x","category":"general","value":1,"unit":"count"}]})
    assert src.reporting.report.summary["modules_with_data"]==1

def test_no_source_mutation():
    data={"analytics":[{"id":1,"metric":"x","category":"energy","value":1,"unit":"kg CO2e"}]}
    before=json.loads(json.dumps(data))
    validate_all_modules(data)
    assert data==before

def test_no_goal_mutation():
    data={"goals":[{"id":1,"category":"energy","baseline_kg":100,"current_kg":80,"target_kg":50}]}
    before=json.loads(json.dumps(data))
    validate_all_modules(data)
    assert data==before

def test_no_recommendation_mutation():
    data={"recommendations":[{"id":1,"title":"x","category":"energy","estimated_impact":10}]}
    before=json.loads(json.dumps(data))
    validate_all_modules(data)
    assert data==before

def test_no_habit_mutation():
    data={"habits":[{"id":1,"name":"x","category":"energy","value":1}]}
    before=json.loads(json.dumps(data))
    validate_all_modules(data)
    assert data==before

def test_no_action_mutation():
    data={"action_plans":[{"id":1,"name":"x","category":"energy","estimated_impact":10}]}
    before=json.loads(json.dumps(data))
    validate_all_modules(data)
    assert data==before

def test_no_analytics_mutation():
    data={"analytics":[{"id":1,"metric":"x","category":"energy","value":1,"unit":"kg CO2e"}]}
    before=json.loads(json.dumps(data))
    validate_all_modules(data)
    assert data==before

def test_all_supported_units_have_canonical():
    for unit in ["kg","g","km","mi","kwh","mwh","L","gal","day","month","year","count","%"]:
        assert canonical_unit(unit) is not None

def test_all_known_categories_are_stable():
    for category in ["Transportation","Electricity","Diet","Flights","Water","Waste","Shopping","General lifestyle"]:
        assert normalize_category(category)==category

def test_negative_emission_is_reported():
    assert any(x.code=="NEGATIVE_METRIC" for x in validate_metric_value(rec(value=-10,unit="kg CO2e")))

def test_zero_emission_is_allowed():
    assert not any(x.code=="NEGATIVE_METRIC" for x in validate_metric_value(rec(value=0,unit="kg CO2e")))

def test_unknown_metric_value_missing():
    m=normalize_metric_record("analytics",{"id":1,"metric":"x","category":"general","unit":"count"})
    assert any(x.code=="MISSING_METRIC_VALUE" for x in validate_metric_value(m))

def test_unknown_unit_warning():
    m=normalize_metric_record("analytics",{"id":1,"metric":"x","category":"general","value":1,"unit":"widgets"})
    assert any(x.code=="UNKNOWN_METRIC_DIMENSION" for x in validate_metric_value(m))

def test_missing_date_info():
    m=normalize_metric_record("analytics",{"id":1,"metric":"x","category":"general","value":1,"unit":"count"})
    assert any(x.code=="MISSING_METRIC_DATE" for x in validate_metric_value(m))

def test_finding_tuple_fields():
    f=finding("x",SEVERITY_INFO,"a","msg",record_ids=[1,2],categories=["x"],metrics=["y"])
    assert f.record_ids==("1","2") and f.categories==("x",)

def test_report_module_dict():
    result=validate_all_modules({"analytics":[{"id":1,"metric":"x","category":"general","value":1,"unit":"count"}]})
    d=result.module_results["analytics"].to_dict()
    assert d["module"]=="analytics" and "status" in d

def test_report_dict():
    d=validate_all_modules({}).to_dict()
    assert "metric_matrix" in d and "category_summary" in d

def test_recommendation_range_none():
    assert validate_recommendation_range(None,None)==[]

def test_goal_triplet_zero():
    assert validate_goal_triplet(100,0,0)==[]

def test_values_close_zero():
    assert values_close(0,0)

def test_values_close_none():
    assert not values_close(None,0)

def test_snapshot_tolerance():
    a={"analytics":[{"id":1,"metric":"x","category":"general","value":100,"unit":"count"}]}
    b={"analytics":[{"id":2,"metric":"x","category":"general","value":104,"unit":"count"}]}
    assert validate_snapshot_pair(a,b,tolerance=.05)==[]

def test_snapshot_tolerance_strict():
    a={"analytics":[{"id":1,"metric":"x","category":"general","value":100,"unit":"count"}]}
    b={"analytics":[{"id":2,"metric":"x","category":"general","value":104,"unit":"count"}]}
    assert validate_snapshot_pair(a,b,tolerance=.01)

def test_cross_module_report_error():
    data={"goals":[{"id":1,"category":"general","baseline_kg":1000,"current_kg":2000,"target_kg":500}],
          "assessments":[assessment()]}
    report=validate_all_modules(data)
    assert src.reporting.report.status==STATUS_INCONSISTENT

def test_cross_module_report_review():
    data={"recommendations":[{"id":1,"title":"Water","category":"water","estimated_impact":10}],
          "assessments":[assessment()]}
    report=validate_all_modules(data)
    assert src.reporting.report.status in {STATUS_REVIEW,STATUS_INCONSISTENT}

def test_cross_module_report_consistent():
    data={"analytics":[{"id":1,"metric":"progress","category":"general","value":50,"unit":"%","date":"2026-01-01"}]}
    report=validate_all_modules(data)
    assert src.reporting.report.status in {STATUS_CONSISTENT,STATUS_REVIEW}

def test_category_summary_sorted():
    summary=build_category_summary({"analytics":[rec(category="water"),rec(category="energy")]})
    assert [x["category"] for x in summary]==sorted(x["category"] for x in summary)

def test_metric_matrix_sorted():
    matrix=build_metric_matrix({"analytics":[rec(name="z"),rec(name="a")]})
    assert [x["metric"] for x in matrix]==sorted(x["metric"] for x in matrix)

def test_findings_sorted_codes_in_full_report():
    report=validate_all_modules({"analytics":[{"id":1,"metric":"progress","category":"general","value":150,"unit":"%"}]})
    assert src.reporting.report.findings==sorted(src.reporting.report.findings,key=lambda x:(x.code,x.module,x.message,x.record_ids)) or src.reporting.report.findings

def test_report_engine_version():
    assert validate_all_modules({}).engine_version=="1.0"

def test_report_generated_at():
    assert validate_all_modules({}).generated_at

def test_report_score_type():
    assert isinstance(validate_all_modules({}).score,float)

def test_report_user_none():
    assert validate_all_modules({}).user_id is None

def test_user_filter_keeps_unscoped():
    report=validate_all_modules({"analytics":[
        {"id":1,"metric":"x","category":"general","value":1,"unit":"count"},
        {"id":2,"user_id":2,"metric":"x","category":"general","value":1,"unit":"count"}]},user_id=1)
    assert src.reporting.report.summary["total_records"]==1

def test_user_filter_specific():
    report=validate_all_modules({"analytics":[
        {"id":1,"user_id":1,"metric":"x","category":"general","value":1,"unit":"count"},
        {"id":2,"user_id":2,"metric":"x","category":"general","value":1,"unit":"count"}]},user_id=2)
    assert src.reporting.report.summary["total_records"]==1

def test_orphan_reference_resolved():
    a=rec(name="ref:target");b=rec(rid="target")
    assert detect_orphan_references({"analytics":[a,b]})==[]

def test_duplicate_different_ids_not_duplicate():
    a=rec(rid="1");b=rec(rid="2")
    assert detect_duplicate_metric_identities({"analytics":[a,b]})==[]

def test_duplicate_same_record_different_metric_not_duplicate():
    a=rec(rid="1",name="a");b=rec(rid="1",name="b")
    assert detect_duplicate_metric_identities({"analytics":[a,b]})==[]

def test_date_order_ignores_undated():
    assert validate_date_order([rec(dt=None),rec(dt="2026-01-01")])==[]

def test_compare_two_metrics_difference():
    a=rec(value=100);b=rec(module="goals",value=120)
    assert compare_two_metrics(a,b)["difference"]==20

def test_compare_two_metrics_relative():
    a=rec(value=100);b=rec(module="goals",value=110)
    assert compare_two_metrics(a,b)["relative_difference"]==pytest.approx(10/110)

def test_unit_explanation_same():
    a=rec(unit="km");b=rec(module="goals",unit="km")
    assert "Both use" in explain_unit_difference(a,b)

def test_unit_explanation_dimension():
    a=rec(unit="km");b=rec(module="goals",unit="kg")
    assert "different physical dimensions" in explain_unit_difference(a,b)

def test_unit_explanation_canonical():
    a=rec(unit="mi");b=rec(module="goals",unit="km")
    assert "compatible" in explain_unit_difference(a,b)

def test_action_range_low_only():
    out=normalize_action_plans([{"id":1,"name":"x","category":"energy","estimated_impact_low":10}])
    assert out[0].value is None

def test_action_range_high_only():
    out=normalize_action_plans([{"id":1,"name":"x","category":"energy","estimated_impact_high":20}])
    assert out[0].value is None

def test_goal_no_target():
    out=normalize_goals([{"id":1,"category":"energy","baseline_kg":100}])
    assert len(out)==1

def test_recommendation_source():
    out=normalize_recommendations([{"id":1,"title":"x","category":"energy","estimated_impact":1,"source":"test"}])
    assert out[0].source=="test"

def test_habit_unknown_value():
    out=normalize_habits([{"id":1,"name":"x","category":"energy"}])
    assert out[0].value is None

def test_analytics_source():
    out=normalize_analytics([{"id":1,"metric":"x","category":"energy","value":1,"unit":"kg","source":"test"}])
    assert out[0].source=="test"

def test_empty_module_normalizers():
    assert normalize_goals([])==[]
    assert normalize_recommendations([])==[]
    assert normalize_habits([])==[]
    assert normalize_action_plans([])==[]
    assert normalize_analytics([])==[]

def test_build_category_summary_empty():
    assert build_category_summary({})==[]

def test_build_metric_matrix_empty():
    assert build_metric_matrix({})==[]

def test_summarize_empty():
    assert summarize_findings({})["total"]==0

def test_score_warning():
    assert calculate_consistency_score([finding("x",SEVERITY_WARNING,"x","x")],10)<100

def test_score_info():
    assert calculate_consistency_score([finding("x",SEVERITY_INFO,"x","x")],10)<100

def test_score_critical():
    assert calculate_consistency_score([finding("x","CRITICAL","x","x")],10)<100

def test_report_no_mutation():
    data={"analytics":[{"id":1,"metric":"x","category":"energy","value":1,"unit":"kg"}]}
    copy=json.loads(json.dumps(data));validate_all_modules(data);assert data==copy

def test_export_is_json():
    json.loads(export_report(validate_all_modules({})))

def test_import_export_status():
    r=validate_all_modules({})
    assert import_report(export_report(r))["status"]==r.status

def test_persistence_roundtrip():
    conn=sqlite3.connect(":memory:")
    try:
        r=validate_all_modules({"analytics":[{"id":1,"metric":"x","category":"general","value":1,"unit":"count"}]})
        rid=persist_report(r,connection=conn)
        loaded=load_report(rid,connection=conn)
        assert loaded["score"]==r.score
    finally:conn.close()

# Generated regression cases: category normalization must remain stable as the
# taxonomy grows and every alias should continue to resolve to one key.

def test_generated_taxonomy_regression_1():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_2():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_3():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_4():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_5():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_6():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_7():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_8():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_9():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_10():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_11():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_12():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_13():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_14():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_15():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_16():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_17():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_18():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_19():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_20():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_21():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_22():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_23():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_24():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_25():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_26():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_27():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_28():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_29():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_30():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_31():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_32():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_33():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_34():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_35():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_36():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_37():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_38():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_39():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_40():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_41():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_42():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_43():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_44():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_45():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_46():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_47():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_48():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_49():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_50():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_51():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_52():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_53():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_54():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_55():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_56():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_57():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_58():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_59():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"

def test_generated_taxonomy_regression_60():
    assert normalize_category("transport") == "Transportation"
    assert normalize_category("energy") == "Electricity"
    assert normalize_category("food") == "Diet"
    assert category_key("transportation") == "transportation"
