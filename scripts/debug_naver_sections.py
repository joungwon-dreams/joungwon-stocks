"""
Naver Main Page 각 섹션별 상세 디버깅
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_sections():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        url = "https://finance.naver.com/item/main.naver?code=015760"
        print(f"접속: {url}")
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(3)

        print("="*70)
        print("1. 투자자별 매매동향 분석")
        print("="*70)

        # table.type2 찾기
        tables_type2 = await page.query_selector_all('table.type2')
        print(f"table.type2 개수: {len(tables_type2)}")

        for i, table in enumerate(tables_type2):
            print(f"\n--- table.type2[{i}] ---")
            text = await table.evaluate('el => el.innerText')
            lines = text.split('\n')[:5]
            for line in lines:
                print(f"  {line}")

            # 헤더 체크
            if '매수' in text and '매도' in text:
                print("  ✅ 이것이 투자자별 매매동향 테이블!")
                rows = await table.query_selector_all('tbody tr')
                print(f"  행 개수: {len(rows)}")

                for j, row in enumerate(rows[:3]):
                    cols = await row.query_selector_all('th, td')
                    print(f"    Row {j}: {len(cols)}개 컬럼")
                    for k, col in enumerate(cols):
                        text = await col.text_content()
                        print(f"      [{k}] {text.strip()}")

        print("\n" + "="*70)
        print("2. 연간/분기 실적 분석")
        print("="*70)

        # 모든 테이블 순회하면서 이전 요소 확인
        all_tables = await page.query_selector_all('table')
        print(f"전체 테이블 개수: {len(all_tables)}")

        for i, table in enumerate(all_tables):
            prev_elem = await table.evaluate('el => el.previousElementSibling?.innerText || ""')

            if '연간' in prev_elem or '분기' in prev_elem:
                print(f"\n--- table[{i}] ---")
                print(f"이전 요소: {prev_elem.strip()[:50]}")

                # 테이블 헤더 확인
                rows = await table.query_selector_all('tr')
                if rows:
                    header = rows[0]
                    headers = await header.query_selector_all('th')
                    print(f"  헤더 개수: {len(headers)}")
                    for j, h in enumerate(headers[:5]):
                        text = await h.text_content()
                        print(f"    [{j}] {text.strip()}")

                    # 첫 번째 데이터 행
                    if len(rows) > 1:
                        data_row = rows[1]
                        cols = await data_row.query_selector_all('th, td')
                        print(f"  데이터 행 컬럼 개수: {len(cols)}")
                        for j, col in enumerate(cols[:5]):
                            text = await col.text_content()
                            print(f"    [{j}] {text.strip()}")

        print("\n" + "="*70)
        print("3. 주요 재무정보 분석")
        print("="*70)

        # strong 태그 분석
        strongs = await page.query_selector_all('strong')
        print(f"strong 태그 개수: {len(strongs)}")

        for i, strong in enumerate(strongs[:10]):
            text = await strong.text_content()
            text = text.strip()

            if len(text) > 2 and len(text) < 20:
                # 부모 요소의 전체 텍스트
                parent_text = await strong.evaluate('el => el.parentElement.innerText')
                print(f"  [{i}] {text:20s}: {parent_text.strip()[:50]}")

        print("\n" + "="*70)
        print("4. 재무정보 섹션 구조 분석")
        print("="*70)

        # 특정 클래스나 ID 찾기
        sections = await page.query_selector_all('.section, .sub_section, .section_wrap')
        print(f"섹션 개수: {len(sections)}")

        for i, section in enumerate(sections[:5]):
            class_name = await section.get_attribute('class')
            section_text = await section.evaluate('el => el.innerText')
            print(f"\n섹션 [{i}] class={class_name}")
            print(f"  {section_text.strip()[:100]}")

        print("\n\n30초 대기...")
        await asyncio.sleep(30)

        await browser.close()

asyncio.run(debug_sections())
