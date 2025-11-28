"""
네이버 금융 - 종목뉴스 vs 공시뉴스 비교
"""
import asyncio
from playwright.async_api import async_playwright

async def check_both_tabs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        code = '015760'  # 한국전력

        print("="*60)
        print("1. 종목뉴스 확인 (news_news.naver)")
        print("="*60)
        url1 = f"https://finance.naver.com/item/news_news.naver?code={code}"
        await page.goto(url1, wait_until='domcontentloaded')
        await asyncio.sleep(2)

        # 종목뉴스 파싱
        news_rows = await page.query_selector_all('table.type5 tbody tr')
        print(f"총 {len(news_rows)}개 행 발견")

        news_count = 0
        for i, row in enumerate(news_rows[:10]):
            # 뉴스 제목 링크
            title_link = await row.query_selector('a.tit')
            if title_link:
                title = await title_link.text_content()
                href = await title_link.get_attribute('href')
                print(f"\n뉴스 {news_count + 1}:")
                print(f"  제목: {title.strip()[:80]}")
                print(f"  링크: {href[:100] if href else 'None'}")
                news_count += 1
            else:
                # 행 내용 확인 (뉴스 없음 메시지 등)
                text = await row.text_content()
                text = text.strip()
                if text and '뉴스가 없습니다' in text:
                    print(f"\n메시지: {text}")

        print(f"\n✅ 종목뉴스 총 {news_count}건")

        print("\n" + "="*60)
        print("2. 공시뉴스 확인 (news_notice.naver)")
        print("="*60)
        url2 = f"https://finance.naver.com/item/news_notice.naver?code={code}"
        await page.goto(url2, wait_until='domcontentloaded')
        await asyncio.sleep(2)

        # 공시뉴스 파싱
        notice_rows = await page.query_selector_all('table.type5 tbody tr')
        print(f"총 {len(notice_rows)}개 행 발견")

        notice_count = 0
        for i, row in enumerate(notice_rows[:10]):
            title_link = await row.query_selector('a.tit')
            if title_link:
                title = await title_link.text_content()
                href = await title_link.get_attribute('href')
                info = await row.query_selector('td.info')
                date = await row.query_selector('td.date')

                print(f"\n공시 {notice_count + 1}:")
                print(f"  제목: {title.strip()[:80]}")
                if info:
                    info_text = await info.text_content()
                    print(f"  출처: {info_text.strip()}")
                if date:
                    date_text = await date.text_content()
                    print(f"  날짜: {date_text.strip()}")
                print(f"  링크: {href[:100] if href else 'None'}")
                notice_count += 1

        print(f"\n✅ 공시뉴스 총 {notice_count}건")

        print("\n" + "="*60)
        print("요약")
        print("="*60)
        print(f"종목뉴스: {news_count}건")
        print(f"공시뉴스: {notice_count}건")
        print(f"합계: {news_count + notice_count}건")

        await browser.close()

asyncio.run(check_both_tabs())
