from typing import Any, Dict

from celery import shared_task

from src.core.celery_app import celery_app  # noqa: F401
from src.core.tasks import send_email


@shared_task(name="send_organization_member_invitation_email_task")
def send_organization_member_invitation_email_task(
    user_data: Dict[str, Any],
    invitation_link: str,
    organization_name: str,
) -> bool:
    """Send an invitation email to a user to join an organization."""
    recipients = [{"name": user_data.get("username", ""), "email": user_data["email"]}]
    context = {
        "user_name": user_data.get("first_name", ""),
        "organization_name": organization_name,
        "invitation_link": invitation_link,
    }
    return send_email(
        f"You're Invited to Join {organization_name}!",
        recipients,
        "organizations/templates/emails/member_invitation.html",
        context,
    )
