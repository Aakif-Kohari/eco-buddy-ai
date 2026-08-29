import streamlit as st
import datetime
from datetime import timedelta
import uuid

from src.utils.sustainability_roadmap import (
    init_roadmap_db,
    generate_personalized_roadmap,
    get_active_roadmap_for_user,
    update_milestone_progress,
    reschedule_missed_milestones,
    detect_missed_milestones,
    get_roadmap_graph_data,
    STATUS_LOCKED,
    STATUS_ACTIONABLE,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_MISSED,
    STATUS_SKIPPED,
    CircularDependencyError,
    MilestoneDependencyError
)

from app import render_top_auth
try:
    from streamlit_agraph import agraph, Node, Edge, Config
    HAS_AGRAPH = True
except ImportError:
    HAS_AGRAPH = False

st.set_page_config(page_title="Sustainability Roadmap", page_icon="🗺️", layout="wide")

def load_custom_css():
    st.markdown("""
        <style>
        .roadmap-card {
            background-color: var(--background-color);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: bold;
            text-transform: uppercase;
        }
        .status-COMPLETED { background-color: #d4edda; color: #155724; }
        .status-IN_PROGRESS { background-color: #fff3cd; color: #856404; }
        .status-ACTIONABLE { background-color: #cce5ff; color: #004085; }
        .status-LOCKED { background-color: #e2e3e5; color: #383d41; }
        .status-MISSED { background-color: #f8d7da; color: #721c24; }
        .status-SKIPPED { background-color: #d6d8db; color: #383d41; }
        </style>
    """, unsafe_allow_html=True)

def initialize_system():
    # Make sure tables exist
    init_roadmap_db()

def main():
    load_custom_css()
    
    try:
        user_id = st.session_state.get('user_id')
        if not user_id:
            st.warning("Please log in to view your Sustainability Roadmap.")
            return
            
        initialize_system()
        
        st.title("🗺️ Your Sustainability Roadmap")
        st.markdown("Follow your personalized path to a more sustainable lifestyle. Milestones are unlocked as you progress.")
        
        # Detect and fetch active roadmap
        roadmap = get_active_roadmap_for_user(user_id)
        
        if not roadmap:
            st.info("You don't have an active roadmap yet.")
            if st.button("🌱 Generate My Personalized Roadmap", type="primary"):
                with st.spinner("Analyzing your profile, habits, and src.utils.goals..."):
                    roadmap = generate_personalized_roadmap(user_id)
                st.success("Roadmap generated successfully!")
                st.rerun()
            return
            
        # Detect missed milestones before rendering
        detect_missed_milestones(roadmap.id)
        roadmap = get_active_roadmap_for_user(user_id) # reload after detection
        
        if not roadmap:
            st.error("Error loading roadmap.")
            return

        # Overall Progress Header
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.progress(roadmap.overall_progress / 100.0)
            st.caption(f"Overall Completion: {roadmap.overall_progress:.1f}%")
        with col2:
            st.metric("Total Milestones", len(roadmap.milestones))
        with col3:
            completed = sum(1 for m in roadmap.milestones if m.status == STATUS_COMPLETED)
            st.metric("Completed", completed)

        # Tabs for different views
        tab_list, tab_graph, tab_timeline, tab_missed = st.tabs([
            "📋 Milestones List", 
            "🕸️ Dependency Graph", 
            "⏳ Estimated Timeline",
            "⚠️ Missed / Overdue"
        ])
        
        with tab_list:
            render_milestones_list(roadmap)
            
        with tab_graph:
            if HAS_AGRAPH:
                render_dependency_graph(roadmap.id)
            else:
                st.info("Dependency graph visualization requires the `streamlit-agraph` package.")
                
        with tab_timeline:
            render_timeline(roadmap)
            
        with tab_missed:
            render_missed_milestones(roadmap)

    except Exception as e:
        st.error(f"An error occurred: {e}")
        import traceback
        st.code(traceback.format_exc())

