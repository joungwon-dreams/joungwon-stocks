"""
보유종목 PDF 리포트 생성기
- 개별 종목 PDF
- 전체 대시보드 PDF
"""
import asyncio
import asyncpg
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import io
import os

# 한글 폰트 등록
pdfmetrics.registerFont(TTFont('NanumGothic', '/System/Library/Fonts/Supplemental/AppleGothic.ttf'))

# matplotlib 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

DB_URL = 'postgresql://wonny@localhost:5432/stock_investment_db'
REPORT_DIR = 'reports'
REQUEST_STOCK_FILE = 'reports/request_stock/request_stock.md'


def get_styles():
    """스타일 정의"""
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Korean', fontName='NanumGothic', fontSize=10, leading=14))
    styles.add(ParagraphStyle(name='KoreanTitle', fontName='NanumGothic', fontSize=18, leading=22, spaceAfter=10))
    styles.add(ParagraphStyle(name='KoreanSubtitle', fontName='NanumGothic', fontSize=14, leading=18, spaceAfter=8))
    styles.add(ParagraphStyle(name='KoreanSmall', fontName='NanumGothic', fontSize=9, leading=12))
    styles.add(ParagraphStyle(name='KoreanLarge', fontName='NanumGothic', fontSize=24, leading=28, spaceAfter=15))
    return styles


async def get_all_holdings(conn):
    """모든 보유종목 조회"""
    return await conn.fetch('''
        SELECT sa.stock_code, sa.stock_name, sa.quantity, sa.avg_buy_price, sa.total_cost
        FROM stock_assets sa
        WHERE sa.quantity > 0
        ORDER BY sa.total_cost DESC
    ''')


