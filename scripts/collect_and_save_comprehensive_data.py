"""
Naver + Daum 종합 데이터 수집 및 DB 저장
"""
import asyncio
import sys
import json
from datetime import datetime
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.fetchers.tier4_browser_automation.naver_main_comprehensive_fetcher import NaverMainComprehensiveFetcher
from src.fetchers.tier2_official_apis.daum_fetcher import DaumFetcher

async def main():
    ticker = '015760'  # 한국전력

    print("="*70)
    print("종합 데이터 수집 - Naver + Daum")
    print("="*70)

    # 1. Daum Finance API (빠르고 안정적)
    print("\n1. Daum Finance API 데이터 수집")
    print("-"*70)

    daum_config = {
        'site_name_ko': 'Daum Finance',
        'data_type': 'daum_comprehensive',
        'domain_id': 1  # 종합 정보
    }

    daum_fetcher = DaumFetcher(site_id=60, config=daum_config)
    daum_data = await daum_fetcher.fetch(ticker)

    if daum_data:
        print(f"✅ Daum: {daum_data['records_count']}개 레코드")
        print(f"   - 투자자 매매동향: {len(daum_data.get('investor_trading', {}).get('data', []))}일")
        print(f"   - 시세 정보: {'O' if daum_data.get('quotes') else 'X'}")
        print(f"   - 재무 지표: {len(daum_data.get('sectors', {}).get('data', []))}개")
        print(f"   - 차트 데이터: {len(daum_data.get('charts_investors', {}).get('data', []))}일")
    else:
        print("❌ Daum 데이터 수집 실패")

    # 2. Naver Main Page (브라우저 자동화)
    print("\n2. Naver Main Page 데이터 수집")
    print("-"*70)

    naver_config = {
        'headless': True,
        'viewport': {'width': 1920, 'height': 1080},
        'data_type': 'naver_main_comprehensive',
        'domain_id': 1
    }

    naver_fetcher = NaverMainComprehensiveFetcher(site_id=61, config=naver_config)

    try:
        await naver_fetcher.initialize()
        naver_data = await naver_fetcher.fetch_data(ticker)

        if naver_data:
            print(f"✅ Naver 수집 성공!")
            investor_trading = naver_data.get('investor_trading', {}).get('daily_trading', [])
            peer_comparison = naver_data.get('peer_comparison', [])
            print(f"   - 투자자 매매동향: {len(investor_trading)}일")
            print(f"   - 동종업종비교: {len(peer_comparison)}개 기업")
        else:
            print("❌ Naver 데이터 수집 실패")
            naver_data = {}

    finally:
        await naver_fetcher.cleanup()

    # 3. 통합 데이터 생성
    print("\n3. 통합 데이터 생성")
    print("-"*70)

    comprehensive_data = {
        'ticker': ticker,
        'collected_at': datetime.now().isoformat(),
        'sources': {
            'daum': daum_data,
            'naver': naver_data
        },
        'summary': {
            'daum_records': daum_data.get('records_count', 0) if daum_data else 0,
            'naver_investor_trading_days': len(naver_data.get('investor_trading', {}).get('daily_trading', [])),
            'naver_peer_companies': len(naver_data.get('peer_comparison', [])),
            'total_data_points': (
                daum_data.get('records_count', 0) +
                len(naver_data.get('investor_trading', {}).get('daily_trading', [])) +
                len(naver_data.get('peer_comparison', []))
            ) if daum_data else 0
        }
    }

    # 4. 파일 저장
    output_path = '/tmp/comprehensive_stock_data.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(comprehensive_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 통합 데이터 저장: {output_path}")
    print(f"   총 데이터 포인트: {comprehensive_data['summary']['total_data_points']}개")

    # 5. 요약 출력
    print("\n" + "="*70)
    print("수집 데이터 요약")
    print("="*70)

    print("\n[Daum Finance]")
    if daum_data:
        quotes = daum_data.get('quotes', {})
        if quotes:
            print(f"  종목명: {quotes.get('name')}")
            print(f"  현재가: {quotes.get('tradePrice'):,.0f}원")
            print(f"  시가총액: {quotes.get('marketCap', 0):,.0f}원")

        sectors = daum_data.get('sectors', {}).get('data', [])
        if sectors and len(sectors) > 0:
            stock = sectors[0]
            print(f"  EPS: {stock.get('eps')}원")
            print(f"  ROE: {stock.get('roe', 0)*100:.2f}%")
            print(f"  영업이익: {stock.get('operatingProfit', 0):,.0f}원")

    print("\n[Naver Finance]")
    if naver_data:
        trading = naver_data.get('investor_trading', {}).get('daily_trading', [])
        if trading:
            latest = trading[0]
            print(f"  최근({latest['date']})")
            print(f"    외국인 순매수: {latest['foreign_net']:,.0f}주")
            print(f"    기관 순매수: {latest['institution_net']:,.0f}주")

        peers = naver_data.get('peer_comparison', [])
        if peers:
            print(f"  동종업종 {len(peers)}개 기업 비교 데이터")

asyncio.run(main())
