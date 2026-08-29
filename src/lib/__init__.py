"""
EcoBuddy AI Library Package
Contains utility modules for the application.
"""

# Export Manager
from .export_manager import (
    ExportManager,
    ExportConfig,
    ExportResult,
    get_export_manager,
    export_assessments,
    export_summary,
    get_supported_formats
)

# History Manager
from .history_manager import (
    HistoryManager,
    HistoryFilter,
    get_history_manager,
    clear_history_manager
)

# Analytics Engine
from .analytics_engine import (
    AnalyticsEngine,
    AnalyticsConfig,
    AnalyticsResult,
    get_analytics_engine,
    analyze_assessments,
    get_analysis_summary
)

# Predictive Model
from .predictive_model import (
    PredictiveModel,
    ModelConfig,
    PredictionResult,
    get_predictive_model,
    train_predictive_model,
    generate_predictions,
    evaluate_predictions
)

# Trend Analyzer
from .trend_analyzer import (
    TrendAnalyzer,
    TrendResult,
    get_trend_analyzer,
    analyze_trends,
    get_trend_forecast
)

# Insight Generator
from .insight_generator import (
    InsightGenerator,
    Insight,
    InsightResult,
    get_insight_generator,
    generate_insights
)

# Notification Manager
from .notification_manager import (
    NotificationManager,
    Notification,
    NotificationPreferences,
    NotificationPriority,
    NotificationType,
    get_notification_manager,
    create_notification,
    get_user_notifications,
    get_unread_count,
    mark_as_read,
    mark_all_as_read,
    dismiss_notification,
    dismiss_all
)

# Alert Rules Engine
from .alert_rules_engine import (
    AlertRulesEngine,
    AlertRule,
    AlertResult,
    AlertSeverity,
    AlertCategory,
    get_alert_rules_engine,
    evaluate_alerts
)

# Reminder Scheduler
from .reminder_scheduler import (
    ReminderScheduler,
    Reminder,
    ReminderType,
    ReminderFrequency,
    get_reminder_scheduler,
    create_reminder,
    get_user_reminders
)

# Notification Templates
from .notification_templates import (
    NotificationTemplateManager,
    NotificationTemplate,
    get_template_manager,
    render_template
)

__all__ = [
    # Export Manager
    'ExportManager',
    'ExportConfig',
    'ExportResult',
    'get_export_manager',
    'export_assessments',
    'export_summary',
    'get_supported_formats',
    
    # History Manager
    'HistoryManager',
    'HistoryFilter',
    'get_history_manager',
    'clear_history_manager',
    
    # Analytics Engine
    'AnalyticsEngine',
    'AnalyticsConfig',
    'AnalyticsResult',
    'get_analytics_engine',
    'analyze_assessments',
    'get_analysis_summary',
    
    # Predictive Model
    'PredictiveModel',
    'ModelConfig',
    'PredictionResult',
    'get_predictive_model',
    'train_predictive_model',
    'generate_predictions',
    'evaluate_predictions',
    
    # Trend Analyzer
    'TrendAnalyzer',
    'TrendResult',
    'get_trend_analyzer',
    'analyze_trends',
    'get_trend_forecast',
    
    # Insight Generator
    'InsightGenerator',
    'Insight',
    'InsightResult',
    'get_insight_generator',
    'generate_insights',
    
    # Notification Manager
    'NotificationManager',
    'Notification',
    'NotificationPreferences',
    'NotificationPriority',
    'NotificationType',
    'get_notification_manager',
    'create_notification',
    'get_user_notifications',
    'get_unread_count',
    'mark_as_read',
    'mark_all_as_read',
    'dismiss_notification',
    'dismiss_all',
    
    # Alert Rules Engine
    'AlertRulesEngine',
    'AlertRule',
    'AlertResult',
    'AlertSeverity',
    'AlertCategory',
    'get_alert_rules_engine',
    'evaluate_alerts',
    
    # Reminder Scheduler
    'ReminderScheduler',
    'Reminder',
    'ReminderType',
    'ReminderFrequency',
    'get_reminder_scheduler',
    'create_reminder',
    'get_user_reminders',
    
    # Notification Templates
    'NotificationTemplateManager',
    'NotificationTemplate',
    'get_template_manager',
    'render_template'
]