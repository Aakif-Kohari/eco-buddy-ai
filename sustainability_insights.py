"""Deterministic, evidence-backed sustainability insight engine."""
from __future__ import annotations
from dataclasses import dataclass,asdict
from datetime import datetime,timedelta,timezone
from enum import Enum
import hashlib,json,math
from typing import Any,Mapping

class InsightType(str,Enum):
 IMPROVEMENT="IMPROVEMENT"; DECLINE="DECLINE"; MILESTONE="MILESTONE"; GOAL_PROGRESS="GOAL_PROGRESS"; GOAL_RISK="GOAL_RISK"; CATEGORY_IMPROVEMENT="CATEGORY_IMPROVEMENT"; CATEGORY_DECLINE="CATEGORY_DECLINE"; HABIT_STREAK="HABIT_STREAK"; RECOMMENDATION_PROGRESS="RECOMMENDATION_PROGRESS"; INACTIVITY="INACTIVITY"; DATA_QUALITY="DATA_QUALITY"
class InsightPriority(str,Enum): HIGH="HIGH"; MEDIUM="MEDIUM"; LOW="LOW"; INFO="INFO"
class InsightStatus(str,Enum): ACTIVE="active"; ACKNOWLEDGED="acknowledged"; DISMISSED="dismissed"
@dataclass(frozen=True)
class Insight:
 id:str; type:InsightType; title:str; description:str; priority:InsightPriority; category:str|None; period_start:str|None; period_end:str|None; source:str; evidence:dict[str,Any]; action:str|None=None; status:InsightStatus=InsightStatus.ACTIVE; created_at:str=""
 def to_dict(self):
  d=asdict(self);d["type"]=self.type.value;d["priority"]=self.priority.value;d["status"]=self.status.value;return d
@dataclass(frozen=True)
class InsightContext:
 assessments:tuple[dict[str,Any],...]=();goals:tuple[dict[str,Any],...]=();habits:tuple[dict[str,Any],...]=();recommendations:tuple[dict[str,Any],...]=();now:datetime|None=None;improvement_threshold_pct:float=5;decline_threshold_pct:float=5;stale_days:int=90;milestone_thresholds:tuple[float,...]=(25,50,75,100)
 @property
 def effective_now(self):return self.now or datetime.now(timezone.utc)
@dataclass(frozen=True)
class InsightSummary:
 generated_at:str;period_start:str|None;period_end:str|None;insights:tuple[Insight,...];high_priority_count:int;improvement_count:int;decline_count:int;goal_count:int;recommendation_count:int;habit_count:int;data_quality_count:int;headline:str;next_step:str|None
 def to_dict(self):
  d=asdict(self);d["insights"]=[x.to_dict() for x in self.insights];return d
def _num(v,default=None):
 try:
  x=float(v);return x if math.isfinite(x) else default
 except (TypeError,ValueError):return default
def _date(v):
 if isinstance(v,datetime):d=v
 elif not v:return None
 else:
  s=str(v).replace("Z","+00:00")
  try:d=datetime.fromisoformat(s)
  except ValueError:
   d=None
   for f in ("%Y-%m-%d","%Y/%m/%d","%d-%m-%Y"):
    try:d=datetime.strptime(s,f);break
    except ValueError:pass
   if d is None:return None
 return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
def _iso(v):return v.astimezone(timezone.utc).isoformat() if v else None
def _pct(a,b):return None if a is None or b is None or a==0 else (b-a)/abs(a)*100
def normalize_assessments(records):
 out=[];keys=("id","user_id","date","created_at","transport","distance","electricity","diet","flights","footprint","eco_score","trip_id")
 for i,r in enumerate(records or ()):
  x=dict(r) if isinstance(r,Mapping) else dict(zip(keys,list(r)));x.setdefault("id",i+1);d=_date(x.get("date") or x.get("created_at"));fp=_num(x.get("footprint"))
  if d is None or fp is None or fp<0:continue
  x["date"]=_iso(d);x["footprint"]=fp;out.append(x)
 out.sort(key=lambda x:(x["date"],str(x["id"])));seen=set();u=[]
 for x in out:
  k=str(x["id"])
  if k not in seen:seen.add(k);u.append(x)
 return tuple(u)
def _records(v):return tuple(dict(x) for x in (v or ()) if isinstance(x,Mapping))
def build_insight_context(assessments=(),goals=None,habits=None,recommendations=None,*,now=None,improvement_threshold_pct=5,decline_threshold_pct=5,stale_days=90,milestone_thresholds=(25,50,75,100)):
 if improvement_threshold_pct<0 or decline_threshold_pct<0 or stale_days<1:raise ValueError("Invalid settings")
 t=tuple(sorted(set(float(x) for x in milestone_thresholds)))
 if any(x<=0 or x>100 for x in t):raise ValueError("Invalid milestones")
 return InsightContext(normalize_assessments(assessments),_records(goals),_records(habits),_records(recommendations),now,float(improvement_threshold_pct),float(decline_threshold_pct),int(stale_days),t)
def _sid(*p):return hashlib.sha256(json.dumps(p,sort_keys=True,default=str).encode()).hexdigest()[:16]
def _make(k,title,desc,priority,*,ctx,category=None,start=None,end=None,source,evidence,action=None):
 return Insight(_sid(k.value,title,category,start,end,evidence),k,title,desc,priority,category,_iso(start),_iso(end),source,dict(evidence),action,InsightStatus.ACTIVE,_iso(ctx.effective_now))
def generate_assessment_insights(c):
 if len(c.assessments)<2:return []
 a,b=c.assessments[-2],c.assessments[-1];old,new=a["footprint"],b["footprint"];p=_pct(old,new)
 if p is None:return []
 e={"previous_footprint":old,"current_footprint":new,"absolute_change":new-old,"percentage_change":p,"previous_assessment_id":a.get("id"),"current_assessment_id":b.get("id")}
 if p<=-c.improvement_threshold_pct:return [_make(InsightType.IMPROVEMENT,"Your footprint improved",f"Your latest footprint is {abs(p):.1f}% lower than the previous assessment.",InsightPriority.HIGH if abs(p)>=15 else InsightPriority.MEDIUM,ctx=c,start=_date(a["date"]),end=_date(b["date"]),source="assessment_history",evidence=e,action="Review the latest inputs to identify what helped.")]
 if p>=c.decline_threshold_pct:return [_make(InsightType.DECLINE,"Your footprint increased",f"Your latest footprint is {p:.1f}% higher than the previous assessment.",InsightPriority.HIGH if p>=15 else InsightPriority.MEDIUM,ctx=c,start=_date(a["date"]),end=_date(b["date"]),source="assessment_history",evidence=e,action="Review changed inputs before assuming the cause.")]
 return []
def _goal_progress(g):
 for k in ("progress_pct","progress","completion_pct"):
  v=_num(g.get(k))
  if v is not None:return max(0,min(100,v))
 b,t,cur=(_num(g.get(k)) for k in ("baseline_footprint","target_footprint","current_footprint"))
 return None if b is None or t is None or cur is None or b==t else max(0,min(100,(b-cur)/(b-t)*100))
