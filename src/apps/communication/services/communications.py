from __future__ import annotations

from typing import Any

from src.core.config import settings
from src.core.logging import get_logger

from ..providers import FcmPushProvider
from ..schemas import (
    CapabilitySummary,
    DeliveryResult,
    ProviderStatus,
)
from .email import email_service

logger = get_logger(__name__)


class CommunicationsService:
    def __init__(self) -> None:
        self._email_service = email_service

        self._push_providers = {
            "fcm": FcmPushProvider(),
        }

    async def send_email(
        self,
        *,
        subject: str,
        recipients: list[dict[str, str]],
        template_name: str,
        context: dict[str, Any],
        inline_template: bool = False,
    ) -> DeliveryResult:
        try:
            if inline_template:
                html_body = str(context.get("html_body", ""))
            else:
                html_body = self._email_service.render_template(
                    template_name=template_name,
                    context=context,
                )

            text_body = (
                str(context["text_body"])
                if context.get("text_body") is not None
                else None
            )

            if not settings.EMAIL_SERVICE_ENABLED and settings.DEBUG:
                sep = "=" * 80
                print(f"\n{sep}\n📧 DEV EMAIL OUTBOX\n{sep}")
                print(f"To:       {[r['email'] for r in recipients]}")
                print(f"Subject:  {subject}")
                print(f"Template: {template_name}")
                print(f"{sep}\n{html_body}\n{sep}\n", flush=True)

                logger.info(
                    "DEV EMAIL template=%s recipients=%s",
                    template_name,
                    [r["email"] for r in recipients],
                )

                return DeliveryResult(
                    channel="email",
                    provider="dev",
                    success=True,
                )

            if not self._email_service.is_configured():
                return DeliveryResult(
                    channel="email",
                    provider=settings.EMAIL_PROVIDER,
                    success=False,
                    error="Email service not configured",
                )

            result = await self._email_service.send(
                subject=subject,
                recipients=recipients,
                html_body=html_body,
                text_body=text_body,
            )

            logger.info(
                "email_delivery provider=%s success=%s",
                result.provider,
                result.success,
            )

            return result

        except Exception as exc:
            logger.exception(
                "email_delivery_failed provider=%s",
                settings.EMAIL_PROVIDER,
            )

            return DeliveryResult(
                channel="email",
                provider=settings.EMAIL_PROVIDER,
                success=False,
                error=str(exc),
            )

    def send_push(
        self,
        payload: dict[str, Any],
    ) -> DeliveryResult:
        target_provider = str(
            payload.get("provider") or settings.PUSH_PROVIDER
        )

        provider = self._push_providers.get(target_provider)

        if not provider:
            return DeliveryResult(
                channel="push",
                provider=target_provider,
                success=False,
                error="Provider not found",
            )

        if not provider.is_configured():
            return DeliveryResult(
                channel="push",
                provider=target_provider,
                success=False,
                error="Provider not configured",
            )

        try:
            result = provider.send(payload)

            logger.info(
                "push_delivery provider=%s success=%s",
                provider.name,
                result.success,
            )

            return result

        except Exception as exc:
            logger.exception(
                "push_delivery_failed provider=%s",
                provider.name,
            )

            return DeliveryResult(
                channel="push",
                provider=provider.name,
                success=False,
                error=str(exc),
            )

    def get_capabilities(self) -> CapabilitySummary:
        return CapabilitySummary(
            active_providers={
                "email": (
                    settings.EMAIL_PROVIDER
                    if settings.EMAIL_ENABLED
                    else None
                ),
                "push": (
                    settings.PUSH_PROVIDER if settings.PUSH_ENABLED else None
                ),
            }
        )

    def get_provider_statuses(self) -> list[ProviderStatus]:
        statuses: list[ProviderStatus] = []

        statuses.append(
            ProviderStatus(
                channel="email",
                provider=settings.EMAIL_PROVIDER,
                active=settings.EMAIL_ENABLED,
                enabled=settings.EMAIL_ENABLED,
                configured=self._email_service.is_configured(),
            )
        )

        for name, provider in self._push_providers.items():
            statuses.append(
                ProviderStatus(
                    channel="push",
                    provider=name,
                    active=name == settings.PUSH_PROVIDER,
                    enabled=settings.PUSH_ENABLED,
                    configured=provider.is_configured(),
                )
            )

        return statuses


communications_service = CommunicationsService()