def render_milestones_list(roadmap):
    st.subheader("Your Action Plan")
    
    filter_status = st.selectbox(
        "Filter by Status", 
        ["All", STATUS_ACTIONABLE, STATUS_IN_PROGRESS, STATUS_LOCKED, STATUS_COMPLETED, STATUS_SKIPPED, STATUS_MISSED]
    )
    
    for ms in roadmap.milestones:
        if filter_status != "All" and ms.status != filter_status:
            continue
            
        with st.container():
            st.markdown(f'<div class="roadmap-card">', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"#### {ms.title}")
                st.markdown(f'<span class="status-badge status-{ms.status}">{ms.status}</span>', unsafe_allow_html=True)
                if ms.is_alternative_group:
                    st.caption("🔄 This is an alternative pathway.")
            with col2:
                st.write(f"**Difficulty:** {ms.difficulty}/10")
                st.write(f"**Impact:** {ms.impact_score}")
            with col3:
                if ms.target_date:
                    st.write(f"**Target:** {ms.target_date.strftime('%Y-%m-%d')}")
                if ms.estimated_completion_date:
                    st.write(f"**ETA:** {ms.estimated_completion_date.strftime('%Y-%m-%d')}")
            
            st.markdown(f"*{ms.description}*")
            
            # Interactive portion for actionable/in-progress
            if ms.status in [STATUS_ACTIONABLE, STATUS_IN_PROGRESS]:
                st.write(f"**Progress:** {ms.current_value} / {ms.target_value} {ms.unit}")
                new_progress = st.slider(
                    f"Update Progress for '{ms.title}'", 
                    min_value=0.0, 
                    max_value=float(ms.target_value), 
                    value=float(ms.current_value),
                    key=f"slider_{ms.id}"
                )
                if new_progress != ms.current_value:
                    if st.button("Save Progress", key=f"btn_{ms.id}"):
                        try:
                            update_milestone_progress(ms.id, new_progress)
                            st.success("Progress saved!")
                            st.rerun()
                        except MilestoneDependencyError as e:
                            st.error(str(e))
                            
            # Blocked dependencies explanation
            if ms.status == STATUS_LOCKED:
                blocking = [d["depends_on_id"] for d in ms.dependencies if d["dependency_type"] == "BLOCKING"]
                if blocking:
                    blocked_by_titles = [m.title for m in roadmap.milestones if m.id in blocking and m.status != STATUS_COMPLETED]
                    if blocked_by_titles:
                        st.warning(f"Locked by: {', '.join(blocked_by_titles)}")
            
            st.markdown("</div>", unsafe_allow_html=True)

def render_dependency_graph(roadmap_id: int):
    st.subheader("Milestone Dependencies")
    st.markdown("Explore how your milestones are connected. Arrows indicate dependencies.")
    
    graph_data = get_roadmap_graph_data(roadmap_id)
    
    nodes = []
    edges = []
    
    status_colors = {
        STATUS_COMPLETED: "#d4edda",
        STATUS_IN_PROGRESS: "#fff3cd",
        STATUS_ACTIONABLE: "#cce5ff",
        STATUS_LOCKED: "#e2e3e5",
        STATUS_MISSED: "#f8d7da",
        STATUS_SKIPPED: "#d6d8db",
    }
    
    for n in graph_data["nodes"]:
        nodes.append( Node(id=n["id"], 
                           label=n["label"], 
                           size=15 + n["value"], 
                           color=status_colors.get(n["group"], "#e2e3e5"),
                           title=n["title"]) )
                           
    for e in graph_data["edges"]:
        edges.append( Edge(source=e["from"], 
                           target=e["to"], 
                           label=e["label"],
                           dashes=e["dashes"]) )
                           
    config = Config(width=800, 
                    height=500, 
                    directed=True,
                    nodeHighlightBehavior=True, 
                    highlightColor="#F7A7A6",
                    collapsible=False,
                    node={'labelProperty':'label'},
                    link={'labelProperty': 'label', 'renderLabel': True})

    agraph(nodes=nodes, edges=edges, config=config)

def render_timeline(roadmap):
    st.subheader("Estimated Completion Timeline")
    st.markdown("This timeline is dynamically calculated based on your historical pace and milestone difficulty.")
    
    import pandas as pd
    try:
        import plotly.express as px
    except ImportError:
        st.info("Plotly is required for the timeline visualization.")
        return
        
    tasks = []
    now = datetime.datetime.now()
    
    for ms in roadmap.milestones:
        if ms.status == STATUS_SKIPPED:
            continue
            
        start = ms.created_at if ms.created_at else now
        end = ms.estimated_completion_date if ms.estimated_completion_date else (start + timedelta(days=7))
        
        # Sanity check for inverted dates
        if end < start:
            end = start + timedelta(days=1)
            
        tasks.append(dict(Task=ms.title, Start=start, Finish=end, Status=ms.status))
        
    if tasks:
        df = pd.DataFrame(tasks)
        fig = px.timeline(df, x_start="Start", x_end="Finish", y="Task", color="Status")
        fig.update_yaxes(autorange="reversed") 
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No timeline data available.")

def render_missed_milestones(roadmap):
    st.subheader("Missed Milestones")
    missed = [m for m in roadmap.milestones if m.status == STATUS_MISSED]
    
    if not missed:
        st.success("Great job! You don't have any missed milestones right now.")
        return
        
    st.warning(f"You have {len(missed)} missed milestone(s).")
    
    for ms in missed:
        st.markdown(f"- **{ms.title}** (Target: {ms.target_date.strftime('%Y-%m-%d') if ms.target_date else 'Unknown'})")
        
    st.write("Don't worry, sustainability is a journey. You can reschedule your missed milestones to get back on track.")
    if st.button("Reschedule Missed Milestones (+14 days)"):
        reschedule_missed_milestones(roadmap.id, shift_days=14)
        st.success("Milestones rescheduled successfully!")
        st.rerun()

if __name__ == "__main__":
    main()
