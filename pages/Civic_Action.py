import streamlit as st
from src.utils.civic_action_engine import CivicActionEngine
from src.core.database import log_civic_action, get_user_civic_actions
from src.community.gamification import award_civic_xp

st.set_page_config(page_title="Civic Action & Policy Impact", page_icon="🏛️")

st.title("🏛️ Civic Action & Policy Impact")
st.markdown("See how environmental policies affect your wallet and your footprint, and take action!")

if 'user_id' not in st.session_state or st.session_state.user_id is None:
    st.warning("Please log in to use the Civic Action features.")
    st.stop()

user_id = st.session_state.user_id
user_name = st.session_state.get('user_name', 'EcoBuddy User')

# We mock a user footprint for demonstration
# In a real app, this would be fetched from the database based on assessments
user_footprint = {
    "owns_ev": False,
    "composts": False,
    "monthly_gas_spend_usd": 150.0,
    "total_emissions_kg": 16000.0
}

engine = CivicActionEngine()
bills = engine.get_active_bills()

st.subheader("Active Environmental Bills")

for bill in bills:
    with st.expander(f"{bill['level']} Bill: {bill['title']}", expanded=True):
        st.write(f"**Summary:** {bill['summary']}")
        
        impact = engine.evaluate_user_impact(user_id, user_footprint, bill)
        savings_usd = impact["financial_savings_usd"]
        savings_kg = impact["carbon_savings_kg"]
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Estimated Financial Impact (Annual)", f"${savings_usd:,.2f}", 
                      delta=f"${savings_usd:,.2f}" if savings_usd > 0 else None)
        with col2:
            st.metric("Estimated Carbon Impact (Annual)", f"{savings_kg:,.0f} kg CO2e",
                      delta=f"-{savings_kg:,.0f} kg" if savings_kg > 0 else None, delta_color="inverse")
            
        st.markdown("---")
        
        prompt_key = f"prompt_{bill['bill_id']}"
        if st.button("Draft Advocacy Letter", key=f"draft_{bill['bill_id']}"):
            st.session_state[prompt_key] = engine.generate_advocacy_prompt(
                user_name, bill['title'], savings_usd, savings_kg
            )
            
        if prompt_key in st.session_state:
            st.text_area("Your Personalized Letter", value=st.session_state[prompt_key], height=300)
            
            if st.button("I Sent This Letter!", key=f"sent_{bill['bill_id']}"):
                if log_civic_action(user_id, bill['bill_id'], "sent_email"):
                    award_civic_xp(user_id)
                    st.success("Action logged! You earned 50 XP and unlocked the Civic Champion badge!")
                    st.balloons()
                else:
                    st.error("Failed to log action.")

st.markdown("---")
st.subheader("Your Civic Actions")
actions = get_user_civic_actions(user_id)
if actions:
    for action in actions:
        st.write(f"- **{action['action_type']}** for Bill ID `{action['bill_id']}` on {action['created_at']}")
else:
    st.info("You haven't taken any civic actions yet. Draft a letter above to get started!")
