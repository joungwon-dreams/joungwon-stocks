"""
Professional Stock Analysis PDF Report Generator
Based on 'Sample.pdf' style (Generative AI Equity Research)

================================================================================
⚠️  CRITICAL: PDF 구조 변경 금지 (STRUCTURE LOCKED)
================================================================================
이 파일의 PDF 구조는 잠겨 있습니다. 구조 변경 전 반드시 확인하세요:

1. 명세서 확인: docs/PDF_STRUCTURE_SPECIFICATION.md
2. 사용자 승인 필요
3. 변경 시 명세서 버전 업데이트 필수

변경 금지 항목:
- 섹션 순서 및 제목 (이모지 포함)
- 테이블 컬럼 순서/너비
- 색상 코드
- 폰트 크기
- 페이지 브레이크 위치
- 차트 크기/비율

Version: 1.0.0 (Locked)
Last Structure Update: 2025-11-28
================================================================================

Report Structure (v1):
1. Header / Investment Opinion / Key Metrics / Company Overview
2. Investment Consensus / Analyst Targets / Recent 2-Week Trend
3. Holding Status / Real-time Ticks
4. Price Trend (120-day)
5. Financial Performance / Investor Trends (30d & 1yr)
6. Peer Comparison
7. News
"""
import asyncio
import sys
import io
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib import rcParams
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db
from scripts.gemini.naver.news import NaverNewsFetcher
from scripts.gemini.naver.consensus import NaverConsensusFetcher
from scripts.gemini.components.peer import generate_peer_comparison_chart, create_peer_table 
from scripts.gemini.components.consensus import create_consensus_detail_section, create_mini_opinion_bar
from scripts.gemini.components.holding import create_holding_status_table 
from scripts.gemini.components.realtime import generate_realtime_tick_chart, create_min_ticks_table_compact, create_stock_realtime_dashboard
from scripts.gemini.components.portfolio_advisor import PortfolioAdvisor

# Set Korean font for matplotlib
rcParams['font.family'] = 'AppleGothic'
rcParams['axes.unicode_minus'] = False

# Register Korean font for ReportLab
try:
    pdfmetrics.registerFont(TTFont('AppleGothic', '/System/Library/Fonts/Supplemental/AppleGothic.ttf'))
except:
    pass

