"""
Report Generator
Generates PDF investment reports including charts and AI analysis.
"""
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# Font Configuration
FONT_PATH = '/Users/wonny/Dev/joungwon.stocks/fonts/NanumGothic.ttf'
FONT_BOLD_PATH = '/Users/wonny/Dev/joungwon.stocks/fonts/NanumGothicBold.ttf'

try:
    pdfmetrics.registerFont(TTFont('NanumGothic', FONT_PATH))
    pdfmetrics.registerFont(TTFont('NanumGothicBold', FONT_BOLD_PATH))
    FONT_NAME = 'NanumGothic'
    FONT_BOLD_NAME = 'NanumGothicBold'
except:
    FONT_NAME = 'Helvetica'
    FONT_BOLD_NAME = 'Helvetica-Bold'

# Matplotlib Font Config
try:
    font_prop = fm.FontProperties(fname=FONT_PATH)
    # Register font to matplotlib
    font_entry = fm.FontEntry(fname=FONT_PATH, name='NanumGothic')
    fm.fontManager.ttflist.append(font_entry)
    plt.rcParams['font.family'] = 'NanumGothic'
    plt.rcParams['axes.unicode_minus'] = False
except Exception as e:
    plt.rcParams['font.family'] = 'AppleGothic'
    plt.rcParams['axes.unicode_minus'] = False


