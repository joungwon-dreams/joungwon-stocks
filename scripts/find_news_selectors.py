"""
네이버 금융 뉴스 셀렉터 찾기
"""
import asyncio
from playwright.async_api import async_playwright

async def find_selectors():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        url = "https://finance.naver.com/item/news.naver?code=015760"
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(3)

        print("="*60)
        print("종목뉴스 섹션 찾기")
        print("="*60)

        # 종목뉴스 제목 찾기
        section_titles = await page.query_selector_all('h4.h_sub, .sub_tit, .title, strong')
        for i, title in enumerate(section_titles[:20]):
            text = await title.text_content()
            if '종목' in text or '뉴스' in text:
                print(f"\n제목 {i}: {text.strip()}")
                # 부모 요소 확인
                parent = await title.evaluate('el => el.parentElement.className')
                print(f"  부모 class: {parent}")

        # 뉴스 리스트 찾기
        print("\n" + "="*60)
        print("뉴스 리스트 영역 찾기")
        print("="*60)

        # 다양한 셀렉터 시도
        selectors = [
            '.realtimeNewsList',
            '.newsList',
            '.newsarea',
            '.news_area',
            'div[class*="news"]',
            'ul[class*="news"]',
            '.section_strategy',
            '#content',
        ]

        for selector in selectors:
            elements = await page.query_selector_all(selector)
            if elements:
                print(f"\n✅ '{selector}': {len(elements)}개 발견")
                for i, elem in enumerate(elements[:2]):
                    # 내부 링크 개수 확인
                    links = await elem.query_selector_all('a')
                    print(f"  요소 {i}: {len(links)}개 링크")

                    # 첫 번째 링크 내용
                    if links:
                        first_link = links[0]
                        text = await first_link.text_content()
                        href = await first_link.get_attribute('href')
                        print(f"    첫 링크: {text.strip()[:50]}")
                        print(f"    URL: {href[:80] if href else 'None'}")

        # HTML 구조 분석
        print("\n" + "="*60)
        print("HTML 구조 저장")
        print("="*60)

        html = await page.content()
        with open('/tmp/naver_news_structure.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("✅ /tmp/naver_news_structure.html")

        # LS전선 텍스트 검색
        print("\n" + "="*60)
        print("'LS전선' 텍스트 검색")
        print("="*60)

        ls_elements = await page.query_selector_all('text=LS전선')
        print(f"발견: {len(ls_elements)}개")
        for i, elem in enumerate(ls_elements[:5]):
            tag = await elem.evaluate('el => el.tagName')
            parent_tag = await elem.evaluate('el => el.parentElement.tagName')
            parent_class = await elem.evaluate('el => el.parentElement.className')
            text = await elem.text_content()
            print(f"\n{i+1}. <{tag}> in <{parent_tag} class='{parent_class}'>")
            print(f"   텍스트: {text.strip()[:80]}")

        await browser.close()

asyncio.run(find_selectors())
