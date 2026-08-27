import streamlit as st
import json
import uuid
import copy

from src.decision_engine.models import ScenarioInputs, SimulationResult
from src.decision_engine.simulator import DecisionSimulator
from src.decision_engine.history import ScenarioHistoryManager, load_baseline_from_user
from src.components.simulator_ui import render_inputs_form, render_simulation_dashboard

st.set_page_config(page_title="Decision Simulator", page_icon="🔮", layout="wide")

st.title("🔮 Personal Sustainability Decision Simulator")
st.markdown("Build 'What-If' scenarios, compare trade-offs, and project your environmental impact over time.")

user_id = st.session_state.get("user_id", 1)
history_manager = ScenarioHistoryManager()

# Initialize session state for the simulator
if "sim_baseline" not in st.session_state:
    st.session_state.sim_baseline = load_baseline_from_user(user_id)
if "sim_alternatives" not in st.session_state:
    st.session_state.sim_alternatives = {}
if "sim_result" not in st.session_state:
    st.session_state.sim_result = None

tab_build, tab_results, tab_history = st.tabs(["🏗️ Build Scenarios", "📊 Simulation Results", "📜 History"])

with tab_build:
    st.header("1. Define Your Baseline")
    with st.expander("Edit Current Lifestyle (Baseline)", expanded=True):
        st.session_state.sim_baseline = render_inputs_form("base", st.session_state.sim_baseline)
        
    st.header("2. Add Alternatives")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        alt_name = st.text_input("Alternative Name", value=f"Scenario {len(st.session_state.sim_alternatives)+1}")
        if st.button("Add Alternative"):
            if alt_name not in st.session_state.sim_alternatives:
                st.session_state.sim_alternatives[alt_name] = copy.deepcopy(st.session_state.sim_baseline)
                st.rerun()
                
    with col2:
        if not st.session_state.sim_alternatives:
            st.info("No alternatives added yet. Add one to compare against your baseline.")
        else:
            for name, alt_inputs in list(st.session_state.sim_alternatives.items()):
                with st.expander(f"Edit {name}", expanded=False):
                    updated_inputs = render_inputs_form(f"alt_{name}", alt_inputs)
                    st.session_state.sim_alternatives[name] = updated_inputs
                    if st.button(f"Remove {name}", key=f"del_{name}"):
                        del st.session_state.sim_alternatives[name]
                        st.rerun()
                        
    st.markdown("---")
    if st.button("🚀 Run Simulation", type="primary", use_container_width=True):
        st.session_state.sim_result = DecisionSimulator.simulate(
            st.session_state.sim_baseline, 
            st.session_state.sim_alternatives
        )
        
        # Auto-save scenarios
        history_manager.save_scenario(user_id, "baseline", "Baseline", st.session_state.sim_baseline, is_baseline=True)
        for name, alt_inputs in st.session_state.sim_alternatives.items():
            history_manager.save_scenario(user_id, str(uuid.uuid4()), name, alt_inputs)
            
        st.success("Simulation Complete! Check the Results tab.")

with tab_results:
    if st.session_state.sim_result:
        render_simulation_dashboard(st.session_state.sim_result)
    else:
        st.info("Run a simulation in the 'Build Scenarios' tab to see results.")

with tab_history:
    st.subheader("Saved Scenarios")
    history = history_manager.get_user_scenarios(user_id)
    
    if not history:
        st.write("No saved scenarios yet.")
    else:
        for sid, name, is_base, created_at, inputs in history:
            with st.container(border=True):
                colA, colB = st.columns([3, 1])
                with colA:
                    st.markdown(f"**{name}** {'(Baseline)' if is_base else ''}")
                    st.caption(f"Saved on: {created_at}")
                with colB:
                    if st.button("Load as Baseline", key=f"load_base_{sid}"):
                        st.session_state.sim_baseline = copy.deepcopy(inputs)
                        st.rerun()
                    if not is_base:
                        if st.button("Load as Alternative", key=f"load_alt_{sid}"):
                            st.session_state.sim_alternatives[name] = copy.deepcopy(inputs)
                            st.rerun()
                        if st.button("Delete", key=f"del_hist_{sid}"):
                            history_manager.delete_scenario(sid)
                            st.rerun()
