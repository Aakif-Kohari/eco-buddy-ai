"""
Quiz routes for EcoBuddy AI.
Handles quiz submissions, tracking, and results.
"""

from flask import Blueprint, request, session, flash, redirect, url_for, render_template
from datetime import datetime
from src.lib.quiz_tracker import get_quiz_tracker
from src.lib.quiz_ui import render_quiz_status, render_quiz_completion_message

quizes_bp = Blueprint('quizes_bp', __name__, url_prefix='/quiz')


def calculate_score(form_data):
    """
    Calculate quiz score from form data.
    
    Args:
        form_data: Form data containing answers
    
    Returns:
        Score as percentage
    """
    # Get all answers from form
    answers = {}
    total_questions = 0
    correct_answers = 0
    
    for key, value in form_data.items():
        if key.startswith('question_'):
            question_id = key.replace('question_', '')
            answers[question_id] = value
            total_questions += 1
            
            # Check if answer is correct
            # You'll need to implement this based on your quiz data
            # For now, assuming all answers are correct for demo
            correct_answers += 1
    
    if total_questions == 0:
        return 0.0
    
    return (correct_answers / total_questions) * 100


@quizes_bp.route('/submit', methods=['POST'])
def submit_quiz():
    """Handle quiz submission with duplicate prevention."""
    user_id = session.get('user_id')
    quiz_id = request.form.get('quiz_id')
    
    if not user_id:
        flash("Please login to submit quiz.", "warning")
        return redirect(url_for('auth.login'))
    
    if not quiz_id:
        flash("Quiz ID is required.", "error")
        return redirect(url_for('quizes_bp.quiz_list'))
    
    tracker = get_quiz_tracker()
    
    # Check if already completed
    if tracker.is_quiz_completed(user_id, quiz_id):
        flash("You have already completed this quiz!", "warning")
        return redirect(url_for('quizes_bp.quiz_results', quiz_id=quiz_id))
    
    # Calculate score
    score = calculate_score(request.form)
    time_taken = int(request.form.get('time_taken', 0))
    
    # Record attempt
    attempt = tracker.record_attempt(
        user_id=user_id,
        quiz_id=quiz_id,
        score=score,
        answers=request.form.get('answers', {}),
        time_taken=time_taken,
        completed=True
    )
    
    if attempt.get('success', False):
        flash(f"Quiz completed! Score: {score:.1f}%", "success")
        return redirect(url_for('quizes_bp.quiz_results', quiz_id=quiz_id))
    else:
        flash(attempt.get('error', 'Failed to record quiz attempt.'), "error")
        return redirect(url_for('quizes_bp.quiz_list'))


@quizes_bp.route('/results/<quiz_id>')
def quiz_results(quiz_id):
    """Show quiz results."""
    user_id = session.get('user_id')
    tracker = get_quiz_tracker()
    
    if not user_id:
        flash("Please login to view results.", "warning")
        return redirect(url_for('auth.login'))
    
    attempt = tracker.get_last_attempt(user_id, quiz_id)
    
    if not attempt:
        flash("No results found for this quiz.", "info")
        return redirect(url_for('quizes_bp.quiz_list'))
    
    return render_template('quiz_results.html', attempt=attempt)


@quizes_bp.route('/progress')
def quiz_progress():
    """Show user's quiz progress."""
    user_id = session.get('user_id')
    
    if not user_id:
        flash("Please login to view progress.", "warning")
        return redirect(url_for('auth.login'))
    
    return render_template('quiz_progress.html', user_id=user_id)


@quizes_bp.route('/leaderboard/<quiz_id>')
def quiz_leaderboard(quiz_id):
    """Show leaderboard for a quiz."""
    tracker = get_quiz_tracker()
    leaderboard = tracker.get_leaderboard(quiz_id, limit=10)
    
    return render_template('quiz_leaderboard.html', leaderboard=leaderboard, quiz_id=quiz_id)


@quizes_bp.route('/list')
def quiz_list():
    """Show list of available quizzes."""
    # You'll need to implement quiz list logic here
    return render_template('quiz_list.html')