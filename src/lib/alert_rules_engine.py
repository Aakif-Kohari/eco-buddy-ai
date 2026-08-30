"""
Alert Rules Engine for EcoBuddy AI
Evaluates conditions and triggers alerts based on user data and rules.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import json

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    INFO = 4


class AlertCategory(Enum):
    """Alert categories."""
    CARBON_BUDGET = "carbon_budget"
    FOOTPRINT = "footprint"
    STREAK = "streak"
    ACHIEVEMENT = "achievement"
    ASSESSMENT = "assessment"
    COMMUNITY = "community"
    SYSTEM = "system"


@dataclass
class AlertRule:
    """Data class for an alert rule."""
    id: str
    name: str
    category: AlertCategory
    severity: AlertSeverity
    condition: str  # Python expression to evaluate
    template_key: str  # Notification template key
    enabled: bool = True
    cooldown_minutes: int = 60
    user_specific: bool = False
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertResult:
    """Result of alert evaluation."""
    triggered: bool
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    template_key: str
    data: Dict[str, Any]
    timestamp: datetime


class AlertRulesEngine:
    """
    Evaluates alert rules against user data and triggers notifications.
    Supports custom rules and conditions.
    """
    
    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._user_data_cache: Dict[int, Dict[str, Any]] = {}
        self._last_evaluation: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        
        # Load default rules
        self._load_default_rules()
        
        logger.info("AlertRulesEngine initialized")
    
    def _load_default_rules(self) -> None:
        """Load default alert rules."""
        default_rules = [
            AlertRule(
                id="carbon_budget_exceeded",
                name="Carbon Budget Exceeded",
                category=AlertCategory.CARBON_BUDGET,
                severity=AlertSeverity.CRITICAL,
                condition="data.get('budget_usage', 0) > 1.0",
                template_key="carbon_budget_exceeded"
            ),
            AlertRule(
                id="carbon_budget_warning",
                name="Carbon Budget Warning",
                category=AlertCategory.CARBON_BUDGET,
                severity=AlertSeverity.HIGH,
                condition="data.get('budget_usage', 0) > 0.8",
                template_key="carbon_budget_warning"
            ),
            AlertRule(
                id="footprint_spike",
                name="Footprint Spike Detected",
                category=AlertCategory.FOOTPRINT,
                severity=AlertSeverity.HIGH,
                condition="data.get('footprint_increase', 0) > 20",
                template_key="footprint_spike"
            ),
            AlertRule(
                id="streak_at_risk",
                name="Streak at Risk",
                category=AlertCategory.STREAK,
                severity=AlertSeverity.HIGH,
                condition="data.get('days_since_assessment', 0) > 3",
                template_key="streak_at_risk"
            ),
            AlertRule(
                id="assessment_reminder",
                name="Assessment Reminder",
                category=AlertCategory.ASSESSMENT,
                severity=AlertSeverity.LOW,
                condition="data.get('days_since_assessment', 0) > 7",
                template_key="assessment_reminder",
                cooldown_minutes=1440  # Once per day
            ),
            AlertRule(
                id="budget_checkin",
                name="Budget Check-in",
                category=AlertCategory.CARBON_BUDGET,
                severity=AlertSeverity.MEDIUM,
                condition="data.get('budget_usage', 0) > 0.5",
                template_key="budget_checkin",
                cooldown_minutes=1440
            ),
            AlertRule(
                id="improvement_detected",
                name="Improvement Detected",
                category=AlertCategory.ACHIEVEMENT,
                severity=AlertSeverity.MEDIUM,
                condition="data.get('improvement', 0) > 10",
                template_key="improvement_detected"
            ),
            AlertRule(
                id="milestone_reached",
                name="Milestone Reached",
                category=AlertCategory.ACHIEVEMENT,
                severity=AlertSeverity.MEDIUM,
                condition="data.get('assessment_count', 0) % 10 == 0 and data.get('assessment_count', 0) > 0",
                template_key="milestone_reached"
            )
        ]
        
        for rule in default_rules:
            self._rules[rule.id] = rule
    
    def add_rule(self, rule: AlertRule) -> bool:
        """
        Add a new alert rule.
        
        Args:
            rule: AlertRule object
        
        Returns:
            True if added successfully
        """
        with self._lock:
            if rule.id in self._rules:
                logger.warning(f"Rule {rule.id} already exists, updating")
            self._rules[rule.id] = rule
            return True
    
    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove an alert rule.
        
        Args:
            rule_id: Rule ID
        
        Returns:
            True if removed successfully
        """
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                return True
            return False
    
    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)
    
    def get_all_rules(self) -> List[AlertRule]:
        """Get all rules."""
        return list(self._rules.values())
    
    def enable_rule(self, rule_id: str, enabled: bool) -> bool:
        """Enable or disable a rule."""
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule:
                rule.enabled = enabled
                return True
            return False
    
    def evaluate_rules(
        self,
        user_id: int,
        data: Dict[str, Any]
    ) -> List[AlertResult]:
        """
        Evaluate all rules against user data.
        
        Args:
            user_id: User ID
            data: User data dictionary
        
        Returns:
            List of triggered alerts
        """
        triggered = []
        
        with self._lock:
            for rule in self._rules.values():
                if not rule.enabled:
                    continue
                
                # Check cooldown
                if self._in_cooldown(rule):
                    continue
                
                # Evaluate condition
                if self._evaluate_condition(rule.condition, data):
                    # Trigger alert
                    result = AlertResult(
                        triggered=True,
                        rule_id=rule.id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        template_key=rule.template_key,
                        data=data,
                        timestamp=datetime.now()
                    )
                    triggered.append(result)
                    
                    # Update rule
                    rule.last_triggered = datetime.now()
                    rule.trigger_count += 1
                    
                    logger.info(f"Alert triggered: {rule.id} for user {user_id}")
        
        return triggered
    
    def _evaluate_condition(self, condition: str, data: Dict[str, Any]) -> bool:
        """
        Evaluate a condition expression.
        
        Args:
            condition: Python expression
            data: Data dictionary
        
        Returns:
            True if condition is met
        """
        try:
            # Create safe evaluation context
            context = {'data': data}
            result = eval(condition, {}, context)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to evaluate condition '{condition}': {e}")
            return False
    
    def _in_cooldown(self, rule: AlertRule) -> bool:
        """Check if rule is in cooldown period."""
        if not rule.last_triggered:
            return False
        
        cooldown_delta = timedelta(minutes=rule.cooldown_minutes)
        return (datetime.now() - rule.last_triggered) < cooldown_delta
    
    def evaluate_all_users(self, users_data: Dict[int, Dict[str, Any]]) -> Dict[int, List[AlertResult]]:
        """
        Evaluate rules for multiple users.
        
        Args:
            users_data: Dictionary of user_id -> data
        
        Returns:
            Dictionary of user_id -> triggered alerts
        """
        results = {}
        
        for user_id, data in users_data.items():
            triggered = self.evaluate_rules(user_id, data)
            if triggered:
                results[user_id] = triggered
        
        return results
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics."""
        stats = {
            'total_rules': len(self._rules),
            'enabled_rules': sum(1 for r in self._rules.values() if r.enabled),
            'by_category': {},
            'total_triggers': 0
        }
        
        for rule in self._rules.values():
            category = rule.category.value
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            stats['total_triggers'] += rule.trigger_count
        
        return stats
    
    def reset_rule_counters(self) -> None:
        """Reset all rule trigger counters."""
        with self._lock:
            for rule in self._rules.values():
                rule.trigger_count = 0
                rule.last_triggered = None
    
    def clear_user_cache(self, user_id: Optional[int] = None) -> None:
        """Clear cached user data."""
        if user_id:
            self._user_data_cache.pop(user_id, None)
        else:
            self._user_data_cache.clear()


# Global alert rules engine instance
_alert_rules_engine: Optional[AlertRulesEngine] = None
_alert_rules_engine_lock = threading.Lock()


def get_alert_rules_engine() -> AlertRulesEngine:
    """Get or create global alert rules engine instance."""
    global _alert_rules_engine
    with _alert_rules_engine_lock:
        if _alert_rules_engine is None:
            _alert_rules_engine = AlertRulesEngine()
        return _alert_rules_engine


def evaluate_alerts(user_id: int, data: Dict[str, Any]) -> List[AlertResult]:
    """
    Convenience function to evaluate alerts.
    
    Args:
        user_id: User ID
        data: User data dictionary
    
    Returns:
        List of triggered alerts
    """
    engine = get_alert_rules_engine()
    return engine.evaluate_rules(user_id, data)