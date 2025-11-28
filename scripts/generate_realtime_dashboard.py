#!/usr/bin/env python3
"""
실시간 보유종목 대시보드 PDF 생성
평가금액 높은 순으로 보유종목 현황 표시
"""
import asyncio
import asyncpg
from datetime import datetime
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 한글 폰트 등록
FONT_PATH = '/System/Library/Fonts/Supplemental/AppleGothic.ttf'
pdfmetrics.registerFont(TTFont('AppleGothic', FONT_PATH))

# 데이터베이스 설정
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_investment_db',
    'user': 'wonny'
}


async def get_holdings_data():
    """보유종목 + 최신 현재가 데이터 조회"""
    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        query = '''
            WITH latest_prices AS (
                SELECT DISTINCT ON (stock_code)
                    stock_code,
                    price,
                    change_rate,
                    volume,
                    timestamp
                FROM min_ticks
                ORDER BY stock_code, timestamp DESC
            )
            SELECT
                sa.stock_code,
                sa.stock_name,
                sa.quantity,
                sa.avg_buy_price,
                sa.total_value,
                lp.price AS current_price,
                lp.change_rate,
                lp.volume,
                lp.timestamp,
                (lp.price * sa.quantity) AS current_value,
                ((lp.price - sa.avg_buy_price) / sa.avg_buy_price * 100) AS profit_rate,
                ((lp.price * sa.quantity) - sa.total_value) AS profit_amount
            FROM stock_assets sa
            JOIN latest_prices lp ON sa.stock_code = lp.stock_code
            WHERE sa.quantity > 0
            ORDER BY (lp.price * sa.quantity) DESC
        '''

        rows = await conn.fetch(query)
        return rows

    finally:
        await conn.close()


