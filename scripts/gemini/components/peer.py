
import io
import matplotlib.pyplot as plt
import numpy as np
from reportlab.platypus import Image, Table, TableStyle
from reportlab.lib.units import cm
from reportlab.lib import colors

def generate_peer_comparison_chart(peers_data, output=None):
    """
    Generate a bar chart comparing PER/PBR/ROE of peers.
    If output is None, returns BytesIO buffer.
    If output is a path, saves to file (backward compatible).
    """
    if not peers_data:
        return None

    companies = [p['name'] for p in peers_data]
    per = [p.get('per', 0) for p in peers_data]
    pbr = [p.get('pbr', 0) for p in peers_data]

    x = np.arange(len(companies))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 4))
    rects1 = ax.bar(x - width/2, per, width, label='PER', color='#8884d8')
    rects2 = ax.bar(x + width/2, pbr, width, label='PBR', color='#82ca9d')

    ax.set_ylabel('Multiple')
    ax.set_xticks(x)
    ax.set_xticklabels(companies, fontfamily='AppleGothic')
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.5)

    plt.tight_layout()

    # BytesIO 버퍼에 저장
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    # 기존 파일 저장 방식도 지원 (backward compatible)
    if output is not None:
        with open(output, 'wb') as f:
            f.write(buf.getvalue())
        buf.seek(0)
        return output

    return buf

def create_peer_table(peers_data):
    """
    Create a formatted table for peer comparison.
    Cols: Name, Price, MarketCap, PER, PBR, ROE
    """
    data = [['종목명', '현재가', '시가총액(억)', 'PER', 'PBR', 'ROE']]
    
    for p in peers_data:
        # Safe float helper
        def sf(v):
            try: return float(v or 0)
            except: return 0.0
            
        per = sf(p.get('per'))
        pbr = sf(p.get('pbr'))
        roe = sf(p.get('roe'))
        
        data.append([
            p['name'],
            f"{p['price']:,}",
            f"{p['market_cap'] // 100000000:,}",
            f"{per:.2f}",
            f"{pbr:.2f}",
            f"{roe:.2f}%"
        ])
        
    table = Table(data, colWidths=[3.5*cm, 2.5*cm, 3.5*cm, 2*cm, 2*cm, 2.5*cm])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'AppleGothic'),
        ('FONTSIZE', (0, 0), (-1, 0), 9), 
        ('FONTSIZE', (0, 1), (-1, -1), 9), 
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'), 
        ('ALIGN', (0, 0), (0, -1), 'CENTER'), 
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F0F0')), 
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    return table
