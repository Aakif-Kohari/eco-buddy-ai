"""
Quiz UI components for EcoBuddy AI.
Provides UI elements for quiz tracking and progress display.
"""

import streamlit as st
from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime
from src.lib.quiz_tracker import get_quiz_tracker


def render_quiz_status(user_id: str, quiz_id: str) -> None:
    """
    Render quiz completion status.
    
    Args:
        user_id: ID of the user
        quiz_id: ID of the quiz
    """
    tracker = get_quiz_tracker()
    completed = tracker.is_quiz_completed(user_id, quiz_id)
    
    if completed:
        attempt = tracker.get_last_attempt(user_id, quiz_id)
        if attempt:
            score = attempt.get("score", 0)
            st.success(f"✅ Quiz completed! Score: {score:.1f}%")
            st.caption(f"Attempted on: {attempt.get('timestamp', 'N/A')}")
    else:
        st.info("📝 You haven't completed this quiz yet.")


def render_progress_dashboard(user_id: str) -> None:
    """
    Render user progress dashboard.
    
    Args:
        user_id: ID of the user
    """
    tracker = get_quiz_tracker()
    progress = tracker.get_user_progress(user_id)
    
    if progress.get("total_quizzes_taken", 0) == 0:
        st.info("📊 No quiz activity yet. Complete a quiz to see your progress!")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📝 Quizzes Taken", progress.get("total_quizzes_taken", 0))
    with col2:
        st.metric("✅ Completed", progress.get("completed_quizzes", 0))
    with col3:
        st.metric("📈 Avg Score", f"{progress.get('average_score', 0):.1f}%")
    with col4:
        st.metric("🏆 Highest", f"{progress.get('highest_score', 0):.1f}%")
    
    # Show history
    st.divider()
    st.subheader("📋 Quiz History")
    
    history = tracker.get_user_history(user_id)
    if history:
        df = pd.DataFrame([
            {
                "Quiz": h.get("quiz_id", "Unknown"),
                "Score": f"{h.get('score', 0):.1f}%",
                "Time": h.get("time_taken", 0),
                "Status": "✅" if h.get("completed", False) else "❌",
                "Date": h.get("timestamp", "N/A")[:10]
            }
            for h in history
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_quiz_leaderboard(quiz_id: str, limit: int = 10) -> None:
    """
    Render leaderboard for a quiz.
    
    Args:
        quiz_id: ID of the quiz
        limit: Maximum number of entries
    """
    tracker = get_quiz_tracker()
    leaderboard = tracker.get_leaderboard(quiz_id, limit)
    
    if not leaderboard:
        st.info("No attempts yet. Be the first to take the quiz!")
        return
    
    st.subheader("🏆 Leaderboard")
    
    for idx, entry in enumerate(leaderboard, 1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        st.markdown(
            f"{medal} **User**: {entry['user_id']} | "
            f"**Score**: {entry['score']:.1f}% | "
            f"**Time**: {entry['time_taken']}s"
        )


def render_quiz_attempt_warning(user_id: str, quiz_id: str) -> bool:
    """
    Render warning if quiz already attempted and get confirmation.
    
    Args:
        user_id: ID of the user
        quiz_id: ID of the quiz
    
    Returns:
        True if user confirms retake, False otherwise
    """
    tracker = get_quiz_tracker()
    
    if tracker.is_quiz_completed(user_id, quiz_id):
        attempt = tracker.get_last_attempt(user_id, quiz_id)
        score = attempt.get("score", 0) if attempt else 0
        
        st.warning(f"⚠️ You have already completed this quiz with {score:.1f}%.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔁 Retake Quiz", key="retake_quiz"):
                return True
        with col2:
            if st.button("❌ Cancel", key="cancel_retake"):
                return False
        return False
    
    return True


def render_quiz_completion_message(attempt: Dict[str, Any]) -> None:
    """
    Render quiz completion message with feedback.
    
    Args:
        attempt: Quiz attempt data
    """
    if not attempt:
        return
    
    score = attempt.get("score", 0)
    attempt_number = attempt.get("attempt_number", 1)
    
    if score >= 80:
        st.balloons()
        st.success(f"🎉 Excellent! You scored {score:.1f}%!")
    elif score >= 60:
        st.success(f"👏 Good job! You scored {score:.1f}%!")
    elif score >= 40:
        st.warning(f"📖 Nice try! You scored {score:.1f}%. Review the material and try again.")
    else:
        st.error(f"💪 Keep learning! You scored {score:.1f}%. Review and try again.")
    
    st.caption(f"Attempt #{attempt_number} completed on {datetime.now().strftime('%Y-%m-%d %H:%M')}")


def render_quiz_stats(quiz_id: str) -> None:
    """
    Render statistics for a quiz.
    
    Args:
        quiz_id: ID of the quiz
    """
    tracker = get_quiz_tracker()
    stats = tracker.get_quiz_stats(quiz_id)
    
    if stats.get("total_attempts", 0) == 0:
        st.info("No statistics available yet.")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📝 Attempts", stats.get("total_attempts", 0))
    with col2:
        st.metric("👤 Users", stats.get("unique_users", 0))
    with col3:
        st.metric("📈 Avg Score", f"{stats.get('average_score', 0):.1f}%")
    with col4:
        st.metric("🎯 Pass Rate", f"{stats.get('pass_rate', 0):.1f}%")