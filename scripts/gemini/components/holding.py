
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import cm

def create_holding_status_table(holding, current_price):
    """
    Create a table showing real-time holding status.
    Cols: Quantity, Avg Price, Current Price, Total Cost, Eval Value, P/L, Return(%)
    """
    if not holding:
        return None
        
    quantity = holding['quantity']
    avg_buy_price = float(holding['avg_buy_price'])
    current_price = float(current_price)
    
    total_buy = quantity * avg_buy_price
    eval_amt = quantity * current_price
    profit_loss = eval_amt - total_buy
    return_rate = (profit_loss / total_buy * 100) if total_buy > 0 else 0.0
    
    # Color for P/L and Return
    pl_color = colors.HexColor('#D32F2F') if profit_loss > 0 else colors.HexColor('#1976D2') if profit_loss < 0 else colors.black
    
    # Format data (No units, no decimals for amounts)
    data = [
        ['Quantity', 'Avg Price', 'Cur Price', 'Total Cost', 'Eval Value', 'P/L', 'Return'],
        [
            f"{quantity:,}",
            f"{int(avg_buy_price):,}",
            f"{int(current_price):,}",
            f"{int(total_buy):,}",
            f"{int(eval_amt):,}",
            f"{int(profit_loss):+,}",
            f"{return_rate:+.2f}%"
        ]
    ]
    
    # Adjust column widths
    table = Table(data, colWidths=[2*cm, 2.5*cm, 2.5*cm, 3*cm, 3*cm, 2.5*cm, 2*cm])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
        ('FONTSIZE', (0, 0), (-1, 0), 9), # Header
        ('FONTSIZE', (0, 1), (-1, -1), 10), # Body
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#455A64')), # Dark Header
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        # Apply color to P/L (col 5) and Return (col 6)
        ('TEXTCOLOR', (5, 1), (6, 1), pl_color), 
        ('FONTNAME', (5, 1), (6, 1), 'AppleGothic'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    return table
