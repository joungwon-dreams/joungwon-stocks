"""
한국전력 전체 데이터 수집 (Tier 1-4)

Orchestrator를 사용하여 모든 Tier의 데이터 수집
"""
import sys
import asyncio
from datetime import datetime

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.core.orchestrator import Orchestrator
from src.config.database import db

# 한국전력 종목코드
KEPCO_CODE = '015760'


async def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("한국전력 전체 데이터 수집 (Tier 1-4)")
    print("=" * 80)
    print()
    print(f"대상 종목: 한국전력 ({KEPCO_CODE})")
    print(f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        await db.connect()

        # Orchestrator 초기화
        orchestrator = Orchestrator()
        await orchestrator.initialize()

        print("🚀 데이터 수집 시작...")
        print()

        # 전체 Tier 수집
        result = await orchestrator.run([KEPCO_CODE])

        print()
        print("=" * 80)
        print("수집 완료")
        print("=" * 80)
        print()

        # 결과 요약
        if result:
            print("📊 수집 결과:")
            print(f"   성공: {result.get('success_count', 0)}건")
            print(f"   실패: {result.get('failure_count', 0)}건")
            print(f"   총 소요 시간: {result.get('total_time', 0):.2f}초")
            print()

            if result.get('summary'):
                print("📋 Tier별 요약:")
                for tier, summary in result['summary'].items():
                    print(f"   {tier}: {summary}")
                print()

        # 데이터베이스 확인
        print("💾 데이터베이스 확인:")

        # 총 수집 데이터 수
        count_query = "SELECT COUNT(*) FROM collected_data WHERE ticker = $1"
        total_count = await db.fetch_val(count_query, KEPCO_CODE)
        print(f"   총 수집 데이터: {total_count}건")

        # Tier별 데이터 수
        tier_query = """
            SELECT rs.tier, COUNT(*) as count
            FROM collected_data cd
            JOIN reference_sites rs ON cd.site_id = rs.id
            WHERE cd.ticker = $1
            GROUP BY rs.tier
            ORDER BY rs.tier
        """
        tier_counts = await db.fetch(tier_query, KEPCO_CODE)

        print("   Tier별 데이터:")
        for row in tier_counts:
            print(f"     Tier {row['tier']}: {row['count']}건")

        # 최근 수집 데이터
        recent_query = """
            SELECT rs.site_name_ko, cd.data_type, cd.collected_at
            FROM collected_data cd
            JOIN reference_sites rs ON cd.site_id = rs.id
            WHERE cd.ticker = $1
            ORDER BY cd.collected_at DESC
            LIMIT 5
        """
        recent_data = await db.fetch(recent_query, KEPCO_CODE)

        print()
        print("   최근 수집 데이터 (5건):")
        for row in recent_data:
            print(f"     {row['site_name_ko']} ({row['data_type']}) - {row['collected_at'].strftime('%H:%M:%S')}")

        print()
        print("✅ 전체 데이터 수집 완료")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
