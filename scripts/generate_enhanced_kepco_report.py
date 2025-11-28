"""
한국전력 향상된 리포트 생성 (Daum + Naver 데이터 포함)
"""
import sys
import asyncio
import json
from datetime import datetime
sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from src.fetchers.tier4_browser_automation.naver_main_comprehensive_fetcher import NaverMainComprehensiveFetcher
from src.fetchers.tier2_official_apis.daum_fetcher import DaumFetcher


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


async def collect_data(ticker: str):
    """Daum + Naver 데이터 수집"""
    print("데이터 수집 중...")

    # Daum Finance
    daum_config = {'site_name_ko': 'Daum Finance', 'data_type': 'daum_comprehensive', 'domain_id': 1}
    daum_fetcher = DaumFetcher(site_id=60, config=daum_config)
    daum_data = await daum_fetcher.fetch(ticker)

    # Naver Finance
    naver_config = {'headless': True, 'viewport': {'width': 1920, 'height': 1080},
                    'data_type': 'naver_main_comprehensive', 'domain_id': 1}
    naver_fetcher = NaverMainComprehensiveFetcher(site_id=61, config=naver_config)

    try:
        await naver_fetcher.initialize()
        naver_data = await naver_fetcher.fetch_data(ticker)
    finally:
        await naver_fetcher.cleanup()

    print(f"✅ 데이터 수집 완료: Daum {daum_data.get('records_count', 0)}개 + Naver {len(naver_data.get('investor_trading', {}).get('daily_trading', []))}일")

    return daum_data, naver_data


def generate_pdf(daum_data: dict, naver_data: dict, output_path: str):
    """PDF 생성"""
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []

    font_name = setup_korean_font()
    styles = getSampleStyleSheet()

    # 스타일 정의
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                 fontName=font_name, fontSize=24, alignment=TA_CENTER, spaceAfter=30)
    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'],
                                   fontName=font_name, fontSize=16, spaceAfter=12)
    normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'],
                                  fontName=font_name, fontSize=10, leading=14)

    # 제목
    story.append(Paragraph('한국전력 투자 분석 리포트', title_style))
    story.append(Paragraph(f'생성일: {datetime.now().strftime("%Y년 %m월 %d일")}', normal_style))
    story.append(Spacer(1, 0.3*inch))

    # 1. 기본 정보 (Daum)
    story.append(Paragraph('1. 기본 정보', heading_style))

    quotes = daum_data.get('quotes', {})
    if quotes:
        info_data = [
            ['종목명', quotes.get('name', 'N/A')],
            ['현재가', f"{quotes.get('tradePrice', 0):,.0f}원"],
            ['전일대비', f"{quotes.get('changePrice', 0):+,.0f}원 ({quotes.get('change', 'N/A')})"],
            ['시가총액', f"{quotes.get('marketCap', 0):,.0f}원"],
            ['거래량', f"{quotes.get('accTradeVolume', 0):,.0f}주"],
        ]

        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(info_table)

    story.append(Spacer(1, 0.3*inch))

    # 2. 재무 지표 (Daum)
    story.append(Paragraph('2. 재무 지표', heading_style))

    sectors = daum_data.get('sectors', {}).get('data', [])
    if sectors and len(sectors) > 0:
        stock = sectors[0]
        financial_data = [
            ['지표', '값'],
            ['매출액', f"{stock.get('netSales', 0):,.0f}원"],
            ['영업이익', f"{stock.get('operatingProfit', 0):,.0f}원"],
            ['조정영업이익', f"{stock.get('adjustOperatingProfit', 0):,.0f}원"],
            ['순이익', f"{stock.get('netIncome', 0):,.0f}원"],
            ['EPS', f"{stock.get('eps', 0):,.1f}원"],
            ['ROE', f"{stock.get('roe', 0)*100:.2f}%"],
            ['외국인비율', f"{stock.get('foreignRatio', 0)*100:.2f}%"],
        ]

        financial_table = Table(financial_data, colWidths=[2.5*inch, 3.5*inch])
        financial_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(financial_table)

    story.append(Spacer(1, 0.3*inch))

    # 3. 투자자 매매동향 (Daum - 최근 10일)
    story.append(Paragraph('3. 투자자 매매동향 (최근 10일)', heading_style))

    investor_days = daum_data.get('investor_trading', {}).get('data', [])
    if investor_days:
        investor_data = [['날짜', '종가', '외국인 순매수', '기관 순매수', '외국인보유율']]

        for item in investor_days[:10]:
            investor_data.append([
                item.get('date', '')[:10],
                f"{item.get('tradePrice', 0):,.0f}",
                f"{item.get('foreignStraightPurchaseVolume', 0):,}",
                f"{item.get('institutionStraightPurchaseVolume', 0):,}",
                f"{item.get('foreignOwnSharesRate', 0)*100:.2f}%"
            ])

        investor_table = Table(investor_data, colWidths=[1.2*inch, 1*inch, 1.4*inch, 1.2*inch, 1.2*inch])
        investor_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(investor_table)

    story.append(Spacer(1, 0.3*inch))

    # 4. Naver 투자자 매매동향
    story.append(Paragraph('4. Naver 투자자 매매동향 (최근 6일)', heading_style))

    naver_trading = naver_data.get('investor_trading', {}).get('daily_trading', [])
    if naver_trading:
        naver_data_table = [['날짜', '종가', '전일대비', '외국인', '기관']]

        for trade in naver_trading:
            naver_data_table.append([
                trade.get('date', ''),
                f"{trade.get('close_price', 0):,.0f}",
                f"{trade.get('change', 0):+,.0f}" if trade.get('change') else 'N/A',
                f"{trade.get('foreign_net', 0):,}",
                f"{trade.get('institution_net', 0):,}"
            ])

        naver_table = Table(naver_data_table, colWidths=[1.1*inch, 1.1*inch, 1.1*inch, 1.4*inch, 1.3*inch])
        naver_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(naver_table)

    story.append(Spacer(1, 0.3*inch))

    # 5. 동종업종 비교 (Naver)
    story.append(Paragraph('5. 동종업종 비교 (상위 5개 기업)', heading_style))

    peers = naver_data.get('peer_comparison', [])
    if peers and len(peers) >= 5:
        peer_data = [['지표', '한국전력', '한전기술', '한전KPS', '한전산업', 'GS파워']]

        for i in range(min(5, len(peers))):
            if i == 0:
                continue  # Skip first row (usually header)
            peer = peers[i]
            peer_data.append([
                peer.get('company', ''),
                *peer.get('data', [])[:5]
            ])

        peer_table = Table(peer_data, colWidths=[1.5*inch] + [1*inch]*5)
        peer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(peer_table)

    # PDF 생성
    doc.build(story)
    print(f"✅ PDF 생성 완료: {output_path}")


async def main():
    ticker = '015760'
    output_path = '/tmp/kepco_enhanced_report.pdf'

    # 데이터 수집
    daum_data, naver_data = await collect_data(ticker)

    # PDF 생성
    generate_pdf(daum_data, naver_data, output_path)

    print(f"\n리포트 생성 완료!")
    print(f"파일 위치: {output_path}")


asyncio.run(main())
