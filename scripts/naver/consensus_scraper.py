"""
Naver Finance Investment Consensus Scraper
Scrapes investment consensus data from Naver Finance using Playwright
Saves to database for efficient access
"""
from playwright.async_api import async_playwright
from typing import Dict, Any, Optional
import asyncio
import sys
from datetime import date
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db

class NaverConsensusScraper:
    BASE_URL = "https://finance.naver.com/item/main.naver"

    async def fetch_consensus(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        Fetch investment consensus data using Playwright

        Args:
            stock_code: Stock code (e.g., '015760')

        Returns:
            Dictionary with structure:
            {
                'consensus_score': 3.95,
                'buy_count': 10,
                'hold_count': 2,
                'sell_count': 0,
                'target_price': 62000,
                'eps': 1234,
                'per': 15.67,
                'analyst_count': 12
            }
        """
        url = f"{self.BASE_URL}?code={stock_code}"
        consensus_data = None

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Navigate to page
                await page.goto(url, wait_until='networkidle')

                # Wait for investment info table
                await page.wait_for_selector('table', timeout=10000)

                # Extract consensus data using JavaScript
                consensus_data = await page.evaluate('''() => {
                    // Find investment opinion table
                    const tables = document.querySelectorAll('table');
                    let consensusScore = null;
                    let targetPrice = null;

                    for (let table of tables) {
                        const text = table.textContent;
                        if (text.includes('투자의견') && text.includes('목표주가')) {
                            const rows = table.querySelectorAll('tr');

                            for (let row of rows) {
                                const th = row.querySelector('th');
                                const td = row.querySelector('td');

                                if (!th || !td) continue;

                                const label = th.textContent.trim();
                                const value = td.textContent.trim();

                                if (label.includes('투자의견')) {
                                    // Extract score: "3.79매수 l 목표주가 59,846"
                                    const scoreMatch = value.match(/(\\d+\\.\\d+)/);
                                    if (scoreMatch) {
                                        consensusScore = parseFloat(scoreMatch[1]);
                                    }

                                    // Extract target price
                                    const parts = value.split('l');
                                    if (parts.length >= 2) {
                                        const priceStr = parts[1].replace(/[^0-9]/g, '');
                                        if (priceStr) {
                                            targetPrice = parseInt(priceStr);
                                        }
                                    }
                                }
                            }
                            break;
                        }
                    }

                    // Find EPS and PER from financial info
                    let eps = null, per = null;

                    for (let table of tables) {
                        const text = table.textContent;
                        if (text.includes('EPS') && text.includes('PER')) {
                            const rows = table.querySelectorAll('tr');

                            for (let row of rows) {
                                const cells = row.querySelectorAll('td, th');
                                const rowText = row.textContent;

                                if (rowText.includes('EPS') && rowText.includes('PER')) {
                                    // Try to extract EPS and PER values
                                    const epsMatch = rowText.match(/EPS[^0-9]+(\\d+[,\\d]*)/);
                                    const perMatch = rowText.match(/PER[^0-9]+([\\d.]+)/);

                                    if (epsMatch) {
                                        eps = parseInt(epsMatch[1].replace(/,/g, ''));
                                    }
                                    if (perMatch) {
                                        per = parseFloat(perMatch[1]);
                                    }
                                }
                            }
                        }
                    }

                    return {
                        consensusScore,
                        buyCount: 0,  // Not available in simple view
                        holdCount: 0,
                        sellCount: 0,
                        targetPrice,
                        eps,
                        per,
                        analystCount: null
                    };
                }''')

                await browser.close()

                if consensus_data and consensus_data.get('consensusScore'):
                    print(f"✅ Scraped consensus data from Naver Finance")
                    print(f"   Score: {consensus_data['consensusScore']}/5.0")
                    print(f"   Analysts: Buy={consensus_data['buyCount']}, Hold={consensus_data['holdCount']}, Sell={consensus_data['sellCount']}")
                else:
                    print(f"⚠️  No consensus data found")
                    return None

        except Exception as e:
            print(f"❌ Naver Finance scraping error: {e}")
            return None

        # Convert to snake_case keys
        if consensus_data:
            return {
                'consensus_score': consensus_data['consensusScore'],
                'buy_count': consensus_data['buyCount'],
                'hold_count': consensus_data['holdCount'],
                'sell_count': consensus_data['sellCount'],
                'target_price': consensus_data['targetPrice'],
                'eps': consensus_data['eps'],
                'per': consensus_data['per'],
                'analyst_count': consensus_data['analystCount']
            }

        return None

    async def save_to_db(self, stock_code: str, consensus: Dict[str, Any]) -> bool:
        """
        Save consensus data to database

        Args:
            stock_code: Stock code
            consensus: Consensus dictionary from fetch_consensus()

        Returns:
            True if saved successfully
        """
        if not consensus:
            return False

        try:
            # Use today's date as data_date
            data_date = date.today()

            # Insert or update (ON CONFLICT DO UPDATE)
            query = """
                INSERT INTO investment_consensus
                    (stock_code, data_date, consensus_score, buy_count, hold_count, sell_count,
                     target_price, eps, per, analyst_count, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, CURRENT_TIMESTAMP)
                ON CONFLICT (stock_code, data_date)
                DO UPDATE SET
                    consensus_score = EXCLUDED.consensus_score,
                    buy_count = EXCLUDED.buy_count,
                    hold_count = EXCLUDED.hold_count,
                    sell_count = EXCLUDED.sell_count,
                    target_price = EXCLUDED.target_price,
                    eps = EXCLUDED.eps,
                    per = EXCLUDED.per,
                    analyst_count = EXCLUDED.analyst_count,
                    updated_at = CURRENT_TIMESTAMP
            """

            await db.execute(
                query,
                stock_code,
                data_date,
                consensus['consensus_score'],
                consensus['buy_count'],
                consensus['hold_count'],
                consensus['sell_count'],
                consensus['target_price'],
                consensus['eps'],
                consensus['per'],
                consensus['analyst_count']
            )

            print(f"💾 Saved consensus data to database")
            return True

        except Exception as e:
            print(f"⚠️  Failed to save consensus: {e}")
            return False

    async def fetch_and_save(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        Fetch consensus from Naver Finance and save to database

        Args:
            stock_code: Stock code

        Returns:
            Consensus dictionary
        """
        consensus = await self.fetch_consensus(stock_code)
        if consensus:
            await self.save_to_db(stock_code, consensus)
        return consensus

    @staticmethod
    async def get_from_db(stock_code: str) -> Optional[Dict[str, Any]]:
        """
        Get consensus from database (fast, no scraping)

        Args:
            stock_code: Stock code

        Returns:
            Consensus dictionary or None
        """
        query = """
            SELECT
                consensus_score,
                buy_count,
                hold_count,
                sell_count,
                target_price,
                eps,
                per,
                analyst_count,
                data_date
            FROM investment_consensus
            WHERE stock_code = $1
            ORDER BY data_date DESC
            LIMIT 1
        """

        row = await db.fetchrow(query, stock_code)

        if row:
            return {
                'consensus_score': float(row['consensus_score']) if row['consensus_score'] else None,
                'buy_count': row['buy_count'],
                'hold_count': row['hold_count'],
                'sell_count': row['sell_count'],
                'target_price': row['target_price'],
                'eps': row['eps'],
                'per': float(row['per']) if row['per'] else None,
                'analyst_count': row['analyst_count'],
                'data_date': row['data_date']
            }

        return None
