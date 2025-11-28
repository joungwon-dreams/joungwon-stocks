"""
네이버 금융 뉴스 상세 분석 - DOM 구조 정확히 파악
"""
import asyncio
from playwright.async_api import async_playwright

async def detailed_inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        url = "https://finance.naver.com/item/news.naver?code=015760"
        print(f"접속: {url}")
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(5)  # 충분히 대기

        print("\n" + "="*60)
        print("JavaScript로 페이지 내 모든 텍스트 검색")
        print("="*60)

        # LS전선 텍스트가 있는 모든 요소 찾기
        result = await page.evaluate("""
            () => {
                const results = [];
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );

                let node;
                while(node = walker.nextNode()) {
                    const text = node.textContent.trim();
                    if (text.includes('LS전선') || text.includes('한국전력')) {
                        const parent = node.parentElement;
                        results.push({
                            text: text.substring(0, 100),
                            tag: parent.tagName,
                            className: parent.className,
                            id: parent.id,
                            parentTag: parent.parentElement?.tagName,
                            parentClass: parent.parentElement?.className
                        });
                    }
                }
                return results;
            }
        """)

        print(f"\n발견된 요소: {len(result)}개")
        for i, item in enumerate(result[:15]):
            print(f"\n{i+1}. {item['text']}")
            print(f"   <{item['tag']} class='{item['className']}' id='{item['id']}'>")
            print(f"   부모: <{item['parentTag']} class='{item['parentClass']}'>")

        print("\n" + "="*60)
        print("iframe 목록 재확인")
        print("="*60)

        iframes_info = await page.evaluate("""
            () => {
                const iframes = document.querySelectorAll('iframe');
                return Array.from(iframes).map((iframe, i) => ({
                    index: i,
                    name: iframe.name,
                    src: iframe.src,
                    id: iframe.id,
                    loaded: iframe.contentDocument !== null
                }));
            }
        """)

        for iframe_info in iframes_info:
            print(f"\niframe {iframe_info['index']}:")
            print(f"  name: {iframe_info['name']}")
            print(f"  src: {iframe_info['src']}")
            print(f"  loaded: {iframe_info['loaded']}")

            # iframe 내부 확인
            if iframe_info['name'] in ['news', 'notice']:
                print(f"\n  -> iframe '{iframe_info['name']}' 내부 확인 중...")
                try:
                    frame_element = await page.query_selector(f'iframe[name="{iframe_info["name"]}"]')
                    if frame_element:
                        frame = await frame_element.content_frame()
                        if frame:
                            # iframe 내 HTML 일부
                            html_snippet = await frame.evaluate("() => document.body.innerHTML.substring(0, 500)")
                            print(f"  HTML: {html_snippet[:200]}...")

                            # iframe 내 링크 확인
                            links = await frame.query_selector_all('a')
                            print(f"  링크 개수: {len(links)}개")

                            # 뉴스 제목 찾기
                            news_titles = await frame.query_selector_all('a.tit, .title a, .newsarea a')
                            if news_titles:
                                print(f"  뉴스 제목: {len(news_titles)}개")
                                for j, title in enumerate(news_titles[:3]):
                                    text = await title.text_content()
                                    print(f"    {j+1}. {text.strip()[:60]}")
                except Exception as e:
                    print(f"  오류: {e}")

        print("\n\n30초 대기 - 페이지 확인...")
        await asyncio.sleep(30)

        await browser.close()

asyncio.run(detailed_inspect())
