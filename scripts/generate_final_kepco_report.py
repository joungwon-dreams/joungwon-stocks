"""
한국전력 최종 리포트 생성 (Tier 1-4 데이터 포함)

Features:
1. 365일 OHLCV 차트, 거래량, 수급분석
2. 증권사 목표치 및 투자의견 (FnGuide)
3. 재무제표 (FnGuide 최근 년도별 실적)
4. 회사 정보
5. 최근 2주간 주가변화
6. Valuation 지표
"""
import sys
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import matplotlib.font_manager as fm

from src.config.database import db

# 한국전력 종목코드
KEPCO_CODE = '015760'
KEPCO_NAME = '한국전력'

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False


def setup_korean_font():
    """PDF용 한글 폰트 설정"""
    try:
        pdfmetrics.registerFont(TTFont('NanumGothic', '/Library/Fonts/NanumGothic.ttf'))
        return 'NanumGothic'
    except:
        try:
            pdfmetrics.registerFont(TTFont('AppleGothic', '/System/Library/Fonts/Supplemental/AppleGothic.ttf'))
            return 'AppleGothic'
        except:
            return 'Helvetica'


def create_candlestick_chart(ohlcv_data: List[Dict], output_path: str):
    """365일 캔들스틱 차트 생성"""
    if not ohlcv_data:
        return
    
    dates = [row['date'] for row in ohlcv_data]
    opens = [row['open'] for row in ohlcv_data]
    highs = [row['high'] for row in ohlcv_data]
    lows = [row['low'] for row in ohlcv_data]
    closes = [row['close'] for row in ohlcv_data]
    volumes = [row['volume'] for row in ohlcv_data]
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
    
    # 캔들스틱 차트
    width = 0.6
    for i, (date, open_, high, low, close) in enumerate(zip(dates, opens, highs, lows, closes)):
        color = 'red' if close >= open_ else 'blue'
        ax1.plot([i, i], [low, high], color=color, linewidth=0.5)
        ax1.add_patch(Rectangle((i - width/2, min(open_, close)), 
                                width, abs(close - open_), 
                                facecolor=color, edgecolor=color))
    
    ax1.set_title(f'{KEPCO_NAME} 주가 추이 (365일)', fontsize=14, fontweight='bold')
    ax1.set_ylabel('주가 (원)', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 거래량 차트
    colors_volume = ['red' if closes[i] >= opens[i] else 'blue' for i in range(len(closes))]
    ax2.bar(range(len(volumes)), volumes, color=colors_volume, alpha=0.5)
    ax2.set_ylabel('거래량', fontsize=10)
    ax2.set_xlabel('날짜', fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # x축 날짜 표시
    step = max(len(dates) // 10, 1)
    ax2.set_xticks(range(0, len(dates), step))
    ax2.set_xticklabels([dates[i].strftime('%m/%d') for i in range(0, len(dates), step)], rotation=45)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def create_supply_demand_chart(supply_data: List[Dict], output_path: str):
    """수급분석 차트 (외국인/기관/개인)"""
    if not supply_data:
        return
    
    dates = [row['date'] for row in supply_data]
    foreigner = [row['foreigner_net'] / 1000 for row in supply_data]  # 천주 단위
    institution = [row['institution_net'] / 1000 for row in supply_data]
    individual = [row['individual_net'] / 1000 for row in supply_data]
    
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
    
    # x축 날짜 표시
    step = max(len(dates) // 10, 1)
    ax.set_xticks(range(0, len(dates), step))
    ax.set_xticklabels([dates[i].strftime('%m/%d') for i in range(0, len(dates), step)], rotation=45)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def create_recent_price_chart(ohlcv_data: List[Dict], output_path: str, days: int = 14):
    """최근 N일 주가 변화 차트"""
    if not ohlcv_data or len(ohlcv_data) < days:
        recent_data = ohlcv_data
    else:
        recent_data = ohlcv_data[-days:]
    
    dates = [row['date'] for row in recent_data]
    closes = [float(row['close']) for row in recent_data]
    highs = [float(row['high']) for row in recent_data]
    lows = [float(row['low']) for row in recent_data]
    
    fig, ax = plt.subplots(figsize=(10, 5))
    
    ax.plot(range(len(dates)), closes, marker='o', linewidth=2, markersize=6, color='blue', label='종가')
    ax.fill_between(range(len(dates)), lows, highs, alpha=0.2, color='gray', label='고가-저가 범위')
    
    # 고가/저가 표시
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


async def generate_pdf_report(ohlcv_data: List[Dict], supply_data: List[Dict], 
                              fnguide_data: Optional[Dict], output_path: str):
    """PDF 리포트 생성"""
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []
    
    # 한글 폰트 설정
    korean_font = setup_korean_font()
    
    # 스타일 정의
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=korean_font,
        fontSize=24,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=korean_font,
        fontSize=16,
        textColor=colors.HexColor('#2c5aa0'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=korean_font,
        fontSize=10,
        leading=14
    )
    
    # 제목
    story.append(Paragraph(f'{KEPCO_NAME} ({KEPCO_CODE}) 종합 투자 리포트', title_style))
    story.append(Paragraph(f'작성일: {datetime.now().strftime("%Y년 %m월 %d일")}', normal_style))
    story.append(Spacer(1, 0.3*inch))
    
    # 1. 회사 정보
    story.append(Paragraph('1. 회사 정보', heading_style))
    if fnguide_data and fnguide_data.get('company_info'):
        company_info = fnguide_data['company_info']
        company_table_data = [
            ['회사명', company_info.get('company_name', KEPCO_NAME)],
            ['시가총액', f"{company_info.get('market_cap', 'N/A')}조원"],
        ]
        company_table = Table(company_table_data, colWidths=[2*inch, 4*inch])
        company_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), korean_font, 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f4f8')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(company_table)
    story.append(Spacer(1, 0.2*inch))
    
    # 2. 재무제표 (FnGuide)
    if fnguide_data and fnguide_data.get('financial_summary'):
        story.append(PageBreak())
        story.append(Paragraph('2. 재무제표 (최근 4개년 + 추정)', heading_style))
        
        financials = fnguide_data['financial_summary']
        years = financials.get('years', [])[1:5]  # 2020-2023
        revenue = financials.get('revenue', [])[1:5]
        op_profit = financials.get('operating_profit', [])[1:5]
        net_profit = financials.get('net_profit', [])[1:5]
        eps = financials.get('eps', [])[1:5]
        
        if years:
            financial_table_data = [['구분'] + [str(y)[:7] for y in years]]
            financial_table_data.append(['매출액 (억원)'] + [f'{int(r):,}' if r else '-' for r in revenue])
            financial_table_data.append(['영업이익 (억원)'] + [f'{int(p):,}' if p else '-' for p in op_profit])
            financial_table_data.append(['당기순이익 (억원)'] + [f'{int(p):,}' if p else '-' for p in net_profit])
            financial_table_data.append(['EPS (원)'] + [f'{int(e):,}' if e else '-' for e in eps])
            
            financial_table = Table(financial_table_data, colWidths=[1.5*inch] + [1.2*inch]*4)
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
    
    # 3. 애널리스트 컨센서스
    if fnguide_data and fnguide_data.get('analyst_consensus'):
        story.append(Paragraph('3. 증권사 투자의견', heading_style))
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
    
    # 4. 365일 주가 차트
    story.append(PageBreak())
    story.append(Paragraph('4. 주가 추이 (365일)', heading_style))
    candlestick_path = '/tmp/kepco_candlestick.png'
    create_candlestick_chart(ohlcv_data, candlestick_path)
    story.append(Image(candlestick_path, width=6.5*inch, height=4.3*inch))
    story.append(Spacer(1, 0.2*inch))
    
    # 5. 수급 분석
    story.append(PageBreak())
    story.append(Paragraph('5. 수급 분석 (외국인/기관/개인)', heading_style))
    supply_path = '/tmp/kepco_supply.png'
    create_supply_demand_chart(supply_data, supply_path)
    story.append(Image(supply_path, width=6.5*inch, height=3.9*inch))
    story.append(Spacer(1, 0.2*inch))
    
    # 6. 최근 14일 주가
    story.append(PageBreak())
    story.append(Paragraph('6. 최근 2주간 주가 변화', heading_style))
    recent_path = '/tmp/kepco_recent.png'
    create_recent_price_chart(ohlcv_data, recent_path, days=14)
    story.append(Image(recent_path, width=6*inch, height=3*inch))
    story.append(Spacer(1, 0.2*inch))
    
    # 7. Valuation 지표
    if fnguide_data and fnguide_data.get('valuation_metrics'):
        story.append(Paragraph('7. Valuation 지표', heading_style))
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
    """메인 실행 함수"""
    print("=" * 80)
    print("한국전력 최종 리포트 생성")
    print("=" * 80)
    print()
    
    try:
        await db.connect()
        
        # 1. OHLCV 데이터 (365일)
        print("📊 OHLCV 데이터 로드 중...")
        ohlcv_query = """
            SELECT stock_code, date, open, high, low, close, volume
            FROM daily_ohlcv
            WHERE stock_code = $1
            ORDER BY date ASC
        """
        ohlcv_data = await db.fetch(ohlcv_query, KEPCO_CODE)
        print(f"   OHLCV: {len(ohlcv_data)}건")
        
        # 2. 수급 데이터
        print("📈 수급 데이터 로드 중...")
        supply_query = """
            SELECT stock_code, date, foreigner_net, institution_net, individual_net
            FROM stock_supply_demand
            WHERE stock_code = $1
            ORDER BY date ASC
        """
        supply_data = await db.fetch(supply_query, KEPCO_CODE)
        print(f"   수급: {len(supply_data)}건")
        
        # 3. FnGuide 데이터
        print("💼 FnGuide 데이터 로드 중...")
        fnguide_query = """
            SELECT data_content->'data' as fnguide_data
            FROM collected_data
            WHERE ticker = $1 AND site_id = 53
            ORDER BY collected_at DESC
            LIMIT 1
        """
        fnguide_row = await db.fetchrow(fnguide_query, KEPCO_CODE)
        fnguide_data = json.loads(fnguide_row['fnguide_data']) if fnguide_row else None
        print(f"   FnGuide: {'있음' if fnguide_data else '없음'}")
        
        # 4. PDF 생성
        print()
        print("📝 PDF 생성 중...")
        output_dir = '/Users/wonny/Dev/joungwon.stocks.report/research_report/final'
        import os
        os.makedirs(output_dir, exist_ok=True)
        output_path = f'{output_dir}/{KEPCO_NAME}_{KEPCO_CODE}_final.pdf'
        
        await generate_pdf_report(ohlcv_data, supply_data, fnguide_data, output_path)
        
        # 파일 크기 확인
        file_size = os.path.getsize(output_path)
        print()
        print(f"✅ 최종 리포트 생성 완료")
        print(f"   파일: {output_path}")
        print(f"   크기: {file_size / 1024:.1f} KB")
        
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
