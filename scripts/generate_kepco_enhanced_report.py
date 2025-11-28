"""
한국전력 향상된 리서치 리포트 PDF 생성

포함 내용:
1. 365일 OHLCV 캔들스틱 차트
2. 거래량 차트
3. 수급분석 차트 (외국인/기관/개인)
4. 최근 2주간 주가 변화
5. 보유 현황
6. 투자 의견
"""
import sys
import asyncio
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib import patches
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from src.config.database import db

# 한국전력 정보
KEPCO_CODE = '015760'
KEPCO_NAME = '한국전력'

# 출력 디렉토리
OUTPUT_DIR = Path('/Users/wonny/Dev/joungwon.stocks.report/research_report/enhanced')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 한글 폰트 설정
FONT_DIR = Path('/Users/wonny/Dev/joungwon.stocks/fonts')
FONT_PATH_REGULAR = FONT_DIR / 'NanumGothic.ttf'
FONT_PATH_BOLD = FONT_DIR / 'NanumGothicBold.ttf'

# 폰트 등록
try:
    pdfmetrics.registerFont(TTFont('NanumGothic', str(FONT_PATH_REGULAR)))
    pdfmetrics.registerFont(TTFont('NanumGothicBold', str(FONT_PATH_BOLD)))
    FONT_NAME = 'NanumGothic'
    FONT_NAME_BOLD = 'NanumGothicBold'
except:
    FONT_NAME = 'Helvetica'
    FONT_NAME_BOLD = 'Helvetica-Bold'

# matplotlib 한글 폰트
font_prop = fm.FontProperties(fname=str(FONT_PATH_REGULAR))
plt.rc('font', family=font_prop.get_name())
plt.rcParams['axes.unicode_minus'] = False


async def fetch_ohlcv_data(days=365):
    """OHLCV 데이터 조회"""
    query = '''
        SELECT date, open, high, low, close, volume
        FROM daily_ohlcv
        WHERE stock_code = $1
        ORDER BY date DESC
        LIMIT $2
    '''
    rows = await db.fetch(query, KEPCO_CODE, days)
    return list(reversed(rows))  # 오래된 순으로 정렬


async def fetch_supply_demand_data(days=365):
    """수급 데이터 조회"""
    query = '''
        SELECT date, foreigner_net, institution_net, individual_net
        FROM stock_supply_demand
        WHERE stock_code = $1
        ORDER BY date DESC
        LIMIT $2
    '''
    rows = await db.fetch(query, KEPCO_CODE, days)
    return list(reversed(rows))


async def fetch_holding_data():
    """보유 현황 조회"""
    query = '''
        SELECT stock_code, stock_name, quantity, avg_buy_price, current_price
        FROM stock_assets
        WHERE stock_code = $1 AND is_active = TRUE AND quantity > 0
    '''
    row = await db.fetchrow(query, KEPCO_CODE)

    if not row:
        return None

    return {
        'code': row['stock_code'],
        'name': row['stock_name'],
        'quantity': row['quantity'],
        'avg_price': float(row['avg_buy_price']),
        'current_price': float(row['current_price']),
        'total_cost': row['quantity'] * float(row['avg_buy_price']),
        'total_value': row['quantity'] * float(row['current_price']),
        'profit': row['quantity'] * (float(row['current_price']) - float(row['avg_buy_price'])),
        'profit_rate': ((float(row['current_price']) - float(row['avg_buy_price'])) / float(row['avg_buy_price'])) * 100
    }


async def fetch_stock_info_naver(stock_code):
    """네이버 금융 API - 종목 기본 정보"""
    url = f"https://m.stock.naver.com/api/stock/{stock_code}/basic"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
                return data
            return None


