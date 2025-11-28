"""
Daum Finance API 테스트
"""
import asyncio
import aiohttp
import json

async def test_daum_api():
    # 한국전력 (015760) 테스트
    ticker = "015760"
    symbol_code = f"A{ticker}"  # Daum uses 'A' prefix

    print("="*60)
    print(f"Daum Finance API 테스트 - {symbol_code}")
    print("="*60)

    # 브라우저 헤더 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': f'https://finance.daum.net/quotes/{symbol_code}',
        'Origin': 'https://finance.daum.net',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }

    async with aiohttp.ClientSession(headers=headers) as session:

        # 1. 투자자별 매매동향
        print("\n1. 투자자별 매매동향 (api/investor/days)")
        print("-"*60)
        url = f"https://finance.daum.net/api/investor/days?page=1&perPage=30&symbolCode={symbol_code}"
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Status: {resp.status}")
                print(f"데이터 구조: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
            else:
                print(f"❌ Status: {resp.status}")

        # 2. 시세 정보
        print("\n\n2. 시세 정보 (api/quotes)")
        print("-"*60)
        url = f"https://finance.daum.net/api/quotes/{symbol_code}?summary=false&changeStatistics=true"
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Status: {resp.status}")
                print(f"데이터 구조: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
            else:
                print(f"❌ Status: {resp.status}")

        # 3. 업종 정보
        print("\n\n3. 업종 정보 (api/quote/sectors)")
        print("-"*60)
        url = f"https://finance.daum.net/api/quote/{symbol_code}/sectors"
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Status: {resp.status}")
                print(f"데이터 구조: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
            else:
                print(f"❌ Status: {resp.status}")

        # 4. 투자자 차트 데이터
        print("\n\n4. 투자자 차트 데이터 (api/charts/investors/days)")
        print("-"*60)
        url = f"https://finance.daum.net/api/charts/investors/days?symbolCode={symbol_code}&page=1&perPage=90"
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Status: {resp.status}")
                print(f"데이터 구조: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
            else:
                print(f"❌ Status: {resp.status}")

        # 5. 전체 데이터 저장
        print("\n\n5. 전체 API 응답 저장")
        print("-"*60)

        all_data = {}

        # Collect all API data
        endpoints = [
            ("investor_days", f"https://finance.daum.net/api/investor/days?page=1&perPage=30&symbolCode={symbol_code}"),
            ("quotes", f"https://finance.daum.net/api/quotes/{symbol_code}?summary=false&changeStatistics=true"),
            ("sectors", f"https://finance.daum.net/api/quote/{symbol_code}/sectors"),
            ("charts_investors", f"https://finance.daum.net/api/charts/investors/days?symbolCode={symbol_code}&page=1&perPage=90")
        ]

        for name, url in endpoints:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        all_data[name] = await resp.json()
                        print(f"  ✅ {name}")
                    else:
                        print(f"  ❌ {name} (Status: {resp.status})")
            except Exception as e:
                print(f"  ❌ {name} (Error: {e})")

        # Save to file
        output_path = "/tmp/daum_api_full_data.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 전체 데이터 저장: {output_path}")

        # Summary
        print("\n" + "="*60)
        print("요약")
        print("="*60)
        for name, data in all_data.items():
            if isinstance(data, dict):
                keys = list(data.keys())[:5]
                print(f"{name:20s}: {keys}")
            elif isinstance(data, list):
                print(f"{name:20s}: {len(data)} items")

asyncio.run(test_daum_api())
