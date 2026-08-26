"""Library for Sustainability History Comparison and Change Attribution."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from emission_factors import recalculate_with_factor_set

class AssessmentRecord:
    def __init__(self, id: int, date: str | datetime, transport: str, distance: float, 
                 electricity: float, diet: str, flights: int, footprint: float, 
                 eco_score: int, factor_version: str = "static-v1"):
        self.id = int(id)
        if isinstance(date, str):
            # Parse ISO format, stripping timezone info if not supported directly in datetime.fromisoformat in older pythons,
            # but in Python 3.11+ fromisoformat handles tz offsets. Let's do a robust parse:
            dt = datetime.fromisoformat(date.replace("Z", "+00:00"))
            self.date = dt
        else:
            self.date = date
            
        self.transport = str(transport)
        self.distance = max(0.0, float(distance))
        self.electricity = max(0.0, float(electricity))
        self.diet = str(diet)
        self.flights = max(0, int(flights))
        self.footprint = float(footprint)
        self.eco_score = int(eco_score)
        self.factor_version = str(factor_version)

    def inputs(self) -> dict:
        return {
            "transport": self.transport,
            "distance": self.distance,
            "electricity": self.electricity,
            "diet": self.diet,
            "flights": self.flights
        }

def normalize_assessment(row: Any) -> AssessmentRecord:
    if isinstance(row, dict):
        return AssessmentRecord(
            id=row["id"],
            date=row["date"],
            transport=row.get("transport", "Car"),
            distance=row.get("distance", 0.0),
            electricity=row.get("electricity", 0.0),
            diet=row.get("diet", "Non-Vegetarian"),
            flights=row.get("flights", 0),
            footprint=row.get("footprint", 0.0),
            eco_score=row.get("eco_score", 0),
            factor_version=row.get("factor_version", "static-v1")
        )
    if isinstance(row, (tuple, list)):
        if len(row) == 11:
            return AssessmentRecord(
                id=row[0],
                date=row[1],
                transport=row[2],
                distance=row[4],
                electricity=row[5],
                diet=row[6],
                flights=row[7],
                footprint=row[8],
                eco_score=row[9],
                factor_version=row[10]
            )
        elif len(row) == 10:
            return AssessmentRecord(
                id=row[0],
                date=row[1],
                transport=row[3],
                distance=row[4],
                electricity=row[5],
                diet=row[6],
                flights=row[7],
                footprint=row[8],
                eco_score=row[9],
                factor_version="static-v1"
            )
    if isinstance(row, AssessmentRecord):
        return row
    raise ValueError(f"Unknown row type: {type(row)}")

def normalize_history(rows: list) -> list[AssessmentRecord]:
    seen_ids = set()
    records = []
    for r in rows:
        norm = normalize_assessment(r)
        if norm.id not in seen_ids:
            seen_ids.add(norm.id)
            records.append(norm)
    records.sort(key=lambda x: x.date)
    return records

def percentage_change(before: float, after: float) -> float | None:
    if before == 0:
        if after == 0:
            return 0.0
        return None
    return round((after - before) / before * 100.0, 4)

class FootprintChange:
    def __init__(self, absolute_change: float, percent_change: float | None):
        self.absolute_change = absolute_change
        self.percent_change = percent_change

class CategoryAttribution:
    def __init__(self, category: str, change_kg: float):
        self.category = category
        self.change_kg = change_kg
    def to_dict(self):
        return {"category": self.category, "change_kg": self.change_kg}

class FactorImpact:
    def __init__(self, from_version: str, to_version: str):
        self.from_version = from_version
        self.to_version = to_version

class Attribution:
    def __init__(self, behaviour_change_kg: float, factor_change_kg: float, 
                 total_change_kg: float, category_attributions: list[CategoryAttribution], 
                 factor_impact: FactorImpact):
        self.behaviour_change_kg = round(behaviour_change_kg, 2)
        self.factor_change_kg = round(factor_change_kg, 2)
        self.total_change_kg = round(total_change_kg, 2)
        self.category_attributions = category_attributions
        self.factor_impact = factor_impact
        self.caveats = [
            "Attribution is a modelled decomposition of stored inputs.",
            "It is not a causal experiment or a guarantee of real-world savings."
        ]

def build_change_attribution(behaviour_change_kg: float, factor_change_kg: float, 
                            total_change_kg: float, category_attributions: list[CategoryAttribution], 
                            factor_impact: FactorImpact) -> Attribution:
    return Attribution(behaviour_change_kg, factor_change_kg, total_change_kg, category_attributions, factor_impact)

class InputChange:
    def __init__(self, parameter: str, before_val: Any, after_val: Any, change: Any):
        self.parameter = parameter
        self.before_val = before_val
        self.after_val = after_val
        self.change = change
    def to_dict(self):
        return {
            "parameter": self.parameter,
            "before": self.before_val,
            "after": self.after_val,
            "change": self.change
        }

class Comparison:
    def __init__(self, before: AssessmentRecord, after: AssessmentRecord, 
                 footprint_change: FootprintChange, methodology_changed: bool, 
                 attribution: Attribution, input_changes: list[InputChange]):
        self.before = before
        self.after = after
        self.footprint_change = footprint_change
        self.methodology_changed = methodology_changed
        self.attribution = attribution
        self.input_changes = input_changes
        self.methodology_warning = (
            f"Methodology changed from {before.factor_version} to {after.factor_version}. "
            "Attribution will correct for this, but direct comparisons may be misleading."
        ) if methodology_changed else None

def compare_assessments(before_raw: Any, after_raw: Any) -> Comparison:
    before = normalize_assessment(before_raw)
    after = normalize_assessment(after_raw)
    
    abs_change = round(after.footprint - before.footprint, 2)
    pct_change = percentage_change(before.footprint, after.footprint)
    
    footprint_change = FootprintChange(abs_change, pct_change)
    methodology_changed = before.factor_version != after.factor_version
    
    inputs_before = before.inputs()
    inputs_after = after.inputs()
    
    recalc_before_under_before = recalculate_with_factor_set(inputs_before, before.factor_version)["total_kg"]
    recalc_before_under_after = recalculate_with_factor_set(inputs_before, after.factor_version)["total_kg"]
    
    factor_change_kg = round(recalc_before_under_after - recalc_before_under_before, 2)
    behaviour_change_kg = round(abs_change - factor_change_kg, 2)
    
    contribs_before = recalculate_with_factor_set(inputs_before, before.factor_version)["contributors"]
    contribs_after = recalculate_with_factor_set(inputs_after, after.factor_version)["contributors"]
    
    category_attributions = []
    for cat in ["Transport", "Electricity", "Diet", "Flights"]:
        change_kg = round(contribs_after[cat] - contribs_before[cat], 2)
        category_attributions.append(CategoryAttribution(cat, change_kg))
        
    factor_impact = FactorImpact(before.factor_version, after.factor_version)
    attribution = Attribution(behaviour_change_kg, factor_change_kg, abs_change, category_attributions, factor_impact)
    
    input_changes = []
    if before.distance != after.distance:
        input_changes.append(InputChange("distance", before.distance, after.distance, round(after.distance - before.distance, 2)))
    if before.electricity != after.electricity:
        input_changes.append(InputChange("electricity", before.electricity, after.electricity, round(after.electricity - before.electricity, 2)))
    if before.flights != after.flights:
        input_changes.append(InputChange("flights", before.flights, after.flights, after.flights - before.flights))
    if before.transport != after.transport:
        input_changes.append(InputChange("transport", before.transport, after.transport, f"{before.transport} -> {after.transport}"))
    if before.diet != after.diet:
        input_changes.append(InputChange("diet", before.diet, after.diet, f"{before.diet} -> {after.diet}"))
        
    return Comparison(before, after, footprint_change, methodology_changed, attribution, input_changes)

def compare_history_endpoints(history: list) -> Comparison:
    sorted_history = normalize_history(history)
    if len(sorted_history) < 2:
        raise ValueError("At least two assessments are required to compare history endpoints.")
    return compare_assessments(sorted_history[0], sorted_history[-1])

def compare_selected_ids(history: list, before_id: Any, after_id: Any) -> Comparison:
    sorted_history = normalize_history(history)
    before_rec = next((x for x in sorted_history if x.id == int(before_id)), None)
    after_rec = next((x for x in sorted_history if x.id == int(after_id)), None)
    if not before_rec or not after_rec:
        raise KeyError(f"Selected assessment IDs ({before_id}, {after_id}) not found in history.")
    return compare_assessments(before_rec, after_rec)

class TimelinePoint:
    def __init__(self, label: str, assessments: int, average_footprint: float, average_eco_score: float):
        self.label = label
        self.assessments = assessments
        self.average_footprint = average_footprint
        self.average_eco_score = average_eco_score
    def to_dict(self):
        return {
            "label": self.label,
            "assessments": self.assessments,
            "average_footprint": self.average_footprint,
            "average_eco_score": self.average_eco_score
        }

def build_history_timeline(history: list, period: str) -> list[TimelinePoint]:
    if period not in ["monthly", "quarterly", "yearly"]:
        raise ValueError(f"Invalid period: {period}")
    sorted_history = normalize_history(history)
    if not sorted_history:
        return []
    groups = {}
    for r in sorted_history:
        if period == "monthly":
            key = r.date.strftime("%Y-%m")
        elif period == "quarterly":
            q = (r.date.month - 1) // 3 + 1
            key = f"{r.date.year}-Q{q}"
        else:
            key = str(r.date.year)
        groups.setdefault(key, []).append(r)
        
    timeline = []
    for key in sorted(groups.keys()):
        recs = groups[key]
        avg_footprint = round(sum(x.footprint for x in recs) / len(recs), 2)
        avg_eco_score = round(sum(x.eco_score for x in recs) / len(recs), 2)
        timeline.append(TimelinePoint(key, len(recs), avg_footprint, avg_eco_score))
    return timeline

class HistorySummary:
    def __init__(self, count: int, footprint_change_kg: float | None, 
                 score_change: int | None, comparable: bool, warnings: list[str]):
        self.count = count
        self.footprint_change_kg = footprint_change_kg
        self.score_change = score_change
        self.comparable = comparable
        self.warnings = warnings

def summarize_history(history: list) -> HistorySummary:
    sorted_history = normalize_history(history)
    count = len(sorted_history)
    if count < 2:
        return HistorySummary(count, None, None, True, [])
    first = sorted_history[0]
    last = sorted_history[-1]
    footprint_change = round(last.footprint - first.footprint, 2)
    score_change = last.eco_score - first.eco_score
    versions = {x.factor_version for x in sorted_history}
    comparable = len(versions) <= 1
    warnings = []
    if not comparable:
        warnings.append(
            "Methodology changes detected in your history. Attributed figures "
            "correct for this, but raw comparisons on the trendline may be misleading."
        )
    return HistorySummary(count, footprint_change, score_change, comparable, warnings)

def trend_direction(history: list) -> str:
    sorted_history = normalize_history(history)
    if len(sorted_history) < 2:
        return "insufficient_data"
    first = sorted_history[0]
    last = sorted_history[-1]
    if last.footprint < first.footprint:
        return "decreasing"
    elif last.footprint > first.footprint:
        return "increasing"
    return "stable"

def rolling_average(history: list, window: int) -> list[dict]:
    sorted_history = normalize_history(history)
    results = []
    for i in range(len(sorted_history)):
        sub = sorted_history[max(0, i - window + 1):i + 1]
        avg = sum(x.footprint for x in sub) / len(sub)
        results.append({
            "record": sorted_history[i],
            "rolling_average": round(avg, 2)
        })
    return results

def find_biggest_changes(history: list, limit: int = 5) -> list[Comparison]:
    sorted_history = normalize_history(history)
    comparisons = []
    for i in range(1, len(sorted_history)):
        comparisons.append(compare_assessments(sorted_history[i-1], sorted_history[i]))
    comparisons.sort(key=lambda x: abs(x.footprint_change.absolute_change), reverse=True)
    return comparisons[:limit]

def history_quality_flags(history: list) -> list[str]:
    sorted_history = normalize_history(history)
    flags = []
    if len(sorted_history) <= 1:
        flags.append("single_assessment")
    versions = {x.factor_version for x in sorted_history}
    if len(versions) > 1:
        flags.append("mixed_factor_versions")
    return flags

def validate_comparison(comparison: Comparison) -> list[str]:
    return []

def export_comparison_json(comparison: Comparison) -> str:
    return json.dumps({
        "schema_version": "1.0",
        "comparison": {
            "before_id": comparison.before.id,
            "after_id": comparison.after.id,
            "absolute_change_kg": comparison.footprint_change.absolute_change,
            "percent_change": comparison.footprint_change.percent_change,
            "behaviour_change_kg": comparison.attribution.behaviour_change_kg,
            "factor_change_kg": comparison.attribution.factor_change_kg
        }
    })

def export_comparison_csv(comparison: Comparison) -> str:
    import io
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Metric", "Before", "After", "Change"])
    writer.writerow(["Annual footprint", comparison.before.footprint, comparison.after.footprint, comparison.footprint_change.absolute_change])
    writer.writerow(["Factor/methodology effect", "", "", comparison.attribution.factor_change_kg])
    writer.writerow(["Behaviour/input effect", "", "", comparison.attribution.behaviour_change_kg])
    return output.getvalue()

def export_markdown_report(comparison: Comparison) -> str:
    return f"""# Sustainability History Comparison

## Overview
Comparing assessment #{comparison.before.id} to #{comparison.after.id}.

## Change attribution
- Behaviour change: {comparison.attribution.behaviour_change_kg:+.1f} kg
- Factor change: {comparison.attribution.factor_change_kg:+.1f} kg
- Total footprint change: {comparison.footprint_change.absolute_change:+.1f} kg ({comparison.footprint_change.percent_change:+.1f}%)
"""

def export_history_json(history: list, period: str = "monthly") -> str:
    sorted_history = normalize_history(history)
    return json.dumps({
        "schema_version": "1.0",
        "assessments": [
            {
                "id": x.id,
                "date": x.date.isoformat(),
                "footprint": x.footprint,
                "eco_score": x.eco_score
            }
            for x in sorted_history
        ]
    })

def top_category_changes(comparison: Comparison, limit: int = 10) -> list[CategoryAttribution]:
    attrs = list(comparison.attribution.category_attributions)
    attrs.sort(key=lambda x: abs(x.change_kg), reverse=True)
    return attrs[:limit]
