from __future__ import annotations

import logging
from typing import Any, cast

from celery import Task, security
from apps.iam.models import user
from apps.iam.models.user import User
from src.core.config import settings

logger = logging.getLogger(__name__)

class OrganizationEmailService:
    @staticmethod
    async def send_member_invitation_email(
        user: User,
        token: str,
        organization_name: str,
    ) -> None:
        from src.apps.organizations.tasks import send_organization_member_invitation_email_task
        from src.core.security import create_secure_url_token

        task = cast(Task, send_organization_member_invitation_email_task)

        secure_token = create_secure_url_token(
            {
                "user_id": user.id,
                "token": token,
                "purpose": "organization_invitation",
            },
            expires_hours=1,
        )
        invitation_link = (
            f"{settings.FRONTEND_URL}/accept-invitation"
            f"?t={secure_token}"
        )
        task.delay(
            {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "first_name": user.profile.first_name,
            },
            invitation_link,
            organization_name,
        )
        logger.info(
            "organization_member_invitation_email_task_queued user_id=%s email=%s organization=%s",
            user.id,
            user.email,
            organization_name,
        )