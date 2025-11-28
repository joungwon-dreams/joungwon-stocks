"""
Debug Daum Finance API - 정확한 요청/응답 확인
"""
import asyncio
import aiohttp
import json

async def test_daum_api():
    stock_code = '015760'  # 한국전력

    # Test 1: Original API endpoint
    print("=" * 80)
    print("TEST 1: 기존 API 엔드포인트")
    print("=" * 80)

    url1 = "https://finance.daum.net/api/research/company"
    params1 = {
        'symbolCode': f'A{stock_code}',
        'page': 1,
        'perPage': 10
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://finance.daum.net/quotes/A015760',
        'Accept': 'application/json',
    }

    print(f"URL: {url1}")
    print(f"Params: {params1}")
    print(f"Headers: {json.dumps(headers, indent=2, ensure_ascii=False)}")
    print()

    async with aiohttp.ClientSession() as session:
        async with session.get(url1, params=params1, headers=headers) as resp:
            print(f"Status: {resp.status}")
            print(f"Response Headers: {dict(resp.headers)}")
            print()

            if resp.status == 200:
                data = await resp.json()
                print(f"Response Data: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
            else:
                text = await resp.text()
                print(f"Error Response: {text[:500]}")

    print("\n")

    # Test 2: Try alternative endpoint (검색으로 추측)
    print("=" * 80)
    print("TEST 2: 대체 API 엔드포인트 - /api/quote")
    print("=" * 80)

    url2 = f"https://finance.daum.net/api/quote/A{stock_code}"
    print(f"URL: {url2}")

    async with aiohttp.ClientSession() as session:
        async with session.get(url2, headers=headers) as resp:
            print(f"Status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
            else:
                text = await resp.text()
                print(f"Error: {text[:500]}")

    print("\n")

    # Test 3: Web page scraping (최후의 수단)
    print("=" * 80)
    print("TEST 3: 웹 페이지에서 데이터 추출")
    print("=" * 80)

    url3 = f"https://finance.daum.net/quotes/A{stock_code}#analyst/opinion"
    print(f"URL: {url3}")
    print("(브라우저로 이 URL 접속하면 종목리포트 데이터가 보입니다)")
    print("개발자 도구 Network 탭에서 실제 API 호출을 확인할 수 있습니다.")

    async with aiohttp.ClientSession() as session:
        async with session.get(url3, headers=headers) as resp:
            print(f"Status: {resp.status}")
            html = await resp.text()
            print(f"HTML Length: {len(html)} characters")

            # Check if page contains the data
            if '종목리포트' in html:
                print("✅ HTML에 '종목리포트' 텍스트 발견")
            if 'research' in html or 'analyst' in html:
                print("✅ HTML에 'research' 또는 'analyst' 키워드 발견")

if __name__ == '__main__':
    asyncio.run(test_daum_api())
