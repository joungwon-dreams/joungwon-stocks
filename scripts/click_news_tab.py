"""
뉴스·공시 탭 클릭 후 확인
"""
import asyncio
from playwright.async_api import async_playwright

async def check_news_tab():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # 메인 페이지로 이동
        url = "https://finance.naver.com/item/main.naver?code=015760"
        print(f"1. 메인 페이지 접속: {url}")
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(2)

        # 현재 URL 확인
        current_url = page.url
        print(f"   현재 URL: {current_url}")

        # 뉴스·공시 탭 찾기
        print("\n2. 뉴스·공시 탭 찾기...")
        tabs = await page.query_selector_all('.tab_con1 a, #tab_con1 a, a')

        news_tab = None
        for tab in tabs:
            text = await tab.text_content()
            if '뉴스' in text and '공시' in text:
                print(f"   찾음: '{text.strip()}'")
                news_tab = tab
                break

        if news_tab:
            print("\n3. 뉴스·공시 탭 클릭...")
            await news_tab.click()
            await asyncio.sleep(3)

            # 클릭 후 URL
            new_url = page.url
            print(f"   클릭 후 URL: {new_url}")

            # 스크린샷
            await page.screenshot(path='/tmp/after_news_tab_click.png', full_page=True)
            print("   스크린샷: /tmp/after_news_tab_click.png")

            # 뉴스 찾기
            print("\n4. 뉴스 찾기...")
            news_links = await page.query_selector_all('a[href*="news"]')
            print(f"   뉴스 관련 링크: {len(news_links)}개")

            for i, link in enumerate(news_links[:10]):
                text = await link.text_content()
                href = await link.get_attribute('href')
                if text and len(text.strip()) > 10:
                    print(f"\n   뉴스 {i+1}: {text.strip()[:60]}")
                    print(f"   URL: {href[:80] if href else 'None'}")

        else:
            print("   ❌ 뉴스·공시 탭을 찾을 수 없습니다")

            # 모든 탭 출력
            print("\n   사용 가능한 탭:")
            all_tabs = await page.query_selector_all('.tab_con1 a, #tab_con1 a')
            for i, tab in enumerate(all_tabs[:10]):
                text = await tab.text_content()
                print(f"     탭 {i}: {text.strip()}")

        print("\n\n10초 대기...")
        await asyncio.sleep(10)

        await browser.close()

asyncio.run(check_news_tab())
