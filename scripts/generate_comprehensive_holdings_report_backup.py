"""
보유종목 종합 리서치 리포트 생성 (전문 애널리스트 수준)

데이터 소스:
- PostgreSQL Database (보유현황, 재무데이터)
- Daum Finance API (재무지표, 투자자 매매동향)
- Naver Finance (동종업종 비교, 뉴스)
- FnGuide (컨센서스, 목표가)
- Gemini AI (투자 분석 및 전망)
"""
import asyncio
import os
import sys
from datetime import datetime
from decimal import Decimal
import aiohttp
import asyncpg
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
import google.generativeai as genai

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.fetchers.tier2_official_apis.daum_fetcher import DaumFetcher
from src.fetchers.tier4_browser_automation.naver_main_comprehensive_fetcher import NaverMainComprehensiveFetcher

# 환경 변수에서 Gemini API 키 로드
from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Gemini AI 설정
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-2.5-flash')  # 빠르고 안정적인 최신 모델
else:
    gemini_model = None
    print("⚠️  Gemini API 키가 설정되지 않았습니다.")

# DB 연결 설정
DB_CONFIG = {
    'database': 'stock_investment_db',
    'user': 'wonny',
    'host': 'localhost',
    'port': 5432
}

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
        print(f"✅ 한글 폰트 로드 성공")
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


def format_number(num):
    """숫자를 천단위 콤마로 포맷"""
    if num is None or num == 'N/A':
        return "N/A"
    try:
        return f"{int(float(num)):,}"
    except:
        return str(num)


