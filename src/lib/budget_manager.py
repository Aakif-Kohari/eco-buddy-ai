"""
Budget Manager for EcoBuddy AI
Manages user carbon budgets, tracking, and alerts.
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


class BudgetPeriod(Enum):
    """Budget time periods."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class BudgetStatus(Enum):
    """Budget status states."""
    ON_TRACK = "on_track"
    WARNING = "warning"
    EXCEEDED = "exceeded"
    CRITICAL = "critical"


@dataclass
class CarbonBudget:
    """Data class for a carbon budget."""
    id: str
    user_id: int
    name: str
    amount: float  # kg CO₂
    period: BudgetPeriod
    start_date: datetime
    end_date: datetime
    current_usage: float = 0.0
    status: BudgetStatus = BudgetStatus.ON_TRACK
    warning_threshold: float = 0.8  # 80%
    critical_threshold: float = 0.95  # 95%
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    previous_budgets: List[str] = field(default_factory=list)  # IDs of previous budgets
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert budget to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'amount': self.amount,
            'period': self.period.value,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'current_usage': self.current_usage,
            'status': self.status.value,
            'warning_threshold': self.warning_threshold,
            'critical_threshold': self.critical_threshold,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'metadata': self.metadata,
            'is_active': self.is_active,
            'previous_budgets': self.previous_budgets
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CarbonBudget':
        """Create budget from dictionary."""
        return cls(
            id=data['id'],
            user_id=data['user_id'],
            name=data['name'],
            amount=data['amount'],
            period=BudgetPeriod(data['period']),
            start_date=datetime.fromisoformat(data['start_date']),
            end_date=datetime.fromisoformat(data['end_date']),
            current_usage=data.get('current_usage', 0.0),
            status=BudgetStatus(data.get('status', 'on_track')),
            warning_threshold=data.get('warning_threshold', 0.8),
            critical_threshold=data.get('critical_threshold', 0.95),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            metadata=data.get('metadata', {}),
            is_active=data.get('is_active', True),
            previous_budgets=data.get('previous_budgets', [])
        )


