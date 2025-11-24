"""
Database Connection Manager
Manages async PostgreSQL connections using asyncpg
"""
import asyncpg
import logging
from typing import Optional, List, Dict, Any
from src.config.settings import settings

logger = logging.getLogger(__name__)


class Database:
    """Async PostgreSQL database connection manager"""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create connection pool"""
        if self.pool is not None:
            logger.warning("Database pool already exists")
            return

        try:
            self.pool = await asyncpg.create_pool(
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info(f"Database pool created: {settings.DB_NAME}@{settings.DB_HOST}")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise

    async def disconnect(self):
        """Close connection pool"""
        if self.pool is None:
            return

        try:
            await self.pool.close()
            self.pool = None
            logger.info("Database pool closed")
        except Exception as e:
            logger.error(f"Error closing database pool: {e}")

    async def execute(self, query: str, *args) -> str:
        """Execute a query (INSERT, UPDATE, DELETE)"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """Fetch multiple rows as list of dicts"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch single row as dict"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def fetchval(self, query: str, *args) -> Any:
        """Fetch single value"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)


# Global database instance
db = Database()
