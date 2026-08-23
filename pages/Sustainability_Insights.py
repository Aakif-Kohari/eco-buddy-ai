"""Streamlit dashboard for Sustainability Insights."""
from datetime import datetime,timezone
import streamlit as st
from database import get_assessments
from sustainability_insights import *
try:
 from recommendations import generate_recommendations
except Exception:generate_recommendations=None
st.set_page_config(page_title="Sustainability Insights",page_icon="💡",layout="wide")
st.title("💡 Sustainability Insights")
st.caption("Deterministic, evidence-backed progress summaries. Unsupported claims are not fabricated.")
uid=st.session_state.get("user_id",1)
try:raw=get_assessments(uid)
except Exception as exc:st.error(f"Unable to load assessment history: {exc}");raw=[]
goals=st.session_state.get("sustainability_goals",[]);habits=st.session_state.get("sustainability_habits",[]);recs=st.session_state.get("sustainability_recommendations",[])
with st.sidebar:
 st.header("Settings");it=st.slider("Improvement threshold (%)",0.,50.,5.,.5);dt=st.slider("Decline threshold (%)",0.,50.,5.,.5);stale=st.number_input("Stale after (days)",7,3650,90);limit=st.slider("Maximum insights",4,30,12)
ctx=build_insight_context(raw,goals,habits,recs,now=datetime.now(timezone.utc),improvement_threshold_pct=it,decline_threshold_pct=dt,stale_days=int(stale))
items=generate_insights(ctx,limit=limit);weekly=build_weekly_summary(ctx);monthly=build_monthly_summary(ctx)
if not raw:st.warning("No valid assessment history is available. Complete an assessment to unlock insights.")
a,b,c,d=st.columns(4);a.metric("Insights",len(items));b.metric("High priority",sum(x.priority==InsightPriority.HIGH for x in items));c.metric("Improvements",sum(x.type in {InsightType.IMPROVEMENT,InsightType.CATEGORY_IMPROVEMENT} for x in items));d.metric("Declines",sum(x.type in {InsightType.DECLINE,InsightType.CATEGORY_DECLINE} for x in items))
st.subheader("Weekly summary");st.info(weekly.headline)
if weekly.next_step:st.write("**Suggested next step:** "+weekly.next_step)
t1,t2,t3=st.tabs(["Insights","Weekly digest","Monthly digest"])
with t1:
 for x in items:
  with st.expander(f"{x.priority.value} · {x.title}"):
   st.write(x.description);st.write(f"**Source:** `{x.source}`");st.json(x.evidence)
   if x.action:st.success("Next step: "+x.action)
with t2:
 st.json(weekly.to_dict());st.download_button("Download weekly JSON",serialize_summary(weekly),"sustainability-weekly-summary.json","application/json");st.download_button("Download weekly Markdown",summary_to_markdown(weekly),"sustainability-weekly-summary.md","text/markdown")
with t3:
 st.json(monthly.to_dict());st.download_button("Download monthly JSON",serialize_summary(monthly),"sustainability-monthly-summary.json","application/json");st.download_button("Download all insights JSON",serialize_insights(items),"sustainability-insights.json","application/json")
