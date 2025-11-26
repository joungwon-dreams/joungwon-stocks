"""
Professional Stock Analysis PDF Report Generator
Based on 'Sample.pdf' style (Generative AI Equity Research)

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
        self.output_dir = Path('/Users/wonny/Dev/joungwon.stocks/reports')
        self.output_dir.mkdir(exist_ok=True)
        self.chart_dir = self.output_dir / 'charts'
        self.chart_dir.mkdir(exist_ok=True)

    async def fetch_all_data(self):
        """Fetch all required data from database"""
        print(f"📊 Fetching data for {self.stock_code}...")

        # Basic info
        query = "SELECT s.stock_code, s.stock_name, s.sector, s.market FROM stocks s WHERE s.stock_code = $1"
        self.stock_info = await db.fetchrow(query, self.stock_code)

        # Fundamentals
        query = "SELECT * FROM stock_fundamentals WHERE stock_code = $1"
        self.fundamentals = await db.fetchrow(query, self.stock_code)

        # Consensus - from investment_consensus table (Naver Finance)
        from scripts.naver.consensus_scraper import NaverConsensusScraper
        self.consensus = await NaverConsensusScraper.get_from_db(self.stock_code)

        # Financial statements (yearly)
        query = """
            SELECT fiscal_year, revenue, operating_profit, net_profit
            FROM stock_financials
            WHERE stock_code = $1 AND period_type = 'yearly'
            ORDER BY fiscal_year DESC LIMIT 5
        """
        self.financials_yearly = await db.fetch(query, self.stock_code)

        # OHLCV (last 120 days) - Reverted to 120
        query = """
            SELECT date, close, volume
            FROM daily_ohlcv
            WHERE stock_code = $1
            ORDER BY date DESC LIMIT 120
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

        # Convert WISEfn format to analyst_targets format
        self.analyst_targets = []
        for report in wisefn_reports:
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

        # Real-time Min Ticks (New)
        query = """
            SELECT timestamp, price, volume 
            FROM min_ticks 
            WHERE stock_code = $1 
            ORDER BY timestamp DESC 
            LIMIT 60
        """
        self.min_ticks = await db.fetch(query, self.stock_code)

        print(f"   ✅ Data fetched successfully")
        print(f"   DEBUG: Consensus keys: {self.consensus.keys() if self.consensus else 'None'}")
        print(f"   DEBUG: Analyst Targets count: {len(self.analyst_targets) if self.analyst_targets else 0}")

    def generate_charts(self):
        """Generate all charts"""
        print(f"📈 Generating charts...")

        if self.ohlcv:
            self._generate_price_chart()
            self._generate_mini_2week_chart() 
        
        if hasattr(self, 'min_ticks') and self.min_ticks:
            output_path = self.chart_dir / 'realtime_tick_chart.png'
            generate_realtime_tick_chart(self.min_ticks, output_path)

        if self.financials_yearly:
            self._generate_financial_chart()
        if self.investor_trends:
            self._generate_investor_chart()
            self._generate_investor_year_chart()
        if self.peers:
            self._generate_peer_chart()

        print(f"   ✅ Charts generated")

    def _generate_price_chart(self):
        dates = [row['date'] for row in reversed(self.ohlcv)]
        prices = [row['close'] for row in reversed(self.ohlcv)]
        volumes = [row['volume'] for row in reversed(self.ohlcv)]

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
        plt.savefig(self.chart_dir / 'price_trend.png', dpi=100, bbox_inches='tight')
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
            ax.axhline(y=avg_buy_price, color='purple', linestyle='-', linewidth=2, alpha=0.8, label='Avg Buy Price')
            # Increased font size for avg price
            ax.text(dates[0], avg_buy_price, f"평단가: {int(avg_buy_price):,}", color='purple', va='bottom', ha='left', fontsize=10, fontweight='bold')

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
        plt.savefig(self.chart_dir / 'mini_2week_chart.png', dpi=100, bbox_inches='tight')
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
        plt.savefig(self.chart_dir / 'financial_performance.png', dpi=100, bbox_inches='tight')
        plt.close()

    def _generate_investor_chart(self):
        # Use first 30 items (since list is sorted DESC, first 30 are latest)
        data_30 = self.investor_trends[:30]
        if not data_30: return

        dates = [row['trade_date'] for row in reversed(data_30)]
        foreign = [row['foreign']/1000 for row in reversed(data_30)]
        institutional = [row['institutional']/1000 for row in reversed(data_30)]

        # Prepare Price Data
        prices = []
        for d in dates:
            # Find matching price in self.ohlcv
            price = next((row['close'] for row in self.ohlcv if row['date'] == d), None)
            if price is None and prices: price = prices[-1] # Fallback to prev
            prices.append(float(price) if price else 0.0)

        # Subplots: 2 rows, share X axis
        import matplotlib.ticker as ticker
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, height_ratios=[1, 1])
        
        # Top: Price Chart
        ax1.plot(dates, prices, color='#455A64', linewidth=2, label='주가')
        ax1.set_ylabel('주가 (원)', fontsize=9)
        ax1.legend(loc='upper left', fontsize=9)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
        
        # Bottom: Investor Trends
        ax2.plot(dates, foreign, marker='o', linewidth=2, label='외국인', color='#E64A19', markersize=4)
        ax2.plot(dates, institutional, marker='s', linewidth=2, label='기관', color='#512DA8', markersize=4)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.3)
        ax2.set_ylabel('순매수량 (천주)', fontsize=9)
        ax2.legend(loc='upper left', fontsize=9)
        ax2.grid(True, alpha=0.3, linestyle='--')

        ax1.set_title('주가 및 투자자별 순매수 추이 (30일)', fontsize=14, fontweight='bold')
        
        ax2.xaxis.set_major_locator(ticker.MaxNLocator(6))
        ax2.tick_params(axis='x', labelsize=8, rotation=0)

        plt.tight_layout()
        plt.savefig(self.chart_dir / 'investor_trends.png', dpi=100, bbox_inches='tight')
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

        # Prepare Price Data
        prices = []
        for d in dates:
            price = next((row['close'] for row in self.ohlcv if row['date'] == d), None)
            if price is None and prices: price = prices[-1]
            prices.append(float(price) if price else 0.0)

        # Subplots
        import matplotlib.ticker as ticker
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, height_ratios=[1, 1])
        
        # Top: Price
        ax1.plot(dates, prices, color='#455A64', linewidth=2, label='주가')
        ax1.set_ylabel('주가 (원)', fontsize=9)
        ax1.legend(loc='upper left', fontsize=9)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
        
        # Bottom: Cumulative Trends
        ax2.plot(dates, foreign_cum, linewidth=2, label='외국인 누적', color='#E64A19')
        ax2.plot(dates, institutional_cum, linewidth=2, label='기관 누적', color='#512DA8')
        # ax2.plot(dates, individual_cum, linewidth=1, label='개인 누적', color='#388E3C', alpha=0.6, linestyle='--') 

        ax1.set_title('주가 및 투자자별 누적 순매수 추이 (1년)', fontsize=14, fontweight='bold')
        ax2.set_ylabel('누적 순매수량 (천주)', fontsize=9)
        ax2.legend(loc='upper left', fontsize=9)
        ax2.grid(True, alpha=0.3, linestyle='--')
        
        ax2.xaxis.set_major_locator(ticker.MaxNLocator(8))
        ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
        ax2.tick_params(axis='x', labelsize=8, rotation=0)

        plt.tight_layout()
        plt.savefig(self.chart_dir / 'investor_trends_year.png', dpi=100, bbox_inches='tight')
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
            
        output_path = self.chart_dir / 'peer_comparison.png'
        generate_peer_comparison_chart(peers_data, output_path)

    def draw_header(self, canvas, doc):
        """Draw header on every page"""
        canvas.saveState()
        
        # Settings
        stock_title = f"{self.stock_info['stock_name']} ({self.stock_code})"
        now = datetime.now()
        date_str = now.strftime("%Y/%m/%d")
        time_str = now.strftime("%H:%M:%S")
        page_num = doc.page
        
        # Draw Left: Stock Title
        canvas.setFont('AppleGothic', 20)
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
        if (self.chart_dir / 'mini_2week_chart.png').exists():
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
                story.append(Image(str(self.chart_dir / 'mini_2week_chart.png'), width=14*cm, height=5.5*cm))
        
        # Double the spacer
        story.append(Spacer(1, 1.0*cm))



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
        if (self.chart_dir / 'price_trend.png').exists():
            story.append(Image(str(self.chart_dir / 'price_trend.png'), width=16*cm, height=9*cm))
        story.append(Spacer(1, 0.5*cm))

        # 5. Financial Performance
        story.append(Paragraph("💰 Financial Performance (재무 실적)", heading_style))
        if (self.chart_dir / 'financial_performance.png').exists():
            story.append(Image(str(self.chart_dir / 'financial_performance.png'), width=16*cm, height=8*cm))
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
        if (self.chart_dir / 'investor_trends.png').exists():
            story.append(Image(str(self.chart_dir / 'investor_trends.png'), width=16*cm, height=8*cm))
        story.append(Spacer(1, 0.3*cm))

        # Add 1-Year Cumulative Chart
        if (self.chart_dir / 'investor_trends_year.png').exists():
            story.append(Image(str(self.chart_dir / 'investor_trends_year.png'), width=16*cm, height=8*cm))
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
        if (self.chart_dir / 'peer_comparison.png').exists():
            story.append(Image(str(self.chart_dir / 'peer_comparison.png'), width=16*cm, height=8*cm))
        story.append(Spacer(1, 0.2*cm))

        # Peer Table
        peer_data = [['기업명', 'PER', 'PBR', 'ROE(%)']]
        peer_data.append([
            self.stock_info['stock_name'],
            f"{float(self.fundamentals['per']):.2f}",
            f"{float(self.fundamentals['pbr']):.2f}",
            f"{float(self.fundamentals['roe']):.2f}"
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
            stock_codes = [r['stock_code'] for r in rows]
            
            print(f"\n{'='*60}")
            print(f"🚀 Generating PDF Reports for {len(stock_codes)} Holdings")
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