class PDFReportGenerator:
    def __init__(self, stock_code: str):
        self.stock_code = stock_code
        self.report_date = datetime.now().strftime('%Y년 %m월 %d일')
        self.output_dir = Path('/Users/wonny/Dev/joungwon.stocks/reports/holding_stock')
        self.output_dir.mkdir(exist_ok=True)
        # BytesIO 버퍼로 차트 저장 (파일 I/O 제거)
        self.chart_buffers = {}

    async def fetch_all_data(self):
        """Fetch all required data from database, with realtime fallback for missing data"""
        print(f"📊 Fetching data for {self.stock_code}...")

        # Basic info
        query = "SELECT s.stock_code, s.stock_name, s.sector, s.market FROM stocks s WHERE s.stock_code = $1"
        self.stock_info = await db.fetchrow(query, self.stock_code)

        # Fundamentals
        query = "SELECT * FROM stock_fundamentals WHERE stock_code = $1"
        self.fundamentals = await db.fetchrow(query, self.stock_code)

        # Fetch company_summary from Naver if missing
        if self.fundamentals and not self.fundamentals.get('company_summary'):
            print(f"   ⚠️ company_summary 없음 → 네이버에서 실시간 수집")
            await self._fetch_company_summary_from_naver()

        # Consensus - from Naver Mobile API (fast, no Playwright needed)
        consensus_fetcher = NaverConsensusFetcher()
        consensus_api = await consensus_fetcher.fetch_consensus(self.stock_code)
        
        if consensus_api:
            self.consensus = {
                'target_price': consensus_api.get('target_price', ''),
                'consensus_score': float(consensus_api.get('opinion', 3.0)) if consensus_api.get('opinion') else 3.0
            }
            print(f"   ✅ consensus API 수집 완료: 목표가 {self.consensus.get('target_price')}")
        else:
            self.consensus = None
            print(f"   ⚠️ consensus 없음")

        # Financial statements (yearly)
        query = """
            SELECT fiscal_year, revenue, operating_profit, net_profit
            FROM stock_financials
            WHERE stock_code = $1 AND period_type = 'yearly'
            ORDER BY fiscal_year DESC LIMIT 5
        """
        self.financials_yearly = await db.fetch(query, self.stock_code)

        # OHLCV (last 365 days for 1 year charts)
        query = """
            SELECT date, close, volume
            FROM daily_ohlcv
            WHERE stock_code = $1
            ORDER BY date DESC LIMIT 365
        """
        self.ohlcv = await db.fetch(query, self.stock_code)

        # Investor trends (last 260 days for 1 year chart)
        query = """
            SELECT trade_date, individual, "foreign", institutional
            FROM investor_trends
            WHERE stock_code = $1
            ORDER BY trade_date DESC LIMIT 260
        """
        self.investor_trends = await db.fetch(query, self.stock_code)

        # Peers
        query = """
            SELECT p.peer_code, p.peer_name, f.per, f.pbr, f.roe, f.current_price, f.market_cap
            FROM stock_peers p
            LEFT JOIN stock_fundamentals f ON p.peer_code = f.stock_code
            WHERE p.stock_code = $1 LIMIT 5
        """
        self.peers = await db.fetch(query, self.stock_code)

        # News
        news_fetcher = NaverNewsFetcher()
        self.news = await news_fetcher.fetch_news(self.stock_code)
        
        # Target Price News
        if self.stock_info:
             self.target_price_news = await news_fetcher.fetch_target_price_news(self.stock_code, self.stock_info['stock_name'])
        else:
             self.target_price_news = []

        # Consensus Detail
        consensus_fetcher = NaverConsensusFetcher()
        self.consensus_detail = await consensus_fetcher.fetch_consensus_detail(self.stock_code)

        # Analyst Targets from Database (WISEfn data)
        from scripts.gemini.wisefn.reports_scraper import WISEfnReportsScraper
        wisefn_reports = await WISEfnReportsScraper.get_from_db(self.stock_code, limit=10)

        # Fetch from WISEfn if no reports in DB
        if not wisefn_reports:
            print(f"   ⚠️ WISEfn 리포트 없음 → WISEfn에서 실시간 수집")
            wisefn_scraper = WISEfnReportsScraper()
            fetched_reports = await wisefn_scraper.fetch_reports(self.stock_code)
            if fetched_reports:
                await wisefn_scraper.save_to_db(self.stock_code, fetched_reports)
                wisefn_reports = await WISEfnReportsScraper.get_from_db(self.stock_code, limit=10)

        # Convert WISEfn format to analyst_targets format
        self.analyst_targets = []
        for report in (wisefn_reports or []):
            # Convert date format: YY.MM.DD -> YYYYMMDD
            date_str = report['date']  # e.g., "25.11.25"
            if '.' in date_str:
                parts = date_str.split('.')
                report_date = f"20{parts[0]}{parts[1]}{parts[2]}"  # "20251125"
            else:
                report_date = date_str

            self.analyst_targets.append({
                'brokerage': report['brokerage'],
                'target_price': report['target_price'],
                'opinion': report['opinion'],
                'report_date': report_date,
                'title': report['title']
            })
            
        # Holding Assets (New)
        query = "SELECT stock_code, stock_name, quantity, avg_buy_price FROM stock_assets WHERE stock_code = $1"
        self.holding = await db.fetchrow(query, self.stock_code)

        # Claude Code Recommendation (신규종목추천 AI 분석 결과)
        query = """
            SELECT recommendation_date, recommended_price, recommendation_type,
                   total_score, gemini_reasoning, note, created_at
            FROM recommendation_history
            WHERE stock_code = $1
            ORDER BY recommendation_date DESC
            LIMIT 1
        """
        self.recommendation = await db.fetchrow(query, self.stock_code)

        # Real-time Min Ticks (New) - with prev_price, prev_volume for comparison
        query = """
            SELECT
                timestamp,
                price,
                volume,
                change_rate,
                LAG(price, 1) OVER (ORDER BY timestamp) as prev_price,
                LAG(volume, 1) OVER (ORDER BY timestamp) as prev_volume
            FROM min_ticks
            WHERE stock_code = $1
            ORDER BY timestamp DESC
            LIMIT 60
        """
        self.min_ticks = await db.fetch(query, self.stock_code)

        # AI Portfolio Feedback (NEW)
        self.ai_feedback = None
        if self.holding and self.holding.get('avg_buy_price'):
            try:
                advisor = PortfolioAdvisor()

                # Get current price
                current_p = 0
                if self.min_ticks:
                    current_p = self.min_ticks[0]['price']
                elif self.ohlcv:
                    current_p = self.ohlcv[0]['close']
                elif self.fundamentals:
                    current_p = self.fundamentals.get('current_price', 0) or 0

                if current_p > 0:
                    # Get investor data for last 5 days
                    investor_data = None
                    if self.investor_trends and len(self.investor_trends) >= 5:
                        foreign_5d = sum(row['foreign'] for row in self.investor_trends[:5])
                        institutional_5d = sum(row['institutional'] for row in self.investor_trends[:5])
                        investor_data = {'foreign_5d': foreign_5d, 'institutional_5d': institutional_5d}

                    # Get news summary (first 3 news titles)
                    news_summary = None
                    if self.news and len(self.news) > 0:
                        news_titles = [n.get('title', '') for n in self.news[:3]]
                        news_summary = ' / '.join(news_titles)

                    # Process AI feedback
                    self.ai_feedback = await advisor.process_daily_feedback(
                        stock_code=self.stock_code,
                        stock_name=self.stock_info['stock_name'],
                        avg_buy_price=float(self.holding['avg_buy_price']),
                        current_price=float(current_p),
                        investor_data=investor_data,
                        news_summary=news_summary
                    )
                    print(f"   ✅ AI Feedback generated: {self.ai_feedback.get('today_strategy', {}).get('recommendation', 'N/A')}")
            except Exception as e:
                print(f"   ⚠️ AI Feedback failed: {e}")
                import traceback
                traceback.print_exc()

        print(f"   ✅ Data fetched successfully")
        print(f"   DEBUG: Consensus keys: {self.consensus.keys() if self.consensus else 'None'}")
        print(f"   DEBUG: Analyst Targets count: {len(self.analyst_targets) if self.analyst_targets else 0}")

    async def _fetch_company_summary_from_naver(self):
        """Fetch company summary from Naver Finance and update fundamentals"""
        try:
            import aiohttp
            from bs4 import BeautifulSoup

            url = f"https://finance.naver.com/item/main.naver?code={self.stock_code}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')

                        # Find company summary div
                        summary_div = soup.find('div', class_='summary_info')
                        if summary_div:
                            summary_text = summary_div.get_text(strip=True)
                            # Clean up text
                            summary_text = ' '.join(summary_text.split())

                            if summary_text and len(summary_text) > 20:
                                # Update fundamentals dict (in-memory)
                                if self.fundamentals:
                                    # Convert Record to dict for modification
                                    self.fundamentals = dict(self.fundamentals)
                                    self.fundamentals['company_summary'] = summary_text

                                # Also save to database
                                await db.execute("""
                                    UPDATE stock_fundamentals
                                    SET company_summary = $1
                                    WHERE stock_code = $2
                                """, summary_text, self.stock_code)
                                print(f"   ✅ company_summary 수집 완료 ({len(summary_text)}자)")
                                return

                        # Alternative: Try meta description
                        meta_desc = soup.find('meta', attrs={'name': 'description'})
                        if meta_desc and meta_desc.get('content'):
                            summary_text = meta_desc['content']
                            if self.fundamentals:
                                self.fundamentals = dict(self.fundamentals)
                                self.fundamentals['company_summary'] = summary_text
                            await db.execute("""
                                UPDATE stock_fundamentals
                                SET company_summary = $1
                                WHERE stock_code = $2
                            """, summary_text, self.stock_code)
                            print(f"   ✅ company_summary (meta) 수집 완료 ({len(summary_text)}자)")
        except Exception as e:
            print(f"   ❌ company_summary 수집 실패: {e}")

    def generate_charts(self):
        """Generate all charts"""
        print(f"📈 Generating charts...")

        if self.ohlcv:
            self._generate_price_chart()
            self._generate_mini_2week_chart() 
        
        if hasattr(self, 'min_ticks') and self.min_ticks:
            # BytesIO 버퍼에 저장
            self.chart_buffers['realtime_tick_chart'] = generate_realtime_tick_chart(self.min_ticks)

        if self.financials_yearly:
            self._generate_financial_chart()
        if self.investor_trends:
            self._generate_investor_chart()
            self._generate_investor_year_chart()
        if self.peers:
            self._generate_peer_chart()

        print(f"   ✅ Charts generated")

    def _generate_price_chart(self):
        # Use only last 120 days for the price trend chart
        data_120 = self.ohlcv[:120] if self.ohlcv else []
        
        dates = [row['date'] for row in reversed(data_120)]
        prices = [row['close'] for row in reversed(data_120)]
        volumes = [row['volume'] for row in reversed(data_120)]

        # Trend color: Red for Up, Blue for Down
        start_price = prices[0]
        end_price = prices[-1]
        trend_color = '#D32F2F' if end_price >= start_price else '#1976D2'

        # Height increased by 10% (6 -> 6.6)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.6), height_ratios=[3, 1])

        ax1.plot(dates, prices, linewidth=2, color=trend_color)
        ax1.fill_between(dates, prices, alpha=0.1, color=trend_color)
        ax1.set_title(f'{self.stock_info["stock_name"]} 주가 추이 (120일)', fontsize=14, fontweight='bold')
        ax1.set_ylabel('주가 (원)', fontsize=10)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.tick_params(axis='x', labelsize=8, rotation=0)
        # Reduce x-ticks density
        import matplotlib.ticker as ticker
        ax1.xaxis.set_major_locator(ticker.MaxNLocator(6))
        
        # Add average buy price as a thick straight line to ax1
        if hasattr(self, 'holding') and self.holding and self.holding.get('avg_buy_price'):
            avg_buy_price = float(self.holding['avg_buy_price'])
            ax1.axhline(y=avg_buy_price, color='purple', linestyle='-', linewidth=2, alpha=0.8, label='Avg Buy Price')
            ax1.text(dates[0], avg_buy_price, f"평단가: {int(avg_buy_price):,}", color='purple', va='bottom', ha='left', fontsize=8)

        # Color volumes based on price change from previous day
        vol_colors = []
        prev_p = prices[0]
        for p in prices:
            if p >= prev_p:
                vol_colors.append('#D32F2F') # Red
            else:
                vol_colors.append('#1976D2') # Blue
            prev_p = p

        ax2.bar(dates, volumes, color=vol_colors, alpha=0.7)
        ax2.set_ylabel('거래량', fontsize=10)
        ax2.xaxis.set_major_locator(ticker.MaxNLocator(6))
        ax2.tick_params(axis='x', labelsize=8, rotation=0)
        ax2.grid(True, alpha=0.3, linestyle='--')

        plt.tight_layout()
        # BytesIO 버퍼에 저장
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        self.chart_buffers['price_trend'] = buf
        plt.close()

    def _generate_mini_2week_chart(self):
        # Data Preparation
        data = list(reversed(self.ohlcv)) if self.ohlcv else []
        
        # Check if latest data is missing (e.g. today's data not in daily_ohlcv yet)
        if data:
            last_date = data[-1]['date'] # datetime.date
            today = datetime.now().date()
            # If last date is not today (and maybe not yesterday if it's morning), append current price
            # Simple logic: If last date < today, try to append current price as a new point
            if last_date < today and self.fundamentals and self.fundamentals.get('current_price'):
                current_p = self.fundamentals['current_price']
                # Mock a row
                data.append({'date': today, 'close': current_p, 'volume': 0})
        
        # Take last 14 days
        data_2w = data[-14:]
        if not data_2w: return

        dates = [row['date'] for row in data_2w]
        prices = [row['close'] for row in data_2w]
        
        current_price = prices[-1]
        start_price = prices[0]
        
        # Color based on trend
        color = '#D32F2F' if current_price >= start_price else '#1976D2'

        # Height increased further (4.7 -> 5.5)
        fig, ax = plt.subplots(figsize=(8, 5.5))
        ax.plot(dates, prices, marker='o', markersize=4, linewidth=2, color=color)
        
        # Horizontal line for current price
        ax.axhline(y=current_price, color='gray', linestyle='--', linewidth=1, alpha=0.7, label='Current Price')
        
        # Add average buy price as a thick straight line
        if hasattr(self, 'holding') and self.holding and self.holding.get('avg_buy_price'):
            avg_buy_price = float(self.holding['avg_buy_price'])
            ax.axhline(y=avg_buy_price, color='#9C27B0', linestyle='-', linewidth=3.5, alpha=0.9, label='평단가')
            # Large bold font for avg price label
            ax.text(dates[-1], avg_buy_price, f"  평단가: {int(avg_buy_price):,}", color='#9C27B0', va='center', ha='left', fontsize=14, fontweight='bold')

        # Annotate Current Price
        ax.text(dates[-1], current_price, f"{current_price:,}", color=color, fontweight='bold', va='bottom', ha='right')

        ax.set_title('최근 2주 주가 변화', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Y-axis comma formatter
        import matplotlib.ticker as ticker
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
        
        # Format X-axis dates (MM-DD)
        import matplotlib.dates as mdates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        # BytesIO 버퍼에 저장
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        self.chart_buffers['mini_2week_chart'] = buf
        plt.close()

    def _generate_financial_chart(self):
        years = [str(row['fiscal_year']) for row in reversed(self.financials_yearly)]
        revenue = [row['revenue']/100000000 for row in reversed(self.financials_yearly)]
        op_profit = [row['operating_profit']/100000000 for row in reversed(self.financials_yearly)]
        net_profit = [row['net_profit']/100000000 for row in reversed(self.financials_yearly)]

        x = np.arange(len(years))
        width = 0.25

        # Height decreased further (4.0 -> 2.8)
        fig, ax = plt.subplots(figsize=(10, 2.8))
        # Revenue (Gray), Op Profit (Red), Net Profit (Blue) - Standardize
        ax.bar(x - width, revenue, width, label='매출액', color='#757575')
        ax.bar(x, op_profit, width, label='영업이익', color='#D32F2F')
        ax.bar(x + width, net_profit, width, label='순이익', color='#1976D2')

        ax.set_title('연간 재무 실적 추이 (단위: 억원)', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(years)
        ax.legend(fontsize=10, loc='upper left')
        ax.grid(True, alpha=0.3, axis='y', linestyle='--')

        plt.tight_layout()
        # BytesIO 버퍼에 저장
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        self.chart_buffers['financial_performance'] = buf
        plt.close()

    def _generate_investor_chart(self):
        # Use first 30 items (since list is sorted DESC, first 30 are latest)
        data_30 = self.investor_trends[:30]
        if not data_30: return

        dates = [row['trade_date'] for row in reversed(data_30)]
        foreign = [row['foreign']/1000 for row in reversed(data_30)]
        institutional = [row['institutional']/1000 for row in reversed(data_30)]

        # Prepare Price Data - 30일 OHLCV 데이터 사용
        ohlcv_30 = self.ohlcv[:30] if self.ohlcv else []
        price_dates = [row['date'] for row in reversed(ohlcv_30)]
        prices = [float(row['close']) for row in reversed(ohlcv_30)]

        # Subplots: 2 rows, share X axis
        import matplotlib.ticker as ticker
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=False, height_ratios=[1, 1])

        # Top: Price Chart (30일 주가 차트)
        if prices:
            ax1.plot(price_dates, prices, color='#455A64', linewidth=2, label='주가')
            ax1.set_ylabel('주가 (원)', fontsize=9)
            ax1.grid(True, alpha=0.3, linestyle='--')
            ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
            ax1.xaxis.set_major_locator(ticker.MaxNLocator(6))
            ax1.tick_params(axis='x', labelsize=8, rotation=0)
            ax1.set_title('주가 추이 (30일)', fontsize=12, fontweight='bold')

            # Add average buy price as a thick straight line
            if hasattr(self, 'holding') and self.holding and self.holding.get('avg_buy_price'):
                avg_buy_price = float(self.holding['avg_buy_price'])
                ax1.axhline(y=avg_buy_price, color='#9C27B0', linestyle='-', linewidth=3.5, alpha=0.9, label='평단가')
                ax1.text(price_dates[-1], avg_buy_price, f"  평단가: {int(avg_buy_price):,}", color='#9C27B0', va='center', ha='left', fontsize=12, fontweight='bold')

            ax1.legend(loc='upper left', fontsize=9)

        # Bottom: Investor Trends
        ax2.plot(dates, foreign, marker='o', linewidth=2, label='외국인', color='#E64A19', markersize=4)
        ax2.plot(dates, institutional, marker='s', linewidth=2, label='기관', color='#512DA8', markersize=4)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.3)
        ax2.set_ylabel('순매수량 (천주)', fontsize=9)
        ax2.legend(loc='upper left', fontsize=9)
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.set_title('투자자별 순매수 추이 (30일)', fontsize=12, fontweight='bold')

        ax2.xaxis.set_major_locator(ticker.MaxNLocator(6))
        ax2.tick_params(axis='x', labelsize=8, rotation=0)

        plt.tight_layout()
        # BytesIO 버퍼에 저장
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        self.chart_buffers['investor_trends'] = buf
        plt.close()

    def _generate_investor_year_chart(self):
        # Use all data (up to 260 days)
        # Cumulative sum chart
        data = list(reversed(self.investor_trends))
        if not data: return

        dates = [row['trade_date'] for row in data]
        # Calculate cumulative sum (unit: 1000 shares)
        foreign_cum = np.cumsum([row['foreign']/1000 for row in data])
        institutional_cum = np.cumsum([row['institutional']/1000 for row in data])
        # individual_cum = np.cumsum([row['individual']/1000 for row in data])

        # Prepare Price Data - 1년 (365일) OHLCV 데이터 사용
        ohlcv_year = self.ohlcv[:365] if self.ohlcv else []  # 최신 365일
        price_dates = [row['date'] for row in reversed(ohlcv_year)]
        prices = [float(row['close']) for row in reversed(ohlcv_year)]

        # Subplots
        import matplotlib.ticker as ticker
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=False, height_ratios=[1, 1])

        # Top: Price Chart (1년 주가 차트)
        if prices:
            ax1.plot(price_dates, prices, color='#455A64', linewidth=2, label='주가')
            ax1.fill_between(price_dates, prices, alpha=0.1, color='#455A64')
            ax1.set_title('주가 추이 (1년)', fontsize=12, fontweight='bold')
            ax1.set_ylabel('주가 (원)', fontsize=9)
            ax1.grid(True, alpha=0.3, linestyle='--')
            ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
            ax1.xaxis.set_major_locator(ticker.MaxNLocator(8))
            ax1.tick_params(axis='x', labelsize=8, rotation=0)

            # Add average buy price as a thick straight line
            if hasattr(self, 'holding') and self.holding and self.holding.get('avg_buy_price'):
                avg_buy_price = float(self.holding['avg_buy_price'])
                ax1.axhline(y=avg_buy_price, color='#9C27B0', linestyle='-', linewidth=3.5, alpha=0.9, label='평단가')
                ax1.text(price_dates[-1], avg_buy_price, f"  평단가: {int(avg_buy_price):,}", color='#9C27B0', va='center', ha='left', fontsize=12, fontweight='bold')

            ax1.legend(loc='upper left', fontsize=9)

        # Bottom: Cumulative Trends
        ax2.plot(dates, foreign_cum, linewidth=2, label='외국인 누적', color='#E64A19')
        ax2.plot(dates, institutional_cum, linewidth=2, label='기관 누적', color='#512DA8')
        # ax2.plot(dates, individual_cum, linewidth=1, label='개인 누적', color='#388E3C', alpha=0.6, linestyle='--')

        ax2.set_title('투자자별 누적 순매수 추이 (1년)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('누적 순매수량 (천주)', fontsize=9)
        ax2.legend(loc='upper left', fontsize=9)
        ax2.grid(True, alpha=0.3, linestyle='--')

        ax2.xaxis.set_major_locator(ticker.MaxNLocator(8))
        ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
        ax2.tick_params(axis='x', labelsize=8, rotation=0)

        plt.tight_layout()
        # BytesIO 버퍼에 저장
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        self.chart_buffers['investor_trends_year'] = buf
        plt.close()

    def _generate_peer_chart(self):
        # Helper for safe float conversion
        def safe_float(val):
            try:
                if val is None: return 0.0
                return float(val)
            except:
                return 0.0

        # Prepare data for helper function
        peers_data = []
        
        # Add target company first
        peers_data.append({
            'name': self.stock_info['stock_name'],
            'price': self.fundamentals['current_price'] or 0,
            'market_cap': self.fundamentals['market_cap'] or 0,
            'per': safe_float(self.fundamentals['per']),
            'pbr': safe_float(self.fundamentals['pbr']),
            'roe': safe_float(self.fundamentals['roe'])
        })
        
        # Add peer companies
        for peer in self.peers:
            peers_data.append({
                'name': peer['peer_name'],
                'price': peer['current_price'] or 0,
                'market_cap': peer['market_cap'] or 0,
                'per': safe_float(peer['per']),
                'pbr': safe_float(peer['pbr']),
                'roe': safe_float(peer['roe'])
            })
            
        # BytesIO 버퍼에 저장
        self.chart_buffers['peer_comparison'] = generate_peer_comparison_chart(peers_data)

    def draw_header(self, canvas, doc):
        """Draw header on every page"""
        canvas.saveState()

        # Settings
        stock_title = f"{self.stock_info['stock_name']} ({self.stock_code})"

        # Claude Code 추천 정보 추가
        if hasattr(self, 'recommendation') and self.recommendation:
            rec_date = self.recommendation['recommendation_date'].strftime('%Y-%m-%d')
            stock_title += f" - Claude Code 추천 ({rec_date})"

        now = datetime.now()
        date_str = now.strftime("%Y/%m/%d")
        time_str = now.strftime("%H:%M:%S")
        page_num = doc.page

        # Draw Left: Stock Title
        canvas.setFont('AppleGothic', 16)  # 폰트 크기 조정 (긴 제목 대응)
        canvas.setFillColor(colors.black)
        canvas.drawString(1.5*cm, A4[1] - 2.0*cm, stock_title)
        
        # Draw Right: Date/Time/Page
        canvas.setFont('AppleGothic', 8)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(A4[0] - 1.5*cm, A4[1] - 1.6*cm, f"DATE {date_str}")
        canvas.drawRightString(A4[0] - 1.5*cm, A4[1] - 2.0*cm, f"TIME {time_str}")
        canvas.drawRightString(A4[0] - 1.5*cm, A4[1] - 2.4*cm, f"PAGE {page_num}")
        
        # Draw Line
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(2)
        canvas.line(1.5*cm, A4[1] - 2.7*cm, A4[0] - 1.5*cm, A4[1] - 2.7*cm)
        
        canvas.restoreState()

    def generate_pdf(self):
        """Generate PDF report"""
        print(f"📝 Generating PDF report...")

        # Format: 종목명_MMDDHHMM.pdf (예: 한국전력_11251621.pdf)
        stock_name = self.stock_info['stock_name']

        output_path = self.output_dir / f'{stock_name}.pdf'
        
        # Top margin increased to 3.5cm to fit the header
        doc = SimpleDocTemplate(str(output_path), pagesize=A4,
                                leftMargin=1.5*cm, rightMargin=1.5*cm,
                                topMargin=3.5*cm, bottomMargin=1.5*cm)

        story = []
        styles = getSampleStyleSheet()

        # Sub-header: Generative AI Equity Research
        story.append(Paragraph("Generative AI Equity Research", ParagraphStyle('SubHeader', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#555555'), alignment=TA_LEFT, spaceAfter=20)))

        # Helper for safe float conversion
        def safe_float(val):
            try:
                if val is None or val == '': return 0.0
                return float(val)
            except:
                return 0.0

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='AppleGothic',
            fontSize=24,
            textColor=colors.HexColor('#212121'),
            spaceAfter=20,
            alignment=TA_CENTER,
            leading=30
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName='AppleGothic',
            fontSize=15,
            textColor=colors.HexColor('#1565C0'), # Blue heading
            spaceAfter=12,
            spaceBefore=20,
            borderPadding=5,
            borderWidth=0,
            borderColor=colors.HexColor('#E0E0E0'),
            borderRadius=5
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName='AppleGothic',
            fontSize=10,
            leading=16
        )
        
        # Determine Investment Opinion & Color Scheme
        consensus_score = safe_float(self.consensus.get('consensus_score')) if self.consensus else 3.0
        
        if consensus_score >= 4.0:
            main_color = colors.HexColor('#D32F2F') # Red
            opinion_text = "STRONG BUY"
            opinion_kr = "강력매수"
            opinion_emoji = "🐂"
        elif consensus_score >= 3.5:
            main_color = colors.HexColor('#FF5252') # Light Red
            opinion_text = "BUY"
            opinion_kr = "매수"
            opinion_emoji = "📈"
        elif consensus_score >= 2.5:
            main_color = colors.HexColor('#757575') # Grey
            opinion_text = "HOLD"
            opinion_kr = "중립"
            opinion_emoji = "🐢"
        elif consensus_score >= 1.5:
            main_color = colors.HexColor('#448AFF') # Light Blue
            opinion_text = "SELL"
            opinion_kr = "매도"
            opinion_emoji = "📉"
        else:
            main_color = colors.HexColor('#1976D2') # Dark Blue
            opinion_text = "STRONG SELL"
            opinion_kr = "강력매도"
            opinion_emoji = "🐻"

        # 1. Investment Opinion Box
        upside = 0
        target_price_str = "-"
        
        if self.consensus and self.fundamentals:
            target = self.consensus.get('target_price')
            current = self.fundamentals['current_price']
            if target and current:
                # target_price가 문자열("106,375")일 수 있으므로 정수로 변환
                if isinstance(target, str):
                    target = int(target.replace(',', ''))
                upside = ((target - current) / current) * 100
                target_price_str = f"{target:,}" # KRW removed

        # Average Buy Price
        avg_price_str = "-"
        if hasattr(self, 'holding') and self.holding and self.holding.get('avg_buy_price'):
            avg_buy_price = float(self.holding['avg_buy_price'])
            if avg_buy_price > 0 and self.fundamentals and self.fundamentals.get('current_price'):
                current_p = float(self.fundamentals['current_price'])
                profit_rate = ((current_p - avg_buy_price) / avg_buy_price) * 100
                color_tag = 'red' if profit_rate >= 0 else 'blue'
                avg_price_str = f"{int(avg_buy_price):,} (<font color='{color_tag}'>{profit_rate:+.2f}%</font>)"
            else:
                avg_price_str = f"{int(avg_buy_price):,}"

        # Upside Arrow and Color
        upside_text = f"{upside:+.1f}%"
        if upside > 0:
            upside_text = f"<font color='#FFCDD2'>▲ {upside:+.1f}%</font>" # Lighter red for visibility on dark bg? No, bg is white. Wait, bg is main_color(Red/Blue).
            # Background is FAFAFA (Light Grey) for data row. So standard Red/Blue is fine.
            upside_text = f"<font color='red'>▲ {upside:+.1f}%</font>"
        elif upside < 0:
            upside_text = f"<font color='blue'>▼ {upside:+.1f}%</font>"
        
        # Style for Opinion Cells
        op_style = ParagraphStyle('OpCell', fontName='AppleGothic', fontSize=11, alignment=1, textColor=main_color)
        
        # Main Opinion Table
        # Wrap data in Paragraphs to render HTML tags
        opinion_data = [
            ['INVESTMENT OPINION', 'Current Price', 'Average Price', 'Target Price', 'Upside'],
            [
                Paragraph(f"{opinion_emoji} {opinion_text}", op_style),
                Paragraph(f"{self.fundamentals['current_price']:,}" if self.fundamentals['current_price'] else "0", op_style),
                Paragraph(avg_price_str, op_style),
                Paragraph(target_price_str, op_style),
                Paragraph(upside_text, op_style)
            ]
        ]

        opinion_table = Table(opinion_data, colWidths=[4.5*cm, 3.5*cm, 3.5*cm, 3.5*cm, 2.5*cm])
        opinion_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), main_color), # Header with opinion color
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
            ('FONTSIZE', (0, 0), (-1, 0), 9), # Header Font Size
            # Data Font Size handled by Paragraph style
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FAFAFA')),
        ]))
        story.append(opinion_table)
        story.append(Spacer(1, 1*cm))

        # 2. Key Metrics
        story.append(Paragraph("📊 Key Metrics (주요 투자지표)", heading_style))
        
        # Use safe_float for all metrics
        per = safe_float(self.fundamentals.get('per'))
        pbr = safe_float(self.fundamentals.get('pbr'))
        roe = safe_float(self.fundamentals.get('roe'))
        div_yield = safe_float(self.fundamentals.get('dividend_yield'))
        mcap = self.fundamentals.get('market_cap', 0) or 0
        foreign_ratio = safe_float(self.fundamentals.get('foreign_ratio'))
        week52_high = self.fundamentals.get('week52_high', 0) or 0
        
        metrics_data = [
            ['Metric', 'Value', 'Metric', 'Value'],
            ['PER', f"{per:.2f}", 'PBR', f"{pbr:.2f}"],
            ['ROE', f"{roe:.2f}%", 'Dividend Yield', f"{div_yield:.2f}%"],
            ['Market Cap', f"{mcap/1000000000000:.1f}조원", 'Foreign Ratio', f"{foreign_ratio:.2f}%"],
            ['Sector', self.fundamentals.get('sector', '-') or '-', '52W High', f"{week52_high:,}"],
        ]

        metrics_table = Table(metrics_data, colWidths=[4.5*cm, 4.5*cm, 4.5*cm, 4.5*cm])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#455A64')), # Dark Grey Header
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')])
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 0.5*cm))

        # 3. Company Overview
        story.append(Paragraph("🏢 Company Overview (기업 개요)", heading_style))
        comp_summary = self.fundamentals.get('company_summary') or ""
        summary_text = comp_summary[:350] + '...' if len(comp_summary) > 350 else comp_summary
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 0.3*cm))



        # 2-Week Price Trend Mini Section



        # 2-Week Price Trend Mini Section
        if 'mini_2week_chart' in self.chart_buffers:
            # Calculate change
            if len(self.ohlcv) >= 14:
                price_2w_ago = self.ohlcv[13]['close']
                current_p = self.ohlcv[0]['close']
                change_rate = ((current_p - price_2w_ago) / price_2w_ago) * 100
                change_text = f"Change (2W): {change_rate:+.2f}%"
                change_color = '#D32F2F' if change_rate > 0 else '#1976D2'
                
                # Increased font size for Change (2W) text
                story.append(Paragraph(f"<b>Recent 2-Week Trend: <font size='12' color='{change_color}'>{change_text}</font></b>", normal_style))
                story.append(Spacer(1, 0.2*cm))
                if 'mini_2week_chart' in self.chart_buffers:
                    story.append(Image(self.chart_buffers['mini_2week_chart'], width=14*cm, height=5.5*cm))
        
        # Double the spacer
        story.append(Spacer(1, 1.0*cm))

        # --- AI Portfolio Feedback Section (NEW) ---
        if hasattr(self, 'ai_feedback') and self.ai_feedback:
            feedback = self.ai_feedback
            today_strategy = feedback.get('today_strategy', {})
            yesterday_review = feedback.get('yesterday_review')

            # Section Title
            story.append(Paragraph("🤖 AI Portfolio Feedback", heading_style))

            # Recommendation colors and text
            rec = today_strategy.get('recommendation', 'HOLD')
            rec_map = {'BUY_MORE': ('추가 매수', '#4CAF50', '🟢'),
                       'HOLD': ('관망', '#9E9E9E', '⚪'),
                       'SELL': ('일부 매도', '#FF9800', '🟡'),
                       'CUT_LOSS': ('손절', '#F44336', '🔴')}
            rec_text, rec_color, rec_emoji = rec_map.get(rec, ('관망', '#9E9E9E', '⚪'))

            # Today's Strategy Box
            strategy_style = ParagraphStyle(
                'strategy', fontName='AppleGothic', fontSize=11,
                textColor=colors.HexColor(rec_color), leading=16
            )
            rationale_style = ParagraphStyle(
                'rationale', fontName='AppleGothic', fontSize=9,
                textColor=colors.HexColor('#424242'), leading=13
            )
            confidence = today_strategy.get('confidence', 0)
            confidence_bar = '█' * int(confidence * 10) + '░' * (10 - int(confidence * 10))

            strategy_data = [
                [Paragraph(f"<b>[오늘의 전략: {rec_text}]</b> {rec_emoji}", strategy_style)],
                [Paragraph(today_strategy.get('rationale', '분석 중...'), rationale_style)],
                [Paragraph(f"신뢰도: {confidence_bar} {int(confidence*100)}%", rationale_style)]
            ]

            strategy_table = Table(strategy_data, colWidths=[16.5*cm])
            strategy_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8F5E9') if rec == 'BUY_MORE'
                 else colors.HexColor('#FFEBEE') if rec in ['SELL', 'CUT_LOSS']
                 else colors.HexColor('#F5F5F5')),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
            ]))
            story.append(strategy_table)
            story.append(Spacer(1, 0.3*cm))

            # Yesterday's Review Box (if available)
            if yesterday_review:
                y_rec = yesterday_review.get('recommendation', 'HOLD')
                y_rec_text = rec_map.get(y_rec, ('관망', '#9E9E9E', '⚪'))[0]
                y_price = float(yesterday_review.get('market_price', 0))
                next_price = float(yesterday_review.get('next_day_price', 0))
                next_return = float(yesterday_review.get('next_day_return', 0))
                was_correct = yesterday_review.get('was_correct', False)
                report_date = yesterday_review.get('report_date')
                date_str = report_date.strftime('%m.%d') if report_date else '어제'

                result_emoji = '✅' if was_correct else '❌'
                result_text = '적중' if was_correct else '실패'
                return_color = 'red' if next_return > 0 else 'blue'

                review_style = ParagraphStyle(
                    'review', fontName='AppleGothic', fontSize=9,
                    textColor=colors.HexColor('#555555'), leading=13
                )

                review_text = f"""<b>[어제 회고 ({date_str})]</b> {result_emoji}
어제 의견: {y_rec_text}
어제 종가: {int(y_price):,}원 → 오늘 종가: {int(next_price):,}원 (<font color='{return_color}'>{next_return:+.2f}%</font>)
판정: {result_emoji} {result_text}"""

                # Add AI comment if available
                review_comment = today_strategy.get('review', '')
                if review_comment:
                    review_text += f"\nAI 코멘트: {review_comment}"

                review_data = [[Paragraph(review_text, review_style)]]
                review_table = Table(review_data, colWidths=[16.5*cm])
                review_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFF8E1') if was_correct else colors.HexColor('#FFEBEE')),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
                ]))
                story.append(review_table)

            story.append(Spacer(1, 0.5*cm))

        # --- Investment Consensus (Moved after 2-Week Chart) ---
        # 기준 날짜 (YY.MM.DD)
        print("DEBUG: Generating Investment Consensus Section (Moved after 2-Week Chart)...")
        today_str = datetime.now().strftime("%y.%m.%d")
        story.append(Paragraph(f"투자의견 컨센서스 <font size=10 color='#777'>(기준:{today_str})</font>", heading_style))

        if self.consensus:
            consensus_elements = create_consensus_detail_section(self.consensus)
            story.extend(consensus_elements)
            story.append(Paragraph("* 자료출처: www.wisereport.co.kr", ParagraphStyle('source', fontName='AppleGothic', fontSize=8, textColor=colors.grey)))
        else:
            story.append(Paragraph("컨센서스 데이터 없음", normal_style))

        story.append(Spacer(1, 0.5*cm))

        # --- Analyst Targets Table (Moved after 2-Week Chart) ---
        if self.analyst_targets:
            story.append(Paragraph("증권사 목표가", heading_style))
            target_data = [['일자', '목표주가', '이전대비', '투자의견', '증권사', '리포트']]
            
            for idx, target in enumerate(self.analyst_targets):
                d_str = target['report_date']
                if len(d_str) == 8:
                    date_fmt = f"{d_str[2:4]}.{d_str[4:6]}.{d_str[6:8]}"
                else:
                    date_fmt = d_str

                opinion_map = {'Buy': '매수', 'Hold': '중립', 'Sell': '매도', 'buy': '매수', 'hold': '중립', 'sell': '매도'}
                opinion_kr = opinion_map.get(target.get('opinion', 'Buy'), '매수')

                title = target.get('title', '')
                if len(title) > 25:
                    title = title[:25] + '...'

                current_price = target['target_price']
                price_change_str = '0'

                if idx + 1 < len(self.analyst_targets):
                    next_target = self.analyst_targets[idx + 1]
                    next_price = next_target['target_price']
                    price_diff = current_price - next_price

                    if price_diff > 0:
                        price_change_str = f"▲ {price_diff:,}"
                    elif price_diff < 0:
                        price_change_str = f"▼ {abs(price_diff):,}"
                    else:
                        price_change_str = "0"
                else:
                    price_change_str = "-"

                op_bar = create_mini_opinion_bar(opinion_kr)
                op_color = colors.HexColor('#F44336')
                if '매수' in opinion_kr: op_color = colors.HexColor('#F44336')
                elif '매도' in opinion_kr: op_color = colors.HexColor('#1565C0')
                elif '중립' in opinion_kr: op_color = colors.HexColor('#4CAF50')
                
                op_cell_data = [[op_bar, Paragraph(f"<font color='white'><b>{opinion_kr}</b></font>", ParagraphStyle('op', fontName='AppleGothic', fontSize=8, alignment=1))]]
                op_cell = Table(op_cell_data, colWidths=[2.2*cm, 1.0*cm])
                op_cell.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('BACKGROUND', (1, 0), (1, 0), op_color),
                    ('LEFTPADDING', (0, 0), (-1, -1), 1),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 1),
                    ('TOPPADDING', (0, 0), (-1, -1), 1),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                ]))

                target_data.append([
                    date_fmt,
                    f"{target['target_price']:,}",
                    price_change_str,
                    op_cell,
                    target['brokerage'],
                    title
                ])
            
            target_table = Table(target_data, colWidths=[2.0*cm, 2.0*cm, 1.5*cm, 3.5*cm, 1.5*cm, 6.0*cm])
            target_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ]))
            
            for r_idx, row in enumerate(target_data[1:], 1):
                change_str = row[2]
                if '▲' in change_str:
                    target_table.setStyle(TableStyle([('TEXTCOLOR', (2, r_idx), (2, r_idx), colors.red)]))
                elif '▼' in change_str:
                    target_table.setStyle(TableStyle([('TEXTCOLOR', (2, r_idx), (2, r_idx), colors.blue)]))
                else:
                    target_table.setStyle(TableStyle([('TEXTCOLOR', (2, r_idx), (2, r_idx), colors.black)]))

            story.append(target_table)
            story.append(Spacer(1, 1*cm))

        # Holding Status (New Section)
        if hasattr(self, 'holding') and self.holding:
            story.append(PageBreak())
            story.append(Paragraph("💼 Holding Status (보유 현황)", heading_style))
            
            # Determine current price priority:
            # 1. Real-time Tick (min_ticks[0])
            # 2. Yesterday's Close (ohlcv[0])
            # 3. Fundamentals Current Price
            
            current_p = 0
            
            if hasattr(self, 'min_ticks') and self.min_ticks:
                current_p = self.min_ticks[0]['price']
            elif hasattr(self, 'ohlcv') and self.ohlcv:
                # ohlcv is sorted by date DESC, so [0] is the latest (yesterday or today close)
                current_p = self.ohlcv[0]['close']
            else:
                current_p = self.fundamentals.get('current_price', 0) or 0
            
            holding_table = create_holding_status_table(self.holding, current_p)
            if holding_table:
                story.append(holding_table)
                story.append(Spacer(1, 0.2*cm))

            # Claude Code 선정 정보 (recommendation_history 기반)
            if hasattr(self, 'recommendation') and self.recommendation:
                story.append(Spacer(1, 0.3*cm))
                story.append(Paragraph("🤖 Claude Code 선정 정보", heading_style))

                rec = self.recommendation
                rec_date = rec['recommendation_date'].strftime('%Y-%m-%d') if rec['recommendation_date'] else '-'
                rec_price = f"{int(rec['recommended_price']):,}원" if rec['recommended_price'] else '-'
                rec_score = f"{float(rec['total_score']):.1f}점" if rec['total_score'] else '-'
                rec_note = rec['note'] if rec['note'] else '-'

                # 선정 정보 테이블
                rec_data = [
                    ['선정일', rec_date],
                    ['매수가', rec_price],
                    ['AI 점수', rec_score],
                    ['AI 등급', rec_note],
                ]

                rec_table = Table(rec_data, colWidths=[4*cm, 12*cm])
                rec_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E3F2FD')),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1565C0')),
                    ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                    ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BBDEFB')),
                ]))
                story.append(rec_table)
                story.append(Spacer(1, 0.2*cm))

                # 추천 이유 (gemini_reasoning)
                if rec['gemini_reasoning']:
                    story.append(Paragraph("📝 추천 이유 (AI 분석)", ParagraphStyle(
                        'ReasoningTitle', fontName='AppleGothic', fontSize=10,
                        textColor=colors.HexColor('#1565C0'), spaceBefore=5, spaceAfter=5
                    )))

                    reasoning_text = rec['gemini_reasoning'].replace('\n', '<br/>')
                    story.append(Paragraph(reasoning_text, ParagraphStyle(
                        'ReasoningBody', fontName='AppleGothic', fontSize=9,
                        textColor=colors.HexColor('#424242'), leading=14,
                        leftIndent=10, rightIndent=10, spaceBefore=5, spaceAfter=10,
                        backColor=colors.HexColor('#FAFAFA'), borderPadding=8
                    )))
                    story.append(Spacer(1, 0.3*cm))

        # Real-time Ticks (New Section - mimicking KEPCO dashboard)
        if hasattr(self, 'min_ticks') and self.min_ticks:
            story.append(Paragraph("⏱️ Real-time Ticks", heading_style))
            
            # Use the new dashboard component
            realtime_dashboard_elements = create_stock_realtime_dashboard(self.stock_info, self.holding, self.min_ticks)
            story.extend(realtime_dashboard_elements)
            story.append(Spacer(1, 0.2*cm))

        # Page Break
        story.append(PageBreak())

        # 4. Price Chart
        story.append(Paragraph("📈 Price Trend (주가 추이)", heading_style))
        if 'price_trend' in self.chart_buffers:
            story.append(Image(self.chart_buffers['price_trend'], width=16*cm, height=9*cm))
        story.append(Spacer(1, 0.5*cm))

        # 5. Financial Performance
        story.append(Paragraph("💰 Financial Performance (재무 실적)", heading_style))
        if 'financial_performance' in self.chart_buffers:
            story.append(Image(self.chart_buffers['financial_performance'], width=16*cm, height=8*cm))
        story.append(Spacer(1, 0.3*cm))

        # Financial Table
        fin_data = [['Year', 'Revenue(억)', 'Op. Profit(억)', 'Net Profit(억)', 'OPM(%)']]
        for row in reversed(self.financials_yearly):
            revenue = row['revenue']/100000000
            op_profit = row['operating_profit']/100000000
            net_profit = row['net_profit']/100000000
            op_margin = (op_profit / revenue * 100) if revenue > 0 else 0
            fin_data.append([
                str(row['fiscal_year']),
                f"{revenue:,.0f}",
                f"{op_profit:,.0f}",
                f"{net_profit:,.0f}",
                f"{op_margin:.1f}%"
            ])

        fin_table = Table(fin_data, colWidths=[3*cm, 3.5*cm, 3.5*cm, 3.5*cm, 3*cm])
        fin_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#455A64')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')])
        ]))
        story.append(fin_table)
        story.append(PageBreak())

        # 6. Investor Trends
        story.append(Paragraph("👥 Investor Trends (수급 동향)", heading_style))
        if 'investor_trends' in self.chart_buffers:
            story.append(Image(self.chart_buffers['investor_trends'], width=16*cm, height=8*cm))
        story.append(Spacer(1, 0.3*cm))

        # Add 1-Year Cumulative Chart
        if 'investor_trends_year' in self.chart_buffers:
            story.append(Image(self.chart_buffers['investor_trends_year'], width=16*cm, height=8*cm))
            story.append(Spacer(1, 0.3*cm))

        # 30-day summary
        if self.investor_trends:
            foreign_sum = sum(row['foreign'] for row in self.investor_trends)
            institutional_sum = sum(row['institutional'] for row in self.investor_trends)
            story.append(Paragraph(
                f"최근 30일 순매수: 외국인 {foreign_sum:+,}주 | 기관 {institutional_sum:+,}주",
                ParagraphStyle('summary', parent=normal_style, fontSize=9, textColor=colors.HexColor('#555555'))
            ))
        story.append(Spacer(1, 0.3*cm))

        # PageBreak before Peer Comparison to keep it together
        story.append(PageBreak())

        # Peer Comparison
        story.append(Paragraph("동종업계 비교", heading_style))
        if 'peer_comparison' in self.chart_buffers:
            story.append(Image(self.chart_buffers['peer_comparison'], width=16*cm, height=8*cm))
        story.append(Spacer(1, 0.2*cm))

        # Peer Table
        peer_data = [['기업명', 'PER', 'PBR', 'ROE(%)']]
        peer_data.append([
            self.stock_info['stock_name'],
            f"{float(self.fundamentals['per']):.2f}" if self.fundamentals.get('per') else '-',
            f"{float(self.fundamentals['pbr']):.2f}" if self.fundamentals.get('pbr') else '-',
            f"{float(self.fundamentals['roe']):.2f}" if self.fundamentals.get('roe') else '-'
        ])
        for peer in self.peers:
            peer_data.append([
                peer['peer_name'],
                f"{float(peer['per']):.2f}" if peer['per'] else '-',
                f"{float(peer['pbr']):.2f}" if peer['pbr'] else '-',
                f"{float(peer['roe']):.2f}" if peer['roe'] else '-'
            ])

        peer_table = Table(peer_data, colWidths=[6*cm, 3.5*cm, 3.5*cm, 3.5*cm])
        peer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e3f2fd')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 2), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
        ]))
        story.append(peer_table)
        story.append(Spacer(1, 0.5*cm))





        # News Section with Summary and Sentiment
        story.append(PageBreak())
        story.append(Paragraph(f"최근 뉴스 분석", title_style))
        story.append(Spacer(1, 0.5*cm))

        if self.news and len(self.news) > 0:
            for idx, news_item in enumerate(self.news[:10], 1):
                # News card for each item
                sentiment = news_item.get('sentiment', '중립')
                title = news_item.get('title', '')
                summary = news_item.get('summary', title)
                date_str = news_item.get('collected_at', '')[:16]  # YYYY-MM-DD HH:MM
                source = news_item.get('source', '알 수 없음')
                url = news_item.get('url', '')

                # Sentiment color
                if sentiment == '호재':
                    sentiment_color = colors.HexColor('#dc3545')  # Red
                    sentiment_bg = colors.HexColor('#f8d7da')
                elif sentiment == '악재':
                    sentiment_color = colors.HexColor('#0056b3')  # Blue
                    sentiment_bg = colors.HexColor('#cce5ff')
                else:
                    sentiment_color = colors.HexColor('#6c757d')  # Grey
                    sentiment_bg = colors.HexColor('#e9ecef')

                # News header (date, source, sentiment)
                header_style = ParagraphStyle(
                    'newsheader',
                    parent=normal_style,
                    fontSize=8,
                    textColor=colors.grey
                )

                sentiment_style = ParagraphStyle(
                    'sentiment',
                    parent=normal_style,
                    fontSize=9,
                    textColor=sentiment_color,
                    fontName='AppleGothic',
                    alignment=TA_CENTER
                )

                title_style_news = ParagraphStyle(
                    'newstitle',
                    parent=normal_style,
                    fontSize=9,
                    fontName='AppleGothic',
                    leading=12
                )

                summary_style = ParagraphStyle(
                    'summary',
                    parent=normal_style,
                    fontSize=8,
                    fontName='AppleGothic',
                    leading=11,
                    textColor=colors.HexColor('#495057')
                )

                # Create news card table
                news_card_data = [
                    [Paragraph(f"<b>{idx}. {title}</b>", title_style_news)],
                    [Paragraph(f"일시: {date_str} | 출처: {source}", header_style)],
                    [Paragraph(f"<b>감성:</b> {sentiment}", sentiment_style)],
                    [Paragraph(f"<b>요약:</b><br/>{summary}", summary_style)],
                    [Paragraph(f"<link href=\"{url}\">원문 보기 &gt;&gt;</link>", header_style)]
                ]

                news_card = Table(news_card_data, colWidths=[16.5*cm])
                news_card.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
                    ('BACKGROUND', (0, 2), (-1, 2), sentiment_bg),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6'))
                ]))

                story.append(news_card)
                story.append(Spacer(1, 0.3*cm))
        else:
            story.append(Paragraph("최근 뉴스 데이터가 없습니다.", normal_style))

        story.append(Spacer(1, 0.5*cm))









        # Footer
        footer_text = f"본 리포트는 AI 기반 자동 생성 리포트입니다. | 생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        story.append(Paragraph(footer_text, ParagraphStyle('footer', parent=normal_style, fontSize=8, textColor=colors.grey, alignment=TA_CENTER)))

        # Build PDF
        doc.build(story, onFirstPage=self.draw_header, onLaterPages=self.draw_header)
        print(f"   ✅ PDF saved: {output_path}")
        return output_path


