"""
네이버 증권 뉴스 iframe 구조 분석
"""
import asyncio
from playwright.async_api import async_playwright

async def analyze_iframe():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 직접 iframe URL 접속
        url = "https://finance.naver.com/item/news_news.naver?code=015760"
        print(f"접속 중: {url}")
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(2)

        # HTML 저장
        html = await page.content()
        with open('/tmp/naver_news_iframe.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("✅ iframe HTML 저장: /tmp/naver_news_iframe.html")

        # 뉴스 테이블 찾기
        selectors_to_test = [
            'table',
            '.type5',
            '.title',
            'a.tit',
            'a.ntype',
            'span.wdate',
            'span.date',
            '.info',
            'td',
        ]

        print("\n셀렉터 테스트:")
        for selector in selectors_to_test:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"  ✅ {selector}: {len(elements)}개")
                    if selector in ['a.tit', '.title', 'a.ntype']:
                        first_text = await elements[0].text_content() if elements else None
                        if first_text:
                            print(f"     예시: {first_text.strip()[:60]}...")
                else:
                    print(f"  ❌ {selector}: 없음")
            except Exception as e:
                print(f"  ❌ {selector}: 에러 - {e}")

        # 실제 뉴스 파싱 시도
        print("\n뉴스 항목 파싱:")
        news_rows = await page.query_selector_all('table.type5 tr')
        print(f"  총 {len(news_rows)}개 행 발견")

        for i, row in enumerate(news_rows[:5]):
            # 제목 링크
            title_link = await row.query_selector('a.tit')
            if title_link:
                title = await title_link.text_content()
                href = await title_link.get_attribute('href')
                print(f"\n  뉴스 {i+1}:")
                print(f"    제목: {title.strip()[:50]}...")
                print(f"    링크: {href}")

            # 날짜
            date_elem = await row.query_selector('.date')
            if date_elem:
                date_text = await date_elem.text_content()
                print(f"    날짜: {date_text.strip()}")

            # 언론사
            info_elem = await row.query_selector('.info')
            if info_elem:
                info_text = await info_elem.text_content()
                print(f"    언론사: {info_text.strip()}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(analyze_iframe())
