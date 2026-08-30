"""
Leaderboard Engine for EcoBuddy AI
Manages leaderboards for individual users, teams, and challenges.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
import json

logger = logging.getLogger(__name__)


class LeaderboardType(Enum):
    """Types of leaderboards."""
    INDIVIDUAL = "individual"
    TEAM = "team"
    CHALLENGE = "challenge"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ALL_TIME = "all_time"


class LeaderboardPeriod(Enum):
    """Leaderboard time periods."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    ALL_TIME = "all_time"


@dataclass
class LeaderboardEntry:
    """Data class for a leaderboard entry."""
    rank: int
    user_id: int
    username: str
    score: float
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TeamLeaderboardEntry:
    """Data class for a team leaderboard entry."""
    rank: int
    team_id: str
    team_name: str
    score: float
    members_count: int
    avatar_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LeaderboardEngine:
    """
    Manages leaderboards for individuals, teams, and challenges.
    Supports multiple time periods and real-time updates.
    """
    
    def __init__(self):
        self._individual_leaderboards: Dict[str, List[LeaderboardEntry]] = {}
        self._team_leaderboards: Dict[str, List[TeamLeaderboardEntry]] = {}
        self._last_update: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        self._cache_ttl = 300  # 5 minutes
        
        # Start cache refresh thread
        self._refresh_thread = threading.Thread(target=self._refresh_worker, daemon=True)
        self._refresh_thread.start()
        
        logger.info("LeaderboardEngine initialized")
    
    def get_individual_leaderboard(
        self,
        period: LeaderboardPeriod = LeaderboardPeriod.ALL_TIME,
        limit: int = 50,
        offset: int = 0,
        force_refresh: bool = False
    ) -> List[LeaderboardEntry]:
        """
        Get individual leaderboard.
        
        Args:
            period: Time period
            limit: Maximum number of entries
            offset: Offset for pagination
            force_refresh: Force cache refresh
        
        Returns:
            List of leaderboard entries
        """
        key = f"individual_{period.value}"
        
        if force_refresh or self._should_refresh(key):
            self._refresh_individual_leaderboard(period)
        
        entries = self._individual_leaderboards.get(key, [])
        return entries[offset:offset + limit]
    
    def get_team_leaderboard(
        self,
        period: LeaderboardPeriod = LeaderboardPeriod.ALL_TIME,
        limit: int = 50,
        offset: int = 0,
        force_refresh: bool = False
    ) -> List[TeamLeaderboardEntry]:
        """
        Get team leaderboard.
        
        Args:
            period: Time period
            limit: Maximum number of entries
            offset: Offset for pagination
            force_refresh: Force cache refresh
        
        Returns:
            List of team leaderboard entries
        """
        key = f"team_{period.value}"
        
        if force_refresh or self._should_refresh(key):
            self._refresh_team_leaderboard(period)
        
        entries = self._team_leaderboards.get(key, [])
        return entries[offset:offset + limit]
    
    def get_challenge_leaderboard(
        self,
        challenge_id: str,
        limit: int = 50,
        offset: int = 0,
        force_refresh: bool = False
    ) -> List[LeaderboardEntry]:
        """
        Get challenge leaderboard.
        
        Args:
            challenge_id: Challenge ID
            limit: Maximum number of entries
            offset: Offset for pagination
            force_refresh: Force cache refresh
        
        Returns:
            List of leaderboard entries
        """
        from .challenge_manager import get_challenge_manager
        
        manager = get_challenge_manager()
        challenge = manager.get_challenge(challenge_id)
        
        if not challenge:
            return []
        
        # Get progress from challenge manager
        entries = []
        for user_id in challenge.participants:
            progress = manager.get_user_progress(user_id, challenge_id)
            if progress:
                entries.append(LeaderboardEntry(
                    rank=0,
                    user_id=user_id,
                    username=self._get_username(user_id),
                    score=progress.progress_value,
                    metadata={
                        'completed': progress.completed,
                        'joined_at': progress.joined_at.isoformat()
                    }
                ))
        
        # Sort by score descending
        entries.sort(key=lambda x: x.score, reverse=True)
        
        # Assign ranks
        for i, entry in enumerate(entries):
            entry.rank = i + 1
        
        return entries[offset:offset + limit]
    
    def get_user_rank(
        self,
        user_id: int,
        period: LeaderboardPeriod = LeaderboardPeriod.ALL_TIME
    ) -> Optional[int]:
        """
        Get a user's rank on the leaderboard.
        
        Args:
            user_id: User ID
            period: Time period
        
        Returns:
            Rank or None if not found
        """
        entries = self.get_individual_leaderboard(period, limit=1000)
        
        for entry in entries:
            if entry.user_id == user_id:
                return entry.rank
        
        return None
    
    def get_team_rank(
        self,
        team_id: str,
        period: LeaderboardPeriod = LeaderboardPeriod.ALL_TIME
    ) -> Optional[int]:
        """
        Get a team's rank on the leaderboard.
        
        Args:
            team_id: Team ID
            period: Time period
        
        Returns:
            Rank or None if not found
        """
        entries = self.get_team_leaderboard(period, limit=1000)
        
        for entry in entries:
            if entry.team_id == team_id:
                return entry.rank
        
        return None
    
    def _refresh_individual_leaderboard(self, period: LeaderboardPeriod) -> None:
        """Refresh individual leaderboard."""
        try:
            from database import get_assessments, get_all_users
            
            users = get_all_users()
            entries = []
            
            for user in users:
                user_id = user['id']
                score = self._calculate_user_score(user_id, period)
                
                if score > 0:
                    entries.append(LeaderboardEntry(
                        rank=0,
                        user_id=user_id,
                        username=user.get('username', f'User_{user_id}'),
                        score=score,
                        display_name=user.get('display_name'),
                        avatar_url=user.get('avatar_url')
                    ))
            
            # Sort by score descending
            entries.sort(key=lambda x: x.score, reverse=True)
            
            # Assign ranks
            for i, entry in enumerate(entries):
                entry.rank = i + 1
            
            key = f"individual_{period.value}"
            self._individual_leaderboards[key] = entries
            self._last_update[key] = datetime.now()
            
            logger.info(f"Refreshed individual leaderboard for period {period.value}")
            
        except Exception as e:
            logger.error(f"Failed to refresh individual leaderboard: {e}")
    
    def _refresh_team_leaderboard(self, period: LeaderboardPeriod) -> None:
        """Refresh team leaderboard."""
        try:
            from .team_manager import get_team_manager
            
            manager = get_team_manager()
            teams = manager.get_all_teams()
            
            entries = []
            for team in teams:
                score = self._calculate_team_score(team.id, period)
                
                if score > 0:
                    entries.append(TeamLeaderboardEntry(
                        rank=0,
                        team_id=team.id,
                        team_name=team.name,
                        score=score,
                        members_count=len(team.members),
                        avatar_url=team.avatar_url
                    ))
            
            # Sort by score descending
            entries.sort(key=lambda x: x.score, reverse=True)
            
            # Assign ranks
            for i, entry in enumerate(entries):
                entry.rank = i + 1
            
            key = f"team_{period.value}"
            self._team_leaderboards[key] = entries
            self._last_update[key] = datetime.now()
            
            logger.info(f"Refreshed team leaderboard for period {period.value}")
            
        except Exception as e:
            logger.error(f"Failed to refresh team leaderboard: {e}")
    
    def _calculate_user_score(self, user_id: int, period: LeaderboardPeriod) -> float:
        """Calculate a user's score for a specific period."""
        try:
            from database import get_assessments
            
            assessments = get_assessments(user_id)
            
            if not assessments:
                return 0.0
            
            # Filter by period
            now = datetime.now()
            filtered = []
            
            for assessment in assessments:
                date = assessment.get('date')
                if isinstance(date, str):
                    date = datetime.fromisoformat(date)
                
                if period == LeaderboardPeriod.ALL_TIME:
                    filtered.append(assessment)
                elif period == LeaderboardPeriod.YEARLY:
                    if date and date.year == now.year:
                        filtered.append(assessment)
                elif period == LeaderboardPeriod.MONTHLY:
                    if date and date.month == now.month and date.year == now.year:
                        filtered.append(assessment)
                elif period == LeaderboardPeriod.WEEKLY:
                    week_ago = now - timedelta(days=7)
                    if date and date >= week_ago:
                        filtered.append(assessment)
                elif period == LeaderboardPeriod.DAILY:
                    if date and date.date() == now.date():
                        filtered.append(assessment)
            
            if not filtered:
                return 0.0
            
            # Calculate score (average eco_score + bonus for consistency)
            total_score = sum(a.get('eco_score', 0) for a in filtered)
            avg_score = total_score / len(filtered)
            
            # Bonus for consistency (lower standard deviation = higher bonus)
            scores = [a.get('eco_score', 0) for a in filtered]
            if len(scores) > 1:
                import statistics
                std = statistics.stdev(scores) if len(scores) > 1 else 0
                consistency_bonus = max(0, 10 - std)  # Up to 10 bonus points
            else:
                consistency_bonus = 0
            
            # Bonus for streak
            streak_bonus = self._calculate_streak_bonus(user_id, period)
            
            return avg_score + consistency_bonus + streak_bonus
            
        except Exception as e:
            logger.error(f"Failed to calculate user score: {e}")
            return 0.0
    
    def _calculate_team_score(self, team_id: str, period: LeaderboardPeriod) -> float:
        """Calculate a team's score for a specific period."""
        try:
            from .team_manager import get_team_manager
            
            manager = get_team_manager()
            team = manager.get_team(team_id)
            
            if not team:
                return 0.0
            
            # Average of member scores
            total_score = 0
            count = 0
            
            for user_id in team.members.keys():
                score = self._calculate_user_score(user_id, period)
                total_score += score
                count += 1
            
            return total_score / count if count > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Failed to calculate team score: {e}")
            return 0.0
    
    def _calculate_streak_bonus(self, user_id: int, period: LeaderboardPeriod) -> float:
        """Calculate streak bonus for a user."""
        try:
            from database import get_assessments
            
            assessments = get_assessments(user_id)
            
            if len(assessments) < 2:
                return 0.0
            
            # Calculate current streak
            streak = 1
            dates = []
            for assessment in assessments:
                date = assessment.get('date')
                if isinstance(date, str):
                    date = datetime.fromisoformat(date)
                if date:
                    dates.append(date)
            
            dates.sort(reverse=True)
            
            for i in range(1, len(dates)):
                diff = (dates[i-1] - dates[i]).days
                if diff <= 7:
                    streak += 1
                else:
                    break
            
            # Bonus: 0.5 points per day of streak, max 15
            return min(streak * 0.5, 15.0)
            
        except Exception as e:
            logger.error(f"Failed to calculate streak bonus: {e}")
            return 0.0
    
    def _get_username(self, user_id: int) -> str:
        """Get username from database."""
        try:
            from database import get_user_by_id
            user = get_user_by_id(user_id)
            return user.get('username', f'User_{user_id}') if user else f'User_{user_id}'
        except:
            return f'User_{user_id}'
    
    def _should_refresh(self, key: str) -> bool:
        """Check if cache should be refreshed."""
        last_update = self._last_update.get(key)
        if not last_update:
            return True
        
        return (datetime.now() - last_update).seconds > self._cache_ttl
    
    def _refresh_worker(self) -> None:
        """Background worker for refreshing leaderboards."""
        while True:
            try:
                time.sleep(60)  # Check every minute
                now = datetime.now()
                
                # Refresh only if cache is stale
                for key in list(self._last_update.keys()):
                    if self._should_refresh(key):
                        if key.startswith('individual_'):
                            period = LeaderboardPeriod(key.replace('individual_', ''))
                            self._refresh_individual_leaderboard(period)
                        elif key.startswith('team_'):
                            period = LeaderboardPeriod(key.replace('team_', ''))
                            self._refresh_team_leaderboard(period)
                            
            except Exception as e:
                logger.error(f"Refresh worker error: {e}")
    
    def force_refresh_all(self) -> None:
        """Force refresh all leaderboards."""
        for period in LeaderboardPeriod:
            self._refresh_individual_leaderboard(period)
            self._refresh_team_leaderboard(period)
    
    def get_leaderboard_statistics(self) -> Dict[str, Any]:
        """Get leaderboard statistics."""
        stats = {
            'individual_leaderboards': len(self._individual_leaderboards),
            'team_leaderboards': len(self._team_leaderboards),
            'last_update': max(self._last_update.values()) if self._last_update else None,
            'cache_ttl': self._cache_ttl
        }
        
        return stats


