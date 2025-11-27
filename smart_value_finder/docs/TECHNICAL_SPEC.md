# Smart Value-Up Finder - Technical Specification

## 1. System Overview
A fully automated stock discovery pipeline that combines quantitative metrics (safety margin, smart money flow) with qualitative AI analysis (policy alignment, news sentiment) to identify undervalued stocks with high upside potential.

## 2. Detailed Architecture & Implementation Plan

### Phase 1: Quantitative Screener (`src/collectors/quant_screener.py`)

**Objective:** Filter ~900 KOSPI stocks down to ~20 high-potential candidates.

**Libraries:**
- `pykrx`: For price, fundamental data (PER/PBR), and investor trading data.
- `pandas`: Data manipulation.
- `pandas_ta` (optional): For RSI calculation if manual calculation is too verbose.

**Filtering Logic (The "Safety & Growth" Strategy):**

1.  **Market Universe:**
    - KOSPI Only (excluding KONEX).
    - Exclude Administrative Issues (관리종목) & Trading Halt (거래정지) stocks if possible via API.

2.  **Value Filter (Safety Margin):**
    - **PBR (Price-to-Book Ratio):** `0.2 <= PBR <= 1.2`
        - *Rationale:* Avoid zombie companies (<0.2) and overvalued stocks (>1.2). Target asset-rich companies suitable for "Value-up".
    - **PER (Price-to-Earnings Ratio):** `0 < PER <= 15`
        - *Rationale:* Must be profitable (PER > 0) and reasonably priced relative to earnings.

3.  **Technical Filter (Entry Timing):**
    - **RSI (14-day):** `30 <= RSI <= 65`
        - *Rationale:* Avoid Overbought (>70) zones. Look for stocks consolidating or starting to rise.
    - **Disparity (이격도):** `(Close / MA60) * 100 <= 110`
        - *Rationale:* Avoid stocks that have already surged significantly.

4.  **Smart Money Filter (Institutional Validation):**
    - **Pension Fund (연기금):** Net Buying (Volume/Value) > 0 in last 5 trading days.
    - **Investment Trust (투신):** Net Buying > 0 in last 5 trading days.
    - *Logic:* Pass if EITHER Pension OR Trust is net buying. These entities are long-term value investors.

**Output:**
- File: `data/processed/screened_candidates_{date}.json`
- Content: List of stock objects with Code, Name, Close, PBR, PER, RSI, NetBuy_Pension, NetBuy_Trust.

---

### Phase 2: Qualitative AI Analyzer (`src/analysis/gemini_analyzer.py`)

**Objective:** Analyze the "Narrative" and "Catalyst" for the screened stocks using Gemini Pro.

**Data Collection (`src/collectors/news_fetcher.py`):**
- Source: Naver Finance News (Mobile API).
- Scope: Last 7 days of news headlines and summaries.
- Limit: Top 5-10 most relevant articles per stock.

**Gemini Prompt Engineering:**

*   **System Role:** "You are an expert Fund Manager specializing in Korean undervalued stocks (Value-up)."
*   **Input Data:**
    - Stock Info: Name, PBR, PER, Market Cap.
    - Supply: "Pension fund has been buying for N days."
    - News List: List of [Date, Title, Summary].
*   **Analysis Tasks:**
    1.  **Policy Alignment:** Does the company benefit from current govt policies (Value-up, K-Defense, Nuclear, Semi, Bio)?
    2.  **Catalyst Check:** Are there keywords like "Turnaround", "Contract", "Expansion", "Merger"?
    3.  **Sentiment:** Is the news tone "Expectation" or "Concern"?
*   **Output Format (JSON):**
    ```json
    {
      "grade": "S/A/B/C",
      "catalyst": "One-line summary of key material",
      "buy_thesis": "Why buy now?",
      "risk_factors": "Potential downsides"
    }
    ```

---

### Phase 3: Final Scoring & Visualization (`src/reporting/final_report.py`)

**Objective:** Rank the analyzed stocks and generate a readable report.

**Scoring Algorithm:**
- **Base Score:** 50 points.
- **Quant Bonus:**
    - Low PBR (<0.6): +10 points.
    - Strong Supply (Pension Net Buy > 100M KRW): +10 points.
- **AI Score:**
    - Grade S: +30 points.
    - Grade A: +20 points.
    - Grade B: +0 points.
    - Grade C: -20 points (Discard).

**Output:**
- **Final Selection:** Top 3-5 stocks.
- **Format:** Markdown Report or PDF (using ReportLab as in previous modules).
- **File:** `reports/Smart_Value_Picks_{date}.pdf`

---

## 3. Implementation Roadmap

1.  **Step 1 (Quant):** Implement `QuantScreener` class.
    - Method: `fetch_fundamentals()`
    - Method: `fetch_technical_indicators()`
    - Method: `fetch_investor_trends()`
    - Method: `run_screening()` -> Returns list.

2.  **Step 2 (Data Fetch):** Implement `NewsFetcher` class.
    - Reuse existing `NaverNewsFetcher` logic but optimized for batch processing.

3.  **Step 3 (AI):** Implement `GeminiAnalyzer` class.
    - Integrate `google.generativeai`.
    - Implement the structured prompt.
    - Handle API rate limits (batch processing with delays).

4.  **Step 4 (Integration):** Create `main.py`.
    - Orchestrate Phase 1 -> Phase 2 -> Phase 3.
    - Error handling and logging (`logs/smart_value.log`).

## 4. Usage

```bash
# Run the full pipeline
python smart_value_finder/main.py --top 5
```

## 5. Optimization Strategy (For Scalability)

To efficiently process ~900 KOSPI stocks without API limits or timeouts:

1.  **Funnel Approach (Pre-Filtering):**
    - Instead of looping through all stocks, use **batch API calls** from `pykrx` to get market-wide data.
    - **Step 1:** `stock.get_market_fundamental_by_ticker(date, market="KOSPI")` retrieves PBR/PER for all KOSPI stocks in ONE call. Filter immediately (PBR < 1.2, PER > 0). This reduces candidates from ~900 to ~300-400.
    - **Step 2:** `stock.get_market_net_purchases_of_equities_by_ticker(date, market="KOSPI")` retrieves institutional buying for all KOSPI stocks in ONE call. Iterate for last 5 days and sum up. Filter candidates with positive Net Buying. This reduces candidates to ~50-100.

2.  **Targeted Data Collection:**
    - Only for the final ~100 candidates, fetch OHLCV history to calculate RSI and Disparity.
    - This drastically reduces the number of heavy computations and historical data fetches.

3.  **Asynchronous Processing:**
    - Use `asyncio` for the remaining ~20-30 finalists when fetching News and Qualitative data, as these require web scraping or external API calls which are I/O bound.