from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi_mail import (
    ConnectionConfig,
    FastMail,
    MessageSchema,
    MessageType,
    NameEmail,
)
from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
)

from src.core.config import settings
from src.core.logging import get_logger

from ..schemas import DeliveryResult

logger = get_logger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parents[2] 

email_templates = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


class EmailService:
    def __init__(self) -> None:
        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.EMAIL_HOST_USER,
            MAIL_PASSWORD=settings.EMAIL_HOST_PASSWORD,
            MAIL_FROM=settings.EMAIL_FROM_ADDRESS,
            MAIL_PORT=int(settings.EMAIL_PORT),
            MAIL_SERVER=settings.EMAIL_HOST,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
            TEMPLATE_FOLDER=TEMPLATES_DIR,
        )

    def is_configured(self) -> bool:
        return settings.EMAIL_ENABLED and all(
            (
                settings.EMAIL_HOST,
                settings.EMAIL_PORT,
                settings.EMAIL_HOST_USER,
                settings.EMAIL_FROM_ADDRESS,
            )
        )

    def render_template(
        self,
        template_name: str,
        context: dict[str, Any],
    ) -> str:
        return email_templates.get_template(
            template_name
        ).render(**context)

    async def send(
        self,
        *,
        subject: str,
        recipients: list[dict[str, str]],
        html_body: str,
        text_body: str | None = None,
    ) -> DeliveryResult:
        recipient_objects = [
            NameEmail(
                name=item.get("name", ""),
                email=item["email"],
            )
            for item in recipients
        ]

        message = MessageSchema(
            subject=subject,
            recipients=recipient_objects,
            body=html_body,
            subtype=MessageType.html,
        )

        await FastMail(self.conf).send_message(message)

        return DeliveryResult(
            channel="email",
            provider="smtp",
            success=True,
        )


email_service = EmailService()