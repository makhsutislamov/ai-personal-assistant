from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

# Module-level session factory — set during app startup via lifespan
_session_factory = None


def set_session_factory(factory) -> None:  # type: ignore[type-arg]
    global _session_factory
    _session_factory = factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Session factory not initialised. Has the app started?")
    async with _session_factory() as session:
        yield session
