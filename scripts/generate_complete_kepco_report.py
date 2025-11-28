"""
한국전력 완전판 리포트 생성

Features:
1-8: 모든 요구사항 포함
"""
import sys
import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pykrx import stock

from src.config.database import db
from src.analysis.investment_analysis import generate_investment_points, get_investment_recommendation

# 환경변수 로드
load_dotenv()

# 한국전력 종목코드
KEPCO_CODE = '015760'
KEPCO_NAME = '한국전력'

# 한글 폰트
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False


def setup_korean_font():
    """PDF용 한글 폰트"""
    try:
        pdfmetrics.registerFont(TTFont('NanumGothic', '/Library/Fonts/NanumGothic.ttf'))
        return 'NanumGothic'
    except:
        try:
            pdfmetrics.registerFont(TTFont('AppleGothic', '/System/Library/Fonts/Supplemental/AppleGothic.ttf'))
            return 'AppleGothic'
        except:
            return 'Helvetica'


def analyze_with_gemini(fnguide_data: dict) -> Optional[str]:
    """Gemini AI를 사용한 투자 포인트 분석"""
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("⚠️ GEMINI_API_KEY가 설정되지 않음 - rule-based 분석 사용")
            return None

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')

        financial_summary = fnguide_data.get('financial_summary', {})
        valuation_metrics = fnguide_data.get('valuation_metrics', {})
        analyst_consensus = fnguide_data.get('analyst_consensus', {})

        prompt = f"""
당신은 전문 주식 애널리스트입니다. 다음 재무 데이터를 분석하여 투자 포인트를 도출해주세요.

## 재무 데이터

### 재무제표 요약
- 연도: {financial_summary.get('years', [])}
- 매출액 (억원): {financial_summary.get('revenue', [])}
- 영업이익 (억원): {financial_summary.get('operating_profit', [])}
- 순이익 (억원): {financial_summary.get('net_profit', [])}
- ROE (%): {financial_summary.get('roe', [])}

### 밸류에이션
- PER: {valuation_metrics.get('per', 'N/A')}배
- PBR: {valuation_metrics.get('pbr', 'N/A')}배
- 배당수익률: {valuation_metrics.get('dividend_yield', 'N/A')}%

### 애널리스트 컨센서스
- 목표주가: {analyst_consensus.get('target_price', 'N/A')}원
- 투자의견 분포: {analyst_consensus.get('opinion_distribution', {})}
- 커버리지: {analyst_consensus.get('analyst_count', 'N/A')}명

## 요청사항

다음 형식으로 투자 포인트를 분석해주세요. 각 항목은 bullet point로 작성하되,
분석 내용은 명확하고 구체적인 수치를 포함해주세요:

### 1. 재무 건전성
(매출 성장성, 수익성 개선 여부를 분석)

### 2. 밸류에이션
(PER, PBR, 배당수익률 기반 저평가/고평가 판단)

### 3. 애널리스트 의견
(목표주가 상승여력, 투자의견 분포 해석)

### 4. 종합 투자 의견
(위 분석을 종합한 1-2문장의 투자 의견)
"""

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        print(f"⚠️ Gemini API 오류: {e} - rule-based 분석 사용")
        return None


