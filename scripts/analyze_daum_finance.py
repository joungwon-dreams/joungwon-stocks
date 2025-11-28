"""
Daum Finance 페이지 분석
https://finance.daum.net/quotes/A005930#influential_investors/home
"""
import asyncio
from playwright.async_api import async_playwright

async def analyze_daum_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # 삼성전자로 테스트
        url = "https://finance.daum.net/quotes/A005930#influential_investors/home"
        print(f"접속: {url}")
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(3)

        # 스크린샷
        await page.screenshot(path='/tmp/daum_finance_full.png', full_page=True)
        print("✅ 스크린샷: /tmp/daum_finance_full.png\n")

        print("="*60)
        print("페이지 내 섹션 분석")
        print("="*60)

        # 1. 탭 메뉴 확인
        print("\n1. 탭 메뉴:")
        tabs = await page.query_selector_all('.tab_list a, .tab_link')
        for tab in tabs[:10]:
            text = await tab.text_content()
            href = await tab.get_attribute('href')
            if text and text.strip():
                print(f"  - {text.strip()} -> {href}")

        # 2. 주요 섹션 제목
        print("\n2. 섹션 제목:")
        titles = await page.query_selector_all('h3, h4, .section_title, .box_title')
        for title in titles[:15]:
            text = await title.text_content()
            if text and len(text.strip()) > 2:
                print(f"  - {text.strip()}")

        # 3. 테이블 확인
        print("\n3. 테이블 개수:")
        tables = await page.query_selector_all('table')
        print(f"  총 {len(tables)}개 테이블")

        # 4. 주요 키워드 검색
        print("\n4. 주요 키워드:")
        keywords = ['투자자', '매매동향', '수급', '외국인', '기관', '실적', '재무', '컨센서스', '동종업계']

        for keyword in keywords:
            result = await page.evaluate(f"""
                () => {{
                    const text = document.body.innerText;
                    return text.includes('{keyword}');
                }}
            """)
            status = "✅" if result else "❌"
            print(f"  {status} '{keyword}'")

        # 5. API 요청 확인
        print("\n5. 네트워크 요청 (XHR/Fetch):")
        # 페이지 리로드하면서 네트워크 모니터링
        requests = []

        async def handle_request(request):
            if request.resource_type in ['xhr', 'fetch']:
                requests.append({
                    'url': request.url,
                    'method': request.method
                })

        page.on('request', handle_request)
        await page.reload(wait_until='networkidle')
        await asyncio.sleep(2)

        for req in requests[:10]:
            print(f"  {req['method']:6s} {req['url'][:80]}")

        print("\n\n30초 대기 (브라우저에서 페이지 확인)...")
        await asyncio.sleep(30)

        await browser.close()

asyncio.run(analyze_daum_page())