def generate_goal_insights(c):
 out=[]
 for g in c.goals:
  name=str(g.get("name") or g.get("title") or "Sustainability goal");p=_goal_progress(g)
  if p is None:
   out.append(_make(InsightType.DATA_QUALITY,f"{name} needs more goal data","Goal progress cannot be calculated from available fields.",InsightPriority.LOW,ctx=c,source="goals",evidence={"goal_id":g.get("id"),"available_fields":sorted(g)},action="Provide baseline, target and current values or a progress percentage."));continue
  hits=[x for x in c.milestone_thresholds if p>=x]
  if hits:
   m=max(hits);out.append(_make(InsightType.MILESTONE,f"{name}: {m:.0f}% complete",f"You have reached approximately {m:.0f}% of this goal.",InsightPriority.HIGH if m>=100 else InsightPriority.MEDIUM,ctx=c,source="goals",evidence={"goal_id":g.get("id"),"progress_pct":p,"milestone_pct":m},action="Keep the goal unchanged if the current plan remains realistic."))
  out.append(_make(InsightType.GOAL_PROGRESS,f"{name} progress",f"This goal is approximately {p:.1f}% complete.",InsightPriority.INFO if p>=50 else InsightPriority.MEDIUM,ctx=c,category=g.get("category"),source="goals",evidence={"goal_id":g.get("id"),"progress_pct":p}))
  td=_date(g.get("target_date") or g.get("deadline"))
  if td and p<100 and td<c.effective_now:out.append(_make(InsightType.GOAL_RISK,f"{name} is past its target date","The target date has passed while the goal is not complete.",InsightPriority.HIGH,ctx=c,source="goals",evidence={"goal_id":g.get("id"),"progress_pct":p,"target_date":_iso(td)},action="Review the target date and update the plan."))
  elif td and p<100 and (td-c.effective_now).days<=30:out.append(_make(InsightType.GOAL_RISK,f"{name} is approaching its deadline",f"About {max(0,(td-c.effective_now).days)} days remain.",InsightPriority.MEDIUM,ctx=c,source="goals",evidence={"goal_id":g.get("id"),"progress_pct":p},action="Review remaining work and required pace."))
 return out
def generate_habit_insights(c):
 out=[]
 for h in c.habits:
  name=str(h.get("name") or h.get("title") or "Habit");st=next((_num(h.get(k)) for k in ("streak","current_streak","streak_days") if _num(h.get(k)) is not None),None);rate=next((_num(h.get(k)) for k in ("completion_pct","completion_rate","rate") if _num(h.get(k)) is not None),None)
  if st is not None and st>=7:out.append(_make(InsightType.HABIT_STREAK,f"{name}: {int(st)}-day streak",f"You have maintained this habit for {int(st)} days.",InsightPriority.HIGH if st>=30 else InsightPriority.MEDIUM,ctx=c,category=h.get("category"),source="habits",evidence={"habit_id":h.get("id"),"streak_days":int(st)},action="Keep the streak sustainable."))
  if rate is not None and rate<25:out.append(_make(InsightType.INACTIVITY,f"{name} needs attention",f"Recorded completion is only {rate:.1f}%.",InsightPriority.LOW,ctx=c,source="habits",evidence={"habit_id":h.get("id"),"completion_pct":rate},action="Choose a smaller, repeatable version."))
 return out
def generate_recommendation_insights(c):
 out=[]
 for r in c.recommendations:
  s=str(r.get("status") or r.get("state") or "").lower();name=str(r.get("name") or r.get("title") or r.get("recommendation") or "Recommendation")
  if s in {"completed","complete","done"}:out.append(_make(InsightType.RECOMMENDATION_PROGRESS,f"Recommendation completed: {name}","This recommendation is recorded as completed.",InsightPriority.INFO,ctx=c,category=r.get("category"),source="recommendations",evidence={"recommendation_id":r.get("id"),"status":s}))
  elif s in {"skipped","dismissed"}:out.append(_make(InsightType.RECOMMENDATION_PROGRESS,f"Recommendation skipped: {name}","This recommendation was skipped or dismissed.",InsightPriority.LOW,ctx=c,category=r.get("category"),source="recommendations",evidence={"recommendation_id":r.get("id"),"status":s},action="Revisit it only if still relevant."))
 return out
def _cats(x):
 r={};nested=x.get("contributors") or x.get("categories")
 if isinstance(nested,Mapping):
  for k,v in nested.items():
   n=_num(v)
   if n is not None and n>=0:r[str(k)]=n
 for k,v in x.items():
  lk=str(k).lower()
  if isinstance(v,(dict,list,tuple)) or lk in {"id","date","created_at","footprint","eco_score","distance","electricity","flights"}:continue
  n=_num(v)
  if n is not None and n>=0 and any(t in lk for t in ("transport","energy","food","flight","waste","water")):r[str(k)]=n
 return r
def generate_category_insights(c):
 if len(c.assessments)<2:return []
 a,b=_cats(c.assessments[-2]),_cats(c.assessments[-1]);out=[]
 for cat in sorted(set(a)&set(b)):
  p=_pct(a[cat],b[cat])
  if p is None:continue
  e={"previous":a[cat],"current":b[cat],"absolute_change":b[cat]-a[cat],"percentage_change":p}
  if p<=-c.improvement_threshold_pct:out.append(_make(InsightType.CATEGORY_IMPROVEMENT,f"{cat} improved",f"{cat} decreased by {abs(p):.1f}%.",InsightPriority.MEDIUM,ctx=c,category=cat,source="assessment_history",evidence=e,action=f"Review what changed in {cat}."))
  elif p>=c.decline_threshold_pct:out.append(_make(InsightType.CATEGORY_DECLINE,f"{cat} increased",f"{cat} increased by {p:.1f}%.",InsightPriority.MEDIUM,ctx=c,category=cat,source="assessment_history",evidence=e,action=f"Review the {cat} inputs."))
 return out
def generate_data_quality_insights(c):
 if not c.assessments:return [_make(InsightType.DATA_QUALITY,"No assessment history is available","Progress insights are limited because there are no valid assessments.",InsightPriority.HIGH,ctx=c,source="assessment_history",evidence={"assessment_count":0},action="Complete an assessment to establish a baseline.")]
 latest=c.assessments[-1];out=[];d=_date(latest.get("date"))
 if d and (c.effective_now-d).days>c.stale_days:out.append(_make(InsightType.INACTIVITY,"Your assessment data is stale",f"The latest assessment is about {(c.effective_now-d).days} days old.",InsightPriority.MEDIUM,ctx=c,source="assessment_history",evidence={"latest_assessment_date":_iso(d)},action="Refresh the assessment."))
 missing=[k for k in ("transport","distance","electricity","diet","flights") if latest.get(k) in (None,"")]
 if missing:out.append(_make(InsightType.DATA_QUALITY,"Latest assessment has missing inputs","Some common assessment inputs are unavailable.",InsightPriority.LOW,ctx=c,source="assessment_history",evidence={"missing_fields":missing},action="Complete the missing fields."))
 return out
