"""
한국전력 종합 리포트 생성 (기존 comprehensive 방식)
"""
import asyncio
import sys
import os
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from datetime import datetime
from src.config.database import db
from src.fetchers.tier2_official_apis.daum_fetcher import DaumFetcher
from src.fetchers.tier4_browser_automation.naver_main_comprehensive_fetcher import NaverMainComprehensiveFetcher
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
import google.generativeai as genai

# 폰트 설정
FONT_PATH = '/Users/wonny/Dev/joungwon.stocks/fonts/NanumGothic.ttf'
FONT_BOLD_PATH = '/Users/wonny/Dev/joungwon.stocks/fonts/NanumGothicBold.ttf'

try:
    pdfmetrics.registerFont(TTFont('NanumGothic', FONT_PATH))
    pdfmetrics.registerFont(TTFont('NanumGothicBold', FONT_BOLD_PATH))
    FONT_NAME = 'NanumGothic'
    FONT_BOLD_NAME = 'NanumGothicBold'
    print("✅ 한글 폰트 로드 성공")
except:
    FONT_NAME = 'Helvetica'
    FONT_BOLD_NAME = 'Helvetica-Bold'

# Matplotlib 폰트
try:
    font_prop = fm.FontProperties(fname=FONT_PATH)
    font_entry = fm.FontEntry(fname=FONT_PATH, name='NanumGothic')
    fm.fontManager.ttflist.append(font_entry)
    plt.rcParams['font.family'] = 'NanumGothic'
    plt.rcParams['axes.unicode_minus'] = False
except:
    plt.rcParams['font.family'] = 'AppleGothic'
    plt.rcParams['axes.unicode_minus'] = False

# Gemini 설정
from src.config.settings import settings
gemini_model = None
if settings.GEMINI_API_KEY:
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
    except Exception as e:
        print(f"⚠️ Gemini 초기화 실패: {e}")

async def fetch_daum_data(stock_code: str):
    """Daum Finance 데이터 수집"""
    daum_config = {
        'site_name_ko': 'Daum Finance',
        'data_type': 'daum_comprehensive',
        'domain_id': 1
    }
    daum_fetcher = DaumFetcher(site_id=60, config=daum_config)
    return await daum_fetcher.fetch(stock_code)

async def fetch_naver_data(stock_code: str):
    """Naver Finance 데이터 수집"""
    naver_config = {
        'headless': True,
        'viewport': {'width': 1920, 'height': 1080},
        'data_type': 'naver_main_comprehensive',
        'domain_id': 1
    }
    naver_fetcher = NaverMainComprehensiveFetcher(site_id=61, config=naver_config)
    try:
        await naver_fetcher.initialize()
        return await naver_fetcher.fetch_data(stock_code)
    finally:
        await naver_fetcher.cleanup()

