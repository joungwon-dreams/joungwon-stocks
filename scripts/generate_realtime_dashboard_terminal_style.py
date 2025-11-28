#!/usr/bin/env python3
"""
터미널 스타일 실시간 보유종목 대시보드 PDF 생성
watch_*.sh 스크립트의 터미널 출력 형식을 PDF로 변환
"""
import asyncio
import asyncpg
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, Preformatted, Image
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
import matplotlib
matplotlib.use('Agg')  # 백엔드 설정 (GUI 없이)
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
import sys

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

# AEGIS 모듈 임포트
from src.aegis.analysis.signal import Signal, calculate_signal_score, score_to_signal

# matplotlib 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

# 한글 폰트 등록
FONT_PATH = '/System/Library/Fonts/Supplemental/AppleGothic.ttf'
pdfmetrics.registerFont(TTFont('AppleGothic', FONT_PATH))

# 색상 정의
COLOR_RED = colors.red
COLOR_BLUE = colors.blue
COLOR_BLACK = colors.black

# 데이터베이스 설정
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_investment_db',
    'user': 'wonny'
}


async def get_stock_detail_data(stock_code: str, stock_name: str, limit_count=20):
    """특정 종목의 상세 데이터 조회"""
    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # 보유 정보 조회
        holding_query = '''
            SELECT quantity, avg_buy_price, total_value
            FROM stock_assets
            WHERE stock_code = $1 AND quantity > 0
        '''
        holding = await conn.fetchrow(holding_query, stock_code)

        # 오늘 데이터 조회 (min_ticks 테이블)
        today_query = '''
            SELECT
                MIN(price) as today_low,
                MAX(price) as today_high,
                COUNT(*) as today_count
            FROM min_ticks
            WHERE stock_code = $1
              AND DATE(timestamp) = CURRENT_DATE
        '''
        today_stats = await conn.fetchrow(today_query, stock_code)

        # 시가 (오늘 첫 데이터)
        open_query = '''
            SELECT price
            FROM min_ticks
            WHERE stock_code = $1
              AND DATE(timestamp) = CURRENT_DATE
            ORDER BY timestamp ASC
            LIMIT 1
        '''
        open_row = await conn.fetchrow(open_query, stock_code)
        today_open = int(open_row['price']) if open_row else 0

        # 전일 종가 (어제 마지막 데이터) - 먼저 조회
        prev_query = '''
            SELECT price
            FROM min_ticks
            WHERE stock_code = $1
              AND DATE(timestamp) = CURRENT_DATE - INTERVAL '1 day'
            ORDER BY timestamp DESC
            LIMIT 1
        '''
        prev_row = await conn.fetchrow(prev_query, stock_code)
        prev_close = int(prev_row['price']) if prev_row else 0

        # 현재 시각 확인 (장 개시 전: 08:50 이전)
        now = datetime.now()
        market_open_time = now.replace(hour=8, minute=50, second=0, microsecond=0)
        is_before_market_open = now < market_open_time

        # 현재가 (최신 데이터)
        current_query = '''
            SELECT price, volume, change_rate, timestamp
            FROM min_ticks
            WHERE stock_code = $1
              AND DATE(timestamp) = CURRENT_DATE
            ORDER BY timestamp DESC
            LIMIT 1
        '''
        current_row = await conn.fetchrow(current_query, stock_code)

        # 장 개시 전이면 전일 종가 사용
        if is_before_market_open or not current_row:
            current_price = prev_close
            current_volume = 0
            current_change_rate = 0.0
            current_time = now
        else:
            current_price = int(current_row['price'])
            current_volume = int(current_row['volume'])
            current_change_rate = float(current_row['change_rate'])
            current_time = current_row['timestamp']

        # 최근 N개 틱 데이터 조회
        ticks_query = '''
            SELECT
                timestamp,
                price,
                volume,
                change_rate,
                LAG(price, 1) OVER (ORDER BY timestamp) as prev_price,
                LAG(volume, 1) OVER (ORDER BY timestamp) as prev_volume
            FROM min_ticks
            WHERE stock_code = $1
              AND DATE(timestamp) = CURRENT_DATE
            ORDER BY timestamp DESC
            LIMIT $2
        '''
        ticks = await conn.fetch(ticks_query, stock_code, limit_count)

        return {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'holding': holding,
            'today_low': int(today_stats['today_low']) if today_stats['today_low'] else 0,
            'today_high': int(today_stats['today_high']) if today_stats['today_high'] else 0,
            'today_count': today_stats['today_count'] or 0,
            'today_open': today_open,
            'current_price': current_price,
            'current_volume': current_volume,
            'current_change_rate': current_change_rate,
            'current_time': current_time,
            'prev_close': prev_close,
            'ticks': ticks
        }

    finally:
        await conn.close()


# async def get_recent_news(stock_code: str, limit=5):
#     """최근 뉴스 조회"""
#     conn = await asyncpg.connect(**DB_CONFIG)
#
#     try:
#         query = '''
#             SELECT
#                 title,
#                 published_at,
#                 publisher,
#                 source_url,
#                 sentiment
#             FROM stock_news
#             WHERE stock_code = $1
#             ORDER BY published_at DESC
#             LIMIT $2
#         '''
#         news = await conn.fetch(query, stock_code, limit)
#         return [dict(row) for row in news]
#
#     finally:
#         await conn.close()