import argparse
import os

# Request stock file path
REQUEST_STOCK_FILE = '/Users/wonny/Dev/joungwon.stocks/reports/request_stock/request_stock.md'


def get_requested_stocks():
    """request_stock.md에서 요청 종목명 읽기"""
    if not os.path.exists(REQUEST_STOCK_FILE):
        return []
    with open(REQUEST_STOCK_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    stocks = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            stocks.append(line)
    return stocks


async def get_stock_code_by_name(name):
    """종목명으로 종목코드 조회"""
    result = await db.fetchrow('''
        SELECT stock_code, stock_name FROM stocks
        WHERE stock_name = $1
    ''', name)
    return result


async def main():
    parser = argparse.ArgumentParser(description='Generate PDF Report')
    parser.add_argument('stock_code', nargs='?', help='Target stock code (optional)')
    args = parser.parse_args()

    await db.connect()
    try:
        if args.stock_code:
            stock_codes = [args.stock_code]
            print(f"\n{'='*60}")
            print(f"🚀 Generating PDF Report for Single Stock: {args.stock_code}")
            print(f"{'='*60}\n")
        else:
            # Get all holding stocks
            rows = await db.fetch("SELECT stock_code, stock_name FROM stock_assets ORDER BY stock_name")
            holding_codes = [r['stock_code'] for r in rows]
            
            # Get requested stocks from request_stock.md
            requested_names = get_requested_stocks()
            requested_codes = []
            for name in requested_names:
                result = await get_stock_code_by_name(name)
                if result:
                    code = result['stock_code']
                    # 보유종목에 없는 경우만 추가 (중복 방지)
                    if code not in holding_codes:
                        requested_codes.append(code)
                        print(f"📌 요청종목 추가: {name} ({code})")
                else:
                    print(f"⚠️ 종목명 '{name}'을(를) 찾을 수 없습니다.")
            
            stock_codes = holding_codes + requested_codes
            
            print(f"\n{'='*60}")
            print(f"🚀 Generating PDF Reports for {len(holding_codes)} Holdings + {len(requested_codes)} Requested")
            print(f"{'='*60}\n")

        for stock_code in stock_codes:
            print(f"🔹 Processing {stock_code}...")
            try:
                generator = PDFReportGenerator(stock_code)
                await generator.fetch_all_data()
                generator.generate_charts()
                pdf_path = generator.generate_pdf()
                print(f"   ✨ Generated: {pdf_path.name}")
            except Exception as e:
                print(f"   ❌ Failed to generate report for {stock_code}: {e}")
                import traceback
                traceback.print_exc()
            print(f"{'-'*60}")

    finally:
        await db.disconnect()
        print(f"\n{'='*60}")
        print(f"✅ All reports generation task finished!")
        print(f"{'='*60}\n")


if __name__ == '__main__':
    asyncio.run(main())