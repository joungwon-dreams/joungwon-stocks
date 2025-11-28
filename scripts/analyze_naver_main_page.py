"""
네이버 금융 메인 페이지 분석 - 사용 가능한 모든 데이터 파악
"""
import asyncio
from playwright.async_api import async_playwright

async def analyze_main_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        url = "https://finance.naver.com/item/main.naver?code=015760"
        print(f"접속: {url}")
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(3)

        # 스크린샷
        await page.screenshot(path='/tmp/naver_main_full.png', full_page=True)
        print("✅ 스크린샷: /tmp/naver_main_full.png\n")

        print("="*60)
        print("페이지 내 섹션 분석")
        print("="*60)

        # 모든 테이블 제목 찾기
        sections = []

        # 방법 1: h4 제목들
        h4_titles = await page.query_selector_all('h4.h_sub')
        for title in h4_titles:
            text = await title.text_content()
            sections.append(("h4", text.strip()))

        # 방법 2: 강조 텍스트
        strong_titles = await page.query_selector_all('.sub_section strong, .section strong')
        for title in strong_titles:
            text = await title.text_content()
            if text and len(text.strip()) > 2:
                sections.append(("strong", text.strip()))

        # 방법 3: 탭 메뉴
        tabs = await page.query_selector_all('.tab_con1 a')
        for tab in tabs:
            text = await tab.text_content()
            href = await tab.get_attribute('href')
            if text and text.strip():
                sections.append(("tab", text.strip(), href))

        print("\n발견된 섹션:")
        seen = set()
        for item in sections:
            if item[1] not in seen and len(item[1]) > 2:
                seen.add(item[1])
                if len(item) == 3:
                    print(f"  [{item[0]}] {item[1]} -> {item[2]}")
                else:
                    print(f"  [{item[0]}] {item[1]}")

        print("\n" + "="*60)
        print("iframe 목록")
        print("="*60)

        iframes = await page.query_selector_all('iframe')
        for i, iframe in enumerate(iframes):
            name = await iframe.get_attribute('name')
            src = await iframe.get_attribute('src')
            if src and len(src) > 10:
                print(f"  iframe {i}: name={name}, src={src}")

        print("\n" + "="*60)
        print("주요 데이터 영역 확인")
        print("="*60)

        # 1. 투자자별 매매동향
        print("\n1. 투자자별 매매동향:")
        trade_table = await page.query_selector('table.type2')
        if trade_table:
            rows = await trade_table.query_selector_all('tr')
            print(f"   테이블 발견: {len(rows)}개 행")
            for row in rows[:3]:
                text = await row.text_content()
                print(f"   {text.strip()[:80]}")

        # 2. 종목토론실
        print("\n2. 종목토론실:")
        discussion = await page.query_selector('.section_strategy')
        if discussion:
            print("   종목토론실 영역 발견")

        # 3. 시가총액
        print("\n3. 시가총액 정보:")
        market_cap = await page.query_selector_all('table td em')
        if market_cap:
            for i, em in enumerate(market_cap[:5]):
                text = await em.text_content()
                print(f"   {i}: {text.strip()}")

        # 4. 외국인 보유 정보
        print("\n4. 외국인 보유:")
        foreign = await page.query_selector('table.lwidth')
        if foreign:
            text = await foreign.text_content()
            print(f"   {text.strip()[:200]}")

        # 5. PER/PBR
        print("\n5. PER/PBR 정보:")
        per_table = await page.query_selector('table.per_table')
        if per_table:
            text = await per_table.text_content()
            print(f"   {text.strip()[:200]}")

        # 6. 검색 가능한 키워드
        print("\n" + "="*60)
        print("페이지 내 주요 키워드 검색")
        print("="*60)

        keywords = ['투자자', '매매동향', '공시', '종목분석', '실적', '재무',
                   '컨센서스', '목표주가', '외국인', '기관', '개인']

        for keyword in keywords:
            result = await page.evaluate(f"""
                () => {{
                    const text = document.body.innerText;
                    return text.includes('{keyword}');
                }}
            """)
            status = "✅" if result else "❌"
            print(f"  {status} '{keyword}'")

        print("\n\n30초 대기 (브라우저에서 페이지 확인)...")
        await asyncio.sleep(30)

        await browser.close()

asyncio.run(analyze_main_page())
