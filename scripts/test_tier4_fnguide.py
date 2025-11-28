"""
Tier 4 FnGuide Playwright Fetcher 테스트

한국전력 데이터로 FnGuide Playwright fetcher 테스트
"""
import sys
import asyncio
import json
from datetime import datetime

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.fetchers.tier4_browser_automation.fnguide_playwright_fetcher import FnGuidePlaywrightFetcher
from src.config.database import db

# 한국전력 종목코드
KEPCO_CODE = '015760'


async def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("Tier 4 FnGuide Playwright Fetcher 테스트")
    print("=" * 80)
    print()
    print(f"대상 종목: 한국전력 ({KEPCO_CODE})")
    print()

    try:
        await db.connect()

        # FnGuide fetcher 생성
        config = {
            'site_id': 53,  # FnGuide site ID
            'domain_id': 1,
            'headless': True,  # 헤드리스 모드
            'timeout': 30000,
            'data_type': 'fnguide_analysis'
        }

        fetcher = FnGuidePlaywrightFetcher(site_id=53, config=config)

        print("🌐 FnGuide 페이지 접속 중...")
        print()

        # 데이터 수집
        result = await fetcher.fetch(KEPCO_CODE)

        if result:
            print("✅ 데이터 수집 성공")
            print()
            print("=" * 80)
            print("수집된 데이터:")
            print("=" * 80)
            print()

            data = result.get('data', {})

            # 회사 정보
            if data.get('company_info'):
                print("📊 회사 정보:")
                for key, value in data['company_info'].items():
                    print(f"   {key}: {value}")
                print()

            # 재무 요약
            if data.get('financial_summary'):
                print("💰 재무 요약:")
                financials = data['financial_summary']
                if financials.get('years'):
                    print(f"   연도: {', '.join(financials['years'])}")
                if financials.get('revenue'):
                    print(f"   매출액: {financials['revenue']}")
                if financials.get('operating_profit'):
                    print(f"   영업이익: {financials['operating_profit']}")
                if financials.get('net_profit'):
                    print(f"   당기순이익: {financials['net_profit']}")
                print()

            # 애널리스트 컨센서스
            if data.get('analyst_consensus'):
                print("📈 애널리스트 컨센서스:")
                consensus = data['analyst_consensus']
                if consensus.get('target_price'):
                    print(f"   목표주가: {consensus['target_price']:,}원")
                if consensus.get('opinion'):
                    print(f"   투자의견: {consensus['opinion']}")
                if consensus.get('analyst_count'):
                    print(f"   애널리스트 수: {consensus['analyst_count']}명")
                print()

            # Valuation 지표
            if data.get('valuation_metrics'):
                print("📊 Valuation 지표:")
                metrics = data['valuation_metrics']
                if metrics.get('per'):
                    print(f"   PER: {metrics['per']}")
                if metrics.get('pbr'):
                    print(f"   PBR: {metrics['pbr']}")
                if metrics.get('dividend_yield'):
                    print(f"   배당수익률: {metrics['dividend_yield']}%")
                print()

            # 전체 JSON 출력 (디버깅용)
            print("=" * 80)
            print("전체 데이터 (JSON):")
            print("=" * 80)
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print()

        else:
            print("❌ 데이터 수집 실패")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