def get_requested_stocks():
    """request_stock.md에서 요청 종목명 읽기"""
    if not os.path.exists(REQUEST_STOCK_FILE):
        return []

    with open(REQUEST_STOCK_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    stocks = []
    for line in lines:
        line = line.strip()
        # 제목(#으로 시작)이나 빈 줄 제외
        if line and not line.startswith('#'):
            stocks.append(line)
    return stocks


async def get_stock_code_by_name(conn, name):
    """종목명으로 종목코드 조회"""
    result = await conn.fetchrow('''
        SELECT stock_code, stock_name FROM stocks
        WHERE stock_name = $1
    ''', name)
    return result


async def get_stock_data(conn, code):
    """종목별 상세 데이터"""
    stock = await conn.fetchrow('''
        SELECT s.*, sa.quantity, sa.avg_buy_price, sa.total_cost
        FROM stocks s
        LEFT JOIN stock_assets sa ON s.stock_code = sa.stock_code
        WHERE s.stock_code = $1
    ''', code)

    ohlcv = await conn.fetch('''
        SELECT date, open, high, low, close, volume
        FROM daily_ohlcv
        WHERE stock_code = $1
        ORDER BY date DESC LIMIT 60
    ''', code)

    ai = await conn.fetchrow('''
        SELECT * FROM smart_recommendations
        WHERE stock_code = $1
        ORDER BY created_at DESC LIMIT 1
    ''', code)

    fund = await conn.fetchrow('''
        SELECT * FROM stock_fundamentals
        WHERE stock_code = $1
    ''', code)

    return stock, ohlcv, ai, fund


def create_stock_chart(ohlcv, avg_price, stock_name):
    """주가 차트 생성"""
    if not ohlcv:
        return None

    closes = [float(row['close']) for row in reversed(ohlcv)]

    fig, ax = plt.subplots(figsize=(7, 3))
    ax.plot(range(len(closes)), closes, 'b-', linewidth=1.5)
    ax.axhline(y=avg_price, color='r', linestyle='--', label=f'Avg: {int(avg_price):,}')
    ax.fill_between(range(len(closes)), closes, alpha=0.3)
    ax.set_ylabel('Price (KRW)')
    ax.set_title(f'{stock_name} Stock Price (60 days)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    img_buffer.seek(0)
    plt.close()

    return img_buffer


async def generate_individual_pdf(conn, code, styles):
    """개별 종목 PDF 생성"""
    stock, ohlcv, ai, fund = await get_stock_data(conn, code)

    if not stock:
        print(f'  ⚠️ {code} 데이터 없음')
        return None

    stock_name = stock['stock_name']
    filename = f'{REPORT_DIR}/{stock_name}.pdf'

    doc = SimpleDocTemplate(filename, pagesize=A4,
                           topMargin=20*mm, bottomMargin=20*mm,
                           leftMargin=15*mm, rightMargin=15*mm)

    elements = []

    # 제목
    elements.append(Paragraph(f'{stock_name} ({code}) 투자 리포트', styles['KoreanTitle']))
    elements.append(Paragraph(f'생성일: {datetime.now().strftime("%Y-%m-%d %H:%M")}', styles['KoreanSmall']))
    elements.append(Spacer(1, 10*mm))

    # 1. 보유 현황
    elements.append(Paragraph('1. 보유 현황', styles['KoreanSubtitle']))

    current_price = float(ohlcv[0]['close']) if ohlcv else 0
    avg_price = float(stock['avg_buy_price']) if stock['avg_buy_price'] else 0
    quantity = stock['quantity'] or 0
    total_cost = float(stock['total_cost']) if stock['total_cost'] else 0
    current_value = current_price * quantity
    profit_loss = current_value - total_cost
    profit_rate = (profit_loss / total_cost * 100) if total_cost > 0 else 0

    holding_data = [
        ['항목', '값'],
        ['보유 수량', f'{quantity:,}주'],
        ['평균 매수가', f'{int(avg_price):,}원'],
        ['현재가', f'{int(current_price):,}원'],
        ['총 매수금액', f'{int(total_cost):,}원'],
        ['평가금액', f'{int(current_value):,}원'],
        ['손익', f'{int(profit_loss):+,}원 ({profit_rate:+.2f}%)'],
    ]

    t = Table(holding_data, colWidths=[80*mm, 80*mm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'NanumGothic'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgreen if profit_loss >= 0 else colors.lightsalmon),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 8*mm))

    # 2. AI 분석 결과
    elements.append(Paragraph('2. AI 분석 결과', styles['KoreanSubtitle']))

    if ai:
        ai_data = [
            ['항목', '내용'],
            ['AI 등급', f'{ai.get("ai_grade", "N/A")}'],
            ['최종 점수', f'{ai.get("final_score", 0):.1f}점'],
            ['정량 점수', f'{ai.get("quant_score", 0):.1f}점'],
            ['정성 점수', f'{ai.get("qual_score", 0):.1f}점'],
        ]

        t = Table(ai_data, colWidths=[50*mm, 110*mm])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'NanumGothic'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph('AI 분석 데이터 없음', styles['Korean']))
    elements.append(Spacer(1, 8*mm))

    # 3. 밸류에이션
    elements.append(Paragraph('3. 밸류에이션', styles['KoreanSubtitle']))

    if fund:
        pbr_val = float(fund.get('pbr') or 0)
        per_val = float(fund.get('per') or 0)
        market_cap = int(fund.get('market_cap') or 0)

        val_data = [
            ['지표', '값', '평가'],
            ['PBR', f'{pbr_val:.2f}', '저평가' if pbr_val < 0.5 else '적정' if pbr_val < 1.0 else '고평가'],
            ['PER', f'{per_val:.2f}', '저평가' if per_val < 10 else '적정' if per_val < 20 else '고평가'],
            ['시가총액', f'{market_cap // 100000000:,}억원', ''],
        ]

        t = Table(val_data, colWidths=[50*mm, 50*mm, 60*mm])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'NanumGothic'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph('밸류에이션 데이터 없음', styles['Korean']))
    elements.append(Spacer(1, 8*mm))

    # 4. 주가 차트
    elements.append(Paragraph('4. 최근 주가 추이 (60일)', styles['KoreanSubtitle']))

    img_buffer = create_stock_chart(ohlcv, avg_price, stock_name)
    if img_buffer:
        elements.append(Image(img_buffer, width=160*mm, height=60*mm))
    elements.append(Spacer(1, 8*mm))

    # 5. 투자 의견
    elements.append(Paragraph('5. 투자 의견', styles['KoreanSubtitle']))

    if ai:
        grade_text = {'S': '강력 매수', 'A': '매수', 'B': '관심', 'C': '중립', 'D': '관망'}.get(ai.get('ai_grade', 'C'), '중립')

        opinion_parts = [
            f'<b>종합 의견:</b> {ai.get("ai_grade", "N/A")}등급 - {grade_text}',
            '',
            f'<b>핵심 투자 포인트:</b>',
            f'{ai.get("ai_key_material", "N/A")}',
            '',
            f'<b>정책 수혜:</b>',
            f'{ai.get("ai_policy_alignment", "N/A")}',
            '',
            f'<b>매수 전략:</b>',
            f'{ai.get("ai_buy_point", "N/A")}',
            '',
            f'<b>리스크 요인:</b>',
            f'{ai.get("ai_risk_factor", "N/A")}',
        ]

        for part in opinion_parts:
            if part:
                elements.append(Paragraph(part, styles['Korean']))
            else:
                elements.append(Spacer(1, 3*mm))

    doc.build(elements)
    return filename


