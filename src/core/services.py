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
from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.config import settings
from core.logging import get_logger
from .schemas import DeliveryResult

logger = get_logger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

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

    async def send_email(
        self,
        *,
        subject: str,
        recipients: list[dict[str, str]],
        template_name: str,
        context: dict[str, Any],
        inline_template: bool = False,
    ) -> DeliveryResult:
        try:
            if inline_template:
                html_body = str(context.get("html_body", ""))
            else:
                html_body = email_templates.get_template(
                    template_name
                ).render(**context)

            text_body = (
                str(context["text_body"])
                if context.get("text_body") is not None
                else None
            )

            result = await self.send(
                subject=subject,
                recipients=recipients,
                html_body=html_body,
                text_body=text_body,
            )

            logger.info(
                "email_delivery provider=%s success=%s",
                settings.EMAIL_PROVIDER,
                result.success,
            )

            return result

        except Exception as exc:
            logger.exception(
                "email_delivery_failed provider=%s",
                settings.EMAIL_PROVIDER,
            )

            return DeliveryResult(
                channel="email",
                provider=settings.EMAIL_PROVIDER,
                success=False,
                error=str(exc),
            )


email_service = EmailService()