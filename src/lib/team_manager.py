"""
Team Manager for EcoBuddy AI
Manages teams, team memberships, and team-based challenges.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class TeamRole(Enum):
    """Team member roles."""
    CAPTAIN = "captain"
    CO_CAPTAIN = "co_captain"
    MEMBER = "member"


class TeamStatus(Enum):
    """Team status states."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


@dataclass
class TeamMember:
    """Data class for a team member."""
    user_id: int
    role: TeamRole
    joined_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    contributions: float = 0.0


@dataclass
class Team:
    """Data class for a team."""
    id: str
    name: str
    description: str
    status: TeamStatus
    created_by: int
    created_at: datetime
    members: Dict[int, TeamMember] = field(default_factory=dict)
    max_members: int = 10
    is_private: bool = False
    tags: List[str] = field(default_factory=list)
    avatar_url: Optional[str] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert team to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'members': {
                user_id: {
                    'role': member.role.value,
                    'joined_at': member.joined_at.isoformat(),
                    'last_active': member.last_active.isoformat(),
                    'contributions': member.contributions
                }
                for user_id, member in self.members.items()
            },
            'max_members': self.max_members,
            'is_private': self.is_private,
            'tags': self.tags,
            'avatar_url': self.avatar_url,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Team':
        """Create team from dictionary."""
        members = {}
        for user_id, member_data in data.get('members', {}).items():
            members[int(user_id)] = TeamMember(
                user_id=int(user_id),
                role=TeamRole(member_data['role']),
                joined_at=datetime.fromisoformat(member_data['joined_at']),
                last_active=datetime.fromisoformat(member_data['last_active']),
                contributions=member_data.get('contributions', 0.0)
            )
        
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            status=TeamStatus(data['status']),
            created_by=data['created_by'],
            created_at=datetime.fromisoformat(data['created_at']),
            members=members,
            max_members=data.get('max_members', 10),
            is_private=data.get('is_private', False),
            tags=data.get('tags', []),
            avatar_url=data.get('avatar_url'),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )


