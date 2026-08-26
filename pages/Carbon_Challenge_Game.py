"""
Carbon Challenge Game Page.
Streamlit page featuring an immersive, text-and-choice-based interactive game interface with dynamic progress bars.
"""

import streamlit as st
from scenario_challenge_engine import ScenarioChallengeEngine
from database import save_challenge_result, get_challenge_history

st.set_page_config(page_title="Carbon Challenge", page_icon="🎮", layout="centered")

st.title("🎮 Interactive Carbon Footprint Scenario Challenge")
st.markdown(
    "Test your ability to balance convenience, budget, and carbon footprint in real-time scenarios."
)

# --- Game Initialization ---
if "game_engine" not in st.session_state:
    st.session_state.game_engine = None
    st.session_state.game_started = False

if not st.session_state.game_started:
    st.subheader("⚙️ Configure Your Challenge")
    scenario_id = "day_in_life"  # Currently only one scenario implemented

    col1, col2 = st.columns(2)
    with col1:
        carbon_budget = st.number_input(
            "Carbon Budget (kg CO₂e)",
            min_value=5.0,
            max_value=50.0,
            step=1.0,
            value=10.0,
        )
    with col2:
        monetary_budget = st.number_input(
            "Monetary Budget ($)", min_value=10.0, max_value=100.0, step=5.0, value=40.0
        )

    if st.button("🚀 Start Challenge", type="primary"):
        st.session_state.game_engine = ScenarioChallengeEngine(
            scenario_id=scenario_id,
            carbon_budget=carbon_budget,
            monetary_budget=monetary_budget,
        )
        st.session_state.game_started = True
        st.rerun()
else:
    engine = st.session_state.game_engine
    state = engine.get_current_state()

    # --- Game UI ---
    st.subheader(state["scenario_title"])

    # Progress Bars
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Carbon Remaining",
            f"{state['carbon_remaining']} / {state['carbon_budget']} kg",
        )
        st.progress(min(1.0, state["total_carbon"] / state["carbon_budget"]))
    with col2:
        st.metric(
            "Money Remaining",
            f"${state['money_remaining']} / ${state['monetary_budget']}",
        )
        st.progress(min(1.0, state["total_cost"] / state["monetary_budget"]))

    st.divider()

    # Current Scenario Text
    st.markdown(f"### {state['text']}")

    # Choices
    if not state["is_complete"]:
        st.markdown("**Make your choice:**")
        for idx, choice in enumerate(state["choices"]):
            if st.button(
                f"{choice['text']}  *(+{choice['carbon_impact']} kg CO₂e, +${choice['cost_impact']})*",
                key=f"choice_{idx}",
                use_container_width=True,
            ):
                try:
                    engine.make_choice(idx)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
    else:
        # End Game Screen
        evaluation = engine.evaluate_outcome()

        st.divider()
        if evaluation["outcome"] == "perfect":
            st.balloons()
            st.success(evaluation["message"])
        elif evaluation["outcome"] == "loss":
            st.error(evaluation["message"])
        else:
            st.warning(evaluation["message"])

        st.markdown("### 📜 Your Journey")
        for step in evaluation["history"]:
            st.markdown(
                f"- **{step['node'].replace('_', ' ').title()}**: Chose '{step['choice']}' (+{step['carbon_added']} kg, +${step['cost_added']})"
            )

        if st.button("🔄 Play Again"):
            st.session_state.game_engine.reset_state()
            st.rerun()

        if st.button("💾 Save Result"):
            save_challenge_result(
                "day_in_life",
                evaluation["outcome"],
                evaluation["final_carbon"],
                evaluation["final_cost"],
            )
            st.success("Result saved to history!")
