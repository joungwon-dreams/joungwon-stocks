"""
WISEfn Analyst Reports Scraper
Scrapes analyst target prices and reports from wisefn.finance.daum.net using Playwright
Saves to database for efficient access
"""
from playwright.async_api import async_playwright
from typing import List, Dict, Any
import asyncio
import sys
from datetime import datetime, date
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db

class WISEfnReportsScraper:
    BASE_URL = "https://wisefn.finance.daum.net/v1/company/reports.aspx"

    async def fetch_reports(self, stock_code: str) -> List[Dict[str, Any]]:
        """
        Fetch analyst reports using Playwright for JavaScript rendering

        Args:
            stock_code: Stock code (e.g., '015760')

        Returns:
            List of report dictionaries with structure:
            [
                {
                    'date': '25.11.25',
                    'target_price': 63000,
                    'price_change': '0' or '▲ 15,000' or '▼ 5,000' or '-',
                    'opinion': '매수',
                    'brokerage': '유진',
                    'title': '지역별차등요금제가 불러올 나비효과'
                },
                ...
            ]
        """
        url = f"{self.BASE_URL}?cmp_cd={stock_code}"
        reports = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Navigate to page
                await page.goto(url, wait_until='networkidle')

                # Wait for table to be fully rendered
                await page.wait_for_selector('table tbody tr .col1', timeout=10000)

                # Extract data using JavaScript
                reports_data = await page.evaluate('''() => {
                    const tbody = document.querySelector('table tbody');
                    const rows = Array.from(tbody.querySelectorAll('tr'));
                    const results = [];

                    for (let row of rows) {
                        const col1 = row.querySelector('.col1')?.textContent?.trim() || '';
                        const col2 = row.querySelector('.col2')?.textContent?.trim() || '';
                        const col3 = row.querySelector('.col3')?.textContent?.trim() || '';
                        const col4 = row.querySelector('.col4')?.textContent?.trim() || '';
                        const col5 = row.querySelector('.col5')?.textContent?.trim() || '';
                        const col6 = row.querySelector('.col6')?.textContent?.trim() || '';

                        // Only include rows with actual data
                        if (col1 && col2) {
                            results.push({
                                date: col1,
                                target_price: col2,
                                price_change: col3,
                                opinion: col4,
                                brokerage: col5,
                                title: col6
                            });
                        }
                    }

                    return results;
                }''')

                await browser.close()

                # Process data
                for item in reports_data:
                    try:
                        # Parse target price (remove commas)
                        target_price = int(item['target_price'].replace(',', ''))
                    except:
                        target_price = 0

                    reports.append({
                        'date': item['date'],
                        'target_price': target_price,
                        'price_change': item['price_change'] if item['price_change'] else '0',
                        'opinion': item['opinion'],
                        'brokerage': item['brokerage'],
                        'title': item['title']
                    })

                print(f"✅ Scraped {len(reports)} reports from WISEfn")

        except Exception as e:
            print(f"❌ WISEfn scraping error: {e}")

        return reports

    async def save_to_db(self, stock_code: str, reports: List[Dict[str, Any]]) -> int:
        """
        Save scraped reports to database

        Args:
            stock_code: Stock code
            reports: List of report dictionaries from fetch_reports()

        Returns:
            Number of reports saved
        """
        if not reports:
            return 0

        saved_count = 0

        for report in reports:
            try:
                # Parse date: YY.MM.DD -> date object
                date_str = report['date']  # e.g., "25.11.25"
                if '.' in date_str:
                    parts = date_str.split('.')
                    year = int(f"20{parts[0]}")
                    month = int(parts[1])
                    day = int(parts[2])
                    report_date = date(year, month, day)
                else:
                    # Assume already in correct format
                    report_date = date_str

                # Insert or update (ON CONFLICT DO UPDATE)
                query = """
                    INSERT INTO wisefn_analyst_reports
                        (stock_code, report_date, brokerage, target_price, price_change, opinion, title, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, CURRENT_TIMESTAMP)
                    ON CONFLICT (stock_code, report_date, brokerage)
                    DO UPDATE SET
                        target_price = EXCLUDED.target_price,
                        price_change = EXCLUDED.price_change,
                        opinion = EXCLUDED.opinion,
                        title = EXCLUDED.title,
                        updated_at = CURRENT_TIMESTAMP
                """

                await db.execute(
                    query,
                    stock_code,
                    report_date,
                    report['brokerage'],
                    report['target_price'],
                    report['price_change'],
                    report['opinion'],
                    report['title']
                )

                saved_count += 1

            except Exception as e:
                print(f"⚠️  Failed to save report: {e}")
                continue

        print(f"💾 Saved {saved_count}/{len(reports)} reports to database")
        return saved_count

    async def fetch_and_save(self, stock_code: str) -> List[Dict[str, Any]]:
        """
        Fetch reports from WISEfn and save to database

        Args:
            stock_code: Stock code

        Returns:
            List of report dictionaries
        """
        reports = await self.fetch_reports(stock_code)
        if reports:
            await self.save_to_db(stock_code, reports)
        return reports

    @staticmethod
    async def get_from_db(stock_code: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get reports from database (fast, no scraping)

        Args:
            stock_code: Stock code
            limit: Maximum number of reports to return

        Returns:
            List of report dictionaries
        """
        query = """
            SELECT
                report_date,
                brokerage,
                target_price,
                price_change,
                opinion,
                title
            FROM wisefn_analyst_reports
            WHERE stock_code = $1
            ORDER BY report_date DESC
            LIMIT $2
        """

        rows = await db.fetch(query, stock_code, limit)

        reports = []
        for row in rows:
            # Convert date to YY.MM.DD format
            date_obj = row['report_date']
            date_str = date_obj.strftime('%y.%m.%d')

            reports.append({
                'date': date_str,
                'brokerage': row['brokerage'],
                'target_price': row['target_price'],
                'price_change': row['price_change'],
                'opinion': row['opinion'],
                'title': row['title']
            })

        return reports