class TeamManager:
    """
    Manages teams, team memberships, and team activities.
    """
    
    def __init__(self):
        self._teams: Dict[str, Team] = {}
        self._user_teams: Dict[int, List[str]] = {}  # user_id -> team_ids
        self._lock = threading.Lock()
        self._team_counter = 0
        
        logger.info("TeamManager initialized")
    
    def _generate_id(self) -> str:
        """Generate unique team ID."""
        self._team_counter += 1
        timestamp = int(time.time() * 1000)
        return f"team_{timestamp}_{self._team_counter}"
    
    def create_team(
        self,
        name: str,
        description: str,
        created_by: int,
        max_members: int = 10,
        is_private: bool = False,
        **kwargs
    ) -> Team:
        """
        Create a new team.
        
        Args:
            name: Team name
            description: Team description
            created_by: User ID of creator
            max_members: Maximum team members
            is_private: Whether team is private
            **kwargs: Additional fields
        
        Returns:
            Team object
        """
        team = Team(
            id=self._generate_id(),
            name=name,
            description=description,
            status=TeamStatus.ACTIVE,
            created_by=created_by,
            created_at=datetime.now(),
            max_members=max_members,
            is_private=is_private,
            tags=kwargs.get('tags', []),
            avatar_url=kwargs.get('avatar_url')
        )
        
        # Add creator as captain
        team.members[created_by] = TeamMember(
            user_id=created_by,
            role=TeamRole.CAPTAIN
        )
        
        with self._lock:
            self._teams[team.id] = team
            if created_by not in self._user_teams:
                self._user_teams[created_by] = []
            self._user_teams[created_by].append(team.id)
        
        logger.info(f"Created team: {name} by user {created_by}")
        return team
    
    def get_team(self, team_id: str) -> Optional[Team]:
        """Get a team by ID."""
        return self._teams.get(team_id)
    
    def get_all_teams(
        self,
        status: Optional[TeamStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Team]:
        """Get all teams with filters."""
        teams = list(self._teams.values())
        
        if status:
            teams = [t for t in teams if t.status == status]
        
        # Sort by created_at (newest first)
        teams.sort(key=lambda t: t.created_at, reverse=True)
        
        return teams[offset:offset + limit]
    
    def get_user_teams(self, user_id: int) -> List[Team]:
        """Get all teams a user belongs to."""
        team_ids = self._user_teams.get(user_id, [])
        return [self._teams[tid] for tid in team_ids if tid in self._teams]
    
    def get_team_members(self, team_id: str) -> List[Dict[str, Any]]:
        """Get all members of a team."""
        team = self._teams.get(team_id)
        if not team:
            return []
        
        members = []
        for user_id, member in team.members.items():
            members.append({
                'user_id': user_id,
                'username': self._get_username(user_id),
                'role': member.role.value,
                'joined_at': member.joined_at,
                'last_active': member.last_active,
                'contributions': member.contributions
            })
        
        return members
    
    def _get_username(self, user_id: int) -> str:
        """Get username from database."""
        try:
            from database import get_user_by_id
            user = get_user_by_id(user_id)
            return user.get('username', f'User_{user_id}') if user else f'User_{user_id}'
        except:
            return f'User_{user_id}'
    
    def join_team(self, team_id: str, user_id: int) -> bool:
        """Join a team."""
        with self._lock:
            team = self._teams.get(team_id)
            if not team:
                return False
            
            if team.status != TeamStatus.ACTIVE:
                return False
            
            if user_id in team.members:
                return False
            
            if len(team.members) >= team.max_members:
                return False
            
            team.members[user_id] = TeamMember(
                user_id=user_id,
                role=TeamRole.MEMBER
            )
            
            if user_id not in self._user_teams:
                self._user_teams[user_id] = []
            self._user_teams[user_id].append(team_id)
            
            logger.info(f"User {user_id} joined team {team_id}")
            return True
    
    def leave_team(self, team_id: str, user_id: int) -> bool:
        """Leave a team."""
        with self._lock:
            team = self._teams.get(team_id)
            if not team:
                return False
            
            if user_id not in team.members:
                return False
            
            # Check if user is captain
            if team.members[user_id].role == TeamRole.CAPTAIN:
                # Transfer captaincy or dissolve team
                if len(team.members) > 1:
                    # Transfer to next member
                    next_member = next(iter(team.members.keys()))
                    team.members[next_member].role = TeamRole.CAPTAIN
                else:
                    # Only member left, delete team
                    del self._teams[team_id]
                    self._user_teams.pop(user_id, None)
                    logger.info(f"Team {team_id} dissolved")
                    return True
            
            del team.members[user_id]
            
            if user_id in self._user_teams:
                self._user_teams[user_id] = [tid for tid in self._user_teams[user_id] if tid != team_id]
            
            logger.info(f"User {user_id} left team {team_id}")
            return True
    
    def update_member_role(self, team_id: str, user_id: int, role: TeamRole) -> bool:
        """Update a member's role."""
        with self._lock:
            team = self._teams.get(team_id)
            if not team:
                return False
            
            if user_id not in team.members:
                return False
            
            team.members[user_id].role = role
            team.updated_at = datetime.now()
            return True
    
    def update_team(self, team_id: str, **kwargs) -> Optional[Team]:
        """Update team details."""
        with self._lock:
            team = self._teams.get(team_id)
            if not team:
                return None
            
            for key, value in kwargs.items():
                if hasattr(team, key):
                    setattr(team, key, value)
            
            team.updated_at = datetime.now()
            return team
    
    def delete_team(self, team_id: str) -> bool:
        """Delete a team."""
        with self._lock:
            team = self._teams.get(team_id)
            if not team:
                return False
            
            # Remove team from all users
            for user_id in team.members.keys():
                if user_id in self._user_teams:
                    self._user_teams[user_id] = [tid for tid in self._user_teams[user_id] if tid != team_id]
            
            del self._teams[team_id]
            logger.info(f"Deleted team {team_id}")
            return True
    
    def get_team_statistics(self, team_id: str) -> Dict[str, Any]:
        """Get team statistics."""
        team = self._teams.get(team_id)
        if not team:
            return {}
        
        members = team.members
        
        return {
            'total_members': len(members),
            'max_members': team.max_members,
            'roles': {
                'captain': sum(1 for m in members.values() if m.role == TeamRole.CAPTAIN),
                'co_captain': sum(1 for m in members.values() if m.role == TeamRole.CO_CAPTAIN),
                'member': sum(1 for m in members.values() if m.role == TeamRole.MEMBER)
            },
            'total_contributions': sum(m.contributions for m in members.values()),
            'average_contributions': sum(m.contributions for m in members.values()) / len(members) if members else 0,
            'last_active': max(m.last_active for m in members.values()) if members else None
        }
    
    def get_team_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get team leaderboard based on contributions."""
        teams_with_contributions = []
        
        for team in self._teams.values():
            if team.status != TeamStatus.ACTIVE:
                continue
            
            total_contributions = sum(m.contributions for m in team.members.values())
            teams_with_contributions.append({
                'team_id': team.id,
                'team_name': team.name,
                'total_contributions': total_contributions,
                'members_count': len(team.members),
                'average': total_contributions / len(team.members) if team.members else 0
            })
        
        teams_with_contributions.sort(key=lambda x: x['total_contributions'], reverse=True)
        return teams_with_contributions[:limit]
    
    def get_team_stats(self) -> Dict[str, Any]:
        """Get team manager statistics."""
        stats = {
            'total_teams': len(self._teams),
            'by_status': {},
            'total_members': 0,
            'average_team_size': 0
        }
        
        total_members = 0
        for team in self._teams.values():
            stats['by_status'][team.status.value] = stats['by_status'].get(team.status.value, 0) + 1
            total_members += len(team.members)
        
        stats['total_members'] = total_members
        stats['average_team_size'] = total_members / len(self._teams) if self._teams else 0
        
        return stats


# Global team manager instance
_team_manager: Optional[TeamManager] = None
_team_manager_lock = threading.Lock()


def get_team_manager() -> TeamManager:
    """Get or create global team manager instance."""
    global _team_manager
    with _team_manager_lock:
        if _team_manager is None:
            _team_manager = TeamManager()
        return _team_manager


def create_team(
    name: str,
    description: str,
    created_by: int,
    max_members: int = 10,
    is_private: bool = False,
    **kwargs
) -> Team:
    """Convenience function to create a team."""
    manager = get_team_manager()
    return manager.create_team(name, description, created_by, max_members, is_private, **kwargs)


def join_team(team_id: str, user_id: int) -> bool:
    """Convenience function to join a team."""
    manager = get_team_manager()
    return manager.join_team(team_id, user_id)


def get_user_teams(user_id: int) -> List[Team]:
    """Convenience function to get user teams."""
    manager = get_team_manager()
    return manager.get_user_teams(user_id)