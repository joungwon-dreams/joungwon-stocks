"""
네이버 금융 뉴스 페이지 스크린샷
"""
import asyncio
from playwright.async_api import async_playwright

async def take_screenshot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # 한국전력 뉴스 페이지
        url = "https://finance.naver.com/item/news.naver?code=015760"
        print(f"접속: {url}")
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(3)

        # 전체 페이지 스크린샷
        await page.screenshot(path='/tmp/naver_news_full.png', full_page=True)
        print("✅ 전체 페이지: /tmp/naver_news_full.png")

        # 뉴스 영역만 스크린샷
        news_area = await page.query_selector('.tb_cont')
        if news_area:
            await news_area.screenshot(path='/tmp/naver_news_area.png')
            print("✅ 뉴스 영역: /tmp/naver_news_area.png")

        # 탭 확인
        print("\n탭 목록:")
        tabs = await page.query_selector_all('.tab_con1 a, .tab_con a')
        for i, tab in enumerate(tabs):
            text = await tab.text_content()
            href = await tab.get_attribute('href')
            print(f"  탭 {i}: {text.strip()} -> {href}")

        print("\n5초 대기...")
        await asyncio.sleep(5)

        await browser.close()
        print("\n스크린샷 확인: open /tmp/naver_news_full.png")

asyncio.run(take_screenshot())
