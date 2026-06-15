import logging
from collections.abc import Awaitable, Callable
from threading import Thread
from typing import Any

import anyio
from celery import shared_task

from src.core.celery_app import celery_app  # noqa: F401
from src.core.config import settings

logger = logging.getLogger(__name__)


def run_async_from_sync[T](func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
    async def wrapper() -> T:
        return await func(*args, **kwargs)

    try:
        anyio.get_current_task()
    except RuntimeError:
        return anyio.run(wrapper)

    result: T | None = None
    error: BaseException | None = None

    def runner() -> None:
        nonlocal result, error
        try:
            result = anyio.run(wrapper)
        except BaseException as exc:
            error = exc

    thread = Thread(target=runner)
    thread.start()
    thread.join()

    if error is not None:
        raise error

    return result  # type: ignore[return-value]


async def send_email_async(
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
            f"  Context : {context}",
            f"  Template: {template_name}",
            sep,
            "",
        ]
        print("\n".join(lines), flush=True)
        return True

    try:
        email_service = get_email_service()

        result = await email_service.send_email(
            subject=subject,
            recipients=recipients,
            template_name=template_name,
            context=context,
            inline_template=inline_template,
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


def send_email(
    subject: str,
    recipients: list[dict[str, str]],
    template_name: str,
    context: dict[str, Any],
    inline_template: bool = False,
) -> bool:
    return run_async_from_sync(
        send_email_async,
        subject,
        recipients,
        template_name,
        context,
        inline_template,
    )


@shared_task(name="send_email_task")
def send_email_task(
    subject: str,
    recipients: list[dict[str, str]],
    template_name: str,
    context: dict[str, Any],
    inline_template: bool = False,
) -> bool:
    return send_email(
        subject=subject,
        recipients=recipients,
        template_name=template_name,
        context=context,
        inline_template=inline_template,
    )


def get_email_service():
    from src.core.services import email_service

    return email_service