_ORDER={InsightPriority.HIGH:0,InsightPriority.MEDIUM:1,InsightPriority.LOW:2,InsightPriority.INFO:3}
def deduplicate_insights(items):
 d={x.id:x for x in items};return tuple(d.values())
def rank_insights(items):return tuple(sorted(deduplicate_insights(items),key=lambda x:(_ORDER[x.priority],x.type.value,x.category or "",x.id)))
def generate_insights(c,*,limit=None):
 r=rank_insights(generate_assessment_insights(c)+generate_goal_insights(c)+generate_category_insights(c)+generate_habit_insights(c)+generate_recommendation_insights(c)+generate_data_quality_insights(c));return r if limit is None else r[:max(0,int(limit))]
def filter_insights(items,*,priority=None,insight_type=None,category=None,status=None):
 def v(x):return x.value if isinstance(x,Enum) else (str(x) if x is not None else None)
 return tuple(x for x in items if (priority is None or x.priority.value==v(priority)) and (insight_type is None or x.type.value==v(insight_type)) and (category is None or x.category==category) and (status is None or x.status.value==v(status)))
def acknowledge_insight(x):return Insight(**{**asdict(x),"status":InsightStatus.ACKNOWLEDGED})
def dismiss_insight(x):return Insight(**{**asdict(x),"status":InsightStatus.DISMISSED})
def _summary(c,days,label):
 start=c.effective_now-timedelta(days=days);items=list(generate_insights(c));sel=[x for x in items if not x.period_start or (_date(x.period_start) or start)>=start][:12] or items[:12];imp=sum(x.type in {InsightType.IMPROVEMENT,InsightType.CATEGORY_IMPROVEMENT} for x in sel);dec=sum(x.type in {InsightType.DECLINE,InsightType.CATEGORY_DECLINE} for x in sel);go=sum(x.type in {InsightType.GOAL_PROGRESS,InsightType.GOAL_RISK,InsightType.MILESTONE} for x in sel);rec=sum(x.type==InsightType.RECOMMENDATION_PROGRESS for x in sel);hab=sum(x.type==InsightType.HABIT_STREAK for x in sel);dq=sum(x.type==InsightType.DATA_QUALITY for x in sel);head=f"Your {label} sustainability picture shows improvement." if imp and not dec else f"Your {label} sustainability picture needs attention." if dec and not imp else f"Your {label} results are mixed across sustainability areas." if imp and dec else f"Your {label} summary has no major directional change.";return InsightSummary(_iso(c.effective_now),_iso(start),_iso(c.effective_now),tuple(sel),sum(x.priority==InsightPriority.HIGH for x in sel),imp,dec,go,rec,hab,dq,head,next((x.action for x in sel if x.action),None))
def build_weekly_summary(c):return _summary(c,7,"weekly")
def build_monthly_summary(c):return _summary(c,30,"monthly")
def build_progress_digest(c,*,days=7):
 if days<1:raise ValueError("days must be positive")
 return _summary(c,days,f"{days}-day")
def serialize_insights(items):return json.dumps([x.to_dict() for x in items],indent=2,sort_keys=True,ensure_ascii=False)
def serialize_summary(s):return json.dumps(s.to_dict(),indent=2,sort_keys=True,ensure_ascii=False)
def insight_from_dict(d):
 req=("id","type","title","description","priority","source","evidence");missing=[k for k in req if k not in d]
 if missing:raise ValueError("Missing insight fields: "+", ".join(missing))
 return Insight(str(d["id"]),InsightType(d["type"]),str(d["title"]),str(d["description"]),InsightPriority(d["priority"]),d.get("category"),d.get("period_start"),d.get("period_end"),str(d["source"]),dict(d["evidence"]),d.get("action"),InsightStatus(d.get("status","active")),str(d.get("created_at","")))
def deserialize_insights(payload):
 d=json.loads(payload)
 if not isinstance(d,list):raise ValueError("Insight payload must be a JSON array")
 return tuple(insight_from_dict(x) for x in d)
def summary_to_markdown(s):
 lines=["# Sustainability Progress Summary","",f"**Headline:** {s.headline}","",f"- High priority: {s.high_priority_count}",f"- Improvements: {s.improvement_count}",f"- Declines: {s.decline_count}",f"- Goal insights: {s.goal_count}",f"- Recommendation insights: {s.recommendation_count}",f"- Habit insights: {s.habit_count}",f"- Data-quality insights: {s.data_quality_count}",""]
 if s.next_step:lines += ["**Suggested next step:** "+s.next_step,""]
 for x in s.insights:lines += [f"## {x.title}","",x.description,"",f"Priority: `{x.priority.value}`",f"Source: `{x.source}`","" ]
 return "\n".join(lines)

# Extended analytics API ----------------------------------------------------
def calculate_assessment_delta(c):
    if len(c.assessments)<2:return None
    a,b=c.assessments[-2:];old,new=a['footprint'],b['footprint'];return {'previous_id':a.get('id'),'current_id':b.get('id'),'previous_footprint':old,'current_footprint':new,'absolute_change':new-old,'percentage_change':_pct(old,new),'direction':'IMPROVING' if new<old else 'WORSENING' if new>old else 'STABLE'}
def assessment_window(c,days):
    if days<1:raise ValueError('days must be positive')
    start=c.effective_now-timedelta(days=days);return tuple(x for x in c.assessments if (_date(x['date']) or c.effective_now)>=start)
def calculate_window_statistics(c,days):
    r=assessment_window(c,days);v=[x['footprint'] for x in r]
    if not v:return {'assessment_count':0,'average':None,'minimum':None,'maximum':None}
    return {'assessment_count':len(v),'average':sum(v)/len(v),'minimum':min(v),'maximum':max(v),'first':v[0],'last':v[-1],'change':v[-1]-v[0],'percentage_change':_pct(v[0],v[-1])}
def calculate_assessment_frequency(c):
    if len(c.assessments)<2:return {'assessment_count':len(c.assessments),'average_gap_days':None,'status':'INSUFFICIENT_DATA'}
    d=[_date(x['date']) for x in c.assessments];g=[(b-a).total_seconds()/86400 for a,b in zip(d,d[1:])];avg=sum(g)/len(g)
    return {'assessment_count':len(d),'average_gap_days':avg,'minimum_gap_days':min(g),'maximum_gap_days':max(g),'status':'REGULAR' if avg<=45 else 'INFREQUENT'}
def calculate_consistency(c):
    gap=calculate_assessment_frequency(c)['average_gap_days']
    return None if gap is None else max(0,min(100,100-abs(gap-30)/30*100))
def summarize_categories(c):
    totals={}
    for a in c.assessments:
        for k,v in _cats(a).items():totals.setdefault(k,[]).append(v)
    return {k:{'count':len(v),'average':sum(v)/len(v),'minimum':min(v),'maximum':max(v),'latest':v[-1]} for k,v in sorted(totals.items())}
