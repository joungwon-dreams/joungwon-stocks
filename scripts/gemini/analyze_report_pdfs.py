"""
Analyze all PDF reports in download/ directory
Extract common data elements and identify what's important
"""
import pdfplumber
import os
from collections import defaultdict
import re

def extract_all_text_from_pdf(pdf_path):
    """Extract all text from PDF"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"   ⚠️ Error reading {pdf_path}: {e}")
    return text

def extract_data_elements(text):
    """Extract common data elements from report text"""
    elements = set()

    # Common financial indicators (Korean)
    patterns = [
        # Basic info
        r'(종목명|회사명|기업명)',
        r'(종목코드|티커)',
        r'(현재가|목표가|목표주가)',
        r'(투자의견|의견)',

        # Price metrics
        r'(시가총액)',
        r'(52주\s*최고가|52주\s*최저가)',
        r'(상승여력)',

        # Financial ratios
        r'(PER|P/E)',
        r'(PBR|P/B)',
        r'(ROE)',
        r'(EPS)',
        r'(BPS)',
        r'(배당수익률)',

        # Growth metrics
        r'(매출액|영업이익|순이익)',
        r'(매출\s*증가율|영업이익\s*증가율)',
        r'(YoY|QoQ)',

        # Quarterly/Annual data
        r'(분기별|연도별)',
        r'(1Q|2Q|3Q|4Q)',

        # Valuation
        r'(적정주가|Fair Value)',
        r'(Valuation)',
        r'(DCF|DDM)',

        # Market data
        r'(외국인\s*지분율|외국인\s*보유비중)',
        r'(기관\s*순매수|외국인\s*순매수)',
        r'(거래량|거래대금)',

        # Business segments
        r'(사업부문|부문별)',
        r'(제품별|지역별)',

        # Forecasts
        r'(전망|Outlook)',
        r'(추정치|컨센서스)',

        # Risk factors
        r'(리스크|위험)',
        r'(모멘텀)',

        # News/Events
        r'(이슈|이벤트)',
        r'(실적발표|어닝)',

        # Peer comparison
        r'(동종업계|경쟁사)',
        r'(업종|섹터)',

        # Chart/Technical
        r'(차트|기술적)',
        r'(이동평균|볼린저)',
    ]

    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            # Extract the matched keyword
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                elements.add(match.group(1))

    return elements

def analyze_all_reports():
    """Analyze all PDF files in download directory"""
    download_dir = "/Users/wonny/Dev/joungwon.stocks/download"
    pdf_files = [f for f in os.listdir(download_dir) if f.endswith('.pdf')]

    print(f"🔍 Analyzing {len(pdf_files)} PDF files...\n")

    # Track elements across all files
    element_frequency = defaultdict(int)
    all_elements = set()
    file_elements = {}

    for pdf_file in pdf_files:
        pdf_path = os.path.join(download_dir, pdf_file)
        print(f"📄 Processing: {pdf_file}")

        # Extract text
        text = extract_all_text_from_pdf(pdf_path)

        # Extract elements
        elements = extract_data_elements(text)
        file_elements[pdf_file] = elements

        # Update frequency
        for elem in elements:
            element_frequency[elem] += 1
            all_elements.add(elem)

        print(f"   Found {len(elements)} elements\n")

    # Sort by frequency (importance indicator)
    sorted_elements = sorted(element_frequency.items(), key=lambda x: x[1], reverse=True)

    print("\n" + "="*80)
    print("📊 ANALYSIS RESULTS")
    print("="*80)

    print(f"\n📈 Total unique elements found: {len(all_elements)}")
    print(f"📁 Total files analyzed: {len(pdf_files)}")

    print("\n\n🎯 DATA ELEMENTS BY IMPORTANCE (Frequency in reports)")
    print("-"*80)
    print(f"{'Element':<30} {'Frequency':<15} {'Coverage':<15}")
    print("-"*80)

    for elem, freq in sorted_elements:
        coverage = f"{freq}/{len(pdf_files)} files"
        importance = "⭐⭐⭐" if freq >= len(pdf_files) * 0.7 else "⭐⭐" if freq >= len(pdf_files) * 0.4 else "⭐"
        print(f"{elem:<30} {freq:<15} {coverage:<15} {importance}")

    return sorted_elements, file_elements

if __name__ == "__main__":
    analyze_all_reports()
