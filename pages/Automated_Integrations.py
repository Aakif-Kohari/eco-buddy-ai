import streamlit as st
import sqlite3
import uuid
import json
from datetime import datetime

from styles.theme import apply_theme
from src.core.database import DB_NAME

st.set_page_config(page_title="Automated Integrations", page_icon="🔗", layout="wide")
apply_theme()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

st.title("🔗 Automated Integrations (Webhooks)")
st.markdown("Connect your smart home, fitness trackers, and automation apps (Zapier, IFTTT) to automatically log EcoBuddy actions.")

# Ensure tables exist just in case (migrations should handle this, but for robustness)
try:
    with get_db() as conn:
        conn.execute("SELECT 1 FROM inbound_webhooks LIMIT 1")
except sqlite3.OperationalError:
    st.error("Webhook tables not found. Please run database migrations.")
    st.stop()

tabs = st.tabs(["🔌 My Webhooks", "➕ Create Webhook", "📜 Event Logs"])

user_id = "default_user" # Mocked user for now

# -----------------
# TAB 1: My Webhooks
# -----------------
with tabs[0]:
    st.subheader("Active Webhooks")
    with get_db() as conn:
        webhooks = conn.execute(
            "SELECT * FROM inbound_webhooks WHERE user_id = ? AND is_active = 1 ORDER BY created_at DESC", 
            (user_id,)
        ).fetchall()
        
    if not webhooks:
        st.info("No active webhooks found. Create one in the next tab!")
    else:
        for wh in webhooks:
            with st.expander(f"**{wh['app_name']}** - {wh['action_template']}"):
                st.code(f"http://localhost:8000/api/v1/webhooks/{wh['secure_token']}", language="text")
                st.markdown("**Mapping Rules:**")
                st.json(json.loads(wh['mapping_rules']) if wh['mapping_rules'] else {})
                
                if st.button("Revoke Webhook", key=f"revoke_{wh['id']}"):
                    with get_db() as conn:
                        conn.execute("UPDATE inbound_webhooks SET is_active = 0 WHERE id = ?", (wh['id'],))
                        conn.commit()
                    st.success("Webhook revoked!")
                    st.rerun()

# -----------------
# TAB 2: Create Webhook
# -----------------
with tabs[1]:
    st.subheader("Generate New Webhook")
    st.markdown("Map incoming JSON payload properties to EcoBuddy data points.")
    
    with st.form("create_webhook_form"):
        app_name = st.text_input("Application Name", placeholder="e.g., Strava via Zapier")
        action_template = st.selectbox("EcoBuddy Action to Log", ["Bike Commute", "Public Transit", "Smart Thermostat Eco-Mode", "Custom Event"])
        
        st.markdown("#### Payload Mapping (JSONPath)")
        st.markdown("Enter the JSON path from your incoming webhook payload to extract values. (e.g. `ride.distance` or `event.data.kwh_saved`)")
        
        map_distance = st.text_input("Distance Mapping (JSONPath)", placeholder="e.g. ride.distance")
        map_duration = st.text_input("Duration Mapping (JSONPath)", placeholder="e.g. ride.moving_time")
        
        submit = st.form_submit_button("Generate Webhook URL")
        
        if submit:
            if not app_name:
                st.error("Please enter an Application Name.")
            else:
                secure_token = "wh_live_" + uuid.uuid4().hex
                wh_id = str(uuid.uuid4())
                
                mapping_rules = {}
                if map_distance:
                    mapping_rules["distance"] = map_distance
                if map_duration:
                    mapping_rules["duration"] = map_duration
                
                with get_db() as conn:
                    conn.execute(
                        "INSERT INTO inbound_webhooks (id, user_id, secure_token, app_name, action_template, mapping_rules) VALUES (?, ?, ?, ?, ?, ?)",
                        (wh_id, user_id, secure_token, app_name, action_template, json.dumps(mapping_rules))
                    )
                    conn.commit()
                st.success("Webhook generated successfully!")
                st.info(f"Your secure URL: `http://localhost:8000/api/v1/webhooks/{secure_token}`")
                st.warning("Save this URL. The token is embedded within it.")

# -----------------
# TAB 3: Event Logs
# -----------------
with tabs[2]:
    st.subheader("Recent Webhook Events")
    
    with get_db() as conn:
        logs = conn.execute(
            """
            SELECT l.created_at, l.status, l.payload, l.error_message, w.app_name 
            FROM webhook_event_logs l
            JOIN inbound_webhooks w ON l.webhook_id = w.id
            WHERE w.user_id = ?
            ORDER BY l.created_at DESC LIMIT 50
            """, (user_id,)
        ).fetchall()
        
    if not logs:
        st.info("No events received yet.")
    else:
        for log in logs:
            status_color = "green" if log["status"] == "SUCCESS" else "red"
            with st.expander(f"{log['created_at']} | {log['app_name']} | :{status_color}[{log['status']}]"):
                if log["error_message"]:
                    st.error(log["error_message"])
                st.markdown("**Raw Payload:**")
                try:
                    st.json(json.loads(log["payload"]))
                except:
                    st.code(log["payload"])
