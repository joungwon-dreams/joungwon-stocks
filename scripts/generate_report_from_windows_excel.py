"""
Windows 엑셀 파일(실제 자산)을 기반으로 PDF 리포트 생성
"""
import asyncio
import sys
import os
from datetime import datetime
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')
from src.config.database import db


# 한글 폰트 등록
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
font_dir = os.path.join(project_root, 'fonts')

try:
    font_regular = os.path.join(font_dir, 'NanumGothic.ttf')
    font_bold = os.path.join(font_dir, 'NanumGothicBold.ttf')

    if os.path.exists(font_regular) and os.path.exists(font_bold):
        pdfmetrics.registerFont(TTFont('NanumGothic', font_regular))
        pdfmetrics.registerFont(TTFont('NanumGothicBold', font_bold))
        FONT_NAME = 'NanumGothic'
        FONT_NAME_BOLD = 'NanumGothicBold'

        # matplotlib도 같은 폰트 사용
        plt.rcParams['font.family'] = ['NanumGothic', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False
        fm.fontManager.addfont(font_regular)
        fm.fontManager.addfont(font_bold)

        print(f"✅ 한글 폰트 로드 성공")
    else:
        raise FileNotFoundError("Font files not found")
except Exception as e:
    print(f"⚠️  폰트 로드 실패: {e}")
    FONT_NAME = 'Helvetica'
    FONT_NAME_BOLD = 'Helvetica-Bold'


# 종목코드 매핑
STOCK_CODE_MAP = {
    '한국전력': '015760',
    '우리금융지주': '316140',
    '카카오': '035720',
    'HDC현대산업개발': '294870',
    '파라다이스': '034230',
    '한국카본': '017960',
    'HD현대에너지솔루션': '329180',
    '롯데쇼핑': '023530',
    '금양그린파워': '322310',
    '한화': '000880',
}


def parse_windows_excel(file_path):
    """Windows 엑셀 파일 파싱"""

    df = pd.read_excel(file_path, sheet_name=0, header=None)

    # Row 7: 요약 정보
    summary_row = df.iloc[7]

    summary = {
        'total_assets': int(summary_row[0]) if pd.notna(summary_row[0]) else 0,
        'available_cash': int(summary_row[2]) if pd.notna(summary_row[2]) else 0,
        'total_profit': int(summary_row[4]) if pd.notna(summary_row[4]) else 0,
        'realized_profit': int(summary_row[7]) if pd.notna(summary_row[7]) else 0,
        'total_investment': int(summary_row[9]) if pd.notna(summary_row[9]) else 0,
        'total_value': int(summary_row[10]) if pd.notna(summary_row[10]) else 0,
        'unrealized_profit': int(summary_row[11]) if pd.notna(summary_row[11]) else 0,
    }

    # 종목 데이터 (Row 11부터 2행씩)
    holdings = []
    i = 11

    while i < len(df):
        stock_name = df.iloc[i, 0]

        if pd.isna(stock_name) or str(stock_name).strip() == '':
            break

        try:
            holding = {
                'stock_name': str(stock_name).strip(),
                'stock_code': STOCK_CODE_MAP.get(str(stock_name).strip(), 'UNKNOWN'),
                'profit_loss': int(df.iloc[i, 3]) if pd.notna(df.iloc[i, 3]) else 0,
                'profit_loss_rate': float(str(df.iloc[i, 5]).replace('%', '')) if pd.notna(df.iloc[i, 5]) else 0,
                'quantity': int(df.iloc[i, 8]) if pd.notna(df.iloc[i, 8]) else 0,
                'avg_buy_price': int(df.iloc[i, 12]) if pd.notna(df.iloc[i, 12]) else 0,
                'current_price': int(df.iloc[i, 16]) if pd.notna(df.iloc[i, 16]) else 0,
                'total_cost': int(df.iloc[i, 19]) if pd.notna(df.iloc[i, 19]) else 0,
                'total_value': int(df.iloc[i+1, 0]) if i+1 < len(df) and pd.notna(df.iloc[i+1, 0]) else 0,
            }

            holdings.append(holding)
        except Exception as e:
            print(f"⚠️  종목 파싱 오류 (Row {i}): {e}")

        i += 2  # 2행씩 건너뛰기

    summary['holdings'] = holdings
    summary['holdings_count'] = len(holdings)

    return summary


async def get_trade_history(limit=200):
    """거래내역 조회 (DB에서)"""
    await db.connect()

    query = """
        SELECT
            trade_date,
            th.stock_code,
            s.stock_name,
            trade_type,
            quantity,
            price,
            total_amount,
            fee,
            tax
        FROM trade_history th
        LEFT JOIN stocks s ON th.stock_code = s.stock_code
        WHERE gemini_reasoning LIKE 'KB증권 엑셀 자동 임포트%'
        ORDER BY trade_date DESC, id DESC
        LIMIT $1
    """
    trades = await db.fetch(query, limit)

    await db.disconnect()

    return trades


def format_number(num):
    """숫자를 천단위 콤마로 포맷"""
    if num is None:
        return "0"
    return f"{int(num):,}"


def create_pie_chart(holdings, temp_dir):
    """종목별 비중 파이 차트"""
    if not holdings or len(holdings) == 0:
        return None

    fig, ax = plt.subplots(figsize=(8, 6))

    labels = [h['stock_name'] for h in holdings]
    sizes = [h['total_cost'] for h in holdings]
    colors_list = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#C39BD3', '#85C1E2', '#F8B88B']

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct='%1.1f%%',
        colors=colors_list[:len(holdings)],
        startangle=90
    )

    for text in texts:
        text.set_fontsize(9)
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(8)
        autotext.set_weight('bold')

    ax.set_title('보유종목 비중', fontsize=14, fontweight='bold', pad=20)

    chart_path = os.path.join(temp_dir, 'pie_chart.png')
    plt.tight_layout()
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()

    return chart_path


def create_profit_bar_chart(summary, temp_dir):
    """손익 현황 막대 차트"""
    fig, ax = plt.subplots(figsize=(8, 5))

    categories = ['실현손익', '미실현손익', '총손익']
    values = [
        float(summary['realized_profit']),
        float(summary['unrealized_profit']),
        float(summary['total_profit'])
    ]

    colors_list = ['#3498db', '#e74c3c', '#2ecc71']
    colors_actual = [colors_list[2] if v >= 0 else colors_list[1] for v in values]

    bars = ax.bar(categories, values, color=colors_actual, alpha=0.8, edgecolor='black', linewidth=1.5)

    for bar, value in zip(bars, values):
        height = bar.get_height()
        value_range = max(values) - min(values) if max(values) != min(values) else 1
        label_y = height + value_range * 0.02 if height >= 0 else height - value_range * 0.02
        ax.text(bar.get_x() + bar.get_width()/2., label_y,
                f'{int(value):,}원',
                ha='center', va='bottom' if height >= 0 else 'top',
                fontsize=10, fontweight='bold')

    ax.set_title('손익 현황', fontsize=14, fontweight='bold', pad=20)
    ax.set_ylabel('금액 (원)', fontsize=11)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax.grid(axis='y', alpha=0.3)

    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x/10000):,}만' if x != 0 else '0'))

    chart_path = os.path.join(temp_dir, 'profit_chart.png')
    plt.tight_layout()
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()

    return chart_path


def create_dashboard_page(pdf_elements, summary, temp_dir):
    """대시보드 페이지 생성"""

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=getSampleStyleSheet()['Heading1'],
        fontName=FONT_NAME_BOLD,
        fontSize=22,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=10,
        alignment=TA_CENTER,
    )

    report_date = datetime.now().strftime('%Y년 %m월 %d일')

    pdf_elements.append(Paragraph(f"임정원 님의 증권자산", title_style))
    pdf_elements.append(Paragraph(f"<font size=10 color='grey'>{report_date} 기준</font>",
        ParagraphStyle('DateStyle', parent=getSampleStyleSheet()['Normal'],
            fontName=FONT_NAME, fontSize=10, textColor=colors.grey, alignment=TA_CENTER)))
    pdf_elements.append(Spacer(1, 0.8*cm))

    # 대시보드 요약 테이블
    dashboard_data = [
        ['총자산', '예수금', '투자금액'],
        [
            f"{format_number(summary['total_assets'])}원",
            f"{format_number(summary['available_cash'])}원",
            f"{format_number(summary['total_investment'])}원"
        ],
    ]

    dashboard_table = Table(dashboard_data, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
    dashboard_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    ]))

    pdf_elements.append(dashboard_table)
    pdf_elements.append(Spacer(1, 0.5*cm))

    # 손익 정보 테이블
    profit_color = colors.HexColor('#e74c3c') if summary['total_profit'] < 0 else colors.HexColor('#27ae60')

    profit_data = [
        ['실현손익', '미실현손익', '총손익'],
        [
            f"{format_number(summary['realized_profit'])}원",
            f"{format_number(summary['unrealized_profit'])}원",
            f"{format_number(summary['total_profit'])}원"
        ],
    ]

    profit_table = Table(profit_data, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
    profit_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 13),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('BACKGROUND', (0, 1), (1, 1), colors.HexColor('#f5f5f5')),
        ('BACKGROUND', (2, 1), (2, 1), profit_color),
        ('TEXTCOLOR', (2, 1), (2, 1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))

    pdf_elements.append(profit_table)
    pdf_elements.append(Spacer(1, 1*cm))

    # 차트 추가
    pie_chart_path = create_pie_chart(summary['holdings'], temp_dir)
    profit_chart_path = create_profit_bar_chart(summary, temp_dir)

    if pie_chart_path and profit_chart_path:
        chart_table_data = [[
            Image(pie_chart_path, width=8*cm, height=6*cm),
            Image(profit_chart_path, width=8*cm, height=5*cm)
        ]]

        chart_table = Table(chart_table_data, colWidths=[8.5*cm, 8.5*cm])
        chart_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))

        pdf_elements.append(chart_table)
        pdf_elements.append(Spacer(1, 1*cm))

    # 보유종목 섹션
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=getSampleStyleSheet()['Heading2'],
        fontName=FONT_NAME_BOLD,
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=10,
    )

    pdf_elements.append(Paragraph("보유종목 상세", section_style))

    # 보유종목 테이블
    holdings_data = [['종목코드', '종목명', '보유수량', '평균매수가', '현재가', '평가손익', '수익률']]

    for h in summary['holdings']:
        profit_color = colors.HexColor('#e74c3c') if h['profit_loss'] < 0 else colors.HexColor('#27ae60')

        holdings_data.append([
            h['stock_code'],
            h['stock_name'],
            f"{int(h['quantity'])}주",
            f"{format_number(h['avg_buy_price'])}원",
            f"{format_number(h['current_price'])}원",
            f"{format_number(h['profit_loss'])}원",
            f"{h['profit_loss_rate']:.2f}%",
        ])

    holdings_table = Table(holdings_data, colWidths=[2.5*cm, 3*cm, 2.5*cm, 2.8*cm, 2.5*cm, 2.8*cm, 2*cm])

    # 기본 스타일
    base_style = [
        ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (5, 1), (6, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]

    # 손익 색상 추가
    for i, h in enumerate(summary['holdings'], start=1):
        if h['profit_loss'] < 0:
            base_style.append(('TEXTCOLOR', (5, i), (6, i), colors.HexColor('#e74c3c')))
        else:
            base_style.append(('TEXTCOLOR', (5, i), (6, i), colors.HexColor('#27ae60')))

    holdings_table.setStyle(TableStyle(base_style))

    pdf_elements.append(holdings_table)


def create_trade_history_pages(pdf_elements, trades):
    """거래내역 페이지 생성"""

    pdf_elements.append(PageBreak())

    section_style = ParagraphStyle(
        'SectionTitle',
        parent=getSampleStyleSheet()['Heading2'],
        fontName=FONT_NAME_BOLD,
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=10,
    )

    pdf_elements.append(Paragraph("거래내역", section_style))
    pdf_elements.append(Spacer(1, 0.3*cm))

    trade_data = [['거래일자', '종목코드', '종목명', '구분', '수량', '단가', '거래금액', '수수료']]

    for trade in trades:
        trade_date = trade['trade_date'].strftime('%Y-%m-%d') if trade['trade_date'] else '-'
        stock_name = trade['stock_name'] or trade['stock_code']

        trade_data.append([
            trade_date,
            trade['stock_code'],
            stock_name,
            trade['trade_type'],
            f"{int(trade['quantity'])}",
            f"{format_number(trade['price'])}",
            f"{format_number(trade['total_amount'])}",
            f"{format_number(trade['fee'] + trade['tax'])}",
        ])

    col_widths = [2.5*cm, 2*cm, 3*cm, 1.5*cm, 1.5*cm, 2.5*cm, 2.5*cm, 1.5*cm]
    trade_table = Table(trade_data, colWidths=col_widths, repeatRows=1)

    style_commands = [
        ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (5, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]

    for i, trade in enumerate(trades, start=1):
        if trade['trade_type'] == '매수':
            style_commands.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#e74c3c')))
        else:
            style_commands.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#3498db')))

    trade_table.setStyle(TableStyle(style_commands))
    pdf_elements.append(trade_table)


async def generate_pdf():
    """PDF 리포트 생성"""

    print("=== Windows 엑셀 기반 거래내역 PDF 생성 ===")
    print()

    # Windows 엑셀 파일 파싱
    excel_path = '/Users/wonny/Dev/joungwon.stocks.report/windows/da03450000.xls'
    print(f"📂 엑셀 파일 읽기: {excel_path}")

    summary = parse_windows_excel(excel_path)

    print(f"✅ 보유종목: {summary['holdings_count']}개")
    print(f"✅ 총자산: {format_number(summary['total_assets'])}원")
    print(f"✅ 예수금: {format_number(summary['available_cash'])}원")
    print(f"✅ 투자금액: {format_number(summary['total_investment'])}원")
    print(f"✅ 실현손익: {format_number(summary['realized_profit'])}원")
    print(f"✅ 미실현손익: {format_number(summary['unrealized_profit'])}원")
    print(f"✅ 총손익: {format_number(summary['total_profit'])}원")
    print()

    # 거래내역 조회
    print("📊 거래내역 조회 중...")
    trades = await get_trade_history(limit=200)
    print(f"✅ 거래내역: {len(trades)}건")
    print()

    # 임시 디렉토리
    temp_dir = os.path.join(project_root, 'temp_charts')
    os.makedirs(temp_dir, exist_ok=True)

    # PDF 파일 생성
    output_dir = '/Users/wonny/Dev/joungwon.stocks.report/stock_assets'
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'trading_report.pdf')

    print(f"📝 PDF 생성 중: {output_path}")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    pdf_elements = []

    create_dashboard_page(pdf_elements, summary, temp_dir)
    create_trade_history_pages(pdf_elements, trades)

    doc.build(pdf_elements)

    # 임시 파일 삭제
    import shutil
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    print()
    print(f"✅ PDF 생성 완료: {output_path}")
    print()


if __name__ == '__main__':
    asyncio.run(generate_pdf())
