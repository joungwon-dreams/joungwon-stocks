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

### 2.2. Daily Self-Retrospective (AI 일일 회고)
- The system tracks AI's **yesterday's** advice and verifies it with today's result.
- **검증 주기: 1일 (매일 어제 판단을 오늘 검증)**
- Example:
    - *Yesterday:* "Buy More" (Price was 20,000)
    - *Today:* Price is 19,500 (-2.5%)
    - *AI Comment:* "어제 추가 매수 의견을 드렸으나, 외국인 매도세로 -2.5% 하락했습니다. 수급 확인이 부족했습니다."
- This builds trust and improves AI logic over time.

## 3. Architecture & Implementation Plan

### 3.1. Database Schema (`sql/11_create_portfolio_feedback.sql`)
```sql
CREATE TABLE portfolio_ai_history (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL,
    report_date DATE DEFAULT CURRENT_DATE,

    -- Snapshot (당시 상태)
    my_avg_price DECIMAL(15,2),
    market_price DECIMAL(15,2),
    return_rate DECIMAL(5,2),

    -- AI Output (AI 판단)
    recommendation VARCHAR(20), -- 'BUY_MORE', 'HOLD', 'SELL', 'CUT_LOSS'
    rationale TEXT,
    confidence DECIMAL(3,2),    -- 신뢰도 0.0 ~ 1.0

    -- Verification (다음날 검증)
    is_verified BOOLEAN DEFAULT FALSE,
    next_day_price DECIMAL(15,2),         -- 다음날 종가
    next_day_return DECIMAL(5,2),         -- 다음날 수익률
    was_correct BOOLEAN,                   -- 판단 적중 여부

    created_at TIMESTAMP DEFAULT NOW(),
    verified_at TIMESTAMP,

    UNIQUE(stock_code, report_date)
);
CREATE INDEX idx_pf_history_code_date ON portfolio_ai_history(stock_code, report_date);
CREATE INDEX idx_pf_history_unverified ON portfolio_ai_history(is_verified) WHERE is_verified = FALSE;
```

### 3.2. Python Component (`scripts/gemini/components/portfolio_advisor.py`)

#### Class: `PortfolioAdvisor`
- **Methods:**
    1.  `get_yesterday_advice(stock_code)`: Fetch yesterday's AI decision from DB.
    2.  `verify_yesterday_advice(stock_code, today_price)`: 어제 판단을 오늘 가격으로 검증.
    3.  `generate_strategy(stock_info, holding_info, supply_data, news, yesterday_advice)`:
        - **Prompting:**
            - Role: "You are a strict Portfolio Manager."
            - Input: "User bought at 50,000. Current is 48,000. Foreigners are selling. Yesterday you said 'Hold' and price dropped -1.5%. What now?"
            - Output: JSON `{ "action": "...", "rationale": "...", "confidence": 0.75, "review": "..." }`
    4.  `save_decision(...)`: Insert today's decision to DB.

### 3.3. Verification Logic (검증 로직)
```
매일 리포트 생성 시:
1. 어제 판단 조회 (is_verified = FALSE)
2. 오늘 종가로 검증
   - BUY_MORE 추천 → 오늘 상승했으면 was_correct = TRUE
   - SELL 추천 → 오늘 하락했으면 was_correct = TRUE
   - HOLD 추천 → 변동폭 ±1% 이내면 was_correct = TRUE
3. 검증 결과 업데이트 (is_verified = TRUE, next_day_return, was_correct)
4. 오늘의 새 판단 생성 및 저장
```

### 3.4. PDF Integration (`scripts/gemini/generate_pdf_report.py`)

- **Location:** Add a new section at the very end of the report (after `Analyst Targets` / before `Footer`).
- **Visual:**
    - **Box 1: Today's Strategy** - Bold text with color (Green=Buy, Red=Sell, Grey=Hold).
    - **Box 2: Yesterday's Review** - "어제 의견: XX → 결과: +/-X.X% → ✅/❌"

## 4. Action Items for Developer (Claude)

1.  **SQL:** Create `portfolio_ai_history` table.
2.  **Python:** Implement `scripts/gemini/components/portfolio_advisor.py`.
    - Needs `NaverNewsFetcher` and `DaumSupplyFetcher` data as input.
    - Needs `Gemini` integration.
    - **Important:** 검증 주기는 1일 (어제 → 오늘)
3.  **Integration:** Modify `scripts/gemini/generate_pdf_report.py` to:
    - Instantiate `PortfolioAdvisor`.
    - Call `verify_yesterday_advice()` first.
    - Call `generate_strategy()`.
    - Render the result in PDF using `ReportLab`.
    - Save today's decision to DB.

## 5. Example Output in PDF

---
**🤖 AI Portfolio Feedback**

**[오늘의 전략: 비중 확대 (BUY MORE)]** 🟢
평단가(52,000원) 대비 -5% 구간이나, 최근 3일간 연기금 순매수가 지속되고 있습니다.
낙폭 과대로 판단되니 추가 매수로 평단가를 낮추는 것을 제안합니다.
신뢰도: ███████░░░ 72%

**[어제 회고 (11.26)]** ✅
어제 의견: 관망 (HOLD)
어제 종가: 49,500원 → 오늘 종가: 49,200원 (-0.6%)
판정: ✅ 적중 (변동폭 ±1% 이내)

AI 코멘트: 수급 불안정 구간에서 관망을 유지한 것이 유효했습니다.
오늘은 낙폭이 확대되어 매수 기회로 판단됩니다.
---
