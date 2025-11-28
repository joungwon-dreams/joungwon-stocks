import io
from reportlab.platypus import Table, TableStyle, Paragraph, Image, Spacer, Flowable
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta, time

# Set Korean font for matplotlib (ensure it's loaded)
try:
    plt.rcParams['font.family'] = 'AppleGothic'
    plt.rcParams['axes.unicode_minus'] = False
except Exception as e:
    print(f"Warning: Matplotlib font setup failed: {e}")


def generate_realtime_tick_chart(ticks_data, output=None):
    """
    Generate a 1-minute tick chart.
    If output is None, returns BytesIO buffer.
    If output is a path, saves to file (backward compatible).
    """
    if not ticks_data:
        return None

    # Sort by time ASC
    sorted_data = sorted(ticks_data, key=lambda x: x['timestamp'])

    times = [row['timestamp'] for row in sorted_data]
    prices = [float(row['price']) for row in sorted_data]
    volumes = [int(row['volume']) for row in sorted_data]

    if not times: return None

    start_price = prices[0]
    end_price = prices[-1]
    color = '#D32F2F' if end_price >= start_price else '#1976D2' # Red/Blue

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 4), height_ratios=[3, 1], sharex=True)

    # Price Chart
    ax1.plot(times, prices, color=color, linewidth=1.5)
    ax1.fill_between(times, prices, min(prices), alpha=0.1, color=color)
    ax1.set_ylabel('Price')
    ax1.grid(True, alpha=0.3, linestyle='--')

    # Volume Chart
    vol_colors = []
    prev_p = prices[0]
    for p in prices:
        vol_colors.append('#D32F2F' if p >= prev_p else '#1976D2')
        prev_p = p

    ax2.bar(times, volumes, color=vol_colors, width=0.0005, alpha=0.6)
    ax2.set_ylabel('Vol')
    ax2.grid(True, alpha=0.3, linestyle='--')

    # Formatting
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.xticks(rotation=0)
    plt.tight_layout()

    # BytesIO 버퍼에 저장
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    # 기존 파일 저장 방식도 지원 (backward compatible)
    if output is not None:
        with open(output, 'wb') as f:
            f.write(buf.getvalue())
        buf.seek(0)
        return output

    return buf

def create_min_ticks_table_compact(ticks_data):
    """
    Create a compact table showing recent ticks (Time, Price, Vol)
    """
    if not ticks_data:
        return None
    
    sorted_data = sorted(ticks_data, key=lambda x: x['timestamp'], reverse=True)
    
    display_count = 10
    data_subset = sorted_data[:display_count]
    
    left_col = data_subset[:5]
    right_col = data_subset[5:]
    
    table_data = [['시간', '체결가', '체결량', '', '시간', '체결가', '체결량']]
    
    for i in range(5):
        row_data = []
        if i < len(left_col):
            row = left_col[i]
            t = row['timestamp'].strftime('%H:%M')
            p = int(row['price'])
            v = int(row['volume'])
            row_data.extend([t, f"{p:,}", f"{v:,}"])
        else:
            row_data.extend(['-', '-', '-'])
            
        row_data.append('')
        
        if i < len(right_col):
            row = right_col[i]
            t = row['timestamp'].strftime('%H:%M')
            p = int(row['price'])
            v = int(row['volume'])
            row_data.extend([t, f"{p:,}", f"{v:,}"])
        else:
            row_data.extend(['-', '-', '-'])
            
        table_data.append(row_data)
        
    t = Table(table_data, colWidths=[2.5*cm, 2.5*cm, 2.5*cm, 0.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
    
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f3f5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('FONTNAME', (1, 1), (1, -1), 'AppleGothic'), 
        ('FONTNAME', (5, 1), (5, -1), 'AppleGothic'),
    ]))
    
    return t

