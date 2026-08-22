import json
import sqlite3
from action_plan import *
from action_plan import _dependency_order


def action(**kw):
    base = {"id":"a", "name":"Action", "category":"Energy", "difficulty":"easy", "potential_impact_low":100, "potential_impact_high":200}
    base.update(kw); return Action.from_mapping(base)


def test_action_normalizes_ranges_and_ids():
    a = Action.from_mapping({"name":"  Save power ","category":"Energy","potential_impact":250})
    assert a.id and a.potential_impact_low == 250 and a.potential_impact_high == 250


def test_missing_impact_is_unavailable():
    result = estimate_action_impact(action(potential_impact_low=None, potential_impact_high=None))
    assert not result["available"] and result["label"] == "Impact estimate unavailable"


def test_priority_uses_category_relevance():
    a = action(category="Energy", id="energy")
    b = action(category="Food", id="food")
    sa = calculate_action_priority(a, {"Energy":900,"Food":100})
    sb = calculate_action_priority(b, {"Energy":900,"Food":100})
    assert sa.priority > sb.priority


def test_priority_deterministic():
    a = action(id="a", name="A")
    b = action(id="b", name="B")
    x = rank_actions([b,a], {"Energy":100})
    y = rank_actions([a,b], {"Energy":100})
    assert [(a.id,s.priority) for a,s in x] == [(a.id,s.priority) for a,s in y]


def test_cost_and_difficulty_affect_score():
    cheap = action(id="cheap", estimated_cost=0, difficulty="easy")
    costly = action(id="costly", estimated_cost=900, difficulty="advanced")
    assert calculate_action_priority(cheap).priority > calculate_action_priority(costly).priority


def test_conflicts_are_detected():
    a = action(id="a", conflicts=("b",))
    b = action(id="b")
    assert detect_action_conflicts([a,b]) == [("a","b")]


def test_conflicting_actions_not_both_ranked():
    a = action(id="a", conflicts=("b",), potential_impact_low=900, potential_impact_high=900)
    b = action(id="b", potential_impact_low=100, potential_impact_high=100)
    result = rank_actions([a,b], {"Energy":100})
    assert len(result) == 1


def test_dependencies_are_ordered():
    dep = action(id="dep", name="Prerequisite", potential_impact_low=10, potential_impact_high=20)
    main = action(id="main", name="Main", dependencies=("dep",), potential_impact_low=900, potential_impact_high=1000)
    # A direct dependency ordering helper must place prerequisite first.
    ordered = _dependency_order([main, dep])
    assert [x.id for x in ordered] == ["dep", "main"]


def test_plan_top5():
    actions = [action(id=str(i), name=str(i), potential_impact_low=i*10, potential_impact_high=i*20) for i in range(10)]
    plan = build_action_plan(actions, {"Energy":1000}, horizon="top5", user_id=7)
    assert len(plan.items) <= 5 and plan.user_id == 7


def test_plan_impact_sums_ranges():
    plan = ActionPlan("p",1,"top5","now",[
        {"estimated_impact_low":10,"estimated_impact_high":20,"impact_available":True,"status":"planned"},
        {"estimated_impact_low":30,"estimated_impact_high":40,"impact_available":True,"status":"planned"},
    ])
    assert calculate_plan_impact(plan)["low"] == 40
    assert calculate_plan_impact(plan)["high"] == 60


def test_unavailable_plan_impact():
    plan = ActionPlan("p",1,"top5","now",[{"impact_available":False,"status":"planned"}])
    assert not calculate_plan_impact(plan)["available"]


def test_plan_cost_and_time():
    plan = ActionPlan("p",1,"top5","now",[
        {"estimated_cost":10,"time_to_complete":2,"status":"planned"},
        {"estimated_cost":15,"time_to_complete":3,"status":"planned"},
    ])
    assert calculate_plan_cost(plan)==25
    assert estimate_time_to_complete(plan)==5


def test_serialization_roundtrip():
    plan = build_action_plan([action()], {"Energy":100}, user_id=2)
    restored = deserialize_plan(serialize_plan(plan))
    assert restored.to_dict() == plan.to_dict()


def test_persistence_and_completion(tmp_path):
    db = str(tmp_path / "actions.db")
    plan = build_action_plan([action(id="a")], {"Energy":100}, user_id=3)
    assert save_action_plan(plan, db) == 1
    assert mark_action_complete(3, plan.id, "a", db_path=db)
    assert load_plan_progress(3, plan.id, db)["a"] == "completed"


def test_completion_excluded_by_default():
    a = action(completed=True)
    assert rank_actions([a], {"Energy":100}) == []


def test_custom_weights():
    a = action(id="a", estimated_cost=0, potential_impact_low=100, potential_impact_high=100)
    b = action(id="b", estimated_cost=1000, potential_impact_low=900, potential_impact_high=900)
    weights = {"impact":0,"relevance":0,"feasibility":1,"preference":0,"cost":0,"difficulty":0,"time":0}
    assert rank_actions([a,b], {"Energy":100}, weights=weights)[0][0].id == "a"


def test_preferences_boost_category():
    a = action(id="a", category="Energy")
    b = action(id="b", category="Food")
    prefs={"preferred_categories":["Food"]}
    assert calculate_action_priority(b, {"Energy":100,"Food":100}, prefs).preference_score > calculate_action_priority(a,{"Energy":100,"Food":100},prefs).preference_score


def test_safe_nan_values():
    a = Action.from_mapping({"name":"A","category":"Energy","estimated_cost":"nan","potential_impact_low":"nan"})
    assert a.estimated_cost == 0 and a.potential_impact_low == 0


def test_mark_invalid_status():
    try:
        mark_action_complete(1,"p","a","invalid",db_path=":memory:")
    except ValueError:
        pass
    else:
        assert False


def test_conflict_ids_from_plan():
    p=ActionPlan("p",1,"top5","now",[{"action_id":"a","conflicts":["b"]},{"action_id":"b","conflicts":[]}])
    assert detect_action_conflict_ids(p)==[("a","b")]


def test_plan_id_is_stable():
    acts=[action(id="a")]
    assert build_action_plan(acts, {"Energy":100}, user_id=1).id == build_action_plan(acts,{"Energy":100},user_id=1).id


def test_empty_actions():
    p=build_action_plan([], {}, user_id=1)
    assert p.items == []


def test_unknown_difficulty_is_safe():
    a=action(difficulty="strange")
    score=calculate_action_priority(a)
    assert 0 <= score.priority <= 1
