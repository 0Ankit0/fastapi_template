
import logging
from pathlib import Path
from src.apps.core.config import settings
from fastapi_mail import ConnectionConfig,FastMail,MessageSchema,MessageType, NameEmail
from typing import Any,Dict,List
from jinja2 import Environment,FileSystemLoader

logger = logging.getLogger(__name__)

# Basic Template setup
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

class EmailService:
    @staticmethod
    async def send_email(
        subject: str,
        recipients: List[NameEmail],
        template_name: str,
        context: Dict[str, Any],
    ) -> None:
        """send an email using a template.
        NOTE: This requires SMTP settings in env (e.g. SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD)
        for now, we'll log if the settings are missing.
        """
        if not settings.EMAIL_ENABLED:
            logger.info(f"Mock Sending Email: Subject: {subject}, Recipients: {recipients}, Template: {template_name}, Context: {context}")
            return
        
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

        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            template_body=context,
            subtype=MessageType.html
        )

        fm = FastMail(conf)
        try:
            await fm.send_message(message, template_name=f"emails/{template_name}.html")
            logger.info(f"Email sent successfully: Subject: {subject}, Recipients: {recipients}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    @staticmethod
    async def send_welcome_email(user) -> None:
        await EmailService.send_email(
            subject="Welcome to Our Service!",
            recipients=[NameEmail(name=user.name, email=user.email)],
            template_name="welcome",
            context={"user": {"email":user.email, "first_name": getattr(user, 'first_name', '')}}
        )

    @staticmethod
    async def send_password_reset_email(user, token:str) -> None:
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        await EmailService.send_email(
            subject="Reset Your Password",
            recipients=[NameEmail(name=user.name, email=user.email)],
            template_name="password_reset",
            context={"user": {"email":user.email, "first_name": getattr(user, 'first_name', '')}, "reset_url": reset_url}
        )

    @staticmethod
    async def send_verification_email(user, token: str) -> None:
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        await EmailService.send_email(
            subject="Verify Your Email Address",
            recipients=[NameEmail(name=getattr(user, 'first_name', ''), email=user.email)],
            template_name="email_verification",
            context={"user": {"email": user.email, "first_name": getattr(user, 'first_name', '')}, "verification_url": verification_url}
        )