"""
AEGIS Report Generator - Phase 10
WillyDreams Style PDF Engine

Unified PDF generation with consistent branding:
- Primary Color: Yellow (#FFD700)
- Header: "PROJECT AEGIS" (left), date (right)
- Footer: "WillyDreams | joungwon.dreams@gmail.com" (left), page (right)
- Section headers with yellow underlines
- Card UI with rounded corners
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, Line
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.widgets.markers import makeMarker

logger = logging.getLogger(__name__)


@dataclass
class StyleConfig:
    """WillyDreams Style Design Tokens"""
    # Brand Colors
    PRIMARY: str = "#FFD700"      # Yellow (포인트 컬러)
    SECONDARY: str = "#1A1A2E"    # Dark Navy
    ACCENT: str = "#16213E"       # Deep Blue
    SUCCESS: str = "#00D26A"      # Green
    DANGER: str = "#FF4757"       # Red
    WARNING: str = "#FFA502"      # Orange
    NEUTRAL: str = "#F8F9FA"      # Light Gray
    TEXT_PRIMARY: str = "#1A1A2E"
    TEXT_SECONDARY: str = "#6C757D"

    # ReportLab Colors
    @property
    def primary_color(self) -> colors.Color:
        return colors.HexColor(self.PRIMARY)

    @property
    def secondary_color(self) -> colors.Color:
        return colors.HexColor(self.SECONDARY)

    @property
    def success_color(self) -> colors.Color:
        return colors.HexColor(self.SUCCESS)

    @property
    def danger_color(self) -> colors.Color:
        return colors.HexColor(self.DANGER)

    @property
    def neutral_color(self) -> colors.Color:
        return colors.HexColor(self.NEUTRAL)

    # Typography
    FONT_TITLE_SIZE: int = 24
    FONT_HEADING_SIZE: int = 16
    FONT_SUBHEADING_SIZE: int = 12
    FONT_BODY_SIZE: int = 10
    FONT_CAPTION_SIZE: int = 8

    # Spacing
    MARGIN_TOP: float = 20 * mm
    MARGIN_BOTTOM: float = 20 * mm
    MARGIN_LEFT: float = 15 * mm
    MARGIN_RIGHT: float = 15 * mm
    CARD_PADDING: float = 10 * mm
    CARD_RADIUS: float = 5 * mm
    SECTION_SPACING: float = 15 * mm

    # Page
    PAGE_SIZE: Tuple[float, float] = A4


class ReportGenerator:
    """
    WillyDreams Style PDF Report Generator

    Provides consistent branding across all AEGIS reports:
    - Header with PROJECT AEGIS logo and date
    - Footer with contact info and page numbers
    - Yellow-accented section headers
    - Card-style content containers
    """

    def __init__(self, style: StyleConfig = None):
        self.style = style or StyleConfig()
        self.fonts_registered = False
        self._register_fonts()
        self._init_styles()

    def _register_fonts(self):
        """Register Korean fonts"""
        if self.fonts_registered:
            return

        # Try different font configurations
        font_configs = [
            {
                'regular': "/Users/wonny/Dev/joungwon.stocks/fonts/NanumGothic.ttf",
                'bold': "/Users/wonny/Dev/joungwon.stocks/fonts/NanumGothicBold.ttf",
            },
            {
                'regular': "/Library/Fonts/NanumGothic.ttf",
                'bold': "/Library/Fonts/NanumGothicBold.ttf",
            },
            {
                'regular': "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
                'bold': "/System/Library/Fonts/Supplemental/AppleGothic.ttf",  # Same for bold
            },
        ]

        registered = False
        for config in font_configs:
            regular_path = config['regular']
            bold_path = config['bold']

            if Path(regular_path).exists():
                try:
                    pdfmetrics.registerFont(TTFont('NanumGothic', regular_path))

                    if Path(bold_path).exists():
                        pdfmetrics.registerFont(TTFont('NanumGothicBold', bold_path))
                    else:
                        # Use regular font as bold fallback
                        pdfmetrics.registerFont(TTFont('NanumGothicBold', regular_path))

                    # Register font family for proper bold/italic mapping
                    from reportlab.pdfbase.pdfmetrics import registerFontFamily
                    registerFontFamily('NanumGothic',
                                     normal='NanumGothic',
                                     bold='NanumGothicBold',
                                     italic='NanumGothic',
                                     boldItalic='NanumGothicBold')

                    registered = True
                    logger.info(f"Registered fonts from: {regular_path}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to register font {regular_path}: {e}")

        if not registered:
            logger.warning("Using default Helvetica font (Korean may not display correctly)")

        self.fonts_registered = True
        self.font_name = 'NanumGothic' if registered else 'Helvetica'
        self.font_bold = 'NanumGothicBold' if registered else 'Helvetica-Bold'

    def _init_styles(self):
        """Initialize paragraph styles"""
        self.styles = getSampleStyleSheet()

        # Title style (24pt Bold)
        self.styles.add(ParagraphStyle(
            name='AegisTitle',
            fontName=self.font_bold,
            fontSize=self.style.FONT_TITLE_SIZE,
            textColor=colors.HexColor(self.style.TEXT_PRIMARY),
            alignment=TA_LEFT,
            spaceAfter=10,
        ))

        # Section heading (16pt Bold + Yellow underline)
        self.styles.add(ParagraphStyle(
            name='AegisHeading',
            fontName=self.font_bold,
            fontSize=self.style.FONT_HEADING_SIZE,
            textColor=colors.HexColor(self.style.TEXT_PRIMARY),
            alignment=TA_LEFT,
            spaceBefore=15,
            spaceAfter=5,
        ))

        # Subheading (12pt)
        self.styles.add(ParagraphStyle(
            name='AegisSubheading',
            fontName=self.font_bold,
            fontSize=self.style.FONT_SUBHEADING_SIZE,
            textColor=colors.HexColor(self.style.TEXT_PRIMARY),
            alignment=TA_LEFT,
            spaceBefore=10,
            spaceAfter=3,
        ))

        # Body text (10pt)
        self.styles.add(ParagraphStyle(
            name='AegisBody',
            fontName=self.font_name,
            fontSize=self.style.FONT_BODY_SIZE,
            textColor=colors.HexColor(self.style.TEXT_PRIMARY),
            alignment=TA_LEFT,
            leading=14,
        ))

        # Caption (8pt gray)
        self.styles.add(ParagraphStyle(
            name='AegisCaption',
            fontName=self.font_name,
            fontSize=self.style.FONT_CAPTION_SIZE,
            textColor=colors.HexColor(self.style.TEXT_SECONDARY),
            alignment=TA_LEFT,
        ))

        # Centered body
        self.styles.add(ParagraphStyle(
            name='AegisBodyCenter',
            fontName=self.font_name,
            fontSize=self.style.FONT_BODY_SIZE,
            textColor=colors.HexColor(self.style.TEXT_PRIMARY),
            alignment=TA_CENTER,
        ))

    def create_document(self, filename: str, title: str = "AEGIS Report") -> SimpleDocTemplate:
        """Create a new PDF document with AEGIS styling"""
        doc = SimpleDocTemplate(
            filename,
            pagesize=self.style.PAGE_SIZE,
            topMargin=self.style.MARGIN_TOP,
            bottomMargin=self.style.MARGIN_BOTTOM,
            leftMargin=self.style.MARGIN_LEFT,
            rightMargin=self.style.MARGIN_RIGHT,
            title=title,
            author="WillyDreams",
        )
        return doc

    def add_header_footer(self, canvas, doc):
        """
        Draw header and footer on each page

        Header: "PROJECT AEGIS" (left), date (right)
        Footer: "WillyDreams | joungwon.dreams@gmail.com" (left), page (right)
        """
        canvas.saveState()
        width, height = self.style.PAGE_SIZE

        # Header background
        canvas.setFillColor(colors.HexColor(self.style.SECONDARY))
        canvas.rect(0, height - 15*mm, width, 15*mm, fill=True, stroke=False)

        # Header text
        canvas.setFillColor(self.style.primary_color)
        canvas.setFont(self.font_bold, 14)
        canvas.drawString(self.style.MARGIN_LEFT, height - 10*mm, "PROJECT AEGIS")

        # Date on right
        canvas.setFillColor(colors.white)
        canvas.setFont(self.font_name, 10)
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        canvas.drawRightString(width - self.style.MARGIN_RIGHT, height - 10*mm, date_str)

        # Yellow accent line under header
        canvas.setStrokeColor(self.style.primary_color)
        canvas.setLineWidth(2)
        canvas.line(0, height - 15*mm, width, height - 15*mm)

        # Footer
        canvas.setFillColor(colors.HexColor(self.style.TEXT_SECONDARY))
        canvas.setFont(self.font_name, 8)
        canvas.drawString(
            self.style.MARGIN_LEFT,
            10*mm,
            "WillyDreams | joungwon.dreams@gmail.com"
        )

        # Page number on right
        page_num = doc.page
        canvas.drawRightString(
            width - self.style.MARGIN_RIGHT,
            10*mm,
            f"Page {page_num}"
        )

        canvas.restoreState()

    def create_section_header(self, title: str, emoji: str = "") -> List:
        """
        Create a section header with yellow underline

        Returns list of flowables: [Paragraph, YellowLine, Spacer]
        """
        elements = []

        # Title with optional emoji
        display_title = f"{emoji} {title}" if emoji else title
        elements.append(Paragraph(display_title, self.styles['AegisHeading']))

        # Yellow underline (using a table trick)
        underline_data = [['', '']]
        underline_table = Table(underline_data, colWidths=[150*mm, 20*mm])
        underline_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (0, 0), 3, self.style.primary_color),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(underline_table)
        elements.append(Spacer(1, 5*mm))

        return elements

    def create_card(self, content: List,
                   background_color: str = None,
                   border_color: str = None) -> Table:
        """
        Create a card container with rounded corners effect

        Args:
            content: List of flowables to put inside the card
            background_color: Card background (default: NEUTRAL)
            border_color: Card border (default: none)

        Returns:
            Table styled as a card
        """
        bg_color = colors.HexColor(background_color) if background_color else self.style.neutral_color

        # Wrap content in a cell
        card_data = [[content]]
        card = Table(card_data, colWidths=[170*mm])

        style_commands = [
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]

        if border_color:
            style_commands.extend([
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor(border_color)),
            ])

        # Rounded corners simulation (using ROUNDEDCORNERS if available)
        try:
            style_commands.append(('ROUNDEDCORNERS', [5, 5, 5, 5]))
        except:
            pass  # ROUNDEDCORNERS not available in older reportlab

        card.setStyle(TableStyle(style_commands))
        return card

    def create_data_table(self, data: List[List],
                         col_widths: List[float] = None,
                         header_row: bool = True,
                         alternate_rows: bool = True) -> Table:
        """
        Create a styled data table

        Args:
            data: 2D list of table data
            col_widths: Column widths in mm
            header_row: Style first row as header
            alternate_rows: Alternate row background colors
        """
        if col_widths:
            col_widths = [w * mm for w in col_widths]

        table = Table(data, colWidths=col_widths)

        style_commands = [
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor(self.style.TEXT_PRIMARY)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
        ]

        if header_row and len(data) > 0:
            style_commands.extend([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.style.SECONDARY)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), self.font_bold),
            ])

        if alternate_rows and len(data) > 1:
            for i in range(1, len(data)):
                if i % 2 == 0:
                    style_commands.append(
                        ('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8F9FA'))
                    )

        table.setStyle(TableStyle(style_commands))
        return table

    def create_metric_box(self, label: str, value: str,
                         trend: str = None,
                         color: str = None) -> Table:
        """
        Create a single metric display box

        Args:
            label: Metric name
            value: Metric value
            trend: Optional trend indicator (up/down/neutral)
            color: Value color override
        """
        # Determine value color
        if color:
            value_color = color
        elif trend == 'up':
            value_color = self.style.SUCCESS
        elif trend == 'down':
            value_color = self.style.DANGER
        else:
            value_color = self.style.TEXT_PRIMARY

        # Build content
        content = [
            [Paragraph(label, self.styles['AegisCaption'])],
            [Paragraph(f"<font color='{value_color}'><b>{value}</b></font>",
                      self.styles['AegisBody'])],
        ]

        if trend:
            trend_symbol = "▲" if trend == 'up' else "▼" if trend == 'down' else "―"
            trend_color = self.style.SUCCESS if trend == 'up' else self.style.DANGER if trend == 'down' else self.style.TEXT_SECONDARY
            content[1][0] = Paragraph(
                f"<font color='{value_color}'><b>{value}</b></font> "
                f"<font color='{trend_color}'>{trend_symbol}</font>",
                self.styles['AegisBody']
            )

        box = Table(content, colWidths=[40*mm])
        box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.style.neutral_color),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))

        return box

    def create_metric_row(self, metrics: List[Dict[str, Any]]) -> Table:
        """
        Create a row of metric boxes

        Args:
            metrics: List of dicts with keys: label, value, trend (optional)
        """
        boxes = []
        for m in metrics:
            box = self.create_metric_box(
                label=m.get('label', ''),
                value=m.get('value', ''),
                trend=m.get('trend'),
                color=m.get('color'),
            )
            boxes.append(box)

        row = Table([boxes], colWidths=[42*mm] * len(boxes))
        row.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        return row

    def create_progress_bar(self, value: float, max_value: float = 100,
                           width: float = 100, height: float = 10,
                           color: str = None) -> Drawing:
        """
        Create a progress bar visualization

        Args:
            value: Current value
            max_value: Maximum value (default 100)
            width: Bar width in mm
            height: Bar height in mm
            color: Bar fill color (default: PRIMARY yellow)
        """
        d = Drawing(width * mm, height * mm)

        # Background
        bg = Rect(0, 0, width * mm, height * mm)
        bg.fillColor = colors.HexColor('#E0E0E0')
        bg.strokeColor = None
        d.add(bg)

        # Progress fill
        fill_width = (value / max_value) * width * mm
        bar_color = colors.HexColor(color) if color else self.style.primary_color

        fill = Rect(0, 0, fill_width, height * mm)
        fill.fillColor = bar_color
        fill.strokeColor = None
        d.add(fill)

        return d

    def create_badge(self, text: str, color: str = None) -> Paragraph:
        """
        Create a badge/tag element

        Args:
            text: Badge text
            color: Badge color (default: PRIMARY)
        """
        bg_color = color or self.style.PRIMARY
        return Paragraph(
            f"<font backColor='{bg_color}' color='#1A1A2E'>&nbsp;{text}&nbsp;</font>",
            self.styles['AegisCaption']
        )

    def build_report(self, doc: SimpleDocTemplate, elements: List) -> str:
        """
        Build the final PDF with header/footer

        Args:
            doc: Document created by create_document()
            elements: List of flowables

        Returns:
            Path to generated PDF
        """
        doc.build(
            elements,
            onFirstPage=self.add_header_footer,
            onLaterPages=self.add_header_footer,
        )
        return doc.filename

    # Convenience method for quick reports
    def generate_simple_report(self, filename: str, title: str,
                              sections: List[Dict[str, Any]]) -> str:
        """
        Generate a simple report from section definitions

        Args:
            filename: Output PDF path
            title: Report title
            sections: List of section dicts with keys:
                - title: Section title
                - emoji: Optional emoji
                - content: List of (type, data) tuples
                  Types: 'text', 'table', 'metrics', 'spacer'

        Returns:
            Path to generated PDF
        """
        doc = self.create_document(filename, title)
        elements = []

        # Title
        elements.append(Paragraph(title, self.styles['AegisTitle']))
        elements.append(Spacer(1, 10*mm))

        for section in sections:
            # Section header
            elements.extend(self.create_section_header(
                section.get('title', ''),
                section.get('emoji', '')
            ))

            # Section content
            for item in section.get('content', []):
                item_type = item[0]
                item_data = item[1]

                if item_type == 'text':
                    elements.append(Paragraph(item_data, self.styles['AegisBody']))
                elif item_type == 'table':
                    elements.append(self.create_data_table(item_data))
                elif item_type == 'metrics':
                    elements.append(self.create_metric_row(item_data))
                elif item_type == 'spacer':
                    elements.append(Spacer(1, item_data * mm))
                elif item_type == 'card':
                    card_content = [Paragraph(item_data, self.styles['AegisBody'])]
                    elements.append(self.create_card(card_content))

            elements.append(Spacer(1, self.style.SECTION_SPACING))

        return self.build_report(doc, elements)
