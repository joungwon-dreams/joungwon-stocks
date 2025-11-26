"""
Professional Stock Analysis Report Generator
Similar to securities firm reports with charts and analysis
"""
import asyncio
import sys
from datetime import datetime, date
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib import rcParams
import numpy as np

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db

# Set Korean font for matplotlib
rcParams['font.family'] = 'AppleGothic'
rcParams['axes.unicode_minus'] = False

class ProfessionalReportGenerator:
    def __init__(self, stock_code: str):
        self.stock_code = stock_code
        self.report_date = datetime.now().strftime('%Y년 %m월 %d일')
        self.output_dir = Path('/Users/wonny/Dev/joungwon.stocks/reports')
        self.output_dir.mkdir(exist_ok=True)

    async def fetch_all_data(self):
        """Fetch all required data from database"""
        print(f"📊 Fetching data for {self.stock_code}...")

        # 1. Basic info
        query = """
            SELECT s.stock_code, s.stock_name, s.sector, s.market
            FROM stocks s WHERE s.stock_code = $1
        """
        self.stock_info = await db.fetchrow(query, self.stock_code)

        # 2. Fundamentals
        query = """
            SELECT * FROM stock_fundamentals WHERE stock_code = $1
        """
        self.fundamentals = await db.fetchrow(query, self.stock_code)

        # 3. Consensus
        query = """
            SELECT * FROM stock_consensus WHERE stock_code = $1
        """
        self.consensus = await db.fetchrow(query, self.stock_code)

        # 4. Financial statements (yearly)
        query = """
            SELECT fiscal_year, revenue, operating_profit, net_profit
            FROM stock_financials
            WHERE stock_code = $1 AND period_type = 'yearly'
            ORDER BY fiscal_year DESC
            LIMIT 5
        """
        self.financials_yearly = await db.fetch(query, self.stock_code)

        # 5. Financial statements (quarterly)
        query = """
            SELECT fiscal_year, fiscal_quarter, revenue, operating_profit, net_profit
            FROM stock_financials
            WHERE stock_code = $1 AND period_type = 'quarterly'
            ORDER BY fiscal_year DESC, fiscal_quarter DESC
            LIMIT 8
        """
        self.financials_quarterly = await db.fetch(query, self.stock_code)

        # 6. OHLCV (last 120 days)
        query = """
            SELECT date, close, volume
            FROM daily_ohlcv
            WHERE stock_code = $1
            ORDER BY date DESC
            LIMIT 120
        """
        self.ohlcv = await db.fetch(query, self.stock_code)

        # 7. Investor trends (last 30 days)
        query = """
            SELECT trade_date, individual, "foreign", institutional
            FROM investor_trends
            WHERE stock_code = $1
            ORDER BY trade_date DESC
            LIMIT 30
        """
        self.investor_trends = await db.fetch(query, self.stock_code)

        # 8. Peers
        query = """
            SELECT p.peer_code, p.peer_name,
                   f.per, f.pbr, f.roe
            FROM stock_peers p
            LEFT JOIN stock_fundamentals f ON p.peer_code = f.stock_code
            WHERE p.stock_code = $1
            LIMIT 5
        """
        self.peers = await db.fetch(query, self.stock_code)

        print(f"   ✅ Data fetched successfully")

    def generate_charts(self):
        """Generate all charts for the report"""
        print(f"📈 Generating charts...")

        chart_dir = self.output_dir / 'charts'
        chart_dir.mkdir(exist_ok=True)

        # Chart 1: Price trend (120 days)
        if self.ohlcv:
            self._generate_price_chart(chart_dir)

        # Chart 2: Financial performance (yearly)
        if self.financials_yearly:
            self._generate_financial_chart(chart_dir)

        # Chart 3: Investor trends
        if self.investor_trends:
            self._generate_investor_chart(chart_dir)

        # Chart 4: Valuation comparison with peers
        if self.peers:
            self._generate_peer_comparison_chart(chart_dir)

        print(f"   ✅ Charts generated")

    def _generate_price_chart(self, chart_dir):
        """Price and volume chart"""
        dates = [row['date'] for row in reversed(self.ohlcv)]
        prices = [row['close'] for row in reversed(self.ohlcv)]
        volumes = [row['volume'] for row in reversed(self.ohlcv)]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[3, 1])

        # Price chart
        ax1.plot(dates, prices, linewidth=2, color='#1f77b4')
        ax1.fill_between(dates, prices, alpha=0.3, color='#1f77b4')
        ax1.set_title(f'{self.stock_info["stock_name"]} 주가 추이 (120일)', fontsize=14, fontweight='bold')
        ax1.set_ylabel('주가 (원)', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='x', rotation=45)

        # Volume chart
        ax2.bar(dates, volumes, color='#2ca02c', alpha=0.6)
        ax2.set_ylabel('거래량', fontsize=12)
        ax2.set_xlabel('날짜', fontsize=12)
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(chart_dir / 'price_trend.png', dpi=150, bbox_inches='tight')
        plt.close()

    def _generate_financial_chart(self, chart_dir):
        """Financial performance chart (yearly)"""
        years = [str(row['fiscal_year']) for row in reversed(self.financials_yearly)]
        revenue = [row['revenue']/100000000 for row in reversed(self.financials_yearly)]  # 억원
        op_profit = [row['operating_profit']/100000000 for row in reversed(self.financials_yearly)]
        net_profit = [row['net_profit']/100000000 for row in reversed(self.financials_yearly)]

        x = np.arange(len(years))
        width = 0.25

        fig, ax = plt.subplots(figsize=(12, 6))

        ax.bar(x - width, revenue, width, label='매출액', color='#1f77b4')
        ax.bar(x, op_profit, width, label='영업이익', color='#ff7f0e')
        ax.bar(x + width, net_profit, width, label='순이익', color='#2ca02c')

        ax.set_title('연간 재무 실적 추이', fontsize=14, fontweight='bold')
        ax.set_ylabel('금액 (억원)', fontsize=12)
        ax.set_xlabel('연도', fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(years)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        plt.savefig(chart_dir / 'financial_performance.png', dpi=150, bbox_inches='tight')
        plt.close()

    def _generate_investor_chart(self, chart_dir):
        """Investor trading trends chart"""
        dates = [row['trade_date'] for row in reversed(self.investor_trends)]
        foreign = [row['foreign']/1000 for row in reversed(self.investor_trends)]  # 천주
        institutional = [row['institutional']/1000 for row in reversed(self.investor_trends)]

        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(dates, foreign, marker='o', linewidth=2, label='외국인', color='#d62728')
        ax.plot(dates, institutional, marker='s', linewidth=2, label='기관', color='#9467bd')
        ax.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)

        ax.set_title('투자자별 순매수 추이 (30일)', fontsize=14, fontweight='bold')
        ax.set_ylabel('순매수량 (천주)', fontsize=12)
        ax.set_xlabel('날짜', fontsize=12)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='x', rotation=45)

        plt.tight_layout()
        plt.savefig(chart_dir / 'investor_trends.png', dpi=150, bbox_inches='tight')
        plt.close()

    def _generate_peer_comparison_chart(self, chart_dir):
        """Peer comparison chart"""
        companies = [self.stock_info['stock_name']]
        pers = [float(self.fundamentals['per']) if self.fundamentals['per'] else 0]
        pbrs = [float(self.fundamentals['pbr']) if self.fundamentals['pbr'] else 0]
        roes = [float(self.fundamentals['roe']) if self.fundamentals['roe'] else 0]

        for peer in self.peers[:4]:  # Top 4 peers
            companies.append(peer['peer_name'])
            pers.append(float(peer['per']) if peer['per'] else 0)
            pbrs.append(float(peer['pbr']) if peer['pbr'] else 0)
            roes.append(float(peer['roe']) if peer['roe'] else 0)

        x = np.arange(len(companies))
        width = 0.25

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # PER & PBR
        ax1.bar(x - width/2, pers, width, label='PER', color='#1f77b4')
        ax1.bar(x + width/2, pbrs, width, label='PBR', color='#ff7f0e')
        ax1.set_title('밸류에이션 비교 (PER, PBR)', fontsize=12, fontweight='bold')
        ax1.set_ylabel('배수', fontsize=11)
        ax1.set_xticks(x)
        ax1.set_xticklabels(companies, rotation=45, ha='right')
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3, axis='y')

        # ROE
        ax2.bar(x, roes, color='#2ca02c')
        ax2.set_title('수익성 비교 (ROE)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('ROE (%)', fontsize=11)
        ax2.set_xticks(x)
        ax2.set_xticklabels(companies, rotation=45, ha='right')
        ax2.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        plt.savefig(chart_dir / 'peer_comparison.png', dpi=150, bbox_inches='tight')
        plt.close()

    def generate_html_report(self):
        """Generate HTML report"""
        print(f"📝 Generating HTML report...")

        # Calculate additional metrics
        upside = 0
        if self.consensus and self.fundamentals:
            target = self.consensus['target_price']
            current = self.fundamentals['current_price']
            if target and current:
                upside = ((target - current) / current) * 100

        html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.stock_info['stock_name']} 투자분석 리포트</title>
    <style>
        body {{
            font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .report-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .report-title {{
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .report-date {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .summary-box {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .summary-item {{
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .summary-label {{
            font-size: 13px;
            color: #666;
            margin-bottom: 8px;
        }}
        .summary-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .summary-value.positive {{
            color: #d32f2f;
        }}
        .summary-value.negative {{
            color: #1976d2;
        }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .section-title {{
            font-size: 20px;
            font-weight: bold;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px;
            text-align: right;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: bold;
            color: #555;
        }}
        th:first-child, td:first-child {{
            text-align: left;
        }}
        .chart-container {{
            margin: 20px 0;
            text-align: center;
        }}
        .chart-container img {{
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .investment-opinion {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 16px;
        }}
        .opinion-buy {{
            background-color: #d32f2f;
            color: white;
        }}
        .opinion-hold {{
            background-color: #ffa726;
            color: white;
        }}
        .opinion-sell {{
            background-color: #1976d2;
            color: white;
        }}
        .highlight-box {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        .footer {{
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 40px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <!-- Header -->
    <div class="report-header">
        <div class="report-title">{self.stock_info['stock_name']} ({self.stock_code})</div>
        <div class="report-date">투자분석 리포트 | {self.report_date}</div>
    </div>

    <!-- Executive Summary -->
    <div class="summary-box">
        <h2 style="margin-top:0;">투자 의견</h2>
        <div style="margin: 20px 0;">
            <span class="investment-opinion opinion-{'buy' if self.consensus and float(self.consensus.get('opinion', 0)) >= 4 else 'hold' if float(self.consensus.get('opinion', 0)) >= 3 else 'sell'}">
                {'매수' if self.consensus and float(self.consensus.get('opinion', 0)) >= 4 else '중립' if float(self.consensus.get('opinion', 0)) >= 3 else '매도'}
            </span>
        </div>

        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-label">현재가</div>
                <div class="summary-value">{self.fundamentals['current_price']:,}원</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">목표가</div>
                <div class="summary-value">{self.consensus['target_price']:,}원</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">상승여력</div>
                <div class="summary-value positive">{upside:+.1f}%</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">시가총액</div>
                <div class="summary-value">{self.fundamentals['market_cap']/1000000000000:.2f}조원</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">업종</div>
                <div class="summary-value" style="font-size:18px;">{self.fundamentals['sector'] or self.stock_info['sector'] or '-'}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">배당수익률</div>
                <div class="summary-value">{float(self.fundamentals['dividend_yield']):.2f}%</div>
            </div>
        </div>
    </div>

    <!-- Key Financials -->
    <div class="section">
        <div class="section-title">주요 재무지표</div>
        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-label">PER</div>
                <div class="summary-value">{float(self.fundamentals['per']):.2f}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">PBR</div>
                <div class="summary-value">{float(self.fundamentals['pbr']):.2f}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">ROE</div>
                <div class="summary-value">{float(self.fundamentals['roe']):.2f}%</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">외국인비중</div>
                <div class="summary-value">{float(self.fundamentals['foreign_ratio']):.2f}%</div>
            </div>
        </div>
    </div>

    <!-- Company Overview -->
    <div class="section">
        <div class="section-title">기업 개요</div>
        <p style="line-height: 1.8; color: #555;">
            {self.fundamentals['company_summary'] or '기업 개요 정보가 없습니다.'}
        </p>
    </div>

    <!-- Price Chart -->
    <div class="section">
        <div class="section-title">주가 추이</div>
        <div class="chart-container">
            <img src="charts/price_trend.png" alt="주가 추이">
        </div>
    </div>

    <!-- Financial Performance -->
    <div class="section">
        <div class="section-title">재무 실적</div>
        <div class="chart-container">
            <img src="charts/financial_performance.png" alt="재무 실적">
        </div>

        <table>
            <thead>
                <tr>
                    <th>연도</th>
                    <th>매출액 (억원)</th>
                    <th>영업이익 (억원)</th>
                    <th>순이익 (억원)</th>
                    <th>영업이익률 (%)</th>
                </tr>
            </thead>
            <tbody>
"""

        # Add yearly financial data
        for row in reversed(self.financials_yearly):
            revenue = row['revenue']/100000000
            op_profit = row['operating_profit']/100000000
            net_profit = row['net_profit']/100000000
            op_margin = (op_profit / revenue * 100) if revenue > 0 else 0

            html += f"""
                <tr>
                    <td>{row['fiscal_year']}</td>
                    <td>{revenue:,.0f}</td>
                    <td>{op_profit:,.0f}</td>
                    <td>{net_profit:,.0f}</td>
                    <td>{op_margin:.1f}</td>
                </tr>
"""

        html += """
            </tbody>
        </table>
    </div>

    <!-- Investor Trends -->
    <div class="section">
        <div class="section-title">투자자별 수급 동향</div>
        <div class="chart-container">
            <img src="charts/investor_trends.png" alt="투자자별 수급">
        </div>
        <div class="highlight-box">
            <strong>최근 30일 순매수:</strong><br>
"""

        # Calculate 30-day net buying
        if self.investor_trends:
            foreign_sum = sum(row['foreign'] for row in self.investor_trends)
            institutional_sum = sum(row['institutional'] for row in self.investor_trends)

            html += f"""
            외국인: {foreign_sum:+,}주 | 기관: {institutional_sum:+,}주
"""

        html += """
        </div>
    </div>

    <!-- Peer Comparison -->
    <div class="section">
        <div class="section-title">동종업계 비교</div>
        <div class="chart-container">
            <img src="charts/peer_comparison.png" alt="동종업계 비교">
        </div>

        <table>
            <thead>
                <tr>
                    <th>기업명</th>
                    <th>PER</th>
                    <th>PBR</th>
                    <th>ROE (%)</th>
                </tr>
            </thead>
            <tbody>
                <tr style="background-color: #e3f2fd;">
                    <td><strong>{self.stock_info['stock_name']}</strong></td>
                    <td><strong>{float(self.fundamentals['per']):.2f}</strong></td>
                    <td><strong>{float(self.fundamentals['pbr']):.2f}</strong></td>
                    <td><strong>{float(self.fundamentals['roe']):.2f}</strong></td>
                </tr>
"""

        for peer in self.peers:
            html += f"""
                <tr>
                    <td>{peer['peer_name']}</td>
                    <td>{float(peer['per']):.2f if peer['per'] else '-'}</td>
                    <td>{float(peer['pbr']):.2f if peer['pbr'] else '-'}</td>
                    <td>{float(peer['roe']):.2f if peer['roe'] else '-'}</td>
                </tr>
"""

        html += f"""
            </tbody>
        </table>
    </div>

    <!-- Analyst Consensus -->
    <div class="section">
        <div class="section-title">애널리스트 컨센서스</div>
        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-label">평균 투자의견</div>
                <div class="summary-value">{float(self.consensus['opinion']):.2f}</div>
                <div class="summary-label" style="margin-top: 5px;">(5점 만점)</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">참여 애널리스트</div>
                <div class="summary-value">{self.consensus['analyst_count']}명</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">매수</div>
                <div class="summary-value positive">{self.consensus['buy_count']}명</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">보유</div>
                <div class="summary-value">{self.consensus['hold_count']}명</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">매도</div>
                <div class="summary-value negative">{self.consensus['sell_count']}명</div>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <div class="footer">
        <p>본 리포트는 AI 기반 자동 생성 리포트로, 투자 결정에 참고용으로만 활용하시기 바랍니다.</p>
        <p>생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
"""

        output_path = self.output_dir / f'{self.stock_code}_{datetime.now().strftime("%Y%m%d")}_report.html'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"   ✅ Report saved: {output_path}")
        return output_path


async def main():
    stock_code = "015760"  # 한국전력

    print(f"\n{'='*60}")
    print(f"🚀 Generating Professional Stock Report")
    print(f"{'='*60}\n")

    await db.connect()

    try:
        generator = ProfessionalReportGenerator(stock_code)

        # Fetch data
        await generator.fetch_all_data()

        # Generate charts
        generator.generate_charts()

        # Generate HTML report
        report_path = generator.generate_html_report()

        print(f"\n{'='*60}")
        print(f"✨ Report generated successfully!")
        print(f"📄 Open: {report_path}")
        print(f"{'='*60}\n")

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
