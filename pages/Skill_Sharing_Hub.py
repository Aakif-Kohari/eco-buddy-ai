"""
Skill Sharing Hub Page.
Streamlit page featuring a searchable marketplace directory, personal skill portfolio, and active swap negotiation interface.
"""

import streamlit as st
from skill_swap_engine import SkillSwapEngine
from knowledge_marketplace import KnowledgeMarketplace
from database import save_skill_listing, execute_skill_swap_db

st.set_page_config(page_title="Skill Sharing Hub", page_icon="🤝", layout="wide")

st.title("🤝 Peer-to-Peer Sustainable Skill Swap Marketplace")
st.markdown(
    "Share your eco-friendly knowledge and learn new skills using our non-monetary **Eco-Karma** economy."
)

# Initialize engine
if "swap_engine" not in st.session_state:
    st.session_state.swap_engine = SkillSwapEngine()
    st.session_state.marketplace = KnowledgeMarketplace(st.session_state.swap_engine)

    # Seed demo data
    engine = st.session_state.swap_engine
    engine.register_user("demo_user", initial_karma=100)
    engine.register_user("alice", initial_karma=80)
    engine.register_user("bob", initial_karma=120)

    engine.add_skill_offering("alice", "Urban Composting", "gardening", "beginner", 20)
    engine.add_skill_offering("bob", "Bicycle Repair", "repair", "intermediate", 30)
    engine.add_skill_offering(
        "alice", "Plant-Based Meal Prep", "cooking", "beginner", 25
    )

engine = st.session_state.swap_engine
marketplace = st.session_state.marketplace

# --- User Context ---
user_id = "demo_user"  # Simulated logged-in user
user_profile = engine.get_user(user_id)

st.sidebar.header("👤 Your Profile")
st.sidebar.metric("Eco-Karma Balance", f"🪙 {user_profile['eco_karma']}")
st.sidebar.metric("Skills Offered", len(user_profile["skills_offered"]))
st.sidebar.metric("Completed Swaps", user_profile["completed_swaps"])

# --- Main Layout ---
tab1, tab2, tab3 = st.tabs(
    ["🏪 Browse Marketplace", "➕ Offer a Skill", "🎒 My Portfolio"]
)

with tab1:
    st.subheader("Search & Discover Skills")
    col1, col2, col3 = st.columns(3)

    with col1:
        search_query = st.text_input("Search skills...")
    with col2:
        filter_cat = st.selectbox("Category", ["All"] + marketplace.VALID_CATEGORIES)
    with col3:
        filter_diff = st.selectbox(
            "Difficulty", ["All"] + marketplace.VALID_DIFFICULTIES
        )

    cat_val = "" if filter_cat == "All" else filter_cat
    diff_val = "" if filter_diff == "All" else filter_diff

    results = marketplace.search_listings(
        query=search_query, category=cat_val, difficulty=diff_val
    )

    if not results:
        st.info("No active listings match your criteria.")
    else:
        for res in results:
            with st.container():
                st.markdown(f"### 🌟 {res['skill_name']}")
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.markdown(
                        f"**Category:** {res['category'].title()} | **Difficulty:** {res['difficulty'].title()}"
                    )
                    st.markdown(
                        f"**Teacher:** User_{res['teacher_id']} (Rating: ⭐ {res['teacher_rating']}, Swaps: {res['teacher_swaps']})"
                    )
                with c2:
                    st.metric("Cost", f"🪙 {res['karma_cost']}")
                with c3:
                    if st.button("Request Swap", key=f"req_{res['listing_id']}"):
                        result = engine.execute_swap(user_id, res["listing_id"])
                        if result["success"]:
                            execute_skill_swap_db(
                                user_id,
                                res["teacher_id"],
                                res["skill_name"],
                                res["karma_cost"],
                            )
                            st.success(
                                f"Swap successful! You learned **{res['skill_name']}**."
                            )
                            st.rerun()
                        else:
                            st.error(result["error"])

with tab2:
    st.subheader("List a New Skill Offering")
    with st.form("new_skill_form"):
        skill_name = st.text_input("Skill Name (e.g., 'Mending Clothes')")
        col_a, col_b = st.columns(2)
        with col_a:
            category = st.selectbox("Category", marketplace.VALID_CATEGORIES)
        with col_b:
            difficulty = st.selectbox("Difficulty", marketplace.VALID_DIFFICULTIES)

        karma_cost = st.slider(
            "Eco-Karma Cost", min_value=5, max_value=100, step=5, value=20
        )

        if st.form_submit_button("Publish Listing"):
            if skill_name:
                engine.add_skill_offering(
                    user_id, skill_name, category, difficulty, karma_cost
                )
                save_skill_listing(
                    user_id, skill_name, category, difficulty, karma_cost
                )
                st.success("Skill listed successfully!")
                st.rerun()
            else:
                st.error("Please provide a skill name.")

with tab3:
    st.subheader("Your Skill Portfolio")
    st.markdown("### Skills You Offer")
    if user_profile["skills_offered"]:
        for skill in user_profile["skills_offered"]:
            st.markdown(f"- ✅ **{skill}**")
    else:
        st.info("You haven't listed any skills yet.")

    st.markdown("### Swap History")
    # In a real app, this would fetch from DB. Here we mock from engine.
    user_swaps = [
        s
        for s in engine.swaps
        if s["learner_id"] == user_id or s["teacher_id"] == user_id
    ]
    if user_swaps:
        for swap in user_swaps:
            role = "Learned" if swap["learner_id"] == user_id else "Taught"
            st.markdown(
                f"- **{role}**: {swap['skill_name']} ({swap['karma_transferred']} 🪙)"
            )
    else:
        st.info("No swap history yet.")
