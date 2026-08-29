import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime, date, timedelta

# Configuration & Page Setup
st.set_page_config(page_title="EcoBuddy AI - Smart Pantry & Food Waste Analyzer", layout="wide")

# Database Initialization
DB_FILE = "pantry.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS pantry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            purchase_date TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            cost REAL NOT NULL,
            is_perishable INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Active' -- Active, Consumed, Wasted
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Database Helper Functions
def get_all_items():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM pantry", conn)
    conn.close()
    if not df.empty:
        df['purchase_date'] = pd.to_datetime(df['purchase_date']).dt.date
        df['expiry_date'] = pd.to_datetime(df['expiry_date']).dt.date
    return df

def add_pantry_item(name, cat, p_date, e_date, item_cost, perishable):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO pantry (item_name, category, purchase_date, expiry_date, cost, is_perishable, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Active')
    ''', (name, cat, p_date.strftime("%Y-%m-%d"), e_date.strftime("%Y-%m-%d"), item_cost, 1 if perishable else 0))
    conn.commit()
    conn.close()

def update_item_status(item_id, new_status):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE pantry SET status = ? WHERE id = ?", (new_status, int(item_id)))
    conn.commit()
    conn.close()

# Spoilage Risk Calculation Engine
def calculate_risk(row):
    if row['status'] != 'Active':
        return 'Logged'
    
    today = date.today()
    days_to_expiry = (row['expiry_date'] - today).days
    
    if days_to_expiry < 0:
        return 'Expired'
    elif days_to_expiry <= 2:
        return 'High Risk'
    elif days_to_expiry <= 5:
        return 'Moderate Risk'
    else:
        return 'Low Risk'

# Application UI Layout
st.title("🍏 EcoBuddy AI: Smart Pantry & Food Waste Analyzer")
st.markdown("An enterprise-grade engine to minimize food waste, track financials, and monitor perishables dynamically.")

# Fetch active dataset
df = get_all_items()

# Sidebar: Actions and Controls
st.sidebar.header("📥 Pantry Operations")
with st.sidebar.form("add_item_form", clear_on_submit=True):
    st.subheader("Add New Food Item")
    item_name = st.text_input("Item Name", placeholder="e.g., Organic Milk")
    category = st.selectbox("Category", ["Dairy & Eggs", "Fruits & Vegetables", "Meat & Seafood", "Bakery", "Grains & Pantry", "Beverages", "Other"])
    purchase_date = st.date_input("Purchase Date", value=date.today())
    expiry_date = st.date_input("Expiration Date", value=date.today() + timedelta(days=7))
    cost = st.number_input("Item Cost (₹ / $)", min_value=0.0, step=0.5, value=1.5)
    is_perishable = st.checkbox("Highly Perishable?", value=True)
    
    submit_button = st.form_submit_button("Log into Pantry")
    if submit_button and item_name:
        add_pantry_item(item_name, category, purchase_date, expiry_date, cost, is_perishable)
        st.sidebar.success(f"Successfully tracked: {item_name}")
        df = get_all_items()  # Refresh dataset

# Process Risk Analytics if data exists
if not df.empty:
    df['Risk_Status'] = df.apply(calculate_risk, axis=1)
    active_df = df[df['status'] == 'Active'].copy()
    
    # Critical Warnings Section for Active Perishables
    urgent_items = active_df[active_df['Risk_Status'].isin(['Expired', 'High Risk'])]
    if not urgent_items.empty:
        st.error("🚨 **Critical Perishable Warnings & Actions Needed:**")
        for _, row in urgent_items.iterrows():
            days_left = (row['expiry_date'] - date.today()).days
            warning_text = f"**{row['item_name']}** ({row['category']}) - "
            if days_left < 0:
                warning_text += f"Expired {-days_left} day(s) ago!"
            else:
                warning_text += f"Expires in {days_left} day(s)!"
            st.warning(warning_text)

    # Metric Row & Financial Insights
    st.subheader("📊 Strategic Metrics & Financial Optimization")
    col1, col2, col3, col4 = st.columns(4)
    
    total_active_cost = active_df['cost'].sum()
    total_wasted_cost = df[df['status'] == 'Wasted']['cost'].sum()
    total_consumed_cost = df[df['status'] == 'Consumed']['cost'].sum()
    
    # Financial Savings Calculation Engine (Targeted 75% mitigation avoidance value)
    potential_savings = total_wasted_cost * 0.75

    col1.metric("Active Portfolio Value", f"${total_active_cost:,.2f}")
    col2.metric("Total Food Wealth Consumed", f"${total_consumed_cost:,.2f}")
    col3.metric("Capital Lost to Waste", f"${total_wasted_cost:,.2f}", delta=f"${total_wasted_cost:,.2f}", delta_color="inverse")
    col4.metric("Potential Target Savings", f"${potential_savings:,.2f}", help="Estimated financial recovery by adopting a 75% waste avoidance strategy.")

    # Main Dashboard Tabs
    tab_pantry, tab_analytics = st.tabs(["🗄️ Pantry Management & Status Triggers", "📈 Spoilage Risk & Activity Analytics"])
    
    with tab_pantry:
        st.subheader("Current Persistent Pantry Inventory")
        if not active_df.empty:
            display_df = active_df[['id', 'item_name', 'category', 'purchase_date', 'expiry_date', 'cost', 'Risk_Status']].copy()
            st.dataframe(display_df, use_container_width=True)
            
            # Status Triggers Area
            st.subheader("🔄 Update Consumption Status Triggers")
            trigger_col1, trigger_col2, trigger_col3 = st.columns([1, 1, 1])
            with trigger_col1:
                selected_item_id = st.selectbox("Select Item to Update", display_df['id'].tolist(), format_func=lambda x: f"ID {x}: {display_df[display_df['id']==x]['item_name'].values[0]}")
            with trigger_col2:
                new_action = st.selectbox("Action State Trigger", ["Consumed", "Wasted"])
            with trigger_col3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Execute Status State Trigger", use_container_width=True):
                    update_item_status(selected_item_id, new_action)
                    st.success(f"Item ID {selected_item_id} transitioned to {new_action}.")
                    st.rerun()
        else:
            st.info("Pantry currently empty or all items have been logged out.")

    with tab_analytics:
        st.subheader("Plotly-Powered Dynamic Waste & Risk Vectors")
        an_col1, an_col2 = st.columns(2)
        
        with an_col1:
            if not active_df.empty:
                risk_counts = active_df['Risk_Status'].value_counts().reset_index()
                risk_counts.columns = ['Risk Level', 'Item Count']
                fig_risk = px.pie(risk_counts, values='Item Count', names='Risk Level', title="Active Inventory Spoilage Risk Distribution",
                                  color='Risk Level', color_discrete_map={'Expired': '#EF553B', 'High Risk': '#FECB52', 'Moderate Risk': '#636EFA', 'Low Risk': '#00CC96'})
                st.plotly_chart(fig_risk, use_container_width=True)
            else:
                st.info("No active risk distributions available.")
                
        with an_col2:
            historical_df = df[df['status'].isin(['Consumed', 'Wasted'])]
            if not historical_df.empty:
                status_summary = historical_df.groupby(['category', 'status'])['cost'].sum().reset_index()
                fig_waste = px.bar(status_summary, x='category', y='cost', color='status', title="Financial Impact: Consumed vs Wasted by Category",
                                   barmode='group', labels={'cost': 'Financial Impact ($)', 'category': 'Food Category'})
                st.plotly_chart(fig_waste, use_container_width=True)
            else:
                st.info("Log dynamic consumption or waste state events to populate historical analytics graphs.")
else:
    st.info("👋 Welcome to EcoBuddy AI! Use the left panel form to log your first food item and initialize the real-time analytics stream.")
