"""
Naver Main Comprehensive Fetcher 테스트
"""
import asyncio
import sys
import json
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.fetchers.tier4_browser_automation.naver_main_comprehensive_fetcher import NaverMainComprehensiveFetcher

async def test_comprehensive():
    print("="*60)
    print("Naver Main Comprehensive Fetcher 테스트")
    print("="*60)

    config = {
        'headless': True,
        'viewport': {'width': 1920, 'height': 1080}
    }

    fetcher = NaverMainComprehensiveFetcher(site_id=999, config=config)

    try:
        # Initialize
        await fetcher.initialize()
        print("✅ 브라우저 초기화 완료\n")

        # Fetch data for 한국전력
        ticker = '015760'
        print(f"한국전력 ({ticker}) 종합 데이터 수집 중...\n")

        data = await fetcher.fetch_data(ticker)

        if data:
            print("✅ 데이터 수집 성공!\n")

            # 1. 투자자별 매매동향
            print("="*60)
            print("1. 투자자별 매매동향")
            print("="*60)
            investor_trading = data.get('investor_trading', {})
            daily_trading = investor_trading.get('daily_trading', [])
            if daily_trading:
                print(f"총 {len(daily_trading)}일 데이터")
                for trade in daily_trading:
                    print(f"  {trade['date']:6s}: 종가={trade['close_price']:>8,.0f}, "
                          f"외국인={trade['foreign_net']:>10,.0f}주, "
                          f"기관={trade['institution_net']:>10,.0f}주")
            else:
                print("  데이터 없음")

            # 2. 연간 실적
            print("\n" + "="*60)
            print("2. 최근 연간 실적")
            print("="*60)
            annual_perf = data.get('annual_performance', [])
            if annual_perf:
                print(f"총 {len(annual_perf)}개 데이터 포인트")
                # Group by metric
                metrics = {}
                for perf in annual_perf:
                    metric = perf['metric']
                    if metric not in metrics:
                        metrics[metric] = []
                    metrics[metric].append(f"{perf['year']}: {perf['value']}")

                for metric, values in list(metrics.items())[:5]:  # 처음 5개만
                    print(f"  {metric}: {', '.join(values[:3])}")  # 최근 3년
            else:
                print("  데이터 없음")

            # 3. 분기 실적
            print("\n" + "="*60)
            print("3. 최근 분기 실적")
            print("="*60)
            quarterly_perf = data.get('quarterly_performance', [])
            if quarterly_perf:
                print(f"총 {len(quarterly_perf)}개 데이터 포인트")
                # Group by metric
                metrics = {}
                for perf in quarterly_perf:
                    metric = perf['metric']
                    if metric not in metrics:
                        metrics[metric] = []
                    metrics[metric].append(f"{perf['quarter']}: {perf['value']}")

                for metric, values in list(metrics.items())[:5]:
                    print(f"  {metric}: {', '.join(values[:2])}")  # 최근 2분기
            else:
                print("  데이터 없음")

            # 4. 주요 재무비율
            print("\n" + "="*60)
            print("4. 주요 재무비율")
            print("="*60)
            ratios = data.get('financial_ratios', {})
            if ratios:
                print(f"총 {len(ratios)}개 지표")
                for name, value in list(ratios.items())[:10]:  # 처음 10개
                    print(f"  {name:20s}: {value}")
            else:
                print("  데이터 없음")

            # 5. 동종업종비교
            print("\n" + "="*60)
            print("5. 동종업종비교")
            print("="*60)
            peers = data.get('peer_comparison', [])
            if peers:
                print(f"총 {len(peers)}개 기업")
                for peer in peers[:5]:  # 처음 5개
                    print(f"  {peer['company']}: {peer['data'][:3] if peer['data'] else []}")
            else:
                print("  데이터 없음")

            # Save to file
            output_path = '/tmp/naver_comprehensive_data.json'
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 데이터 저장: {output_path}")

        else:
            print("❌ 데이터 수집 실패")

    finally:
        await fetcher.cleanup()
        print("\n✅ 브라우저 종료")

asyncio.run(test_comprehensive())
