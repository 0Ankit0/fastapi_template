import pytest

from src.apps.communications.service import CommunicationsService
from src.apps.communications.types import DeliveryResult
from src.apps.core.config import settings


class _StubProvider:
    def __init__(self, name: str, *, configured: bool = True, success: bool = True) -> None:
        self.name = name
        self._configured = configured
        self._success = success
        self.calls = 0

    def is_configured(self) -> bool:
        return self._configured

    def send(self, **_: object) -> DeliveryResult:
        self.calls += 1
        return DeliveryResult(
            channel="email",
            provider=self.name,
            success=self._success,
            error=None if self._success else f"{self.name} failed",
        )


@pytest.mark.unit
def test_send_email_falls_back_to_next_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    service = CommunicationsService()
    primary = _StubProvider("smtp", success=False)
    fallback = _StubProvider("resend", success=True)
    service._email_providers = {"smtp": primary, "resend": fallback}  # type: ignore[attr-defined]

    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "smtp")
    monkeypatch.setattr(settings, "EMAIL_FALLBACK_PROVIDERS", ["resend"])

    result = service.send_email(
        subject="Template test",
        recipients=[{"email": "demo@example.com"}],
        template_name="ignored",
        context={"html_body": "<p>Hello</p>"},
        template_dir=".",
        inline_template=True,
    )

    assert primary.calls == 1
    assert fallback.calls == 1
    assert result.success is True
    assert result.provider == "resend"


@pytest.mark.unit
def test_provider_statuses_include_analytics() -> None:
    service = CommunicationsService()
    channels = {status.channel for status in service.get_provider_statuses()}
    assert {"email", "push", "sms", "analytics"}.issubset(channels)