def create_candlestick_chart(ohlcv_data, output_path):
    """캔들스틱 차트"""
    dates = [row['date'] for row in ohlcv_data]
    opens = [float(row['open']) for row in ohlcv_data]
    highs = [float(row['high']) for row in ohlcv_data]
    lows = [float(row['low']) for row in ohlcv_data]
    closes = [float(row['close']) for row in ohlcv_data]
    volumes = [float(row['volume']) for row in ohlcv_data]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})

    width = 0.6
    for i, (date, open_, high, low, close) in enumerate(zip(dates, opens, highs, lows, closes)):
        color = 'red' if close >= open_ else 'blue'
        ax1.plot([i, i], [low, high], color=color, linewidth=0.5)
        ax1.add_patch(Rectangle((i - width/2, min(open_, close)), width, abs(close - open_), 
                                facecolor=color, edgecolor=color))

    ax1.set_title(f'{KEPCO_NAME} 주가 추이 (365일)', fontsize=14, fontweight='bold')
    ax1.set_ylabel('주가 (원)', fontsize=10)
    ax1.grid(True, alpha=0.3)

    colors_volume = ['red' if closes[i] >= opens[i] else 'blue' for i in range(len(closes))]
    ax2.bar(range(len(volumes)), volumes, color=colors_volume, alpha=0.5)
    ax2.set_ylabel('거래량', fontsize=10)
    ax2.set_xlabel('날짜', fontsize=10)
    ax2.grid(True, alpha=0.3)

    step = max(len(dates) // 10, 1)
    ax2.set_xticks(range(0, len(dates), step))
    ax2.set_xticklabels([dates[i].strftime('%m/%d') for i in range(0, len(dates), step)], rotation=45)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def create_supply_demand_chart(supply_data, output_path):
    """수급 분석 차트"""
    dates = [row['date'] for row in supply_data]
    foreigner = [float(row['foreigner_net']) / 1000 for row in supply_data]
    institution = [float(row['institution_net']) / 1000 for row in supply_data]
    individual = [float(row['individual_net']) / 1000 for row in supply_data]

    fig, ax = plt.subplots(figsize=(12, 6))

    x = range(len(dates))
    ax.bar(x, foreigner, label='외국인', alpha=0.7, color='green')
    ax.bar(x, institution, bottom=foreigner, label='기관', alpha=0.7, color='blue')
    individual_bottom = [f + i for f, i in zip(foreigner, institution)]
    ax.bar(x, individual, bottom=individual_bottom, label='개인', alpha=0.7, color='orange')

    ax.set_title(f'{KEPCO_NAME} 수급 분석 (365일)', fontsize=14, fontweight='bold')
    ax.set_ylabel('순매수량 (천주)', fontsize=10)
    ax.set_xlabel('날짜', fontsize=10)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

    step = max(len(dates) // 10, 1)
    ax.set_xticks(range(0, len(dates), step))
    ax.set_xticklabels([dates[i].strftime('%m/%d') for i in range(0, len(dates), step)], rotation=45)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def create_recent_price_chart(ohlcv_data, output_path, days=14):
    """최근 N일 차트"""
    recent_data = ohlcv_data[-days:] if len(ohlcv_data) >= days else ohlcv_data

    dates = [row['date'] for row in recent_data]
    closes = [float(row['close']) for row in recent_data]
    highs = [float(row['high']) for row in recent_data]
    lows = [float(row['low']) for row in recent_data]

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(range(len(dates)), closes, marker='o', linewidth=2, markersize=6, color='blue', label='종가')
    ax.fill_between(range(len(dates)), lows, highs, alpha=0.2, color='gray', label='고가-저가 범위')

    max_idx = closes.index(max(closes))
    min_idx = closes.index(min(closes))
    ax.annotate(f'최고: {closes[max_idx]:,}원', 
                xy=(max_idx, closes[max_idx]), xytext=(max_idx, closes[max_idx] * 1.02),
                ha='center', fontsize=9, color='red', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='red', lw=1))
    ax.annotate(f'최저: {closes[min_idx]:,}원', 
                xy=(min_idx, closes[min_idx]), xytext=(min_idx, closes[min_idx] * 0.98),
                ha='center', fontsize=9, color='blue', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='blue', lw=1))

    ax.set_title(f'{KEPCO_NAME} 최근 {days}일 주가 변화', fontsize=14, fontweight='bold')
    ax.set_ylabel('주가 (원)', fontsize=10)
    ax.set_xlabel('날짜', fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    ax.set_xticks(range(len(dates)))
    ax.set_xticklabels([d.strftime('%m/%d') for d in dates], rotation=45)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


async def generate_pdf_report(ohlcv_data, supply_data, fnguide_data, sector_info, output_path):
    """완전판 PDF 생성"""
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []

    korean_font = setup_korean_font()

    # 스타일
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontName=korean_font,
                                 fontSize=24, textColor=colors.HexColor('#1f4788'), spaceAfter=30, alignment=TA_CENTER)
    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontName=korean_font,
                                   fontSize=16, textColor=colors.HexColor('#2c5aa0'), spaceAfter=12, spaceBefore=12)
    normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontName=korean_font, fontSize=10, leading=14)

    # 제목
    story.append(Paragraph(f'{KEPCO_NAME} ({KEPCO_CODE}) 종합 투자 리포트', title_style))
    story.append(Paragraph(f'작성일: {datetime.now().strftime("%Y년 %m월 %d일")}', normal_style))
    story.append(Spacer(1, 0.3*inch))

    # 1. 회사 정보
    story.append(Paragraph('1. 회사 정보', heading_style))
    if fnguide_data and fnguide_data.get('company_info'):
        company_info = fnguide_data['company_info']
        company_data = [
            ['회사명', company_info.get('company_name', KEPCO_NAME)],
            ['시가총액', f"{company_info.get('market_cap', 'N/A')}조원"],
            ['업종', sector_info.get('sector', 'N/A')],
        ]
        company_table = Table(company_data, colWidths=[2*inch, 4*inch])
        company_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), korean_font, 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f4f8')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(company_table)
    story.append(Spacer(1, 0.2*inch))

    # 2. 재무제표
    if fnguide_data and fnguide_data.get('financial_summary'):
        story.append(PageBreak())
        story.append(Paragraph('2. 재무제표 (최근 4개년 + 추정)', heading_style))

        financials = fnguide_data['financial_summary']
        years = financials.get('years', [])[1:5]
        revenue = financials.get('revenue', [])[1:5]
        op_profit = financials.get('operating_profit', [])[1:5]
        net_profit = financials.get('net_profit', [])[1:5]
        eps = financials.get('eps', [])[1:5]

        if years:
            financial_data = [['구분'] + [str(y)[:7] for y in years]]
            financial_data.append(['매출액 (억원)'] + [f'{int(r):,}' if r else '-' for r in revenue])
            financial_data.append(['영업이익 (억원)'] + [f'{int(p):,}' if p else '-' for p in op_profit])
            financial_data.append(['당기순이익 (억원)'] + [f'{int(p):,}' if p else '-' for p in net_profit])
            financial_data.append(['EPS (원)'] + [f'{int(e):,}' if e else '-' for e in eps])

            financial_table = Table(financial_data, colWidths=[1.5*inch] + [1.2*inch]*4)
            financial_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), korean_font, 9),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#e8f4f8')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(financial_table)
            story.append(Spacer(1, 0.2*inch))

    # 3. 투자 포인트 (Gemini AI 분석)
    story.append(PageBreak())
    story.append(Paragraph('3. 투자 포인트 (AI 전문 분석)', heading_style))

    if fnguide_data:
        # Gemini AI 분석 시도
        print("Gemini AI 투자 분석 생성 중...")
        gemini_analysis = analyze_with_gemini(fnguide_data)

        if gemini_analysis:
            # Gemini AI 분석 결과 출력
            print("✅ Gemini AI 분석 완료")
            # 마크다운 형식을 PDF 형식으로 변환
            lines = gemini_analysis.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 0.1*inch))
                elif line.startswith('###'):
                    # 소제목
                    subtitle = line.replace('###', '').strip()
                    subtitle_style = ParagraphStyle(
                        'SubTitle',
                        parent=normal_style,
                        fontSize=12,
                        textColor=colors.HexColor('#1a5490'),
                        spaceAfter=6,
                        fontName=korean_font
                    )
                    story.append(Paragraph(f'<b>{subtitle}</b>', subtitle_style))
                elif line.startswith('*') or line.startswith('-'):
                    # 불렛 포인트
                    text = line.lstrip('*-').strip()
                    story.append(Paragraph(f'• {text}', normal_style))
                elif line.startswith('#'):
                    # 제목 (무시)
                    continue
                else:
                    # 일반 텍스트
                    story.append(Paragraph(line, normal_style))
        else:
            # Fallback: Rule-based 분석
            print("Rule-based 분석 사용")
            investment_points = generate_investment_points(fnguide_data)
            recommendation = get_investment_recommendation(fnguide_data)

            if investment_points['all_points']:
                points_text = '<br/>'.join([f'• {p}' for p in investment_points['all_points']])
                story.append(Paragraph(points_text, normal_style))
                story.append(Spacer(1, 0.1*inch))

            story.append(Paragraph(f'<b>종합 투자 의견:</b> {recommendation}', normal_style))
    else:
        story.append(Paragraph('데이터 부족으로 투자 포인트를 분석할 수 없습니다.', normal_style))

    story.append(Spacer(1, 0.2*inch))

    # 4. 애널리스트 컨센서스
    story.append(Paragraph('4. 증권사 투자의견', heading_style))
    if fnguide_data and fnguide_data.get('analyst_consensus'):
        consensus = fnguide_data['analyst_consensus']

        consensus_data = [
            ['분석 애널리스트 수', f"{consensus.get('analyst_count', 'N/A')}명"],
        ]

        consensus_table = Table(consensus_data, colWidths=[2*inch, 4*inch])
        consensus_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), korean_font, 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f4f8')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(consensus_table)
        story.append(Spacer(1, 0.2*inch))

    # 5. 365일 주가 차트
    story.append(PageBreak())
    story.append(Paragraph('5. 주가 추이 (365일)', heading_style))
    candlestick_path = '/tmp/kepco_candlestick.png'
    create_candlestick_chart(ohlcv_data, candlestick_path)
    story.append(Image(candlestick_path, width=6.5*inch, height=4.3*inch))
    story.append(Spacer(1, 0.2*inch))

    # 6. 수급 분석
    story.append(PageBreak())
    story.append(Paragraph('6. 수급 분석 (외국인/기관/개인)', heading_style))
    supply_path = '/tmp/kepco_supply.png'
    create_supply_demand_chart(supply_data, supply_path)
    story.append(Image(supply_path, width=6.5*inch, height=3.9*inch))
    story.append(Spacer(1, 0.2*inch))

    # 7. 최근 14일 주가
    story.append(PageBreak())
    story.append(Paragraph('7. 최근 2주간 주가 변화', heading_style))
    recent_path = '/tmp/kepco_recent.png'
    create_recent_price_chart(ohlcv_data, recent_path, days=14)
    story.append(Image(recent_path, width=6*inch, height=3*inch))
    story.append(Spacer(1, 0.2*inch))

    # 8. Valuation 지표
    if fnguide_data and fnguide_data.get('valuation_metrics'):
        story.append(Paragraph('8. Valuation 지표', heading_style))
        metrics = fnguide_data['valuation_metrics']

        metrics_data = [
            ['PER', f"{metrics.get('per', 'N/A')}"],
            ['PBR', f"{metrics.get('pbr', 'N/A')}"],
            ['배당수익률', f"{metrics.get('dividend_yield', 'N/A')}%"],
        ]

        metrics_table = Table(metrics_data, colWidths=[2*inch, 4*inch])
        metrics_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), korean_font, 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f4f8')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(metrics_table)

    # PDF 생성
    doc.build(story)
    print(f"✅ PDF 생성 완료: {output_path}")