async def generate_requested_stock_pdf(conn, code, stock_name, styles):
    """요청 종목 PDF 생성 (비보유종목 - 평단가/수량 없음)"""
    stock, ohlcv, ai, fund = await get_stock_data(conn, code)

    if not ohlcv:
        print(f'  ⚠️ {stock_name} ({code}) OHLCV 데이터 없음')
        return None

    filename = f'{REPORT_DIR}/{stock_name}.pdf'

    doc = SimpleDocTemplate(filename, pagesize=A4,
                           topMargin=20*mm, bottomMargin=20*mm,
                           leftMargin=15*mm, rightMargin=15*mm)

    elements = []

    # 제목
    elements.append(Paragraph(f'{stock_name} ({code}) 종목 분석 리포트', styles['KoreanTitle']))
    elements.append(Paragraph(f'생성일: {datetime.now().strftime("%Y-%m-%d %H:%M")}', styles['KoreanSmall']))
    elements.append(Paragraph('※ 비보유 종목 (요청 분석)', styles['KoreanSmall']))
    elements.append(Spacer(1, 10*mm))

    # 1. 현재가 정보 (보유현황 대신)
    elements.append(Paragraph('1. 현재가 정보', styles['KoreanSubtitle']))

    current_price = float(ohlcv[0]['close']) if ohlcv else 0
    prev_close = float(ohlcv[1]['close']) if len(ohlcv) > 1 else current_price
    change = current_price - prev_close
    change_rate = (change / prev_close * 100) if prev_close > 0 else 0

    price_data = [
        ['항목', '값'],
        ['현재가', f'{int(current_price):,}원'],
        ['전일대비', f'{int(change):+,}원 ({change_rate:+.2f}%)'],
        ['당일 고가', f'{int(ohlcv[0]["high"]):,}원'],
        ['당일 저가', f'{int(ohlcv[0]["low"]):,}원'],
        ['거래량', f'{int(ohlcv[0]["volume"]):,}주'],
    ]

    t = Table(price_data, colWidths=[80*mm, 80*mm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'NanumGothic'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (1, 2), (1, 2), colors.lightgreen if change >= 0 else colors.lightsalmon),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 8*mm))

    # 2. AI 분석 결과
    elements.append(Paragraph('2. AI 분석 결과', styles['KoreanSubtitle']))

    if ai:
        ai_data = [
            ['항목', '내용'],
            ['AI 등급', f'{ai.get("ai_grade", "N/A")}'],
            ['최종 점수', f'{ai.get("final_score", 0):.1f}점'],
            ['정량 점수', f'{ai.get("quant_score", 0):.1f}점'],
            ['정성 점수', f'{ai.get("qual_score", 0):.1f}점'],
        ]

        t = Table(ai_data, colWidths=[50*mm, 110*mm])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'NanumGothic'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph('AI 분석 데이터 없음', styles['Korean']))
    elements.append(Spacer(1, 8*mm))

    # 3. 밸류에이션
    elements.append(Paragraph('3. 밸류에이션', styles['KoreanSubtitle']))

    if fund:
        pbr_val = float(fund.get('pbr') or 0)
        per_val = float(fund.get('per') or 0)
        market_cap = int(fund.get('market_cap') or 0)

        val_data = [
            ['지표', '값', '평가'],
            ['PBR', f'{pbr_val:.2f}', '저평가' if pbr_val < 0.5 else '적정' if pbr_val < 1.0 else '고평가'],
            ['PER', f'{per_val:.2f}', '저평가' if per_val < 10 else '적정' if per_val < 20 else '고평가'],
            ['시가총액', f'{market_cap // 100000000:,}억원', ''],
        ]

        t = Table(val_data, colWidths=[50*mm, 50*mm, 60*mm])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'NanumGothic'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph('밸류에이션 데이터 없음', styles['Korean']))
    elements.append(Spacer(1, 8*mm))

    # 4. 주가 차트 (평균가 라인 없이)
    elements.append(Paragraph('4. 최근 주가 추이 (60일)', styles['KoreanSubtitle']))

    if ohlcv:
        closes = [float(row['close']) for row in reversed(ohlcv)]

        fig, ax = plt.subplots(figsize=(7, 3))
        ax.plot(range(len(closes)), closes, 'b-', linewidth=1.5)
        ax.fill_between(range(len(closes)), closes, alpha=0.3)
        ax.set_ylabel('Price (KRW)')
        ax.set_title(f'{stock_name} Stock Price (60 days)')
        ax.grid(True, alpha=0.3)

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()

        elements.append(Image(img_buffer, width=160*mm, height=60*mm))
    elements.append(Spacer(1, 8*mm))

    # 5. 투자 의견
    elements.append(Paragraph('5. 투자 의견', styles['KoreanSubtitle']))

    if ai:
        grade_text = {'S': '강력 매수', 'A': '매수', 'B': '관심', 'C': '중립', 'D': '관망'}.get(ai.get('ai_grade', 'C'), '중립')

        opinion_parts = [
            f'<b>종합 의견:</b> {ai.get("ai_grade", "N/A")}등급 - {grade_text}',
            '',
            f'<b>핵심 투자 포인트:</b>',
            f'{ai.get("ai_key_material", "N/A")}',
            '',
            f'<b>정책 수혜:</b>',
            f'{ai.get("ai_policy_alignment", "N/A")}',
            '',
            f'<b>매수 전략:</b>',
            f'{ai.get("ai_buy_point", "N/A")}',
            '',
            f'<b>리스크 요인:</b>',
            f'{ai.get("ai_risk_factor", "N/A")}',
        ]

        for part in opinion_parts:
            if part:
                elements.append(Paragraph(part, styles['Korean']))
            else:
                elements.append(Spacer(1, 3*mm))
    else:
        elements.append(Paragraph('AI 투자 의견 데이터 없음', styles['Korean']))

    doc.build(elements)
    return filename


