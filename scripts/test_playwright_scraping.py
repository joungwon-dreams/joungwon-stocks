#!/usr/bin/env python3
"""
Playwright 스크래핑 테스트
한 종목만 테스트하여 거래량, 호가 정보가 제대로 수집되는지 확인
"""
import asyncio
from playwright.async_api import async_playwright


async def test_single_stock(stock_code='035720'):
    """카카오(035720) 테스트"""
    print(f"\n{'='*80}")
    print(f"🧪 Playwright 스크래핑 테스트: {stock_code}")
    print(f"{'='*80}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
        print(f"📡 페이지 로딩: {url}")
        await page.goto(url, wait_until='networkidle')

        # JavaScript 로딩 대기
        await page.wait_for_timeout(2000)
        print("✅ 페이지 로딩 완료\n")

        # 현재가
        price_elem = await page.query_selector('.today .blind')
        price_text = await price_elem.inner_text() if price_elem else "0"
        price = int(price_text.replace(',', ''))
        print(f"💰 현재가: {price:,}원")

        # 등락률
        change_elem = await page.query_selector('.today .rate .blind')
        if change_elem:
            change_text = await change_elem.inner_text()
            print(f"📈 등락률: {change_text}")

        # 거래량 시도 1: span.blind
        print(f"\n🔍 거래량 수집 시도...")
        volume = 0
        try:
            # 모든 테이블 행 출력해서 구조 확인
            all_rows = await page.query_selector_all('.gray_cnt table tr')
            print(f"   총 {len(all_rows)}개 행 발견")

            for i, row in enumerate(all_rows[:10]):  # 처음 10개만
                text = await row.inner_text()
                if '거래량' in text:
                    print(f"   행 {i}: {text[:100]}")
                    # 거래량이 포함된 행에서 숫자 추출
                    cells = await row.query_selector_all('td')
                    for j, cell in enumerate(cells):
                        cell_text = await cell.inner_text()
                        print(f"     셀 {j}: {cell_text}")
                        # 숫자만 있는 셀 찾기
                        cleaned = cell_text.replace(',', '').strip()
                        if cleaned.isdigit():
                            volume = int(cleaned)
                            print(f"   ✅ 거래량 발견: {volume:,}")
                            break
                    if volume > 0:
                        break
        except Exception as e:
            print(f"   ⚠️  거래량 파싱 실패: {e}")

        # 거래량 시도 2: #_quant
        if volume == 0:
            try:
                quant_elem = await page.query_selector('#_quant')
                if quant_elem:
                    volume_text = await quant_elem.inner_text()
                    volume = int(volume_text.replace(',', ''))
                    print(f"   ✅ #_quant에서 거래량 발견: {volume:,}")
            except:
                pass

        print(f"📊 거래량 최종: {volume:,}\n")

        # 호가 정보
        print(f"🔍 호가 정보 수집 시도...")
        try:
            # 호가 테이블 구조 확인
            hoga_tables = await page.query_selector_all('.tb_cls table')
            print(f"   호가 테이블 {len(hoga_tables)}개 발견")

            if hoga_tables:
                # 첫번째 테이블의 모든 행 출력
                rows = await hoga_tables[0].query_selector_all('tr')
                print(f"   총 {len(rows)}개 호가 행")

                for i, row in enumerate(rows[:3]):  # 처음 3개만
                    cells = await row.query_selector_all('td')
                    cell_texts = []
                    for cell in cells:
                        text = await cell.inner_text()
                        cell_texts.append(text.strip())
                    print(f"   행 {i}: {' | '.join(cell_texts)}")

                # 매도호가 (첫번째 행)
                ask_elem = await page.query_selector('.tb_cls tr:first-child .ask')
                if ask_elem:
                    ask_text = await ask_elem.inner_text()
                    ask_price = int(ask_text.replace(',', ''))
                    print(f"   💸 매도호가: {ask_price:,}원")

                # 매수호가 (마지막 행)
                bid_elem = await page.query_selector('.tb_cls tr:last-child .bid')
                if bid_elem:
                    bid_text = await bid_elem.inner_text()
                    bid_price = int(bid_text.replace(',', ''))
                    print(f"   💵 매수호가: {bid_price:,}원")
        except Exception as e:
            print(f"   ⚠️  호가 파싱 실패: {e}")

        await browser.close()

        print(f"\n{'='*80}")
        print("✅ 테스트 완료")
        print(f"{'='*80}\n")


if __name__ == '__main__':
    asyncio.run(test_single_stock())
