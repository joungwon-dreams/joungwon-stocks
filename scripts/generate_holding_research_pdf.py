"""
보유종목 리서치 리포트 PDF 생성

각 보유종목에 대한 상세 리서치 리포트를 PDF 형식으로 생성합니다.
"""
import asyncio
import os
import sys
from datetime import datetime
from decimal import Decimal
import aiohttp
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

# 한글 폰트 설정
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
font_dir = os.path.join(project_root, 'fonts')

font_regular = os.path.join(font_dir, 'NanumGothic.ttf')
font_bold = os.path.join(font_dir, 'NanumGothicBold.ttf')

# ReportLab 폰트 등록
try:
    if os.path.exists(font_regular) and os.path.exists(font_bold):
        pdfmetrics.registerFont(TTFont('NanumGothic', font_regular))
        pdfmetrics.registerFont(TTFont('NanumGothicBold', font_bold))
        FONT_NAME = 'NanumGothic'
        FONT_NAME_BOLD = 'NanumGothicBold'
        print(f"✅ 한글 폰트 로드 성공: {font_regular}")
    else:
        raise FileNotFoundError("Font files not found")
except Exception as e:
    print(f"⚠️  폰트 로드 실패: {e}")
    FONT_NAME = 'Helvetica'
    FONT_NAME_BOLD = 'Helvetica-Bold'

