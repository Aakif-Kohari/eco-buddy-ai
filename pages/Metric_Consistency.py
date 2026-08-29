"""
Streamlit UI for the Sustainability Metric Consistency Center.

The page is read-only with respect to source sustainability data. It discovers
common SQLite tables, allows manual JSON input, runs the validation engine,
shows module/category health, exposes findings and permits an explicit
immutable validation snapshot.
"""
from __future__ import annotations
import json
import os
import sqlite3
from pathlib import Path
from typing import Any
import streamlit as st
from src.utils.metric_consistency import (
 DB_NAME,MODULES,build_health_summary,export_report,findings_by_severity,
 persist_report,validate_all_modules
)

st.set_page_config(page_title="Metric Consistency Center",page_icon="🔎",layout="wide")
DB_PATH=os.getenv("ECO_BUDDY_DB",DB_NAME)
TABLE_HINTS={
 "assessments":("assessments","assessment_history","assessment"),
 "goals":("goals","sustainability_goals"),
 "recommendations":("recommendations","recommendation_history"),
 "habits":("habits","user_habits"),
 "action_plans":("action_plan_items","action_plans","action_plan"),
 "analytics":("analytics","analytics_snapshots","trend_snapshots"),
}

def safe_json(text:str)->list[dict[str,Any]]:
 if not text.strip():return []
 try:value=json.loads(text)
 except json.JSONDecodeError as e:raise ValueError(f"Invalid JSON: {e}") from e
 if isinstance(value,dict):value=value.get("records",value.get("data",[value]))
 if not isinstance(value,list):raise ValueError("JSON must be a list or an object containing records/data.")
 return [x for x in value if isinstance(x,dict)]

def table_names(conn):
 return [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()]

def discover_table(conn,module):
 names=set(table_names(conn))
 return next((x for x in TABLE_HINTS.get(module,()) if x in names),None)

def read_table(conn,table):
 cols=[r[1] for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()]
 if not cols:return []
 rows=conn.execute(f'SELECT * FROM "{table}" LIMIT 1000').fetchall()
 return [dict(zip(cols,row)) for row in rows]

def discover_database_data(path):
 data={m:[] for m in MODULES};tables={m:None for m in MODULES}
 if not Path(path).exists():return data,tables
 try:
  conn=sqlite3.connect(path)
  try:
   for module in MODULES:
    table=discover_table(conn,module);tables[module]=table
    if table:data[module]=read_table(conn,table)
  finally:conn.close()
 except sqlite3.Error:return data,tables
 return data,tables

def render_manual(module,initial):
 key=f"metric_json_{module}"
 text=st.text_area(f"{module.replace('_',' ').title()} JSON",
                   value=st.session_state.get(key,json.dumps(initial[:25],indent=2,default=str)),
                   height=160,key=key)
 try:return safe_json(text)
 except ValueError as e:
  st.error(str(e));return []

st.title("🔎 Sustainability Metric Consistency Center")
st.caption("Read-only cross-module validation for EcoBuddy sustainability metrics.")

with st.sidebar:
 st.header("Settings")
 db_path=st.text_input("SQLite database",value=DB_PATH)
 tolerance=st.slider("Cross-module value tolerance (%)",0.0,25.0,5.0,0.5)
 user_id=st.text_input("User ID (optional)")
 use_db=st.checkbox("Load discoverable SQLite tables",True)
 persist=st.checkbox("Enable snapshot persistence",False)

if use_db:data,tables=discover_database_data(db_path)
else:data={m:[] for m in MODULES};tables={m:None for m in MODULES}

st.subheader("Detected module sources")
cols=st.columns(3)
for i,module in enumerate(MODULES):
 with cols[i%3]:
  table=tables[module];count=len(data[module])
  if table:st.success(f"**{module.replace('_',' ').title()}**\n\n`{table}` · {count} rows")
  else:st.info(f"**{module.replace('_',' ').title()}**\n\nNo known table")

with st.expander("Manual JSON overrides",expanded=False):
 st.write("Paste JSON for a module when its database table is unavailable or you want to validate a fixture.")
 manual={}
 for module in MODULES:manual[module]=render_manual(module,data[module])
 if st.button("Apply non-empty manual modules"):
  for module in MODULES:
   if manual[module]:data[module]=manual[module]
  st.session_state["metric_manual_data"]=data
  st.rerun()

if "metric_manual_data" in st.session_state:data=st.session_state["metric_manual_data"]

if st.button("Run consistency validation",type="primary",use_container_width=True):
 with st.spinner("Checking metric consistency across modules..."):
  report=validate_all_modules(data,user_id=user_id.strip() or None,tolerance=tolerance/100)
 st.session_state["metric_consistency_report"]=report

