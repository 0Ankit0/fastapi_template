from pathlib import Path
from typing import Optional

from casbin import AsyncEnforcer
from casbin_async_sqlalchemy_adapter import Adapter as AsyncAdapter
from sqlalchemy.ext.asyncio import AsyncEngine

GLOBAL_DOMAIN = "global"


class CasbinEnforcer:
    _enforcer: Optional[AsyncEnforcer] = None

    @classmethod
    async def get_enforcer(cls, engine: AsyncEngine) -> AsyncEnforcer:
        if cls._enforcer is None:
            model_path = Path(__file__).resolve().parents[1] / "casbin_model.conf"
            adapter = AsyncAdapter(engine, db_class=None)
            cls._enforcer = AsyncEnforcer(str(model_path), adapter)
            await cls._enforcer.load_policy()
        return cls._enforcer

    @classmethod
    def normalize_domain(cls, domain: str | None) -> str:
        normalized = (domain or "").strip()
        return normalized or GLOBAL_DOMAIN

    @classmethod
    async def _ensure_enforcer(cls) -> AsyncEnforcer:
        if cls._enforcer is None:
            from src.db.session import engine

            return await cls.get_enforcer(engine)
        return cls._enforcer

    @classmethod
    async def add_policy(
        cls,
        sub: str,
        obj: str,
        act: str,
        domain: str = GLOBAL_DOMAIN,
    ) -> bool:
        enforcer = await cls._ensure_enforcer()
        return await enforcer.add_policy(sub, cls.normalize_domain(domain), obj, act)

    @classmethod
    async def remove_policy(
        cls,
        sub: str,
        obj: str,
        act: str,
        domain: str = GLOBAL_DOMAIN,
    ) -> bool:
        enforcer = await cls._ensure_enforcer()
        return await enforcer.remove_policy(sub, cls.normalize_domain(domain), obj, act)

    @classmethod
    async def add_role_for_user(
        cls,
        user: str,
        role: str,
        domain: str = GLOBAL_DOMAIN,
    ) -> bool:
        enforcer = await cls._ensure_enforcer()
        return await enforcer.add_role_for_user_in_domain(
            user,
            role,
            cls.normalize_domain(domain),
        )

    @classmethod
    async def remove_role_for_user(
        cls,
        user: str,
        role: str,
        domain: str = GLOBAL_DOMAIN,
    ) -> bool:
        enforcer = await cls._ensure_enforcer()
        return await enforcer.remove_grouping_policy(
            user,
            role,
            cls.normalize_domain(domain),
        )

    @classmethod
    async def get_roles_for_user(
        cls,
        user: str,
        domain: str = GLOBAL_DOMAIN,
    ) -> list[str]:
        enforcer = await cls._ensure_enforcer()
        return await enforcer.get_roles_for_user_in_domain(
            user,
            cls.normalize_domain(domain),
        )

    @classmethod
    async def get_users_for_role(
        cls,
        role: str,
        domain: str = GLOBAL_DOMAIN,
    ) -> list[str]:
        enforcer = await cls._ensure_enforcer()
        return await enforcer.get_users_for_role_in_domain(
            role,
            cls.normalize_domain(domain),
        )

    @classmethod
    async def enforce(
        cls,
        sub: str,
        obj: str,
        act: str,
        domain: str = GLOBAL_DOMAIN,
    ) -> bool:
        enforcer = await cls._ensure_enforcer()
        return enforcer.enforce(sub, cls.normalize_domain(domain), obj, act)

    @classmethod
    async def get_permissions_for_user(
        cls,
        user: str,
        domain: str = GLOBAL_DOMAIN,
    ) -> list[list[str]]:
        enforcer = await cls._ensure_enforcer()
        return await enforcer.get_permissions_for_user_in_domain(
            user,
            cls.normalize_domain(domain),
        )