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
import sys
from pathlib import Path
import pandas as pd

# AEGIS 신호 시스템 임포트
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.aegis.analysis.signal import Signal, calculate_signal_score, score_to_signal

# 한글 폰트 등록
pdfmetrics.registerFont(TTFont('NanumGothic', '/System/Library/Fonts/Supplemental/AppleGothic.ttf'))

# matplotlib 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

DB_URL = 'postgresql://wonny@localhost:5432/stock_investment_db'
REPORT_DIR = 'reports/holding_stock'
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


async def save_aegis_signal_history(conn, stock_code: str, detail: dict, signal_type: str):
    """AEGIS 강매수/강매도 신호를 DB에 저장 (시간당 1회만)"""
    try:
        await conn.execute('''
            INSERT INTO aegis_signal_history
            (stock_code, stock_name, signal_type, signal_score, current_price,
             ma_score, vwap_score, rsi_score, ma_reason, vwap_reason, rsi_reason)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (stock_code, signal_type, DATE(recorded_at), EXTRACT(HOUR FROM recorded_at))
            DO NOTHING
        ''', stock_code, detail['name'], signal_type, detail['total_score'],
            detail['current_price'], detail['ma_score'], detail['vwap_score'],
            detail['rsi_score'], detail['ma_reason'], detail['vwap_reason'], detail['rsi_reason'])
    except Exception as e:
        # 중복 시 무시
        pass


async def get_aegis_signal_history(conn, limit: int = 20):
    """최근 AEGIS 신호 히스토리 조회"""
    return await conn.fetch('''
        SELECT stock_code, stock_name, signal_type, signal_score, current_price,
               ma_reason, vwap_reason, rsi_reason, recorded_at
        FROM aegis_signal_history
        ORDER BY recorded_at DESC
        LIMIT $1
    ''', limit)


