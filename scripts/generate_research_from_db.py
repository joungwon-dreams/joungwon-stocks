"""
데이터베이스 기반 보유종목 리서치 리포트 PDF 생성

stock_assets와 collected_data 테이블에서 실시간 데이터를 가져와
각 보유종목에 대한 상세 리서치 리포트를 PDF로 생성합니다.
"""
import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import aiohttp

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db

# 한글 폰트 등록
FONT_PATH = '/Users/wonny/Dev/joungwon.stocks/fonts/NanumGothic.ttf'
FONT_BOLD_PATH = '/Users/wonny/Dev/joungwon.stocks/fonts/NanumGothicBold.ttf'

try:
    pdfmetrics.registerFont(TTFont('NanumGothic', FONT_PATH))
    pdfmetrics.registerFont(TTFont('NanumGothicBold', FONT_BOLD_PATH))
    FONT_NAME = 'NanumGothic'
    FONT_BOLD_NAME = 'NanumGothicBold'
except:
    print("⚠️  한글 폰트 로드 실패, Helvetica 사용")
    FONT_NAME = 'Helvetica'
    FONT_BOLD_NAME = 'Helvetica-Bold'

# matplotlib 한글 폰트 설정
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

try:
    font_prop = fm.FontProperties(fname=FONT_PATH)
    plt.rcParams['font.family'] = font_prop.get_name()
    plt.rcParams['axes.unicode_minus'] = False
except:
    # Fallback to any Korean font available
    try:
        plt.rcParams['font.family'] = 'AppleGothic'  # macOS default Korean font
        plt.rcParams['axes.unicode_minus'] = False
    except:
        print("⚠️  matplotlib 한글 폰트 설정 실패")


