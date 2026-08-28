from datetime import datetime,timedelta,timezone
import json,pytest
from src.utils.sustainability_insights import *
N=datetime(2026,8,23,12,tzinfo=timezone.utc)
def A(a=4000,b=3600):return [{"id":1,"date":(N-timedelta(days=30)).isoformat(),"footprint":a,"transport":"Car","distance":10000,"electricity":200,"diet":"Omnivore","flights":2},{"id":2,"date":N.isoformat(),"footprint":b,"transport":"Car","distance":9000,"electricity":180,"diet":"Omnivore","flights":1}]
def C(*a,**k):return build_insight_context(*a,now=N,**k)
def test_normalize():assert len(normalize_assessments(A()))==2
def test_tuple():assert normalize_assessments([(1,1,N.isoformat(),N.isoformat(),"Car",1,2,"Omnivore",1,4000,80,None)])[0]["footprint"]==4000
def test_invalid():assert not normalize_assessments([{"date":"bad","footprint":1},{"date":N.isoformat(),"footprint":-1}])
def test_improvement():assert generate_assessment_insights(C(A()))[0].type==InsightType.IMPROVEMENT
def test_decline():assert generate_assessment_insights(C(A(3000,3600)))[0].type==InsightType.DECLINE
def test_threshold():assert not generate_assessment_insights(C(A(4000,3900)))
def test_empty_quality():assert generate_data_quality_insights(C())[0].type==InsightType.DATA_QUALITY
def test_stale():assert generate_data_quality_insights(C([{"id":1,"date":(N-timedelta(days=120)).isoformat(),"footprint":1}]))
@pytest.mark.parametrize("p",[25,50,75,100])
def test_milestone(p):assert any(x.type==InsightType.MILESTONE for x in generate_goal_insights(C([], [{"id":1,"name":"G","progress_pct":p}])))
def test_goal_calc():assert any("50.0%" in x.description for x in generate_goal_insights(C([],[{"id":1,"name":"G","baseline_footprint":5000,"target_footprint":4000,"current_footprint":4500}])))
def test_goal_missing():assert generate_goal_insights(C([],[{"id":1,"name":"G"}]))
def test_goal_risk():assert any(x.type==InsightType.GOAL_RISK for x in generate_goal_insights(C([],[{"id":1,"name":"G","progress_pct":50,"target_date":"2026-01-01"}])))
def test_habit_streak():assert generate_habit_insights(C([],habits=[{"id":1,"name":"Walk","streak":10}]))
def test_habit_low():assert generate_habit_insights(C([],habits=[{"id":1,"name":"Walk","completion_pct":10}]))
def test_rec_done():assert generate_recommendation_insights(C([],recommendations=[{"id":1,"status":"completed"}]))
def test_rec_skip():assert generate_recommendation_insights(C([],recommendations=[{"id":1,"status":"skipped"}]))
def test_category():
 x=[{"id":1,"date":(N-timedelta(days=30)).isoformat(),"footprint":4,"transport_emissions":1000},{"id":2,"date":N.isoformat(),"footprint":3,"transport_emissions":800}]
 assert generate_category_insights(C(x))
def test_all():
 x=generate_insights(C(A(),[{"id":1,"name":"G","progress_pct":50}],[{"id":1,"name":"H","streak":8}],[{"id":1,"name":"R","status":"completed"}]))
 t={i.type for i in x};assert InsightType.IMPROVEMENT in t and InsightType.GOAL_PROGRESS in t and InsightType.HABIT_STREAK in t and InsightType.RECOMMENDATION_PROGRESS in t
def test_deterministic():assert [x.id for x in generate_insights(C(A()))]==[x.id for x in generate_insights(C(A()))]
def test_filter():assert all(x.priority==InsightPriority.HIGH for x in filter_insights(generate_insights(C()),priority="HIGH"))
def test_status():
 x=generate_insights(C(A()))[0];assert acknowledge_insight(x).status==InsightStatus.ACKNOWLEDGED;assert dismiss_insight(x).status==InsightStatus.DISMISSED
def test_roundtrip():assert deserialize_insights(serialize_insights(generate_insights(C(A()))))
def test_bad_payload():
 with pytest.raises(ValueError):deserialize_insights("{}")
def test_summary():
 s=build_weekly_summary(C(A()));assert s.headline and serialize_summary(s);assert build_monthly_summary(C(A())).period_start
def test_digest():
 with pytest.raises(ValueError):build_progress_digest(C(A()),days=0)
 assert build_progress_digest(C(A()),days=14).period_start
def test_markdown():assert summary_to_markdown(build_weekly_summary(C(A()))).startswith("# Sustainability")
def test_limit():assert len(generate_insights(C(A()),limit=1))==1
def test_nonfinite():assert not normalize_assessments([{"date":N.isoformat(),"footprint":float("nan")}])
def test_no_shared_category():
 x=[{"id":1,"date":(N-timedelta(days=30)).isoformat(),"footprint":1,"food_emissions":5},{"id":2,"date":N.isoformat(),"footprint":1,"transport_emissions":2}]
 assert not generate_category_insights(C(x))
def test_immutable():
 x=A();s=json.dumps(x,sort_keys=True);generate_insights(C(x));assert json.dumps(x,sort_keys=True)==s
def test_settings():
 with pytest.raises(ValueError):build_insight_context([],improvement_threshold_pct=-1)
 with pytest.raises(ValueError):build_insight_context([],stale_days=0)
def test_custom_milestone():assert any(x.type==InsightType.MILESTONE for x in generate_goal_insights(C([],[{"id":1,"progress_pct":10}],milestone_thresholds=(10,))))
def test_clamp():assert any("100.0%" in x.description for x in generate_goal_insights(C([],[{"id":1,"progress_pct":150}])))
def test_summary_counts():
 s=build_monthly_summary(C(A(),[{"id":1,"progress_pct":50}],[{"id":1,"streak":8}],[{"id":1,"status":"completed"}]))
 assert s.goal_count and s.habit_count and s.recommendation_count
def test_status_roundtrip():
 i=acknowledge_insight(generate_insights(C(A()))[0]);assert deserialize_insights(serialize_insights([i]))[0].status==InsightStatus.ACKNOWLEDGED
