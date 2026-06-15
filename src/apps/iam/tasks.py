"""IAM-specific Celery email tasks (welcome, password reset, verification, new-IP)."""
from typing import Any, Dict

from celery import shared_task

from src.core.celery_app import celery_app  # noqa: F401 — bind tasks to configured app
from src.core.tasks import send_email


@shared_task(name="send_welcome_email_task")
def send_welcome_email_task(user_data: Dict[str, Any]) -> bool:
    """Send a welcome email after successful registration."""
    recipients = [{"name": user_data.get("username", ""), "email": user_data["email"]}]
    context = {
        "user": {"email": user_data["email"], "first_name": user_data.get("first_name", "")},
    }
    return send_email("Welcome to Our Service!", recipients, "iam/templates/emails/welcome.html", context)


@shared_task(name="send_password_reset_email_task")
def send_password_reset_email_task(user_data: Dict[str, Any], reset_url: str) -> bool:
    """Send a password-reset email."""
    recipients = [{"name": user_data.get("username", ""), "email": user_data["email"]}]
    context = {
        "user": {"email": user_data["email"], "first_name": user_data.get("first_name", "")},
        "reset_url": reset_url,
    }
    return send_email("Reset Your Password", recipients, "iam/templates/emails/password_reset.html", context)


@shared_task(name="send_verification_email_task")
def send_verification_email_task(user_data: Dict[str, Any], verification_url: str) -> bool:
    """Send an email-address verification email."""
    recipients = [{"name": user_data.get("username", ""), "email": user_data["email"]}]
    context = {
        "user": {"email": user_data["email"], "first_name": user_data.get("first_name", "")},
        "verification_url": verification_url,
    }
    return send_email("Verify Your Email Address", recipients, "iam/templates/emails/email_verification.html", context)
