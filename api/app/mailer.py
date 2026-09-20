from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

log = logging.getLogger(__name__)


def send_mail(to: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
            smtp.send_message(message)
    except OSError:
        log.exception("SMTP send failed to %s (%s)", to, subject)


def send_confirm_email(to: str, raw_token: str) -> None:
    link = f"{settings.PUBLIC_APP_URL.rstrip('/')}/api/auth/confirm?token={raw_token}"
    send_mail(
        to,
        "Confirm Your Email",
        f"Confirm your ARPW account:\n\n{link}\n",
    )


def send_reset_email(to: str, raw_token: str) -> None:
    link = f"{settings.PUBLIC_APP_URL.rstrip('/')}/reset-password?token={raw_token}"
    send_mail(
        to,
        "Reset Your Password",
        f"Reset your ARPW password:\n\n{link}\n",
    )
