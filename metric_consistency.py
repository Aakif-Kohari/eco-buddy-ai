"""
EcoBuddy Sustainability Metric Consistency and Cross-Module Validation Engine.

Additive, read-only validation for assessments, goals, recommendations, habits,
action plans, and analytics.  It normalizes category names and units, validates
dates and numeric values, compares shared metrics, detects contradictions, and
produces deterministic JSON/SQLite snapshots without modifying source data.

Issue #1169.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
import sqlite3
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

ENGINE_VERSION = "1.0"
DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")
MODULES = ("assessments","goals","recommendations","habits","action_plans","analytics")
KNOWN_CATEGORIES = ("Transportation","Electricity","Diet","Flights","Water","Waste","Shopping","General lifestyle")

SEVERITY_CRITICAL="CRITICAL"; SEVERITY_ERROR="ERROR"; SEVERITY_WARNING="WARNING"; SEVERITY_INFO="INFO"
SEVERITY_ORDER={SEVERITY_CRITICAL:0,SEVERITY_ERROR:1,SEVERITY_WARNING:2,SEVERITY_INFO:3}
STATUS_CONSISTENT="CONSISTENT"; STATUS_REVIEW="REVIEW"; STATUS_INCONSISTENT="INCONSISTENT"; STATUS_INSUFFICIENT_DATA="INSUFFICIENT_DATA"

CATEGORY_ALIASES={
 "transport":"Transportation","transportation":"Transportation","transportation emissions":"Transportation",
 "travel":"Transportation","commute":"Transportation","car":"Transportation",
 "electricity":"Electricity","energy":"Electricity","power":"Electricity","home energy":"Electricity",
 "diet":"Diet","food":"Diet","meals":"Diet","food consumption":"Diet",
 "flight":"Flights","flights":"Flights","air travel":"Flights","aviation":"Flights",
 "water":"Water","water use":"Water","waste":"Waste","waste management":"Waste","trash":"Waste",
 "shopping":"Shopping","purchases":"Shopping","consumer goods":"Shopping",
 "lifestyle":"General lifestyle","general":"General lifestyle","general lifestyle":"General lifestyle",
}
UNIT_DIMENSIONS={
 "kg":"mass","g":"mass","tonne":"mass","tonnes":"mass","t":"mass",
 "kg co2":"emissions","kg co2e":"emissions","kgco2e":"emissions","g co2e":"emissions",
 "km":"distance","m":"distance","mi":"distance","mile":"distance","miles":"distance",
 "kwh":"energy","wh":"energy","mwh":"energy",
 "l":"volume","liter":"volume","liters":"volume","litre":"volume","litres":"volume","gal":"volume","gallon":"volume","gallons":"volume",
 "day":"time","days":"time","week":"time","weeks":"time","month":"time","months":"time","year":"time","years":"time",
 "count":"count","counts":"count","item":"count","items":"count","%":"ratio","percent":"ratio","percentage":"ratio",
}
CANONICAL_UNITS={"mass":"kg","emissions":"kg CO2e","distance":"km","energy":"kWh","volume":"L","time":"year","count":"count","ratio":"%"}
CONVERSIONS={
 ("g","kg"):0.001,("kg","g"):1000,("tonne","kg"):1000,("tonnes","kg"):1000,("t","kg"):1000,
 ("kg","tonne"):0.001,("kg","t"):0.001,("m","km"):0.001,("km","m"):1000,
 ("mi","km"):1.609344,("mile","km"):1.609344,("miles","km"):1.609344,("km","mi"):0.6213711922,
 ("wh","kwh"):0.001,("kwh","wh"):1000,("mwh","kwh"):1000,("kwh","mwh"):0.001,
 ("liter","l"):1,("liters","l"):1,("litre","l"):1,("litres","l"):1,
 ("gal","l"):3.785411784,("gallon","l"):3.785411784,("gallons","l"):3.785411784,
 ("day","year"):1/365.25,("days","year"):1/365.25,("week","year"):7/365.25,("weeks","year"):7/365.25,
 ("month","year"):1/12,("months","year"):1/12,("year","day"):365.25,("year","week"):52.1775,("year","month"):12,
}
ALIASES={
 "metric":("metric","metric_name","name","title","key","indicator"),
 "category":("category","category_name","area","domain","sector"),
 "unit":("unit","units","metric_unit","unit_name"),
 "value":("value","amount","metric_value","current","current_value"),
 "id":("id","metric_id","assessment_id","goal_id","action_id"),
 "user_id":("user_id","owner_id","profile_id"),
 "date":("date","created_at","updated_at","timestamp"),
}
DEFAULT_TOLERANCE=0.05

class MetricConsistencyError(ValueError): pass

@dataclass(frozen=True)
class MetricValue:
 module:str; record_id:str; metric:str; category:str; value:float|None; unit:str
 canonical_value:float|None; canonical_unit:str; dimension:str|None; date:date|None
 user_id:str|None; source:str|None=None; confidence:str="known"
 def to_dict(self):
  d=asdict(self); d["date"]=self.date.isoformat() if self.date else None; return d

@dataclass(frozen=True)
class ValidationFinding:
 code:str; severity:str; module:str; message:str
 record_ids:tuple[str,...]=(); categories:tuple[str,...]=(); metrics:tuple[str,...]=()
 expected:Any=None; observed:Any=None; suggested_action:str=""; rule:str=""
 def to_dict(self): return asdict(self)

@dataclass
class ModuleValidation:
 module:str; record_count:int=0; valid_metric_count:int=0; invalid_metric_count:int=0
 findings:list[ValidationFinding]=field(default_factory=list)
 @property
 def status(self):
  if any(x.severity in (SEVERITY_CRITICAL,SEVERITY_ERROR) for x in self.findings): return STATUS_INCONSISTENT
  if self.findings: return STATUS_REVIEW
  if not self.record_count: return STATUS_INSUFFICIENT_DATA
  return STATUS_CONSISTENT
 def to_dict(self):
  return {"module":self.module,"record_count":self.record_count,"valid_metric_count":self.valid_metric_count,
          "invalid_metric_count":self.invalid_metric_count,"status":self.status,
          "findings":[x.to_dict() for x in self.findings]}

@dataclass
class ConsistencyReport:
 generated_at:str; engine_version:str; user_id:str|None; status:str; score:float
 module_results:dict[str,ModuleValidation]; findings:list[ValidationFinding]
 metric_matrix:list[dict[str,Any]]; category_summary:list[dict[str,Any]]; summary:dict[str,Any]
 def to_dict(self):
  return {"generated_at":self.generated_at,"engine_version":self.engine_version,"user_id":self.user_id,
          "status":self.status,"score":self.score,
          "module_results":{k:v.to_dict() for k,v in self.module_results.items()},
          "findings":[x.to_dict() for x in self.findings],"metric_matrix":self.metric_matrix,
          "category_summary":self.category_summary,"summary":self.summary}
 def to_json(self,indent=2): return json.dumps(self.to_dict(),indent=indent,sort_keys=True,default=str)

def _text(v): return " ".join(str(v or "").strip().lower().split())
def _finite(v):
 try:
  x=float(v)
  return x if math.isfinite(x) else None
 except (TypeError,ValueError): return None
def _date(v):
 if v is None:return None
 if isinstance(v,datetime):return v.date()
 if isinstance(v,date):return v
 s=str(v).strip().replace("Z","+00:00")
 for parser in (lambda:datetime.fromisoformat(s).date(),lambda:datetime.strptime(s[:10],"%Y-%m-%d").date(),
                lambda:datetime.strptime(s[:10],"%Y/%m/%d").date(),lambda:datetime.strptime(s[:10],"%d-%m-%Y").date()):
  try:return parser()
  except ValueError:pass
 return None
def _pick(m,names):
 for n in names:
  if n in m and m[n] is not None:return m[n]
 return None
def normalize_category(v):
 k=_text(v)
 return CATEGORY_ALIASES.get(k,str(v).strip() if v is not None else "Unknown") if k else "Unknown"
def category_key(v):return _text(normalize_category(v))
def normalize_unit(v):
 k=_text(v).replace("co₂","co2")
 return {"kgco2e":"kg co2e","kg co2":"kg co2e","kilograms co2e":"kg co2e","kilometres":"km",
         "kilometers":"km","kilometre":"km","kilometer":"km","kilowatt hour":"kwh","kilowatt hours":"kwh"}.get(k,k)
def unit_dimension(v):return UNIT_DIMENSIONS.get(normalize_unit(v))
def canonical_unit(v):return CANONICAL_UNITS.get(unit_dimension(v))
def convert_value(value,source,target):
 x=_finite(value); s=normalize_unit(source); t=normalize_unit(target)
 if x is None:return None
 if s==t:return x
 if unit_dimension(s)!=unit_dimension(t):raise MetricConsistencyError(f"Incompatible units: {source!r} and {target!r}")
 factor=CONVERSIONS.get((s,t))
 if factor is None:
  if canonical_unit(s)==canonical_unit(t):return x
  raise MetricConsistencyError(f"No conversion registered from {source!r} to {target!r}")
 return x*factor
def canonicalize_value(value,unit):
 u=normalize_unit(unit); dim=unit_dimension(u); cu=canonical_unit(u)
 if not dim:return _finite(value),u,None
 try:return convert_value(value,u,cu),cu,dim
 except MetricConsistencyError:return None,cu,dim

def _metric_name(r):return str(_pick(r,ALIASES["metric"]) or "value").strip()
def _record_id(r,i):return str(_pick(r,ALIASES["id"]) if _pick(r,ALIASES["id"]) is not None else f"row-{i}")
def _user_id(r):
 v=_pick(r,ALIASES["user_id"]);return str(v) if v is not None else None
def normalize_metric_record(module,record,index=0):
 rid=_record_id(record,index); metric=_metric_name(record)
 cat=normalize_category(_pick(record,ALIASES["category"]) or "Unknown")
 raw=_pick(record,ALIASES["value"]); unit=normalize_unit(_pick(record,ALIASES["unit"]) or "count")
 cv,cu,dim=canonicalize_value(raw,unit)
 return MetricValue(module,rid,metric,cat,_finite(raw),unit,cv,cu,dim,_date(_pick(record,ALIASES["date"])),_user_id(record),
                    str(record.get("source")) if record.get("source") is not None else None,
                    str(record.get("confidence") or "known"))

def finding(code,severity,module,message,record_ids=(),categories=(),metrics=(),expected=None,observed=None,suggested_action="",rule=""):
 return ValidationFinding(code,severity,module,message,tuple(str(x) for x in record_ids),
                          tuple(str(x) for x in categories),tuple(str(x) for x in metrics),
                          expected,observed,suggested_action,rule)

def normalize_module_records(module,records):
 metrics=[]; findings=[]
 for i,r in enumerate(records or []):
  if not isinstance(r,Mapping):
   findings.append(finding("NON_MAPPING_RECORD",SEVERITY_ERROR,module,f"Record {i} is not a mapping.",[f"row-{i}"],
                           suggested_action="Normalize module output before validation.",rule="Records must be mappings."))
   continue
  m=normalize_metric_record(module,r,i);metrics.append(m)
  findings.extend(validate_metric_value(m))
 return metrics,deduplicate_findings(findings)

def normalize_assessments(records):
 out=[]
 for i,r in enumerate(records or []):
  if isinstance(r,Mapping):
   base=str(r.get("id",i));dt=_date(r.get("date",r.get("created_at")));uid=r.get("user_id")
   fields=[("Transportation",r.get("transport"),r.get("transport_unit","count")),
           ("Transportation",r.get("distance"),r.get("distance_unit","km")),
           ("Electricity",r.get("electricity"),r.get("electricity_unit","kWh")),
           ("Diet",r.get("diet"),r.get("diet_unit","count")),
           ("Flights",r.get("flights"),r.get("flights_unit","count")),
           ("General lifestyle",r.get("footprint"),r.get("footprint_unit","kg CO2e"))]
  elif isinstance(r,(tuple,list)) and len(r)>=9:
   base=str(r[0]);dt=_date(r[1]);uid=None
   fields=[("Transportation",r[2],"count"),("Transportation",r[3],"km"),("Electricity",r[4],"kWh"),
           ("Diet",r[5],"count"),("Flights",r[6],"count"),("General lifestyle",r[7],"kg CO2e")]
  else:continue
  for p,(cat,val,unit) in enumerate(fields):
   cv,cu,dim=canonicalize_value(val,unit)
   out.append(MetricValue("assessments",f"{base}:{p}",f"{_text(cat)}_{p}",cat,_finite(val),normalize_unit(unit),
                           cv,cu,dim,dt,str(uid) if uid is not None else None,"assessment"))
 return out

def normalize_goals(records):
 out=[]
 for i,r in enumerate(records or []):
  if not isinstance(r,Mapping):continue
  rid=_record_id(r,i);cat=normalize_category(_pick(r,("category","category_name","area")) or "General lifestyle")
  dt=_date(_pick(r,("target_date","end_date","date")));uid=_user_id(r);unit=r.get("unit","kg CO2e")
  for name,val in (("baseline",_pick(r,("baseline_kg","baseline"))),("current",_pick(r,("current_kg","current","current_value"))),
                   ("target",_pick(r,("target_kg","target","target_value")))):
   if val is None:continue
   cv,cu,dim=canonicalize_value(val,unit)
   out.append(MetricValue("goals",f"{rid}:{name}",name,cat,_finite(val),normalize_unit(unit),cv,cu,dim,dt,uid,"goal"))
 return out

def normalize_recommendations(records):
 out=[]
 for i,r in enumerate(records or []):
  if not isinstance(r,Mapping):continue
  rid=_record_id(r,i);cat=normalize_category(_pick(r,("category","area","domain")) or "Unknown")
  name=str(_pick(r,("name","title","recommendation","text")) or "recommendation")
  val=_pick(r,("estimated_impact","impact","potential_impact","value"));unit=r.get("impact_unit",r.get("unit","kg CO2e"))
  cv,cu,dim=canonicalize_value(val,unit)
  out.append(MetricValue("recommendations",rid,name,cat,_finite(val),normalize_unit(unit),cv,cu,dim,_date(_pick(r,ALIASES["date"])),
                         _user_id(r),str(r.get("source") or "recommendation"),str(r.get("confidence") or "estimated")))
 return out

def normalize_habits(records):
 out=[]
 for i,r in enumerate(records or []):
  if not isinstance(r,Mapping):continue
  rid=_record_id(r,i);cat=normalize_category(_pick(r,("category","area","domain")) or "Unknown")
  name=str(_pick(r,("name","title","habit","habit_name")) or "habit")
  val=_pick(r,("value","target","target_value","impact","estimated_impact"));unit=r.get("unit",r.get("target_unit","count"))
  cv,cu,dim=canonicalize_value(val,unit)
  out.append(MetricValue("habits",rid,name,cat,_finite(val),normalize_unit(unit),cv,cu,dim,_date(_pick(r,ALIASES["date"])),
                         _user_id(r),str(r.get("source") or "habit"),"known" if val is not None else "unknown"))
 return out

def normalize_action_plans(records):
 out=[]
 for i,r in enumerate(records or []):
  if not isinstance(r,Mapping):continue
  rid=_record_id(r,i);cat=normalize_category(_pick(r,("category","area","domain")) or "Unknown")
  name=str(_pick(r,("name","title","action","action_name")) or "action")
  val=_pick(r,("estimated_impact","potential_impact","impact","value"))
  lo=_finite(r.get("estimated_impact_low",r.get("impact_low")));hi=_finite(r.get("estimated_impact_high",r.get("impact_high")))
  if val is None and lo is not None and hi is not None:val=(lo+hi)/2
  unit=r.get("impact_unit",r.get("unit","kg CO2e"));cv,cu,dim=canonicalize_value(val,unit)
  out.append(MetricValue("action_plans",rid,name,cat,_finite(val),normalize_unit(unit),cv,cu,dim,_date(_pick(r,ALIASES["date"])),
                         _user_id(r),str(r.get("source") or "action_plan"),"estimated"))
 return out

def normalize_analytics(records):
 out=[]
 for i,r in enumerate(records or []):
  if not isinstance(r,Mapping):continue
  rid=_record_id(r,i);cat=normalize_category(_pick(r,("category","area","domain")) or "General lifestyle")
  name=_metric_name(r);val=_pick(r,ALIASES["value"]);unit=r.get("unit",r.get("metric_unit","kg CO2e"))
  cv,cu,dim=canonicalize_value(val,unit)
  out.append(MetricValue("analytics",rid,name,cat,_finite(val),normalize_unit(unit),cv,cu,dim,_date(_pick(r,ALIASES["date"])),
                         _user_id(r),str(r.get("source") or "analytics"),"derived"))
 return out

NORMALIZERS={"assessments":normalize_assessments,"goals":normalize_goals,"recommendations":normalize_recommendations,
             "habits":normalize_habits,"action_plans":normalize_action_plans,"analytics":normalize_analytics}
def normalize_all_modules(data):
 return {m:NORMALIZERS[m](data.get(m,[]) if isinstance(data,Mapping) else []) for m in MODULES}

def validate_metric_value(m):
 f=[]
 if m.value is None:
  f.append(finding("MISSING_METRIC_VALUE",SEVERITY_ERROR,m.module,f"{m.module} record {m.record_id} has no finite value for '{m.metric}'.",
                   [m.record_id],metrics=[m.metric],suggested_action="Provide a finite numeric value or explicitly mark it unavailable.",
                   rule="Metric values must be finite numbers."))
 if m.value is not None and m.value<0 and m.dimension in {"mass","emissions","distance","energy","volume","time","count"}:
  f.append(finding("NEGATIVE_METRIC",SEVERITY_WARNING,m.module,f"{m.metric} is negative ({m.value:g} {m.unit}).",
                   [m.record_id],metrics=[m.metric],observed=m.value,suggested_action="Verify the signed metric definition.",
                   rule="Physical quantities are non-negative unless explicitly defined as deltas."))
 if m.dimension is None:
  f.append(finding("UNKNOWN_METRIC_DIMENSION",SEVERITY_WARNING,m.module,f"Metric '{m.metric}' uses unknown unit '{m.unit}'.",
                   [m.record_id],metrics=[m.metric],observed=m.unit,suggested_action="Register the unit and physical dimension.",
                   rule="Cross-module comparisons require compatible dimensions."))
 if m.date is None and m.module in {"assessments","analytics"}:
  f.append(finding("MISSING_METRIC_DATE",SEVERITY_WARNING,m.module,f"{m.module} metric {m.record_id} has no usable date.",
                   [m.record_id],metrics=[m.metric],suggested_action="Store an observation date.",rule="Historical metrics require dates."))
 return f

def deduplicate_findings(findings):
 seen=set();out=[]
 for x in findings:
  k=(x.code,x.severity,x.module,x.message,x.record_ids,x.categories,x.metrics)
  if k not in seen:seen.add(k);out.append(x)
 return out

def validate_module_metrics(module,metrics,raw_findings=()):
 f=list(raw_findings)
 for m in metrics:f.extend(validate_metric_value(m))
 return ModuleValidation(module,len(metrics),sum(m.value is not None and m.dimension is not None for m in metrics),
                         sum(m.value is None or m.dimension is None for m in metrics),deduplicate_findings(f))

def compare_category_taxonomy(modules):
 variants=defaultdict(Counter)
 for ms in modules.values():
  for m in ms:variants[category_key(m.category)][m.category]+=1
 out=[]
 for key,c in variants.items():
  if len(c)>1:
   out.append(finding("CATEGORY_ALIAS_VARIATION",SEVERITY_INFO,"cross_module",
     f"Category '{normalize_category(key)}' appears under multiple spellings: {', '.join(sorted(c))}.",
     categories=[normalize_category(key),*sorted(c)],observed=dict(c),expected=normalize_category(key),
     suggested_action="Use the shared category normalizer.",rule="Equivalent categories should use one canonical taxonomy."))
 return out

def values_close(a,b,tol=DEFAULT_TOLERANCE):
 if a is None or b is None:return False
 return abs(a-b)/max(abs(a),abs(b),1.0)<=tol

def compare_units(metrics,tolerance=DEFAULT_TOLERANCE):
 groups=defaultdict(list)
 for m in metrics:groups[(category_key(m.category),_text(m.metric))].append(m)
 out=[]
 for identity,g in groups.items():
  dims={m.dimension for m in g if m.dimension}
  if len(dims)>1:
   out.append(finding("UNIT_DIMENSION_CONFLICT",SEVERITY_ERROR,"cross_module",
     f"Metric '{identity[1]}' in {identity[0]} uses incompatible physical dimensions.",
     [m.record_id for m in g],metrics=[m.metric for m in g],observed=[m.unit for m in g],
     suggested_action="Verify metric definitions before comparison.",rule="A metric identity must have one dimension."))
   continue
  units={m.unit for m in g}
  if len(units)>1:
   out.append(finding("UNIT_VARIATION",SEVERITY_WARNING,"cross_module",
     f"Metric '{identity[1]}' uses multiple units: {', '.join(sorted(units))}.",
     [m.record_id for m in g],metrics=[m.metric for m in g],observed=sorted(units),
     expected=sorted({m.canonical_unit for m in g}),suggested_action="Normalize to canonical units.",
     rule="Equivalent units require deterministic conversion."))
  for i,left in enumerate(g):
   for right in g[i+1:]:
    if left.module==right.module or left.canonical_value is None or right.canonical_value is None:continue
    if left.canonical_unit!=right.canonical_unit:continue
    if not values_close(left.canonical_value,right.canonical_value,tolerance):
     out.append(finding("CROSS_MODULE_VALUE_MISMATCH",SEVERITY_WARNING,"cross_module",
       f"Metric '{left.metric}' differs across {left.module} and {right.module}: {left.canonical_value:g} vs {right.canonical_value:g} {left.canonical_unit}.",
       [left.record_id,right.record_id],categories=[left.category,right.category],metrics=[left.metric,right.metric],
       expected=left.canonical_value,observed=right.canonical_value,
       suggested_action="Verify observation period and metric definition.",
       rule=f"Shared snapshot values should agree within {tolerance:.1%}."))
 return out

def compare_dates(modules,max_skew_days=366):
 allm=[m for ms in modules.values() for m in ms if m.date]
 out=[];today=date.today()
 for m in allm:
  if m.date>today:
   out.append(finding("FUTURE_METRIC_DATE",SEVERITY_ERROR,m.module,f"Record {m.record_id} is dated in the future.",
                       [m.record_id],metrics=[m.metric],observed=m.date.isoformat(),suggested_action="Verify observation date.",
                       rule="Historical metrics cannot be future dated."))
 for mod,ms in modules.items():
  dated=[m for m in ms if m.date]
  for a,b in zip(dated,dated[1:]):
   if b.date<a.date:
    out.append(finding("OUT_OF_ORDER_DATE",SEVERITY_WARNING,mod,f"{mod} records are not chronological.",
                       [a.record_id,b.record_id],suggested_action="Sort historical records by date.",rule="Time-series data should be ordered."))
 groups=defaultdict(list)
 for m in allm:groups[(category_key(m.category),_text(m.metric))].append(m)
 for ident,g in groups.items():
  dates=[m.date for m in g]
  if len(dates)>1 and (max(dates)-min(dates)).days>max_skew_days:
   out.append(finding("TEMPORAL_WINDOW_MISMATCH",SEVERITY_WARNING,"cross_module",
     f"Metric '{ident[1]}' spans {(max(dates)-min(dates)).days} days across modules.",
     [m.record_id for m in g],metrics=[m.metric for m in g],observed={"earliest":min(dates).isoformat(),"latest":max(dates).isoformat()},
     suggested_action="Compare aligned observation periods.",rule=f"Snapshot comparisons should normally be within {max_skew_days} days."))
 return out

def compare_user_scopes(modules):
 scopes={m:{x.user_id for x in ms if x.user_id is not None} for m,ms in modules.items()}
 all_ids={u for s in scopes.values() for u in s}
 if len(all_ids)<=1:return []
 out=[]
 for mod,ids in scopes.items():
  if ids and ids!=all_ids:
   out.append(finding("USER_SCOPE_MISMATCH",SEVERITY_CRITICAL,mod,
     f"{mod} contains user IDs {sorted(ids)} while the validation set contains {sorted(all_ids)}.",
     expected=sorted(all_ids),observed=sorted(ids),suggested_action="Filter every module to one user.",
     rule="Cross-module validation requires one user scope."))
 return out

def detect_duplicate_metric_identities(modules):
 groups=defaultdict(list)
 for ms in modules.values():
  for m in ms:groups[(m.module,m.record_id,category_key(m.category),_text(m.metric))].append(m)
 return [finding("DUPLICATE_METRIC_IDENTITY",SEVERITY_WARNING,k[0],
                 f"Metric identity {k[1]}:{k[2]}:{k[3]} occurs {len(g)} times.",
                 [m.record_id for m in g],categories=[m.category for m in g],metrics=[m.metric for m in g],
                 suggested_action="Ensure one stable metric identity per observation.",
                 rule="A module should not expose duplicate metric identities.")
         for k,g in groups.items() if len(g)>1]

def detect_orphan_references(modules):
 known={m.record_id for ms in modules.values() for m in ms};out=[]
 for mod,ms in modules.items():
  for m in ms:
   if m.metric.startswith("ref:") and m.metric[4:].strip() not in known:
    ref=m.metric[4:].strip()
    out.append(finding("ORPHAN_REFERENCE",SEVERITY_WARNING,mod,f"Record {m.record_id} references missing record '{ref}'.",
                        [m.record_id,ref],suggested_action="Remove or restore the stale reference.",
                        rule="Cross-module references should resolve."))
 return out

def detect_goal_metric_consistency(goals,assessments,tolerance=DEFAULT_TOLERANCE):
 grouped=defaultdict(dict)
 for m in goals:grouped[m.record_id.rsplit(":",1)[0]][m.metric]=m
 assessment=defaultdict(list)
 for m in assessments:
  if m.dimension=="emissions":assessment[category_key(m.category)].append(m)
 out=[]
 for gid,vals in grouped.items():
  cur=vals.get("current")
  if not cur or cur.canonical_value is None:continue
  candidates=[m for m in assessment.get(category_key(cur.category),[]) if m.canonical_value is not None]
  if not candidates:
   out.append(finding("GOAL_WITHOUT_ASSESSMENT_SUPPORT",SEVERITY_WARNING,"goals",
     f"Goal {gid} has a current value but no matching assessment metric.",[gid],[cur.category],
     suggested_action="Verify goal category or provide supporting assessment.",
     rule="Footprint-based goal current values should be traceable."))
   continue
  latest=max(candidates,key=lambda m:m.date or date.min)
  if not values_close(cur.canonical_value,latest.canonical_value,tolerance):
   out.append(finding("GOAL_CURRENT_ASSESSMENT_MISMATCH",SEVERITY_ERROR,"goals",
     f"Goal {gid} current value {cur.canonical_value:g} differs from latest assessment {latest.canonical_value:g}.",
     [gid,latest.record_id],[cur.category],expected=latest.canonical_value,observed=cur.canonical_value,
     suggested_action="Refresh the goal from the intended assessment snapshot.",
     rule=f"Goal and assessment values should agree within {tolerance:.1%}."))
 return out

def detect_recommendation_alignment(recommendations,assessments):
 cats={category_key(m.category) for m in assessments};out=[]
 for m in recommendations:
  if m.category=="Unknown":
   out.append(finding("RECOMMENDATION_MISSING_CATEGORY",SEVERITY_WARNING,"recommendations",
     f"Recommendation {m.record_id} has no sustainability category.",[m.record_id],
     suggested_action="Assign a canonical category.",rule="Recommendations share assessment taxonomy."))
  elif cats and category_key(m.category) not in cats:
   out.append(finding("RECOMMENDATION_UNSUPPORTED_CATEGORY",SEVERITY_INFO,"recommendations",
     f"Recommendation {m.record_id} targets '{m.category}', absent from the assessment.",
     [m.record_id],[m.category],suggested_action="Verify recommendation scope.",
     rule="Recommendations should be traceable to assessed categories."))
 return out

def detect_action_plan_alignment(actions,recommendations):
 cats={category_key(m.category) for m in recommendations};out=[]
 for m in actions:
  if m.category=="Unknown":
   out.append(finding("ACTION_MISSING_CATEGORY",SEVERITY_WARNING,"action_plans",
     f"Action {m.record_id} has no sustainability category.",[m.record_id],
     suggested_action="Assign a canonical category.",rule="Actions share recommendation taxonomy."))
  elif cats and category_key(m.category) not in cats:
   out.append(finding("ACTION_UNSUPPORTED_CATEGORY",SEVERITY_INFO,"action_plans",
     f"Action {m.record_id} targets '{m.category}' with no recommendation in that category.",
     [m.record_id],[m.category],suggested_action="Verify action scope.",
     rule="Action categories should normally be traceable to recommendations."))
 return out

def detect_habit_alignment(habits,assessments):
 cats={category_key(m.category) for m in assessments};out=[]
 if not cats:return out
 for m in habits:
  if category_key(m.category) not in cats:
   out.append(finding("HABIT_UNSUPPORTED_CATEGORY",SEVERITY_INFO,"habits",
     f"Habit {m.record_id} uses category '{m.category}' absent from assessments.",[m.record_id],[m.category],
     suggested_action="Check category mapping.",rule="Habit categories should be traceable when impact is claimed."))
 return out

def detect_analytics_alignment(analytics,assessments,tolerance=DEFAULT_TOLERANCE):
 index=defaultdict(list);out=[]
 for m in assessments:
  if m.canonical_value is not None:index[(category_key(m.category),_text(m.metric))].append(m)
 for a in analytics:
  if a.canonical_value is None:continue
  candidates=index.get((category_key(a.category),_text(a.metric)),[])
  if not candidates:continue
  latest=max(candidates,key=lambda m:m.date or date.min)
  if latest.canonical_value is not None and not values_close(a.canonical_value,latest.canonical_value,tolerance):
   out.append(finding("ANALYTICS_ASSESSMENT_MISMATCH",SEVERITY_ERROR,"analytics",
     f"Analytics {a.record_id} reports {a.canonical_value:g}, latest assessment reports {latest.canonical_value:g}.",
     [a.record_id,latest.record_id],[a.category],[a.metric],latest.canonical_value,a.canonical_value,
     "Verify analytics source and observation period.",f"Analytics should agree within {tolerance:.1%}."))
 return out

def validate_metric_ranges(modules):
 out=[]
 for mod,ms in modules.items():
  for m in ms:
   if m.value is None:continue
   if m.dimension=="ratio" and not 0<=m.value<=100:
    out.append(finding("RATIO_OUT_OF_RANGE",SEVERITY_ERROR,mod,f"{m.metric}={m.value:g}% is outside 0-100.",[m.record_id],metrics=[m.metric],
                       observed=m.value,suggested_action="Verify percentage semantics.",rule="Percentages must be 0-100."))
   if m.metric.lower() in {"progress","completion"} and not 0<=m.value<=100:
    out.append(finding("PROGRESS_OUT_OF_RANGE",SEVERITY_ERROR,mod,f"{m.metric}={m.value:g} is outside 0-100.",[m.record_id],metrics=[m.metric],
                       observed=m.value,suggested_action="Validate progress before persistence.",rule="Progress is 0-100."))
 return out

def build_metric_matrix(modules):
 groups=defaultdict(list)
 for ms in modules.values():
  for m in ms:groups[(category_key(m.category),_text(m.metric))].append(m)
 return [{"category":normalize_category(k[0]),"metric":k[1],"modules":sorted({m.module for m in g}),
          "module_count":len({m.module for m in g}),
          "values":[{"module":m.module,"record_id":m.record_id,"value":m.value,"unit":m.unit,
                     "canonical_value":m.canonical_value,"canonical_unit":m.canonical_unit,
                     "date":m.date.isoformat() if m.date else None}
                    for m in sorted(g,key=lambda x:(x.module,x.record_id))]}
         for k,g in sorted(groups.items())]

def build_category_summary(modules):
 groups=defaultdict(lambda:defaultdict(int))
 for mod,ms in modules.items():
  for m in ms:
   if m.category!="Unknown":groups[category_key(m.category)][mod]+=1
 return [{"category":normalize_category(k),"modules":dict(sorted(v.items())),"module_count":len(v),
          "coverage_percent":round(len(v)/len(MODULES)*100,2)}
         for k,v in sorted(groups.items())]

def calculate_consistency_score(findings,record_count):
 if record_count<=0:return 0.0
 penalty=sum({SEVERITY_CRITICAL:20,SEVERITY_ERROR:10,SEVERITY_WARNING:4,SEVERITY_INFO:1}.get(x.severity,1) for x in findings)
 return round(max(0,min(100,100-(penalty/max(record_count,1))*10)),2)

def report_status(findings,record_count):
 if record_count==0:return STATUS_INSUFFICIENT_DATA
 if any(x.severity in (SEVERITY_CRITICAL,SEVERITY_ERROR) for x in findings):return STATUS_INCONSISTENT
 return STATUS_REVIEW if findings else STATUS_CONSISTENT

def sort_findings(findings):
 return sorted(findings,key=lambda x:(SEVERITY_ORDER.get(x.severity,99),x.code,x.module,x.message,x.record_ids))

def validate_all_modules(data,user_id=None,tolerance=DEFAULT_TOLERANCE,max_date_skew_days=366):
 modules=normalize_all_modules(data); results={};allf=[]
 if user_id is not None:
  uid=str(user_id)
  modules={k:[m for m in v if m.user_id is None or m.user_id==uid] for k,v in modules.items()}
 for mod in MODULES:
  results[mod]=validate_module_metrics(mod,modules[mod]);allf.extend(results[mod].findings)
 allm=[m for ms in modules.values() for m in ms]
 allf.extend(compare_category_taxonomy(modules));allf.extend(compare_units(allm,tolerance))
 allf.extend(compare_dates(modules,max_date_skew_days));allf.extend(compare_user_scopes(modules))
 allf.extend(detect_duplicate_metric_identities(modules));allf.extend(detect_orphan_references(modules))
 allf.extend(detect_goal_metric_consistency(modules["goals"],modules["assessments"],tolerance))
 allf.extend(detect_recommendation_alignment(modules["recommendations"],modules["assessments"]))
 allf.extend(detect_action_plan_alignment(modules["action_plans"],modules["recommendations"]))
 allf.extend(detect_habit_alignment(modules["habits"],modules["assessments"]))
 allf.extend(detect_analytics_alignment(modules["analytics"],modules["assessments"],tolerance))
 allf.extend(validate_metric_ranges(modules));allf=sort_findings(deduplicate_findings(allf))
 total=len(allm);counts=Counter(x.severity for x in allf)
 return ConsistencyReport(_now(),ENGINE_VERSION,str(user_id) if user_id is not None else None,report_status(allf,total),
   calculate_consistency_score(allf,total),results,allf,build_metric_matrix(modules),build_category_summary(modules),
   {"total_records":total,"total_findings":len(allf),"critical":counts.get(SEVERITY_CRITICAL,0),"errors":counts.get(SEVERITY_ERROR,0),
    "warnings":counts.get(SEVERITY_WARNING,0),"info":counts.get(SEVERITY_INFO,0),"modules_checked":6,
    "modules_with_data":sum(bool(v) for v in modules.values()),
    "categories_seen":len({category_key(m.category) for m in allm if m.category!="Unknown"})})

def _now():return datetime.now(timezone.utc).isoformat()
def create_validation_snapshot(data,**kwargs):return validate_all_modules(data,**kwargs)
def summarize_findings(findings):
 c=Counter(x.severity for x in findings);return {"critical":c.get(SEVERITY_CRITICAL,0),"error":c.get(SEVERITY_ERROR,0),
 "warning":c.get(SEVERITY_WARNING,0),"info":c.get(SEVERITY_INFO,0),"total":len(findings)}
def findings_for_module(findings,module):return [x for x in findings if x.module==module]
def findings_for_category(findings,category):
 k=category_key(category);return [x for x in findings if any(category_key(c)==k for c in x.categories)]
def findings_by_severity(findings,severity):return [x for x in findings if x.severity==severity]
def unsupported_units(metrics):return {m.unit for m in metrics if m.dimension is None}
def canonical_categories(metrics):return {normalize_category(m.category) for m in metrics if m.category!="Unknown"}
def category_coverage(modules):
 out=defaultdict(set)
 for mod,ms in modules.items():
  for m in ms:
   if m.category!="Unknown":out[normalize_category(m.category)].add(mod)
 return dict(out)
def metric_identity(m):return category_key(m.category),_text(m.metric)
def explain_unit_difference(a,b):
 if a.unit==b.unit:return f"Both use {a.unit}."
 if a.dimension!=b.dimension:return f"{a.unit} and {b.unit} are different physical dimensions."
 if a.canonical_unit==b.canonical_unit:return f"{a.unit} and {b.unit} are compatible and normalize to {a.canonical_unit}."
 return f"No canonical conversion is registered for {a.unit} and {b.unit}."
def compare_two_metrics(a,b,tolerance=DEFAULT_TOLERANCE):
 compatible=a.dimension is not None and a.dimension==b.dimension
 if compatible and a.canonical_value is not None and b.canonical_value is not None:
  diff=b.canonical_value-a.canonical_value;rel=abs(diff)/max(abs(a.canonical_value),abs(b.canonical_value),1);same=rel<=tolerance
 else:diff=rel=None;same=False
 return {"left":a.to_dict(),"right":b.to_dict(),"compatible_units":compatible,
         "same_value_within_tolerance":same,"difference":diff,"relative_difference":rel,
         "unit_explanation":explain_unit_difference(a,b)}
def validate_snapshot_pair(first,second,tolerance=DEFAULT_TOLERANCE):
 a=normalize_all_modules(first);b=normalize_all_modules(second);out=[]
 for mod in MODULES:
  ai={metric_identity(x):x for x in a[mod]};bi={metric_identity(x):x for x in b[mod]}
  for ident in sorted(set(ai)&set(bi)):
   l,r=ai[ident],bi[ident]
   if l.canonical_value is None or r.canonical_value is None:continue
   if l.dimension!=r.dimension:
    out.append(finding("SNAPSHOT_UNIT_CONFLICT",SEVERITY_ERROR,mod,f"Metric {ident} changed physical dimension.",
                        [l.record_id,r.record_id],metrics=[l.metric],expected=l.dimension,observed=r.dimension,
                        suggested_action="Verify metric definition.",rule="Metric identity retains physical dimension."))
   elif not values_close(l.canonical_value,r.canonical_value,tolerance):
    out.append(finding("SNAPSHOT_VALUE_CHANGE",SEVERITY_INFO,mod,f"Metric {ident} changed between snapshots.",
                        [l.record_id,r.record_id],metrics=[l.metric],expected=l.canonical_value,observed=r.canonical_value,
                        suggested_action="Confirm this is a real observation change.",rule="Snapshot changes are informational."))
 return sort_findings(out)
def validate_date_order(records):
 out=[];dated=[x for x in records if x.date]
 for a,b in zip(dated,dated[1:]):
  if b.date<a.date:out.append(finding("DATE_ORDER_VIOLATION",SEVERITY_WARNING,a.module,f"Record {b.record_id} precedes {a.record_id}.",
                                      [a.record_id,b.record_id],suggested_action="Sort the time series.",rule="Chronological data should be ordered."))
 return out
def validate_goal_triplet(baseline,current,target,unit="kg CO2e"):
 b,c,t=map(_finite,(baseline,current,target));out=[]
 if any(x is None for x in (b,c,t)):return [finding("INVALID_GOAL_TRIPLET",SEVERITY_ERROR,"goals","Baseline/current/target must be finite.",expected="finite numbers",observed=[b,c,t],
   suggested_action="Repair goal metrics.",rule="Goal metrics are numeric.")]
 if min(b,c,t)<0:out.append(finding("NEGATIVE_GOAL_VALUE",SEVERITY_ERROR,"goals","Goal values cannot be negative.",observed=[b,c,t],
   suggested_action="Verify source metric.",rule="Footprint values are non-negative."))
 if t>b:out.append(finding("TARGET_ABOVE_BASELINE",SEVERITY_WARNING,"goals",f"Target {t:g} {unit} is above baseline {b:g}.",
   expected=b,observed=t,suggested_action="Confirm goal direction.",rule="Reduction targets normally do not exceed baseline."))
 if b>0 and c>b*1.5:out.append(finding("CURRENT_ABOVE_BASELINE",SEVERITY_WARNING,"goals",f"Current {c:g} is >50% above baseline {b:g}.",
   expected=b,observed=c,suggested_action="Verify current assessment and baseline.",rule="Large divergence needs review."))
 return out
def validate_recommendation_range(low,high,unit="kg CO2e"):
 l,h=_finite(low),_finite(high)
 if l is None or h is None:return []
 out=[]
 if l<0 or h<0:out.append(finding("NEGATIVE_IMPACT_ESTIMATE",SEVERITY_WARNING,"recommendations","Impact estimates should not be negative.",
   observed=[l,h],suggested_action="Use an explicit signed delta if needed.",rule="Savings ranges are non-negative."))
 if h<l:out.append(finding("REVERSED_IMPACT_RANGE",SEVERITY_ERROR,"recommendations",f"Impact range {l:g}-{h:g} {unit} is reversed.",
   expected=f"high >= {l:g}",observed=h,suggested_action="Correct range endpoints.",rule="High must be >= low."))
 return out
def validate_metric_definition(name,category,unit):
 out=[]
 if not str(name).strip():out.append(finding("MISSING_METRIC_NAME",SEVERITY_ERROR,"definition","Metric definition has no name.",
   suggested_action="Provide stable metric identity.",rule="Every metric requires an identity."))
 if normalize_category(category)=="Unknown":out.append(finding("UNKNOWN_CATEGORY",SEVERITY_WARNING,"definition",f"Metric '{name}' has unknown category.",
   categories=[str(category)],suggested_action="Map to shared taxonomy.",rule="Categories should be canonical."))
 if unit_dimension(unit) is None:out.append(finding("UNKNOWN_UNIT",SEVERITY_WARNING,"definition",f"Metric '{name}' uses unknown unit '{unit}'.",
   observed=unit,suggested_action="Register unit dimension.",rule="Units must be known."))
 return out
def export_report(report):return report.to_json()
def import_report(payload):
 try:d=json.loads(payload)
 except json.JSONDecodeError as e:raise MetricConsistencyError("Invalid consistency report JSON.") from e
 if not isinstance(d,dict):raise MetricConsistencyError("Consistency report must be a JSON object.")
 missing={"generated_at","engine_version","status","score","findings"}-set(d)
 if missing:raise MetricConsistencyError("Missing report fields: "+", ".join(sorted(missing)))
 return d
def ensure_storage(conn):
 conn.execute("""CREATE TABLE IF NOT EXISTS metric_consistency_reports(
 id INTEGER PRIMARY KEY AUTOINCREMENT,user_id TEXT,generated_at TEXT NOT NULL,engine_version TEXT NOT NULL,
 status TEXT NOT NULL,score REAL NOT NULL,finding_count INTEGER NOT NULL,report_json TEXT NOT NULL)""");conn.commit()
def persist_report(report,connection=None,db_path=DB_NAME):
 own=connection is None;conn=connection or sqlite3.connect(db_path)
 try:
  ensure_storage(conn);cur=conn.execute("INSERT INTO metric_consistency_reports(user_id,generated_at,engine_version,status,score,finding_count,report_json) VALUES(?,?,?,?,?,?,?)",
    (report.user_id,report.generated_at,report.engine_version,report.status,report.score,len(report.findings),report.to_json()));conn.commit();return cur.lastrowid
 finally:
  if own:conn.close()
def load_reports(connection=None,db_path=DB_NAME,user_id=None,limit=20):
 own=connection is None;conn=connection or sqlite3.connect(db_path)
 try:
  ensure_storage(conn);limit=max(1,min(int(limit),200))
  if user_id is None:rows=conn.execute("SELECT id,user_id,generated_at,engine_version,status,score,finding_count FROM metric_consistency_reports ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
  else:rows=conn.execute("SELECT id,user_id,generated_at,engine_version,status,score,finding_count FROM metric_consistency_reports WHERE user_id=? ORDER BY id DESC LIMIT ?",(str(user_id),limit)).fetchall()
  return [{"id":r[0],"user_id":r[1],"generated_at":r[2],"engine_version":r[3],"status":r[4],"score":r[5],"finding_count":r[6]} for r in rows]
 finally:
  if own:conn.close()
def load_report(report_id,connection=None,db_path=DB_NAME):
 own=connection is None;conn=connection or sqlite3.connect(db_path)
 try:
  ensure_storage(conn);r=conn.execute("SELECT report_json FROM metric_consistency_reports WHERE id=?",(int(report_id),)).fetchone()
  return json.loads(r[0]) if r else None
 finally:
  if own:conn.close()
def delete_report(report_id,connection=None,db_path=DB_NAME):
 own=connection is None;conn=connection or sqlite3.connect(db_path)
 try:
  ensure_storage(conn);cur=conn.execute("DELETE FROM metric_consistency_reports WHERE id=?",(int(report_id),));conn.commit();return cur.rowcount>0
 finally:
  if own:conn.close()
def report_hash(report):return hashlib.sha256(report.to_json(indent=0).encode()).hexdigest()
def compare_reports(left,right):
 a=left.to_dict() if isinstance(left,ConsistencyReport) else dict(left);b=right.to_dict() if isinstance(right,ConsistencyReport) else dict(right)
 ac=Counter(x.get("code") for x in a.get("findings",[]));bc=Counter(x.get("code") for x in b.get("findings",[]))
 return {"score_change":round(float(b.get("score",0))-float(a.get("score",0)),2),"status_changed":a.get("status")!=b.get("status"),
         "new_finding_codes":sorted(set(bc)-set(ac)),"resolved_finding_codes":sorted(set(ac)-set(bc)),
         "finding_code_counts_before":dict(ac),"finding_code_counts_after":dict(bc)}
def check_category(v):
 c=normalize_category(v);return {"input":v,"canonical":c,"known":c in KNOWN_CATEGORIES,"key":category_key(v)}
def check_unit(v):
 u=normalize_unit(v);d=unit_dimension(u);return {"input":v,"normalized":u,"dimension":d,"canonical":canonical_unit(u),"supported":d is not None}
def check_conversion(value,source,target):
 try:return {"supported":True,"value":_finite(value),"source":normalize_unit(source),"target":normalize_unit(target),"converted":convert_value(value,source,target)}
 except MetricConsistencyError as e:return {"supported":False,"value":_finite(value),"source":normalize_unit(source),"target":normalize_unit(target),"converted":None,"error":str(e)}
def build_health_summary(report):
 s=summarize_findings(report.findings)
 return {"status":report.status,"score":report.score,"finding_count":len(report.findings),"severity":s,
         "modules":{m:{"status":r.status,"records":r.record_count,"findings":len(r.findings)} for m,r in report.module_results.items()}}

__all__=[name for name in globals() if not name.startswith("_")]
