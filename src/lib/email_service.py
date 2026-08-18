"""
Email Service for EcoBuddy AI
Handles email sending, templates, and scheduling for weekly eco-tips digest.
"""

import os
import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import threading
import time
from dataclasses import dataclass, field
import streamlit as st
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Email configuration settings."""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""
    use_tls: bool = True
    weekly_digest_day: int = 0  # 0 = Monday
    weekly_digest_time: str = "09:00"
    send_enabled: bool = True


@dataclass
class WeeklyDigestData:
    """Data for weekly eco-tips digest email."""
    user_email: str
    user_name: str
    week_start: str
    week_end: str
    eco_score: float
    total_footprint: float
    tips: List[Dict[str, Any]]
    achievements: List[Dict[str, Any]]
    challenges: List[Dict[str, Any]]
    streak_days: int
    tree_equivalent: int
    improvement_percentage: float
    tip_of_week: Dict[str, str]
    quote_of_week: str


class EmailTemplateManager:
    """Manages email templates for eco-tips digest."""
    
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, str]:
        """Load email templates."""
        return {
            "weekly_digest": """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Weekly Eco-Tips Digest</title>
                <style>
                    body { font-family: 'Segoe UI', Arial, sans-serif; background: #f0fdf4; margin: 0; padding: 0; }
                    .container { max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 20px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
                    .header { background: linear-gradient(135deg, #22c55e, #16a34a); padding: 30px; text-align: center; color: white; }
                    .header h1 { margin: 0; font-size: 28px; font-weight: 700; }
                    .header p { margin: 8px 0 0; opacity: 0.9; font-size: 14px; }
                    .content { padding: 30px; }
                    .greeting { font-size: 20px; color: #1a1a2e; margin-bottom: 10px; }
                    .greeting span { color: #22c55e; }
                    .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }
                    .stat-card { background: #f8fafc; border-radius: 12px; padding: 15px; text-align: center; border: 1px solid #e2e8f0; }
                    .stat-card .number { font-size: 24px; font-weight: 700; color: #22c55e; }
                    .stat-card .label { font-size: 12px; color: #64748b; margin-top: 4px; }
                    .tip-of-week { background: linear-gradient(135deg, #f0fdf4, #dcfce7); border-radius: 12px; padding: 20px; margin: 20px 0; border-left: 4px solid #22c55e; }
                    .tip-of-week .label { font-size: 12px; text-transform: uppercase; color: #16a34a; font-weight: 600; letter-spacing: 0.5px; }
                    .tip-of-week .text { font-size: 16px; color: #1a1a2e; margin-top: 8px; line-height: 1.6; }
                    .tips-list { margin: 20px 0; }
                    .tip-item { padding: 12px 0; border-bottom: 1px solid #f1f5f9; display: flex; align-items: start; gap: 12px; }
                    .tip-item .icon { font-size: 20px; }
                    .tip-item .content { flex: 1; padding: 0; }
                    .tip-item .title { font-weight: 600; color: #1a1a2e; font-size: 14px; }
                    .tip-item .desc { color: #64748b; font-size: 13px; margin-top: 2px; }
                    .achievement-badge { display: inline-block; background: #fef9c3; padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #854d0e; margin: 4px; }
                    .footer { padding: 20px; text-align: center; background: #f8fafc; border-top: 1px solid #e2e8f0; }
                    .footer a { color: #22c55e; text-decoration: none; }
                    .footer p { color: #94a3b8; font-size: 12px; margin: 4px 0; }
                    .progress-bar { width: 100%; height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; margin: 8px 0; }
                    .progress-bar .fill { height: 100%; background: linear-gradient(90deg, #22c55e, #16a34a); border-radius: 4px; transition: width 0.3s; }
                    .quote { font-style: italic; color: #475569; padding: 16px; background: #f1f5f9; border-radius: 8px; margin: 16px 0; text-align: center; }
                    .btn { display: inline-block; padding: 10px 24px; background: #22c55e; color: white; text-decoration: none; border-radius: 8px; font-weight: 600; margin-top: 16px; }
                    .btn:hover { background: #16a34a; }
                    @media (max-width: 480px) { .stats-grid { grid-template-columns: 1fr; } }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🌱 Weekly Eco-Tips Digest</h1>
                        <p>Your weekly sustainability update</p>
                    </div>
                    <div class="content">
                        <p class="greeting">Hello <span>{user_name}</span>! 👋</p>
                        <p style="color: #64748b;">Here's your weekly eco-tips digest for <strong>{week_range}</strong>.</p>

                        <div class="stats-grid">
                            <div class="stat-card">
                                <div class="number">{eco_score}</div>
                                <div class="label">Eco Score</div>
                            </div>
                            <div class="stat-card">
                                <div class="number">{total_footprint}</div>
                                <div class="label">kg CO₂ / year</div>
                            </div>
                            <div class="stat-card">
                                <div class="number">{streak_days}</div>
                                <div class="label">Day Streak 🔥</div>
                            </div>
                            <div class="stat-card">
                                <div class="number">{tree_equivalent}</div>
                                <div class="label">Trees Needed 🌳</div>
                            </div>
                        </div>

                        {improvement_section}

                        <div class="tip-of-week">
                            <div class="label">💡 Tip of the Week</div>
                            <div class="text">{tip_of_week_text}</div>
                        </div>

                        <div class="tips-list">
                            <h3 style="color: #1a1a2e; font-size: 16px;">🌿 This Week's Eco Tips</h3>
                            {tips_list}
                        </div>

                        {achievements_section}

                        {challenges_section}

                        <div class="quote">
                            "{quote_of_week}"
                        </div>

                        <a href="{app_url}" class="btn">🌍 View My Progress</a>
                    </div>
                    <div class="footer">
                        <p>You're receiving this because you subscribed to EcoBuddy AI weekly digest.</p>
                        <p><a href="{unsubscribe_url}">Unsubscribe</a> | <a href="{preferences_url}">Manage Preferences</a></p>
                        <p>© 2026 EcoBuddy AI. Encouraging sustainable living.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            
            "welcome": """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Welcome to EcoBuddy AI!</title>
                <style>
                    body { font-family: 'Segoe UI', Arial, sans-serif; background: #f0fdf4; margin: 0; padding: 20px; }
                    .container { max-width: 500px; margin: 0 auto; background: white; border-radius: 16px; padding: 30px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
                    .header { text-align: center; }
                    .header h1 { color: #22c55e; margin: 0; }
                    .btn { display: inline-block; padding: 10px 24px; background: #22c55e; color: white; text-decoration: none; border-radius: 8px; margin-top: 16px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🌱 Welcome to EcoBuddy AI!</h1>
                        <p>Start your sustainability journey today.</p>
                    </div>
                    <p>Hi {user_name},</p>
                    <p>Welcome to EcoBuddy AI! We're excited to help you track and reduce your carbon footprint.</p>
                    <p>Every week, you'll receive:</p>
                    <ul>
                        <li>🌿 5-10 personalized eco-tips</li>
                        <li>📊 Your weekly progress report</li>
                        <li>🏆 Achievements and milestones</li>
                        <li>💡 Quote of the week</li>
                    </ul>
                    <a href="{app_url}" class="btn">Get Started</a>
                    <p style="color: #94a3b8; font-size: 12px; margin-top: 20px;">You can unsubscribe anytime.</p>
                </div>
            </body>
            </html>
            """
        }
    
    def render_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """Render an email template with data."""
        template = self.templates.get(template_name)
        if not template:
            return ""
        
        # Replace placeholders
        result = template
        for key, value in data.items():
            result = result.replace(f"{{{key}}}", str(value))
        
        return result


class EmailService:
    """Service for sending emails."""
    
    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or EmailConfig()
        self.template_manager = EmailTemplateManager()
        self._load_env_config()
    
    def _load_env_config(self):
        """Load email configuration from environment variables."""
        self.config.sender_email = os.getenv("SMTP_USERNAME", "")
        self.config.sender_password = os.getenv("SMTP_PASSWORD", "")
        self.config.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.config.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.config.send_enabled = os.getenv("EMAIL_ENABLED", "true").lower() == "true"
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content
            text_content: Plain text content (optional)
        
        Returns:
            Tuple of (success, message)
        """
        if not self.config.send_enabled:
            return False, "Email sending is disabled"
        
        if not self.config.sender_email or not self.config.sender_password:
            return False, "Email credentials not configured"
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.config.sender_email
            msg["To"] = to_email
            
            # Plain text version
            if text_content:
                part_text = MIMEText(text_content, "plain")
                msg.attach(part_text)
            
            # HTML version
            part_html = MIMEText(html_content, "html")
            msg.attach(part_html)
            
            # Send email
            context = ssl.create_default_context() if self.config.use_tls else None
            
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls(context=context)
                server.login(self.config.sender_email, self.config.sender_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {to_email}: {subject}")
            return True, "Email sent successfully"
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False, f"Failed to send email: {str(e)}"
    
    def send_weekly_digest(self, digest_data: WeeklyDigestData) -> Tuple[bool, str]:
        """Send weekly eco-tips digest email."""
        # Prepare data for template
        app_url = os.getenv("APP_URL", "https://ecobuddy.ai")
        unsubscribe_url = f"{app_url}/unsubscribe?email={digest_data.user_email}"
        preferences_url = f"{app_url}/preferences"
        
        # Prepare tips list
        tips_html = ""
        for tip in digest_data.tips[:5]:
            tips_html += f"""
            <div class="tip-item">
                <span class="icon">🌿</span>
                <div class="content">
                    <div class="title">{tip.get('title', 'Eco Tip')}</div>
                    <div class="desc">{tip.get('description', '')}</div>
                </div>
            </div>
            """
        
        # Prepare achievements
        achievements_html = ""
        if digest_data.achievements:
            achievements_html = """
            <div style="margin: 20px 0;">
                <h3 style="color: #1a1a2e; font-size: 16px;">🏆 This Week's Achievements</h3>
            """
            for achievement in digest_data.achievements:
                achievements_html += f"""
                <span class="achievement-badge">🏅 {achievement.get('name', 'Achievement')}</span>
                """
            achievements_html += "</div>"
        
        # Prepare challenges
        challenges_html = ""
        if digest_data.challenges:
            challenges_html = """
            <div style="margin: 20px 0;">
                <h3 style="color: #1a1a2e; font-size: 16px;">🎯 Active Challenges</h3>
            """
            for challenge in digest_data.challenges:
                challenges_html += f"""
                <div style="background: #f8fafc; padding: 12px; border-radius: 8px; margin: 8px 0; border: 1px solid #e2e8f0;">
                    <div style="font-weight: 600;">{challenge.get('title', 'Challenge')}</div>
                    <div style="color: #64748b; font-size: 13px;">Progress: {challenge.get('progress', 0)}%</div>
                    <div class="progress-bar"><div class="fill" style="width: {challenge.get('progress', 0)}%;"></div></div>
                </div>
                """
            challenges_html += "</div>"
        
        # Improvement section
        improvement_section = ""
        if digest_data.improvement_percentage > 0:
            improvement_section = f"""
            <div style="background: #dcfce7; padding: 12px; border-radius: 8px; text-align: center; margin: 8px 0;">
                📈 Your footprint is down <strong>{digest_data.improvement_percentage:.1f}%</strong> from last week! Keep it up!
            </div>
            """
        elif digest_data.improvement_percentage < 0:
            improvement_section = f"""
            <div style="background: #fef3c7; padding: 12px; border-radius: 8px; text-align: center; margin: 8px 0;">
                📊 Your footprint increased by <strong>{abs(digest_data.improvement_percentage):.1f}%</strong>. Let's work on it this week!
            </div>
            """
        
        # Prepare template data
        template_data = {
            "user_name": digest_data.user_name,
            "week_range": f"{digest_data.week_start} - {digest_data.week_end}",
            "eco_score": digest_data.eco_score,
            "total_footprint": round(digest_data.total_footprint, 1),
            "streak_days": digest_data.streak_days,
            "tree_equivalent": digest_data.tree_equivalent,
            "tip_of_week_text": digest_data.tip_of_week.get("text", "Start small, think big!"),
            "tips_list": tips_html,
            "achievements_section": achievements_html,
            "challenges_section": challenges_html,
            "quote_of_week": digest_data.quote_of_week,
            "app_url": app_url,
            "unsubscribe_url": unsubscribe_url,
            "preferences_url": preferences_url,
            "improvement_section": improvement_section
        }
        
        html_content = self.template_manager.render_template("weekly_digest", template_data)
        
        subject = f"🌱 Your Weekly Eco-Tips Digest - Week {digest_data.week_start}"
        
        return self.send_email(digest_data.user_email, subject, html_content)
    
    def send_welcome_email(self, user_email: str, user_name: str) -> Tuple[bool, str]:
        """Send welcome email to new users."""
        app_url = os.getenv("APP_URL", "https://ecobuddy.ai")
        
        template_data = {
            "user_name": user_name,
            "app_url": app_url
        }
        
        html_content = self.template_manager.render_template("welcome", template_data)
        subject = "🌱 Welcome to EcoBuddy AI!"
        
        return self.send_email(user_email, subject, html_content)


# Global email service instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get global email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


def send_weekly_digest_to_user(user_email: str, user_name: str) -> Tuple[bool, str]:
    """Convenience function to send weekly digest to a user."""
    service = get_email_service()
    return service.send_welcome_email(user_email, user_name)