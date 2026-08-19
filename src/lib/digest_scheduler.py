"""
Weekly Eco-Tips Digest Scheduler
Handles scheduling and sending of weekly digests.
"""

import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import streamlit as st
from src.lib.email_service import get_email_service, WeeklyDigestData
from src.lib.eco_tips_digest import EcoTipsDigestGenerator, UserPreferences

logger = logging.getLogger(__name__)


class DigestScheduler:
    """
    Scheduler for weekly eco-tips digest.
    """
    
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_run: Optional[datetime] = None
        self._digest_count = 0
    
    def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Digest scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Digest scheduler stopped")
    
    def _run(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                now = datetime.now()
                
                # Check if it's Monday at 9:00 AM
                if now.weekday() == 0 and now.hour == 9 and now.minute < 5:
                    self._send_weekly_digests()
                    self._last_run = now
                    self._digest_count += 1
                    logger.info(f"Weekly digest sent at {now}")
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def _send_weekly_digests(self) -> None:
        """Send weekly digests to all subscribed users."""
        # In production, get users from database
        users = self._get_subscribed_users()
        
        service = get_email_service()
        generator = EcoTipsDigestGenerator()
        
        for user in users:
            try:
                preferences = user.get("preferences", UserPreferences())
                digest = generator.generate_digest(user, preferences)
                success, message = service.send_weekly_digest(digest)
                
                if success:
                    logger.info(f"Digest sent to {user.get('email')}")
                    self._record_digest_sent(user.get('id'), digest)
                else:
                    logger.error(f"Failed to send digest to {user.get('email')}: {message}")
                    
            except Exception as e:
                logger.error(f"Error sending digest to {user.get('email')}: {e}")
    
    def _get_subscribed_users(self) -> List[Dict[str, Any]]:
        """Get users subscribed to weekly digest."""
        # This should be replaced with database query
        # For now, return sample users
        return [
            {
                "id": 1,
                "email": "user1@example.com",
                "name": "User One",
                "eco_score": 75,
                "total_footprint": 3500,
                "streak_days": 12,
                "total_assessments": 8,
                "contributors": {
                    "Transport": 1200,
                    "Electricity": 800,
                    "Food": 600,
                    "Waste": 400
                },
                "preferences": UserPreferences()
            }
        ]
    
    def _record_digest_sent(self, user_id: int, digest: WeeklyDigestData) -> None:
        """Record that a digest was sent to a user."""
        # In production, save to database
        logger.info(f"Digest recorded for user {user_id}")


# Global scheduler instance
_scheduler: Optional[DigestScheduler] = None


def get_scheduler() -> DigestScheduler:
    """Get global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = DigestScheduler()
    return _scheduler


def start_digest_scheduler() -> None:
    """Start the digest scheduler."""
    scheduler = get_scheduler()
    scheduler.start()


def stop_digest_scheduler() -> None:
    """Stop the digest scheduler."""
    scheduler = get_scheduler()
    scheduler.stop()


def send_digest_now(user_id: int) -> bool:
    """
    Send a digest immediately to a user.
    
    Args:
        user_id: User ID
    
    Returns:
        True if sent successfully
    """
    # Get user data from database
    # For now, use sample data
    user_data = {
        "id": user_id,
        "email": st.session_state.get("user_email", "test@example.com"),
        "name": st.session_state.get("username", "Eco Warrior"),
        "eco_score": 75,
        "total_footprint": 3500,
        "streak_days": 12,
        "total_assessments": 8,
        "contributors": {
            "Transport": 1200,
            "Electricity": 800,
            "Food": 600,
            "Waste": 400
        }
    }
    
    try:
        service = get_email_service()
        generator = EcoTipsDigestGenerator()
        preferences = st.session_state.get("digest_preferences", UserPreferences())
        digest = generator.generate_digest(user_data, preferences)
        success, message = service.send_weekly_digest(digest)
        
        if success:
            st.success("✅ Digest sent successfully!")
            return True
        else:
            st.error(f"❌ Failed to send digest: {message}")
            return False
            
    except Exception as e:
        st.error(f"❌ Error sending digest: {str(e)}")
        return False