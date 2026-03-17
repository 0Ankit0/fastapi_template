import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.observability.models import SecurityIncident
from src.apps.observability.service import build_log_summary, create_log_entry, create_or_update_incident


@pytest.mark.unit
class TestObservabilityService:
    @pytest.mark.asyncio
    async def test_create_or_update_incident_deduplicates_open_incident(self, db_session: AsyncSession):
        incident = await create_or_update_incident(
            db_session,
            signal_type="auth.failed_login_burst",
            severity="high",
            title="Repeated failed logins",
            summary="First occurrence",
            fingerprint="auth.failed_login_burst:test",
            metadata={"count": 5},
        )
        await db_session.commit()

        updated = await create_or_update_incident(
            db_session,
            signal_type="auth.failed_login_burst",
            severity="high",
            title="Repeated failed logins",
            summary="Second occurrence",
            fingerprint="auth.failed_login_burst:test",
            metadata={"count": 6},
        )
        await db_session.commit()

        assert updated.id == incident.id
        assert updated.occurrence_count == 2
        assert updated.summary == "Second occurrence"

    @pytest.mark.asyncio
    async def test_build_log_summary_counts_logs_and_incidents(self, db_session: AsyncSession):
        await create_log_entry(
            db_session,
            level="INFO",
            logger_name="api.requests",
            source="api",
            message="Healthy request",
            event_code="http.request.completed",
        )
        await create_log_entry(
            db_session,
            level="ERROR",
            logger_name="api.requests",
            source="api",
            message="Broken request",
            event_code="ops.request_error",
        )
        db_session.add(
            SecurityIncident(
                signal_type="ops.error_spike",
                severity="high",
                status="open",
                title="Error spike",
                summary="Too many 5xx responses",
                fingerprint="ops.error_spike:/broken",
            )
        )
        await db_session.commit()

        summary = await build_log_summary(db_session)

        assert summary["total_logs_24h"] == 2
        assert summary["info_logs_24h"] == 1
        assert summary["error_logs_24h"] == 1
        assert summary["open_incidents"] == 1
        assert summary["critical_incidents"] == 1
