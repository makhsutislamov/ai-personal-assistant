from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


def _apply_cipher_key(dbapi_conn: object, _: object, key: str) -> None:
    """Set SQLCipher encryption key on new connections."""
    if key:
        dbapi_conn.execute(f"PRAGMA key='{key}'")  # type: ignore[attr-defined]


def create_engine(db_path: str, encryption_key: str = "") -> AsyncEngine:
    """Return an async SQLAlchemy engine backed by SQLCipher or plain SQLite."""
    if encryption_key:
        connect_args = {"check_same_thread": False}
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            connect_args=connect_args,
            echo=False,
        )

        @event.listens_for(engine.sync_engine, "connect")
        def on_connect(dbapi_conn: object, connection_record: object) -> None:
            _apply_cipher_key(dbapi_conn, connection_record, encryption_key)

    else:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )

    return engine


def create_session_factory(engine: AsyncEngine) -> sessionmaker:  # type: ignore[type-arg]
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
