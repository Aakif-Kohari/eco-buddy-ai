import streamlit as st
import plotly.graph_objects as go
from accountability_buddy import BuddySystem
from session_state_utils import init_session_state

st.set_page_config(page_title="Eco Buddies", page_icon="🤝", layout="wide")

st.title("🤝 Eco Buddy Partner")
st.markdown("Pair up with friends to keep each other accountable and reduce your carbon footprints together!")

# Assuming user_id is stored in session state
init_session_state()
if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.warning("Please log in to use the Eco Buddy feature.")
    st.stop()

current_user_id = st.session_state.user_id
buddy_system = BuddySystem()

tab1, tab2, tab3 = st.tabs(["Find a Buddy", "Pending Requests", "My Buddies"])

with tab1:
    st.subheader("Search for an Eco Buddy")
    search_username = st.text_input("Enter username to search:")
    
    if st.button("Search"):
        if not search_username:
            st.error("Please enter a username.")
        else:
            user = buddy_system.get_user_by_username(search_username)
            if not user:
                st.error("User not found.")
            elif user["id"] == current_user_id:
                st.warning("You cannot buddy with yourself.")
            else:
                st.success(f"Found user: {user['username']}")
                st.session_state.found_user_id = user["id"]

    if "found_user_id" in st.session_state:
        if st.button("Send Buddy Request"):
            success, msg = buddy_system.send_buddy_request(current_user_id, st.session_state.found_user_id)
            if success:
                st.success(msg)
                del st.session_state.found_user_id
            else:
                st.error(msg)

with tab2:
    st.subheader("Pending Requests")
    requests = buddy_system.get_pending_requests(current_user_id)
    
    if not requests:
        st.info("No pending buddy requests.")
    else:
        for req in requests:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{req['sender_name']}** sent you a request.")
            with col2:
                if st.button("Accept", key=f"accept_{req['id']}"):
                    success, msg = buddy_system.accept_buddy_request(req['id'])
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
            with col3:
                if st.button("Reject", key=f"reject_{req['id']}"):
                    success, msg = buddy_system.reject_buddy_request(req['id'])
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

with tab3:
    st.subheader("My Buddies")
    buddies = buddy_system.get_buddies(current_user_id)
    
    if not buddies:
        st.info("You don't have any Eco Buddies yet. Search for one in the 'Find a Buddy' tab!")
    else:
        buddy_names = [b["buddy_name"] for b in buddies]
        selected_buddy_name = st.selectbox("Select Buddy", buddy_names)
        
        selected_buddy = next(b for b in buddies if b["buddy_name"] == selected_buddy_name)
        buddy_id = selected_buddy["buddy_id"]
        
        # Dashboard
        stats = buddy_system.get_buddy_comparison(current_user_id, buddy_id)
        
        st.markdown(f"### Synergy Score: {stats['synergy_score']:.1f} / 100")
        st.progress(stats['synergy_score'] / 100.0)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Your Footprint", f"{stats['user1']['total_footprint']:.1f} kg CO2")
        with col2:
            st.metric(f"{selected_buddy_name}'s Footprint", f"{stats['user2']['total_footprint']:.1f} kg CO2")
            
        # Comparison Chart
        fig = go.Figure(data=[
            go.Bar(name='You', x=['Total Footprint'], y=[stats['user1']['total_footprint']]),
            go.Bar(name=selected_buddy_name, x=['Total Footprint'], y=[stats['user2']['total_footprint']])
        ])
        fig.update_layout(barmode='group', title="Footprint Comparison (kg CO2)")
        st.plotly_chart(fig, use_container_width=True)

        # Nudges
        st.subheader(f"Nudge {selected_buddy_name}")
        nudge_msg = st.selectbox("Select a nudge message", [
            "Keep up the great work! 🌱",
            "Let's reduce our carbon footprints this week! 🚲",
            "Remember to log your eco-friendly actions! 📝",
            "You're an eco-champion! 🏆"
        ])
        
        if st.button("Send Nudge"):
            if buddy_system.send_nudge(current_user_id, buddy_id, nudge_msg):
                st.success("Nudge sent!")
                
        with st.expander("Nudge History"):
            history = buddy_system.get_nudge_history(current_user_id, buddy_id)
            for h in history:
                st.write(f"**{h['sender_name']}**: {h['message']} *(on {h['created_at']})*")
