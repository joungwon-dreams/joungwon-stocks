"""
네이버 금융 뉴스 재확인 - 한국전력
"""
import asyncio
from playwright.async_api import async_playwright

async def check_naver_news():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 브라우저 보이게
        page = await browser.new_page()

        url = "https://finance.naver.com/item/news.naver?code=015760"
        print(f"접속: {url}")
        await page.goto(url, wait_until='networkidle')

        # 페이지 로드 대기
        await asyncio.sleep(3)

        # 전체 HTML 구조 확인
        html = await page.content()

        # iframe 확인
        iframes = await page.query_selector_all('iframe')
        print(f"\n발견된 iframe 개수: {len(iframes)}")

        for i, iframe in enumerate(iframes):
            src = await iframe.get_attribute('src')
            name = await iframe.get_attribute('name')
            print(f"  iframe {i}: name={name}, src={src}")

        # 탭 확인
        tabs = await page.query_selector_all('ul.tab_con1 li, ul.tab_con li')
        print(f"\n탭 개수: {len(tabs)}")
        for i, tab in enumerate(tabs):
            text = await tab.text_content()
            print(f"  탭 {i}: {text.strip()}")

        # 메인 영역의 뉴스 테이블 확인
        print("\n메인 영역 뉴스 테이블 확인...")
        tables = await page.query_selector_all('table')
        print(f"테이블 개수: {len(tables)}")

        for i, table in enumerate(tables):
            class_name = await table.get_attribute('class')
            rows = await table.query_selector_all('tr')
            print(f"  Table {i}: class={class_name}, rows={len(rows)}")

            # 첫 3개 행의 내용 미리보기
            for j, row in enumerate(rows[:3]):
                text = await row.text_content()
                print(f"    Row {j}: {text.strip()[:100]}")

        # iframe 내부 확인 (news_news.naver)
        print("\n\niframe 내부 확인...")
        iframe_element = await page.query_selector('iframe[name="news_frame"]')
        if iframe_element:
            frame = await iframe_element.content_frame()
            if frame:
                # iframe 내 뉴스 확인
                news_rows = await frame.query_selector_all('table.type5 tr')
                print(f"iframe 내 뉴스 행: {len(news_rows)}개")

                for i, row in enumerate(news_rows[:5]):
                    title_elem = await row.query_selector('a.tit')
                    if title_elem:
                        title = await title_elem.text_content()
                        print(f"  뉴스 {i}: {title.strip()[:60]}")

        print("\n\n10초 대기 (브라우저 확인)...")
        await asyncio.sleep(10)

        await browser.close()

asyncio.run(check_naver_news())
