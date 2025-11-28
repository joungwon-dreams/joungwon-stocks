"""
한국전력 전체 데이터 수집

48개 사이트에서 한국전력 데이터 수집:
- Tier 1: 4개 (Official Libraries)
- Tier 2: 5개 (Official APIs)
- Tier 3: 39개 (Web Scraping)
- Tier 4: 0개 (Browser Automation - 아직 미구현)
"""
import asyncio
import sys
import logging
from datetime import datetime

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.core.orchestrator import Orchestrator
from src.config.database import db

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/wonny/Dev/joungwon.stocks/logs/kepco_collection.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 한국전력 종목코드
KEPCO_CODE = '015760'


async def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("한국전력 전체 데이터 수집")
    print("=" * 80)
    print()
    print(f"📊 대상 종목: 한국전력 ({KEPCO_CODE})")
    print(f"🕐 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    start_time = datetime.now()

    try:
        # Orchestrator 초기화
        orchestrator = Orchestrator(max_concurrent=10)
        await orchestrator.initialize()

        print(f"✅ Orchestrator 초기화 완료")
        print(f"📡 등록된 사이트: {len(orchestrator.sites)}개")
        print()

        # Tier별 사이트 통계
        tier_counts = {}
        for site in orchestrator.sites:
            tier = site.get('tier', 0)
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        print("Tier별 사이트 분포:")
        for tier in sorted(tier_counts.keys()):
            print(f"  Tier {tier}: {tier_counts[tier]}개")
        print()

        # 데이터 수집 실행
        print("🚀 데이터 수집 시작...")
        print()

        await orchestrator.run(tickers=[KEPCO_CODE])

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print()
        print("=" * 80)
        print("✅ 데이터 수집 완료")
        print("=" * 80)
        print(f"⏱️  소요 시간: {duration:.1f}초")
        print(f"🕐 종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 수집된 데이터 통계
        query = '''
            SELECT
                data_type,
                COUNT(*) as count,
                MAX(collected_at) as last_collected
            FROM collected_data
            WHERE ticker = $1
            GROUP BY data_type
            ORDER BY count DESC
        '''

        stats = await db.fetch(query, KEPCO_CODE)

        print("수집 데이터 통계:")
        print("-" * 80)

        total_records = 0
        for row in stats:
            total_records += row['count']
            print(f"  {row['data_type']:20s}: {row['count']:4d}개 (최종: {row['last_collected']})")

        print("-" * 80)
        print(f"총 {total_records}개 레코드 수집 ({len(stats)}개 데이터 타입)")
        print()
        print(f"📁 로그 파일: /Users/wonny/Dev/joungwon.stocks/logs/kepco_collection.log")

    except Exception as e:
        logger.error(f"데이터 수집 실패: {e}", exc_info=True)
        print(f"❌ 에러 발생: {e}")
        raise

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
