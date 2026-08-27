"""
Notification Data Models.

Defines the core data structures for the Notification Engine, including preferences,
templates, delivery logs, and the notification payloads themselves.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Dict, Any, List, Optional, Union, Tuple
import json

@dataclass
class NotificationPreference:
    """User preferences for receiving notifications."""
    user_id: int
    email_enabled: bool = True
    in_app_enabled: bool = True
    push_enabled: bool = False
    quiet_hours_start: Optional[time] = None
    quiet_hours_end: Optional[time] = None
    timezone: str = "UTC"
    opted_out_categories: List[str] = field(default_factory=list)
    daily_digest_enabled: bool = False
    weekly_digest_enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email_enabled": self.email_enabled,
            "in_app_enabled": self.in_app_enabled,
            "push_enabled": self.push_enabled,
            "quiet_hours_start": self.quiet_hours_start.strftime('%H:%M') if self.quiet_hours_start else None,
            "quiet_hours_end": self.quiet_hours_end.strftime('%H:%M') if self.quiet_hours_end else None,
            "timezone": self.timezone,
            "opted_out_categories": self.opted_out_categories,
            "daily_digest_enabled": self.daily_digest_enabled,
            "weekly_digest_enabled": self.weekly_digest_enabled
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationPreference':
        start = data.get("quiet_hours_start")
        end = data.get("quiet_hours_end")
        return cls(
            user_id=data["user_id"],
            email_enabled=bool(data.get("email_enabled", True)),
            in_app_enabled=bool(data.get("in_app_enabled", True)),
            push_enabled=bool(data.get("push_enabled", False)),
            quiet_hours_start=datetime.strptime(start, '%H:%M').time() if start else None,
            quiet_hours_end=datetime.strptime(end, '%H:%M').time() if end else None,
            timezone=data.get("timezone", "UTC"),
            opted_out_categories=data.get("opted_out_categories", []),
            daily_digest_enabled=bool(data.get("daily_digest_enabled", False)),
            weekly_digest_enabled=bool(data.get("weekly_digest_enabled", True))
        )

@dataclass
class NotificationTemplate:
    """Reusable template for generating notifications."""
    template_id: str
    category: str
    title_template: str
    body_template: str
    default_priority: str = "normal"
    action_url: Optional[str] = None
    icon: str = "🔔"
    
    def render(self, context: Dict[str, Any]) -> Tuple[str, str]:
        """Safely formats the title and body using the provided context."""
        try:
            rendered_title = self.title_template.format(**context)
            rendered_body = self.body_template.format(**context)
            return rendered_title, rendered_body
        except KeyError as e:
            raise ValueError(f"Missing context variable for template {self.template_id}: {e}")

@dataclass
class NotificationPayload:
    """The actual instance of a notification to be delivered."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: int = 0
    category: str = "general"
    title: str = ""
    message: str = ""
    priority: str = "normal"  # low, normal, high, urgent
    status: str = "pending"  # pending, sent, read, failed, scheduled, archived
    action_url: Optional[str] = None
    icon: str = "🔔"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_for: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    retry_count: int = 0
    error_log: Optional[str] = None
    dedupe_key: Optional[str] = None
    
    def to_db_tuple(self) -> tuple:
        return (
            self.id, self.user_id, self.category, self.title, self.message,
            self.priority, self.status, self.action_url, self.icon,
            json.dumps(self.metadata),
            self.created_at.isoformat() if self.created_at else None,
            self.scheduled_for.isoformat() if self.scheduled_for else None,
            self.sent_at.isoformat() if self.sent_at else None,
            self.read_at.isoformat() if self.read_at else None,
            self.expires_at.isoformat() if self.expires_at else None,
            self.retry_count, self.error_log, self.dedupe_key
        )
        
    @classmethod
    def from_db_row(cls, row: tuple) -> 'NotificationPayload':
        return cls(
            id=row[0],
            user_id=row[1],
            category=row[2],
            title=row[3],
            message=row[4],
            priority=row[5],
            status=row[6],
            action_url=row[7],
            icon=row[8],
            metadata=json.loads(row[9]) if row[9] else {},
            created_at=datetime.fromisoformat(row[10]) if row[10] else None,
            scheduled_for=datetime.fromisoformat(row[11]) if row[11] else None,
            sent_at=datetime.fromisoformat(row[12]) if row[12] else None,
            read_at=datetime.fromisoformat(row[13]) if row[13] else None,
            expires_at=datetime.fromisoformat(row[14]) if row[14] else None,
            retry_count=row[15],
            error_log=row[16],
            dedupe_key=row[17]
        )