def create_stock_realtime_dashboard(stock_info, holding_info, min_ticks_data):
    """
    Create a detailed real-time dashboard for a single stock.
    Filter: Max 34 items, Time <= 15:30.
    """
    elements = []
    
    # Debug prints
    if min_ticks_data:
        print(f"DEBUG: Total ticks: {len(min_ticks_data)}")
        print(f"DEBUG: Range: {min_ticks_data[-1]['timestamp']} ~ {min_ticks_data[0]['timestamp']}")
    
    if not stock_info or not min_ticks_data:
        return elements

    # Filter Data: Time <= 15:30
    # Removed UTC conversion as debug showed timestamps are likely KST (17:28)
    filtered_data = []
    for t in min_ticks_data:
        ts = t['timestamp']
        current_time = ts.time()
        
        if current_time <= time(15, 30):
             filtered_data.append(t)
    
    # Fallback: If no data before 15:30 (e.g. after-hours only), use all data
    # to ensure dashboard is not empty per user feedback
    if not filtered_data and min_ticks_data:
        filtered_data = min_ticks_data
    
    print(f"DEBUG: Filtered ticks (<= 15:30): {len(filtered_data)}")
    
    # Sort DESC
    sorted_data = sorted(filtered_data, key=lambda x: x['timestamp'], reverse=True)
    
    # Limit to 34 items (17 per column)
    display_count = 34
    data_subset = sorted_data[:display_count]

    # --- Top Summary Section ---
    # Use filtered data for summary to reflect market hours, or unfiltered if requested?
    # Usually user wants current status. If 17:28 exists, that IS current status.
    # But user specifically asked for "15:30 이전 데이터만 표시". 
    # This implies they want to see the "Market Close" state, or just filter the list?
    # "리스트를 ... 15:30분 이전 해서 그전 데이타를 보여줘" -> Likely applies to the list table.
    # The top summary usually shows the *latest* available info (Current Price).
    
    target_data = data_subset if data_subset else min_ticks_data 
    
    latest_tick = min_ticks_data[0] if min_ticks_data else None # Use absolute latest for Current Price summary?
    # Or use filtered latest? Let's stick to unfiltered for top summary "Current Price" as it is reality.
    # But if user wants to ignore after-hours... let's use filtered[0] if available.
    
    if sorted_data:
        latest_tick = sorted_data[0]
    elif min_ticks_data:
        latest_tick = min_ticks_data[0] # Fallback
        
    current_price = int(latest_tick['price']) if latest_tick else 0
    
    open_price = stock_info.get('open_price', 0)
    if not open_price and min_ticks_data:
        # Find 09:00 tick
        open_tick = next((t for t in reversed(min_ticks_data) if t['timestamp'].hour >= 9 and t['timestamp'].minute >=0 and t['timestamp'].hour < 10), None)
        open_price = int(open_tick['price']) if open_tick else current_price
    
    # High/Low/Vol from FILTERED data (up to 15:30)
    source_data = filtered_data if filtered_data else min_ticks_data 
    high_price = max(int(t['price']) for t in source_data) if source_data else 0
    low_price = min(int(t['price']) for t in source_data) if source_data else 0
    total_volume = sum(int(t['volume']) for t in source_data) if source_data else 0

    평단가 = int(holding_info['avg_buy_price']) if holding_info and holding_info.get('avg_buy_price') else 0
    수량 = int(holding_info['quantity']) if holding_info and holding_info.get('quantity') else 0
    
    평가금액 = current_price * 수량
    손익금액 = 평가금액 - (평단가 * 수량)
    손익률 = (손익금액 / (평단가 * 수량) * 100) if (평단가 * 수량) > 0 else 0

    profit_color = 'red' if 손익금액 >= 0 else 'blue'
    
    summary_data_top = [
        [Paragraph(f"<b>시가:</b> {open_price:,}", ParagraphStyle('normal', fontName='AppleGothic', fontSize=9)),
         Paragraph(f"<b>현재가:</b> {current_price:,}", ParagraphStyle('normal', fontName='AppleGothic', fontSize=9)),
         Paragraph(f"<b>거래량:</b> {total_volume:,}", ParagraphStyle('normal', fontName='AppleGothic', fontSize=9))],
        [Paragraph(f"<b>최고:</b> {high_price:,}", ParagraphStyle('normal', fontName='AppleGothic', fontSize=9)),
         Paragraph(f"<b>최저:</b> {low_price:,}", ParagraphStyle('normal', fontName='AppleGothic', fontSize=9)),
         Paragraph(f"<b>평단가:</b> <font color='{profit_color}'>{평단가:,}</font>", ParagraphStyle('normal', fontName='AppleGothic', fontSize=9))],
        [Paragraph(f"<b>평가금액:</b> {평가금액:,}", ParagraphStyle('normal', fontName='AppleGothic', fontSize=9)),
         Paragraph(f"<b>손익금액:</b> <font color='{profit_color}'>{손익금액:+,}</font>", ParagraphStyle('normal', fontName='AppleGothic', fontSize=9)),
         Paragraph(f"<b>손익률:</b> <font color='{profit_color}'>{손익률:+.2f}%</font>", ParagraphStyle('normal', fontName='AppleGothic', fontSize=9))]
    ]
    
    summary_table_top = Table(summary_data_top, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
    summary_table_top.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,-1), 'AppleGothic'),
        ('GRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8F9FA')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(summary_table_top)
    elements.append(Spacer(1, 0.5*cm))

    # --- Min Ticks Detail Table (realtime_dashboard.pdf 형식과 동일) ---
    # 컬럼 순서: 시간 → 거래량 → 현재가 → 직전 → 변동률 → 전일 → 전일률 → 평단가 → 평가율
    detail_headers = ['시간', '거래량', '현재가', '직전', '변동률', '전일', '전일률', '평단가', '평가율']
    detail_table_data = [detail_headers]

    # Styles
    cell_style_center = ParagraphStyle('cell_center', fontName='AppleGothic', fontSize=9, alignment=TA_CENTER)
    cell_style_small = ParagraphStyle('cell_small', fontName='AppleGothic', fontSize=7, alignment=TA_CENTER)

    # 전일 종가 계산 (첫 번째 틱의 가격에서 change_rate 역산)
    first_tick = data_subset[-1] if data_subset else None
    prev_close = 0
    if first_tick:
        first_price = int(first_tick['price'])
        first_rate = float(first_tick.get('change_rate', 0.0))
        if first_rate != 0:
            prev_close = int(first_price / (1 + first_rate / 100))
        else:
            prev_close = first_price

    for tick in data_subset:
        ts = tick['timestamp']
        시간 = ts.strftime('%H:%M')

        현재가 = int(tick['price'])
        거래량 = int(tick['volume'])
        prev_price = int(tick['prev_price']) if tick.get('prev_price') else 현재가
        prev_volume = int(tick['prev_volume']) if tick.get('prev_volume') else 거래량

        # 직전 대비 (가격)
        직전_diff = 현재가 - prev_price
        if 직전_diff > 0:
            직전_str = f"+{직전_diff:,}"
            c_직전 = 'red'
        elif 직전_diff < 0:
            직전_str = f"{직전_diff:,}"
            c_직전 = 'blue'
        else:
            직전_str = "0"
            c_직전 = 'black'

        # 변동률 (직전 대비)
        if prev_price > 0:
            변동률 = ((현재가 - prev_price) / prev_price) * 100
        else:
            변동률 = 0.0
        c_변동률 = 'red' if 변동률 >= 0 else 'blue'

        # 전일 대비
        전일_diff = 현재가 - prev_close if prev_close > 0 else 0
        if 전일_diff > 0:
            전일_str = f"+{전일_diff:,}"
            c_전일 = 'red'
        elif 전일_diff < 0:
            전일_str = f"{전일_diff:,}"
            c_전일 = 'blue'
        else:
            전일_str = "0"
            c_전일 = 'black'

        # 전일률
        전일률 = ((현재가 - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
        c_전일률 = 'red' if 전일률 >= 0 else 'blue'

        # 평단가 대비
        평단가_diff = 현재가 - 평단가 if 평단가 > 0 else 0
        if 평단가_diff > 0:
            평단가_str = f"+{평단가_diff:,}"
            c_평단가 = 'red'
        elif 평단가_diff < 0:
            평단가_str = f"{평단가_diff:,}"
            c_평단가 = 'blue'
        else:
            평단가_str = "0"
            c_평단가 = 'black'

        # 평가율
        평가율 = (평단가_diff / 평단가 * 100) if 평단가 > 0 else 0.0
        c_평가율 = 'red' if 평가율 >= 0 else 'blue'

        # 거래량 증가율 (누적 거래량이므로 이전 대비 증가율)
        if prev_volume > 0 and 거래량 > prev_volume:
            vol_increase_pct = ((거래량 - prev_volume) / prev_volume) * 100
            거래량_str = f"{거래량:,} <font color='red'>+{vol_increase_pct:.1f}%</font>"
        else:
            거래량_str = f"{거래량:,}"

        # Paragraph 생성
        p_거래량 = Paragraph(거래량_str, cell_style_center)
        p_현재가 = Paragraph(f"{현재가:,}", cell_style_center)
        p_직전 = Paragraph(f"<font color='{c_직전}'>{직전_str}</font>", cell_style_center)
        p_변동률 = Paragraph(f"<font color='{c_변동률}'>{변동률:+.2f}%</font>", cell_style_center)
        p_전일 = Paragraph(f"<font color='{c_전일}'>{전일_str}</font>", cell_style_center)
        p_전일률 = Paragraph(f"<font color='{c_전일률}'>{전일률:+.2f}%</font>", cell_style_center)
        p_평단가 = Paragraph(f"<font color='{c_평단가}'>{평단가_str}</font>", cell_style_center)
        p_평가율 = Paragraph(f"<font color='{c_평가율}'>{평가율:+.2f}%</font>", cell_style_small)

        detail_table_data.append([
            시간,
            p_거래량,
            p_현재가,
            p_직전,
            p_변동률,
            p_전일,
            p_전일률,
            p_평단가,
            p_평가율
        ])

    detail_table = Table(detail_table_data, colWidths=[1.5*cm, 2.5*cm, 2*cm, 1.5*cm, 1.8*cm, 1.8*cm, 1.5*cm, 1.5*cm, 1.5*cm])
    detail_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e0e0e0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(detail_table)

    return elements