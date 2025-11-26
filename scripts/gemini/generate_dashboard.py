
from scripts.gemini.fetchers.market import MarketDataFetcher
from scripts.gemini.components.ai_advisor import AIInvestmentAdvisor

class DashboardGenerator:
    def __init__(self):
        self.output_dir = Path('/Users/wonny/Dev/joungwon.stocks/reports')
        self.output_dir.mkdir(exist_ok=True)
        self.chart_dir = self.output_dir / 'charts'
        self.chart_dir.mkdir(exist_ok=True)
        self.market_fetcher = MarketDataFetcher()
        self.ai_advisor = AIInvestmentAdvisor()
        self.market_status = {}
        self.ai_advice = []
        
    async def fetch_data(self):
        """Fetch all asset data AND market data"""
        # 1. Market Data
        self.market_status = await self.market_fetcher.fetch_market_indices()
        
        # 2. Assets
        assets = await db.fetch("SELECT * FROM stock_assets ORDER BY total_value DESC")
        
        self.portfolio = []
        for asset in assets:
            code = asset['stock_code']
            name = asset['stock_name']
            qty = asset['quantity']
            avg_price = float(asset['avg_buy_price'])
            
            # Current Price Logic
            current_price = float(asset['current_price']) # Default from asset table
            
            # Check MinTick
            tick = await db.fetchrow("SELECT price FROM min_ticks WHERE stock_code = $1 ORDER BY timestamp DESC LIMIT 1", code)
            if tick:
                current_price = float(tick['price'])
            else:
                # Check OHLCV
                ohlcv = await db.fetchrow("SELECT close FROM daily_ohlcv WHERE stock_code = $1 ORDER BY date DESC LIMIT 1", code)
                if ohlcv:
                    current_price = float(ohlcv['close'])
            
            total_buy = qty * avg_price
            eval_amt = qty * current_price
            profit = eval_amt - total_buy
            return_rate = (profit / total_buy * 100) if total_buy > 0 else 0.0
            
            self.portfolio.append({
                'code': code,
                'name': name,
                'qty': qty,
                'avg_price': avg_price,
                'current_price': current_price,
                'total_buy': total_buy,
                'eval_amt': eval_amt,
                'profit': profit,
                'return_rate': return_rate
            })
            
        # 3. AI Analysis
        try:
            self.ai_advice = self.ai_advisor.get_investment_advice(self.portfolio, self.market_status)
        except:
            self.ai_advice = []

    def generate_asset_flow_chart(self):
        """Generate a dummy Asset Flow Chart (Area Chart) to match screenshot"""
        fig, ax = plt.subplots(figsize=(6, 2.5), facecolor='#252525')
        ax.set_facecolor('#252525')
        
        # Dummy Data for visualization (Simulating 6 months trend)
        x = range(10)
        y = [100, 102, 105, 104, 108, 110, 112, 111, 115, 118]
        
        ax.plot(x, y, color='#ff4d4d', linewidth=2)
        ax.fill_between(x, y, color='#ff4d4d', alpha=0.2)
        
        ax.tick_params(axis='x', colors='#aaaaaa')
        ax.tick_params(axis='y', colors='#aaaaaa')
        ax.spines['bottom'].set_color('#444444')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.set_xticks([])
        ax.set_yticks([])
        
        chart_path = self.chart_dir / 'asset_flow.png'
        plt.tight_layout()
        plt.savefig(chart_path, dpi=100)
        plt.close()
        return chart_path

    def generate_pdf(self):
        print("📝 Generating Dark Mode Dashboard...")
        output_path = self.output_dir / 'Dashboard.pdf'
        
        # Landscape for wide table
        doc = SimpleDocTemplate(str(output_path), pagesize=landscape(A4),
                                leftMargin=1*cm, rightMargin=1*cm,
                                topMargin=1*cm, bottomMargin=1*cm)
        
        story = []
        
        # --- Styles ---
        style_title = ParagraphStyle('Title', fontName='AppleGothic', fontSize=24, textColor=TEXT_WHITE, leading=30)
        style_label = ParagraphStyle('Label', fontName='AppleGothic', fontSize=10, textColor=TEXT_GRAY)
        style_val_big = ParagraphStyle('ValBig', fontName='AppleGothic', fontSize=28, textColor=TEXT_WHITE, leading=34)
        style_val_sub = ParagraphStyle('ValSub', fontName='AppleGothic', fontSize=12, textColor=COLOR_RED)
        
        # --- 1. Top Section (Summary) ---
        total_buy_sum = sum(p['total_buy'] for p in self.portfolio)
        total_eval_sum = sum(p['eval_amt'] for p in self.portfolio)
        total_profit = total_eval_sum - total_buy_sum
        total_return = (total_profit / total_buy_sum * 100) if total_buy_sum > 0 else 0.0
        
        # Top Layout: Title | Total Asset | Asset Flow Chart
        
        # Title Block
        title_block = [
            [Paragraph("임정원 님의 총자산", style_title)],
            [Paragraph(f"순자산 {int(total_eval_sum):,}원", style_val_sub)] # Simplified
        ]
        
        # Total Asset Block
        profit_color = COLOR_RED if total_profit > 0 else COLOR_BLUE
        profit_sign = "+" if total_profit > 0 else ""
        
        summary_block = [
            [Paragraph(f"{int(total_eval_sum):,}원", style_val_big)],
            [Paragraph(f"{profit_sign}{int(total_profit):,}원 ({total_return:+.2f}%)", ParagraphStyle('P', fontName='AppleGothic', fontSize=12, textColor=profit_color))]
        ]
        
        # Chart Block
        chart_path = self.generate_asset_flow_chart()
        chart_img = Image(str(chart_path), width=8*cm, height=3*cm)
        
        # Combine into one Top Table
        top_data = [
            [
                Table(title_block, style=[('VALIGN', (0,0), (-1,-1), 'TOP')]),
                Table(summary_block, style=[('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (0,0), (-1,-1), 'RIGHT')]),
                chart_img
            ]
        ]
        
        top_table = Table(top_data, colWidths=[8*cm, 8*cm, 10*cm])
        top_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), BG_CARD),
            ('VALIGN', (0,0), (-1,-1), 'CENTER'),
            ('LEFTPADDING', (0,0), (-1,-1), 15),
            ('RIGHTPADDING', (0,0), (-1,-1), 15),
            ('TOPPADDING', (0,0), (-1,-1), 15),
            ('BOTTOMPADDING', (0,0), (-1,-1), 15),
            ('ROUNDEDCORNERS', [10, 10, 10, 10]), # Not supported in standard reportlab table, but simulates card area
        ]))
        
        story.append(top_table)
        story.append(Spacer(1, 1*cm))
        
        # --- 2. Holdings Table (Dark Theme) ---
        
        h_header = ['종목명', '보유수량', '평가금액', '평가손익', '손익률', '현재가', '평균매수단가', '총매수금액']
        h_data = [h_header]
        
        for p in self.portfolio:
            color = COLOR_RED if p['profit'] > 0 else COLOR_BLUE
            
            row = [
                p['name'],
                f"{p['qty']:,}주",
                f"{int(p['eval_amt']):,}",
                f"{int(p['profit']):+,}",
                f"{p['return_rate']:+.2f}%",
                f"{int(p['current_price']):,}",
                f"{int(p['avg_price']):,}",
                f"{int(p['total_buy']):,}"
            ]
            h_data.append(row)
            
        # Table Widths
        col_w = [4*cm, 2*cm, 3*cm, 3*cm, 2*cm, 2.5*cm, 3*cm, 3*cm]
        
        h_table = Table(h_data, colWidths=col_w)
        
        # Styling
        ts = TableStyle([
            # Header
            ('BACKGROUND', (0,0), (-1,0), BG_CARD),
            ('TEXTCOLOR', (0,0), (-1,0), TEXT_GRAY),
            ('FONTNAME', (0,0), (-1,0), 'AppleGothic'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor('#444444')),
            
            # Body
            ('BACKGROUND', (0,1), (-1,-1), BG_DARK),
            ('TEXTCOLOR', (0,1), (-1,-1), TEXT_WHITE),
            ('FONTNAME', (0,1), (-1,-1), 'AppleGothic'),
            ('FONTSIZE', (0,1), (-1,-1), 10),
            ('ALIGN', (1,1), (-1,-1), 'RIGHT'), # Numbers Right Align
            ('ALIGN', (0,1), (0,-1), 'LEFT'),   # Name Left Align
            
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LINEBELOW', (0,1), (-1,-1), 0.5, colors.HexColor('#333333')), # Separator lines
        ])
        
        # Apply Colors for P/L and Return columns (Idx 3, 4)
        for i, p in enumerate(self.portfolio):
            row_idx = i + 1
            c = COLOR_RED if p['profit'] > 0 else COLOR_BLUE
            ts.add('TEXTCOLOR', (3, row_idx), (4, row_idx), c)
            
        h_table.setStyle(ts)
        story.append(h_table)
        story.append(Spacer(1, 1.5*cm))

        # --- 3. AI Strategy Section (New) ---
        story.append(Paragraph("🤖 AI Investment Strategy (Beta)", ParagraphStyle('AIHead', parent=styles['Heading2'], fontName='AppleGothic', textColor=TEXT_WHITE)))
        story.append(Spacer(1, 0.3*cm))
        
        if self.ai_advice:
            ai_header = ['Action', 'Stock', 'Qty', 'Reasoning']
            ai_data = [ai_header]
            
            for item in self.ai_advice:
                action = item.get('action', 'HOLD')
                # Color for action
                a_color = TEXT_WHITE
                if action == 'BUY': a_color = COLOR_RED
                elif action == 'SELL': a_color = COLOR_BLUE
                
                ai_data.append([
                    action,
                    item.get('stock', ''),
                    str(item.get('qty', '-')),
                    item.get('reason', '')
                ])
                
            ai_table = Table(ai_data, colWidths=[3*cm, 4*cm, 2*cm, 16*cm])
            ai_ts = TableStyle([
                ('BACKGROUND', (0,0), (-1,0), BG_CARD),
                ('TEXTCOLOR', (0,0), (-1,0), TEXT_GRAY),
                ('FONTNAME', (0,0), (-1,-1), 'AppleGothic'),
                ('BACKGROUND', (0,1), (-1,-1), BG_DARK),
                ('TEXTCOLOR', (0,1), (-1,-1), TEXT_WHITE),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#444444')),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ])
            
            # Apply Action colors
            for i, item in enumerate(self.ai_advice):
                act = item.get('action', '').upper()
                if act == 'BUY': c = COLOR_RED
                elif act == 'SELL': c = COLOR_BLUE
                else: c = TEXT_WHITE
                ai_ts.add('TEXTCOLOR', (0, i+1), (0, i+1), c)
                ai_ts.add('FONTNAME', (0, i+1), (0, i+1), 'AppleGothic') # Bold if possible
                
            ai_table.setStyle(ai_ts)
            story.append(ai_table)
        else:
            story.append(Paragraph("Analyzing market data...", ParagraphStyle('Normal', fontName='AppleGothic', textColor=TEXT_GRAY)))
        
        doc.build(story, onFirstPage=self.draw_background, onLaterPages=self.draw_background)
        print(f"✅ Dashboard saved: {output_path}")
