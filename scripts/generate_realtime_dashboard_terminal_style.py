#!/usr/bin/env python3
"""
터미널 스타일 실시간 보유종목 대시보드 PDF 생성
watch_*.sh 스크립트의 터미널 출력 형식을 PDF로 변환
"""
import asyncio
import asyncpg
from datetime import datetime, timedelta
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, Preformatted
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

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


def create_pdf(holdings_list, output_path):
    """PDF 생성 (터미널 스타일, 한글 폰트, 색상 적용)"""
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.pagesizes import landscape, A4

    page_width, page_height = landscape(A4)
    c = pdf_canvas.Canvas(str(output_path), pagesize=landscape(A4))

    # 폰트 설정
    font_name = 'AppleGothic'
    font_size = 12  # 폰트 크기 12로 조정
    line_height = 15

    # 각 종목별 페이지 생성
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

            # 거래량 우측 정렬 + 이전 거래량 대비 화살표
            volume_str = format_number(volume)
            if volume > prev_volume:
                volume_arrow = "▲"
                arrow_color = COLOR_RED
            elif volume < prev_volume:
                volume_arrow = "▼"
                arrow_color = COLOR_BLUE
            else:
                volume_arrow = ""
                arrow_color = COLOR_BLACK

            # 거래량 숫자 출력
            volume_width = c.stringWidth(volume_str, font_name, font_size)
            c.setFillColor(COLOR_BLACK)
            c.drawString(col_volume_right - volume_width - 15, y_position, volume_str)

            # 화살표 출력 (색상 적용)
            if volume_arrow:
                c.setFillColor(arrow_color)
                c.drawString(col_volume_right - 12, y_position, volume_arrow)

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
    output_dir = Path('/Users/wonny/Dev/joungwon.stocks/reports')
    output_dir.mkdir(parents=True, exist_ok=True)

    # 보유종목 목록 조회 (평가금액 높은 순)
    print("📡 보유종목 목록 조회 중...")
    holdings = await get_all_holdings()
    print(f"✅ {len(holdings)}개 종목 발견\n")

    # 각 종목별 상세 데이터 수집
    holdings_data = []
    for row in holdings:
        stock_code = row['stock_code']
        stock_name = row['stock_name']
        print(f"   📊 {stock_name}({stock_code}) 데이터 수집 중...")

        data = await get_stock_detail_data(stock_code, stock_name, limit_count=20)

        holdings_data.append((stock_code, stock_name, data))

    print(f"\n✅ 모든 종목 데이터 수집 완료\n")

    # PDF 생성
    output_path = output_dir / 'realtime_dashboard.pdf'
    print(f"📄 PDF 생성 중: {output_path}")
    create_pdf(holdings_data, output_path)

    print("\n" + "="*80)
    print(f"✅ 완료! PDF 경로: {output_path}")
    print("="*80 + "\n")


if __name__ == '__main__':
    asyncio.run(main())
