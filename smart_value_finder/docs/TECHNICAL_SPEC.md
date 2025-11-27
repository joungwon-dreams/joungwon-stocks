
---

## 6. Phase 4: Performance Tracking & Feedback Loop (Post-Analysis)

**Objective:** Track the actual market performance of recommended stocks and refine the AI's judgment criteria based on results.

### 6.1 Database Schema (Extension)
Leverage existing `recommendation_history` and `verification_results` tables, or create specialized tables for this finder:

- **`smart_recommendations` Table:**
    - `id`, `stock_code`, `recommendation_date`, `ai_grade`, `base_price` (at recommendation), `target_price` (AI suggested), `stop_loss_price`.
    - `ai_rationale` (Summary of why it was picked).

- **`smart_performance` Table:**
    - `recommendation_id` (FK), `check_date` (e.g., +1 week, +1 month).
    - `current_price`, `return_rate`, `max_profit`, `max_drawdown`.
    - `status` (Active, Closed-Profit, Closed-Loss).

### 6.2 Feedback Mechanism (Self-Improvement)

1.  **Weekly Performance Review Job:**
    - Calculate return rates for all active recommendations.
    - Identify "Success" (e.g., > +5%) and "Failure" (e.g., < -5%) cases.

2.  **AI Retrospective (The Learning Loop):**
    - **Input:** Failed case's original analysis + Actual market outcome + News during the period.
    - **Prompt:** "You recommended Stock X on [Date] citing [Reason]. However, it dropped 10% due to [Reason]. Analyze what was missed in the initial assessment. Update your 'Risk Analysis criteria' for future evaluations."
    - **Output:** Updated "System Instruction" or specific "Watchlist Keywords" for the next Phase 2 run.

---

## 7. Development Considerations & Best Practices

### 7.1 Data Integrity & Bias
-   **Look-ahead Bias:** Ensure Phase 1 screening only uses data available *before* the market open or after close of the target date.
-   **Survivor Bias:** `pykrx` generally handles delisted stocks correctly, but be aware that filtering only "currently active" stocks for backtesting might skew results.
-   **Adjusted Prices:** Always use adjusted prices (수정주가) for technical analysis (RSI, MA) to account for dividends/splits.

### 7.2 API Management
-   **Rate Limiting:**
    - Gemini API: Implement exponential backoff (as done in `analyze_paradise_deep.py`).
    - Naver/Daum: Use random delays between requests (2-5 seconds) if scraping.
-   **Cost Control:** Monitor Gemini token usage. Optimize prompts to be concise.

### 7.3 System Stability
-   **Error Handling:** The pipeline should not crash if one stock fails. Log the error and move to the next.
-   **Logging:** Maintain detailed logs (`logs/smart_value.log`) for every decision step (Why was Stock A filtered out in Phase 1? Why did AI reject Stock B?).

### 7.4 Execution Strategy
-   **Timing:** Run Phase 1 (Quant) after market close (e.g., 16:00 KST).
-   **Review:** Run Phase 2 (AI) overnight or early morning.
-   **Trading:** Human final review recommended before actual trading execution based on Phase 3 report.
