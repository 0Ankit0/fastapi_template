from __future__ import annotations

import logging
from typing import cast

from celery import Task
from starlette.datastructures import URL
from src.apps.iam.models.user import User
from src.core.config import settings
from src.main import app

logger = logging.getLogger(__name__)

class OrganizationEmailService:
    @staticmethod
    async def send_member_invitation_email(
        user: User | None,
        email: str | None,
        token: str,
        org_slug: str,
        url: URL,
    ) -> None:
        from src.apps.organizations.tasks import send_organization_member_invitation_email_task
        from src.core.security import create_secure_url_token

        task = cast(Task, send_organization_member_invitation_email_task)

        secure_token = create_secure_url_token(
            {
                "user_id": user.id if user else email,
                "org_slug": org_slug, 
                "token": token,
                "purpose": "organization_invitation",
            },
            expires_hours=1,
        )
        invitation_link = (
            f"{url}"
            f"?t={secure_token}"
        )
        task.delay(
            {
                "id": user.id if user else email,
                "email": user.email if user else email,
                "username": user.username if user else None,
                "first_name": user.profile.first_name if user else None,
                "org_slug": org_slug,
            },
            invitation_link,
            org_slug,
        )
        logger.info(
            "organization_member_invitation_email_task_queued user_id=%s email=%s organization=%s",
            user.id if user else email,
            user.email if user else email,
            org_slug,
        )
