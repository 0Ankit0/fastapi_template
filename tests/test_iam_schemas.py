from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.apps.iam.schemas.user import LoginRequest, UserCreate


def test_user_create_rejects_password_mismatch() -> None:
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            username="tester",
            email="tester@example.com",
            password="StrongPass1!",
            confirm_password="DifferentPass1!",
        )

    assert "Passwords do not match" in str(exc_info.value)


def test_user_create_rejects_weak_password() -> None:
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            username="tester",
            email="tester@example.com",
            password="weak",
            confirm_password="weak",
        )

    assert "Password must be at least" in str(exc_info.value)


def test_login_request_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(username="tester", password="StrongPass1!", unexpected=True)