def create_pdf(holdings_data, output_path):
    """PDF 생성"""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    # 스타일 정의
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName='AppleGothic',
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=1  # center
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontName='AppleGothic',
        fontSize=12,
        textColor=colors.HexColor('#666666'),
        spaceAfter=20,
        alignment=1
    )

    # PDF 요소 리스트
    elements = []

    # 제목
    now = datetime.now()
    title = Paragraph("📊 실시간 보유종목 대시보드", title_style)
    subtitle = Paragraph(
        f"생성 시각: {now.strftime('%Y년 %m월 %d일 %H:%M:%S')}",
        subtitle_style
    )
    elements.append(title)
    elements.append(subtitle)
    elements.append(Spacer(1, 0.3*inch))

    # 전체 요약
    total_invested = sum(float(row['total_value']) for row in holdings_data)
    total_current = sum(float(row['current_value']) for row in holdings_data)
    total_profit = total_current - total_invested
    total_profit_rate = (total_profit / total_invested * 100) if total_invested > 0 else 0

    summary_data = [
        ['항목', '금액'],
        ['총 투자금액', f"{total_invested:,.0f}원"],
        ['총 평가금액', f"{total_current:,.0f}원"],
        ['총 손익금액', f"{total_profit:+,.0f}원"],
        ['총 손익률', f"{total_profit_rate:+.2f}%"],
    ]

    summary_table = Table(summary_data, colWidths=[2*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90e2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 0.5*inch))

    # 보유종목 상세 테이블
    detail_title = Paragraph(
        "📈 보유종목 상세 (평가금액 높은 순)",
        ParagraphStyle(
            'DetailTitle',
            parent=styles['Heading2'],
            fontName='AppleGothic',
            fontSize=16,
            textColor=colors.HexColor('#333333'),
            spaceAfter=15
        )
    )
    elements.append(detail_title)

    # 테이블 데이터
    table_data = [
        ['종목명', '종목코드', '수량', '평단가', '현재가', '등락률', '평가금액', '손익률']
    ]

    for row in holdings_data:
        stock_name = row['stock_name']
        stock_code = row['stock_code']
        quantity = int(row['quantity'])
        avg_price = int(row['avg_buy_price'])
        current_price = int(row['current_price'])
        change_rate = float(row['change_rate'])
        current_value = int(row['current_value'])
        profit_rate = float(row['profit_rate'])

        table_data.append([
            stock_name,
            stock_code,
            f"{quantity:,}주",
            f"{avg_price:,}원",
            f"{current_price:,}원",
            f"{change_rate:+.2f}%",
            f"{current_value:,}원",
            f"{profit_rate:+.2f}%"
        ])

    detail_table = Table(
        table_data,
        colWidths=[1*inch, 0.8*inch, 0.7*inch, 0.8*inch, 0.8*inch, 0.7*inch, 1*inch, 0.7*inch]
    )

    # 테이블 스타일
    table_style = [
        ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
    ]

    # 손익률에 따른 색상 적용
    for i, row in enumerate(holdings_data, start=1):
        profit_rate = float(row['profit_rate'])
        if profit_rate > 0:
            table_style.append(('TEXTCOLOR', (7, i), (7, i), colors.red))
        elif profit_rate < 0:
            table_style.append(('TEXTCOLOR', (7, i), (7, i), colors.blue))

        change_rate = float(row['change_rate'])
        if change_rate > 0:
            table_style.append(('TEXTCOLOR', (5, i), (5, i), colors.red))
        elif change_rate < 0:
            table_style.append(('TEXTCOLOR', (5, i), (5, i), colors.blue))

    detail_table.setStyle(TableStyle(table_style))
    elements.append(detail_table)

    # 페이지 나누기
    elements.append(PageBreak())

    # 개별 종목 상세 정보
    for row in holdings_data:
        stock_info_title = Paragraph(
            f"📌 {row['stock_name']} ({row['stock_code']})",
            ParagraphStyle(
                'StockTitle',
                parent=styles['Heading3'],
                fontName='AppleGothic',
                fontSize=14,
                textColor=colors.HexColor('#2c3e50'),
                spaceAfter=10
            )
        )
        elements.append(stock_info_title)

        # 종목별 상세 정보
        stock_detail = [
            ['항목', '내용'],
            ['보유 수량', f"{int(row['quantity']):,}주"],
            ['평균 매수가', f"{int(row['avg_buy_price']):,}원"],
            ['투자 금액', f"{int(row['total_value']):,}원"],
            ['현재가', f"{int(row['current_price']):,}원"],
            ['당일 등락률', f"{float(row['change_rate']):+.2f}%"],
            ['거래량', f"{int(row['volume']):,}주"],
            ['평가 금액', f"{int(row['current_value']):,}원"],
            ['손익 금액', f"{int(row['profit_amount']):+,}원"],
            ['손익률', f"{float(row['profit_rate']):+.2f}%"],
            ['데이터 시각', row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')],
        ]

        stock_table = Table(stock_detail, colWidths=[2*inch, 3.5*inch])
        stock_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
        ]))

        elements.append(stock_table)
        elements.append(Spacer(1, 0.3*inch))

    # PDF 빌드
    doc.build(elements)
    print(f"✅ PDF 생성 완료: {output_path}")


async def main():
    """메인 함수"""
    print("\n" + "="*80)
    print("📊 실시간 보유종목 대시보드 PDF 생성")
    print("="*80 + "\n")

    # 출력 디렉토리
    output_dir = Path('/Users/wonny/Dev/joungwon.stocks/reports')
    output_dir.mkdir(parents=True, exist_ok=True)

    # 데이터 조회
    print("📡 보유종목 데이터 조회 중...")
    holdings_data = await get_holdings_data()
    print(f"✅ {len(holdings_data)}개 종목 데이터 조회 완료\n")

    # PDF 생성
    output_path = output_dir / 'realtime_dashboard.pdf'
    print(f"📄 PDF 생성 중: {output_path}")
    create_pdf(holdings_data, output_path)

    print("\n" + "="*80)
    print(f"✅ 완료! PDF 경로: {output_path}")
    print("="*80 + "\n")


if __name__ == '__main__':
    asyncio.run(main())
