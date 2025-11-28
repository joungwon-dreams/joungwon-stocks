"""
거래내역 손익 리포트 PDF 생성
"""
import asyncio
import sys
from datetime import datetime
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db


# 한글 폰트 등록
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
font_dir = os.path.join(project_root, 'fonts')

try:
    font_regular = os.path.join(font_dir, 'NanumGothic.ttf')
    font_bold = os.path.join(font_dir, 'NanumGothicBold.ttf')

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
    print("   Helvetica 폰트로 대체 (한글 깨질 수 있음)")
    FONT_NAME = 'Helvetica'
    FONT_NAME_BOLD = 'Helvetica-Bold'


async def get_portfolio_summary():
    """포트폴리오 요약 데이터 조회"""

    # 보유종목 데이터
    holdings_query = """
        SELECT
            stock_code,
            stock_name,
            quantity,
            avg_buy_price,
            current_price,
            total_cost,
            total_value,
            profit_loss,
            profit_loss_rate
        FROM stock_assets
        WHERE quantity > 0
        ORDER BY total_cost DESC
    """
    holdings = await db.fetch(holdings_query)

    # 총 투자금액 계산
    total_investment = sum([h['total_cost'] for h in holdings])

    # 예수금 계산
    cash_query = """
        SELECT
            SUM(CASE WHEN trade_type = '매도' THEN total_amount ELSE 0 END) as total_sell,
            SUM(CASE WHEN trade_type = '매수' THEN total_amount ELSE 0 END) as total_buy
        FROM trade_history
        WHERE gemini_reasoning LIKE 'KB증권 엑셀 자동 임포트%'
    """
    cash_result = await db.fetchrow(cash_query)

    # 입금 총액
    total_deposits = 72_982_315  # KB증권 엑셀에서 파싱된 입금 총액

    total_sell = cash_result['total_sell'] or 0
    total_buy = cash_result['total_buy'] or 0
    available_cash = total_deposits + total_sell - total_buy

    return {
        'holdings': holdings,
        'holdings_count': len(holdings),
        'total_investment': total_investment,
        'available_cash': available_cash,
        'total_assets': total_investment + available_cash,
        'total_deposits': total_deposits,
    }


async def get_trade_history(limit=100):
    """거래내역 조회"""
    query = """
        SELECT
            trade_date,
            th.stock_code,
            s.stock_name,
            trade_type,
            quantity,
            price,
            total_amount,
            fee,
            tax
        FROM trade_history th
        LEFT JOIN stocks s ON th.stock_code = s.stock_code
        WHERE gemini_reasoning LIKE 'KB증권 엑셀 자동 임포트%'
        ORDER BY trade_date DESC, id DESC
        LIMIT $1
    """
    return await db.fetch(query, limit)


def format_number(num):
    """숫자를 천단위 콤마로 포맷"""
    if num is None:
        return "0"
    return f"{int(num):,}"


def create_dashboard_page(pdf_elements, summary):
    """대시보드 페이지 생성"""

    # 제목 스타일
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=getSampleStyleSheet()['Heading1'],
        fontName=FONT_NAME_BOLD,
        fontSize=20,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=20,
        alignment=TA_CENTER,
    )

    # 섹션 제목 스타일
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=getSampleStyleSheet()['Heading2'],
        fontName=FONT_NAME_BOLD,
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=10,
        spaceBefore=15,
    )

    # 날짜
    report_date = datetime.now().strftime('%Y년 %m월 %d일')

    # 제목
    pdf_elements.append(Paragraph(f"임정원 님의 증자산", title_style))
    pdf_elements.append(Paragraph(f"<font size=10>{report_date} 기준</font>", ParagraphStyle(
        'DateStyle',
        parent=getSampleStyleSheet()['Normal'],
        fontName=FONT_NAME,
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )))
    pdf_elements.append(Spacer(1, 0.5*cm))

    # 대시보드 요약 테이블
    dashboard_data = [
        ['항목', '금액'],
        ['총자산', f"{format_number(summary['total_assets'])}원"],
        ['현금(예수금)', f"{format_number(summary['available_cash'])}원"],
        ['보유종목 평가액', f"{format_number(summary['total_investment'])}원"],
        ['보유종목 수', f"{summary['holdings_count']}개"],
    ]

    dashboard_table = Table(dashboard_data, colWidths=[8*cm, 8*cm])
    dashboard_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ecf0f1'), colors.HexColor('#d5dbdb')]),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))

    pdf_elements.append(dashboard_table)
    pdf_elements.append(Spacer(1, 1*cm))

    # 보유종목 섹션
    pdf_elements.append(Paragraph("보유종목 상세", section_style))

    # 보유종목 테이블
    holdings_data = [['종목코드', '종목명', '보유수량', '평균매수가', '총매수금액']]

    for h in summary['holdings']:
        holdings_data.append([
            h['stock_code'],
            h['stock_name'],
            f"{int(h['quantity'])}주",
            f"{format_number(h['avg_buy_price'])}원",
            f"{format_number(h['total_cost'])}원",
        ])

    holdings_table = Table(holdings_data, colWidths=[3*cm, 4*cm, 3*cm, 3.5*cm, 3.5*cm])
    holdings_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    pdf_elements.append(holdings_table)