async def get_all_holdings():
    """모든 보유종목 목록 조회 (평가금액 높은 순)"""
    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        query = '''
            WITH latest_prices AS (
                SELECT DISTINCT ON (stock_code)
                    stock_code,
                    price
                FROM min_ticks
                ORDER BY stock_code, timestamp DESC
            )
            SELECT
                sa.stock_code,
                sa.stock_name,
                (lp.price * sa.quantity) AS current_value
            FROM stock_assets sa
            JOIN latest_prices lp ON sa.stock_code = lp.stock_code
            WHERE sa.quantity > 0
            ORDER BY (lp.price * sa.quantity) DESC
        '''
        rows = await conn.fetch(query)
        return rows

    finally:
        await conn.close()


def format_number(num):
    """숫자 천단위 콤마 포맷"""
    if num is None:
        return "0"
    return f"{int(num):,}"


def calc_change_emoji(current, base):
    """변동률 계산 및 이모지 반환"""
    if base == 0 or base is None:
        return "N/A", ""

    change = ((current - base) / base) * 100

    if change > 0:
        return f"+{change:.2f}%", "🔺"
    elif change < 0:
        return f"{change:.2f}%", "🔹"
    else:
        return "0.00%", "⚪"


def create_terminal_style_content(data):
    """터미널 스타일 텍스트 생성"""
    lines = []

    # 헤더
    lines.append("━" * 80)
    now = datetime.now()
    lines.append(f"📊 {data['stock_name']} ({data['stock_code']}) ⏰ {now.strftime('%Y-%m-%d %H:%M')}  (수집: {data['today_count']})")
    lines.append("━" * 80)

    # 가격 정보
    current_change, current_emoji = calc_change_emoji(data['current_price'], data['prev_close'])
    high_change, high_emoji = calc_change_emoji(data['today_high'], data['prev_close'])
    low_change, low_emoji = calc_change_emoji(data['today_low'], data['prev_close'])

    lines.append(f"시가: {format_number(data['today_open'])} | 현재가: {format_number(data['current_price'])} {current_change} {current_emoji} | 거래량: {format_number(data['current_volume'])}")
    lines.append(f"최고: {format_number(data['today_high'])} {high_change} {high_emoji} | 최저: {format_number(data['today_low'])} {low_change} {low_emoji}")

    # 보유 정보
    if data['holding']:
        quantity = int(data['holding']['quantity'])
        avg_price = int(data['holding']['avg_buy_price'])
        eval_amount = data['current_price'] * quantity
        holding_amount = avg_price * quantity
        profit = eval_amount - holding_amount
        profit_rate = ((data['current_price'] - avg_price) / avg_price) * 100

        if profit_rate > 0:
            profit_sign = "+"
            profit_emoji = "🔺"
        elif profit_rate < 0:
            profit_sign = ""
            profit_emoji = "🔹"
        else:
            profit_sign = ""
            profit_emoji = "⚪"

        lines.append(f"평단가: {format_number(avg_price)} {profit_sign}{profit_rate:.2f}%{profit_emoji} {format_number(quantity)}주 | {format_number(eval_amount)} {profit_sign}{format_number(abs(profit))}원{profit_emoji}")

    lines.append("━" * 80)

    # 테이블 헤더
    lines.append(f"{'시간':^8}  {'현재가':>10}  {'거래량':>12}  {'직전':>10}  {'변동률':>10}  {'전일':>10}  {'전일률':>10}  {'평단가':>10}  {'평가율':>10}")
    lines.append("-" * 120)

    # 틱 데이터
    for tick in data['ticks']:
        time_str = tick['timestamp'].strftime('%H:%M')
        price = int(tick['price'])
        volume = int(tick['volume'])
        prev_price = int(tick['prev_price']) if tick['prev_price'] else price

        # 직전 대비
        price_diff = price - prev_price
        if price_diff > 0:
            diff_str = f"+{format_number(price_diff)}🔺"
            pct_str = f"+{((price / prev_price - 1) * 100):.2f}%"
        elif price_diff < 0:
            diff_str = f"{format_number(price_diff)}🔹"
            pct_str = f"{((price / prev_price - 1) * 100):.2f}%"
        else:
            diff_str = "0⚪"
            pct_str = "0.00%"

        # 전일 대비
        prev_diff = price - data['prev_close']
        if prev_diff > 0:
            prev_diff_str = f"+{format_number(prev_diff)}🔺"
        elif prev_diff < 0:
            prev_diff_str = f"{format_number(prev_diff)}🔹"
        else:
            prev_diff_str = "0⚪"

        prev_pct = ((price / data['prev_close'] - 1) * 100) if data['prev_close'] > 0 else 0
        if prev_pct >= 5.0:
            prev_pct_str = f"+{prev_pct:.2f}%🔺"
        elif prev_pct <= -3.0:
            prev_pct_str = f"{prev_pct:.2f}%🔹"
        elif prev_pct > 0:
            prev_pct_str = f"+{prev_pct:.2f}%"
        elif prev_pct < 0:
            prev_pct_str = f"{prev_pct:.2f}%"
        else:
            prev_pct_str = "0.00%"

        # 평단가 대비
        if data['holding']:
            avg_price = int(data['holding']['avg_buy_price'])
            avg_diff = price - avg_price
            if avg_diff > 0:
                avg_diff_str = f"+{format_number(avg_diff)}🔺"
                avg_pct_str = f"+{((price / avg_price - 1) * 100):.2f}%🔺"
            elif avg_diff < 0:
                avg_diff_str = f"{format_number(avg_diff)}🔹"
                avg_pct_str = f"{((price / avg_price - 1) * 100):.2f}%🔹"
            else:
                avg_diff_str = "0⚪"
                avg_pct_str = "0.00%⚪"
        else:
            avg_diff_str = "-"
            avg_pct_str = "-"

        lines.append(f"{time_str:^8}  {format_number(price):>10}  {format_number(volume):>12}  {diff_str:>10}  {pct_str:>10}  {prev_diff_str:>10}  {prev_pct_str:>10}  {avg_diff_str:>10}  {avg_pct_str:>10}")

    lines.append("━" * 80)

    return "\n".join(lines)