# matplotlib 폰트 설정
if os.path.exists(font_regular):
    plt.rcParams['font.family'] = ['NanumGothic', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    fm.fontManager.addfont(font_regular)
    fm.fontManager.addfont(font_bold)

import asyncpg

# DB 연결 설정
DB_CONFIG = {
    'database': 'stock_investment_db',
    'user': 'wonny',
    'host': 'localhost',
    'port': 5432
}


async def fetch_holdings_from_db():
    """데이터베이스에서 보유종목 조회"""
    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        rows = await conn.fetch('''
            SELECT stock_code, stock_name, quantity, avg_buy_price, profit_loss
            FROM stock_assets
            WHERE quantity > 0
            ORDER BY stock_code
        ''')

        holdings = {}
        for row in rows:
            holdings[row['stock_code']] = {
                'name': row['stock_name'],
                'quantity': row['quantity'],
                'avg_price': float(row['avg_buy_price']),
                'profit': float(row['profit_loss'])
            }

        return holdings

    finally:
        await conn.close()


def format_number(num):
    """숫자를 천단위 콤마로 포맷"""
    if num is None:
        return "0"
    return f"{int(num):,}"


async def fetch_stock_info(session, stock_code):
    """종목 기본 정보 조회 (네이버 금융)"""
    url = f"https://m.stock.naver.com/api/stock/{stock_code}/basic"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
    except Exception as e:
        print(f"⚠️  종목 정보 조회 실패 ({stock_code}): {e}")
    return None


async def fetch_stock_price_data(session, stock_code):
    """종목 가격 데이터 조회 (네이버 금융)"""
    url = f"https://m.stock.naver.com/api/stock/{stock_code}/price"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
    except Exception as e:
        print(f"⚠️  가격 데이터 조회 실패 ({stock_code}): {e}")
    return None


def create_price_chart(stock_code, stock_name, holding_data, temp_dir):
    """주가 차트 생성"""
    chart_path = os.path.join(temp_dir, f"{stock_code}_chart.png")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # 차트 1: 평균매수가와 현재손익
    categories = ['평균매수가', '현재 손익']
    values = [holding_data['avg_price'], holding_data['profit']]
    colors_list = ['#3498db', '#27ae60' if holding_data['profit'] > 0 else '#e74c3c']

    ax1.bar(categories, values, color=colors_list, alpha=0.7, edgecolor='black', width=0.6)
    ax1.set_title(f'{stock_name} - 투자 현황', fontsize=14, fontweight='bold', pad=15)
    ax1.set_ylabel('금액 (원)', fontsize=11)
    ax1.grid(axis='y', alpha=0.3)

    for i, v in enumerate(values):
        ax1.text(i, v, f'{v:,.0f}원', ha='center',
                va='bottom' if v > 0 else 'top', fontsize=10, fontweight='bold')

    # 차트 2: 투자금액 vs 손익
    total_investment = holding_data['quantity'] * holding_data['avg_price']
    profit_rate = (holding_data['profit'] / total_investment * 100) if total_investment > 0 else 0

    labels = ['투자금액', '손익']
    sizes = [total_investment, abs(holding_data['profit'])]
    colors_pie = ['#3498db', '#27ae60' if holding_data['profit'] > 0 else '#e74c3c']
    explode = (0.05, 0.1)

    ax2.pie(sizes, explode=explode, labels=labels, colors=colors_pie, autopct='%1.1f%%',
            shadow=True, startangle=90, textprops={'fontsize': 10})
    ax2.set_title(f'손익률: {profit_rate:.2f}%', fontsize=14, fontweight='bold', pad=15)

    plt.tight_layout()
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()

    return chart_path


async def generate_pdf_report(stock_code, holding_data, output_dir, temp_dir):
    """개별 종목 PDF 리포트 생성"""
    stock_name = holding_data['name']
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"📝 {stock_name} ({stock_code}) PDF 생성 중...")

    # 데이터 수집
    async with aiohttp.ClientSession() as session:
        stock_info = await fetch_stock_info(session, stock_code)
        price_data = await fetch_stock_price_data(session, stock_code)

    # 차트 생성
    chart_path = create_price_chart(stock_code, stock_name, holding_data, temp_dir)

    # PDF 생성
    output_path = os.path.join(output_dir, f"{stock_name}_{stock_code}.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    # 스타일 정의
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=FONT_NAME_BOLD,
        fontSize=22,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=20,
        alignment=TA_CENTER,
    )

    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=20,
    )

    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontName=FONT_NAME_BOLD,
        fontSize=15,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=20,
    )

    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=10,
        leading=16,
        alignment=TA_JUSTIFY,
    )

    # PDF 요소 리스트
    elements = []

    # 제목
    elements.append(Paragraph(f"{stock_name} ({stock_code})", title_style))
    elements.append(Paragraph(f"리서치 리포트 | {timestamp}", subtitle_style))
    elements.append(Spacer(1, 0.5*cm))

    # 보유 현황 섹션
    elements.append(Paragraph("📊 보유 현황", section_style))

    total_investment = holding_data['quantity'] * holding_data['avg_price']
    profit_rate = (holding_data['profit'] / total_investment * 100) if total_investment > 0 else 0
    profit_status = '🟢 수익' if holding_data['profit'] > 0 else '🔴 손실'

    holdings_data = [
        ['항목', '값'],
        ['보유수량', f"{format_number(holding_data['quantity'])}주"],
        ['평균매수가', f"{format_number(holding_data['avg_price'])}원"],
        ['총 투자금액', f"{format_number(total_investment)}원"],
        ['현재 손익', f"{format_number(holding_data['profit'])}원 ({profit_rate:.2f}%)"],
        ['손익 상태', profit_status],
    ]

    holdings_table = Table(holdings_data, colWidths=[8*cm, 8*cm])
    holdings_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ecf0f1'), colors.HexColor('#d5dbdb')]),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))

    elements.append(holdings_table)
    elements.append(Spacer(1, 0.5*cm))

    # 차트 추가
    if os.path.exists(chart_path):
        elements.append(Image(chart_path, width=16*cm, height=6.7*cm))
        elements.append(Spacer(1, 0.5*cm))

    # 데이터 출처
    elements.append(Paragraph(
        f"<font size=8>데이터 출처: Windows Excel (da03450000.xls) | 수집시간: {timestamp}</font>",
        ParagraphStyle('DataSource', parent=body_style, fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    ))
    elements.append(Spacer(1, 0.8*cm))

    # 현재 시세 정보 섹션
    elements.append(Paragraph("📈 현재 시세 정보", section_style))
    elements.append(Paragraph(
        f"<font size=8>데이터 출처: 네이버 금융 API | 수집시간: {timestamp}</font>",
        ParagraphStyle('DataSource2', parent=body_style, fontSize=8, textColor=colors.grey, spaceAfter=10)
    ))

    # 기본 정보 테이블
    if stock_info and isinstance(stock_info, dict):
        basic_data = [
            ['항목', '값'],
            ['종목명', stock_info.get('stockName', stock_name)],
            ['종목코드', stock_code],
            ['시장구분', stock_info.get('marketValue', 'N/A')],
            ['업종', stock_info.get('industryCodeName', 'N/A')],
        ]
    else:
        basic_data = [
            ['항목', '값'],
            ['종목명', stock_name],
            ['종목코드', stock_code],
            ['시장구분', 'N/A (데이터 수집 필요)'],
            ['업종', 'N/A (데이터 수집 필요)'],
        ]

    basic_table = Table(basic_data, colWidths=[6*cm, 10*cm])
    basic_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    elements.append(basic_table)
    elements.append(Spacer(1, 0.5*cm))

    # 가격 정보 테이블 (API 응답이 있는 경우)
    if price_data and isinstance(price_data, dict):
        close_price = price_data.get('closePrice', 'N/A')
        if isinstance(close_price, (int, float)):
            price_info_data = [
                ['항목', '값'],
                ['현재가', f"{format_number(close_price)}원"],
                ['전일대비', f"{price_data.get('compareToPreviousClosePrice', 'N/A')}원 ({price_data.get('fluctuationsRatio', 'N/A')}%)"],
                ['시가', f"{format_number(price_data.get('openPrice', 0))}원"],
                ['고가', f"{format_number(price_data.get('highPrice', 0))}원"],
                ['저가', f"{format_number(price_data.get('lowPrice', 0))}원"],
                ['거래량', f"{format_number(price_data.get('accumulatedTradingVolume', 0))}주"],
            ]

            price_table = Table(price_info_data, colWidths=[6*cm, 10*cm])
            price_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
                ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f9fa')]),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))

            elements.append(price_table)
            elements.append(Spacer(1, 0.8*cm))

    # 투자 의견 섹션
    elements.append(Paragraph("💡 투자 의견", section_style))

    # 현재 포지션 분석
    position_text = f"""
    <b>보유 수량:</b> {format_number(holding_data['quantity'])}주<br/>
    <b>투자 금액:</b> {format_number(total_investment)}원<br/>
    <b>손익률:</b> {profit_rate:.2f}%
    """
    elements.append(Paragraph(position_text, body_style))
    elements.append(Spacer(1, 0.3*cm))

    # 향후 전략
    if profit_rate > 5:
        strategy_text = """
        ✅ <b>수익 구간</b>: 목표 수익률 달성 시 일부 매도 고려<br/>
        📊 분할 매도 전략으로 수익 실현<br/>
        🎯 남은 포지션은 추가 상승 기대
        """
    elif profit_rate > 0:
        strategy_text = """
        💚 <b>소폭 수익</b>: 추가 상승 여력 관찰 필요<br/>
        📈 시장 흐름에 따라 보유 또는 익절 판단<br/>
        🔍 목표가 재설정 검토
        """
    elif profit_rate > -3:
        strategy_text = """
        ⚠️ <b>소폭 손실</b>: 단기 변동성으로 판단<br/>
        📊 기업 펀더멘털 재확인 필요<br/>
        🎯 평균 단가 조정 또는 손절 기준 재검토
        """
    else:
        strategy_text = """
        🔴 <b>손실 구간</b>: 손절 기준 재검토 필요<br/>
        ⚠️ 추가 하락 리스크 평가<br/>
        💡 포지션 축소 또는 손절 고려
        """

    elements.append(Paragraph(strategy_text, body_style))
    elements.append(Spacer(1, 0.8*cm))

    # 참고 자료
    elements.append(Paragraph("📚 참고 자료", section_style))
    ref_text = f"""
    • 네이버 금융: https://m.stock.naver.com/domestic/stock/{stock_code}/total<br/>
    • KB증권 HTS: https://www.kbsec.com/
    """
    elements.append(Paragraph(ref_text, body_style))
    elements.append(Spacer(1, 0.5*cm))

    # 면책 조항
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=body_style,
        fontSize=8,
        textColor=colors.grey,
        leading=12,
        borderWidth=1,
        borderColor=colors.grey,
        borderPadding=10,
        backColor=colors.HexColor('#f9f9f9'),
    )

    disclaimer_text = """
    <b>면책 조항</b>: 본 리포트는 개인 투자 기록 및 참고 자료로, 투자 권유가 아닙니다.
    투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.
    """
    elements.append(Paragraph(disclaimer_text, disclaimer_style))

    # PDF 빌드
    doc.build(elements)

    print(f"✅ {stock_name} PDF 생성 완료: {output_path}")

    return output_path


