"""
Deep Analysis for Paradise (034230)
Collects all available data and uses Gemini AI to generate a free-form investment strategy report.
"""
import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import google.generativeai as genai
from dotenv import load_dotenv

sys.path.insert(0, '/Users/wonny/Dev/joungwon.stocks')

from src.config.database import db
from scripts.gemini.naver.news import NaverNewsFetcher
from scripts.gemini.naver.consensus import NaverConsensusFetcher
from scripts.gemini.daum.supply import DaumSupplyFetcher
from scripts.gemini.daum.price import DaumPriceFetcher
from scripts.gemini.daum.financials import DaumFinancialsFetcher

# Load Env
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Font Registration
try:
    pdfmetrics.registerFont(TTFont('AppleGothic', '/System/Library/Fonts/Supplemental/AppleGothic.ttf'))
except:
    pass

async def collect_all_data(stock_code, stock_name):
    """Collect comprehensive data for deep analysis"""
    print(f"🔍 Collecting raw data for {stock_name} ({stock_code})...")
    
    data = {}
    
    # 1. Basic Price & Info
    print("   - Fetching Price...")
    daum_price = DaumPriceFetcher()
    data['quote'] = await daum_price.fetch_quote(stock_code)
    
    # 2. Supply (Investor Trends) - Last 30 days
    print("   - Fetching Investor Trends...")
    daum_supply = DaumSupplyFetcher()
    data['supply'] = await daum_supply.fetch_history(stock_code, days=30)
    
    # 3. Financials
    print("   - Fetching Financials...")
    daum_fin = DaumFinancialsFetcher()
    data['financials'] = await daum_fin.fetch_ratios(stock_code)
    data['statements'] = await daum_fin.fetch_statements(stock_code)
    
    # 4. Consensus
    print("   - Fetching Consensus...")
    naver_cons = NaverConsensusFetcher()
    data['consensus'] = await naver_cons.fetch_consensus(stock_code)
    
    # 5. News (Real-time)
    print("   - Fetching News...")
    naver_news = NaverNewsFetcher()
    data['news'] = await naver_news.fetch_news(stock_code)
    
    return data

async def analyze_with_ai(stock_name, stock_code, data):
    """Send data to Gemini and get a deep analysis"""
    print("🧠 Sending data to Gemini for analysis...")
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Prepare Context
    news_summary = "\n".join([f"- {n['title']} ({n['sentiment']})" for n in data['news'][:5]])
    
    supply_summary = "No supply data"
    if data['supply']:
        recent = data['supply'][-1]
        supply_summary = f"Latest: Individual {recent['individual']}, Foreign {recent['foreign']}, Inst {recent['institutional']}"
        
    financial_summary = f"PER: {data['financials'].get('ratios', {}).get('per', 'N/A')}, PBR: {data['financials'].get('ratios', {}).get('pbr', 'N/A')}"
    
    consensus_summary = "No consensus"
    if data['consensus']:
        c = data['consensus']
        consensus_summary = f"Opinion: {c.get('opinion', 'N/A')}, Target: {c.get('target_price', 'N/A')}"

    prompt = f"""
당신은 월스트리트의 전설적인 펀드매니저입니다. 아래 제공된 데이터를 바탕으로 '{stock_name}({stock_code})'에 대한 심층 투자 리포트를 작성하세요.
형식에 구애받지 말고, 오직 데이터에 기반한 통찰과 판단을 서술하세요.

[수집된 데이터]
1. 현재가 및 시황: {data['quote']}
2. 수급 동향 (최근): {supply_summary}
3. 재무 지표: {financial_summary}
4. 컨센서스: {consensus_summary}
5. 최근 주요 뉴스:
{news_summary}

[요청 사항]
1. **현재 상황 진단:** 주가 흐름, 수급 주체들의 움직임(외국인/기관 매집 여부 등)을 분석하세요.
2. **재무 및 펀더멘털:** 현재 밸류에이션이 적절한지, 저평가/고평가 상태인지 평가하세요.
3. **모멘텀 및 리스크:** 뉴스에 기반한 호재와 잠재적 악재를 분석하세요. 파라다이스의 경우 카지노/관광 산업 업황을 고려하세요.
4. **최종 판단 (결론):** 
   - 매수 / 매도 / 관망 중 하나를 명확히 선택하세요.
   - 목표가와 손절가를 제안하세요.
   - 구체적인 대응 전략(분할 매수, 비중 축소 등)을 조언하세요.

어조는 전문적이고 단호하게, 그러나 논리적으로 작성해 주세요. 마크다운 형식은 쓰지 말고 줄글로 작성해 주세요.
"""
    
    import time
    max_retries = 3
    base_delay = 10
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e):
                print(f"⚠️ Quota exceeded. Retrying in {base_delay * (attempt + 1)} seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(base_delay * (attempt + 1))
            else:
                print(f"❌ Gemini Error: {e}")
                return "AI 분석을 생성하는 도중 오류가 발생했습니다."
    
    return "API 할당량 초과로 분석을 생성하지 못했습니다."

def create_pdf(text, output_path):
    """Create raw text PDF"""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    # Normal style with Korean font
    style_normal = ParagraphStyle(
        'KoreanNormal',
        parent=styles['Normal'],
        fontName='AppleGothic',
        fontSize=11,
        leading=18,
        spaceAfter=12
    )
    
    style_title = ParagraphStyle(
        'KoreanTitle',
        parent=styles['Heading1'],
        fontName='AppleGothic',
        fontSize=24,
        leading=30,
        spaceAfter=30,
        alignment=1 # Center
    )

    story = []
    
    # Title
    story.append(Paragraph("파라다이스 (034230) AI 심층 투자 분석", style_title))
    story.append(Paragraph(f"생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}", style_normal))
    story.append(Spacer(1, 1*cm))
    
    # Body (Split by newlines for paragraphs)
    for para in text.split('\n'):
        if para.strip():
            # Bold headers logic (simple)
            if para.strip().startswith(('1.', '2.', '3.', '4.', '최종', '결론', '매수', '매도')):
                 story.append(Paragraph(f"<b>{para}</b>", style_normal))
            else:
                 story.append(Paragraph(para, style_normal))
            
    doc.build(story)
    print(f"✅ PDF Created: {output_path}")

async def main():
    stock_code = '034230'
    stock_name = '파라다이스'
    
    # 1. Collect Data
    data = await collect_all_data(stock_code, stock_name)
    
    # 2. Analyze
    analysis_text = await analyze_with_ai(stock_name, stock_code, data)
    print("\n--- AI Analysis Result ---")
    print(analysis_text[:200] + "...")
    print("--------------------------\n")
    
    # 3. Save PDF
    output_path = Path(f'/Users/wonny/Dev/joungwon.stocks/reports/{stock_name}_detail.pdf')
    create_pdf(analysis_text, output_path)

if __name__ == '__main__':
    asyncio.run(main())