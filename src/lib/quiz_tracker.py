"""
Quiz tracking and duplicate prevention module for EcoBuddy AI.
Tracks user quiz progress, prevents duplicate submissions, and stores quiz history.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

# In-memory storage for quiz tracking (can be replaced with database)
_quiz_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
_quiz_attempts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
_user_progress: Dict[str, Dict[str, Any]] = {}


class QuizTracker:
    """
    Tracks user quiz activity, prevents duplicates, and stores progress.
    """
    
    def __init__(self):
        self.history = _quiz_history
        self.attempts = _quiz_attempts
        self.progress = _user_progress
    
    def record_attempt(
        self, 
        user_id: str, 
        quiz_id: str, 
        score: float, 
        answers: Dict[str, Any],
        time_taken: int = 0,
        completed: bool = True
    ) -> Dict[str, Any]:
        """
        Record a quiz attempt for a user.
        
        Args:
            user_id: ID of the user
            quiz_id: ID of the quiz
            score: Score achieved (0-100)
            answers: User's answers
            time_taken: Time taken in seconds
            completed: Whether the quiz was completed
        
        Returns:
            Dictionary with attempt details
        """
        # Check if already completed
        if self.is_quiz_completed(user_id, quiz_id):
            return {
                "success": False,
                "error": "Quiz already completed",
                "attempt": self.get_last_attempt(user_id, quiz_id)
            }
        
        attempt = {
            "user_id": user_id,
            "quiz_id": quiz_id,
            "score": round(score, 2),
            "answers": answers,
            "time_taken": time_taken,
            "completed": completed,
            "attempt_number": self.get_attempt_count(user_id, quiz_id) + 1,
            "timestamp": datetime.now().isoformat(),
        }
        
        self.history[user_id].append(attempt)
        self.attempts[user_id][quiz_id] += 1
        
        # Update progress
        self._update_progress(user_id, quiz_id, score)
        
        return {
            "success": True,
            "attempt": attempt,
            "attempt_number": attempt["attempt_number"],
            "message": "Quiz attempt recorded successfully"
        }
    
    def is_quiz_completed(self, user_id: str, quiz_id: str) -> bool:
        """
        Check if a user has completed a quiz.
        
        Args:
            user_id: ID of the user
            quiz_id: ID of the quiz
        
        Returns:
            True if the quiz is completed, False otherwise
        """
        history = self.history.get(user_id, [])
        for attempt in history:
            if attempt.get("quiz_id") == quiz_id and attempt.get("completed", False):
                return True
        return False
    
    def get_last_attempt(self, user_id: str, quiz_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the last attempt for a quiz.
        
        Args:
            user_id: ID of the user
            quiz_id: ID of the quiz
        
        Returns:
            Last attempt details or None if no attempts
        """
        history = self.history.get(user_id, [])
        attempts = [a for a in history if a.get("quiz_id") == quiz_id]
        if attempts:
            return attempts[-1]
        return None
    
    def get_attempt_count(self, user_id: str, quiz_id: str) -> int:
        """
        Get the number of attempts for a quiz.
        
        Args:
            user_id: ID of the user
            quiz_id: ID of the quiz
        
        Returns:
            Number of attempts
        """
        return self.attempts.get(user_id, {}).get(quiz_id, 0)
    
    def get_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get complete quiz history for a user.
        
        Args:
            user_id: ID of the user
        
        Returns:
            List of all quiz attempts
        """
        return self.history.get(user_id, [])
    
    def get_user_progress(self, user_id: str) -> Dict[str, Any]:
        """
        Get overall progress for a user.
        
        Args:
            user_id: ID of the user
        
        Returns:
            Dictionary with progress statistics
        """
        if user_id in self.progress:
            return self.progress[user_id]
        
        # Calculate progress from history
        return self._calculate_progress(user_id)
    
    def _update_progress(self, user_id: str, quiz_id: str, score: float) -> None:
        """
        Update user progress after a quiz attempt.
        
        Args:
            user_id: ID of the user
            quiz_id: ID of the quiz
            score: Score achieved
        """
        progress = self._calculate_progress(user_id)
        progress["last_quiz"] = quiz_id
        progress["last_score"] = score
        progress["last_updated"] = datetime.now().isoformat()
        self.progress[user_id] = progress
    
    def _calculate_progress(self, user_id: str) -> Dict[str, Any]:
        """
        Calculate progress statistics from history.
        
        Args:
            user_id: ID of the user
        
        Returns:
            Dictionary with progress statistics
        """
        history = self.history.get(user_id, [])
        completed = [a for a in history if a.get("completed", False)]
        
        if not completed:
            return {
                "total_quizzes_taken": 0,
                "completed_quizzes": 0,
                "average_score": 0.0,
                "highest_score": 0.0,
                "lowest_score": 0.0,
                "total_time_spent": 0,
                "last_quiz": None,
                "last_score": 0.0,
                "last_updated": None
            }
        
        scores = [a.get("score", 0) for a in completed]
        time_spent = sum(a.get("time_taken", 0) for a in completed)
        
        return {
            "total_quizzes_taken": len(history),
            "completed_quizzes": len(completed),
            "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
            "highest_score": max(scores) if scores else 0.0,
            "lowest_score": min(scores) if scores else 0.0,
            "total_time_spent": time_spent,
            "last_quiz": completed[-1].get("quiz_id") if completed else None,
            "last_score": completed[-1].get("score", 0) if completed else 0.0,
            "last_updated": completed[-1].get("timestamp") if completed else None
        }
    
    def get_quiz_stats(self, quiz_id: str) -> Dict[str, Any]:
        """
        Get statistics for a specific quiz.
        
        Args:
            quiz_id: ID of the quiz
        
        Returns:
            Dictionary with quiz statistics
        """
        attempts = []
        for user_attempts in self.history.values():
            for attempt in user_attempts:
                if attempt.get("quiz_id") == quiz_id and attempt.get("completed", False):
                    attempts.append(attempt)
        
        if not attempts:
            return {
                "total_attempts": 0,
                "completed_attempts": 0,
                "average_score": 0.0,
                "highest_score": 0.0,
                "lowest_score": 0.0,
                "unique_users": 0,
                "pass_rate": 0.0
            }
        
        scores = [a.get("score", 0) for a in attempts]
        unique_users = len(set(a.get("user_id") for a in attempts))
        passing = sum(1 for s in scores if s >= 70)  # Assuming 70% passing
        
        return {
            "total_attempts": len(attempts),
            "completed_attempts": len(attempts),
            "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
            "highest_score": max(scores) if scores else 0.0,
            "lowest_score": min(scores) if scores else 0.0,
            "unique_users": unique_users,
            "pass_rate": round((passing / len(scores)) * 100, 2) if scores else 0.0
        }
    
    def reset_user_progress(self, user_id: str) -> None:
        """
        Reset progress for a user.
        
        Args:
            user_id: ID of the user
        """
        if user_id in self.history:
            del self.history[user_id]
        if user_id in self.attempts:
            del self.attempts[user_id]
        if user_id in self.progress:
            del self.progress[user_id]
    
    def can_retake_quiz(self, user_id: str, quiz_id: str, cooldown_minutes: int = 0) -> Tuple[bool, str]:
        """
        Check if a user can retake a quiz.
        
        Args:
            user_id: ID of the user
            quiz_id: ID of the quiz
            cooldown_minutes: Cooldown period in minutes
        
        Returns:
            Tuple of (can_retake, message)
        """
        if not self.is_quiz_completed(user_id, quiz_id):
            return True, "Quiz not attempted yet"
        
        last_attempt = self.get_last_attempt(user_id, quiz_id)
        if not last_attempt:
            return True, "No previous attempts found"
        
        if cooldown_minutes <= 0:
            return False, "Quiz already completed. Retakes are not allowed."
        
        # Check cooldown
        timestamp = last_attempt.get("timestamp")
        if timestamp:
            last_time = datetime.fromisoformat(timestamp)
            elapsed = (datetime.now() - last_time).total_seconds() / 60
            if elapsed < cooldown_minutes:
                remaining = int(cooldown_minutes - elapsed)
                return False, f"Please wait {remaining} minutes before retaking this quiz."
        
        return True, "Ready to retake"
    
    def get_leaderboard(self, quiz_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get leaderboard for a quiz.
        
        Args:
            quiz_id: ID of the quiz
            limit: Maximum number of entries
        
        Returns:
            List of leaderboard entries
        """
        attempts = []
        for user_id, user_attempts in self.history.items():
            for attempt in user_attempts:
                if attempt.get("quiz_id") == quiz_id and attempt.get("completed", False):
                    attempts.append({
                        "user_id": user_id,
                        "score": attempt.get("score", 0),
                        "timestamp": attempt.get("timestamp"),
                        "time_taken": attempt.get("time_taken", 0)
                    })
        
        # Sort by score (highest first), then by time taken
        attempts.sort(key=lambda x: (-x["score"], x["time_taken"]))
        return attempts[:limit]
    
    def get_quiz_completion_rate(self) -> Dict[str, float]:
        """
        Get overall quiz completion rates.
        
        Returns:
            Dictionary with completion statistics
        """
        total_users = len(self.history)
        if total_users == 0:
            return {
                "average_completion_rate": 0.0,
                "total_users": 0,
                "total_completed_quizzes": 0
            }
        
        total_completed = 0
        for attempts in self.history.values():
            total_completed += sum(1 for a in attempts if a.get("completed", False))
        
        return {
            "average_completion_rate": round((total_completed / total_users) * 100, 2) if total_users > 0 else 0.0,
            "total_users": total_users,
            "total_completed_quizzes": total_completed
        }


# Global instance
_quiz_tracker = None


def get_quiz_tracker() -> QuizTracker:
    """
    Get the global quiz tracker instance.
    
    Returns:
        QuizTracker instance
    """
    global _quiz_tracker
    if _quiz_tracker is None:
        _quiz_tracker = QuizTracker()
    return _quiz_tracker