async def get_aegis_signal(stock_code: str) -> tuple:
    """
    AEGIS 신호 계산 (일봉 데이터 기반)

    Returns:
        (signal_text, signal_emoji, signal_color, score)
    """
    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # 일봉 데이터 조회 (최소 60일 필요)
        rows = await conn.fetch('''
            SELECT date, open, high, low, close, volume
            FROM daily_ohlcv
            WHERE stock_code = $1
            ORDER BY date DESC
            LIMIT 100
        ''', stock_code)

        if not rows or len(rows) < 60:
            return "데이터부족", "➖", COLOR_BLACK, 0

        # DataFrame 변환
        df = pd.DataFrame([dict(r) for r in rows])
        df = df.sort_values('date').reset_index(drop=True)

        # Decimal → float 변환
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        # 신호 점수 계산
        scored_df = calculate_signal_score(df)
        latest_score = int(scored_df['total_score'].iloc[-1])
        signal = score_to_signal(latest_score)

        # 신호별 표시
        signal_map = {
            Signal.STRONG_BUY: ("강력매수", "🔴", COLOR_RED),
            Signal.BUY: ("매수", "🔺", colors.orangered),
            Signal.HOLD: ("관망", "➖", COLOR_BLACK),
            Signal.SELL: ("매도", "🔻", COLOR_BLUE),
            Signal.STRONG_SELL: ("강력매도", "🔵", colors.darkblue),
        }

        text, emoji, color = signal_map.get(signal, ("관망", "➖", COLOR_BLACK))
        return text, emoji, color, latest_score

    except Exception as e:
        print(f"   ⚠️ AEGIS 신호 계산 오류 ({stock_code}): {e}")
        return "오류", "⚠️", COLOR_BLACK, 0

    finally:
        await conn.close()


async def get_aegis_signal_history(limit: int = 10) -> list:
    """최근 AEGIS 신호 히스토리 조회"""
    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        rows = await conn.fetch('''
            SELECT stock_code, stock_name, signal_type, signal_score,
                   current_price, recorded_at
            FROM aegis_signal_history
            ORDER BY recorded_at DESC
            LIMIT $1
        ''', limit)
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"   ⚠️ 신호 히스토리 조회 오류: {e}")
        return []
    finally:
        await conn.close()


def create_aegis_dashboard_page(c, aegis_signals, page_width, page_height):
    """
    PROJECT AEGIS Market Dashboard 페이지 생성 (3페이지)
    - 매수/매도 추천 종목 2단 레이아웃
    - 신호 히스토리 테이블
    """
    font_name = 'AppleGothic'
    now = datetime.now()
    y = page_height - 50

    # 제목
    c.setFont(font_name, 24)
    c.setFillColor(COLOR_BLACK)
    c.drawCentredString(page_width / 2, y, "PROJECT AEGIS Market Dashboard")
    y -= 25

    # 부제목
    c.setFont(font_name, 11)
    c.setFillColor(colors.grey)
    c.drawCentredString(page_width / 2, y, f"AI 기반 매매 신호 분석 | {now.strftime('%Y-%m-%d %H:%M')}")
    y -= 40

    # 매수/매도 종목 분류
    buy_signals = []
    sell_signals = []

    for stock_code, stock_name, aegis in aegis_signals:
        sig_text, sig_emoji, sig_color, sig_score = aegis
        item = {
            'name': stock_name,
            'code': stock_code,
            'signal': sig_text,
            'score': sig_score,
            'color': sig_color
        }
        if sig_score >= 1:  # 매수/강력매수
            buy_signals.append(item)
        elif sig_score <= -1:  # 매도/강력매도
            sell_signals.append(item)

    # 2단 레이아웃 (매수 | 매도)
    box_width = (page_width - 100) / 2
    box_height = 180
    left_x = 50
    right_x = page_width / 2 + 10

    # 매수 추천 박스 (좌측)
    c.setStrokeColor(COLOR_RED)
    c.setLineWidth(2)
    c.rect(left_x, y - box_height, box_width - 10, box_height)

    c.setFont(font_name, 14)
    c.setFillColor(COLOR_RED)
    c.drawString(left_x + 10, y - 20, "📈 매수 추천")

    c.setFont(font_name, 11)
    buy_y = y - 45
    for item in buy_signals[:6]:  # 최대 6개
        score_text = f"+{item['score']}" if item['score'] > 0 else str(item['score'])
        c.setFillColor(item['color'])
        c.drawString(left_x + 15, buy_y, f"• {item['name']} ({item['signal']}, {score_text})")
        buy_y -= 22

    if not buy_signals:
        c.setFillColor(colors.grey)
        c.drawString(left_x + 15, buy_y, "매수 추천 종목 없음")

    # 매도 추천 박스 (우측)
    c.setStrokeColor(COLOR_BLUE)
    c.setLineWidth(2)
    c.rect(right_x, y - box_height, box_width - 10, box_height)

    c.setFont(font_name, 14)
    c.setFillColor(COLOR_BLUE)
    c.drawString(right_x + 10, y - 20, "📉 매도 추천")

    c.setFont(font_name, 11)
    sell_y = y - 45
    for item in sell_signals[:6]:  # 최대 6개
        score_text = str(item['score'])
        c.setFillColor(item['color'])
        c.drawString(right_x + 15, sell_y, f"• {item['name']} ({item['signal']}, {score_text})")
        sell_y -= 22

    if not sell_signals:
        c.setFillColor(colors.grey)
        c.drawString(right_x + 15, sell_y, "매도 추천 종목 없음")

    y -= box_height + 30

    # 전체 신호 요약 테이블
    c.setFont(font_name, 14)
    c.setFillColor(COLOR_BLACK)
    c.drawString(50, y, "📊 보유종목 AEGIS 신호 현황")
    y -= 25

    # 테이블 데이터 준비
    table_header = ['종목명', '코드', '신호', '점수']
    table_data = [table_header]

    for stock_code, stock_name, aegis in aegis_signals:
        sig_text, _, _, sig_score = aegis
        score_str = f"+{sig_score}" if sig_score > 0 else str(sig_score)
        table_data.append([stock_name, stock_code, sig_text, score_str])

    col_widths = [150, 80, 80, 60]
    signal_table = Table(table_data, colWidths=col_widths)

    # 테이블 스타일
    table_style = [
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.grey),
    ]

    # 신호별 색상 적용
    for i, (stock_code, stock_name, aegis) in enumerate(aegis_signals):
        row = i + 1
        _, _, sig_color, sig_score = aegis
        if sig_score >= 1:
            table_style.append(('TEXTCOLOR', (2, row), (3, row), COLOR_RED))
        elif sig_score <= -1:
            table_style.append(('TEXTCOLOR', (2, row), (3, row), COLOR_BLUE))

    signal_table.setStyle(TableStyle(table_style))
    table_width, table_height = signal_table.wrap(0, 0)
    signal_table.drawOn(c, 50, y - table_height)

    c.showPage()