async def fetch_holdings_from_db():
    """데이터베이스에서 보유종목 조회"""
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        rows = await conn.fetch('''
            SELECT stock_code, stock_name, quantity, avg_buy_price,
                   current_price, profit_loss, profit_loss_rate
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
                'current_price': float(row['current_price']),
                'profit': float(row['profit_loss']),
                'profit_rate': float(row['profit_loss_rate']) if row['profit_loss_rate'] else 0.0
            }
        return holdings
    finally:
        await conn.close()


async def fetch_daily_ohlcv_from_db(stock_code: str, days: int = 30):
    """데이터베이스에서 일별 OHLCV 조회"""
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        rows = await conn.fetch('''
            SELECT date, open, high, low, close, volume
            FROM daily_ohlcv
            WHERE stock_code = $1
            ORDER BY date DESC
            LIMIT $2
        ''', stock_code, days)

        # 날짜순으로 정렬 (오래된 것부터)
        return list(reversed(rows))
    finally:
        await conn.close()


async def fetch_daum_data(stock_code: str):
    """Daum Finance 데이터 수집"""
    daum_config = {
        'site_name_ko': 'Daum Finance',
        'data_type': 'daum_comprehensive',
        'domain_id': 1
    }
    daum_fetcher = DaumFetcher(site_id=60, config=daum_config)
    return await daum_fetcher.fetch(stock_code)


async def fetch_naver_data(stock_code: str):
    """Naver Finance 데이터 수집"""
    naver_config = {
        'headless': True,
        'viewport': {'width': 1920, 'height': 1080},
        'data_type': 'naver_main_comprehensive',
        'domain_id': 1
    }
    naver_fetcher = NaverMainComprehensiveFetcher(site_id=61, config=naver_config)
    try:
        await naver_fetcher.initialize()
        return await naver_fetcher.fetch_data(stock_code)
    finally:
        await naver_fetcher.cleanup()


async def get_gemini_investment_analysis(stock_name: str, stock_code: str, holding_data: dict,
                                        daum_data: dict, naver_data: dict):
    """Gemini AI를 활용한 종합 투자 분석"""
    if not gemini_model:
        return {
            'investment_points': '• Gemini API 미설정',
            'risk_factors': '• Gemini API 미설정',
            'investment_opinion': 'Gemini API가 설정되지 않았습니다.',
            'target_price': 'N/A'
        }

    # 데이터 요약
    quotes = daum_data.get('quotes', {})
    current_price = quotes.get('tradePrice', holding_data.get('current_price', 0))

    sectors = daum_data.get('sectors', {}).get('data', [])
    financial_info = sectors[0] if sectors else {}

    investor_trading = daum_data.get('investor_trading', {}).get('data', [])[:5]

    prompt = f"""
당신은 한국 주식시장 전문 애널리스트입니다. 다음 종목에 대한 상세한 투자 분석 리포트를 작성해주세요.

**종목 정보**
- 종목명: {stock_name} ({stock_code})
- 현재가: {format_number(current_price)}원
- 보유수량: {holding_data['quantity']}주
- 평균매수가: {format_number(holding_data['avg_price'])}원
- 현재 손익률: {holding_data['profit_rate']:.2f}%

**재무 지표**
- 매출액: {format_number(financial_info.get('netSales', 0))}원
- 영업이익: {format_number(financial_info.get('operatingProfit', 0))}원
- 순이익: {format_number(financial_info.get('netIncome', 0))}원
- EPS: {financial_info.get('eps', 'N/A')}원
- ROE: {financial_info.get('roe', 0)*100:.2f}% (if available)
- 외국인비율: {financial_info.get('foreignRatio', 0)*100:.2f}%

**최근 투자자 매매동향 (5일)**
{chr(10).join([f"- {item.get('date', '')[:10]}: 외국인 {format_number(item.get('foreignStraightPurchaseVolume', 0))}주, 기관 {format_number(item.get('institutionStraightPurchaseVolume', 0))}주" for item in investor_trading])}

다음 형식으로 답변해주세요:

## 투자 포인트 (3-5개)
• [핵심 투자 포인트 1]
• [핵심 투자 포인트 2]
• [핵심 투자 포인트 3]

## 리스크 요인 (2-3개)
• [주요 리스크 1]
• [주요 리스크 2]

## 종합 투자 의견
[200-300자 분량의 종합 투자 의견. 현재 보유 중인 상황을 고려하여 보유 유지, 추가 매수, 일부 매도 등의 전략 제시]

## 목표가
[합리적인 근거를 바탕으로 한 목표가 제시 (단위: 원)]
"""

    try:
        response = gemini_model.generate_content(prompt)
        analysis_text = response.text

        # 응답 파싱
        sections = {
            'investment_points': '',
            'risk_factors': '',
            'investment_opinion': '',
            'target_price': 'N/A'
        }

        lines = analysis_text.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if '## 투자 포인트' in line or '##투자 포인트' in line:
                current_section = 'investment_points'
            elif '## 리스크 요인' in line or '##리스크 요인' in line:
                current_section = 'risk_factors'
            elif '## 종합 투자 의견' in line or '##종합 투자 의견' in line:
                current_section = 'investment_opinion'
            elif '## 목표가' in line or '##목표가' in line:
                current_section = 'target_price'
            elif line and current_section:
                if current_section == 'target_price':
                    # 목표가에서 숫자 추출
                    import re
                    numbers = re.findall(r'[\d,]+', line)
                    if numbers:
                        sections[current_section] = numbers[0].replace(',', '')
                else:
                    sections[current_section] += line + '\n'

        return sections

    except Exception as e:
        print(f"⚠️  Gemini AI 분석 실패: {e}")
        return {
            'investment_points': f'• AI 분석 실패: {str(e)}',
            'risk_factors': '• 데이터 부족',
            'investment_opinion': 'AI 분석을 완료할 수 없습니다.',
            'target_price': 'N/A'
        }


def create_investor_trading_chart(stock_name, investor_data, temp_dir, stock_code):
    """투자자 매매동향 차트 생성"""
    if not investor_data:
        return None

    chart_path = os.path.join(temp_dir, f"{stock_code}_investor_chart.png")

    # 최근 10일 데이터
    recent_data = investor_data[:10]
    dates = [item.get('date', '')[:10] for item in recent_data]
    foreign = [item.get('foreignStraightPurchaseVolume', 0) for item in recent_data]
    institution = [item.get('institutionStraightPurchaseVolume', 0) for item in recent_data]

    fig, ax = plt.subplots(figsize=(12, 6))

    x = range(len(dates))
    width = 0.35

    ax.bar([i - width/2 for i in x], foreign, width, label='외국인', color='#3498db', alpha=0.8)
    ax.bar([i + width/2 for i in x], institution, width, label='기관', color='#e74c3c', alpha=0.8)

    ax.set_xlabel('날짜', fontsize=11)
    ax.set_ylabel('순매수량 (주)', fontsize=11)
    ax.set_title(f'{stock_name} - 투자자 매매동향 (최근 10일)', fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha='right')
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

    plt.tight_layout()
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()

    return chart_path


def create_stock_price_chart(stock_name, ohlcv_data, temp_dir, stock_code):
    """주가 차트 생성 (캔들스틱)"""
    if not ohlcv_data or len(ohlcv_data) == 0:
        return None

    chart_path = os.path.join(temp_dir, f"{stock_code}_price_chart.png")

    dates = [row['date'].strftime('%m/%d') for row in ohlcv_data]
    opens = [float(row['open']) for row in ohlcv_data]
    highs = [float(row['high']) for row in ohlcv_data]
    lows = [float(row['low']) for row in ohlcv_data]
    closes = [float(row['close']) for row in ohlcv_data]
    volumes = [float(row['volume']) for row in ohlcv_data]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [3, 1]})

    # 캔들스틱 차트
    for i in range(len(dates)):
        color = '#e74c3c' if closes[i] < opens[i] else '#27ae60'  # 하락: 빨강, 상승: 초록
        # 캔들 몸통
        ax1.plot([i, i], [opens[i], closes[i]], color=color, linewidth=8, solid_capstyle='round')
        # 위 꼬리
        ax1.plot([i, i], [closes[i] if closes[i] > opens[i] else opens[i], highs[i]],
                color=color, linewidth=1)
        # 아래 꼬리
        ax1.plot([i, i], [lows[i], opens[i] if closes[i] > opens[i] else closes[i]],
                color=color, linewidth=1)

    ax1.set_title(f'{stock_name} - 주가 추이 (최근 30일)', fontsize=14, fontweight='bold', pad=15)
    ax1.set_ylabel('가격 (원)', fontsize=11)
    ax1.set_xticks(range(0, len(dates), max(1, len(dates)//10)))
    ax1.set_xticklabels([dates[i] for i in range(0, len(dates), max(1, len(dates)//10))], rotation=45, ha='right')
    ax1.grid(axis='y', alpha=0.3)

    # 거래량 차트
    colors_vol = ['#e74c3c' if closes[i] < opens[i] else '#27ae60' for i in range(len(dates))]
    ax2.bar(range(len(dates)), volumes, color=colors_vol, alpha=0.6)
    ax2.set_ylabel('거래량', fontsize=11)
    ax2.set_xlabel('날짜', fontsize=11)
    ax2.set_xticks(range(0, len(dates), max(1, len(dates)//10)))
    ax2.set_xticklabels([dates[i] for i in range(0, len(dates), max(1, len(dates)//10))], rotation=45, ha='right')
    ax2.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()

    return chart_path


async def generate_comprehensive_report(stock_code, holding_data, output_dir, temp_dir):
    """종합 리포트 생성"""
    stock_name = holding_data['name']
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"📝 {stock_name} ({stock_code}) 종합 리포트 생성 중...")

    # 데이터 수집
    print(f"  📊 Daum Finance 데이터 수집...")
    daum_data = await fetch_daum_data(stock_code)

    print(f"  📊 Naver Finance 데이터 수집...")
    naver_data = await fetch_naver_data(stock_code)

    print(f"  🤖 Gemini AI 투자 분석...")
    gemini_analysis = await get_gemini_investment_analysis(
        stock_name, stock_code, holding_data, daum_data, naver_data
    )

    # 차트 생성
    investor_data = daum_data.get('investor_trading', {}).get('data', [])
    chart_path = create_investor_trading_chart(stock_name, investor_data, temp_dir, stock_code)

    # PDF 생성
    output_path = os.path.join(output_dir, f"{stock_name}_{stock_code}_comprehensive.pdf")

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
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=10,
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
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=15,
        borderWidth=0,
        borderColor=colors.HexColor('#3498db'),
        borderPadding=5,
        backColor=colors.HexColor('#ecf0f1'),
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

    # ========== 커버 페이지 ==========
    elements.append(Paragraph(f"{stock_name} ({stock_code})", title_style))
    elements.append(Paragraph(f"종합 투자 리서치 리포트", subtitle_style))

    # 투자 의견 박스
    quotes = daum_data.get('quotes', {})
    current_price = quotes.get('tradePrice', holding_data.get('current_price', 0))
    target_price_str = gemini_analysis.get('target_price', 'N/A')

    try:
        target_price = int(target_price_str.replace(',', '')) if target_price_str != 'N/A' else 0
        upside = ((target_price - current_price) / current_price * 100) if current_price > 0 and target_price > 0 else 0
    except:
        target_price = 0
        upside = 0

    opinion_data = [
        ['투자의견', '목표가', '현재가', '상승여력'],
        ['보유 유지',
         f"{format_number(target_price)}원" if target_price > 0 else 'N/A',
         f"{format_number(current_price)}원",
         f"{upside:.1f}%" if upside > 0 else 'N/A']
    ]

    opinion_table = Table(opinion_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
    opinion_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f0f0')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))

    elements.append(opinion_table)
    elements.append(Spacer(1, 0.5*cm))

    # 주요 지표
    sectors = daum_data.get('sectors', {}).get('data', [])
    financial_info = sectors[0] if sectors else {}

    key_metrics_data = [
        ['지표', '값', '지표', '값'],
        ['시가총액', f"{format_number(quotes.get('marketCap', 0))}원",
         'EPS', f"{format_number(financial_info.get('eps', 0))}원"],
        ['매출액', f"{format_number(financial_info.get('netSales', 0))}원",
         'ROE', f"{financial_info.get('roe', 0)*100:.2f}%" if financial_info.get('roe') else 'N/A'],
        ['영업이익', f"{format_number(financial_info.get('operatingProfit', 0))}원",
         '외국인비율', f"{financial_info.get('foreignRatio', 0)*100:.2f}%" if financial_info.get('foreignRatio') else 'N/A'],
    ]

    metrics_table = Table(key_metrics_data, colWidths=[3.5*cm, 4.5*cm, 3.5*cm, 4.5*cm])
    metrics_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (2, 0), (2, -1), 'LEFT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    elements.append(metrics_table)
    elements.append(Spacer(1, 0.3*cm))

    elements.append(Paragraph(
        f"<font size=8>리포트 생성: {timestamp} | AI 분석: Gemini Pro</font>",
        ParagraphStyle('DataSource', parent=body_style, fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    ))

    elements.append(Spacer(1, 0.8*cm))

    # ========== 투자 포인트 (AI 분석) ==========
    elements.append(Paragraph("💡 투자 포인트", section_style))
    elements.append(Paragraph(
        gemini_analysis.get('investment_points', '• 데이터 부족').replace('\n', '<br/>'),
        body_style
    ))
    elements.append(Spacer(1, 0.5*cm))

    # ========== 보유 현황 ==========
    elements.append(Paragraph("📊 보유 현황", section_style))

    total_investment = holding_data['quantity'] * holding_data['avg_price']
    current_value = holding_data['quantity'] * current_price

    holdings_data = [
        ['항목', '값'],
        ['보유수량', f"{format_number(holding_data['quantity'])}주"],
        ['평균매수가', f"{format_number(holding_data['avg_price'])}원"],
        ['현재가', f"{format_number(current_price)}원"],
        ['투자금액', f"{format_number(total_investment)}원"],
        ['평가금액', f"{format_number(current_value)}원"],
        ['손익', f"{format_number(holding_data['profit'])}원"],
        ['손익률', f"{holding_data['profit_rate']:.2f}%"],
    ]

    holdings_table = Table(holdings_data, colWidths=[6*cm, 10*cm])
    holdings_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    elements.append(holdings_table)
    elements.append(Spacer(1, 0.5*cm))

    # ========== 투자자 매매동향 차트 ==========
    elements.append(Paragraph("📈 투자자 매매동향", section_style))

    if chart_path and os.path.exists(chart_path):
        elements.append(Image(chart_path, width=16*cm, height=8*cm))
        elements.append(Spacer(1, 0.3*cm))

    # 투자자 매매동향 테이블
    if investor_data:
        investor_table_data = [['날짜', '종가', '외국인 순매수', '기관 순매수', '외국인보유율']]

        for item in investor_data[:10]:
            investor_table_data.append([
                item.get('date', '')[:10],
                f"{format_number(item.get('tradePrice', 0))}",
                f"{format_number(item.get('foreignStraightPurchaseVolume', 0))}",
                f"{format_number(item.get('institutionStraightPurchaseVolume', 0))}",
                f"{item.get('foreignOwnSharesRate', 0)*100:.2f}%" if item.get('foreignOwnSharesRate') else 'N/A'
            ])

        investor_table = Table(investor_table_data, colWidths=[3*cm, 3*cm, 3.5*cm, 3*cm, 3.5*cm])
        investor_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
            ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(investor_table)
        elements.append(Spacer(1, 0.5*cm))

    # ========== 동종업종 비교 ==========
    elements.append(PageBreak())
    elements.append(Paragraph("📊 동종업종 비교", section_style))

    peers = naver_data.get('peer_comparison', [])
    if peers and len(peers) > 3:
        # 동종업종 테이블 (처음 5개 지표만)
        peer_table_data = []
        for peer in peers[:8]:  # 처음 8개 지표
            company = peer.get('company', '')
            data = peer.get('data', [])
            if data:
                peer_table_data.append([company] + data[:5])

        if peer_table_data:
            peer_table = Table(peer_table_data, colWidths=[3.5*cm] + [2.5*cm]*5)
            peer_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), FONT_NAME_BOLD),
                ('FONTNAME', (1, 0), (-1, -1), FONT_NAME),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))

            elements.append(peer_table)
            elements.append(Spacer(1, 0.5*cm))

    # ========== 리스크 요인 (AI 분석) ==========
    elements.append(Paragraph("⚠️ 리스크 요인", section_style))
    elements.append(Paragraph(
        gemini_analysis.get('risk_factors', '• 데이터 부족').replace('\n', '<br/>'),
        body_style
    ))
    elements.append(Spacer(1, 0.5*cm))

    # ========== 종합 투자 의견 (AI 분석) ==========
    elements.append(Paragraph("💼 종합 투자 의견", section_style))
    elements.append(Paragraph(
        gemini_analysis.get('investment_opinion', 'AI 분석 데이터 없음'),
        body_style
    ))
    elements.append(Spacer(1, 0.5*cm))

    # ========== 데이터 출처 ==========
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(
        f"<font size=8>데이터 출처: PostgreSQL DB, Daum Finance API, Naver Finance API, Gemini Pro AI | 생성: {timestamp}</font>",
        ParagraphStyle('DataSource2', parent=body_style, fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    ))

    # ========== 면책 조항 ==========
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
    AI 분석 결과는 참고용이며, 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.
    과거 데이터 및 AI 분석이 미래 수익을 보장하지 않습니다.
    """
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph(disclaimer_text, disclaimer_style))

    # PDF 빌드
    doc.build(elements)

    print(f"  ✅ {stock_name} 종합 리포트 생성 완료")

    return output_path


async def main():
    """메인 실행 함수"""
    print("=" * 70)
    print("보유종목 종합 리서치 리포트 생성 (전문 애널리스트 수준)")
    print("=" * 70)
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

    # 각 보유종목에 대한 종합 리포트 생성
    generated_reports = []

    for stock_code, holding_data in holdings.items():
        try:
            report_path = await generate_comprehensive_report(
                stock_code,
                holding_data,
                output_dir,
                temp_dir
            )
            generated_reports.append(report_path)

            # API 호출 간격 (과부하 방지)
            await asyncio.sleep(2)

        except Exception as e:
            print(f"❌ {holding_data['name']} ({stock_code}) 리포트 생성 실패: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 70)
    print(f"✅ 종합 리포트 생성 완료: {len(generated_reports)}개")
    print("=" * 70)
    print()

    for report_path in generated_reports:
        print(f"  - {report_path}")


if __name__ == '__main__':
    asyncio.run(main())
