import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from eco_credits_ledger import mint_credits, get_balance, transfer_credits
from database_connection import database_connection
import os
import time
import json
from auth import get_current_user

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

st.set_page_config(page_title="Eco-Credits Trading", page_icon="💹", layout="wide")

st.title("💹 Eco-Credits Trading Terminal")
st.markdown("Mint your verified sustainability surplus into Eco-Credits and trade them on the open market or donate them to community projects.")

# Mock user for development
user = get_current_user()
if not user:
    # Fallback for testing if no auth context
    user = {"username": "test_user_1"}

user_id = user["username"]

# Fetch balance
balance = get_balance(user_id)
st.sidebar.metric("Your Eco-Credits Balance", f"{balance:.2f} 🌱")

tab1, tab2, tab3 = st.tabs(["Trading Terminal", "Mint Credits", "Community Donations"])

with tab1:
    st.header("Order Book & Trading")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Mock Candlestick Chart for Eco-Credits
        # In a real app, this would be generated from eco_ledger_transactions and eco_order_book
        st.subheader("Market Price (EC/USD)")
        
        # Generate some mock data for the chart
        df = pd.DataFrame({
            'Date': pd.date_range(start='2026-08-01', periods=25),
            'Open': [10, 10.5, 11, 10.8, 11.2, 11.5, 12, 11.8, 12.2, 12.5, 13, 12.8, 13.5, 13.2, 14, 13.8, 14.5, 14.2, 15, 14.8, 15.5, 15.2, 16, 15.8, 16.5],
            'High': [11, 11.5, 12, 11.8, 12.2, 12.5, 13, 12.8, 13.2, 13.5, 14, 13.8, 14.5, 14.2, 15, 14.8, 15.5, 15.2, 16, 15.8, 16.5, 16.2, 17, 16.8, 17.5],
            'Low': [9, 9.5, 10, 9.8, 10.2, 10.5, 11, 10.8, 11.2, 11.5, 12, 11.8, 12.5, 12.2, 13, 12.8, 13.5, 13.2, 14, 13.8, 14.5, 14.2, 15, 14.8, 15.5],
            'Close': [10.5, 11, 10.8, 11.2, 11.5, 12, 11.8, 12.2, 12.5, 13, 12.8, 13.5, 13.2, 14, 13.8, 14.5, 14.2, 15, 14.8, 15.5, 15.2, 16, 15.8, 16.5, 16.2]
        })
        
        fig = go.Figure(data=[go.Candlestick(x=df['Date'],
                        open=df['Open'],
                        high=df['High'],
                        low=df['Low'],
                        close=df['Close'])])
        
        fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Place Order")
        order_type = st.radio("Order Type", ["Buy", "Sell"], horizontal=True)
        amount = st.number_input("Amount (Credits)", min_value=0.1, step=0.1)
        price = st.number_input("Limit Price (USD)", min_value=0.1, step=0.1)
        
        if st.button("Submit Order"):
            # Mocking order placement
            if order_type == "Sell" and balance < amount:
                st.error("Insufficient balance to sell.")
            else:
                with database_connection(DB_NAME) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO eco_order_book (user_id, order_type, amount, price)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, order_type, amount, price))
                    conn.commit()
                st.success("Order placed successfully!")
                time.sleep(1)
                st.rerun()

        st.subheader("Live Order Book")
        # Fetching order book
        with database_connection(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT order_type, amount, price FROM eco_order_book WHERE status='OPEN' ORDER BY price DESC LIMIT 10")
            orders = cursor.fetchall()
            
            if orders:
                st.dataframe(pd.DataFrame(orders, columns=["Type", "Amount", "Price"]))
            else:
                st.info("No active orders.")

with tab2:
    st.header("Mint Credits")
    st.markdown("Upload verifiable data (like a utility bill showing solar surplus) to mint new Eco-Credits.")
    
    uploaded_file = st.file_uploader("Upload Utility Bill (PDF, JPG, PNG)", type=["pdf", "jpg", "png"])
    
    if uploaded_file is not None:
        st.success(f"File {uploaded_file.name} uploaded successfully.")
        
        if st.button("Verify and Mint"):
            with st.spinner("Analyzing document with OCR and verifying surplus..."):
                time.sleep(2) # Simulating OCR processing
                
                # In reality, this would use ocr_utils to parse the bill and determine surplus
                mock_surplus = 50.0 
                
                proof = {
                    "filename": uploaded_file.name,
                    "verified_surplus_kwh": mock_surplus,
                    "verification_timestamp": time.time()
                }
                
                success = mint_credits(user_id, mock_surplus, proof)
                if success:
                    st.balloons()
                    st.success(f"Successfully minted {mock_surplus} Eco-Credits!")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Failed to mint credits. Please check the logs.")

with tab3:
    st.header("Community Donations")
    st.markdown("Donate your surplus Eco-Credits to fund local sustainability projects.")
    
    # Initialize some mock funds if empty
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM eco_community_funds")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO eco_community_funds (project_name, target_amount, description) VALUES ('Community Solar Garden', 5000, 'Funding a solar array for the local community center.')")
            cursor.execute("INSERT INTO eco_community_funds (project_name, target_amount, description) VALUES ('Urban Reforestation', 2000, 'Planting 100 trees in downtown areas.')")
            conn.commit()
            
        cursor.execute("SELECT id, project_name, target_amount, current_amount, description FROM eco_community_funds")
        funds = cursor.fetchall()
    
    for fund in funds:
        fund_id, name, target, current, desc = fund
        with st.container():
            st.subheader(name)
            st.write(desc)
            progress = min(current / target, 1.0)
            st.progress(progress, text=f"{current} / {target} Credits ({progress*100:.1f}%)")
            
            donation_amount = st.number_input("Amount to donate", min_value=1.0, step=1.0, key=f"donate_{fund_id}")
            if st.button("Donate", key=f"btn_{fund_id}"):
                if donation_amount > balance:
                    st.error("Insufficient balance.")
                else:
                    # Transfer credits to 'SYSTEM_FUND' (burning them from user, adding to fund)
                    success = transfer_credits(user_id, "SYSTEM_FUND", donation_amount)
                    if success:
                        with database_connection(DB_NAME) as conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE eco_community_funds SET current_amount = current_amount + ? WHERE id = ?", (donation_amount, fund_id))
                            conn.commit()
                        st.success(f"Thank you for donating {donation_amount} credits to {name}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Donation failed.")
            st.divider()
