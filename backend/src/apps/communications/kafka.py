import json
from typing import Any

from src.apps.core.config import settings


class KafkaService:
    def __init__(self) -> None:
        self._producer: Any | None = None
        self._started = False

    @property
    def enabled(self) -> bool:
        return bool(settings.KAFKA_ENABLED)

    def is_configured(self) -> bool:
        return self.enabled and bool(settings.KAFKA_BOOTSTRAP_SERVERS)

    def build_topic_name(self, topic: str | None = None) -> str:
        raw_topic = (topic or settings.KAFKA_DEFAULT_TOPIC).strip(".")
        prefix = settings.KAFKA_TOPIC_PREFIX.strip(".")
        return f"{prefix}.{raw_topic}" if prefix else raw_topic

    async def start(self) -> None:
        if not self.enabled or self._started:
            return

        try:
            from aiokafka import AIOKafkaProducer
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Kafka is enabled but aiokafka is not installed. Add the dependency and sync the backend environment."
            ) from exc

        producer_kwargs: dict[str, Any] = {
            "bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "client_id": settings.KAFKA_CLIENT_ID,
            "security_protocol": settings.KAFKA_SECURITY_PROTOCOL,
            "request_timeout_ms": settings.KAFKA_REQUEST_TIMEOUT_MS,
            "enable_idempotence": settings.KAFKA_ENABLE_IDEMPOTENCE,
        }
        if settings.KAFKA_SASL_MECHANISM:
            producer_kwargs["sasl_mechanism"] = settings.KAFKA_SASL_MECHANISM
        if settings.KAFKA_USERNAME:
            producer_kwargs["sasl_plain_username"] = settings.KAFKA_USERNAME
        password = settings.KAFKA_PASSWORD.get_secret_value()
        if password:
            producer_kwargs["sasl_plain_password"] = password

        self._producer = AIOKafkaProducer(**producer_kwargs)
        await self._producer.start()
        self._started = True

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
        self._producer = None
        self._started = False

    async def publish(
        self,
        payload: dict[str, Any],
        *,
        topic: str | None = None,
        key: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {"published": False, "reason": "kafka_disabled"}

        if not self._started:
            await self.start()

        if self._producer is None:
            raise RuntimeError("Kafka producer is not available")

        encoded_headers = [
            (header_key, header_value.encode("utf-8"))
            for header_key, header_value in (headers or {}).items()
        ]
        metadata = await self._producer.send_and_wait(
            self.build_topic_name(topic),
            json.dumps(payload, default=str).encode("utf-8"),
            key=key.encode("utf-8") if key else None,
            headers=encoded_headers,
        )
        return {
            "published": True,
            "topic": metadata.topic,
            "partition": metadata.partition,
            "offset": metadata.offset,
        }

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "configured": self.is_configured(),
            "started": self._started,
            "bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "client_id": settings.KAFKA_CLIENT_ID,
            "topic_prefix": settings.KAFKA_TOPIC_PREFIX,
            "default_topic": self.build_topic_name(),
            "security_protocol": settings.KAFKA_SECURITY_PROTOCOL,
        }


_kafka_service: KafkaService | None = None


def get_kafka_service() -> KafkaService:
    global _kafka_service
    if _kafka_service is None:
        _kafka_service = KafkaService()
    return _kafka_service