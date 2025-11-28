#!/usr/bin/env python3
"""
네이버 금융 페이지 HTML 구조 확인
"""
import asyncio
from playwright.async_api import async_playwright


async def check_page_structure(stock_code='035720'):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
        print(f"페이지 로딩: {url}\n")
        await page.goto(url, wait_until='networkidle')
        await page.wait_for_timeout(3000)

        # HTML 저장
        content = await page.content()
        with open('/tmp/naver_finance.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ HTML 저장 완료: /tmp/naver_finance.html")

        # 주요 선택자 테스트
        print("\n🔍 선택자 테스트:")

        # 1. 현재가
        selectors_to_test = [
            ('.today .blind', '현재가 (.today .blind)'),
            ('.no_today .blind', '현재가 (.no_today .blind)'),
            ('#_nowVal', '현재가 (#_nowVal)'),
            ('.rate_info .blind', '현재가 (.rate_info .blind)'),
        ]

        for selector, name in selectors_to_test:
            elem = await page.query_selector(selector)
            if elem:
                text = await elem.inner_text()
                print(f"   ✅ {name}: {text[:50]}")
            else:
                print(f"   ❌ {name}: 없음")

        # 2. 거래량
        print("\n🔍 거래량 선택자:")
        volume_selectors = [
            ('#_quant', '거래량 (#_quant)'),
            ('.gray_cnt em#_quant', '거래량 (.gray_cnt em#_quant)'),
        ]

        for selector, name in volume_selectors:
            elem = await page.query_selector(selector)
            if elem:
                text = await elem.inner_text()
                print(f"   ✅ {name}: {text}")
            else:
                print(f"   ❌ {name}: 없음")

        # 3. 모든 테이블 확인
        print("\n🔍 테이블 구조:")
        tables = await page.query_selector_all('table')
        print(f"   총 테이블 개수: {len(tables)}")

        for i, table in enumerate(tables[:5]):
            classes = await table.get_attribute('class')
            print(f"   테이블 {i}: class='{classes}'")

        await browser.close()


if __name__ == '__main__':
    asyncio.run(check_page_structure())
