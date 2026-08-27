import streamlit as st
from src.community.eco_pledge import (
    PLEDGE_TEMPLATES,
    create_pledge,
    get_public_pledges,
    get_user_pledges,
    support_pledge,
    verify_pledge_progress
)
from datetime import datetime, timedelta

st.set_page_config(page_title="Eco Pledge Board", page_icon="🤝", layout="wide")
st.title("🤝 Community Eco Pledge Board")

# Dummy user_id for demonstration purposes
USER_ID = "user_123" 

tab1, tab2, tab3 = st.tabs(["Community Feed", "Make a Pledge", "My Pledges"])

with tab1:
    st.header("Community Feed")
    sort_by = st.selectbox("Sort by", ["recent", "trending"])
    pledges = get_public_pledges(limit=50, offset=0, sort_by=sort_by)
    
    if not pledges:
        st.info("No public pledges yet. Be the first to make one!")
    else:
        for p in pledges:
            with st.card():
                st.subheader(p['title'])
                st.write(p['description'])
                
                col1, col2 = st.columns(2)
                with col1:
                    if p['target_value']:
                        progress = min(p['current_value'] / p['target_value'], 1.0)
                        st.progress(progress, text=f"Progress: {p['current_value']} / {p['target_value']} {p['target_metric']}")
                with col2:
                    st.write(f"🤝 {p['supporters_count']} Supporters")
                    if st.button("Support", key=f"support_{p['id']}"):
                        if support_pledge(p['id'], USER_ID):
                            st.success("You supported this pledge!")
                            st.rerun()
                        else:
                            st.warning("You already supported this pledge.")
                st.caption(f"Status: {p['status']} | Created: {p['created_at'][:10]}")

with tab2:
    st.header("Make a Pledge")
    
    pledge_type = st.radio("Pledge Type", ["Use Template", "Custom Pledge"])
    
    with st.form("make_pledge_form"):
        if pledge_type == "Use Template":
            template_options = {k: v['title'] for k, v in PLEDGE_TEMPLATES.items()}
            selected_template_id = st.selectbox("Select a Template", options=list(template_options.keys()), format_func=lambda x: template_options[x])
            
            selected_template = PLEDGE_TEMPLATES[selected_template_id]
            title = selected_template['title']
            description = st.text_area("Description (optional)", value=selected_template['description'])
            target_metric = selected_template['target_metric']
            target_value = selected_template['target_value']
            deadline = st.date_input("Deadline", datetime.now().date() + timedelta(days=30))
            template_id = selected_template_id
        else:
            title = st.text_input("Pledge Title")
            description = st.text_area("Description")
            target_metric = st.text_input("Target Metric (e.g., kg CO2 avoided)")
            target_value = st.number_input("Target Value", min_value=0.0, value=1.0)
            deadline = st.date_input("Deadline", datetime.now().date() + timedelta(days=30))
            template_id = None
            
        submitted = st.form_submit_button("Create Pledge")
        
        if submitted:
            if not title:
                st.error("Please enter a title.")
            else:
                create_pledge(
                    user_id=USER_ID,
                    title=title,
                    description=description,
                    template_id=template_id,
                    target_metric=target_metric,
                    target_value=target_value,
                    deadline=deadline.isoformat()
                )
                st.success("Pledge created successfully!")
                st.rerun()

with tab3:
    st.header("My Pledges")
    my_pledges = get_user_pledges(USER_ID)
    
    if not my_pledges:
        st.info("You haven't made any pledges yet.")
    else:
        for p in my_pledges:
            with st.expander(f"{p['title']} ({p['status']})"):
                st.write(p['description'])
                if p['target_value']:
                    progress = min(p['current_value'] / p['target_value'], 1.0)
                    st.progress(progress, text=f"Progress: {p['current_value']} / {p['target_value']} {p['target_metric']}")
                    
                if st.button("Verify Progress", key=f"verify_{p['id']}"):
                    updated_pledge = verify_pledge_progress(p['id'])
                    st.success("Progress verified!")
                    st.rerun()
