"""Database initialization helpers."""

from __future__ import annotations


async def init_db() -> None:
    """Create all registered SQLAlchemy tables for local development. Use this for testing purpose only and use proper database migration tools for production."""

    from db.base import Base
    from db.session import engine
    from src.apps import load_all_models

    load_all_models()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