async def get_aegis_signal(conn, stock_code: str) -> dict:
    """
    AEGIS 신호 계산 (일봉 데이터 기반)
    Returns: dict with signal info and details
    """
    try:
        rows = await conn.fetch('''
            SELECT date, open, high, low, close, volume
            FROM daily_ohlcv
            WHERE stock_code = $1
            ORDER BY date DESC
            LIMIT 100
        ''', stock_code)

        if not rows or len(rows) < 60:
            return {
                'text': "-",
                'color': colors.grey,
                'total_score': 0,
                'ma_score': 0,
                'vwap_score': 0,
                'rsi_score': 0,
                'ma_reason': "데이터 부족",
                'vwap_reason': "데이터 부족",
                'rsi_reason': "데이터 부족",
                'close': 0,
                'rsi': 0,
                'vwap': 0,
                'ma_5': 0,
                'ma_20': 0,
                'ma_60': 0,
            }

        df = pd.DataFrame([dict(r) for r in rows])
        df = df.sort_values('date').reset_index(drop=True)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        scored_df = calculate_signal_score(df)
        latest = scored_df.iloc[-1]
        total_score = int(latest['total_score'])
        ma_score = int(latest['ma_score'])
        vwap_score = int(latest['vwap_score'])
        rsi_score = int(latest['rsi_score'])
        signal = score_to_signal(total_score)

        # 텍스트 + 색상 매핑
        signal_map = {
            Signal.STRONG_BUY: ("강매수", colors.red),
            Signal.BUY: ("매수", colors.orangered),
            Signal.HOLD: ("관망", colors.grey),
            Signal.SELL: ("매도", colors.blue),
            Signal.STRONG_SELL: ("강매도", colors.darkblue),
        }
        text, color = signal_map.get(signal, ("관망", colors.grey))
        score_str = f"({total_score:+d})"

        # MA 판단 이유
        if ma_score > 0:
            ma_reason = "정배열 (5>20>60)"
        elif ma_score < 0:
            ma_reason = "역배열 (5<20<60)"
        else:
            ma_reason = "중립"

        # VWAP 판단 이유
        close = float(latest['close'])
        vwap = float(latest['vwap']) if not pd.isna(latest['vwap']) else close
        if vwap_score > 0:
            vwap_reason = f"VWAP 지지 ({close:,.0f}>{vwap:,.0f})"
        elif vwap_score < 0:
            vwap_reason = f"VWAP 이탈 ({close:,.0f}<{vwap:,.0f})"
        else:
            vwap_reason = "중립"

        # RSI 판단 이유
        rsi = float(latest['rsi']) if not pd.isna(latest['rsi']) else 50
        if rsi_score > 0:
            rsi_reason = f"과매도 (RSI {rsi:.0f}<30)"
        elif rsi_score < 0:
            rsi_reason = f"과매수 (RSI {rsi:.0f}>70)"
        else:
            rsi_reason = f"중립 (RSI {rsi:.0f})"

        return {
            'text': f"{text}{score_str}",
            'color': color,
            'total_score': total_score,
            'ma_score': ma_score,
            'vwap_score': vwap_score,
            'rsi_score': rsi_score,
            'ma_reason': ma_reason,
            'vwap_reason': vwap_reason,
            'rsi_reason': rsi_reason,
            'close': close,
            'rsi': rsi,
            'vwap': vwap,
            'ma_5': float(latest['ma_5']) if not pd.isna(latest['ma_5']) else 0,
            'ma_20': float(latest['ma_20']) if not pd.isna(latest['ma_20']) else 0,
            'ma_60': float(latest['ma_60']) if not pd.isna(latest['ma_60']) else 0,
        }

    except Exception as e:
        return {
            'text': "ERR",
            'color': colors.grey,
            'total_score': 0,
            'ma_score': 0,
            'vwap_score': 0,
            'rsi_score': 0,
            'ma_reason': str(e)[:20],
            'vwap_reason': "-",
            'rsi_reason': "-",
            'close': 0,
            'rsi': 0,
            'vwap': 0,
            'ma_5': 0,
            'ma_20': 0,
            'ma_60': 0,
        }


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
    """요청 종목 PDF 생성 (비보유종목 - 보유종목과 동일 양식, 평단가/수량만 0)"""
    stock, ohlcv, ai, fund = await get_stock_data(conn, code)

    if not ohlcv:
        print(f'  ⚠️ {stock_name} ({code}) OHLCV 데이터 없음')
        return None

    filename = f'{REPORT_DIR}/{stock_name}.pdf'

    doc = SimpleDocTemplate(filename, pagesize=A4,
                           topMargin=20*mm, bottomMargin=20*mm,
                           leftMargin=15*mm, rightMargin=15*mm)

    elements = []

    # 제목 (보유종목과 동일)
    elements.append(Paragraph(f'{stock_name} ({code}) 투자 리포트', styles['KoreanTitle']))
    elements.append(Paragraph(f'생성일: {datetime.now().strftime("%Y-%m-%d %H:%M")}', styles['KoreanSmall']))
    elements.append(Spacer(1, 10*mm))

    # 1. 보유 현황 (보유종목과 동일 양식, 값만 0/-)
    elements.append(Paragraph('1. 보유 현황', styles['KoreanSubtitle']))

    current_price = float(ohlcv[0]['close']) if ohlcv else 0
    avg_price = 0  # 비보유종목
    quantity = 0  # 비보유종목
    total_cost = 0  # 비보유종목
    current_value = 0  # 비보유종목
    profit_loss = 0  # 비보유종목
    profit_rate = 0  # 비보유종목

    holding_data = [
        ['항목', '값'],
        ['보유 수량', '-'],
        ['평균 매수가', '-'],
        ['현재가', f'{int(current_price):,}원'],
        ['총 매수금액', '-'],
        ['평가금액', '-'],
        ['손익', '-'],
    ]

    t = Table(holding_data, colWidths=[80*mm, 80*mm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'NanumGothic'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),  # 비보유종목은 회색
    ]))
    elements.append(t)
    elements.append(Spacer(1, 8*mm))

    # 2. AI 분석 결과 (보유종목과 동일)
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

    # 3. 밸류에이션 (보유종목과 동일)
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

    # 4. 주가 차트 (보유종목과 동일 - 평균가 라인 없이)
    elements.append(Paragraph('4. 최근 주가 추이 (60일)', styles['KoreanSubtitle']))

    img_buffer = create_stock_chart(ohlcv, 0, stock_name)  # avg_price=0이면 라인 안 보임
    if img_buffer:
        elements.append(Image(img_buffer, width=160*mm, height=60*mm))
    elements.append(Spacer(1, 8*mm))

    # 5. 투자 의견 (보유종목과 동일)
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
    elements.append(Paragraph(f'업데이트 시간: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', styles['KoreanSmall']))
    elements.append(Spacer(1, 5*mm))  # Spacer 축소

    # 포트폴리오 요약
    total_cost = 0
    total_value = 0
    portfolio_data = []
    price_changes = []  # 전일 대비 등락 정보 저장
    aegis_colors = []   # AEGIS 신호 색상 저장
    aegis_details = []  # AEGIS 판단 근거 저장

    for h in holdings:
        code = h['stock_code']
        # min_ticks에서 최신 실시간 가격 조회 (1분 스크립트에서 수집)
        tick = await conn.fetchrow('''
            SELECT price FROM min_ticks
            WHERE stock_code = $1
            ORDER BY timestamp DESC LIMIT 1
        ''', code)

        # min_ticks에 데이터가 없으면 daily_ohlcv fallback
        if tick:
            current_price = float(tick['price'])
        else:
            ohlcv = await conn.fetchrow('''
                SELECT close FROM daily_ohlcv
                WHERE stock_code = $1 ORDER BY date DESC LIMIT 1
            ''', code)
            current_price = float(ohlcv['close']) if ohlcv else 0

        # 전일 종가 조회 (등락률 계산용)
        prev_close = await conn.fetchval('''
            SELECT close FROM daily_ohlcv
            WHERE stock_code = $1
            ORDER BY date DESC LIMIT 1
        ''', code)
        prev_close = float(prev_close) if prev_close else current_price

        # 전일 대비 등락률
        change_rate = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0
        price_changes.append(change_rate)

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

        # AEGIS 신호 계산
        aegis_info = await get_aegis_signal(conn, code)

        # 현재가에 등락률 표시 (한 줄로 - 행 높이 축소)
        change_str = f'{change_rate:+.1f}%'
        current_price_display = f'{int(current_price):,} ({change_str})'

        portfolio_data.append([
            h['stock_name'],
            code,
            f'{qty:,}',
            f'{int(avg_price):,}',
            current_price_display,
            f'{int(cost):,}',
            f'{int(value):,}',
            f'{int(pl):+,}',
            f'{pl_rate:+.1f}%',
            grade,
            aegis_info['text']
        ])

        # AEGIS 색상 저장 (테이블 스타일에서 사용)
        aegis_colors.append(aegis_info['color'])

        # AEGIS 상세 정보 저장 (판단 근거 테이블용)
        aegis_details.append({
            'code': code,
            'name': h['stock_name'],
            'signal': aegis_info['text'],
            'color': aegis_info['color'],
            'total_score': aegis_info['total_score'],
            'ma_score': aegis_info['ma_score'],
            'vwap_score': aegis_info['vwap_score'],
            'rsi_score': aegis_info['rsi_score'],
            'ma_reason': aegis_info['ma_reason'],
            'vwap_reason': aegis_info['vwap_reason'],
            'rsi_reason': aegis_info['rsi_reason'],
            'current_price': int(current_price),
        })

    total_pl = total_value - total_cost
    total_pl_rate = (total_pl / total_cost * 100) if total_cost > 0 else 0

    # 요약 테이블 (컴팩트)
    elements.append(Paragraph('포트폴리오 요약', styles['KoreanSubtitle']))

    summary_data = [
        ['총 투자금액', '총 평가금액', '총 손익', '수익률'],
        [f'{int(total_cost):,}원', f'{int(total_value):,}원',
         f'{int(total_pl):+,}원', f'{total_pl_rate:+.2f}%']
    ]

    t = Table(summary_data, colWidths=[60*mm, 60*mm, 60*mm, 60*mm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'NanumGothic'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # 폰트 축소
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (2, 1), (3, 1), colors.lightgreen if total_pl >= 0 else colors.lightsalmon),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 5*mm))  # Spacer 축소

    # 종목별 상세
    elements.append(Paragraph('종목별 상세 현황', styles['KoreanSubtitle']))

    header = ['종목명', '코드', '수량', '평단가', '현재가', '매수금액', '평가금액', '손익', '수익률', 'AI등급', 'AEGIS']
    table_data = [header] + portfolio_data

    # 컬럼 너비 조정 (총 255mm로 확장)
    # 종목명 28 + 코드 16 + 수량 13 + 평단가 18 + 현재가 36 + 매수금액 26 + 평가금액 26 + 손익 24 + 수익률 18 + AI등급 16 + AEGIS 16 = 237mm
    t = Table(table_data, colWidths=[28*mm, 16*mm, 13*mm, 18*mm, 36*mm, 26*mm, 26*mm, 24*mm, 18*mm, 16*mm, 16*mm])

    style_commands = [
        ('FONTNAME', (0, 0), (-1, -1), 'NanumGothic'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # 폰트 8pt
        ('FONTSIZE', (0, 0), (-1, 0), 8),   # 헤더도 동일
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # 헤더는 가운데
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),    # 종목명은 좌측
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # 코드는 가운데
        ('ALIGN', (2, 1), (-3, -1), 'RIGHT'),  # 숫자 컬럼들 우측정렬 (수량~수익률)
        ('ALIGN', (-2, 1), (-1, -1), 'CENTER'), # AI등급, AEGIS는 가운데
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
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

    # 현재가 셀 색상 적용 (전일 대비: 상승=빨강, 하락=파랑)
    for i, change in enumerate(price_changes, 1):
        if change > 0:
            style_commands.append(('TEXTCOLOR', (4, i), (4, i), colors.red))
        elif change < 0:
            style_commands.append(('TEXTCOLOR', (4, i), (4, i), colors.blue))

    # AEGIS 신호 색상 적용 (마지막 컬럼)
    for i, aegis_color in enumerate(aegis_colors, 1):
        style_commands.append(('TEXTCOLOR', (-1, i), (-1, i), aegis_color))

    t.setStyle(TableStyle(style_commands))
    elements.append(t)
    elements.append(Spacer(1, 8*mm))

    # AEGIS 판단 근거 테이블
    elements.append(Paragraph('🛡️ AEGIS 신호 판단 근거', styles['KoreanSubtitle']))
    elements.append(Spacer(1, 2*mm))

    # 점수 체계 설명
    score_legend = Paragraph(
        '<font size="7" color="gray">'
        '점수체계: MA정배열(+1)/역배열(-1) | VWAP지지(+1)/이탈(-1) | RSI과매도(+1)/과매수(-1) → '
        '합계 ≥+2:강매수, +1:매수, 0:관망, -1:매도, ≤-2:강매도'
        '</font>',
        styles['Korean']
    )
    elements.append(score_legend)
    elements.append(Spacer(1, 3*mm))

    # AEGIS 상세 테이블
    aegis_header = ['종목명', '신호', 'MA', 'VWAP', 'RSI', 'MA 판단근거', 'VWAP 판단근거', 'RSI 판단근거']
    aegis_table_data = [aegis_header]

    for detail in aegis_details:
        # 점수를 문자열로 변환 (+1, -1, 0)
        ma_str = f"{detail['ma_score']:+d}" if detail['ma_score'] != 0 else "0"
        vwap_str = f"{detail['vwap_score']:+d}" if detail['vwap_score'] != 0 else "0"
        rsi_str = f"{detail['rsi_score']:+d}" if detail['rsi_score'] != 0 else "0"

        aegis_table_data.append([
            detail['name'],
            detail['signal'],
            ma_str,
            vwap_str,
            rsi_str,
            detail['ma_reason'],
            detail['vwap_reason'],
            detail['rsi_reason'],
        ])

    # 컬럼 너비: 종목명 24 + 신호 18 + MA 10 + VWAP 10 + RSI 10 + MA근거 40 + VWAP근거 45 + RSI근거 40 = 197mm
    aegis_t = Table(aegis_table_data, colWidths=[24*mm, 18*mm, 10*mm, 10*mm, 10*mm, 40*mm, 45*mm, 40*mm])

    aegis_style_commands = [
        ('FONTNAME', (0, 0), (-1, -1), 'NanumGothic'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.3, 0.4)),  # 진한 회색-파랑
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),   # 종목명 좌측
        ('ALIGN', (1, 1), (4, -1), 'CENTER'), # 신호, MA, VWAP, RSI 가운데
        ('ALIGN', (5, 1), (-1, -1), 'LEFT'),  # 판단근거 좌측
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]

    # 신호 컬럼 색상 적용
    for i, detail in enumerate(aegis_details, 1):
        aegis_style_commands.append(('TEXTCOLOR', (1, i), (1, i), detail['color']))
        # MA 점수 색상
        if detail['ma_score'] > 0:
            aegis_style_commands.append(('TEXTCOLOR', (2, i), (2, i), colors.red))
        elif detail['ma_score'] < 0:
            aegis_style_commands.append(('TEXTCOLOR', (2, i), (2, i), colors.blue))
        # VWAP 점수 색상
        if detail['vwap_score'] > 0:
            aegis_style_commands.append(('TEXTCOLOR', (3, i), (3, i), colors.red))
        elif detail['vwap_score'] < 0:
            aegis_style_commands.append(('TEXTCOLOR', (3, i), (3, i), colors.blue))
        # RSI 점수 색상
        if detail['rsi_score'] > 0:
            aegis_style_commands.append(('TEXTCOLOR', (4, i), (4, i), colors.red))
        elif detail['rsi_score'] < 0:
            aegis_style_commands.append(('TEXTCOLOR', (4, i), (4, i), colors.blue))

    aegis_t.setStyle(TableStyle(aegis_style_commands))
    elements.append(aegis_t)
    elements.append(Spacer(1, 8*mm))

    # 강매수/강매도 종목 하이라이트
    strong_buy_list = [d for d in aegis_details if d['total_score'] >= 2]
    strong_sell_list = [d for d in aegis_details if d['total_score'] <= -2]
    current_time = datetime.now().strftime("%H:%M")

    # 강매수/강매도 신호 DB에 저장
    for item in strong_buy_list:
        await save_aegis_signal_history(conn, item['code'], item, 'STRONG_BUY')
    for item in strong_sell_list:
        await save_aegis_signal_history(conn, item['code'], item, 'STRONG_SELL')

    # 현재 강매수/강매도 테이블
    if strong_buy_list or strong_sell_list:
        elements.append(Paragraph('⚠️ 주요 신호 종목 (현재)', styles['KoreanSubtitle']))
        elements.append(Spacer(1, 2*mm))

        # 강매수 종목
        if strong_buy_list:
            elements.append(Paragraph(
                f'<font color="red"><b>🔴 강력매수 신호 ({current_time} 기준)</b></font>',
                styles['Korean']
            ))
            strong_buy_data = [['종목명', '현재가', '신호', '시간']]
            for item in strong_buy_list:
                strong_buy_data.append([
                    item['name'],
                    f"{item['current_price']:,}원",
                    item['signal'],
                    current_time
                ])

            sb_table = Table(strong_buy_data, colWidths=[40*mm, 35*mm, 25*mm, 20*mm])
            sb_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'NanumGothic'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (-1, 0), colors.red),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('BACKGROUND', (0, 1), (-1, -1), colors.Color(1, 0.9, 0.9)),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(sb_table)
            elements.append(Spacer(1, 5*mm))

        # 강매도 종목
        if strong_sell_list:
            elements.append(Paragraph(
                f'<font color="darkblue"><b>🔵 강력매도 신호 ({current_time} 기준)</b></font>',
                styles['Korean']
            ))
            strong_sell_data = [['종목명', '현재가', '신호', '시간']]
            for item in strong_sell_list:
                strong_sell_data.append([
                    item['name'],
                    f"{item['current_price']:,}원",
                    item['signal'],
                    current_time
                ])

            ss_table = Table(strong_sell_data, colWidths=[40*mm, 35*mm, 25*mm, 20*mm])
            ss_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'NanumGothic'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.9, 0.9, 1)),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(ss_table)

        elements.append(Spacer(1, 8*mm))

    # 신호 히스토리 테이블
    signal_history = await get_aegis_signal_history(conn, limit=20)
    if signal_history:
        elements.append(Paragraph('📜 주요 신호 히스토리 (최근 20건)', styles['KoreanSubtitle']))
        elements.append(Spacer(1, 2*mm))

        history_data = [['시간', '종목명', '신호', '현재가', '판단근거']]
        for row in signal_history:
            time_str = row['recorded_at'].strftime("%m/%d %H:%M")
            signal_text = "강매수" if row['signal_type'] == 'STRONG_BUY' else "강매도"
            # 판단근거 요약 (MA/VWAP/RSI 중 점수 있는 것만)
            reasons = []
            if 'MA' in row['ma_reason'] or '배열' in row['ma_reason']:
                reasons.append(row['ma_reason'][:15])
            if 'VWAP' in row['vwap_reason']:
                reasons.append(row['vwap_reason'][:15])
            if 'RSI' in row['rsi_reason']:
                reasons.append(row['rsi_reason'][:12])
            reason_str = " / ".join(reasons) if reasons else "-"

            history_data.append([
                time_str,
                row['stock_name'],
                f"{signal_text}({row['signal_score']:+d})",
                f"{row['current_price']:,}원",
                reason_str
            ])

        # 컬럼 너비: 시간 25 + 종목명 30 + 신호 22 + 현재가 28 + 판단근거 90 = 195mm
        hist_table = Table(history_data, colWidths=[25*mm, 30*mm, 22*mm, 28*mm, 90*mm])
        hist_style = [
            ('FONTNAME', (0, 0), (-1, -1), 'NanumGothic'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.3, 0.3, 0.3)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # 시간 가운데
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # 종목명 좌측
            ('ALIGN', (2, 1), (3, -1), 'CENTER'),  # 신호, 현재가 가운데
            ('ALIGN', (4, 1), (4, -1), 'LEFT'),    # 판단근거 좌측
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]

        # 신호 타입별 색상 적용
        for i, row in enumerate(signal_history, 1):
            if row['signal_type'] == 'STRONG_BUY':
                hist_style.append(('TEXTCOLOR', (2, i), (2, i), colors.red))
                hist_style.append(('BACKGROUND', (0, i), (-1, i), colors.Color(1, 0.95, 0.95)))
            else:
                hist_style.append(('TEXTCOLOR', (2, i), (2, i), colors.darkblue))
                hist_style.append(('BACKGROUND', (0, i), (-1, i), colors.Color(0.95, 0.95, 1)))

        hist_table.setStyle(TableStyle(hist_style))
        elements.append(hist_table)
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

    # 손익 바 차트 (min_ticks 실시간 가격 사용)
    pls = []
    for h in holdings:
        code = h['stock_code']
        # min_ticks에서 최신 실시간 가격 조회
        tick = await conn.fetchval('''
            SELECT price FROM min_ticks
            WHERE stock_code = $1
            ORDER BY timestamp DESC LIMIT 1
        ''', code)
        if tick:
            current = float(tick)
        else:
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
