"""
투자자별 매매동향 섹션 상세 분석
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_investor_section():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        url = "https://finance.naver.com/item/main.naver?code=015760"
        print(f"접속: {url}")
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(3)

        print("="*70)
        print("투자자별 매매동향 섹션 분석")
        print("="*70)

        # 1. section.invest_trend 찾기
        invest_section = await page.query_selector('.section.invest_trend')

        if invest_section:
            print("✅ .section.invest_trend 발견!")

            # 내부 HTML 구조 확인
            html = await invest_section.evaluate('el => el.innerHTML')
            print(f"\nHTML 길이: {len(html)} 자\n")

            # 모든 테이블 찾기
            tables = await invest_section.query_selector_all('table')
            print(f"테이블 개수: {len(tables)}\n")

            for i, table in enumerate(tables):
                print(f"--- 테이블 {i} ---")

                # 테이블 클래스
                table_class = await table.get_attribute('class')
                print(f"클래스: {table_class}")

                # 헤더 행
                rows = await table.query_selector_all('tr')
                print(f"행 개수: {len(rows)}")

                if rows:
                    # 첫 행 (헤더)
                    header_row = rows[0]
                    headers = await header_row.query_selector_all('th, td, span')
                    print(f"\n헤더 컬럼 개수: {len(headers)}")
                    for j, h in enumerate(headers):
                        text = await h.text_content()
                        tag = await h.evaluate('el => el.tagName')
                        print(f"  [{j}] <{tag}> {text.strip()}")

                    # 데이터 행 (최대 5개)
                    print(f"\n데이터 행:")
                    for j, row in enumerate(rows[1:6]):
                        cols = await row.query_selector_all('th, td, span')
                        texts = []
                        for col in cols:
                            text = await col.text_content()
                            texts.append(text.strip())
                        print(f"  Row {j}: {texts}")

                print()

            # 2. sub_section.right 확인
            print("="*70)
            print("sub_section.right 분석")
            print("="*70)

            right_section = await invest_section.query_selector('.sub_section.right')
            if right_section:
                print("✅ .sub_section.right 발견!")

                tables = await right_section.query_selector_all('table')
                print(f"테이블 개수: {len(tables)}\n")

                for i, table in enumerate(tables):
                    print(f"--- 테이블 {i} ---")
                    table_class = await table.get_attribute('class')
                    print(f"클래스: {table_class}")

                    rows = await table.query_selector_all('tr')
                    print(f"행 개수: {len(rows)}\n")

                    # 전체 텍스트
                    text = await table.evaluate('el => el.innerText')
                    print(f"내용:\n{text[:500]}")
                    print()

        else:
            print("❌ .section.invest_trend 없음!")

        print("\n20초 대기...")
        await asyncio.sleep(20)

        await browser.close()

asyncio.run(debug_investor_section())
