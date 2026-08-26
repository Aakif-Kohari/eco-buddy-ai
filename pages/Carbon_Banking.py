"""
Carbon Banking Dashboard.
Streamlit page featuring a banking dashboard, historical balance charts, and interactive rollover/borrowing simulators.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from carbon_banking_engine import CarbonBankingEngine
from intertemporal_trading import IntertemporalTrading
from database import save_carbon_banking_action, get_carbon_banking_history

st.set_page_config(page_title="Carbon Banking", page_icon="🏦", layout="wide")

st.title("🏦 Dynamic Carbon Budget Rollover & Banking Simulator")
st.markdown(
    "Manage your carbon allowance like a bank account. Roll over unused credits or borrow from the future with realistic decay and interest mechanics."
)

# Initialize session state
if "banking_engine" not in st.session_state:
    st.session_state.banking_engine = CarbonBankingEngine(
        user_id="demo_user", base_monthly_allowance=500.0
    )
    st.session_state.trading = IntertemporalTrading(
        decay_rate_pct=5.0, interest_rate_pct=10.0
    )

    # Setup demo months
    st.session_state.banking_engine.get_account("2023-10")
    st.session_state.banking_engine.get_account("2023-11")
    st.session_state.banking_engine.log_usage("2023-10", 350.0)  # 150 remaining

engine = st.session_state.banking_engine
trading = st.session_state.trading

# --- Dashboard Metrics ---
st.subheader("📊 Current Account Status")
current_month = "2023-10"
next_month = "2023-11"

current_acc = engine.get_account(current_month)
next_acc = engine.get_account(next_month)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Monthly Base Allowance", f"{current_acc['base_allowance']:.0f} kg")
col2.metric("Banked from Previous", f"{current_acc['banked_from_previous']:.0f} kg")
col3.metric("Total Available", f"{current_acc['total_available']:.0f} kg")
col4.metric(
    "Remaining Balance",
    f"{current_acc['remaining']:.0f} kg",
    delta=f"{current_acc['remaining'] - current_acc['base_allowance']:.0f}",
)

# --- Interactive Simulators ---
tab1, tab2 = st.tabs(["🔄 Rollover Simulator", "💸 Borrowing Simulator"])

with tab1:
    st.subheader("Rollover Unused Allowance")
    st.info(
        f"You have **{current_acc['remaining']:.0f} kg** remaining in {current_month}."
    )

    rollover_pct = st.slider("Percentage to roll over to next month", 0, 100, 50)

    if st.button("Simulate Rollover"):
        rolled_amount = engine.rollover_unused_allowance(
            current_month, next_month, rollover_pct
        )

        # Apply decay to show realistic value
        decayed_value = trading.apply_decay_to_banked(rolled_amount, months_held=1)

        st.success(f"Successfully rolled over **{rolled_amount:.0f} kg**.")
        st.warning(
            f"Due to a {trading.decay_rate_pct}% monthly decay rate, its effective value next month will be **{decayed_value:.0f} kg**."
        )

        save_carbon_banking_action(
            "demo_user", "rollover", rolled_amount, current_month, next_month
        )

        # Refresh display
        current_acc = engine.get_account(current_month)
        next_acc = engine.get_account(next_month)
        st.rerun()

with tab2:
    st.subheader("Borrow from Future Allowance")
    st.info(
        f"Next month's ({next_month}) base allowance is **{next_acc['base_allowance']:.0f} kg**."
    )

    borrow_amount = st.number_input(
        "Amount to borrow (kg)",
        min_value=0.0,
        max_value=next_acc["base_allowance"] * 0.5,
        step=10.0,
        value=50.0,
    )

    if st.button("Simulate Borrowing"):
        success = engine.borrow_from_future(current_month, next_month, borrow_amount)

        if success:
            penalty = trading.calculate_borrowing_penalty(
                borrow_amount, months_until_due=1
            )
            st.success(f"Successfully borrowed **{borrow_amount:.0f} kg**.")
            st.error(
                f"Warning: You will owe **{penalty['total_owed']:.0f} kg** next month (includes {penalty['interest']:.0f} kg interest penalty)."
            )

            save_carbon_banking_action(
                "demo_user", "borrow", borrow_amount, current_month, next_month
            )
            st.rerun()
        else:
            st.error(
                "Borrowing limit exceeded. You can only borrow up to 50% of next month's base allowance."
            )

# --- Strategy Evaluation ---
st.divider()
st.subheader("🧠 AI Strategy Recommendation")
strategy = trading.evaluate_banking_strategy(
    current_surplus=current_acc["remaining"], projected_deficit=0.0
)

if strategy["recommendation"] == "Bank Surplus":
    st.success(
        f"**Recommendation:** {strategy['recommendation']}. You have a surplus of {strategy['original_amount']:.0f} kg. If banked, it will be worth {strategy['value_next_month']:.0f} kg next month (loss of {strategy['loss_to_decay']:.0f} kg to decay)."
    )
else:
    st.warning(
        f"**Recommendation:** {strategy['recommendation']}. Borrowing {strategy['amount_needed']:.0f} kg will cost you {strategy['penalty_cost']:.0f} kg in interest penalties."
    )

# --- History ---
st.divider()
st.subheader("📜 Banking History")
history = get_carbon_banking_history("demo_user")
if history:
    st.dataframe(pd.DataFrame(history), use_container_width=True)
else:
    st.info("No banking actions recorded yet.")