async def generate_dashboard_pdf(conn, styles):
    """전체 대시보드 PDF 생성"""
    holdings = await get_all_holdings(conn)

    filename = f'{REPORT_DIR}/realtime_dashboard.pdf'
    doc = SimpleDocTemplate(filename, pagesize=landscape(A4),
                           topMargin=15*mm, bottomMargin=15*mm,
                           leftMargin=10*mm, rightMargin=10*mm)

    elements = []

    # 제목
    elements.append(Paragraph('📊 보유종목 실시간 대시보드', styles['KoreanLarge']))
    elements.append(Paragraph(f'생성일시: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', styles['KoreanSmall']))
    elements.append(Spacer(1, 10*mm))

    # 포트폴리오 요약
    total_cost = 0
    total_value = 0
    portfolio_data = []

    for h in holdings:
        code = h['stock_code']
        ohlcv = await conn.fetch('''
            SELECT close FROM daily_ohlcv
            WHERE stock_code = $1 ORDER BY date DESC LIMIT 1
        ''', code)

        current_price = float(ohlcv[0]['close']) if ohlcv else 0
        qty = h['quantity']
        avg_price = float(h['avg_buy_price'])
        cost = float(h['total_cost'])
        value = current_price * qty
        pl = value - cost
        pl_rate = (pl / cost * 100) if cost > 0 else 0

        total_cost += cost
        total_value += value

        # AI 등급
        ai = await conn.fetchrow('''
            SELECT ai_grade FROM smart_recommendations
            WHERE stock_code = $1 ORDER BY created_at DESC LIMIT 1
        ''', code)
        grade = ai['ai_grade'] if ai else '-'

        portfolio_data.append([
            h['stock_name'],
            code,
            f'{qty:,}',
            f'{int(avg_price):,}',
            f'{int(current_price):,}',
            f'{int(cost):,}',
            f'{int(value):,}',
            f'{int(pl):+,}',
            f'{pl_rate:+.1f}%',
            grade
        ])

    total_pl = total_value - total_cost
    total_pl_rate = (total_pl / total_cost * 100) if total_cost > 0 else 0

    # 요약 테이블
    elements.append(Paragraph('포트폴리오 요약', styles['KoreanSubtitle']))

    summary_data = [
        ['총 투자금액', '총 평가금액', '총 손익', '수익률'],
        [f'{int(total_cost):,}원', f'{int(total_value):,}원',
         f'{int(total_pl):+,}원', f'{total_pl_rate:+.2f}%']
    ]

    t = Table(summary_data, colWidths=[65*mm, 65*mm, 65*mm, 65*mm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'NanumGothic'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (2, 1), (3, 1), colors.lightgreen if total_pl >= 0 else colors.lightsalmon),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10*mm))

    # 종목별 상세
    elements.append(Paragraph('종목별 상세 현황', styles['KoreanSubtitle']))

    header = ['종목명', '코드', '수량', '평단가', '현재가', '매수금액', '평가금액', '손익', '수익률', 'AI등급']
    table_data = [header] + portfolio_data

    t = Table(table_data, colWidths=[35*mm, 20*mm, 18*mm, 25*mm, 25*mm, 30*mm, 30*mm, 28*mm, 20*mm, 18*mm])

    style_commands = [
        ('FONTNAME', (0, 0), (-1, -1), 'NanumGothic'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]

    # 손익에 따라 행 색상 적용
    for i, row in enumerate(portfolio_data, 1):
        pl_str = row[7].replace(',', '').replace('+', '')
        try:
            pl_val = int(pl_str)
            if pl_val >= 0:
                style_commands.append(('BACKGROUND', (7, i), (8, i), colors.Color(0.9, 1, 0.9)))
            else:
                style_commands.append(('BACKGROUND', (7, i), (8, i), colors.Color(1, 0.9, 0.9)))
        except:
            pass

    t.setStyle(TableStyle(style_commands))
    elements.append(t)
    elements.append(Spacer(1, 10*mm))

    # 포트폴리오 파이 차트
    elements.append(PageBreak())
    elements.append(Paragraph('포트폴리오 구성', styles['KoreanSubtitle']))

    names = [h['stock_name'] for h in holdings]
    values = [float(h['total_cost']) for h in holdings]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # 비중 파이 차트
    ax1.pie(values, labels=names, autopct='%1.1f%%', startangle=90)
    ax1.set_title('Portfolio Allocation')

    # 손익 바 차트
    pls = []
    for h in holdings:
        code = h['stock_code']
        ohlcv = await conn.fetchval('''
            SELECT close FROM daily_ohlcv
            WHERE stock_code = $1 ORDER BY date DESC LIMIT 1
        ''', code)
        current = float(ohlcv) if ohlcv else 0
        cost = float(h['total_cost'])
        value = current * h['quantity']
        pls.append(value - cost)

    colors_bar = ['green' if p >= 0 else 'red' for p in pls]
    ax2.barh(names, pls, color=colors_bar)
    ax2.axvline(x=0, color='black', linewidth=0.5)
    ax2.set_title('Profit/Loss by Stock')
    ax2.set_xlabel('P/L (KRW)')

    plt.tight_layout()

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    img_buffer.seek(0)
    plt.close()

    elements.append(Image(img_buffer, width=250*mm, height=100*mm))

    doc.build(elements)
    return filename


async def main():
    """메인 실행"""
    print('=== 보유종목 PDF 리포트 생성 시작 ===\n')

    os.makedirs(REPORT_DIR, exist_ok=True)

    conn = await asyncpg.connect(DB_URL)
    styles = get_styles()

    try:
        # 1. 보유종목 조회
        holdings = await get_all_holdings(conn)
        holding_names = {h['stock_name'] for h in holdings}
        print(f'보유종목: {len(holdings)}개')

        # 2. 요청 종목 조회
        requested_stocks = get_requested_stocks()
        # 이미 보유 중인 종목은 제외
        requested_stocks = [s for s in requested_stocks if s not in holding_names]
        print(f'요청종목: {len(requested_stocks)}개 (비보유)\n')

        # 3. 보유종목 개별 PDF 생성
        print('[1/3] 보유종목 PDF 생성')
        for h in holdings:
            code = h['stock_code']
            name = h['stock_name']
            print(f'  생성 중: {name} ({code})...', end=' ')

            result = await generate_individual_pdf(conn, code, styles)
            if result:
                print(f'✅')
            else:
                print(f'⚠️ 실패')

        # 4. 요청종목 개별 PDF 생성
        if requested_stocks:
            print(f'\n[2/3] 요청종목 PDF 생성 (비보유)')
            for stock_name in requested_stocks:
                stock_info = await get_stock_code_by_name(conn, stock_name)
                if stock_info:
                    code = stock_info['stock_code']
                    print(f'  생성 중: {stock_name} ({code})...', end=' ')
                    result = await generate_requested_stock_pdf(conn, code, stock_name, styles)
                    if result:
                        print(f'✅')
                    else:
                        print(f'⚠️ 실패')
                else:
                    print(f'  ⚠️ {stock_name}: 종목을 찾을 수 없음')

        # 5. 대시보드 PDF 생성
        print(f'\n[3/3] 대시보드 PDF 생성...', end=' ')
        dashboard = await generate_dashboard_pdf(conn, styles)
        print(f'✅')

        print(f'\n=== 완료 ===')
        print(f'생성 위치: {os.path.abspath(REPORT_DIR)}/')
        print(f'- 보유종목 리포트: {len(holdings)}개')
        print(f'- 요청종목 리포트: {len(requested_stocks)}개')
        print(f'- 대시보드: realtime_dashboard.pdf')

    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
