import logging
from pathlib import Path
from typing import Any, Dict, List
from celery import shared_task
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType, NameEmail
from jinja2 import Environment, FileSystemLoader
from src.apps.core.config import settings

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "apps" / "iam" / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


@shared_task(name="send_email_task")
def send_email_task(
    subject: str,
    recipients: List[Dict[str, str]],
    template_name: str,
    context: Dict[str, Any],
) -> bool:
    """Send an email using a template via Celery task"""
    if not settings.EMAIL_ENABLED:
        logger.info(f"Mock Sending Email: Subject: {subject}, Recipients: {recipients}, Template: {template_name}")
        return True
    
    try:
        # Create email configuration
        conf = ConnectionConfig(
            MAIL_USERNAME=settings.EMAIL_HOST_USER,
            MAIL_PASSWORD=settings.EMAIL_HOST_PASSWORD,
            MAIL_FROM=settings.EMAIL_FROM_ADDRESS,
            MAIL_PORT=int(settings.EMAIL_PORT),
            MAIL_SERVER=settings.EMAIL_HOST,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
            TEMPLATE_FOLDER=TEMPLATE_DIR
        )
        
        # Convert recipients list of dicts to NameEmail objects
        recipient_objects = [NameEmail(name=r.get("name", ""), email=r["email"]) for r in recipients]
        
        message = MessageSchema(
            subject=subject,
            recipients=recipient_objects,
            template_body=context,
            subtype=MessageType.html
        )
        
        fm = FastMail(conf)
        # Note: FastMail.send_message is async, but Celery tasks are sync
        # We need to use asyncio to run the async function
        import asyncio
        asyncio.run(fm.send_message(message, template_name=f"emails/{template_name}.html"))
        
        logger.info(f"Email sent successfully: Subject: {subject}, Recipients: {recipients}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


@shared_task(name="send_welcome_email_task")
def send_welcome_email_task(user_data: Dict[str, Any]) -> bool:
    """Send welcome email task"""
    recipients = [{"name": user_data.get("username", ""), "email": user_data["email"]}]
    context = {"user": {"email": user_data["email"], "first_name": user_data.get("first_name", "")}}
    return send_email_task("Welcome to Our Service!", recipients, "welcome", context)


@shared_task(name="send_password_reset_email_task")
def send_password_reset_email_task(user_data: Dict[str, Any], reset_url: str) -> bool:
    """Send password reset email task"""
    recipients = [{"name": user_data.get("username", ""), "email": user_data["email"]}]
    context = {
        "user": {"email": user_data["email"], "first_name": user_data.get("first_name", "")},
        "reset_url": reset_url
    }
    return send_email_task("Reset Your Password", recipients, "password_reset", context)


@shared_task(name="send_verification_email_task")
def send_verification_email_task(user_data: Dict[str, Any], verification_url: str) -> bool:
    """Send email verification task"""
    recipients = [{"name": user_data.get("username", ""), "email": user_data["email"]}]
    context = {
        "user": {"email": user_data["email"], "first_name": user_data.get("first_name", "")},
        "verification_url": verification_url
    }
    return send_email_task("Verify Your Email Address", recipients, "email_verification", context)


@shared_task(name="send_new_ip_notification_task")
def send_new_ip_notification_task(
    user_data: Dict[str, Any],
    ip_address: str,
    whitelist_url: str,
    blacklist_url: str
) -> bool:
    """Send new IP notification email task"""
    recipients = [{"name": user_data.get("username", ""), "email": user_data["email"]}]
    context = {
        "user": {"email": user_data["email"], "first_name": user_data.get("first_name", "")},
        "ip_address": ip_address,
        "whitelist_url": whitelist_url,
        "blacklist_url": blacklist_url
    }
    return send_email_task("New IP Address Login Attempt", recipients, "new_ip_notification", context)