def safe_int(value, default=0):
    """Safely convert value to int, handling strings and None"""
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_float(value, default=0.0):
    """Safely convert value to float, handling strings and None"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


async def fetch_holding_stocks():
    """stock_assets에서 보유종목 조회"""
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
        WHERE is_active = TRUE
          AND quantity > 0
        ORDER BY stock_code
    '''

    rows = await db.fetch(query)
    return [dict(row) for row in rows]


async def fetch_collected_data(stock_code):
    """collected_data에서 해당 종목의 최신 데이터 조회"""
    query = '''
        SELECT DISTINCT ON (data_type)
            data_type,
            data_content,
            site_id,
            domain_id,
            collected_at
        FROM collected_data
        WHERE ticker = $1
        ORDER BY data_type, collected_at DESC
    '''

    rows = await db.fetch(query, stock_code)
    return [dict(row) for row in rows]


async def fetch_stock_info(session, stock_code):
    """네이버 금융 API에서 종목 기본 정보 조회"""
    url = f'https://m.stock.naver.com/api/stock/{stock_code}/basic'

    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data
    except Exception as e:
        print(f"⚠️  종목 정보 조회 실패 ({stock_code}): {e}")

    return None


async def fetch_stock_price_data(session, stock_code):
    """네이버 금융 API에서 종목 가격 데이터 조회"""
    url = f'https://m.stock.naver.com/api/stock/{stock_code}/price'

    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                # If data is a list, return the first item
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
                return data
    except Exception as e:
        print(f"⚠️  가격 데이터 조회 실패 ({stock_code}): {e}")

    return None


def create_price_chart(stock_code, stock_name, holding_data, temp_dir):
    """투자 현황 차트 생성"""

    # 2개의 subplot 생성
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # 1. 막대 차트 - 평균매수가 vs 현재손익
    avg_price = holding_data['avg_buy_price']
    profit_loss = holding_data['profit_loss']

    categories = ['평균매수가', '현재손익']
    values = [avg_price, profit_loss]
    colors_bar = ['#3498db', '#27ae60' if profit_loss >= 0 else '#e74c3c']

    ax1.bar(categories, values, color=colors_bar, alpha=0.7)
    ax1.set_title(f'{stock_name} 투자 현황', fontsize=14, fontweight='bold')
    ax1.set_ylabel('금액 (원)', fontsize=11)
    ax1.grid(axis='y', alpha=0.3)

    # 값 표시
    for i, v in enumerate(values):
        ax1.text(i, v, f'{v:,.0f}원', ha='center', va='bottom' if v >= 0 else 'top', fontsize=10)

    # 2. 파이 차트 - 투자금액 vs 손익
    total_cost = holding_data['total_cost']
    profit_loss = holding_data['profit_loss']

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

    # 저장
    chart_path = os.path.join(temp_dir, f'{stock_code}_chart.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()

    return chart_path


async def generate_pdf_report(stock_code, holding_data, collected_data, output_dir, temp_dir):
    """개별 종목 PDF 리포트 생성"""

    stock_name = holding_data['stock_name']
    pdf_file = os.path.join(output_dir, f'{stock_name}_{stock_code}.pdf')

    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=A4,
        topMargin=2*cm,
        bottomMargin=2*cm,
        leftMargin=2*cm,
        rightMargin=2*cm
    )

    story = []
    styles = getSampleStyleSheet()

    # 커스텀 스타일
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=FONT_BOLD_NAME,
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )

    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontName=FONT_BOLD_NAME,
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=20
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=10,
        leading=14
    )

    # 제목
    story.append(Paragraph(f'{stock_name} 리서치 리포트', title_style))
    story.append(Paragraph(f'종목코드: {stock_code}', normal_style))
    story.append(Spacer(1, 0.5*cm))

    # 생성 시간
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    story.append(Paragraph(f'생성일시: {now}', normal_style))
    story.append(Spacer(1, 1*cm))

    # ==================== 섹션 1: 보유 현황 ====================
    story.append(Paragraph('1. 보유 현황', section_style))
    story.append(Spacer(1, 0.3*cm))

    profit_rate = holding_data['profit_rate']
    profit_emoji = "🟢" if profit_rate >= 0 else "🔴"

    holding_table_data = [
        ['항목', '값'],
        ['보유수량', f"{holding_data['quantity']:,}주"],
        ['평균매수가', f"{holding_data['avg_buy_price']:,}원"],
        ['현재가', f"{holding_data['current_price']:,}원"],
        ['총 투자금액', f"{holding_data['total_cost']:,}원"],
        ['현재 평가금액', f"{holding_data['total_value']:,}원"],
        ['평가손익', f"{profit_emoji} {holding_data['profit_loss']:,}원"],
        ['손익률', f"{profit_emoji} {profit_rate:.2f}%"],
    ]

    holding_table = Table(holding_table_data, colWidths=[6*cm, 8*cm])
    holding_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD_NAME),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ecf0f1'), colors.HexColor('#d5dbdb')])
    ]))

    story.append(holding_table)
    story.append(Spacer(1, 0.5*cm))

    # 차트 추가
    chart_path = create_price_chart(stock_code, stock_name, holding_data, temp_dir)
    story.append(Image(chart_path, width=15*cm, height=6.25*cm))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph(f'<font size=8 color="#7f8c8d">데이터 출처: stock_assets 테이블 | 업데이트: {now}</font>', normal_style))
    story.append(Spacer(1, 1*cm))

    # ==================== 섹션 2: 수집된 데이터 ====================
    story.append(Paragraph('2. 수집된 데이터 현황', section_style))
    story.append(Spacer(1, 0.3*cm))

    if collected_data:
        data_table_data = [['데이터 타입', 'Site ID / Domain ID', '수집 시간']]

        for item in collected_data:
            data_type = item['data_type']
            source_info = f"Site {item['site_id']} / Domain {item['domain_id']}"
            collected_at = item['collected_at'].strftime('%Y-%m-%d %H:%M:%S')
            data_table_data.append([data_type, source_info, collected_at])

        data_table = Table(data_table_data, colWidths=[4*cm, 6*cm, 4*cm])
        data_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD_NAME),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ecf0f1'), colors.HexColor('#d5dbdb')])
        ]))

        story.append(data_table)
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(f'<font size=8 color="#7f8c8d">총 {len(collected_data)}개 데이터 타입 수집 완료</font>', normal_style))
    else:
        story.append(Paragraph('수집된 데이터가 없습니다.', normal_style))

    story.append(Spacer(1, 1*cm))

    # ==================== 섹션 3: 현재 시세 정보 ====================
    story.append(Paragraph('3. 현재 시세 정보 (네이버 금융)', section_style))
    story.append(Spacer(1, 0.3*cm))

    async with aiohttp.ClientSession() as session:
        stock_info = await fetch_stock_info(session, stock_code)
        price_data = await fetch_stock_price_data(session, stock_code)

        await asyncio.sleep(0.5)  # Rate limit

        if stock_info and price_data:
            price_table_data = [
                ['항목', '값'],
                ['종목명', stock_info.get('stockName', 'N/A')],
                ['시장구분', stock_info.get('marketValue', 'N/A')],
                ['업종', stock_info.get('industryCodeName', 'N/A')],
                ['현재가', f"{safe_int(price_data.get('closePrice')):,}원"],
                ['전일대비', f"{safe_int(price_data.get('compareToPreviousClosePrice')):,}원 ({safe_float(price_data.get('fluctuationsRatio')):.2f}%)"],
                ['시가', f"{safe_int(price_data.get('openPrice')):,}원"],
                ['고가', f"{safe_int(price_data.get('highPrice')):,}원"],
                ['저가', f"{safe_int(price_data.get('lowPrice')):,}원"],
                ['거래량', f"{safe_int(price_data.get('accumulatedTradingVolume')):,}주"],
            ]

            price_table = Table(price_table_data, colWidths=[6*cm, 8*cm])
            price_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD_NAME),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ecf0f1'), colors.HexColor('#d5dbdb')])
            ]))

            story.append(price_table)
            story.append(Spacer(1, 0.3*cm))
            story.append(Paragraph(f'<font size=8 color="#7f8c8d">데이터 출처: 네이버 금융 API | 조회 시간: {now}</font>', normal_style))
        else:
            story.append(Paragraph('시세 정보를 가져올 수 없습니다.', normal_style))

    story.append(Spacer(1, 1*cm))

    # ==================== 섹션 4: 투자 의견 ====================
    story.append(Paragraph('4. 투자 의견', section_style))
    story.append(Spacer(1, 0.3*cm))

    if profit_rate > 5:
        opinion = f"""
        현재 {profit_rate:.2f}% 수익 구간입니다. 목표 수익률을 달성한 경우 일부 매도를 고려할 수 있습니다.
        분할 매도 전략으로 수익을 실현하면서 추가 상승 여력도 기대할 수 있습니다.
        """
    elif profit_rate > 0:
        opinion = f"""
        현재 {profit_rate:.2f}% 소폭 수익 구간입니다. 추가 상승 여력을 관찰하면서
        시장 흐름을 확인하는 것이 좋습니다. 손익분기점을 넘어섰으므로 안정적인 포지션입니다.
        """
    elif profit_rate > -3:
        opinion = f"""
        현재 {profit_rate:.2f}% 소폭 손실 구간입니다. 단기 변동성으로 판단되며,
        종목의 펀더멘털을 재확인하고 장기 투자 관점에서 접근하는 것이 좋습니다.
        """
    else:
        opinion = f"""
        현재 {profit_rate:.2f}% 손실 구간입니다. 손절 기준을 재검토하고
        포지션 축소를 고려해볼 필요가 있습니다. 추가 하락 리스크를 관리하세요.
        """

    story.append(Paragraph(opinion.strip(), normal_style))
    story.append(Spacer(1, 1*cm))

    # ==================== 섹션 5: 참고 자료 ====================
    story.append(Paragraph('5. 참고 자료', section_style))
    story.append(Spacer(1, 0.3*cm))

    links = f"""
    • 네이버 금융: https://finance.naver.com/item/main.naver?code={stock_code}<br/>
    • KB증권 HTS: https://www.kbsec.com<br/>
    <br/>
    <font color="#e74c3c">※ 본 리포트는 투자 참고용이며, 투자 판단은 본인의 책임입니다.</font>
    """

    story.append(Paragraph(links.strip(), normal_style))

    # PDF 생성
    doc.build(story)

    return pdf_file


async def main():
    """메인 실행 함수"""

    output_dir = '/Users/wonny/Dev/joungwon.stocks.report/research_report/holding_stock'
    temp_dir = '/tmp/stock_charts'

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    print("=" * 80)
    print("데이터베이스 기반 보유종목 리서치 리포트 생성")
    print("=" * 80)
    print()

    await db.connect()

    try:
        # 보유종목 조회
        holding_stocks = await fetch_holding_stocks()

        print(f"📊 보유종목: {len(holding_stocks)}개")
        print()

        # 각 종목별 PDF 생성
        for stock in holding_stocks:
            stock_code = stock['stock_code']
            stock_name = stock['stock_name']

            print(f"🔄 {stock_name} ({stock_code}) 리포트 생성 중...")

            # collected_data 조회
            collected_data = await fetch_collected_data(stock_code)

            # PDF 생성
            pdf_file = await generate_pdf_report(
                stock_code, stock, collected_data, output_dir, temp_dir
            )

            print(f"✅ PDF 생성 완료: {pdf_file}")
            print(f"   - 보유수량: {stock['quantity']:,}주")
            print(f"   - 손익률: {stock['profit_rate']:.2f}%")
            print(f"   - 수집 데이터: {len(collected_data)}개 타입")
            print()

        print("=" * 80)
        print(f"✅ 전체 리포트 생성 완료: {len(holding_stocks)}개")
        print("=" * 80)
        print(f"📁 출력 디렉토리: {output_dir}")

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