def create_summary_pages(c, holdings_data, page_width, page_height):
    """
    포트폴리오 요약 페이지 생성 (1-2페이지)
    1페이지: 제목 + 포트폴리오 요약 테이블 + 종목별 상세 현황 테이블
    2페이지: 포트폴리오 구성 차트 (파이차트 + 막대그래프)
    """
    font_name = 'AppleGothic'
    now = datetime.now()

    # 포트폴리오 데이터 계산
    portfolio_data = []
    total_investment = 0
    total_evaluation = 0

    for stock_code, stock_name, data in holdings_data:
        if data['holding']:
            qty = int(data['holding']['quantity'])
            avg_price = int(data['holding']['avg_buy_price'])
            current_price = data['current_price']
            buy_amount = qty * avg_price
            eval_amount = qty * current_price
            pnl = eval_amount - buy_amount
            pnl_rate = (pnl / buy_amount * 100) if buy_amount > 0 else 0

            # AI 등급 (임시로 '-' 표시, 나중에 연동 가능)
            ai_grade = data.get('ai_grade', '-')

            portfolio_data.append({
                'name': stock_name,
                'code': stock_code,
                'qty': qty,
                'avg_price': avg_price,
                'current_price': current_price,
                'buy_amount': buy_amount,
                'eval_amount': eval_amount,
                'pnl': pnl,
                'pnl_rate': pnl_rate,
                'ai_grade': ai_grade
            })

            total_investment += buy_amount
            total_evaluation += eval_amount

    total_pnl = total_evaluation - total_investment
    total_pnl_rate = (total_pnl / total_investment * 100) if total_investment > 0 else 0

    # ===== 1페이지: 포트폴리오 요약 =====
    y = page_height - 50

    # 제목
    c.setFont(font_name, 28)
    c.setFillColor(COLOR_BLACK)
    c.drawString(50, y, "보유종목 실시간 대시보드")
    y -= 30

    # 생성일시
    c.setFont(font_name, 11)
    c.setFillColor(colors.grey)
    c.drawString(50, y, f"생성일시: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 40

    # 포트폴리오 요약 제목
    c.setFont(font_name, 16)
    c.setFillColor(COLOR_BLACK)
    c.drawString(50, y, "포트폴리오 요약")
    y -= 25

    # 요약 테이블
    summary_data = [
        ['총 투자금액', '총 평가금액', '총 손익', '수익률'],
        [f'{total_investment:,}원', f'{total_evaluation:,}원',
         f'{total_pnl:+,}원', f'{total_pnl_rate:+.2f}%']
    ]

    summary_table = Table(summary_data, colWidths=[170, 170, 170, 170])
    summary_style = TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, 1), 14),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.85, 0.95, 0.85)),  # 연한 녹색
        ('TEXTCOLOR', (2, 1), (2, 1), COLOR_RED if total_pnl > 0 else COLOR_BLUE if total_pnl < 0 else COLOR_BLACK),
        ('TEXTCOLOR', (3, 1), (3, 1), COLOR_RED if total_pnl_rate > 0 else COLOR_BLUE if total_pnl_rate < 0 else COLOR_BLACK),
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
        ('BOX', (0, 0), (-1, -1), 1, colors.grey),
    ])
    summary_table.setStyle(summary_style)

    table_width, table_height = summary_table.wrap(0, 0)
    summary_table.drawOn(c, 50, y - table_height)
    y -= table_height + 30

    # 종목별 상세 현황 제목
    c.setFont(font_name, 16)
    c.setFillColor(COLOR_BLACK)
    c.drawString(50, y, "종목별 상세 현황")
    y -= 25

    # 종목별 테이블
    detail_header = ['종목명', '코드', '수량', '평단가', '현재가', '매수금액', '평가금액', '손익', '수익률', 'AI등급']
    detail_data = [detail_header]

    for item in portfolio_data:
        pnl_str = f"{item['pnl']:+,}"
        pnl_rate_str = f"{item['pnl_rate']:+.1f}%"

        detail_data.append([
            item['name'],
            item['code'],
            f"{item['qty']:,}",
            f"{item['avg_price']:,}",
            f"{item['current_price']:,}",
            f"{item['buy_amount']:,}",
            f"{item['eval_amount']:,}",
            pnl_str,
            pnl_rate_str,
            item['ai_grade']
        ])

    col_widths = [85, 55, 40, 60, 60, 80, 80, 75, 55, 45]
    detail_table = Table(detail_data, colWidths=col_widths)

    # 테이블 스타일 (손익/수익률 색상 적용)
    detail_style = [
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # 종목명 좌측
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),  # 나머지 우측
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOX', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
    ]

    # 손익/수익률 색상 적용
    for i, item in enumerate(portfolio_data):
        row = i + 1
        if item['pnl'] > 0:
            detail_style.append(('TEXTCOLOR', (7, row), (8, row), COLOR_RED))
        elif item['pnl'] < 0:
            detail_style.append(('TEXTCOLOR', (7, row), (8, row), COLOR_BLUE))

    detail_table.setStyle(TableStyle(detail_style))
    table_width, table_height = detail_table.wrap(0, 0)
    detail_table.drawOn(c, 50, y - table_height)

    c.showPage()

    # ===== 2페이지: 포트폴리오 구성 차트 =====
    y = page_height - 50

    # 제목
    c.setFont(font_name, 20)
    c.setFillColor(COLOR_BLACK)
    c.drawString(50, y, "포트폴리오 구성")
    y -= 40

    # 임시 디렉토리에 차트 저장
    temp_dir = tempfile.mkdtemp()

    try:
        # 1. 파이차트 (Portfolio Allocation)
        fig1, ax1 = plt.subplots(figsize=(5, 4))
        labels = [item['name'] for item in portfolio_data]
        sizes = [item['eval_amount'] for item in portfolio_data]
        percentages = [s / total_evaluation * 100 for s in sizes]

        # 색상 팔레트
        cmap = plt.colormaps.get_cmap('tab20')
        chart_colors = [cmap(i / len(portfolio_data)) for i in range(len(portfolio_data))]

        wedges, texts, autotexts = ax1.pie(
            sizes, labels=labels, autopct='%1.1f%%',
            colors=chart_colors, startangle=90
        )
        ax1.set_title('Portfolio Allocation', fontsize=12)
        plt.tight_layout()

        pie_path = os.path.join(temp_dir, 'pie_chart.png')
        plt.savefig(pie_path, dpi=100, bbox_inches='tight', facecolor='white')
        plt.close(fig1)

        # 2. 막대그래프 (Profit/Loss by Stock)
        fig2, ax2 = plt.subplots(figsize=(5, 4))
        names = [item['name'] for item in portfolio_data]
        pnls = [item['pnl'] for item in portfolio_data]
        bar_colors = ['red' if p > 0 else 'green' for p in pnls]

        ax2.barh(names, pnls, color=bar_colors)
        ax2.set_xlabel('P/L (KRW)')
        ax2.set_title('Profit/Loss by Stock', fontsize=12)
        ax2.axvline(x=0, color='black', linewidth=0.5)
        plt.tight_layout()

        bar_path = os.path.join(temp_dir, 'bar_chart.png')
        plt.savefig(bar_path, dpi=100, bbox_inches='tight', facecolor='white')
        plt.close(fig2)

        # 차트를 PDF에 추가
        chart_width = 350
        chart_height = 280

        # 파이차트 (좌측)
        c.drawImage(pie_path, 30, y - chart_height, width=chart_width, height=chart_height)

        # 막대그래프 (우측)
        c.drawImage(bar_path, page_width / 2 + 20, y - chart_height, width=chart_width, height=chart_height)

    finally:
        # 임시 파일 정리
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    c.showPage()


