"""
네이버 증권 뉴스 페이지 구조 분석
"""
import asyncio
from playwright.async_api import async_playwright

async def analyze_structure():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        url = "https://finance.naver.com/item/news.naver?code=015760"
        print(f"접속 중: {url}")
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(3)  # 페이지 로딩 대기

        # 전체 HTML 저장
        html = await page.content()
        with open('/tmp/naver_news_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("✅ HTML 저장: /tmp/naver_news_page.html")

        # 주요 셀렉터 테스트
        selectors_to_test = [
            '.tb_cont',
            '.type5',
            '.news_list',
            'table.type5',
            '.news_area',
            '#news_area',
            'table',
            '.title',
            '.info',
            '.date',
        ]

        print("\n셀렉터 테스트:")
        for selector in selectors_to_test:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"  ✅ {selector}: {len(elements)}개 요소 발견")

                    # 첫 번째 요소의 내용 출력
                    if selector in ['.title', '.info', '.date']:
                        first = await elements[0].text_content()
                        print(f"     예시: {first[:50]}...")
                else:
                    print(f"  ❌ {selector}: 요소 없음")
            except Exception as e:
                print(f"  ❌ {selector}: 에러 - {e}")

        # 테이블 구조 분석
        print("\n테이블 구조 분석:")
        tables = await page.query_selector_all('table')
        for i, table in enumerate(tables):
            rows = await table.query_selector_all('tr')
            print(f"  Table {i}: {len(rows)}개 행")

            # 첫 몇 개 행 분석
            for j, row in enumerate(rows[:3]):
                cells = await row.query_selector_all('td, th')
                cell_texts = []
                for cell in cells:
                    text = await cell.text_content()
                    cell_texts.append(text.strip()[:30])
                print(f"    Row {j}: {len(cells)}개 셀 - {cell_texts}")

        # 스크린샷
        await page.screenshot(path='/tmp/naver_news_screenshot.png', full_page=True)
        print("\n✅ 스크린샷 저장: /tmp/naver_news_screenshot.png")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(analyze_structure())