# Global leaderboard engine instance
_leaderboard_engine: Optional[LeaderboardEngine] = None
_leaderboard_engine_lock = threading.Lock()


def get_leaderboard_engine() -> LeaderboardEngine:
    """Get or create global leaderboard engine instance."""
    global _leaderboard_engine
    with _leaderboard_engine_lock:
        if _leaderboard_engine is None:
            _leaderboard_engine = LeaderboardEngine()
        return _leaderboard_engine


def get_individual_leaderboard(
    period: LeaderboardPeriod = LeaderboardPeriod.ALL_TIME,
    limit: int = 50,
    offset: int = 0
) -> List[LeaderboardEntry]:
    """Convenience function to get individual leaderboard."""
    engine = get_leaderboard_engine()
    return engine.get_individual_leaderboard(period, limit, offset)


def get_team_leaderboard(
    period: LeaderboardPeriod = LeaderboardPeriod.ALL_TIME,
    limit: int = 50,
    offset: int = 0
) -> List[TeamLeaderboardEntry]:
    """Convenience function to get team leaderboard."""
    engine = get_leaderboard_engine()
    return engine.get_team_leaderboard(period, limit, offset)


def get_user_rank(user_id: int, period: LeaderboardPeriod = LeaderboardPeriod.ALL_TIME) -> Optional[int]:
    """Convenience function to get user rank."""
    engine = get_leaderboard_engine()
    return engine.get_user_rank(user_id, period)