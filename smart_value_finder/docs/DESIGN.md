# Smart Value-Up Finder Design Document

## 1. Project Goal
Develop an automated pipeline to identify stocks that are:
1.  **Undervalued** (Quantitative)
2.  **Supported by Smart Money** (Institutional Buying)
3.  **Backed by Strong Narrative/Policy** (Qualitative via Gemini AI)

## 2. Architecture

### Phase 1: Quantitative Screening (Python)
- **Input:** KOSPI/KOSDAQ All Stocks
- **Tools:** `pykrx`, `FinanceDataReader`, `pandas`
- **Filters:**
    - **Valuation:** 0.2 <= PBR <= 1.0, PER < 10
    - **Technical:** Disparity (20/60 MA) <= 105%, 30 <= RSI <= 60
    - **Supply/Demand:** Net buying by Pension Fund/Investment Trust > 0 (Last 5-20 days)
- **Output:** List of candidate stocks (JSON)

### Phase 2: Qualitative Analysis (Gemini AI)
- **Input:** Candidate list from Phase 1
- **Tools:** `Naver News Crawler`, `Gemini API`
- **Process:**
    1. Collect recent news headlines & summaries (last 7 days).
    2. Collect analyst report summaries.
    3. **Gemini Prompting:**
        - Analyze Policy Alignment (Value-up, K-Defense, Semi, Nuclear, etc.)
        - Analyze Sentiment & Buzz
        - Check for "Turnaround" or "Target Price Up" keywords
- **Output:** AI Analysis Result (Grade, Key Material, Buy Point, Risk)

### Phase 3: Final Scoring & Reporting
- **Logic:**
    - Quantitative Score (40%): Based on PBR depth and Net Buying amount.
    - Qualitative Score (60%): Based on Gemini Grade (S=100, A=80, B=50, C=0).
- **Output:** Final Ranking Report (PDF/Markdown)

## 3. Data Structure

### Input for Gemini (JSON)
```json
{
  "target_stock": {
    "name": "OOO중공업",
    "code": "012345",
    "metrics": {
      "PBR": 0.6,
      "PER": 8.5,
      "RSI": 45,
      "Close": 15000
    },
    "investors": {
      "pension_fund_net_buy_amount": 5000000000,
      "net_buy_days": 5
    },
    "recent_news": [
      {"title": "정부, 신규 원전 건설 계획 발표", "date": "2024-11-25"},
      {"title": "OOO중공업, 3분기 깜짝 실적 기대", "date": "2024-11-24"}
    ],
    "report_summary": "수주 잔고가 충분하고 하반기 턴어라운드 예상."
  }
}
```

### Output from Gemini
```text
종합 등급: A
핵심 재료: 신규 원전 정책 수혜 및 실적 턴어라운드
매수 포인트: 연기금의 5일 연속 매수세와 정부 정책이 맞물리는 시점. PBR 0.6배로 하방 경직성 확보.
리스크: 원자재 가격 상승에 따른 이익률 훼손 가능성.
```

## 4. Directory Structure
(See project root)
