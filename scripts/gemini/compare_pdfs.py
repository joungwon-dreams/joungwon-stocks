import os
from pypdf import PdfReader

def extract_text_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading {file_path}: {e}"

def analyze_report(file_path):
    filename = os.path.basename(file_path)
    text = extract_text_from_pdf(file_path)
    
    # Keywords to check for
    keywords = {
        "AI Analysis": ["AI", "Gemini", "인공지능", "종합 분석", "투자 의견"],
        "Real-time Data": ["실시간", "현재가", "거래량", "등락률"],
        "Charts": ["차트", "주가 흐름", "수급", "Candle"],
        "Financials": ["PER", "PBR", "ROE", "재무"],
        "News": ["뉴스", "News", "관련 기사"],
        "Consensus": ["컨센서스", "목표주가", "투자의견"]
    }
    
    found_features = []
    for feature, keys in keywords.items():
        if any(k in text for k in keys):
            found_features.append(feature)
            
    return {
        "filename": filename,
        "size_kb": round(os.path.getsize(file_path) / 1024, 2),
        "features": found_features,
        "preview": text[:200].replace('\n', ' ')  # First 200 chars
    }

def main():
    base_dir = "/Users/wonny/Dev/joungwon.stocks/download"
    
    # Files to compare
    my_report = "한국전력_015760.pdf"
    samples = ["sample.pdf", "20251124_company_77878000.pdf"] # Pick a sample and a generated company report
    
    files_to_check = [my_report] + [f for f in samples if os.path.exists(os.path.join(base_dir, f))]
    
    print(f"{'Filename':<30} | {'Size (KB)':<10} | {'Detected Features'}")
    print("-" * 80)
    
    for fname in files_to_check:
        path = os.path.join(base_dir, fname)
        if os.path.exists(path):
            result = analyze_report(path)
            features = ", ".join(result['features'])
            print(f"{result['filename']:<30} | {result['size_kb']:<10} | {features}")
            # print(f"   Preview: {result['preview']}...\n")

if __name__ == "__main__":
    main()
