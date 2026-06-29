from __future__ import annotations

from types import SimpleNamespace

import anyio

from apps.iam.models.user import User


def test_core_email_task_returns_bool_in_dev_mode() -> None:
    from src.apps.communication.tasks import send_email_task

    result = send_email_task(
        subject="Hello",
        recipients=[{"name": "Tester", "email": "tester@example.com"}],
        template_name="iam/templates/emails/welcome.html",
        context={"user": {"email": "tester@example.com", "first_name": "Test"}},
    )

    assert result is True


def test_eager_task_delay_from_async_context_returns_bool() -> None:
    from src.apps.iam.tasks import send_verification_email_task
    result = send_verification_email_task(
        {"id": 1, "username": "tester", "email": "tester@example.com", "first_name": "Test"},
        "https://example.com/verify",
    )
    assert result is True


def test_iam_email_tasks_return_delivery_status() -> None:
    from src.apps.iam.tasks import (
        send_password_reset_email_task,
        send_verification_email_task,
        send_welcome_email_task,
    )

    user_data = {"id": 1, "username": "tester", "email": "tester@example.com", "first_name": "Test"}

    assert send_welcome_email_task(user_data) is True
    assert send_password_reset_email_task(user_data, "https://example.com/reset") is True
    assert send_verification_email_task(user_data, "https://example.com/verify") is True


def test_organization_invitation_task_returns_delivery_status() -> None:
    from src.apps.organizations.tasks import send_organization_member_invitation_email_task

    result = send_organization_member_invitation_email_task(
        {"id": 1, "username": "tester", "email": "tester@example.com", "first_name": "Test"},
        "https://example.com/invite",
        "Acme",
    )

    assert result is True


def test_auth_email_service_queues_verification_email(monkeypatch) -> None:
    from src.apps.iam.services.email import AuthEmailService
    from src.apps.iam.tasks import send_verification_email_task
    from src.core import security

    calls: dict[str, object] = {}

    def fake_secure_url_token(data, expires_hours):
        calls["secure_data"] = data
        calls["expires_hours"] = expires_hours
        return "secure-token"

    def fake_delay(user_data, verification_url):
        calls["user_data"] = user_data
        calls["verification_url"] = verification_url

    monkeypatch.setattr(security, "create_secure_url_token", fake_secure_url_token)
    monkeypatch.setattr(send_verification_email_task, "delay", fake_delay)

    user = User(id=7, username="tester", email="tester@example.com", first_name="Test")
    anyio.run(AuthEmailService.send_verification_email, user, "email-token")

    assert calls["secure_data"] == {
        "user_id": 7,
        "token": "email-token",
        "purpose": "email_verification",
    }
    assert calls["expires_hours"] == 24
    assert calls["verification_url"] == "http://localhost:3000/verify-email?t=secure-token"
    assert calls["user_data"] == {
        "id": 7,
        "username": "tester",
        "email": "tester@example.com",
        "first_name": "Test",
    }
