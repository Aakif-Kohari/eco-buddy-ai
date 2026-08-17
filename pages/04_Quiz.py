"""
Quiz Page for EcoBuddy AI
Allows users to take quizzes and track their progress.
"""

import streamlit as st
from datetime import datetime
from src.lib.quiz_tracker import get_quiz_tracker
from src.lib.quiz_ui import (
    render_quiz_status,
    render_quiz_completion_message,
    render_progress_dashboard,
    render_quiz_leaderboard,
    render_quiz_attempt_warning
)

# Page configuration
st.set_page_config(page_title="Eco Quiz", page_icon="📝", layout="wide")

st.title("📝 Eco Quiz")

# Sample quiz data (replace with your actual quiz data)
SAMPLE_QUIZ = {
    "id": "eco_101",
    "title": "Eco Knowledge Quiz",
    "questions": [
        {
            "id": "q1",
            "question": "What is the most effective way to reduce carbon footprint?",
            "options": ["Planting trees", "Reducing energy consumption", "Recycling", "All of the above"],
            "correct": 3
        },
        {
            "id": "q2",
            "question": "Which of these is a renewable energy source?",
            "options": ["Coal", "Natural gas", "Solar power", "Nuclear"],
            "correct": 2
        },
        {
            "id": "q3",
            "question": "What is the biggest contributor to greenhouse gas emissions?",
            "options": ["Transportation", "Agriculture", "Energy production", "Industry"],
            "correct": 2
        }
    ]
}

# Initialize quiz tracker
tracker = get_quiz_tracker()

# Get user ID (from session state or default)
user_id = st.session_state.get("user_id", "default_user")

# Tabs
tab1, tab2, tab3 = st.tabs(["📝 Take Quiz", "📊 My Progress", "🏆 Leaderboard"])

# ============================================================================
# TAB 1: Take Quiz
# ============================================================================
with tab1:
    st.subheader("📝 Take a Quiz")
    
    # Check if user already completed the quiz
    quiz_id = SAMPLE_QUIZ["id"]
    
    if tracker.is_quiz_completed(user_id, quiz_id):
        attempt = tracker.get_last_attempt(user_id, quiz_id)
        st.warning(f"⚠️ You have already completed this quiz!")
        if attempt:
            st.info(f"Your score: **{attempt.get('score', 0):.1f}%**")
        
        # Allow retake
        if st.button("🔄 Retake Quiz"):
            st.session_state["quiz_retake"] = True
            st.rerun()
        
        if st.session_state.get("quiz_retake", False):
            st.info("You can retake the quiz. Your progress will be updated.")
            # Show the quiz again
            _render_quiz(SAMPLE_QUIZ, user_id, tracker)
    else:
        # Show quiz for first time
        _render_quiz(SAMPLE_QUIZ, user_id, tracker)

# ============================================================================
# TAB 2: Progress
# ============================================================================
with tab2:
    st.subheader("📊 My Quiz Progress")
    render_progress_dashboard(user_id)

# ============================================================================
# TAB 3: Leaderboard
# ============================================================================
with tab3:
    st.subheader("🏆 Quiz Leaderboard")
    render_quiz_leaderboard(SAMPLE_QUIZ["id"])


# ============================================================================
# Helper Functions
# ============================================================================

def _render_quiz(quiz_data, user_id, tracker):
    """Render the quiz questions."""
    
    # Initialize session state for quiz
    if "quiz_started" not in st.session_state:
        st.session_state.quiz_started = False
        st.session_state.quiz_answers = {}
        st.session_state.quiz_submitted = False
        st.session_state.start_time = datetime.now()
    
    if not st.session_state.quiz_started:
        if st.button("🚀 Start Quiz"):
            st.session_state.quiz_started = True
            st.rerun()
        return
    
    # Show questions
    st.info(f"📝 Answer all {len(quiz_data['questions'])} questions")
    
    answers = {}
    for idx, q in enumerate(quiz_data["questions"]):
        st.markdown(f"**Q{idx+1}: {q['question']}**")
        answers[q["id"]] = st.radio(
            "",
            q["options"],
            key=f"q_{q['id']}",
            index=None
        )
        st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📤 Submit Quiz", type="primary"):
            # Check if all questions answered
            unanswered = [q["id"] for q in quiz_data["questions"] if answers.get(q["id"]) is None]
            
            if unanswered:
                st.error(f"❌ Please answer all questions before submitting.")
                return
            
            # Calculate score
            correct = 0
            for q in quiz_data["questions"]:
                if answers.get(q["id"]) == q["options"][q["correct"]]:
                    correct += 1
            
            score = (correct / len(quiz_data["questions"])) * 100
            
            # Record attempt
            attempt = tracker.record_attempt(
                user_id=user_id,
                quiz_id=quiz_data["id"],
                score=score,
                answers=answers,
                time_taken=int((datetime.now() - st.session_state.start_time).total_seconds()),
                completed=True
            )
            
            if attempt.get("success", False):
                st.session_state.quiz_submitted = True
                st.session_state.quiz_score = score
                render_quiz_completion_message(attempt.get("attempt", {}))
                st.balloons()
                st.rerun()
            else:
                st.error(attempt.get("error", "Failed to submit quiz."))
    
    with col2:
        if st.button("🚫 Cancel"):
            st.session_state.quiz_started = False
            st.session_state.quiz_answers = {}
            st.rerun()
    
    # Show results if submitted
    if st.session_state.get("quiz_submitted", False):
        st.success(f"✅ Quiz completed! Score: {st.session_state.quiz_score:.1f}%")
        
        if st.button("🔄 Take Another Quiz"):
            st.session_state.quiz_started = False
            st.session_state.quiz_submitted = False
            st.rerun()