class ReportGenerator:
    def __init__(self, output_dir: str, temp_dir: str = '/tmp/stock_charts'):
        self.output_dir = output_dir
        self.temp_dir = temp_dir
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

    def _create_chart(self, stock_code: str, stock_name: str, holding_data: dict, history_data: list = None, investor_data: list = None) -> str:
        """Create investment status, candle chart, and investor trends"""
        chart_path = os.path.join(self.temp_dir, f'{stock_code}_chart.png')
        
        if history_data and len(history_data) > 0:
            import mplfinance as mpf
            import pandas as pd
            import matplotlib.pyplot as plt
            
            # Prepare Price Data
            df = pd.DataFrame(history_data)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df = df.sort_index()
            
            # Prepare Investor Data (if available)
            addplot = []
            if investor_data and len(investor_data) > 0:
                df_inv = pd.DataFrame(investor_data)
                df_inv['date'] = pd.to_datetime(df_inv['date'])
                df_inv.set_index('date', inplace=True)
                df_inv = df_inv.sort_index()
                
                # Merge to ensure dates align (left join on price data)
                df_merged = df.join(df_inv, how='left').fillna(0)
                
                # Create additional plots for Foreign/Institutional
                # We'll use a separate panel for this
                ap_foreign = mpf.make_addplot(df_merged['foreign'].cumsum(), panel=2, color='red', secondary_y=False, title='Foreign (Cum)')
                ap_inst = mpf.make_addplot(df_merged['institutional'].cumsum(), panel=2, color='blue', secondary_y=False, title='Inst (Cum)')
                addplot = [ap_foreign, ap_inst]

            # Create custom style with Korean font support
            rc = {'font.family': 'NanumGothic', 'axes.unicode_minus': False}
            mc = mpf.make_marketcolors(up='r', down='b', inherit=True)
            s = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=True, rc=rc)
            
            # Plot Configuration
            # Panel 0: Price (Candle)
            # Panel 1: Volume
            # Panel 2: Investor Trends (if available)
            
            mpf.plot(df, type='candle', volume=True, style=s, 
                     addplot=addplot,
                     title=f'\n{stock_name} ({stock_code}) Price & Investor Trends',
                     savefig=dict(fname=chart_path, dpi=100, bbox_inches='tight'),
                     figratio=(12, 8) if addplot else (12, 6), 
                     figscale=1.2,
                     panel_ratios=(3, 1, 1) if addplot else (3, 1))
                     
        else:
            # Fallback to simple bar chart if no history
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

            # Bar Chart
            avg_price = holding_data.get('avg_buy_price', 0)
            profit_loss = holding_data.get('profit_loss', 0)
            categories = ['Avg Price', 'P/L']
            values = [avg_price, profit_loss]
            colors_bar = ['#3498db', '#27ae60' if profit_loss >= 0 else '#e74c3c']

            ax1.bar(categories, values, color=colors_bar, alpha=0.7)
            ax1.set_title(f'{stock_name} Status', fontsize=14, fontweight='bold')
            
            # Pie Chart
            total_cost = holding_data.get('total_cost', 0)
            if profit_loss >= 0:
                labels = ['Invested', 'Profit']
                sizes = [total_cost, profit_loss]
                colors_pie = ['#3498db', '#27ae60']
            else:
                labels = ['Value', 'Loss']
                sizes = [total_cost + profit_loss, -profit_loss]
                colors_pie = ['#3498db', '#e74c3c']

            if sum(sizes) > 0:
                ax2.pie(sizes, labels=labels, colors=colors_pie, autopct='%1.1f%%', startangle=90)
            ax2.set_title(f'P/L Rate ({holding_data.get("profit_rate", 0):.2f}%)', fontsize=14, fontweight='bold')

            plt.tight_layout()
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            
        return chart_path

    def generate_pdf(self, stock_code: str, holding_data: dict, collected_data: list, realtime_data: dict, ai_analysis: dict, history_data: list = None, investor_data: list = None) -> str:
        """Generate PDF report"""
        stock_name = holding_data['stock_name']
        pdf_file = os.path.join(self.output_dir, f'{stock_name}_{stock_code}.pdf')

        doc = SimpleDocTemplate(
            pdf_file,
            pagesize=A4,
            topMargin=2*cm, bottomMargin=2*cm,
            leftMargin=2*cm, rightMargin=2*cm
        )

        story = []
        styles = getSampleStyleSheet()

        # Styles
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontName=FONT_BOLD_NAME, fontSize=24, alignment=TA_CENTER, spaceAfter=20)
        section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontName=FONT_BOLD_NAME, fontSize=16, spaceBefore=15, spaceAfter=10, textColor=colors.HexColor('#2c3e50'))
        normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontName=FONT_NAME, fontSize=10, leading=16)
        ai_text_style = ParagraphStyle('AIText', parent=normal_style, fontSize=11, leading=18, alignment=TA_JUSTIFY)

        # Header
        story.append(Paragraph(f'{stock_name} AI 투자 분석 리포트', title_style))
        story.append(Paragraph(f'생성일시: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', ParagraphStyle('Date', parent=normal_style, alignment=TA_CENTER)))
        story.append(Spacer(1, 1*cm))

        # 1. AI Analysis Summary (Highlight)
        story.append(Paragraph('🤖 Gemini AI 종합 분석', section_style))
        
        # AI Summary Box
        ai_summary = ai_analysis.get('summary', '분석 내용 없음')
        story.append(Paragraph(ai_summary, ai_text_style))
        story.append(Spacer(1, 0.5*cm))

        # Sentiment & Recommendation Table
        sentiment = ai_analysis.get('sentiment', 'N/A')
        recommendation = ai_analysis.get('recommendation', 'N/A')
        
        ai_table_data = [
            ['시장 감성', '투자 제안'],
            [sentiment, recommendation]
        ]
        ai_table = Table(ai_table_data, colWidths=[8*cm, 8*cm])
        ai_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8e44ad')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), FONT_BOLD_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f4ecf7'))
        ]))
        story.append(ai_table)
        story.append(Spacer(1, 1*cm))

        # 2. Holding Status
        story.append(Paragraph('📊 보유 현황 및 차트', section_style))
        
        # Chart
        chart_path = self._create_chart(stock_code, stock_name, holding_data, history_data, investor_data)
        story.append(Image(chart_path, width=16*cm, height=6.5*cm))
        story.append(Spacer(1, 0.5*cm))

        # Holding Table
        profit_rate = holding_data['profit_rate']
        profit_color = colors.green if profit_rate >= 0 else colors.red
        
        holding_table_data = [
            ['보유수량', f"{holding_data['quantity']:,}주", '평가손익', f"{holding_data['profit_loss']:,}원"],
            ['평균매수가', f"{holding_data['avg_buy_price']:,}원", '수익률', f"{profit_rate:.2f}%"]
        ]
        holding_table = Table(holding_table_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
        holding_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
            ('BACKGROUND', (2, 0), (2, -1), colors.whitesmoke),
            ('TEXTCOLOR', (3, 1), (3, 1), profit_color), # Profit rate color
        ]))
        story.append(holding_table)
        story.append(Spacer(1, 1*cm))

        # 3. Market Data (Daum & Naver)
        story.append(Paragraph('📈 실시간 시세 및 컨센서스', section_style))
        
        daum = realtime_data.get('daum', {})
        naver = realtime_data.get('naver', {})
        quotes = daum.get('quotes', {})
        consensus = naver.get('consensus', {})
        
        price_table_data = [
            ['현재가', f"{quotes.get('tradePrice', 0):,}원", '목표주가', f"{consensus.get('target_price', 'N/A')}"],
            ['등락률', f"{quotes.get('changeRate', 0):.2f}%", '투자의견', f"{consensus.get('opinion', 'N/A')}"],
            ['거래량', f"{quotes.get('accTradeVolume', 0):,}주", '외국인소진율', f"{quotes.get('foreignRatio', 0):.2f}%"]
        ]
        
        price_table = Table(price_table_data, colWidths=[3*cm, 5*cm, 3*cm, 5*cm])
        price_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
            ('BACKGROUND', (2, 0), (2, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        story.append(price_table)
        story.append(Spacer(1, 1*cm))

        # Disclaimer
        story.append(Paragraph('※ 본 리포트는 AI에 의해 자동 생성되었으며, 투자의 참고 자료로만 활용하시기 바랍니다.', 
                             ParagraphStyle('Disclaimer', parent=normal_style, fontSize=8, textColor=colors.grey, alignment=TA_CENTER)))

        doc.build(story)
        return pdf_file