def create_pdf(holdings_list, aegis_signals, output_path):
    """PDF 생성 (터미널 스타일, 한글 폰트, 색상 적용)"""
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.pagesizes import landscape, A4

    page_width, page_height = landscape(A4)
    c = pdf_canvas.Canvas(str(output_path), pagesize=landscape(A4))

    # 폰트 설정
    font_name = 'AppleGothic'
    font_size = 12  # 폰트 크기 12로 조정
    line_height = 15

    # ===== 1-2페이지: 포트폴리오 요약 =====
    create_summary_pages(c, holdings_list, page_width, page_height)

    # ===== 3페이지: PROJECT AEGIS Market Dashboard =====
    create_aegis_dashboard_page(c, aegis_signals, page_width, page_height)

    # ===== 4페이지~: 각 종목별 페이지 생성 =====
    for stock_code, stock_name, data in holdings_list:
        y_position = page_height - 30

        # 헤더 - 수익률 계산
        if data['holding']:
            avg_price = int(data['holding']['avg_buy_price'])
            profit_rate = ((data['current_price'] - avg_price) / avg_price) * 100
            if profit_rate > 0:
                title_color = COLOR_RED
            elif profit_rate < 0:
                title_color = COLOR_BLUE
            else:
                title_color = COLOR_BLACK
        else:
            title_color = COLOR_BLACK
            profit_rate = 0

        # 헤더 라인
        c.setFont(font_name, font_size)
        c.setFillColor(COLOR_BLACK)
        header_line = "━" * 100
        c.drawString(30, y_position, header_line)
        y_position -= line_height + 5

        # 타이틀 - 종목명은 28pt (2배), 수익률에 따라 색상
        now = datetime.now()
        title_font_size = 28  # 14pt → 28pt (2배)
        c.setFont(font_name, title_font_size)
        c.setFillColor(title_color)

        # 종목명만 색상 적용
        stock_title = f"📊 {data['stock_name']} ({data['stock_code']})"
        c.drawString(30, y_position, stock_title)

        # 시간 정보는 검은색 (작은 글자로)
        x_offset = c.stringWidth(stock_title + " ", font_name, title_font_size)
        c.setFont(font_name, 12)
        c.setFillColor(COLOR_BLACK)
        time_text = f"⏰ {now.strftime('%Y-%m-%d %H:%M')}  (수집: {data['today_count']})"
        c.drawString(30 + x_offset, y_position - 8, time_text)  # y 위치 조정
        y_position -= title_font_size + 5  # 큰 폰트에 맞춰 간격 조정

        c.setFont(font_name, font_size)
        c.drawString(30, y_position, header_line)
        y_position -= line_height + 10

        # 가격 정보 (색상 적용)
        c.setFont(font_name, font_size)
        current_change, current_emoji = calc_change_emoji(data['current_price'], data['prev_close'])
        high_change, high_emoji = calc_change_emoji(data['today_high'], data['prev_close'])
        low_change, low_emoji = calc_change_emoji(data['today_low'], data['prev_close'])

        # 첫 번째 줄: 시가, 현재가, 거래량
        line1 = f"시가: {format_number(data['today_open'])} | 현재가: {format_number(data['current_price'])} "
        c.setFillColor(COLOR_BLACK)
        c.drawString(30, y_position, line1)

        # 현재가 변동률 색상
        x_offset = c.stringWidth(line1, font_name, font_size)
        if "+" in current_change:
            c.setFillColor(COLOR_RED)
        elif "-" in current_change:
            c.setFillColor(COLOR_BLUE)
        else:
            c.setFillColor(COLOR_BLACK)
        c.drawString(30 + x_offset, y_position, f"{current_change} {current_emoji}")

        x_offset += c.stringWidth(f"{current_change} {current_emoji} ", font_name, font_size)
        c.setFillColor(COLOR_BLACK)
        c.drawString(30 + x_offset, y_position, f"| 거래량: {format_number(data['current_volume'])}")
        y_position -= line_height

        # 두 번째 줄: 최고, 최저
        line2 = f"최고: {format_number(data['today_high'])} "
        c.setFillColor(COLOR_BLACK)
        c.drawString(30, y_position, line2)

        x_offset = c.stringWidth(line2, font_name, font_size)
        if "+" in high_change:
            c.setFillColor(COLOR_RED)
        elif "-" in high_change:
            c.setFillColor(COLOR_BLUE)
        else:
            c.setFillColor(COLOR_BLACK)
        c.drawString(30 + x_offset, y_position, f"{high_change} {high_emoji}")

        x_offset += c.stringWidth(f"{high_change} {high_emoji} ", font_name, font_size)
        line2b = f"| 최저: {format_number(data['today_low'])} "
        c.setFillColor(COLOR_BLACK)
        c.drawString(30 + x_offset, y_position, line2b)

        x_offset += c.stringWidth(line2b, font_name, font_size)
        if "+" in low_change:
            c.setFillColor(COLOR_RED)
        elif "-" in low_change:
            c.setFillColor(COLOR_BLUE)
        else:
            c.setFillColor(COLOR_BLACK)
        c.drawString(30 + x_offset, y_position, f"{low_change} {low_emoji}")
        y_position -= line_height

        # 보유 정보
        if data['holding']:
            quantity = int(data['holding']['quantity'])
            avg_price = int(data['holding']['avg_buy_price'])
            eval_amount = data['current_price'] * quantity
            holding_amount = avg_price * quantity
            profit = eval_amount - holding_amount
            profit_rate = ((data['current_price'] - avg_price) / avg_price) * 100

            if profit_rate > 0:
                profit_sign = "+"
                profit_emoji = "🔺"
                profit_color = COLOR_RED
            elif profit_rate < 0:
                profit_sign = ""
                profit_emoji = "🔹"
                profit_color = COLOR_BLUE
            else:
                profit_sign = ""
                profit_emoji = "⚪"
                profit_color = COLOR_BLACK

            line3 = f"평단가: {format_number(avg_price)} "
            c.setFillColor(COLOR_BLACK)
            c.drawString(30, y_position, line3)

            x_offset = c.stringWidth(line3, font_name, font_size)
            c.setFillColor(profit_color)
            c.drawString(30 + x_offset, y_position, f"{profit_sign}{profit_rate:.2f}%{profit_emoji}")

            x_offset += c.stringWidth(f"{profit_sign}{profit_rate:.2f}%{profit_emoji} ", font_name, font_size)
            c.setFillColor(COLOR_BLACK)
            c.drawString(30 + x_offset, y_position, f"{format_number(quantity)}주 | {format_number(eval_amount)} ")

            x_offset += c.stringWidth(f"{format_number(quantity)}주 | {format_number(eval_amount)} ", font_name, font_size)
            c.setFillColor(profit_color)
            c.drawString(30 + x_offset, y_position, f"{profit_sign}{format_number(abs(profit))}원{profit_emoji}")
            y_position -= line_height

        # 구분선
        c.setFillColor(COLOR_BLACK)
        y_position -= 5
        c.drawString(30, y_position, header_line)
        y_position -= line_height + 5

        # 테이블 헤더 (고정폭) - 거래량을 현재가 앞으로 이동
        c.setFillColor(COLOR_BLACK)
        header_x = 40
        c.drawString(header_x, y_position, "시간")
        c.drawString(header_x + 70, y_position, "거래량")
        c.drawString(header_x + 180, y_position, "현재가")
        c.drawString(header_x + 260, y_position, "직전")
        c.drawString(header_x + 350, y_position, "변동률")
        c.drawString(header_x + 430, y_position, "전일")
        c.drawString(header_x + 520, y_position, "전일률")
        c.drawString(header_x + 610, y_position, "평단가")
        c.drawString(header_x + 700, y_position, "평가율")
        y_position -= line_height

        separator = "-" * 120
        c.drawString(30, y_position, separator)
        y_position -= line_height + 3

        # 틱 데이터 (색상 적용)
        for tick in data['ticks']:
            if y_position < 50:  # 페이지 끝에 도달
                break

            time_str = tick['timestamp'].strftime('%H:%M')
            price = int(tick['price'])
            volume = int(tick['volume'])
            prev_price = int(tick['prev_price']) if tick['prev_price'] else price
            prev_volume = int(tick['prev_volume']) if tick['prev_volume'] else volume

            # 우측 정렬 기본 정보 - 거래량을 현재가 앞으로 이동
            row_x = 40
            col_time = row_x
            col_volume_right = row_x + 150  # 거래량 우측 끝 (먼저)
            col_price_right = row_x + 250  # 현재가 우측 끝 (나중)
            col_diff_right = row_x + 340  # 직전 우측 끝
            col_pct_right = row_x + 420  # 변동률 우측 끝
            col_prev_diff_right = row_x + 510  # 전일 우측 끝
            col_prev_pct_right = row_x + 600  # 전일률 우측 끝
            col_avg_diff_right = row_x + 690  # 평단가 우측 끝
            col_avg_pct_right = row_x + 780  # 평가율 우측 끝

            c.setFillColor(COLOR_BLACK)
            c.drawString(col_time, y_position, time_str)

            # 거래량 우측 정렬 + 이전 거래량 대비 증가율(%)
            volume_str = format_number(volume)
            if prev_volume > 0 and volume > prev_volume:
                volume_increase_pct = ((volume - prev_volume) / prev_volume) * 100
                volume_pct_str = f"+{volume_increase_pct:.1f}%"
                pct_color = COLOR_RED
            else:
                volume_pct_str = ""
                pct_color = COLOR_BLACK

            # 거래량 숫자 출력
            volume_width = c.stringWidth(volume_str, font_name, font_size)
            c.setFillColor(COLOR_BLACK)
            c.drawString(col_volume_right - volume_width - 50, y_position, volume_str)

            # 증가율 출력 (색상 적용)
            if volume_pct_str:
                c.setFillColor(pct_color)
                c.drawString(col_volume_right - 45, y_position, volume_pct_str)

            # 현재가 우측 정렬
            c.setFillColor(COLOR_BLACK)
            price_str = format_number(price)
            price_width = c.stringWidth(price_str, font_name, font_size)
            c.drawString(col_price_right - price_width, y_position, price_str)

            # 직전 대비 (색상) - 우측 정렬
            price_diff = price - prev_price
            if price_diff > 0:
                diff_str = f"+{format_number(price_diff)}🔺"
                c.setFillColor(COLOR_RED)
            elif price_diff < 0:
                diff_str = f"{format_number(price_diff)}🔹"
                c.setFillColor(COLOR_BLUE)
            else:
                diff_str = "0⚪"
                c.setFillColor(COLOR_BLACK)
            diff_width = c.stringWidth(diff_str, font_name, font_size)
            c.drawString(col_diff_right - diff_width, y_position, diff_str)

            # 변동률 (색상) - 우측 정렬
            if price > prev_price:
                pct_str = f"+{((price / prev_price - 1) * 100):.2f}%"
                c.setFillColor(COLOR_RED)
            elif price < prev_price:
                pct_str = f"{((price / prev_price - 1) * 100):.2f}%"
                c.setFillColor(COLOR_BLUE)
            else:
                pct_str = "0.00%"
                c.setFillColor(COLOR_BLACK)
            pct_width = c.stringWidth(pct_str, font_name, font_size)
            c.drawString(col_pct_right - pct_width, y_position, pct_str)

            # 전일 대비 (색상) - 우측 정렬
            prev_diff = price - data['prev_close']
            if prev_diff > 0:
                prev_diff_str = f"+{format_number(prev_diff)}🔺"
                c.setFillColor(COLOR_RED)
            elif prev_diff < 0:
                prev_diff_str = f"{format_number(prev_diff)}🔹"
                c.setFillColor(COLOR_BLUE)
            else:
                prev_diff_str = "0⚪"
                c.setFillColor(COLOR_BLACK)
            prev_diff_width = c.stringWidth(prev_diff_str, font_name, font_size)
            c.drawString(col_prev_diff_right - prev_diff_width, y_position, prev_diff_str)

            # 전일률 (색상) - 우측 정렬
            prev_pct = ((price / data['prev_close'] - 1) * 100) if data['prev_close'] > 0 else 0
            if prev_pct >= 5.0:
                prev_pct_str = f"+{prev_pct:.2f}%🔺"
                c.setFillColor(COLOR_RED)
            elif prev_pct <= -3.0:
                prev_pct_str = f"{prev_pct:.2f}%🔹"
                c.setFillColor(COLOR_BLUE)
            elif prev_pct > 0:
                prev_pct_str = f"+{prev_pct:.2f}%"
                c.setFillColor(COLOR_RED)
            elif prev_pct < 0:
                prev_pct_str = f"{prev_pct:.2f}%"
                c.setFillColor(COLOR_BLUE)
            else:
                prev_pct_str = "0.00%"
                c.setFillColor(COLOR_BLACK)
            prev_pct_width = c.stringWidth(prev_pct_str, font_name, font_size)
            c.drawString(col_prev_pct_right - prev_pct_width, y_position, prev_pct_str)

            # 평단가 대비 (색상) - 우측 정렬
            if data['holding']:
                avg_price = int(data['holding']['avg_buy_price'])
                avg_diff = price - avg_price
                if avg_diff > 0:
                    avg_diff_str = f"+{format_number(avg_diff)}🔺"
                    c.setFillColor(COLOR_RED)
                elif avg_diff < 0:
                    avg_diff_str = f"{format_number(avg_diff)}🔹"
                    c.setFillColor(COLOR_BLUE)
                else:
                    avg_diff_str = "0⚪"
                    c.setFillColor(COLOR_BLACK)
                avg_diff_width = c.stringWidth(avg_diff_str, font_name, font_size)
                c.drawString(col_avg_diff_right - avg_diff_width, y_position, avg_diff_str)

                # 평가율 (색상) - 우측 정렬
                avg_pct = ((price / avg_price - 1) * 100)
                if avg_pct > 0:
                    avg_pct_str = f"+{avg_pct:.2f}%🔺"
                    c.setFillColor(COLOR_RED)
                elif avg_pct < 0:
                    avg_pct_str = f"{avg_pct:.2f}%🔹"
                    c.setFillColor(COLOR_BLUE)
                else:
                    avg_pct_str = "0.00%⚪"
                    c.setFillColor(COLOR_BLACK)
                avg_pct_width = c.stringWidth(avg_pct_str, font_name, font_size)
                c.drawString(col_avg_pct_right - avg_pct_width, y_position, avg_pct_str)
            else:
                c.setFillColor(COLOR_BLACK)
                dash_width = c.stringWidth("-", font_name, font_size)
                c.drawString(col_avg_diff_right - dash_width, y_position, "-")
                c.drawString(col_avg_pct_right - dash_width, y_position, "-")

            y_position -= line_height

        # 하단 구분선
        c.setFillColor(COLOR_BLACK)
        y_position -= 5
        c.drawString(30, y_position, header_line)

        # 새 페이지
        c.showPage()

    # PDF 저장
    c.save()
    print(f"✅ PDF 생성 완료: {output_path}")


