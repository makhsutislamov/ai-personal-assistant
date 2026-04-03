from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from assistant.db.models import Base


async def run_migrations(engine: AsyncEngine) -> None:
    """Create all tables if they don't exist (idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