def create_trade_history_pages(pdf_elements, trades):
    """거래내역 페이지 생성"""

    # 새 페이지 시작
    pdf_elements.append(PageBreak())

    # 섹션 제목
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=getSampleStyleSheet()['Heading2'],
        fontName=FONT_NAME_BOLD,
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=10,
    )

    pdf_elements.append(Paragraph("거래내역", section_style))
    pdf_elements.append(Spacer(1, 0.3*cm))

    # 거래내역 테이블 헤더
    trade_data = [['거래일자', '종목코드', '종목명', '구분', '수량', '단가', '거래금액', '수수료']]

    # 거래내역 데이터
    for trade in trades:
        trade_date = trade['trade_date'].strftime('%Y-%m-%d') if trade['trade_date'] else '-'
        stock_name = trade['stock_name'] or trade['stock_code']

        # 매수/매도 색상 구분
        trade_type = trade['trade_type']

        trade_data.append([
            trade_date,
            trade['stock_code'],
            stock_name,
            trade_type,
            f"{int(trade['quantity'])}",
            f"{format_number(trade['price'])}",
            f"{format_number(trade['total_amount'])}",
            f"{format_number(trade['fee'] + trade['tax'])}",
        ])

    # 거래내역 테이블 생성
    col_widths = [2.5*cm, 2*cm, 3*cm, 1.5*cm, 1.5*cm, 2.5*cm, 2.5*cm, 1.5*cm]
    trade_table = Table(trade_data, colWidths=col_widths, repeatRows=1)

    # 테이블 스타일
    style_commands = [
        ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (5, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]

    # 매수/매도 색상 구분
    for i, trade in enumerate(trades, start=1):
        if trade['trade_type'] == '매수':
            style_commands.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#e74c3c')))
        else:
            style_commands.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#3498db')))

    trade_table.setStyle(TableStyle(style_commands))

    pdf_elements.append(trade_table)


async def generate_pdf():
    """PDF 리포트 생성"""

    print("=== 거래내역 손익 리포트 PDF 생성 ===")
    print()

    await db.connect()

    try:
        # 데이터 조회
        print("📊 데이터 조회 중...")
        summary = await get_portfolio_summary()
        trades = await get_trade_history(limit=200)

        print(f"✅ 보유종목: {summary['holdings_count']}개")
        print(f"✅ 거래내역: {len(trades)}건")
        print()

        # PDF 파일 생성
        output_path = '/Users/wonny/Dev/joungwon.stocks.report/trading_report.pdf'
        print(f"📝 PDF 생성 중: {output_path}")

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )

        # PDF 요소 리스트
        pdf_elements = []

        # 대시보드 페이지 생성
        create_dashboard_page(pdf_elements, summary)

        # 거래내역 페이지 생성
        create_trade_history_pages(pdf_elements, trades)

        # PDF 빌드
        doc.build(pdf_elements)

        print()
        print(f"✅ PDF 생성 완료: {output_path}")
        print()
        print("=== 요약 ===")
        print(f"총자산: {format_number(summary['total_assets'])}원")
        print(f"예수금: {format_number(summary['available_cash'])}원")
        print(f"보유종목 평가액: {format_number(summary['total_investment'])}원")
        print(f"보유종목 수: {summary['holdings_count']}개")

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(generate_pdf())
