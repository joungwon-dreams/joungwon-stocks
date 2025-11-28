"""
Daum Finance Fetcher 테스트
"""
import asyncio
import sys
import json
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.fetchers.tier2_official_apis.daum_fetcher import DaumFetcher

async def test_daum_fetcher():
    print("="*60)
    print("Daum Finance Fetcher 테스트")
    print("="*60)

    config = {
        'site_name_ko': 'Daum Finance',
        'data_type': 'daum_comprehensive'
    }

    fetcher = DaumFetcher(site_id=999, config=config)

    # Test validation
    print("\n1. API Validation 테스트")
    print("-"*60)
    is_valid = await fetcher.validate_structure()
    print(f"API 유효성: {'✅ 정상' if is_valid else '❌ 실패'}")

    # Test fetch
    print("\n2. 한국전력 (015760) 데이터 수집")
    print("-"*60)
    ticker = '015760'

    data = await fetcher.fetch(ticker)

    if data:
        print(f"✅ 데이터 수집 성공!")
        print(f"총 {data['records_count']}개 레코드\n")

        # 투자자별 매매동향
        print("="*60)
        print("1. 투자자별 매매동향 (최근 30일)")
        print("="*60)
        investor_data = data.get('investor_trading', {}).get('data', [])
        if investor_data:
            print(f"총 {len(investor_data)}일 데이터")
            for item in investor_data[:5]:
                print(f"  {item['date'][:10]}: "
                      f"외국인 {item['foreignStraightPurchaseVolume']:>10,}주, "
                      f"기관 {item['institutionStraightPurchaseVolume']:>10,}주")
        else:
            print("  데이터 없음")

        # 시세 정보
        print("\n" + "="*60)
        print("2. 시세 정보")
        print("="*60)
        quotes = data.get('quotes', {})
        if quotes:
            print(f"  종목명: {quotes.get('name')}")
            print(f"  현재가: {quotes.get('tradePrice'):,}원")
            print(f"  전일대비: {quotes.get('changePrice'):,}원 ({quotes.get('change')})")
            print(f"  시가총액: {quotes.get('marketCap', 0):,}원")
            print(f"  거래량: {quotes.get('accTradeVolume', 0):,}주")
        else:
            print("  데이터 없음")

        # 재무 지표 (sectors API에서 추출)
        print("\n" + "="*60)
        print("3. 재무 지표")
        print("="*60)
        sectors = data.get('sectors', {}).get('data', [])
        if sectors and len(sectors) > 0:
            stock = sectors[0]  # 첫 번째가 해당 종목
            print(f"  매출액: {stock.get('netSales', 0):,.0f}원")
            print(f"  영업이익: {stock.get('operatingProfit', 0):,.0f}원")
            print(f"  조정영업이익: {stock.get('adjustOperatingProfit', 0):,.0f}원")
            print(f"  순이익: {stock.get('netIncome', 0):,.0f}원")
            print(f"  EPS: {stock.get('eps')}원")
            print(f"  ROE: {stock.get('roe')}")
            print(f"  외국인비율: {stock.get('foreignRatio', 0)*100:.2f}%")
        else:
            print("  데이터 없음")

        # 차트 데이터
        print("\n" + "="*60)
        print("4. 투자자 차트 데이터 (최근 90일)")
        print("="*60)
        charts_data = data.get('charts_investors', {}).get('data', [])
        if charts_data:
            print(f"총 {len(charts_data)}일 데이터")
            # 최근 5일만 출력
            for item in charts_data[-5:]:
                print(f"  {item['date'][:10]}: "
                      f"외국인보유율 {item['foreignOwnSharesRate']*100:>6.2f}%, "
                      f"순매수 {item['foreignStraightPurchaseVolume']:>10,}주")
        else:
            print("  데이터 없음")

        # 전체 데이터 저장
        output_path = '/tmp/daum_fetcher_data.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 전체 데이터 저장: {output_path}")

    else:
        print("❌ 데이터 수집 실패")

asyncio.run(test_daum_fetcher())