def create_simple_chart(stock_code: str, stock_name: str, holding_data: dict) -> str:
    """간단한 차트 생성"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    avg_price = holding_data['avg_buy_price']
    profit_loss = holding_data['profit_loss']
    categories = ['평균매수가', '현재손익']
    values = [avg_price, profit_loss]
    colors_bar = ['#3498db', '#27ae60' if profit_loss >= 0 else '#e74c3c']

    ax1.bar(categories, values, color=colors_bar, alpha=0.7)
    ax1.set_title(f'{stock_name} 투자 현황', fontsize=14, fontweight='bold')
    ax1.set_ylabel('금액 (원)', fontsize=11)
    ax1.grid(axis='y', alpha=0.3)
    for i, v in enumerate(values):
        ax1.text(i, v, f'{v:,.0f}원', ha='center', va='bottom' if v >= 0 else 'top', fontsize=10)

    total_cost = holding_data['total_cost']
    if profit_loss >= 0:
        labels = ['투자금액', '수익']
        sizes = [total_cost, profit_loss]
        colors_pie = ['#3498db', '#27ae60']
    else:
        labels = ['현재평가액', '손실']
        sizes = [total_cost + profit_loss, -profit_loss]
        colors_pie = ['#3498db', '#e74c3c']

    ax2.pie(sizes, labels=labels, colors=colors_pie, autopct='%1.1f%%', startangle=90)
    ax2.set_title(f'손익 구성 ({holding_data["profit_rate"]:.2f}%)', fontsize=14, fontweight='bold')

    plt.tight_layout()
    chart_path = f'/tmp/{stock_code}_chart.png'
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    return chart_path

async def main():
    print("📝 한국전력 (015760) 종합 리포트 생성 중...")

    await db.connect()

    try:
        stock_code = '015760'
        stock_name = '한국전력'

        # 1. DB에서 보유 정보 조회
        query = '''
            SELECT
                stock_code,
                stock_name,
                quantity,
                avg_buy_price,
                current_price,
                (current_price - avg_buy_price) * quantity as profit_loss,
                ROUND((current_price - avg_buy_price)::numeric / avg_buy_price * 100, 2) as profit_rate,
                avg_buy_price * quantity as total_cost,
                current_price * quantity as total_value
            FROM stock_assets
            WHERE stock_code = $1
              AND is_active = TRUE
              AND quantity > 0
        '''
        rows = await db.fetch(query, stock_code)

        if not rows:
            print(f"❌ {stock_name} 보유 정보 없음")
            return

        holding_data = dict(rows[0])
        print(f"✅ {stock_name} 보유 정보 확인")

        # 2. Daum Finance 데이터 수집
        print("  📊 Daum Finance 데이터 수집...")
        daum_data = await fetch_daum_data(stock_code)

        # 3. Naver Finance 데이터 수집
        print("  📊 Naver Finance 데이터 수집...")
        naver_data = await fetch_naver_data(stock_code)

        # 4. PDF 생성
        print("  📈 PDF 생성...")
        pdf_path = f'/Users/wonny/Dev/joungwon.stocks.report/research_report/holding_stock/한국전력_015760_comprehensive.pdf'

        doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                               topMargin=2*cm, bottomMargin=2*cm,
                               leftMargin=2*cm, rightMargin=2*cm)

        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                    fontName=FONT_BOLD_NAME, fontSize=24,
                                    alignment=TA_CENTER, spaceAfter=20)
        section_style = ParagraphStyle('Section', parent=styles['Heading2'],
                                       fontName=FONT_BOLD_NAME, fontSize=16,
                                       spaceBefore=15, spaceAfter=10,
                                       textColor=colors.HexColor('#2c3e50'))
        normal_style = ParagraphStyle('Normal', parent=styles['Normal'],
                                     fontName=FONT_NAME, fontSize=10, leading=16)

        # 제목
        story.append(Paragraph(f'{stock_name} 종합 투자 리포트', title_style))
        story.append(Paragraph(f'생성일시: {datetime.now().strftime("%Y/%m/%d %H:%M")}',
                              ParagraphStyle('Date', parent=normal_style, alignment=TA_CENTER)))
        story.append(Spacer(1, 1*cm))

        # 보유 현황
        story.append(Paragraph('📊 보유 현황', section_style))
        chart_path = create_simple_chart(stock_code, stock_name, holding_data)
        story.append(Image(chart_path, width=16*cm, height=6.5*cm))
        story.append(Spacer(1, 0.5*cm))

        # 보유 정보 테이블
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
            ('TEXTCOLOR', (3, 1), (3, 1), profit_color),
        ]))
        story.append(holding_table)
        story.append(Spacer(1, 1*cm))

        # Daum/Naver 데이터
        story.append(Paragraph('📈 실시간 시세', section_style))
        quotes = daum_data.get('quotes', {})

        price_table_data = [
            ['현재가', f"{quotes.get('tradePrice', 0):,}원", '거래량', f"{quotes.get('accTradeVolume', 0):,}주"],
            ['등락률', f"{quotes.get('changeRate', 0):.2f}%", '외국인비율', f"{quotes.get('foreignRatio', 0):.2f}%"]
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

        doc.build(story)
        print(f"✅ 리포트 생성 완료: {pdf_path}")

    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
