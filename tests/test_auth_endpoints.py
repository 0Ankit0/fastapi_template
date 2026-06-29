from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

from src.core.enums import UserStatus

from conftest import FakeDB, FakeExecuteResult


def signup_payload(**overrides):
    payload = {
        "username": "tester",
        "email": "tester@example.com",
        "password": "StrongPass1!",
        "confirm_password": "StrongPass1!",
        "first_name": "Test",
        "last_name": "User",
        "phone": "1234567890",
    }
    payload.update(overrides)
    return payload


def test_signup_rejects_duplicate_username(auth_client) -> None:
    client, db_holder, _ = auth_client
    db = FakeDB(FakeExecuteResult(value=SimpleNamespace(id=1, username="tester")))
    db_holder["db"] = db

    response = client.post("/api/v1/auth/signup/", json=signup_payload())

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Username already exists"
    assert db.rollbacks == 1


def test_signup_success_returns_tokens_and_tracks_session(auth_client, monkeypatch, fake_expiration) -> None:
    from src.apps.iam.services.email import AuthEmailService
    from src.core.cache import RedisCache

    client, db_holder, modules = auth_client
    register = modules["register"]
    db = FakeDB(FakeExecuteResult(value=None))
    db_holder["db"] = db

    sent_welcome: list[int] = []

    monkeypatch.setattr(register.security, "get_password_hash", lambda password: f"hashed:{password}")
    monkeypatch.setattr(register.security, "create_access_token", lambda *args, **kwargs: "access-token")
    monkeypatch.setattr(register.security, "create_refresh_token", lambda *args, **kwargs: "refresh-token")
    monkeypatch.setattr(
        register.security,
        "decode_token",
        lambda token: {"jti": f"{token}-jti", "exp": fake_expiration.isoformat()},
    )
    monkeypatch.setattr(register.security, "payload_expiration", lambda payload: fake_expiration)

    async def fake_revoke_tokens_for_ip(*args, **kwargs):
        return None

    async def fake_clear_pattern(pattern: str):
        return 0

    async def fake_send_welcome_email(user):
        sent_welcome.append(user.id)

    monkeypatch.setattr(register, "revoke_tokens_for_ip", fake_revoke_tokens_for_ip)
    monkeypatch.setattr(RedisCache, "clear_pattern", fake_clear_pattern)
    monkeypatch.setattr(AuthEmailService, "send_welcome_email", fake_send_welcome_email)

    response = client.post("/api/v1/auth/signup/", json=signup_payload())

    assert response.status_code == 200
    assert response.json()["message"] == "Account created successfully"
    assert response.json()["data"] == {
        "access": "access-token",
        "refresh": "refresh-token",
        "token_type": "bearer",
    }
    assert sent_welcome == [1]
    assert db.commits == 2
    assert [item.__class__.__name__ for item in db.added].count("TokenTracking") == 2


def test_resend_verification_uses_generic_message_for_unknown_email(auth_client, monkeypatch) -> None:
    from src.apps.iam.services.email import AuthEmailService

    client, db_holder, _ = auth_client
    db_holder["db"] = FakeDB(FakeExecuteResult(value=None))

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("Verification email should not be sent")

    monkeypatch.setattr(AuthEmailService, "send_verification_email", fail_if_called)

    response = client.post("/api/v1/auth/resend-verification/", json={"email": "missing@example.com"})

    assert response.status_code == 200
    assert response.json()["message"] == "If an account with that email exists, a verification email has been sent"


def test_resend_verification_queues_email_for_existing_user(auth_client, monkeypatch) -> None:
    from src.apps.iam.services.email import AuthEmailService

    user = SimpleNamespace(id=5, email="tester@example.com", username="tester")
    client, db_holder, modules = auth_client
    register = modules["register"]
    db_holder["db"] = FakeDB(FakeExecuteResult(value=user))
    sent: dict[str, object] = {}

    monkeypatch.setattr(register.security, "create_email_verification_token", lambda user_id: "email-token")

    async def fake_send_verification_email(sent_user, token):
        sent["user"] = sent_user
        sent["token"] = token

    monkeypatch.setattr(AuthEmailService, "send_verification_email", fake_send_verification_email)

    response = client.post("/api/v1/auth/resend-verification/", json={"email": "tester@example.com"})

    assert response.status_code == 200
    assert sent == {"user": user, "token": "email-token"}


def test_login_rejects_unknown_user(auth_client) -> None:
    client, db_holder, _ = auth_client
    db = FakeDB(FakeExecuteResult(value=None))
    db_holder["db"] = db

    response = client.post(
        "/api/v1/auth/login/",
        json={"username": "missing", "password": "StrongPass1!"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Invalid username or password"
    assert db.commits == 1
    assert db.rollbacks == 1
    assert db.added[0].__class__.__name__ == "LoginAttempt"


def test_login_success_returns_tokens_and_tracks_session(auth_client, monkeypatch, fake_expiration) -> None:
    client, db_holder, modules = auth_client
    login = modules["login"]
    user = SimpleNamespace(
        id=3,
        username="tester",
        password_hash="hashed-password",
        is_confirmed=True,
        status=UserStatus.ACTIVE,
        otp_enabled=False,
        otp_verified=False,
    )
    db = FakeDB(
        FakeExecuteResult(value=user),
        FakeExecuteResult(values=[]),
    )
    db_holder["db"] = db

    monkeypatch.setattr(login.security, "verify_password", lambda password, password_hash: True)
    monkeypatch.setattr(login.security, "create_access_token", lambda *args, **kwargs: "access-token")
    monkeypatch.setattr(login.security, "create_refresh_token", lambda *args, **kwargs: "refresh-token")
    monkeypatch.setattr(
        login.security,
        "decode_token",
        lambda token: {"jti": f"{token}-jti", "exp": fake_expiration.isoformat()},
    )
    monkeypatch.setattr(login.security, "payload_expiration", lambda payload: fake_expiration)
    monkeypatch.setattr(login.settings, "REQUIRE_EMAIL_VERIFICATION", True)
    monkeypatch.setattr(login.settings, "MAX_LOGIN_ATTEMPTS", 5)
    monkeypatch.setattr(login.settings, "ACCOUNT_LOCKOUT_DURATION_MINUTES", 15)

    async def fake_revoke_tokens_for_ip(*args, **kwargs):
        return None

    monkeypatch.setattr(login, "revoke_tokens_for_ip", fake_revoke_tokens_for_ip)

    response = client.post(
        "/api/v1/auth/login/",
        json={"username": "tester", "password": "StrongPass1!"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Logged in successfully"
    assert response.json()["data"] == {
        "access": "access-token",
        "refresh": "refresh-token",
        "token_type": "bearer",
    }
    assert db.commits == 3
    assert [item.__class__.__name__ for item in db.added].count("TokenTracking") == 2
    assert [item.__class__.__name__ for item in db.added].count("LoginAttempt") == 2
