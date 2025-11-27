"""
데이터베이스 연결 유틸리티
"""
import asyncio
import asyncpg
import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

import sys
sys.path.insert(0, '.')
from 신규종목추천.config.settings import settings

logger = logging.getLogger(__name__)


class Database:
    """비동기 PostgreSQL 데이터베이스 연결 관리"""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """데이터베이스 연결 풀 생성"""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                host=settings.db.host,
                port=settings.db.port,
                database=settings.db.database,
                user=settings.db.user,
                password=settings.db.password or None,
                min_size=2,
                max_size=10,
            )
            logger.info("Database connection pool created")

    async def disconnect(self):
        """데이터베이스 연결 풀 종료"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")

    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """SELECT 쿼리 실행"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """단일 행 SELECT"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def fetchval(self, query: str, *args) -> Any:
        """단일 값 SELECT"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def execute(self, query: str, *args) -> str:
        """INSERT/UPDATE/DELETE 실행"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def executemany(self, query: str, args_list: List[tuple]) -> None:
        """배치 INSERT/UPDATE"""
        async with self.pool.acquire() as conn:
            await conn.executemany(query, args_list)

    @asynccontextmanager
    async def transaction(self):
        """트랜잭션 컨텍스트 매니저"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn


# 전역 데이터베이스 인스턴스
db = Database()