async def main():
    """메인 함수"""
    print("\n" + "="*80)
    print("📊 터미널 스타일 실시간 대시보드 PDF 생성")
    print("="*80 + "\n")

    # 시간 제한 체크 (04:00 ~ 18:00만 허용)
    now = datetime.now()
    current_hour = now.hour

    if current_hour < 4 or current_hour >= 18:
        # 다음 생성 가능 시각 계산
        from datetime import timedelta
        if current_hour >= 18:
            # 18시 이후면 내일 04시
            next_available = (now + timedelta(days=1)).replace(hour=4, minute=0, second=0)
        else:
            # 04시 이전이면 오늘 04시
            next_available = now.replace(hour=4, minute=0, second=0)

        print(f"⚠️  PDF 생성 시간 제한: 04:00 ~ 18:00만 허용됩니다.")
        print(f"   현재 시각: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   다음 생성 가능 시각: {next_available.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        return

    # 출력 디렉토리
    output_dir = Path('/Users/wonny/Dev/joungwon.stocks/reports/holding_stock')
    output_dir.mkdir(parents=True, exist_ok=True)

    # 보유종목 목록 조회 (평가금액 높은 순)
    print("📡 보유종목 목록 조회 중...")
    holdings = await get_all_holdings()
    print(f"✅ {len(holdings)}개 종목 발견\n")

    # 각 종목별 상세 데이터 수집
    holdings_data = []
    aegis_signals = []

    for row in holdings:
        stock_code = row['stock_code']
        stock_name = row['stock_name']
        print(f"   📊 {stock_name}({stock_code}) 데이터 수집 중...")

        data = await get_stock_detail_data(stock_code, stock_name, limit_count=20)
        holdings_data.append((stock_code, stock_name, data))

        # AEGIS 신호 계산
        aegis_signal = await get_aegis_signal(stock_code)
        aegis_signals.append((stock_code, stock_name, aegis_signal))
        sig_text, _, _, sig_score = aegis_signal
        print(f"      AEGIS: {sig_text} ({sig_score:+d})")

    print(f"\n✅ 모든 종목 데이터 수집 완료\n")

    # PDF 생성
    output_path = output_dir / 'realtime_dashboard.pdf'
    print(f"📄 PDF 생성 중: {output_path}")
    create_pdf(holdings_data, aegis_signals, output_path)

    print("\n" + "="*80)
    print(f"✅ 완료! PDF 경로: {output_path}")
    print("="*80 + "\n")


if __name__ == '__main__':
    asyncio.run(main())
