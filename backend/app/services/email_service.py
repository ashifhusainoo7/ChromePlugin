from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Iterable

from loguru import logger

from app.config import settings


class EmailService:
    def __init__(self) -> None:
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.email_from = settings.email_from
        self.email_to = settings.email_to

    def send_alert(self, subject: str, html_body: str) -> None:
        if not (self.smtp_host and self.email_from and self.email_to):
            logger.warning("Email not configured; skipping alert")
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.email_from
        msg["To"] = ", ".join(self.email_to)

        part = MIMEText(html_body, "html")
        msg.attach(part)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20) as server:
                server.starttls()
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.email_from, self.email_to, msg.as_string())
                logger.info("Alert email sent")
        except Exception as exc:
            logger.exception(f"Failed to send email: {exc}")


__all__ = ["EmailService"]