import logging
from pathlib import Path
from typing import Any, Dict, List
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr
from app.core.config import settings
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# Basic Template Setup (if not using fastapi-mail's internal template support)
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

class EmailService:
    @staticmethod
    async def send_email(
        subject: str,
        recipients: List[EmailStr],
        template_name: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Send an email using a template.
        NOTE: This requires SMTP settings in env (MAIL_USERNAME, etc.)
        For now, we'll log if settings are missing.
        """
        if not settings.EMAIL_HOST:
             logger.info(f"Mock Sending Email: {subject} to {recipients}. Template: {template_name}")
             return

        # Configure fastapi-mail
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

        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            template_body=context,
            subtype=MessageType.html
        )

        fm = FastMail(conf)
        try:
            await fm.send_message(message, template_name=f"emails/{template_name}.html")
            logger.info(f"Email sent to {recipients}: {subject}")
        except Exception as e:
            logger.error(f"Error sending email: {e}")

    @staticmethod
    async def send_welcome_email(user) -> None:
         await EmailService.send_email(
             subject="Welcome to Django Template Platform",
             recipients=[user.email],
             template_name="welcome",
             context={"user": {"email": user.email, "first_name": getattr(user, "first_name", "")}}
         )

    @staticmethod
    async def send_password_reset_email(user, token: str) -> None:
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        await EmailService.send_email(
            subject="Reset Your Password",
            recipients=[user.email],
            template_name="password_reset",
            context={"user": {"email": user.email}, "reset_url": reset_url}
        )