@dataclass
class BudgetTransaction:
    """Data class for a budget transaction."""
    id: str
    user_id: int
    budget_id: str
    amount: float  # kg CO₂
    timestamp: datetime
    source: str  # assessment, manual, etc.
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class BudgetManager:
    """
    Manages user carbon budgets, tracking usage, and generating alerts.
    """
    
    def __init__(self):
        self._budgets: Dict[str, CarbonBudget] = {}
        self._user_budgets: Dict[int, List[str]] = {}  # user_id -> budget_ids
        self._transactions: Dict[str, List[BudgetTransaction]] = {}  # budget_id -> transactions
        self._lock = threading.Lock()
        self._budget_counter = 0
        
        # Start monitoring thread
        self._stop_monitor = False
        self._monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
        self._monitor_thread.start()
        
        logger.info("BudgetManager initialized")
    
    def _generate_id(self) -> str:
        """Generate unique budget ID."""
        self._budget_counter += 1
        timestamp = int(time.time() * 1000)
        return f"budget_{timestamp}_{self._budget_counter}"
    
    def create_budget(
        self,
        user_id: int,
        name: str,
        amount: float,
        period: BudgetPeriod,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> CarbonBudget:
        """
        Create a new carbon budget.
        
        Args:
            user_id: User ID
            name: Budget name
            amount: Budget amount in kg CO₂
            period: Budget period
            start_date: Start date (default: now)
            end_date: End date (calculated if not provided)
            **kwargs: Additional fields
        
        Returns:
            CarbonBudget object
        """
        if start_date is None:
            start_date = datetime.now()
        
        if end_date is None:
            if period == BudgetPeriod.DAILY:
                end_date = start_date + timedelta(days=1)
            elif period == BudgetPeriod.WEEKLY:
                end_date = start_date + timedelta(days=7)
            elif period == BudgetPeriod.MONTHLY:
                # End of month
                if start_date.month == 12:
                    end_date = start_date.replace(year=start_date.year + 1, month=1, day=1)
                else:
                    end_date = start_date.replace(month=start_date.month + 1, day=1)
            elif period == BudgetPeriod.YEARLY:
                end_date = start_date.replace(year=start_date.year + 1, month=1, day=1)
            else:
                end_date = start_date + timedelta(days=30)
        
        budget = CarbonBudget(
            id=self._generate_id(),
            user_id=user_id,
            name=name,
            amount=amount,
            period=period,
            start_date=start_date,
            end_date=end_date,
            warning_threshold=kwargs.get('warning_threshold', 0.8),
            critical_threshold=kwargs.get('critical_threshold', 0.95),
            metadata=kwargs.get('metadata', {}),
            previous_budgets=kwargs.get('previous_budgets', [])
        )
        
        with self._lock:
            self._budgets[budget.id] = budget
            if user_id not in self._user_budgets:
                self._user_budgets[user_id] = []
            self._user_budgets[user_id].append(budget.id)
            self._transactions[budget.id] = []
        
        logger.info(f"Created budget {budget.id} for user {user_id}: {amount}kg {period.value}")
        return budget
    
    def get_budget(self, budget_id: str) -> Optional[CarbonBudget]:
        """Get a budget by ID."""
        return self._budgets.get(budget_id)
    
    def get_user_budgets(self, user_id: int, active_only: bool = True) -> List[CarbonBudget]:
        """Get all budgets for a user."""
        budget_ids = self._user_budgets.get(user_id, [])
        budgets = [self._budgets[b_id] for b_id in budget_ids if b_id in self._budgets]
        
        if active_only:
            budgets = [b for b in budgets if b.is_active]
        
        return budgets
    
    def get_active_budget(self, user_id: int) -> Optional[CarbonBudget]:
        """Get the current active budget for a user."""
        budgets = self.get_user_budgets(user_id, active_only=True)
        now = datetime.now()
        
        for budget in budgets:
            if budget.start_date <= now <= budget.end_date:
                return budget
        
        return None
    
    def update_budget_usage(self, budget_id: str, amount: float) -> bool:
        """
        Update budget usage.
        
        Args:
            budget_id: Budget ID
            amount: Amount to add (in kg CO₂)
        
        Returns:
            True if successful
        """
        with self._lock:
            budget = self._budgets.get(budget_id)
            if not budget:
                return False
            
            budget.current_usage += amount
            budget.updated_at = datetime.now()
            
            # Update status
            self._update_budget_status(budget)
            
            # Add transaction
            transaction = BudgetTransaction(
                id=f"txn_{int(time.time() * 1000)}_{len(self._transactions[budget_id])}",
                user_id=budget.user_id,
                budget_id=budget_id,
                amount=amount,
                timestamp=datetime.now(),
                source="automatic",
                description=f"Added {amount:.2f} kg CO₂ to budget"
            )
            self._transactions[budget_id].append(transaction)
            
            # Check for alerts
            self._check_budget_alerts(budget)
            
            logger.info(f"Updated budget {budget_id}: {budget.current_usage:.2f}/{budget.amount} kg")
            return True
    
    def _update_budget_status(self, budget: CarbonBudget) -> None:
        """Update budget status based on usage."""
        usage_ratio = budget.current_usage / budget.amount if budget.amount > 0 else 0
        
        if usage_ratio >= budget.critical_threshold:
            budget.status = BudgetStatus.CRITICAL
        elif usage_ratio >= budget.warning_threshold:
            budget.status = BudgetStatus.WARNING
        elif usage_ratio > budget.amount:
            budget.status = BudgetStatus.EXCEEDED
        else:
            budget.status = BudgetStatus.ON_TRACK
    
    def _check_budget_alerts(self, budget: CarbonBudget) -> None:
        """Check and trigger budget alerts."""
        from .notification_manager import create_notification, NotificationType
        
        usage_ratio = budget.current_usage / budget.amount if budget.amount > 0 else 0
        
        if usage_ratio >= budget.critical_threshold:
            # Critical alert
            create_notification(
                user_id=budget.user_id,
                type=NotificationType.ALERT,
                template_key='carbon_budget_exceeded',
                percentage=usage_ratio * 100,
                usage=budget.current_usage,
                budget=budget.amount,
                remaining=budget.amount - budget.current_usage
            )
        elif usage_ratio >= budget.warning_threshold:
            # Warning alert
            create_notification(
                user_id=budget.user_id,
                type=NotificationType.ALERT,
                template_key='carbon_budget_warning',
                percentage=usage_ratio * 100,
                usage=budget.current_usage,
                budget=budget.amount,
                remaining=budget.amount - budget.current_usage
            )
    
    def get_budget_progress(self, budget_id: str) -> Dict[str, Any]:
        """Get detailed budget progress."""
        budget = self._budgets.get(budget_id)
        if not budget:
            return {}
        
        days_elapsed = (datetime.now() - budget.start_date).days + 1
        days_total = (budget.end_date - budget.start_date).days + 1
        
        # Calculate daily target
        daily_target = budget.amount / days_total if days_total > 0 else budget.amount
        
        # Calculate projected usage
        projected_usage = budget.current_usage / days_elapsed * days_total if days_elapsed > 0 else 0
        
        usage_ratio = budget.current_usage / budget.amount if budget.amount > 0 else 0
        
        return {
            'budget': budget,
            'usage_ratio': usage_ratio,
            'usage_percentage': usage_ratio * 100,
            'remaining': budget.amount - budget.current_usage,
            'daily_target': daily_target,
            'days_elapsed': days_elapsed,
            'days_remaining': max(0, days_total - days_elapsed),
            'projected_usage': projected_usage,
            'projected_overshoot': max(0, projected_usage - budget.amount),
            'status': budget.status.value,
            'is_on_track': budget.current_usage <= daily_target * days_elapsed if days_elapsed > 0 else True
        }
    
    def get_budget_transactions(
        self,
        budget_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[BudgetTransaction]:
        """Get transactions for a budget."""
        transactions = self._transactions.get(budget_id, [])
        transactions.sort(key=lambda t: t.timestamp, reverse=True)
        return transactions[offset:offset + limit]
    
    def reset_budget(self, budget_id: str) -> bool:
        """Reset a budget (archive and create new)."""
        with self._lock:
            budget = self._budgets.get(budget_id)
            if not budget:
                return False
            
            # Archive current budget
            budget.is_active = False
            budget.updated_at = datetime.now()
            
            # Create new budget with same settings
            new_budget = self.create_budget(
                user_id=budget.user_id,
                name=f"{budget.name} - {datetime.now().strftime('%b %Y')}",
                amount=budget.amount,
                period=budget.period,
                start_date=datetime.now(),
                previous_budgets=budget.previous_budgets + [budget.id],
                warning_threshold=budget.warning_threshold,
                critical_threshold=budget.critical_threshold,
                metadata=budget.metadata
            )
            
            logger.info(f"Reset budget {budget_id}, created {new_budget.id}")
            return True
    
    def _monitor_worker(self) -> None:
        """Background worker for budget monitoring."""
        while not self._stop_monitor:
            try:
                time.sleep(60)  # Check every minute
                self._check_expiring_budgets()
            except Exception as e:
                logger.error(f"Monitor worker error: {e}")
    
    def _check_expiring_budgets(self) -> None:
        """Check for expiring budgets and create alerts."""
        now = datetime.now()
        
        with self._lock:
            for budget in self._budgets.values():
                if not budget.is_active:
                    continue
                
                days_until_expiry = (budget.end_date - now).days
                
                if days_until_expiry <= 3 and days_until_expiry > 0:
                    # Budget expiring soon
                    from .notification_manager import create_notification, NotificationType
                    create_notification(
                        user_id=budget.user_id,
                        type=NotificationType.REMINDER,
                        template_key='budget_checkin',
                        percentage=(budget.current_usage / budget.amount) * 100 if budget.amount > 0 else 0,
                        usage=budget.current_usage,
                        budget=budget.amount,
                        remaining=budget.amount - budget.current_usage
                    )
    
    def get_budget_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get budget statistics for a user."""
        budgets = self.get_user_budgets(user_id)
        
        stats = {
            'total_budgets': len(budgets),
            'active_budgets': sum(1 for b in budgets if b.is_active),
            'by_period': {},
            'by_status': {},
            'average_usage': 0,
            'total_usage': 0
        }
        
        total_usage = 0
        for budget in budgets:
            stats['by_period'][budget.period.value] = stats['by_period'].get(budget.period.value, 0) + 1
            stats['by_status'][budget.status.value] = stats['by_status'].get(budget.status.value, 0) + 1
            total_usage += budget.current_usage
        
        if budgets:
            stats['average_usage'] = total_usage / len(budgets)
            stats['total_usage'] = total_usage
        
        return stats


# Global budget manager instance
_budget_manager: Optional[BudgetManager] = None
_budget_manager_lock = threading.Lock()


def get_budget_manager() -> BudgetManager:
    """Get or create global budget manager instance."""
    global _budget_manager
    with _budget_manager_lock:
        if _budget_manager is None:
            _budget_manager = BudgetManager()
        return _budget_manager


def create_budget(
    user_id: int,
    name: str,
    amount: float,
    period: BudgetPeriod,
    **kwargs
) -> CarbonBudget:
    """Convenience function to create a budget."""
    manager = get_budget_manager()
    return manager.create_budget(user_id, name, amount, period, **kwargs)


def get_user_budgets(user_id: int, active_only: bool = True) -> List[CarbonBudget]:
    """Convenience function to get user budgets."""
    manager = get_budget_manager()
    return manager.get_user_budgets(user_id, active_only)


def get_active_budget(user_id: int) -> Optional[CarbonBudget]:
    """Convenience function to get active budget."""
    manager = get_budget_manager()
    return manager.get_active_budget(user_id)


def update_budget_usage(budget_id: str, amount: float) -> bool:
    """Convenience function to update budget usage."""
    manager = get_budget_manager()
    return manager.update_budget_usage(budget_id, amount)


def get_budget_progress(budget_id: str) -> Dict[str, Any]:
    """Convenience function to get budget progress."""
    manager = get_budget_manager()
    return manager.get_budget_progress(budget_id)