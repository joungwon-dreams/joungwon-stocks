#!/usr/bin/env python3
"""
Database Maintenance Script
주간/월간 DB 유지보수 자동화

기능:
- VACUUM ANALYZE 실행
- 오래된 데이터 정리
- 인덱스 재구축
- 통계 정보 갱신
"""
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.database import db


async def vacuum_analyze_tables():
    """주요 테이블 VACUUM ANALYZE"""
    tables = [
        'daily_ohlcv',
        'min_ticks',
        'stock_assets',
        'trade_history',
        'aegis_signal_history',
        'stock_news',
        'smart_phase1_candidates',
        'smart_recommendations',
    ]

    print("🧹 VACUUM ANALYZE 실행 중...")
    for table in tables:
        try:
            await db.execute(f"VACUUM ANALYZE {table}")
            print(f"   ✅ {table}")
        except Exception as e:
            print(f"   ❌ {table}: {e}")


async def cleanup_old_data():
    """오래된 데이터 정리"""
    print("\n🗑️ 오래된 데이터 정리 중...")

    # 90일 이상 된 min_ticks 삭제
    result = await db.execute("""
        DELETE FROM min_ticks
        WHERE timestamp < NOW() - INTERVAL '90 days'
    """)
    print(f"   min_ticks: {result} rows deleted (90일 이상)")

    # 30일 이상 된 fetch_execution_logs 삭제
    result = await db.execute("""
        DELETE FROM fetch_execution_logs
        WHERE started_at < NOW() - INTERVAL '30 days'
    """)
    print(f"   fetch_execution_logs: {result} rows deleted (30일 이상)")

    # 180일 이상 된 smart_phase1_candidates 삭제
    result = await db.execute("""
        DELETE FROM smart_phase1_candidates
        WHERE created_at < NOW() - INTERVAL '180 days'
    """)
    print(f"   smart_phase1_candidates: {result} rows deleted (180일 이상)")


async def reindex_tables():
    """인덱스 재구축 (월간)"""
    print("\n🔄 인덱스 재구축 중...")

    tables = ['daily_ohlcv', 'min_ticks', 'aegis_signal_history']
    for table in tables:
        try:
            await db.execute(f"REINDEX TABLE {table}")
            print(f"   ✅ {table}")
        except Exception as e:
            print(f"   ❌ {table}: {e}")


async def get_db_stats():
    """DB 통계 조회"""
    print("\n📊 데이터베이스 통계:")

    # 테이블 크기
    rows = await db.fetch("""
        SELECT
            relname as table_name,
            pg_size_pretty(pg_total_relation_size(relid)) as size,
            n_live_tup as rows
        FROM pg_stat_user_tables
        ORDER BY pg_total_relation_size(relid) DESC
        LIMIT 5
    """)

    print("   Top 5 테이블:")
    for row in rows:
        print(f"     - {row['table_name']}: {row['size']} ({row['rows']:,} rows)")

    # 전체 DB 크기
    result = await db.fetchrow("""
        SELECT pg_size_pretty(pg_database_size(current_database())) as size
    """)
    print(f"\n   전체 DB 크기: {result['size']}")


async def main():
    """메인 함수"""
    print("=" * 60)
    print("🔧 Database Maintenance")
    print(f"   시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    await db.connect()

    try:
        # 1. VACUUM ANALYZE
        await vacuum_analyze_tables()

        # 2. 오래된 데이터 정리
        await cleanup_old_data()

        # 3. 월간 작업 (매월 1일만)
        if datetime.now().day == 1:
            await reindex_tables()

        # 4. 통계 확인
        await get_db_stats()

        print("\n" + "=" * 60)
        print("✅ Database maintenance completed")
        print("=" * 60)

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