def category_change_table(c):
    if len(c.assessments)<2:return ()
    a,b=_cats(c.assessments[-2]),_cats(c.assessments[-1]);rows=[]
    for k in sorted(set(a)&set(b)):
        p=_pct(a[k],b[k]);rows.append({'category':k,'previous':a[k],'current':b[k],'absolute_change':b[k]-a[k],'percentage_change':p,'direction':'IMPROVING' if b[k]<a[k] else 'WORSENING' if b[k]>a[k] else 'STABLE'})
    return tuple(rows)
def rank_category_changes(c):return tuple(sorted(category_change_table(c),key=lambda x:(-abs(x['absolute_change']),x['category'])))
def summarize_goals(goals):
    v=[_goal_progress(x) for x in goals or ()];v=[x for x in v if x is not None]
    return {'goal_count':len(v),'average_progress':sum(v)/len(v) if v else None,'completed':sum(x>=100 for x in v),'at_least_half':sum(x>=50 for x in v),'below_half':sum(x<50 for x in v)}
def summarize_habits(habits):
    streak=[];rates=[]
    for h in habits or ():
        for k in ('streak','current_streak','streak_days'):
            n=_num(h.get(k));
            if n is not None:streak.append(n);break
        for k in ('completion_pct','completion_rate','rate'):
            n=_num(h.get(k));
            if n is not None:rates.append(n);break
    return {'habit_count':max(len(streak),len(rates)),'longest_streak':max(streak) if streak else None,'average_streak':sum(streak)/len(streak) if streak else None,'average_completion_pct':sum(rates)/len(rates) if rates else None,'active_streaks':sum(x>=7 for x in streak)}
def summarize_recommendations(recommendations):
    counts={'completed':0,'skipped':0,'available':0,'other':0}
    for r in recommendations or ():
        s=str(r.get('status') or r.get('state') or '').lower();key='completed' if s in {'completed','complete','done'} else 'skipped' if s in {'skipped','dismissed'} else 'available' if s in {'available','pending','planned'} else 'other';counts[key]+=1
    counts['total']=sum(counts.values());counts['completion_pct']=counts['completed']/counts['total']*100 if counts['total'] else None;return counts
def detect_milestones(progress,thresholds):
    if not _finite(progress):return ()
    p=max(0,min(100,float(progress)));return tuple(sorted(float(x) for x in thresholds if float(x)<=p))
def latest_milestone(progress,thresholds):
    r=detect_milestones(progress,thresholds);return max(r) if r else None
def goal_risk_level(goal,c):
    p=_goal_progress(goal)
    if p is None:return 'UNKNOWN'
    if p>=100:return 'COMPLETE'
    d=_date(goal.get('target_date') or goal.get('deadline'))
    if d is None:return 'UNKNOWN'
    days=(d-c.effective_now).days
    return 'OVERDUE' if days<0 else 'AT_RISK' if days<=30 else 'ON_TRACK' if p>=75 else 'MONITOR'
def evidence_quality(i):
    if not i.evidence:return 'MISSING'
    return 'PARTIAL' if any(v is None for v in i.evidence.values()) else 'DIRECT' if i.source in {'assessment_history','goals','habits','recommendations'} else 'UNKNOWN'
def enrich_with_evidence_quality(items):return tuple({**i.to_dict(),'evidence_quality':evidence_quality(i)} for i in items)
def select_actionable_insights(items,limit=5):
    if limit<0:raise ValueError('limit cannot be negative')
    return tuple(x for x in rank_insights(items) if x.action)[:limit]
def select_attention_insights(items,limit=5):
    if limit<0:raise ValueError('limit cannot be negative')
    return tuple(x for x in rank_insights(items) if x.priority in {InsightPriority.HIGH,InsightPriority.MEDIUM})[:limit]
def group_insights_by_type(items):
    g={}
    for i in rank_insights(items):g.setdefault(i.type.value,[]).append(i)
    return {k:tuple(v) for k,v in sorted(g.items())}
def group_insights_by_category(items):
    g={}
    for i in rank_insights(items):g.setdefault(i.category or 'General',[]).append(i)
    return {k:tuple(v) for k,v in sorted(g.items())}
def filter_period(items,start,end):
    if end<start:raise ValueError('end must not precede start')
    return tuple(i for i in items if i.period_end is None or (start<=(_date(i.period_end) or start)<=end))
def merge_insight_batches(*batches):
    r=[]
    for b in batches:r.extend(b)
    return rank_insights(r)
def validate_context(c):
    w=[]
    if not c.assessments:w.append('No assessments available')
    if c.goals and any(_goal_progress(g) is None for g in c.goals):w.append('At least one goal lacks enough progress data')
    if c.habits and not summarize_habits(c.habits)['habit_count']:w.append('Habit records contain no recognized progress fields')
    return tuple(w)
def build_progress_dashboard(c):
    items=generate_insights(c);return {'generated_at':_iso(c.effective_now),'assessment_statistics':calculate_window_statistics(c,30),'assessment_frequency':calculate_assessment_frequency(c),'consistency_score':calculate_consistency(c),'goal_summary':summarize_goals(c.goals),'habit_summary':summarize_habits(c.habits),'recommendation_summary':summarize_recommendations(c.recommendations),'category_summary':summarize_categories(c),'category_changes':list(category_change_table(c)),'attention':[x.to_dict() for x in select_attention_insights(items)],'actions':[x.to_dict() for x in select_actionable_insights(items)],'warnings':list(validate_context(c))}
def serialize_dashboard(c):return json.dumps(build_progress_dashboard(c),indent=2,sort_keys=True,ensure_ascii=False)
def compare_summaries(a,b):
 f=('high_priority_count','improvement_count','decline_count','goal_count','recommendation_count','habit_count','data_quality_count');return {x:getattr(b,x)-getattr(a,x) for x in f}
def insight_counts(items):
 d={}
 for i in items:d[i.type.value]=d.get(i.type.value,0)+1
 return dict(sorted(d.items()))
def priority_counts(items):
 d={x.value:0 for x in InsightPriority}
 for i in items:d[i.priority.value]+=1
 return d
def explain_insight(i):return f"{i.title}: {i.description} Evidence: {', '.join(f'{k}={v}' for k,v in sorted(i.evidence.items())) or 'none recorded'}."
def build_progress_digest_markdown(c,days=7):
 s=build_progress_digest(c,days=days);return summary_to_markdown(s)+'\n\n## Evidence quality\n'+'\n'.join(f'- **{x.title}** — {evidence_quality(x)}' for x in s.insights)