async def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("보유종목 리서치 리포트 PDF 생성")
    print("=" * 60)
    print()

    # 데이터베이스에서 보유종목 조회
    print("📊 데이터베이스에서 보유종목 조회 중...")
    holdings = await fetch_holdings_from_db()
    print(f"✅ 총 {len(holdings)}개 보유종목 확인")
    print()

    # 출력 디렉토리 생성
    output_dir = '/Users/wonny/Dev/joungwon.stocks.report/research_report/holding_stock'
    temp_dir = '/tmp/stock_charts'

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    print(f"📁 출력 디렉토리: {output_dir}")
    print(f"📊 임시 차트 디렉토리: {temp_dir}")
    print()

    # 각 보유종목에 대한 PDF 생성
    generated_reports = []

    for stock_code, holding_data in holdings.items():
        try:
            report_path = await generate_pdf_report(
                stock_code,
                holding_data,
                output_dir,
                temp_dir
            )
            generated_reports.append(report_path)

            # API 호출 간격
            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"❌ {holding_data['name']} ({stock_code}) PDF 생성 실패: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 60)
    print(f"✅ PDF 생성 완료: {len(generated_reports)}개")
    print("=" * 60)
    print()

    for report_path in generated_reports:
        print(f"  - {report_path}")


if __name__ == '__main__':
    asyncio.run(main())