def create_candlestick_chart(ohlcv_data, output_path):
    """365일 캔들스틱 차트 생성"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10),
                                    gridspec_kw={'height_ratios': [3, 1]})

    dates = [row['date'] for row in ohlcv_data]
    opens = [float(row['open']) for row in ohlcv_data]
    highs = [float(row['high']) for row in ohlcv_data]
    lows = [float(row['low']) for row in ohlcv_data]
    closes = [float(row['close']) for row in ohlcv_data]
    volumes = [int(row['volume']) for row in ohlcv_data]

    # 캔들스틱 차트
    for i in range(len(dates)):
        color = 'red' if closes[i] >= opens[i] else 'blue'

        # 몸통
        ax1.add_patch(patches.Rectangle(
            (i, min(opens[i], closes[i])),
            0.6,
            abs(closes[i] - opens[i]),
            facecolor=color,
            edgecolor=color,
            alpha=0.8
        ))

        # 그림자 (위아래 꼬리)
        ax1.plot([i + 0.3, i + 0.3], [lows[i], highs[i]], color=color, linewidth=1)

    ax1.set_xlim(-1, len(dates))
    ax1.set_ylim(min(lows) * 0.95, max(highs) * 1.05)
    ax1.set_title(f'{KEPCO_NAME} ({KEPCO_CODE}) - 365일 주가 차트', fontsize=16, fontweight='bold')
    ax1.set_ylabel('가격 (원)', fontsize=12)
    ax1.grid(True, alpha=0.3)

    # X축 레이블 (월 단위)
    step = max(1, len(dates) // 12)
    ax1.set_xticks(range(0, len(dates), step))
    ax1.set_xticklabels([dates[i].strftime('%Y-%m') for i in range(0, len(dates), step)], rotation=45)

    # 거래량 차트
    colors_vol = ['red' if closes[i] >= opens[i] else 'blue' for i in range(len(dates))]
    ax2.bar(range(len(dates)), volumes, color=colors_vol, alpha=0.6, width=0.8)
    ax2.set_xlim(-1, len(dates))
    ax2.set_ylabel('거래량', fontsize=12)
    ax2.set_xlabel('날짜', fontsize=12)
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.set_xticks(range(0, len(dates), step))
    ax2.set_xticklabels([dates[i].strftime('%Y-%m') for i in range(0, len(dates), step)], rotation=45)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    return output_path


def create_supply_demand_chart(supply_data, output_path):
    """수급분석 차트 생성 (외국인/기관/개인)"""
    fig, ax = plt.subplots(figsize=(14, 8))

    dates = [row['date'] for row in supply_data]
    foreigner = [int(row['foreigner_net']) for row in supply_data]
    institution = [int(row['institution_net']) for row in supply_data]
    individual = [int(row['individual_net']) for row in supply_data]

    x = range(len(dates))
    width = 0.8

    ax.bar(x, foreigner, width, label='외국인', color='#3498db', alpha=0.8)
    ax.bar(x, institution, width, bottom=foreigner, label='기관', color='#e74c3c', alpha=0.8)

    # 개인은 외국인+기관 위에
    bottom_vals = [foreigner[i] + institution[i] for i in range(len(dates))]
    ax.bar(x, individual, width, bottom=bottom_vals, label='개인', color='#2ecc71', alpha=0.8)

    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax.set_title(f'{KEPCO_NAME} - 수급 분석 (순매수)', fontsize=16, fontweight='bold')
    ax.set_ylabel('순매수 (주)', fontsize=12)
    ax.set_xlabel('날짜', fontsize=12)
    ax.legend(fontsize=12, loc='upper left')
    ax.grid(True, alpha=0.3, axis='y')

    # X축 레이블
    step = max(1, len(dates) // 12)
    ax.set_xticks(range(0, len(dates), step))
    ax.set_xticklabels([dates[i].strftime('%Y-%m') for i in range(0, len(dates), step)], rotation=45)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    return output_path


def create_recent_price_change_chart(ohlcv_data, output_path, days=14):
    """최근 N일 주가 변화 차트"""
    recent_data = ohlcv_data[-days:]

    fig, ax = plt.subplots(figsize=(12, 6))

    dates = [row['date'].strftime('%m/%d') for row in recent_data]
    closes = [float(row['close']) for row in recent_data]

    colors_line = ['red' if i > 0 and closes[i] >= closes[i-1] else 'blue'
                   for i in range(len(closes))]

    ax.plot(dates, closes, marker='o', linewidth=2, markersize=6, color='#2c3e50')

    for i, (date, close) in enumerate(zip(dates, closes)):
        color = colors_line[i]
        ax.scatter(i, close, color=color, s=80, zorder=5)

    ax.set_title(f'{KEPCO_NAME} - 최근 {days}일 주가 변화', fontsize=16, fontweight='bold')
    ax.set_ylabel('종가 (원)', fontsize=12)
    ax.set_xlabel('날짜', fontsize=12)
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)

    # 최고가/최저가 표시
    max_idx = closes.index(max(closes))
    min_idx = closes.index(min(closes))

    ax.annotate(f'고: {closes[max_idx]:,.0f}',
                xy=(max_idx, closes[max_idx]),
                xytext=(5, 5), textcoords='offset points',
                fontsize=10, color='red', fontweight='bold')

    ax.annotate(f'저: {closes[min_idx]:,.0f}',
                xy=(min_idx, closes[min_idx]),
                xytext=(5, -15), textcoords='offset points',
                fontsize=10, color='blue', fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    return output_path


def safe_int(value, default=0):
    """안전한 정수 변환"""
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


async def generate_pdf_report(holding_data, ohlcv_data, supply_data, stock_info, temp_dir):
    """PDF 리포트 생성"""
    output_file = OUTPUT_DIR / f'{KEPCO_NAME}_{KEPCO_CODE}_enhanced.pdf'

    doc = SimpleDocTemplate(
        str(output_file),
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
        fontName=FONT_NAME_BOLD,
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=20,
        alignment=1  # 중앙 정렬
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=FONT_NAME_BOLD,
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12
    )

    # 제목
    title = Paragraph(f'<b>{KEPCO_NAME} ({KEPCO_CODE})</b><br/>상세 리서치 리포트', title_style)
    story.append(title)
    story.append(Spacer(1, 0.5*cm))

    # 생성 날짜
    report_date = Paragraph(
        f'<font name="{FONT_NAME}" size=10>리포트 생성: {datetime.now().strftime("%Y년 %m월 %d일 %H:%M")}</font>',
        styles['Normal']
    )
    story.append(report_date)
    story.append(Spacer(1, 1*cm))

    # 1. 보유 현황
    if holding_data:
        story.append(Paragraph('1. 보유 현황', heading_style))

        profit_color = '#27ae60' if holding_data['profit'] >= 0 else '#e74c3c'
        profit_symbol = '🟢' if holding_data['profit'] >= 0 else '🔴'

        holding_table_data = [
            ['항목', '내용'],
            ['보유수량', f"{holding_data['quantity']:,} 주"],
            ['평균매수가', f"{holding_data['avg_price']:,.0f} 원"],
            ['현재가', f"{holding_data['current_price']:,.0f} 원"],
            ['총 투자금액', f"{holding_data['total_cost']:,.0f} 원"],
            ['평가금액', f"{holding_data['total_value']:,.0f} 원"],
            ['손익', f"{profit_symbol} {holding_data['profit']:+,.0f} 원"],
            ['손익률', f"{holding_data['profit_rate']:+.2f}%"]
        ]

        holding_table = Table(holding_table_data, colWidths=[5*cm, 10*cm])
        holding_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 1), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7'))
        ]))

        story.append(holding_table)
        story.append(Spacer(1, 1*cm))

    # 2. 365일 주가 차트
    story.append(Paragraph('2. 365일 주가 추이', heading_style))

    chart_path = temp_dir / 'candlestick_365d.png'
    create_candlestick_chart(ohlcv_data, chart_path)

    chart_img = Image(str(chart_path), width=16*cm, height=11*cm)
    story.append(chart_img)
    story.append(Spacer(1, 0.5*cm))

    story.append(PageBreak())

    # 3. 수급 분석
    story.append(Paragraph('3. 수급 분석 (외국인/기관/개인)', heading_style))

    supply_chart_path = temp_dir / 'supply_demand_365d.png'
    create_supply_demand_chart(supply_data, supply_chart_path)

    supply_img = Image(str(supply_chart_path), width=16*cm, height=9*cm)
    story.append(supply_img)
    story.append(Spacer(1, 1*cm))

    # 4. 최근 2주 주가 변화
    story.append(Paragraph('4. 최근 2주간 주가 변화', heading_style))

    recent_chart_path = temp_dir / 'recent_14d.png'
    create_recent_price_change_chart(ohlcv_data, recent_chart_path, days=14)

    recent_img = Image(str(recent_chart_path), width=16*cm, height=8*cm)
    story.append(recent_img)
    story.append(Spacer(1, 1*cm))

    story.append(PageBreak())

    # 5. 현재 시세 정보 (네이버 API)
    if stock_info:
        story.append(Paragraph('5. 현재 시세 정보', heading_style))

        stock_name = stock_info.get('stockName', KEPCO_NAME)
        market_value = stock_info.get('marketValue', 'N/A')
        industry = stock_info.get('industryCodeName', 'N/A')

        stock_info_data = [
            ['항목', '내용'],
            ['종목명', stock_name],
            ['종목코드', KEPCO_CODE],
            ['시장구분', market_value],
            ['업종', industry]
        ]

        stock_info_table = Table(stock_info_data, colWidths=[5*cm, 10*cm])
        stock_info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 1), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7'))
        ]))

        story.append(stock_info_table)
        story.append(Spacer(1, 1*cm))

    # 6. 투자 의견
    if holding_data:
        story.append(Paragraph('6. 투자 의견', heading_style))

        profit_rate = holding_data['profit_rate']

        if profit_rate > 5:
            opinion = "✅ 수익 구간: 목표 수익률 달성. 분할 매도 전략을 고려하십시오."
        elif profit_rate > 0:
            opinion = "⚠️ 소폭 수익: 추가 상승 여력을 관찰하며 시장 흐름을 확인하십시오."
        elif profit_rate > -3:
            opinion = "⚠️ 소폭 손실: 단기 변동성으로 판단. 펀더멘털을 재확인하십시오."
        else:
            opinion = "❌ 손실 구간: 손절 기준 재검토 및 포지션 축소를 고려하십시오."

        opinion_para = Paragraph(
            f'<font name="{FONT_NAME}" size=12>{opinion}</font>',
            styles['Normal']
        )
        story.append(opinion_para)
        story.append(Spacer(1, 0.5*cm))

    # 면책 조항
    story.append(Spacer(1, 1*cm))
    disclaimer = Paragraph(
        f'<font name="{FONT_NAME}" size=9 color="#7f8c8d">'
        f'본 리포트는 투자 참고 자료이며, 투자 판단의 최종 책임은 투자자에게 있습니다.<br/>'
        f'데이터 출처: pykrx, 네이버 금융 API<br/>'
        f'생성일시: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        f'</font>',
        styles['Normal']
    )
    story.append(disclaimer)

    # PDF 생성
    doc.build(story)

    return output_file


async def main():
    """메인 실행 함수"""
    print("=" * 80)
    print(f"{KEPCO_NAME} ({KEPCO_CODE}) 향상된 리포트 생성")
    print("=" * 80)
    print()

    temp_dir = Path('/tmp/kepco_enhanced_charts')
    temp_dir.mkdir(exist_ok=True)

    try:
        await db.connect()

        # 데이터 수집
        print("📊 데이터 조회 중...")
        ohlcv_data = await fetch_ohlcv_data(365)
        supply_data = await fetch_supply_demand_data(365)
        holding_data = await fetch_holding_data()
        stock_info = await fetch_stock_info_naver(KEPCO_CODE)

        print(f"   - OHLCV: {len(ohlcv_data)}개")
        print(f"   - 수급: {len(supply_data)}개")
        print(f"   - 보유: {'있음' if holding_data else '없음'}")
        print()

        # PDF 생성
        print("📝 PDF 생성 중...")
        output_file = await generate_pdf_report(
            holding_data,
            ohlcv_data,
            supply_data,
            stock_info,
            temp_dir
        )

        print()
        print("=" * 80)
        print("✅ PDF 생성 완료")
        print("=" * 80)
        print(f"📁 파일 위치: {output_file}")
        print()

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