report=st.session_state.get("metric_consistency_report")
if report is None:
 st.info("Click **Run consistency validation** to generate the first src.reporting.report.")
 st.stop()

health=build_health_summary(report)
if health["status"]=="CONSISTENT":st.success(f"All checked metrics are consistent. Score {health['score']:.1f}/100.")
elif health["status"]=="REVIEW":st.warning(f"Review recommended. Score {health['score']:.1f}/100.")
elif health["status"]=="INCONSISTENT":st.error(f"Cross-module inconsistencies detected. Score {health['score']:.1f}/100.")
else:st.info("Not enough data for a meaningful cross-module consistency result.")

cards=st.columns(5)
cards[0].metric("Score",f"{health['score']:.1f}")
cards[1].metric("Findings",health["finding_count"])
cards[2].metric("Errors",health["severity"]["error"])
cards[3].metric("Warnings",health["severity"]["warning"])
cards[4].metric("Info",health["severity"]["info"])

st.subheader("Module health")
st.dataframe([{
 "Module":m.replace("_"," ").title(),"Status":r.status,"Records":r.record_count,
 "Valid metrics":r.valid_metric_count,"Invalid metrics":r.invalid_metric_count,"Findings":len(r.findings)
} for m,r in src.reporting.report.module_results.items()],use_container_width=True,hide_index=True)

st.subheader("Category coverage")
if src.reporting.report.category_summary:st.dataframe(src.reporting.report.category_summary,use_container_width=True,hide_index=True)
else:st.info("No categorized metrics found.")

st.subheader("Findings")
fc=st.columns(4)
with fc[0]:severity=st.selectbox("Severity",["ALL","CRITICAL","ERROR","WARNING","INFO"])
with fc[1]:module=st.selectbox("Module",["ALL",*MODULES,"cross_module","definition"])
with fc[2]:category=st.text_input("Category contains")
with fc[3]:code=st.text_input("Code contains")
findings=src.reporting.report.findings
if severity!="ALL":findings=findings_by_severity(findings,severity)
if module!="ALL":findings=[x for x in findings if x.module==module]
if category.strip():
 n=category.strip().lower();findings=[x for x in findings if n in x.message.lower() or n in " ".join(x.categories).lower()]
if code.strip():
 n=code.strip().lower();findings=[x for x in findings if n in x.code.lower()]
if not findings:st.success("No findings match the filters.")
for i,item in enumerate(findings):
 with st.expander(f"{item.severity} · {item.code} · {item.module}",expanded=i<3):
  st.write(item.message)
  if item.record_ids:st.caption("Records: "+", ".join(item.record_ids))
  if item.categories:st.caption("Categories: "+", ".join(item.categories))
  if item.metrics:st.caption("Metrics: "+", ".join(item.metrics))
  if item.expected is not None:st.write("**Expected:**",item.expected)
  if item.observed is not None:st.write("**Observed:**",item.observed)
  if item.rule:st.write("**Rule:**",item.rule)
  if item.suggested_action:st.write("**Suggested action:**",item.suggested_action)

st.subheader("Cross-module metric matrix")
if src.reporting.report.metric_matrix:
 st.dataframe([{"Category":x["category"],"Metric":x["metric"],"Modules":", ".join(x["modules"]),"Module count":x["module_count"]}
               for x in src.reporting.report.metric_matrix],use_container_width=True,hide_index=True)
else:st.info("No metric identities were found.")

st.download_button("Download validation report (JSON)",export_report(report),
                   "sustainability_metric_consistency_report.json","application/json",use_container_width=True)

if persist and st.button("Save immutable validation snapshot",use_container_width=True):
 try:st.success(f"Saved snapshot #{persist_report(report,db_path=db_path)}.")
 except Exception as e:st.error(f"Could not save snapshot: {e}")

with st.expander("Validation methodology"):
 st.markdown("""
 - Category aliases are normalized to one shared sustainability taxonomy.
 - Compatible units are converted before values are compared.
 - Different physical dimensions are never compared.
 - Historical source records are never silently rewritten or recalculated.
 - Goal/current/assessment mismatches are reported rather than repaired.
 - Recommendations, habits and action-plan items are checked against assessment categories.
 - Analytics are compared to source assessment metrics where a shared identity exists.
 - Missing data is reported as insufficient evidence instead of being guessed.
 - Validation snapshots are stored separately from source sustainability data.
 """)

st.caption("Issue #1169 · additive validation layer · source data is read-only")
