"""IAM-specific email tasks."""

from typing import Any

from celery import shared_task

from src.apps.communication.services.communications import (
    communications_service,
)
from src.apps.communication.tasks import (
    run_async_from_sync,
)


@shared_task(
    name="send_welcome_email_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_welcome_email_task(
    user_data: dict[str, Any],
) -> bool:
    recipients = [
        {
            "name": user_data.get("username", ""),
            "email": user_data["email"],
        }
    ]

    context = {
        "user": {
            "email": user_data["email"],
            "first_name": user_data.get(
                "first_name",
                "",
            ),
        }
    }

    result = run_async_from_sync(
        communications_service.send_email,
        subject="Welcome to Our Service!",
        recipients=recipients,
        template_name="iam/templates/emails/welcome.html",
        context=context,
    )

    return result.success


@shared_task(
    name="send_password_reset_email_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_password_reset_email_task(
    user_data: dict[str, Any],
    reset_url: str,
) -> bool:
    recipients = [
        {
            "name": user_data.get("username", ""),
            "email": user_data["email"],
        }
    ]

    context = {
        "user": {
            "email": user_data["email"],
            "first_name": user_data.get(
                "first_name",
                "",
            ),
        },
        "reset_url": reset_url,
    }

    result = run_async_from_sync(
        communications_service.send_email,
        subject="Reset Your Password",
        recipients=recipients,
        template_name="iam/templates/emails/password_reset.html",
        context=context,
    )

    return result.success


@shared_task(
    name="send_verification_email_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_verification_email_task(
    user_data: dict[str, Any],
    verification_url: str,
) -> bool:
    recipients = [
        {
            "name": user_data.get("username", ""),
            "email": user_data["email"],
        }
    ]

    context = {
        "user": {
            "email": user_data["email"],
            "first_name": user_data.get(
                "first_name",
                "",
            ),
        },
        "verification_url": verification_url,
    }

    result = run_async_from_sync(
        communications_service.send_email,
        subject="Verify Your Email Address",
        recipients=recipients,
        template_name="iam/templates/emails/email_verification.html",
        context=context,
    )

    return result.success