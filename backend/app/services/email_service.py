"""
Enterprise Email Notification Service
Handles all email notifications for sentiment alerts and system notifications
"""

import asyncio
import logging
import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

from app.core.config import get_settings, get_email_config
from app.core.logging import setup_logging


class EmailPriority(Enum):
    """Email priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EmailTemplate(Enum):
    """Available email templates"""
    SENTIMENT_ALERT = "sentiment_alert"
    SESSION_SUMMARY = "session_summary"
    ERROR_NOTIFICATION = "error_notification"
    SYSTEM_MAINTENANCE = "system_maintenance"


@dataclass
class EmailRecipient:
    """Email recipient information"""
    email: str
    name: Optional[str] = None
    type: str = "to"  # to, cc, bcc


@dataclass
class SentimentAlert:
    """Sentiment alert data for email templates"""
    meeting_url: str
    session_id: str
    timestamp: datetime
    sentiment_score: float
    sentiment_label: str
    confidence: float
    transcription: str
    participant_count: int
    session_duration: str
    threshold_exceeded: float


@dataclass
class EmailMetrics:
    """Email service metrics"""
    total_sent: int = 0
    total_failed: int = 0
    alerts_sent: int = 0
    summaries_sent: int = 0
    last_sent: Optional[datetime] = None
    last_error: Optional[str] = None


class EmailService:
    """
    Enterprise email notification service with template support and delivery tracking
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.email_config = get_email_config()
        self.logger = setup_logging()
        
        # Email client configuration
        self.mail_client = None
        self.connection_config = None
        
        # Template engine
        self.template_env = None
        
        # Metrics and tracking
        self.metrics = EmailMetrics()
        self.rate_limit = {}  # For preventing email spam
        
        # Initialize email service
        asyncio.create_task(self._initialize())
    
    async def _initialize(self):
        """Initialize email service and templates"""
        try:
            if not self.email_config["server"] or not self.email_config["from_email"]:
                self.logger.warning("Email service not configured - email notifications disabled")
                return
            
            # Set up FastMail configuration
            self.connection_config = ConnectionConfig(
                MAIL_USERNAME=self.email_config["username"],
                MAIL_PASSWORD=self.email_config["password"],
                MAIL_FROM=self.email_config["from_email"],
                MAIL_PORT=self.email_config["port"],
                MAIL_SERVER=self.email_config["server"],
                MAIL_FROM_NAME=self.email_config["from_name"],
                MAIL_STARTTLS=self.email_config["starttls"],
                MAIL_SSL_TLS=self.email_config["ssl_tls"],
                USE_CREDENTIALS=self.email_config["use_credentials"],
                VALIDATE_CERTS=self.email_config["validate_certs"]
            )
            
            self.mail_client = FastMail(self.connection_config)
            
            # Initialize Jinja2 template environment
            template_dir = Path(__file__).parent.parent / "templates" / "email"
            template_dir.mkdir(parents=True, exist_ok=True)
            
            self.template_env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=select_autoescape(['html', 'xml'])
            )
            
            # Create default templates if they don't exist
            await self._create_default_templates()
            
            self.logger.info(f"Email service initialized - SMTP: {self.email_config['server']}:{self.email_config['port']}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize email service: {str(e)}", exc_info=True)
    
    async def _create_default_templates(self):
        """Create default email templates"""
        templates = {
            "sentiment_alert.html": self._get_sentiment_alert_template(),
            "session_summary.html": self._get_session_summary_template(),
            "error_notification.html": self._get_error_notification_template(),
            "system_maintenance.html": self._get_maintenance_template()
        }
        
        template_dir = Path(__file__).parent.parent / "templates" / "email"
        
        for filename, content in templates.items():
            template_path = template_dir / filename
            if not template_path.exists():
                template_path.write_text(content)
                self.logger.debug(f"Created email template: {filename}")
    
    async def send_sentiment_alert(
        self,
        recipients: List[str],
        alert_data: SentimentAlert,
        priority: EmailPriority = EmailPriority.HIGH
    ) -> bool:
        """
        Send sentiment alert email notification
        """
        try:
            if not self.mail_client:
                self.logger.warning("Email service not configured - cannot send sentiment alert")
                return False
            
            # Check rate limiting
            if not self._check_rate_limit("sentiment_alert", recipients):
                self.logger.warning("Sentiment alert email rate limited")
                return False
            
            # Prepare email content
            subject = f"🚨 Negative Sentiment Alert - Meeting {alert_data.session_id}"
            
            # Render template
            template = self.template_env.get_template("sentiment_alert.html")
            html_body = template.render(
                alert=alert_data,
                timestamp=alert_data.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                company_name="Your Company",
                support_email=self.email_config["from_email"]
            )
            
            # Create message
            message = MessageSchema(
                subject=subject,
                recipients=recipients,
                body=html_body,
                subtype="html"
            )
            
            # Send email
            await self.mail_client.send_message(message)
            
            # Update metrics
            self.metrics.total_sent += 1
            self.metrics.alerts_sent += 1
            self.metrics.last_sent = datetime.now()
            
            # Update rate limiting
            self._update_rate_limit("sentiment_alert", recipients)
            
            self.logger.info(
                f"Sentiment alert email sent",
                recipients=recipients,
                session_id=alert_data.session_id,
                sentiment_score=alert_data.sentiment_score
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send sentiment alert email: {str(e)}", exc_info=True)
            self.metrics.total_failed += 1
            self.metrics.last_error = str(e)
            return False
    
    async def send_session_summary(
        self,
        recipients: List[str],
        session_data: Dict[str, Any],
        priority: EmailPriority = EmailPriority.NORMAL
    ) -> bool:
        """
        Send session summary email
        """
        try:
            if not self.mail_client:
                return False
            
            subject = f"📊 Meeting Session Summary - {session_data.get('session_id', 'Unknown')}"
            
            # Render template
            template = self.template_env.get_template("session_summary.html")
            html_body = template.render(
                session=session_data,
                company_name="Your Company",
                support_email=self.email_config["from_email"]
            )
            
            # Create message
            message = MessageSchema(
                subject=subject,
                recipients=recipients,
                body=html_body,
                subtype="html"
            )
            
            # Send email
            await self.mail_client.send_message(message)
            
            # Update metrics
            self.metrics.total_sent += 1
            self.metrics.summaries_sent += 1
            self.metrics.last_sent = datetime.now()
            
            self.logger.info(f"Session summary email sent to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send session summary email: {str(e)}", exc_info=True)
            self.metrics.total_failed += 1
            return False
    
    async def send_error_notification(
        self,
        recipients: List[str],
        error_data: Dict[str, Any],
        priority: EmailPriority = EmailPriority.URGENT
    ) -> bool:
        """
        Send error notification email
        """
        try:
            if not self.mail_client:
                return False
            
            subject = f"🔥 System Error Alert - {error_data.get('error_type', 'Unknown Error')}"
            
            # Render template
            template = self.template_env.get_template("error_notification.html")
            html_body = template.render(
                error=error_data,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                company_name="Your Company",
                support_email=self.email_config["from_email"]
            )
            
            # Create message
            message = MessageSchema(
                subject=subject,
                recipients=recipients,
                body=html_body,
                subtype="html"
            )
            
            # Send email
            await self.mail_client.send_message(message)
            
            # Update metrics
            self.metrics.total_sent += 1
            self.metrics.last_sent = datetime.now()
            
            self.logger.info(f"Error notification email sent to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send error notification email: {str(e)}", exc_info=True)
            self.metrics.total_failed += 1
            return False
    
    def _check_rate_limit(self, email_type: str, recipients: List[str]) -> bool:
        """Check if email sending is rate limited"""
        now = datetime.now()
        rate_limit_key = f"{email_type}_{hash(tuple(sorted(recipients)))}"
        
        # Check if we've sent to these recipients recently
        if rate_limit_key in self.rate_limit:
            last_sent = self.rate_limit[rate_limit_key]
            time_diff = (now - last_sent).total_seconds()
            
            # Rate limit: max 1 sentiment alert per 5 minutes to same recipients
            if email_type == "sentiment_alert" and time_diff < 300:  # 5 minutes
                return False
        
        return True
    
    def _update_rate_limit(self, email_type: str, recipients: List[str]):
        """Update rate limiting timestamp"""
        rate_limit_key = f"{email_type}_{hash(tuple(sorted(recipients)))}"
        self.rate_limit[rate_limit_key] = datetime.now()
    
    def get_metrics(self) -> EmailMetrics:
        """Get email service metrics"""
        return self.metrics
    
    async def test_connection(self) -> bool:
        """Test email service connection"""
        try:
            if not self.mail_client:
                return False
            
            # Test connection by trying to send a test email to the from address
            test_message = MessageSchema(
                subject="Email Service Test",
                recipients=[self.email_config["from_email"]],
                body="This is a test message to verify email service configuration.",
                subtype="plain"
            )
            
            await self.mail_client.send_message(test_message)
            self.logger.info("Email service connection test successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Email service connection test failed: {str(e)}")
            return False
    
    def _get_sentiment_alert_template(self) -> str:
        """Get sentiment alert email template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Sentiment Alert</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #dc3545; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f8f9fa; }
        .alert-box { background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; margin: 15px 0; }
        .metrics { display: flex; justify-content: space-between; margin: 20px 0; }
        .metric { text-align: center; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
        .button { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 Negative Sentiment Alert</h1>
            <p>Detected in Meeting Session: {{ alert.session_id }}</p>
        </div>
        
        <div class="content">
            <div class="alert-box">
                <h3>Alert Details</h3>
                <p><strong>Time:</strong> {{ timestamp }}</p>
                <p><strong>Meeting URL:</strong> <a href="{{ alert.meeting_url }}">{{ alert.meeting_url }}</a></p>
                <p><strong>Sentiment Score:</strong> {{ "%.3f"|format(alert.sentiment_score) }}</p>
                <p><strong>Confidence:</strong> {{ "%.1f"|format(alert.confidence * 100) }}%</p>
                <p><strong>Threshold Exceeded:</strong> {{ "%.3f"|format(alert.threshold_exceeded) }}</p>
            </div>
            
            <div class="metrics">
                <div class="metric">
                    <h4>{{ alert.participant_count }}</h4>
                    <p>Participants</p>
                </div>
                <div class="metric">
                    <h4>{{ alert.session_duration }}</h4>
                    <p>Session Duration</p>
                </div>
                <div class="metric">
                    <h4>{{ alert.sentiment_label|title }}</h4>
                    <p>Sentiment</p>
                </div>
            </div>
            
            {% if alert.transcription %}
            <div class="alert-box">
                <h3>Transcription Sample</h3>
                <p><em>"{{ alert.transcription[:200] }}{% if alert.transcription|length > 200 %}..."{% endif %}</em></p>
            </div>
            {% endif %}
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{ alert.meeting_url }}" class="button">Join Meeting</a>
            </div>
        </div>
        
        <div class="footer">
            <p>This alert was generated by {{ company_name }} Meet Sentiment Bot</p>
            <p>For support, contact: {{ support_email }}</p>
        </div>
    </div>
</body>
</html>
        """
    
    def _get_session_summary_template(self) -> str:
        """Get session summary email template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Session Summary</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #28a745; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f8f9fa; }
        .summary-box { background: white; border: 1px solid #dee2e6; padding: 15px; margin: 15px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Meeting Session Summary</h1>
            <p>Session: {{ session.session_id }}</p>
        </div>
        
        <div class="content">
            <div class="summary-box">
                <h3>Session Overview</h3>
                <p><strong>Duration:</strong> {{ session.duration }}</p>
                <p><strong>Participants:</strong> {{ session.participant_count }}</p>
                <p><strong>Total Alerts:</strong> {{ session.alert_count }}</p>
                <p><strong>Average Sentiment:</strong> {{ "%.3f"|format(session.avg_sentiment) }}</p>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by {{ company_name }} Meet Sentiment Bot</p>
            <p>For support, contact: {{ support_email }}</p>
        </div>
    </div>
</body>
</html>
        """
    
    def _get_error_notification_template(self) -> str:
        """Get error notification email template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>System Error Alert</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #dc3545; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f8f9fa; }
        .error-box { background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; margin: 15px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 System Error Alert</h1>
            <p>{{ error.error_type }}</p>
        </div>
        
        <div class="content">
            <div class="error-box">
                <h3>Error Details</h3>
                <p><strong>Time:</strong> {{ timestamp }}</p>
                <p><strong>Error:</strong> {{ error.message }}</p>
                <p><strong>Component:</strong> {{ error.component }}</p>
                {% if error.session_id %}<p><strong>Session:</strong> {{ error.session_id }}</p>{% endif %}
            </div>
        </div>
        
        <div class="footer">
            <p>{{ company_name }} Meet Sentiment Bot - System Alert</p>
            <p>For support, contact: {{ support_email }}</p>
        </div>
    </div>
</body>
</html>
        """
    
    def _get_maintenance_template(self) -> str:
        """Get maintenance notification email template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>System Maintenance</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #ffc107; color: #212529; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f8f9fa; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔧 System Maintenance Notice</h1>
        </div>
        
        <div class="content">
            <h3>Scheduled Maintenance</h3>
            <p>We will be performing scheduled maintenance on the Meet Sentiment Bot system.</p>
            <p><strong>Start Time:</strong> {{ maintenance.start_time }}</p>
            <p><strong>Expected Duration:</strong> {{ maintenance.duration }}</p>
            <p><strong>Impact:</strong> {{ maintenance.impact }}</p>
        </div>
        
        <div class="footer">
            <p>{{ company_name }} Meet Sentiment Bot</p>
            <p>For questions, contact: {{ support_email }}</p>
        </div>
    </div>
</body>
</html>
        """