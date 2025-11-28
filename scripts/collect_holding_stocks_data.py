"""
보유종목 데이터 수집 스크립트

9개 보유종목에 대해 41개 사이트에서 데이터를 수집합니다.
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
        logging.FileHandler('/Users/wonny/Dev/joungwon.stocks/logs/collection.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 보유종목 9개
HOLDING_STOCKS = [
    '015760',  # 한국전력
    '316140',  # 우리금융지주
    '035720',  # 카카오
    '294870',  # HDC현대산업개발
    '034230',  # 파라다이스
    '017960',  # 한국카본
    '329180',  # HD현대에너지솔루션
    '023530',  # 롯데쇼핑
    '322310',  # 금양그린파워
]


async def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("보유종목 데이터 수집 시작")
    print("=" * 80)
    print()
    print(f"📊 대상 종목: {len(HOLDING_STOCKS)}개")
    for stock_code in HOLDING_STOCKS:
        print(f"  - {stock_code}")
    print()

    start_time = datetime.now()

    try:
        # Orchestrator 초기화
        orchestrator = Orchestrator(max_concurrent=10)
        await orchestrator.initialize()

        print(f"✅ Orchestrator 초기화 완료")
        print(f"📡 활성 사이트: {len(orchestrator.fetchers)}개")
        print(f"⚙️  최대 동시 실행: {orchestrator.max_concurrent}개")
        print()

        # 데이터 수집 실행
        print("🚀 데이터 수집 시작...")
        print()

        await orchestrator.run(tickers=HOLDING_STOCKS)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print()
        print("=" * 80)
        print("✅ 데이터 수집 완료")
        print("=" * 80)
        print(f"⏱️  소요 시간: {duration:.1f}초")
        print(f"📁 로그 파일: /Users/wonny/Dev/joungwon.stocks/logs/collection.log")

    except Exception as e:
        logger.error(f"데이터 수집 실패: {e}", exc_info=True)
        print(f"❌ 에러 발생: {e}")
        raise

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
