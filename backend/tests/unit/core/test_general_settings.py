from src.apps.core.config import (
    NON_RUNTIME_EDITABLE_SETTING_KEYS,
    build_effective_settings,
    get_environment_settings_snapshot,
)


def test_general_settings_snapshot_includes_all_known_settings() -> None:
    snapshot = get_environment_settings_snapshot()

    assert "PROJECT_NAME" in snapshot
    assert "DATABASE_URL" in snapshot
    assert snapshot["PROJECT_NAME"] is not None


def test_build_effective_settings_prefers_enabled_database_value() -> None:
    resolved_settings = build_effective_settings(
        [
            {
                "key": "PROJECT_NAME",
                "db_value": "Database Project Name",
                "use_db_value": True,
                "is_runtime_editable": True,
            }
        ]
    )

    assert resolved_settings.PROJECT_NAME == "Database Project Name"


def test_build_effective_settings_ignores_non_runtime_editable_keys() -> None:
    resolved_settings = build_effective_settings(
        [
            {
                "key": "DATABASE_URL",
                "db_value": "sqlite+aiosqlite:///./override.db",
                "use_db_value": True,
                "is_runtime_editable": True,
            }
        ]
    )

    assert "DATABASE_URL" in NON_RUNTIME_EDITABLE_SETTING_KEYS
    assert resolved_settings.DATABASE_URL != "sqlite+aiosqlite:///./override.db"
