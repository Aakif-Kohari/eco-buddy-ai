"""
Notification Templates for EcoBuddy AI
Stores and manages notification templates for all notification types.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class NotificationTemplate:
    """Data class for a notification template."""
    key: str
    type: str
    title: str
    message_template: str
    priority: str  # critical, high, medium, low, info
    action_label: Optional[str] = None
    action_url: Optional[str] = None
    category: str = "general"
    variables: List[str] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class NotificationTemplateManager:
    """
    Manages notification templates with variable substitution.
    """
    
    def __init__(self):
        self._templates: Dict[str, NotificationTemplate] = {}
        self._load_default_templates()
        self._custom_templates: Dict[str, NotificationTemplate] = {}
        
        logger.info("NotificationTemplateManager initialized")
    
    def _load_default_templates(self) -> None:
        """Load default notification templates."""
        defaults = [
            # Alert Templates
            NotificationTemplate(
                key="carbon_budget_exceeded",
                type="alert",
                title="⚠️ Carbon Budget Alert",
                message_template="You have exceeded {percentage}% of your monthly carbon budget. Current usage: {usage:.1f} kg CO₂.",
                priority="critical",
                action_label="View Budget",
                action_url="/budget",
                category="carbon_budget",
                variables=["percentage", "usage", "budget", "remaining"]
            ),
            NotificationTemplate(
                key="carbon_budget_warning",
                type="alert",
                title="⚠️ Carbon Budget Warning",
                message_template="You have used {percentage}% of your monthly carbon budget. Remaining: {remaining:.1f} kg CO₂.",
                priority="high",
                action_label="View Budget",
                action_url="/budget",
                category="carbon_budget",
                variables=["percentage", "usage", "budget", "remaining"]
            ),
            NotificationTemplate(
                key="footprint_spike",
                type="alert",
                title="📈 Footprint Spike Detected",
                message_template="Your carbon footprint increased by {increase:.1f}% compared to your average.",
                priority="high",
                action_label="View Details",
                action_url="/analytics",
                category="footprint",
                variables=["increase", "current", "average", "date"]
            ),
            NotificationTemplate(
                key="streak_at_risk",
                type="alert",
                title="🔥 Streak at Risk!",
                message_template="You haven't logged an assessment in {days} days. Your {streak} day streak is at risk!",
                priority="high",
                action_label="Log Now",
                action_url="/assessment",
                category="streak",
                variables=["days", "streak", "last_assessment"]
            ),
            
            # Achievement Templates
            NotificationTemplate(
                key="new_badge",
                type="achievement",
                title="🏆 New Badge Unlocked!",
                message_template="You earned the '{badge_name}' badge for {reason}!",
                priority="medium",
                action_label="View Badges",
                action_url="/badges",
                category="achievement",
                variables=["badge_name", "reason", "badge_icon"]
            ),
            NotificationTemplate(
                key="level_up",
                type="achievement",
                title="🎉 Level Up!",
                message_template="Congratulations! You reached Level {level} with {xp} XP!",
                priority="medium",
                action_label="View Profile",
                action_url="/profile",
                category="achievement",
                variables=["level", "xp", "next_level", "progress"]
            ),
            NotificationTemplate(
                key="milestone_reached",
                type="achievement",
                title="🎯 Milestone Reached!",
                message_template="You completed {count} assessments! Keep up the great work!",
                priority="medium",
                action_label="View History",
                action_url="/history",
                category="achievement",
                variables=["count", "next_milestone", "total_footprint"]
            ),
            
            # Progress Templates
            NotificationTemplate(
                key="weekly_summary",
                type="progress",
                title="📊 Weekly Progress Summary",
                message_template="This week: {footprint_change}% change in footprint. You completed {assessments} assessments.",
                priority="low",
                action_label="View Report",
                action_url="/weekly_report",
                category="progress",
                variables=["footprint_change", "assessments", "score_change", "week"]
            ),
            NotificationTemplate(
                key="monthly_summary",
                type="progress",
                title="📈 Monthly Progress Report",
                message_template="This month: You reduced your footprint by {reduction:.1f}%. Average score: {score:.0f}/100.",
                priority="low",
                action_label="View Report",
                action_url="/monthly_report",
                category="progress",
                variables=["reduction", "score", "assessments", "month"]
            ),
            NotificationTemplate(
                key="improvement_detected",
                type="progress",
                title="🌟 Improvement Detected!",
                message_template="Your carbon footprint has improved by {improvement:.1f}% compared to last {period}.",
                priority="medium",
                action_label="View Details",
                action_url="/analytics",
                category="progress",
                variables=["improvement", "period", "current", "previous"]
            ),
            
            # Reminder Templates
            NotificationTemplate(
                key="assessment_reminder",
                type="reminder",
                title="🌱 Assessment Reminder",
                message_template="It's been {days} days since your last assessment. Log your impact today!",
                priority="low",
                action_label="Start Assessment",
                action_url="/assessment",
                category="reminder",
                variables=["days", "last_date", "streak"]
            ),
            NotificationTemplate(
                key="budget_checkin",
                type="reminder",
                title="💰 Budget Check-in",
                message_template="You've used {percentage}% of your monthly carbon budget. Keep tracking!",
                priority="medium",
                action_label="View Budget",
                action_url="/budget",
                category="reminder",
                variables=["percentage", "usage", "budget", "days_left"]
            ),
            NotificationTemplate(
                key="goal_reminder",
                type="reminder",
                title="🎯 Goal Reminder",
                message_template="You're {progress}% towards your goal of {goal} kg CO₂. Keep going!",
                priority="medium",
                action_label="View Goals",
                action_url="/goals",
                category="reminder",
                variables=["progress", "goal", "current", "deadline"]
            ),
            
            # Challenge Templates
            NotificationTemplate(
                key="challenge_start",
                type="challenge",
                title="🏁 New Challenge Started!",
                message_template="The '{challenge_name}' challenge has started. Complete it to earn {xp} XP!",
                priority="medium",
                action_label="View Challenge",
                action_url="/challenges",
                category="challenge",
                variables=["challenge_name", "xp", "duration", "deadline"]
            ),
            NotificationTemplate(
                key="challenge_progress",
                type="challenge",
                title="📊 Challenge Progress",
                message_template="You're {progress}% through the '{challenge_name}' challenge. Keep going!",
                priority="low",
                action_label="View Challenge",
                action_url="/challenges",
                category="challenge",
                variables=["challenge_name", "progress", "remaining_days", "target"]
            ),
            NotificationTemplate(
                key="challenge_completed",
                type="challenge",
                title="🎉 Challenge Completed!",
                message_template="You completed the '{challenge_name}' challenge! Earned {xp} XP!",
                priority="high",
                action_label="View Rewards",
                action_url="/rewards",
                category="challenge",
                variables=["challenge_name", "xp", "rank", "rewards"]
            ),
            
            # Social Templates
            NotificationTemplate(
                key="new_follower",
                type="social",
                title="👤 New Follower",
                message_template="{username} started following you!",
                priority="low",
                action_label="View Profile",
                action_url="/profile",
                category="social",
                variables=["username", "user_id", "avatar"]
            ),
            NotificationTemplate(
                key="community_achievement",
                type="social",
                title="🏆 Community Achievement",
                message_template="Your team '{team_name}' reached a new milestone!",
                priority="medium",
                action_label="View Team",
                action_url="/team",
                category="social",
                variables=["team_name", "milestone", "achievement", "rank"]
            ),
            NotificationTemplate(
                key="shared_insight",
                type="social",
                title="💡 Shared Insight",
                message_template="{username} shared an insight about sustainability with you!",
                priority="low",
                action_label="View Insight",
                action_url="/insights",
                category="social",
                variables=["username", "insight_title", "insight_type"]
            ),
            
            # System Templates
            NotificationTemplate(
                key="maintenance",
                type="system",
                title="🔧 System Maintenance",
                message_template="EcoBuddy AI will be undergoing maintenance on {date}. Downtime: ~{duration} minutes.",
                priority="info",
                action_label="Learn More",
                action_url="/status",
                category="system",
                variables=["date", "duration", "time", "features_affected"]
            ),
            NotificationTemplate(
                key="feature_update",
                type="system",
                title="🚀 New Feature Available!",
                message_template="{feature_name} is now available. Check it out!",
                priority="info",
                action_label="Explore",
                action_url="/features",
                category="system",
                variables=["feature_name", "feature_description", "release_date"]
            )
        ]
        
        for template in defaults:
            self._templates[template.key] = template
    
    def get_template(self, key: str) -> Optional[NotificationTemplate]:
        """Get a template by key."""
        return self._templates.get(key) or self._custom_templates.get(key)
    
    def get_templates_by_type(self, type: str) -> List[NotificationTemplate]:
        """Get all templates of a specific type."""
        return [
            t for t in self._templates.values()
            if t.type == type and t.enabled
        ]
    
    def get_templates_by_category(self, category: str) -> List[NotificationTemplate]:
        """Get all templates in a category."""
        return [
            t for t in self._templates.values()
            if t.category == category and t.enabled
        ]
    
    def add_template(self, template: NotificationTemplate) -> bool:
        """
        Add a custom template.
        
        Args:
            template: NotificationTemplate object
        
        Returns:
            True if added successfully
        """
        if template.key in self._templates:
            logger.warning(f"Template {template.key} already exists in defaults")
            return False
        
        self._custom_templates[template.key] = template
        logger.info(f"Added custom template {template.key}")
        return True
    
    def update_template(self, key: str, **kwargs) -> Optional[NotificationTemplate]:
        """
        Update an existing template.
        
        Args:
            key: Template key
            **kwargs: Fields to update
        
        Returns:
            Updated template or None
        """
        template = self.get_template(key)
        if not template:
            return None
        
        for field, value in kwargs.items():
            if hasattr(template, field):
                setattr(template, field, value)
        
        logger.info(f"Updated template {key}")
        return template
    
    def delete_template(self, key: str) -> bool:
        """Delete a custom template."""
        if key in self._custom_templates:
            del self._custom_templates[key]
            logger.info(f"Deleted custom template {key}")
            return True
        return False
    
    def enable_template(self, key: str, enabled: bool) -> bool:
        """Enable or disable a template."""
        template = self.get_template(key)
        if not template:
            return False
        
        template.enabled = enabled
        return True
    
    def render_template(self, key: str, **kwargs) -> Optional[str]:
        """
        Render a template with variable substitution.
        
        Args:
            key: Template key
            **kwargs: Variables to substitute
        
        Returns:
            Rendered message or None
        """
        template = self.get_template(key)
        if not template or not template.enabled:
            return None
        
        try:
            return template.message_template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing variable {e} in template {key}")
            return None
        except Exception as e:
            logger.error(f"Failed to render template {key}: {e}")
            return None
    
    def get_template_metadata(self, key: str) -> Dict[str, Any]:
        """Get template metadata."""
        template = self.get_template(key)
        if not template:
            return {}
        
        return {
            'key': template.key,
            'type': template.type,
            'title': template.title,
            'priority': template.priority,
            'category': template.category,
            'variables': template.variables,
            'enabled': template.enabled
        }
    
    def get_all_templates(self) -> List[NotificationTemplate]:
        """Get all templates."""
        return list(self._templates.values()) + list(self._custom_templates.values())
    
    def get_template_statistics(self) -> Dict[str, Any]:
        """Get template statistics."""
        stats = {
            'total': len(self._templates) + len(self._custom_templates),
            'by_type': {},
            'by_category': {},
            'enabled': 0,
            'disabled': 0,
            'custom': len(self._custom_templates)
        }
        
        for template in self._templates.values():
            stats['by_type'][template.type] = stats['by_type'].get(template.type, 0) + 1
            stats['by_category'][template.category] = stats['by_category'].get(template.category, 0) + 1
            if template.enabled:
                stats['enabled'] += 1
            else:
                stats['disabled'] += 1
        
        return stats


# Global template manager instance
_template_manager: Optional[NotificationTemplateManager] = None


def get_template_manager() -> NotificationTemplateManager:
    """Get or create global template manager instance."""
    global _template_manager
    if _template_manager is None:
        _template_manager = NotificationTemplateManager()
    return _template_manager


def render_template(key: str, **kwargs) -> Optional[str]:
    """
    Convenience function to render a template.
    
    Args:
        key: Template key
        **kwargs: Variables to substitute
    
    Returns:
        Rendered message or None
    """
    manager = get_template_manager()
    return manager.render_template(key, **kwargs)