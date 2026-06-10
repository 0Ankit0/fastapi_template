import asyncio
import logging
from typing import Any

from celery import shared_task

from src.core.celery_app import celery_app  # noqa: F401
from src.core.config import settings

logger = logging.getLogger(__name__)


@shared_task(name="send_email_task")
def send_email_task(
    subject: str,
    recipients: list[dict[str, str]],
    template_name: str,
    context: dict[str, Any],
    inline_template: bool = False,
) -> bool:
    if not settings.EMAIL_SERVICE_ENABLED and settings.DEBUG:
        sep = "=" * 60
        lines = [
            "",
            sep,
            "  DEV EMAIL (not sent)",
            sep,
            f"  To      : {', '.join(r['email'] for r in recipients)}",
            f"  Subject : {subject}",
            f"  Template: {template_name}",
            sep,
            "",
        ]
        print("\n".join(lines), flush=True)
        return True

    try:
        email_service = get_email_service()

        result = asyncio.run(
            email_service.send_email(
                subject=subject,
                recipients=recipients,
                template_name=template_name,
                context=context,
                inline_template=inline_template,
            )
        )

        if not result.success:
            logger.error(
                "Failed to send email via %s: %s",
                result.provider,
                result.error,
            )

        return result.success

    except Exception:
        logger.exception("Failed to send email")
        return False


def get_email_service():
    from src.core.services import email_service

    return email_service