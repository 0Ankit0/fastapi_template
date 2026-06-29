import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import httpx
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType, NameEmail
from jinja2 import Environment, FileSystemLoader

from src.core.config import settings
from src.core.http import default_timeout, retry_sync

from .interfaces import EmailProviderBase, PushProviderBase
from .schemas import DeliveryResult
from src.core.enums import EmailProvider, PushProvider

logger = logging.getLogger(__name__)


def render_template(template_dir: str, template_name: str, context: dict[str, Any]) -> str:
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(f"emails/{template_name}.html")
    return template.render(**context)


class SmtpEmailProvider(EmailProviderBase):
    name = EmailProvider.SMTP.value

    def is_configured(self) -> bool:
        return settings.EMAIL_ENABLED and bool(
            settings.EMAIL_HOST
            and settings.EMAIL_PORT
            and settings.EMAIL_HOST_USER
            and settings.EMAIL_FROM_ADDRESS
        )

    def send(
        self,
        *,
        subject: str,
        recipients: list[dict[str, str]],
        html_body: str,
        text_body: str | None = None,
    ) -> DeliveryResult:
        conf = ConnectionConfig(
            MAIL_USERNAME=settings.EMAIL_HOST_USER,
            MAIL_PASSWORD=settings.EMAIL_HOST_PASSWORD,
            MAIL_FROM=settings.EMAIL_FROM_ADDRESS,
            MAIL_PORT=int(settings.EMAIL_PORT),
            MAIL_SERVER=settings.EMAIL_HOST,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
            TEMPLATE_FOLDER=Path("."),
        )
        recipient_objects = [NameEmail(name=item.get("name", ""), email=item["email"]) for item in recipients]
        message = MessageSchema(
            subject=subject,
            recipients=recipient_objects,
            body=html_body,
            subtype=MessageType.html,
        )
        asyncio.run(FastMail(conf).send_message(message))
        return DeliveryResult(channel="email", provider=self.name, success=True)

class FcmPushProvider(PushProviderBase):
    name = PushProvider.FCM.value

    def is_configured(self) -> bool:
        return settings.PUSH_ENABLED and bool(
            settings.FCM_SERVER_KEY
            or (
                settings.FCM_PROJECT_ID
                and (
                    settings.FCM_SERVICE_ACCOUNT_JSON
                    or settings.FCM_SERVICE_ACCOUNT_FILE
                )
            )
        )

    def _access_token(self) -> str | None:
        if settings.FCM_SERVICE_ACCOUNT_JSON:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            info = json.loads(settings.FCM_SERVICE_ACCOUNT_JSON)
            credentials = service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/firebase.messaging"],
            )
            credentials.refresh(Request())
            return credentials.token

        if settings.FCM_SERVICE_ACCOUNT_FILE:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            credentials = service_account.Credentials.from_service_account_file(
                settings.FCM_SERVICE_ACCOUNT_FILE,
                scopes=["https://www.googleapis.com/auth/firebase.messaging"],
            )
            credentials.refresh(Request())
            return credentials.token

        return None

    def send(self, payload: dict[str, Any]) -> DeliveryResult:
        access_token = self._access_token()
        if access_token and settings.FCM_PROJECT_ID:
            response = retry_sync(
                lambda: httpx.post(
                    f"https://fcm.googleapis.com/v1/projects/{settings.FCM_PROJECT_ID}/messages:send",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "message": {
                            "token": payload["token"],
                            "notification": {
                                "title": payload["title"],
                                "body": payload["body"],
                            },
                            "data": payload.get("data") or {},
                        }
                    },
                    timeout=default_timeout(),
                )
            )
        else:
            response = retry_sync(
                lambda: httpx.post(
                    "https://fcm.googleapis.com/fcm/send",
                    headers={
                        "Authorization": f"key={settings.FCM_SERVER_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "to": payload["token"],
                        "notification": {
                            "title": payload["title"],
                            "body": payload["body"],
                        },
                        "data": payload.get("data") or {},
                    },
                    timeout=default_timeout(),
                )
            )
        response.raise_for_status()
        data = response.json()
        return DeliveryResult(
            channel="push",
            provider=self.name,
            success=bool(data.get("name")) or data.get("failure", 0) == 0,
            metadata=data,
        )