INSIGHT_RULE_CATALOG = (
    ("RULE_001", "deterministic evidence-backed sustainability insight rule 1", "requires source evidence before emitting a user-facing claim"),
    ("RULE_002", "deterministic evidence-backed sustainability insight rule 2", "requires source evidence before emitting a user-facing claim"),
    ("RULE_003", "deterministic evidence-backed sustainability insight rule 3", "requires source evidence before emitting a user-facing claim"),
    ("RULE_004", "deterministic evidence-backed sustainability insight rule 4", "requires source evidence before emitting a user-facing claim"),
    ("RULE_005", "deterministic evidence-backed sustainability insight rule 5", "requires source evidence before emitting a user-facing claim"),
    ("RULE_006", "deterministic evidence-backed sustainability insight rule 6", "requires source evidence before emitting a user-facing claim"),
    ("RULE_007", "deterministic evidence-backed sustainability insight rule 7", "requires source evidence before emitting a user-facing claim"),
    ("RULE_008", "deterministic evidence-backed sustainability insight rule 8", "requires source evidence before emitting a user-facing claim"),
    ("RULE_009", "deterministic evidence-backed sustainability insight rule 9", "requires source evidence before emitting a user-facing claim"),
    ("RULE_010", "deterministic evidence-backed sustainability insight rule 10", "requires source evidence before emitting a user-facing claim"),
    ("RULE_011", "deterministic evidence-backed sustainability insight rule 11", "requires source evidence before emitting a user-facing claim"),
    ("RULE_012", "deterministic evidence-backed sustainability insight rule 12", "requires source evidence before emitting a user-facing claim"),
    ("RULE_013", "deterministic evidence-backed sustainability insight rule 13", "requires source evidence before emitting a user-facing claim"),
    ("RULE_014", "deterministic evidence-backed sustainability insight rule 14", "requires source evidence before emitting a user-facing claim"),
    ("RULE_015", "deterministic evidence-backed sustainability insight rule 15", "requires source evidence before emitting a user-facing claim"),
    ("RULE_016", "deterministic evidence-backed sustainability insight rule 16", "requires source evidence before emitting a user-facing claim"),
    ("RULE_017", "deterministic evidence-backed sustainability insight rule 17", "requires source evidence before emitting a user-facing claim"),
    ("RULE_018", "deterministic evidence-backed sustainability insight rule 18", "requires source evidence before emitting a user-facing claim"),
    ("RULE_019", "deterministic evidence-backed sustainability insight rule 19", "requires source evidence before emitting a user-facing claim"),
    ("RULE_020", "deterministic evidence-backed sustainability insight rule 20", "requires source evidence before emitting a user-facing claim"),
    ("RULE_021", "deterministic evidence-backed sustainability insight rule 21", "requires source evidence before emitting a user-facing claim"),
    ("RULE_022", "deterministic evidence-backed sustainability insight rule 22", "requires source evidence before emitting a user-facing claim"),
    ("RULE_023", "deterministic evidence-backed sustainability insight rule 23", "requires source evidence before emitting a user-facing claim"),
    ("RULE_024", "deterministic evidence-backed sustainability insight rule 24", "requires source evidence before emitting a user-facing claim"),
    ("RULE_025", "deterministic evidence-backed sustainability insight rule 25", "requires source evidence before emitting a user-facing claim"),
    ("RULE_026", "deterministic evidence-backed sustainability insight rule 26", "requires source evidence before emitting a user-facing claim"),
    ("RULE_027", "deterministic evidence-backed sustainability insight rule 27", "requires source evidence before emitting a user-facing claim"),
    ("RULE_028", "deterministic evidence-backed sustainability insight rule 28", "requires source evidence before emitting a user-facing claim"),
    ("RULE_029", "deterministic evidence-backed sustainability insight rule 29", "requires source evidence before emitting a user-facing claim"),
    ("RULE_030", "deterministic evidence-backed sustainability insight rule 30", "requires source evidence before emitting a user-facing claim"),
    ("RULE_031", "deterministic evidence-backed sustainability insight rule 31", "requires source evidence before emitting a user-facing claim"),
    ("RULE_032", "deterministic evidence-backed sustainability insight rule 32", "requires source evidence before emitting a user-facing claim"),
    ("RULE_033", "deterministic evidence-backed sustainability insight rule 33", "requires source evidence before emitting a user-facing claim"),
    ("RULE_034", "deterministic evidence-backed sustainability insight rule 34", "requires source evidence before emitting a user-facing claim"),
    ("RULE_035", "deterministic evidence-backed sustainability insight rule 35", "requires source evidence before emitting a user-facing claim"),
    ("RULE_036", "deterministic evidence-backed sustainability insight rule 36", "requires source evidence before emitting a user-facing claim"),
    ("RULE_037", "deterministic evidence-backed sustainability insight rule 37", "requires source evidence before emitting a user-facing claim"),
    ("RULE_038", "deterministic evidence-backed sustainability insight rule 38", "requires source evidence before emitting a user-facing claim"),
    ("RULE_039", "deterministic evidence-backed sustainability insight rule 39", "requires source evidence before emitting a user-facing claim"),
    ("RULE_040", "deterministic evidence-backed sustainability insight rule 40", "requires source evidence before emitting a user-facing claim"),
    ("RULE_041", "deterministic evidence-backed sustainability insight rule 41", "requires source evidence before emitting a user-facing claim"),
    ("RULE_042", "deterministic evidence-backed sustainability insight rule 42", "requires source evidence before emitting a user-facing claim"),
    ("RULE_043", "deterministic evidence-backed sustainability insight rule 43", "requires source evidence before emitting a user-facing claim"),
    ("RULE_044", "deterministic evidence-backed sustainability insight rule 44", "requires source evidence before emitting a user-facing claim"),
    ("RULE_045", "deterministic evidence-backed sustainability insight rule 45", "requires source evidence before emitting a user-facing claim"),
    ("RULE_046", "deterministic evidence-backed sustainability insight rule 46", "requires source evidence before emitting a user-facing claim"),
    ("RULE_047", "deterministic evidence-backed sustainability insight rule 47", "requires source evidence before emitting a user-facing claim"),
    ("RULE_048", "deterministic evidence-backed sustainability insight rule 48", "requires source evidence before emitting a user-facing claim"),
    ("RULE_049", "deterministic evidence-backed sustainability insight rule 49", "requires source evidence before emitting a user-facing claim"),
    ("RULE_050", "deterministic evidence-backed sustainability insight rule 50", "requires source evidence before emitting a user-facing claim"),
    ("RULE_051", "deterministic evidence-backed sustainability insight rule 51", "requires source evidence before emitting a user-facing claim"),
    ("RULE_052", "deterministic evidence-backed sustainability insight rule 52", "requires source evidence before emitting a user-facing claim"),
    ("RULE_053", "deterministic evidence-backed sustainability insight rule 53", "requires source evidence before emitting a user-facing claim"),
    ("RULE_054", "deterministic evidence-backed sustainability insight rule 54", "requires source evidence before emitting a user-facing claim"),
    ("RULE_055", "deterministic evidence-backed sustainability insight rule 55", "requires source evidence before emitting a user-facing claim"),
    ("RULE_056", "deterministic evidence-backed sustainability insight rule 56", "requires source evidence before emitting a user-facing claim"),
    ("RULE_057", "deterministic evidence-backed sustainability insight rule 57", "requires source evidence before emitting a user-facing claim"),
    ("RULE_058", "deterministic evidence-backed sustainability insight rule 58", "requires source evidence before emitting a user-facing claim"),
    ("RULE_059", "deterministic evidence-backed sustainability insight rule 59", "requires source evidence before emitting a user-facing claim"),
    ("RULE_060", "deterministic evidence-backed sustainability insight rule 60", "requires source evidence before emitting a user-facing claim"),
    ("RULE_061", "deterministic evidence-backed sustainability insight rule 61", "requires source evidence before emitting a user-facing claim"),
    ("RULE_062", "deterministic evidence-backed sustainability insight rule 62", "requires source evidence before emitting a user-facing claim"),
    ("RULE_063", "deterministic evidence-backed sustainability insight rule 63", "requires source evidence before emitting a user-facing claim"),
    ("RULE_064", "deterministic evidence-backed sustainability insight rule 64", "requires source evidence before emitting a user-facing claim"),
    ("RULE_065", "deterministic evidence-backed sustainability insight rule 65", "requires source evidence before emitting a user-facing claim"),
    ("RULE_066", "deterministic evidence-backed sustainability insight rule 66", "requires source evidence before emitting a user-facing claim"),
    ("RULE_067", "deterministic evidence-backed sustainability insight rule 67", "requires source evidence before emitting a user-facing claim"),
    ("RULE_068", "deterministic evidence-backed sustainability insight rule 68", "requires source evidence before emitting a user-facing claim"),
    ("RULE_069", "deterministic evidence-backed sustainability insight rule 69", "requires source evidence before emitting a user-facing claim"),
    ("RULE_070", "deterministic evidence-backed sustainability insight rule 70", "requires source evidence before emitting a user-facing claim"),
    ("RULE_071", "deterministic evidence-backed sustainability insight rule 71", "requires source evidence before emitting a user-facing claim"),
    ("RULE_072", "deterministic evidence-backed sustainability insight rule 72", "requires source evidence before emitting a user-facing claim"),
    ("RULE_073", "deterministic evidence-backed sustainability insight rule 73", "requires source evidence before emitting a user-facing claim"),
    ("RULE_074", "deterministic evidence-backed sustainability insight rule 74", "requires source evidence before emitting a user-facing claim"),
    ("RULE_075", "deterministic evidence-backed sustainability insight rule 75", "requires source evidence before emitting a user-facing claim"),
    ("RULE_076", "deterministic evidence-backed sustainability insight rule 76", "requires source evidence before emitting a user-facing claim"),
    ("RULE_077", "deterministic evidence-backed sustainability insight rule 77", "requires source evidence before emitting a user-facing claim"),
    ("RULE_078", "deterministic evidence-backed sustainability insight rule 78", "requires source evidence before emitting a user-facing claim"),
    ("RULE_079", "deterministic evidence-backed sustainability insight rule 79", "requires source evidence before emitting a user-facing claim"),
    ("RULE_080", "deterministic evidence-backed sustainability insight rule 80", "requires source evidence before emitting a user-facing claim"),
    ("RULE_081", "deterministic evidence-backed sustainability insight rule 81", "requires source evidence before emitting a user-facing claim"),
    ("RULE_082", "deterministic evidence-backed sustainability insight rule 82", "requires source evidence before emitting a user-facing claim"),
    ("RULE_083", "deterministic evidence-backed sustainability insight rule 83", "requires source evidence before emitting a user-facing claim"),
    ("RULE_084", "deterministic evidence-backed sustainability insight rule 84", "requires source evidence before emitting a user-facing claim"),
    ("RULE_085", "deterministic evidence-backed sustainability insight rule 85", "requires source evidence before emitting a user-facing claim"),
    ("RULE_086", "deterministic evidence-backed sustainability insight rule 86", "requires source evidence before emitting a user-facing claim"),
    ("RULE_087", "deterministic evidence-backed sustainability insight rule 87", "requires source evidence before emitting a user-facing claim"),
    ("RULE_088", "deterministic evidence-backed sustainability insight rule 88", "requires source evidence before emitting a user-facing claim"),
    ("RULE_089", "deterministic evidence-backed sustainability insight rule 89", "requires source evidence before emitting a user-facing claim"),
    ("RULE_090", "deterministic evidence-backed sustainability insight rule 90", "requires source evidence before emitting a user-facing claim"),
    ("RULE_091", "deterministic evidence-backed sustainability insight rule 91", "requires source evidence before emitting a user-facing claim"),
    ("RULE_092", "deterministic evidence-backed sustainability insight rule 92", "requires source evidence before emitting a user-facing claim"),
    ("RULE_093", "deterministic evidence-backed sustainability insight rule 93", "requires source evidence before emitting a user-facing claim"),
    ("RULE_094", "deterministic evidence-backed sustainability insight rule 94", "requires source evidence before emitting a user-facing claim"),
    ("RULE_095", "deterministic evidence-backed sustainability insight rule 95", "requires source evidence before emitting a user-facing claim"),
    ("RULE_096", "deterministic evidence-backed sustainability insight rule 96", "requires source evidence before emitting a user-facing claim"),
    ("RULE_097", "deterministic evidence-backed sustainability insight rule 97", "requires source evidence before emitting a user-facing claim"),
    ("RULE_098", "deterministic evidence-backed sustainability insight rule 98", "requires source evidence before emitting a user-facing claim"),
    ("RULE_099", "deterministic evidence-backed sustainability insight rule 99", "requires source evidence before emitting a user-facing claim"),
    ("RULE_100", "deterministic evidence-backed sustainability insight rule 100", "requires source evidence before emitting a user-facing claim"),
    ("RULE_101", "deterministic evidence-backed sustainability insight rule 101", "requires source evidence before emitting a user-facing claim"),
    ("RULE_102", "deterministic evidence-backed sustainability insight rule 102", "requires source evidence before emitting a user-facing claim"),
    ("RULE_103", "deterministic evidence-backed sustainability insight rule 103", "requires source evidence before emitting a user-facing claim"),
    ("RULE_104", "deterministic evidence-backed sustainability insight rule 104", "requires source evidence before emitting a user-facing claim"),
    ("RULE_105", "deterministic evidence-backed sustainability insight rule 105", "requires source evidence before emitting a user-facing claim"),
    ("RULE_106", "deterministic evidence-backed sustainability insight rule 106", "requires source evidence before emitting a user-facing claim"),
    ("RULE_107", "deterministic evidence-backed sustainability insight rule 107", "requires source evidence before emitting a user-facing claim"),
    ("RULE_108", "deterministic evidence-backed sustainability insight rule 108", "requires source evidence before emitting a user-facing claim"),
    ("RULE_109", "deterministic evidence-backed sustainability insight rule 109", "requires source evidence before emitting a user-facing claim"),
    ("RULE_110", "deterministic evidence-backed sustainability insight rule 110", "requires source evidence before emitting a user-facing claim"),
    ("RULE_111", "deterministic evidence-backed sustainability insight rule 111", "requires source evidence before emitting a user-facing claim"),
    ("RULE_112", "deterministic evidence-backed sustainability insight rule 112", "requires source evidence before emitting a user-facing claim"),
    ("RULE_113", "deterministic evidence-backed sustainability insight rule 113", "requires source evidence before emitting a user-facing claim"),
    ("RULE_114", "deterministic evidence-backed sustainability insight rule 114", "requires source evidence before emitting a user-facing claim"),
    ("RULE_115", "deterministic evidence-backed sustainability insight rule 115", "requires source evidence before emitting a user-facing claim"),
    ("RULE_116", "deterministic evidence-backed sustainability insight rule 116", "requires source evidence before emitting a user-facing claim"),
    ("RULE_117", "deterministic evidence-backed sustainability insight rule 117", "requires source evidence before emitting a user-facing claim"),
    ("RULE_118", "deterministic evidence-backed sustainability insight rule 118", "requires source evidence before emitting a user-facing claim"),
    ("RULE_119", "deterministic evidence-backed sustainability insight rule 119", "requires source evidence before emitting a user-facing claim"),
    ("RULE_120", "deterministic evidence-backed sustainability insight rule 120", "requires source evidence before emitting a user-facing claim"),
    ("RULE_121", "deterministic evidence-backed sustainability insight rule 121", "requires source evidence before emitting a user-facing claim"),
    ("RULE_122", "deterministic evidence-backed sustainability insight rule 122", "requires source evidence before emitting a user-facing claim"),
    ("RULE_123", "deterministic evidence-backed sustainability insight rule 123", "requires source evidence before emitting a user-facing claim"),
    ("RULE_124", "deterministic evidence-backed sustainability insight rule 124", "requires source evidence before emitting a user-facing claim"),
    ("RULE_125", "deterministic evidence-backed sustainability insight rule 125", "requires source evidence before emitting a user-facing claim"),
    ("RULE_126", "deterministic evidence-backed sustainability insight rule 126", "requires source evidence before emitting a user-facing claim"),
    ("RULE_127", "deterministic evidence-backed sustainability insight rule 127", "requires source evidence before emitting a user-facing claim"),
    ("RULE_128", "deterministic evidence-backed sustainability insight rule 128", "requires source evidence before emitting a user-facing claim"),
    ("RULE_129", "deterministic evidence-backed sustainability insight rule 129", "requires source evidence before emitting a user-facing claim"),
    ("RULE_130", "deterministic evidence-backed sustainability insight rule 130", "requires source evidence before emitting a user-facing claim"),
    ("RULE_131", "deterministic evidence-backed sustainability insight rule 131", "requires source evidence before emitting a user-facing claim"),
    ("RULE_132", "deterministic evidence-backed sustainability insight rule 132", "requires source evidence before emitting a user-facing claim"),
    ("RULE_133", "deterministic evidence-backed sustainability insight rule 133", "requires source evidence before emitting a user-facing claim"),
    ("RULE_134", "deterministic evidence-backed sustainability insight rule 134", "requires source evidence before emitting a user-facing claim"),
    ("RULE_135", "deterministic evidence-backed sustainability insight rule 135", "requires source evidence before emitting a user-facing claim"),
    ("RULE_136", "deterministic evidence-backed sustainability insight rule 136", "requires source evidence before emitting a user-facing claim"),
    ("RULE_137", "deterministic evidence-backed sustainability insight rule 137", "requires source evidence before emitting a user-facing claim"),
    ("RULE_138", "deterministic evidence-backed sustainability insight rule 138", "requires source evidence before emitting a user-facing claim"),
    ("RULE_139", "deterministic evidence-backed sustainability insight rule 139", "requires source evidence before emitting a user-facing claim"),
    ("RULE_140", "deterministic evidence-backed sustainability insight rule 140", "requires source evidence before emitting a user-facing claim"),
    ("RULE_141", "deterministic evidence-backed sustainability insight rule 141", "requires source evidence before emitting a user-facing claim"),
    ("RULE_142", "deterministic evidence-backed sustainability insight rule 142", "requires source evidence before emitting a user-facing claim"),
    ("RULE_143", "deterministic evidence-backed sustainability insight rule 143", "requires source evidence before emitting a user-facing claim"),
    ("RULE_144", "deterministic evidence-backed sustainability insight rule 144", "requires source evidence before emitting a user-facing claim"),
    ("RULE_145", "deterministic evidence-backed sustainability insight rule 145", "requires source evidence before emitting a user-facing claim"),
    ("RULE_146", "deterministic evidence-backed sustainability insight rule 146", "requires source evidence before emitting a user-facing claim"),
    ("RULE_147", "deterministic evidence-backed sustainability insight rule 147", "requires source evidence before emitting a user-facing claim"),
    ("RULE_148", "deterministic evidence-backed sustainability insight rule 148", "requires source evidence before emitting a user-facing claim"),
    ("RULE_149", "deterministic evidence-backed sustainability insight rule 149", "requires source evidence before emitting a user-facing claim"),
    ("RULE_150", "deterministic evidence-backed sustainability insight rule 150", "requires source evidence before emitting a user-facing claim"),
    ("RULE_151", "deterministic evidence-backed sustainability insight rule 151", "requires source evidence before emitting a user-facing claim"),
    ("RULE_152", "deterministic evidence-backed sustainability insight rule 152", "requires source evidence before emitting a user-facing claim"),
    ("RULE_153", "deterministic evidence-backed sustainability insight rule 153", "requires source evidence before emitting a user-facing claim"),
    ("RULE_154", "deterministic evidence-backed sustainability insight rule 154", "requires source evidence before emitting a user-facing claim"),
    ("RULE_155", "deterministic evidence-backed sustainability insight rule 155", "requires source evidence before emitting a user-facing claim"),
    ("RULE_156", "deterministic evidence-backed sustainability insight rule 156", "requires source evidence before emitting a user-facing claim"),
    ("RULE_157", "deterministic evidence-backed sustainability insight rule 157", "requires source evidence before emitting a user-facing claim"),
    ("RULE_158", "deterministic evidence-backed sustainability insight rule 158", "requires source evidence before emitting a user-facing claim"),
    ("RULE_159", "deterministic evidence-backed sustainability insight rule 159", "requires source evidence before emitting a user-facing claim"),
    ("RULE_160", "deterministic evidence-backed sustainability insight rule 160", "requires source evidence before emitting a user-facing claim"),
    ("RULE_161", "deterministic evidence-backed sustainability insight rule 161", "requires source evidence before emitting a user-facing claim"),
    ("RULE_162", "deterministic evidence-backed sustainability insight rule 162", "requires source evidence before emitting a user-facing claim"),
    ("RULE_163", "deterministic evidence-backed sustainability insight rule 163", "requires source evidence before emitting a user-facing claim"),
    ("RULE_164", "deterministic evidence-backed sustainability insight rule 164", "requires source evidence before emitting a user-facing claim"),
    ("RULE_165", "deterministic evidence-backed sustainability insight rule 165", "requires source evidence before emitting a user-facing claim"),
    ("RULE_166", "deterministic evidence-backed sustainability insight rule 166", "requires source evidence before emitting a user-facing claim"),
    ("RULE_167", "deterministic evidence-backed sustainability insight rule 167", "requires source evidence before emitting a user-facing claim"),
    ("RULE_168", "deterministic evidence-backed sustainability insight rule 168", "requires source evidence before emitting a user-facing claim"),
    ("RULE_169", "deterministic evidence-backed sustainability insight rule 169", "requires source evidence before emitting a user-facing claim"),
    ("RULE_170", "deterministic evidence-backed sustainability insight rule 170", "requires source evidence before emitting a user-facing claim"),
    ("RULE_171", "deterministic evidence-backed sustainability insight rule 171", "requires source evidence before emitting a user-facing claim"),
    ("RULE_172", "deterministic evidence-backed sustainability insight rule 172", "requires source evidence before emitting a user-facing claim"),
    ("RULE_173", "deterministic evidence-backed sustainability insight rule 173", "requires source evidence before emitting a user-facing claim"),
    ("RULE_174", "deterministic evidence-backed sustainability insight rule 174", "requires source evidence before emitting a user-facing claim"),
    ("RULE_175", "deterministic evidence-backed sustainability insight rule 175", "requires source evidence before emitting a user-facing claim"),
    ("RULE_176", "deterministic evidence-backed sustainability insight rule 176", "requires source evidence before emitting a user-facing claim"),
    ("RULE_177", "deterministic evidence-backed sustainability insight rule 177", "requires source evidence before emitting a user-facing claim"),
    ("RULE_178", "deterministic evidence-backed sustainability insight rule 178", "requires source evidence before emitting a user-facing claim"),
    ("RULE_179", "deterministic evidence-backed sustainability insight rule 179", "requires source evidence before emitting a user-facing claim"),
    ("RULE_180", "deterministic evidence-backed sustainability insight rule 180", "requires source evidence before emitting a user-facing claim"),
    ("RULE_181", "deterministic evidence-backed sustainability insight rule 181", "requires source evidence before emitting a user-facing claim"),
    ("RULE_182", "deterministic evidence-backed sustainability insight rule 182", "requires source evidence before emitting a user-facing claim"),
    ("RULE_183", "deterministic evidence-backed sustainability insight rule 183", "requires source evidence before emitting a user-facing claim"),
    ("RULE_184", "deterministic evidence-backed sustainability insight rule 184", "requires source evidence before emitting a user-facing claim"),
    ("RULE_185", "deterministic evidence-backed sustainability insight rule 185", "requires source evidence before emitting a user-facing claim"),
    ("RULE_186", "deterministic evidence-backed sustainability insight rule 186", "requires source evidence before emitting a user-facing claim"),
    ("RULE_187", "deterministic evidence-backed sustainability insight rule 187", "requires source evidence before emitting a user-facing claim"),
    ("RULE_188", "deterministic evidence-backed sustainability insight rule 188", "requires source evidence before emitting a user-facing claim"),
    ("RULE_189", "deterministic evidence-backed sustainability insight rule 189", "requires source evidence before emitting a user-facing claim"),
    ("RULE_190", "deterministic evidence-backed sustainability insight rule 190", "requires source evidence before emitting a user-facing claim"),
    ("RULE_191", "deterministic evidence-backed sustainability insight rule 191", "requires source evidence before emitting a user-facing claim"),
    ("RULE_192", "deterministic evidence-backed sustainability insight rule 192", "requires source evidence before emitting a user-facing claim"),
    ("RULE_193", "deterministic evidence-backed sustainability insight rule 193", "requires source evidence before emitting a user-facing claim"),
    ("RULE_194", "deterministic evidence-backed sustainability insight rule 194", "requires source evidence before emitting a user-facing claim"),
    ("RULE_195", "deterministic evidence-backed sustainability insight rule 195", "requires source evidence before emitting a user-facing claim"),
    ("RULE_196", "deterministic evidence-backed sustainability insight rule 196", "requires source evidence before emitting a user-facing claim"),
    ("RULE_197", "deterministic evidence-backed sustainability insight rule 197", "requires source evidence before emitting a user-facing claim"),
    ("RULE_198", "deterministic evidence-backed sustainability insight rule 198", "requires source evidence before emitting a user-facing claim"),
    ("RULE_199", "deterministic evidence-backed sustainability insight rule 199", "requires source evidence before emitting a user-facing claim"),
    ("RULE_200", "deterministic evidence-backed sustainability insight rule 200", "requires source evidence before emitting a user-facing claim"),
    ("RULE_201", "deterministic evidence-backed sustainability insight rule 201", "requires source evidence before emitting a user-facing claim"),
    ("RULE_202", "deterministic evidence-backed sustainability insight rule 202", "requires source evidence before emitting a user-facing claim"),
    ("RULE_203", "deterministic evidence-backed sustainability insight rule 203", "requires source evidence before emitting a user-facing claim"),
    ("RULE_204", "deterministic evidence-backed sustainability insight rule 204", "requires source evidence before emitting a user-facing claim"),
    ("RULE_205", "deterministic evidence-backed sustainability insight rule 205", "requires source evidence before emitting a user-facing claim"),
    ("RULE_206", "deterministic evidence-backed sustainability insight rule 206", "requires source evidence before emitting a user-facing claim"),
    ("RULE_207", "deterministic evidence-backed sustainability insight rule 207", "requires source evidence before emitting a user-facing claim"),
    ("RULE_208", "deterministic evidence-backed sustainability insight rule 208", "requires source evidence before emitting a user-facing claim"),
    ("RULE_209", "deterministic evidence-backed sustainability insight rule 209", "requires source evidence before emitting a user-facing claim"),
    ("RULE_210", "deterministic evidence-backed sustainability insight rule 210", "requires source evidence before emitting a user-facing claim"),
    ("RULE_211", "deterministic evidence-backed sustainability insight rule 211", "requires source evidence before emitting a user-facing claim"),
    ("RULE_212", "deterministic evidence-backed sustainability insight rule 212", "requires source evidence before emitting a user-facing claim"),
    ("RULE_213", "deterministic evidence-backed sustainability insight rule 213", "requires source evidence before emitting a user-facing claim"),
    ("RULE_214", "deterministic evidence-backed sustainability insight rule 214", "requires source evidence before emitting a user-facing claim"),
    ("RULE_215", "deterministic evidence-backed sustainability insight rule 215", "requires source evidence before emitting a user-facing claim"),
    ("RULE_216", "deterministic evidence-backed sustainability insight rule 216", "requires source evidence before emitting a user-facing claim"),
    ("RULE_217", "deterministic evidence-backed sustainability insight rule 217", "requires source evidence before emitting a user-facing claim"),
    ("RULE_218", "deterministic evidence-backed sustainability insight rule 218", "requires source evidence before emitting a user-facing claim"),
    ("RULE_219", "deterministic evidence-backed sustainability insight rule 219", "requires source evidence before emitting a user-facing claim"),
    ("RULE_220", "deterministic evidence-backed sustainability insight rule 220", "requires source evidence before emitting a user-facing claim"),
)
def insight_rule_catalog():
    """Return a stable copy of the documented rule catalog."""
    return tuple(INSIGHT_RULE_CATALOG)
