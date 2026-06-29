from __future__ import annotations

import logging
from typing import Any, cast

from celery import Task

from src.apps.iam.models.user import User
from src.core.config import settings

logger = logging.getLogger(__name__)


class AuthEmailService:
    @staticmethod
    async def send_email(
        *,
        subject: str,
        recipients: list[dict[str, str]],
        template_name: str,
        context: dict[str, Any],
    ) -> None:
        from src.apps.communication.tasks import send_email_task
        task = cast(Task, send_email_task)

        task.delay(
            subject=subject,
            recipients=recipients,
            template_name=template_name,
            context=context,
        )

        logger.info(
            "email_task_queued template=%s recipients=%s",
            template_name,
            [r["email"] for r in recipients],
        )

    @staticmethod
    async def send_welcome_email(user: Any) -> None:
        from src.apps.iam.tasks import send_welcome_email_task
        task = cast(Task, send_welcome_email_task)

        task.delay(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": getattr(user, "first_name", ""),
            }
        )

        logger.info(
            "welcome_email_task_queued user_id=%s email=%s",
            user.id,
            user.email,
        )

    @staticmethod
    async def send_password_reset_email(
        user: Any,
        token: str,
    ) -> None:
        from src.core import security
        from src.apps.iam.tasks import send_password_reset_email_task

        secure_token = security.create_secure_url_token(
            {
                "user_id": user.id,
                "token": token,
                "purpose": "password_reset",
            },
            expires_hours=1,
        )

        reset_url = (
            f"{settings.FRONTEND_URL}/reset-password"
            f"?t={secure_token}"
        )

        task = cast(Task, send_password_reset_email_task)
        task.delay(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": getattr(user, "first_name", ""),
            },
            reset_url,
        )

        logger.info(
            "password_reset_email_task_queued user_id=%s",
            user.id,
        )

    @staticmethod
    async def send_verification_email(
        user: User,
        token: str,
    ) -> None:
        from src.core import security
        from src.apps.iam.tasks import send_verification_email_task

        secure_token = security.create_secure_url_token(
            {
                "user_id": user.id,
                "token": token,
                "purpose": "email_verification",
            },
            expires_hours=24,
        )

        verification_url = (
            f"{settings.FRONTEND_URL}/verify-email"
            f"?t={secure_token}"
        )

        task = cast(Task, send_verification_email_task)
        task.delay(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": getattr(user, "first_name", ""),
            },
            verification_url,
        )

        logger.info(
            "verification_email_task_queued user_id=%s",
            user.id,
        )


auth_email_service = AuthEmailService()