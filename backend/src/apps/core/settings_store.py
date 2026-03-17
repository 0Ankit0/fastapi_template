from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.core.config import (
    NON_RUNTIME_EDITABLE_SETTING_KEYS,
    get_environment_settings_snapshot,
    settings,
)
from src.apps.core.models import GeneralSetting


async def sync_general_settings(session: AsyncSession) -> None:
    env_snapshot = get_environment_settings_snapshot()
    result = await session.execute(select(GeneralSetting))
    existing_settings = {item.key: item for item in result.scalars().all()}
    now = datetime.now()

    for key, env_value in env_snapshot.items():
        general_setting = existing_settings.get(key)
        if general_setting is None:
            session.add(
                GeneralSetting(
                    key=key,
                    env_value=env_value,
                    is_runtime_editable=key not in NON_RUNTIME_EDITABLE_SETTING_KEYS,
                )
            )
            continue

        general_setting.env_value = env_value
        general_setting.is_runtime_editable = key not in NON_RUNTIME_EDITABLE_SETTING_KEYS
        general_setting.updated_at = now
        session.add(general_setting)

    await session.commit()
    settings.refresh_from_database(force=True)
