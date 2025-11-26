from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, Flowable
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.graphics.shapes import Drawing, Rect, Polygon, String, Line
from reportlab.graphics import renderPDF

def create_consensus_gauge(score):
    """
    Create a gauge chart for consensus score (0.0 - 5.0).
    """
    width = 200
    height = 60
    d = Drawing(width, height)
    
    bw = width / 5
    
    gauge_colors = [
        colors.HexColor('#e3f2fd'), # Strong Sell
        colors.HexColor('#bbdefb'), # Sell
        colors.HexColor('#e8f5e9'), # Hold
        colors.HexColor('#ffebee'), # Buy
        colors.HexColor('#ffcdd2'), # Strong Buy
    ]
    
    for i in range(5):
        d.add(Rect(i*bw, 20, bw, 15, fillColor=gauge_colors[i], strokeColor=None))
    
    line_colors = [
        colors.HexColor('#1565C0'),
        colors.HexColor('#42A5F5'),
        colors.HexColor('#4CAF50'),
        colors.HexColor('#FF9800'),
        colors.HexColor('#F44336'),
    ]
    for i in range(5):
        d.add(Rect(i*bw, 20, bw, 2, fillColor=line_colors[i], strokeColor=None))

    labels = ['강력매도', '매도', '중립', '매수', '강력매수']
    label_colors = [colors.HexColor('#1565C0'), colors.HexColor('#1976D2'), colors.HexColor('#388E3C'), colors.HexColor('#F57C00'), colors.HexColor('#D32F2F')]
    
    for i in range(5):
        d.add(String(i*bw + bw/2, 5, labels[i], fontName='AppleGothic', fontSize=8, textAnchor='middle', fillColor=label_colors[i]))

    safe_score = max(1.0, min(5.0, score))
    pin_x = (safe_score - 1.0) / 4.0 * width
    
    pin_y = 35 
    d.add(Polygon([pin_x, pin_y, pin_x-5, pin_y+8, pin_x+5, pin_y+8], fillColor=colors.red, strokeColor=colors.red))
    d.add(String(pin_x, pin_y+12, f"{score:.2f}", fontName='Helvetica-Bold', fontSize=14, textAnchor='middle', fillColor=colors.red))

    return d


def create_consensus_detail_section(consensus_data):
    """
    Create a Consensus Detail section with Gauge Chart and Detail Table.
    """
    story_elements = []
    
    if not consensus_data:
        return story_elements

    try:
        score = float(consensus_data.get('consensus_score') or 0)
    except:
        score = 3.0
        
    try:
        target = int(consensus_data.get('target_price') or 0)
    except:
        target = 0
    
    gauge = create_consensus_gauge(score)
    
    eps = consensus_data.get('eps') or 0
    per = consensus_data.get('per') or 0.0
    analyst_count = consensus_data.get('analyst_count') or 0
    
    right_data = [
        ['투자의견', '목표주가(원)', 'EPS(원)', 'PER(배)', '추정기관수'],
        [f"{score:.2f}", f"{target:,}", f"{int(eps):,}", f"{float(per):.2f}", f"{int(analyst_count)}"]
    ]
    
    right_table = Table(right_data, colWidths=[2*cm, 2.5*cm, 2*cm, 2*cm, 2*cm])
    right_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.lightgrey),
        ('TEXTCOLOR', (0, 1), (0, 1), colors.red),
        ('FONTNAME', (0, 1), (0, 1), 'AppleGothic'),
    ]))
    
    container_data = [[gauge, right_table]]
    container_table = Table(container_data, colWidths=[8*cm, 11*cm])
    container_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    story_elements.append(container_table)
    story_elements.append(Spacer(1, 0.5*cm))
    
    return story_elements

def create_mini_opinion_bar(opinion_text):
    """
    Create a mini bar chart for analyst opinion (Buy/Hold/Sell).
    """
    width = 60
    height = 12
    d = Drawing(width, height)
    
    sw = width / 3
    d.add(Rect(0, 4, sw, 4, fillColor=colors.HexColor('#1565C0'), strokeColor=None)) # Sell
    d.add(Rect(sw, 4, sw, 4, fillColor=colors.HexColor('#4CAF50'), strokeColor=None)) # Hold
    d.add(Rect(sw*2, 4, sw, 4, fillColor=colors.HexColor('#F44336'), strokeColor=None)) # Buy
    
    pin_x = 0
    pin_color = colors.black
    
    op_lower = opinion_text.lower()
    if '매수' in op_lower or 'buy' in op_lower:
        pin_x = sw*2 + sw/2
        pin_color = colors.HexColor('#F44336')
    elif '중립' in op_lower or 'hold' in op_lower:
        pin_x = sw + sw/2
        pin_color = colors.HexColor('#4CAF50')
    elif '매도' in op_lower or 'sell' in op_lower:
        pin_x = sw/2
        pin_color = colors.HexColor('#1565C0')
    
    d.add(Polygon([pin_x, 1, pin_x-3, 8, pin_x+3, 8], fillColor=pin_color, strokeColor=pin_color))
    
    return d