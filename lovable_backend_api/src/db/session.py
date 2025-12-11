"""Async SQLAlchemy engine and session management.

This module configures an async SQLAlchemy 2.x engine and async sessionmaker
wired to the DATABASE_URL provided by AppSettings. It exposes helpers for
acquiring sessions and running operations with proper lifecycle management.

Environment:
- DATABASE_URL (via src.core.config.get_settings)

Notes:
- Uses SQLAlchemy 2.x style with async engine and AsyncSession
- Make sure your DATABASE_URL uses an async driver, for example:
  - postgresql+asyncpg://user:password@host:port/dbname
  - sqlite+aiosqlite:///./local.db
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


from src.core.config import get_settings

_settings = get_settings()

# Create async SQLAlchemy engine
# pool_pre_ping True helps avoid stale connections in long-running apps.
ENGINE: AsyncEngine = create_async_engine(
    _settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

# Configure sessionmaker to return AsyncSession instances
ASYNC_SESSION_MAKER: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=ENGINE,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# PUBLIC_INTERFACE
@asynccontextmanager
async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession with proper open/close and rollback on error."""
    async with ASYNC_SESSION_MAKER() as session:
        try:
            yield session
        except Exception:
            # Rollback on any exception to leave connection clean
            await session.rollback()
            raise


# PUBLIC_INTERFACE
async def run_in_transaction(
    fn: Callable[[AsyncSession], "Optional[object]"],
) -> "Optional[object]":
    """Run a callable inside a transaction and commit upon success.

    The provided callable receives an AsyncSession. On success the transaction
    is committed; on exception, it's rolled back and the exception is re-raised.

    Args:
        fn: a callable taking AsyncSession and returning any value.

    Returns:
        The value returned by the callable.
    """
    async with get_async_session() as session:
        try:
            result = await fn(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise
