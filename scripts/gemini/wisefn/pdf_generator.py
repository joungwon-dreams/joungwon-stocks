"""
WISEfn Analyst Reports PDF Generator
Creates PDF with Daum Finance 종목리포트 design
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from typing import List, Dict, Any
from datetime import datetime
import os

class DaumReportPDFGenerator:
    """Generate PDF matching Daum Finance analyst report design"""

    def __init__(self, output_dir: str = "/Users/wonny/Dev/joungwon.stocks/reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Register Korean fonts
        try:
            font_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'fonts')
            pdfmetrics.registerFont(TTFont('NanumGothic', os.path.join(font_dir, 'NanumGothic.ttf')))
            pdfmetrics.registerFont(TTFont('NanumGothicBold', os.path.join(font_dir, 'NanumGothicBold.ttf')))
            self.font_name = 'NanumGothic'
            self.font_bold = 'NanumGothicBold'
            print(f"✅ Loaded Korean fonts from: {font_dir}")
        except Exception as e:
            print(f"⚠️  Korean font load failed: {e}")
            print("   Using default fonts (Korean text may not display correctly)")
            self.font_name = 'Helvetica'
            self.font_bold = 'Helvetica-Bold'

    def generate_report(self, stock_name: str, stock_code: str, reports: List[Dict[str, Any]]) -> str:
        """
        Generate PDF report with analyst data

        Args:
            stock_name: Stock name (e.g., '한국전력')
            stock_code: Stock code (e.g., '015760')
            reports: List of report dictionaries from WISEfnReportsScraper

        Returns:
            Path to generated PDF file
        """
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%m%d%H%M")
        filename = f"{stock_name}_{timestamp}.pdf"
        filepath = os.path.join(self.output_dir, filename)

        # Create PDF document
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )

        elements = []
        styles = getSampleStyleSheet()

        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=self.font_bold,
            fontSize=16,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            alignment=0  # Left align
        )

        # Add title
        title = f"{stock_name} ({stock_code}) 종목리포트"
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 10*mm))

        # Prepare table data
        table_data = [
            ['일자', '목표주가', '아진대비', '투자의견', '증권사', '리포트']
        ]

        for report in reports:
            # Format target price with comma
            target_price = f"{report['target_price']:,}"

            # Format price change
            price_change = report['price_change']
            if price_change == '0':
                price_change = '0'
            elif price_change == '-':
                price_change = '-'
            else:
                # Handle cases like "15,000" -> "▲ 15,000"
                try:
                    change_val = int(price_change.replace(',', ''))
                    if change_val > 0:
                        price_change = f"▲ {change_val:,}"
                    elif change_val < 0:
                        price_change = f"▼ {abs(change_val):,}"
                except:
                    pass

            table_data.append([
                report['date'],
                target_price,
                price_change,
                report['opinion'],
                report['brokerage'],
                report['title'][:40] + '...' if len(report['title']) > 40 else report['title']
            ])

        # Create table
        table = Table(
            table_data,
            colWidths=[20*mm, 25*mm, 25*mm, 20*mm, 20*mm, 60*mm]
        )

        # Table style matching Daum design
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#333333')),
            ('FONTNAME', (0, 0), (-1, 0), self.font_bold),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),

            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Date column
            ('ALIGN', (1, 1), (2, -1), 'RIGHT'),   # Price columns
            ('ALIGN', (3, 1), (4, -1), 'CENTER'),  # Opinion, Brokerage
            ('ALIGN', (5, 1), (5, -1), 'LEFT'),    # Title column
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),

            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),

            # Row padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))

        elements.append(table)

        # Add footer
        elements.append(Spacer(1, 10*mm))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontName=self.font_name,
            fontSize=8,
            textColor=colors.HexColor('#999999')
        )
        footer_text = f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 데이터 출처: WISEfn (Daum Finance)"
        elements.append(Paragraph(footer_text, footer_style))

        # Build PDF
        doc.build(elements)

        print(f"✅ PDF generated: {filepath}")
        return filepath
