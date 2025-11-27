# Smart Portfolio Feedback System Specification

## 1. Project Intent (의도)
Transform the existing "Passive" PDF report into an "Active" investment advisor.
- **Current:** Shows charts, news, and fundamental data. (User has to judge)
- **Goal:** AI explicitly suggests **"Buy More / Hold / Sell"** based on the user's average buy price and reviews its **past suggestions** (Retrospective).

## 2. Core Features

### 2.1. Daily Strategy (오늘의 대응 전략)
- AI analyzes the gap between `Avg Buy Price` and `Current Price`.
- Considers Momentum, Supply (Foreigner/Institutional), and News.
- Outputs: **Action** (Buy More/Hold/Sell) and **Rationale**.

### 2.2. Self-Retrospective (AI 회고 및 반성)
- The system tracks AI's past advices.
- Example:
    - *Last Week:* "Buy More" (Price was 20,000)
    - *Today:* Price is 19,000 (-5%)
    - *AI Comment:* "My prediction failed. I underestimated the foreign selling pressure. I will adjust risk tolerance."
- This builds trust and improves AI logic over time.

## 3. Architecture & Implementation Plan

### 3.1. Database Schema (`sql/11_create_portfolio_feedback.sql`)
```sql
CREATE TABLE portfolio_ai_history (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL,
    report_date DATE DEFAULT CURRENT_DATE,
    
    -- Snapshot
    my_avg_price DECIMAL(15,2),
    market_price DECIMAL(15,2),
    return_rate DECIMAL(5,2),
    
    -- AI Output
    recommendation VARCHAR(20), -- 'BUY_MORE', 'HOLD', 'SELL', 'CUT_LOSS'
    rationale TEXT,
    
    -- Verification (Updated later)
    is_verified BOOLEAN DEFAULT FALSE,
    actual_return_after_7d DECIMAL(5,2),
    
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_pf_history_code_date ON portfolio_ai_history(stock_code, report_date);
```

### 3.2. Python Component (`scripts/gemini/components/portfolio_advisor.py`)

#### Class: `PortfolioAdvisor`
- **Methods:**
    1.  `get_past_advice(stock_code, days_ago=7)`: Fetch AI's decision from DB.
    2.  `generate_strategy(stock_info, holding_info, past_advice)`:
        - **Prompting:**
            - Role: "You are a strict Portfolio Manager."
            - Input: "User bought at 50,000. Current is 48,000. Foreigners are selling. Last week you said 'Hold'. What now?"
            - Output: JSON `{ "action": "...", "reason": "...", "review": "..." }`
    3.  `save_decision(...)`: Insert today's decision to DB.

### 3.3. PDF Integration (`scripts/gemini/generate_pdf_report.py`)

- **Location:** Add a new section at the very end of the report (after `Analyst Targets` / before `Footer`).
- **Visual:**
    - **Box 1: Strategy:** Bold text with color (Red=Buy, Blue=Sell, Grey=Hold).
    - **Box 2: Review:** "Last week's advice result: -3.5%. AI's Reflection: ..."

## 4. Action Items for Developer (Claude)

1.  **SQL:** Create `portfolio_ai_history` table.
2.  **Python:** Implement `scripts/gemini/components/portfolio_advisor.py`.
    - Needs `NaverNewsFetcher` and `DaumSupplyFetcher` data as input.
    - Needs `Gemini` integration.
3.  **Integration:** Modify `scripts/gemini/generate_pdf_report.py` to:
    - Instantiate `PortfolioAdvisor`.
    - Call `generate_strategy`.
    - Render the result in PDF using `ReportLab`.
    - Save the result to DB.

## 5. Example Output in PDF

---
**🤖 AI Portfolio Feedback**

**[오늘의 전략: 비중 확대 (BUY MORE)]**
평단가(52,000원) 대비 -5% 구간이나, 최근 3일간 연기금 순매수가 지속되고 있습니다. 낙폭 과대로 판단되니 추가 매수로 평단가를 낮추는 것을 제안합니다.

**[지난주 회고 (24.11.20)]**
당시 '관망' 의견을 드렸고, 이후 주가는 -2% 하락하여 방어에 성공했습니다. 수급이 돌아설 때까지 보수적인 관점을 유지한 것이 유효했습니다.
---