async def main():
    print("=" * 80)
    print("한국전력 완전판 리포트 생성")
    print("=" * 80)
    print()

    try:
        await db.connect()

        # 1. OHLCV 데이터
        print("📊 OHLCV 데이터...")
        ohlcv_query = "SELECT * FROM daily_ohlcv WHERE stock_code = $1 ORDER BY date ASC"
        ohlcv_data = await db.fetch(ohlcv_query, KEPCO_CODE)
        print(f"   {len(ohlcv_data)}건")

        # 2. 수급 데이터
        print("📈 수급 데이터...")
        supply_query = "SELECT * FROM stock_supply_demand WHERE stock_code = $1 ORDER BY date ASC"
        supply_data = await db.fetch(supply_query, KEPCO_CODE)
        print(f"   {len(supply_data)}건")

        # 3. FnGuide 데이터
        print("💼 FnGuide 데이터...")
        fnguide_query = "SELECT data_content->'data' as fnguide_data FROM collected_data WHERE ticker = $1 AND site_id = 53 ORDER BY collected_at DESC LIMIT 1"
        fnguide_row = await db.fetchrow(fnguide_query, KEPCO_CODE)
        fnguide_data = json.loads(fnguide_row['fnguide_data']) if fnguide_row else None
        print(f"   {'있음' if fnguide_data else '없음'}")

        # 4. 섹터 정보
        print("🏢 섹터 정보...")
        try:
            market_data = stock.get_market_ticker_list(market="ALL")
            if KEPCO_CODE in market_data:
                # pykrx에서 섹터 정보 가져오기
                sector_info = {
                    'sector': '전기·가스·증기 및 수도사업',  # 한국전력 업종
                    'market': 'KOSPI'
                }
            else:
                sector_info = {'sector': 'N/A', 'market': 'N/A'}
        except:
            sector_info = {'sector': 'N/A', 'market': 'N/A'}
        print(f"   {sector_info.get('sector', 'N/A')}")

        # 5. PDF 생성
        print()
        print("📝 PDF 생성 중...")
        output_dir = '/Users/wonny/Dev/joungwon.stocks.report/research_report/complete'
        import os
        os.makedirs(output_dir, exist_ok=True)
        output_path = f'{output_dir}/{KEPCO_NAME}_{KEPCO_CODE}_complete.pdf'

        await generate_pdf_report(ohlcv_data, supply_data, fnguide_data, sector_info, output_path)

        file_size = os.path.getsize(output_path)
        print()
        print(f"✅ 완전판 리포트 생성 완료")
        print(f"   파일: {output_path}")
        print(f"   크기: {file_size / 1024:.1f} KB")

    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
