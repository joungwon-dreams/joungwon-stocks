# Joungwon Stocks: System Evolution Design Specification
> **Version:** 1.0
> **Author:** Gemini (Architect)
> **Target:** Claude (Implementer)
> **Date:** 2025-11-28

This document outlines the detailed technical design for evolving the `joungwon.stocks` system from a simple data collector to a fully automated, AI-driven trading system.

---

## 📐 Phase 1: Validation & Backtesting Framework
**Objective:** Verify the profitability of trading logic using historical data before risking real capital.

### 1.1 Architecture
- **Module Path:** `src/analysis/backtest/`
- **Core Components:**
    1.  **`BacktestEngine`**: The runner that iterates through historical `min_ticks` data.
    2.  **`StrategyInterface`**: Abstract base class for all strategies.
    3.  **`PerformanceMonitor`**: Calculates MDD, CAGR, Sharpe Ratio.

### 1.2 Detailed Specs

#### A. `BacktestEngine` (Class)
- **Input:** `pandas.DataFrame` (Time-series data: timestamp, open, high, low, close, volume).
- **Methods:**
    - `run(strategy: StrategyInterface, initial_capital: float = 100_000_000)`: Executes the simulation.
    - `_match_order(signal, price)`: Simulates order execution with **Slippage (0.05%)** and **Commission (0.015%)**.
- **Logic:** 
    - Use vectorized operations (Pandas) where possible for speed, or a simple event-loop if signal logic is complex.

#### B. `PerformanceMonitor` (Class)
- **Methods:**
    - `calculate_mdd(equity_curve)`: Returns Max Drawdown %.
    - `calculate_win_rate(trade_history)`: Returns Win %.
    - `generate_report()`: Outputs an HTML or Text summary.

---

## 📐 Phase 2: Risk Management System
**Objective:** Protect capital by mathematically sizing bets and managing stop-losses.

### 2.1 Architecture
- **Module Path:** `src/core/risk/`
- **Integration:** Called by the `OrderExecutor` before sending any buy order.

### 2.2 Detailed Specs

#### A. `RiskManager` (Class)
- **Configuration:** `MAX_CAPITAL_PER_TRADE` (e.g., 5%), `MAX_DAILY_LOSS` (e.g., -2%).
- **Methods:**
    - `calculate_position_size(capital, risk_per_trade, stop_loss_gap)`:
        - Logic: Uses **Kelly Criterion** (fractional) or Fixed Fractional Risk (1-2% risk of total capital).
    - `calculate_dynamic_stop_loss(df)`:
        - Logic: Returns price level based on `Close - (ATR(14) * 2)`.

#### B. `CircuitBreaker` (Class)
- **Logic:** Checks `daily_pnl`. If loss > 2%, raises `TradingHaltedException` to stop all new buys for the day.

---

## 📐 Phase 3: Multi-Strategy Ensemble
**Objective:** Adapt to changing market conditions (Bull/Bear/Sideways) by blending multiple strategies to maximize win rate and minimize drawdown.

### 3.1 Architecture
- **Module Path:** `src/aegis/ensemble/`
- **Core Components:**
    1.  **`MarketRegimeClassifier`**: Analyzes market trends to determine current regime.
    2.  **`StrategyRegistry`**: Holds instances of all available strategies.
    3.  **`StrategyOrchestrator`**: The conductor that requests signals from all strategies and computes the final weighted signal.

### 3.2 Detailed Specs

#### A. `MarketRegimeClassifier` (Class)
- **Methods:**
    - `analyze(df: pd.DataFrame) -> MarketRegime` (Enum: BULL, BEAR, SIDEWAY)
- **Logic:**
    - **BULL:** Price > MA(20) > MA(60) AND ADX > 25 (Strong Trend)
    - **BEAR:** Price < MA(20) < MA(60) AND ADX > 25
    - **SIDEWAY:** MA(20) oscillating around MA(60) OR ADX < 20 (Weak Trend)
    - *Alternative simple logic:* Use `ma_slope` or `bollinger_band_width`.

#### B. `StrategyRegistry` (Class)
- **Role:** Factory/Repository for strategies.
- **Strategies to Implement:**
    1.  **`SwingStrategy`** (Existing): VWAP + RSI + MA (Score-based). Good for trends & pullbacks.
    2.  **`MeanReversionStrategy`** (New): Bollinger Band Reversal. Good for SIDEWAY.
    3.  **`TrendFollowingStrategy`** (New): MACD + DMI. Good for strong BULL/BEAR.

#### C. `StrategyOrchestrator` (Class)
- **Logic (Ensemble Voting):**
    - Calls `calculate_signal()` on ALL registered strategies.
    - Gets current `MarketRegime`.
    - Applies **Dynamic Weights** based on regime:
        - **If BULL:** TrendFollowing(50%) + Swing(30%) + MeanReversion(20%)
        - **If SIDEWAY:** MeanReversion(60%) + Swing(30%) + TrendFollowing(10%)
        - **If BEAR:** Defensive Weights (or Cash logic)
    - **Final Signal:**
        - `Weighted_Score = sum(strategy_score * weight)`
        - If `Weighted_Score` >= Threshold -> **FINAL_BUY_SIGNAL**

### 3.3 Action Plan
1.  Refactor existing `SwingStrategy` to conform to a strictly typed `IStrategy` interface (if not already).
2.  Implement `MarketRegimeClassifier` with basic MA logic.
3.  Implement `StrategyOrchestrator` to blend signals.
4.  (Optional for now) Add `MeanReversionStrategy` as a second strategy to test the ensemble.

## 📐 Phase 3.5: Ensemble Optimization & Verification
**Objective:** Maximize the performance of the Ensemble system by tuning weights and verifying robustness across diverse market conditions before adding AI models.

### 3.5.1 Architecture
- **Module Path:** `src/aegis/optimization/`
- **Core Components:**
    1.  **`WeightOptimizer`**: Finds the best weight combination for each regime.
    2.  **`RobustnessTester`**: Validates strategy across multiple assets and timeframes.

### 3.5.2 Detailed Specs

#### A. `WeightOptimizer` (Class)
- **Method:** Grid Search (Simple & Effective)
- **Logic:**
    - Iterate weights for Swing vs. MeanReversion (e.g., 90:10, 80:20 ... 10:90).
    - Run backtest for each combination on a specific Regime period (e.g., filter data where Regime=BULL).
    - **Metric:** Maximize `Sharpe Ratio` or `Profit Factor`.
- **Output:** Optimal weight configuration dictionary (e.g., `{'BULL': {'Swing': 0.8, 'MeanRev': 0.2}, ...}`).

#### B. `RobustnessTester` (Class)
- **Data Source:** Select 5 diverse stocks representing different sectors/volatility (e.g., KEPCO(Stable), Kakao(Volatile), Samsung Elec(Large Cap)).
- **Periods:**
    - Bull Market (e.g., 2023 Q4)
    - Bear Market (e.g., 2022)
    - Sideways (e.g., Recent months)
- **Process:**
    - Run `EnsembleStrategy` with optimized weights on all datasets.
    - Aggregates results: Win Rate, MDD, CAGR.
    - **Fail Condition:** If any single stock has MDD > 10%, the weights are rejected (Too risky).

## 📐 Phase 3.9: Advanced Data Pipeline
**Objective:** Upgrade the data collection layer (Fetchers) to provide high-quality, real-time, and noise-free data to AEGIS. "Garbage In, Garbage Out" prevention.

### 3.9.1 Architecture
- **Module Path:** `src/fetchers/advanced/`
- **Core Components:**
    1.  **`EnhancedNewsFetcher`**: Real-time de-duplication and relevance scoring.
    2.  **`MarketScanner`**: Monitors sector performance and market breadth.
    3.  **`DataCleaner`**: Standardizes data formats and handles missing values.

### 3.9.2 Detailed Specs

#### A. `EnhancedNewsFetcher`
- **Improvements:**
    - **De-duplication:** Use Cosine Similarity or simple Title fuzzy matching to group similar news (e.g., "Samsung earnings up" vs "Samsung Q3 profit rises").
    - **Priority Scoring:** Assign score (1-5) based on keywords (e.g., "Exclusive", "Breaking", "Contract").
    - **Speed:** Separate "Headline Scanning" (every 30s) from "Full Content Parsing" (on demand).

#### B. `MarketScanner`
- **Role:** Provide "Context" to AEGIS.
- **Metrics:**
    - **Sector Heatmap:** Which sectors are leading today? (e.g., Semi, Bio, Auto).
    - **Market Breadth:** ADR (Advance-Decline Ratio) to gauge market sentiment.
    - **Foreigner/Institutional Net Buying:** Real-time estimation.

#### C. `DataCleaner`
- **Role:** Quality Assurance.
- **Functions:**
    - Detect and repair outliers in `min_ticks` (e.g., price spikes due to data errors).
    - Fill missing `OHLCV` gaps with forward-fill.

---

## 📐 Phase 4: Multi-modal Information Fusion & Dynamic Optimization
**Objective:** Maximize win rate by integrating "field information" (News, Disclosures, Analyst Reports, Supply/Demand, Fundamentals) with technical analysis.

### 4.1 Architecture
- **Module Path:** `src/aegis/fusion/`
- **Core Components:**
    1.  **`InformationFusionEngine`**: The central brain that aggregates signals from all analyzers.
    2.  **`DisclosureAnalyzer`**: Analyzes DART disclosures for critical events.
    3.  **`SupplyDemandAnalyzer`**: Evaluates investor flows (Foreigner/Institutional).
    4.  **`FundamentalIntegrator`**: Checks financial health (ROE, Debt Ratio, OPM).
    5.  **`NewsSentimentAnalyzer`**: (Already planned) Real-time news sentiment.
    6.  **`ConsensusMomentum`**: (Already planned) Analyst target trends.

### 4.2 Detailed Specs

#### A. `DisclosureAnalyzer`
- **Input:** DART API (via `dart-fss` or `opendartreader`).
- **Logic:**
    -   **Critical Keywords:** "Supply Contract", "Capital Increase", "Embezzlement", "Stock Buyback".
    -   **Impact Scoring:**
        -   Supply Contract (>10% rev): +2.0
        -   Stock Buyback / Insider Buy: +1.0
        -   Capital Increase (General Public): -2.0
        -   Embezzlement / Breach of Trust: **TRADING HALT**
-   **Output:** `disclosure_score` (float), `trading_halt` (bool).

#### B. `SupplyDemandAnalyzer`
- **Input:** Daily/Real-time investor trading data (from `pykrx` or KIS API).
- **Logic:**
    -   **Foreigner/Institutional Dual Buy:** +1.0
    -   **Continuous Net Buying (3+ days):** +0.5
    -   **Program Net Buying:** +0.5
    -   **High Short Selling Volume:** -1.0
-   **Output:** `supply_score` (float).

#### C. `FundamentalIntegrator`
- **Input:** Quarterly financial statements.
- **Logic:**
    -   **Profitability:** OPM > Industry Avg (+0.5)
    -   **Stability:** Debt Ratio < 200% (Pass/Fail)
    -   **Efficiency:** ROE > 10% (+0.5)
-   **Output:** `fundamental_score` (float).

#### D. `InformationFusionEngine`
- **Input:** All scores from sub-analyzers + `MarketScanner` context.
- **Logic:**
    -   Normalize all scores to a -1.0 to +1.0 scale (or similar).
    -   Apply dynamic weights ($W_n$) based on Market Regime (from Phase 3).
-   **Formula:**
    $$ Score_{final} = W_{tech}S_{tech} + W_{news}S_{news} + W_{disc}S_{disc} + W_{supply}S_{supply} + W_{fund}S_{fund} + W_{mkt}S_{mkt} $$
-   **Decision:**
    -   $Score_{final} \ge 2.0$: **STRONG BUY**
    -   $Score_{final} \ge 1.0$: **BUY**
    -   *Trading Halt* from Disclosure overrides all.

### 4.3 Action Plan
1.  Implement **`DisclosureAnalyzer`** (Critical for risk avoidance).
2.  Implement **`SupplyDemandAnalyzer`** (Follow the money).
3.  Implement **`FundamentalIntegrator`** (Basic health check).
4.  Build **`InformationFusionEngine`** to combine these with existing Technical & News signals.

## 📐 Phase 5.0: Advanced Market Context & Calendar
**Objective:** Enhance decision quality by incorporating "Time" (Economic Calendar) and "Sentiment" (Market Overheat/Fear) into the AEGIS system.

### 5.0.1 Architecture
- **Module Path:** `src/aegis/context/`
- **Core Components:**
    1.  **`MacroCalendarFetcher`**: Tracks major economic events (FOMC, CPI, Options Expiry).
    2.  **`PassiveFundTracker`**: Monitors index rebalancing events (MSCI, KOSPI200).
    3.  **`MarketSentimentMeter`**: Gauges market fear/greed using VIX, Credit Balance, Market RSI.
    4.  **`SectorEventMonitor`**: Tracks industry-specific events (CES, Medical Conferences).

### 5.0.2 Detailed Specs

#### A. `MacroCalendarFetcher`
- **Source:** Investing.com (via crawling) or public APIs.
- **Key Events:** FOMC Meeting, CPI/PPI Release, Quadruple Witching Day.
- **Output:** List of upcoming high-impact events with `d_day` count.
- **Logic:**
    -   If `d_day == 0` for High Impact Event -> **Reduce Position Size / Hold Signal**.

#### B. `PassiveFundTracker`
- **Source:** KRX Information Data System.
- **Logic:**
    -   Identify stocks added/deleted from MSCI/KOSPI200.
    -   **Strategy:** Buy 'Added' stocks 2 weeks prior to effective date.

#### C. `MarketSentimentMeter`
- **Metrics:**
    -   **VIX (Volatilty):** > 30 (Extreme Fear), < 15 (Complacency).
    -   **Market RSI:** Avg RSI of KOSPI200. > 70 (Overbought), < 30 (Oversold).
    -   **Credit Balance Ratio:** Total Credit Balance / Market Cap. High ratio -> Risk of liquidation.
-   **Output:** `market_condition` (Overheated / Neutral / Fear / Panic).

#### D. `SectorEventMonitor`
- **Source:** Manual input list or specialized calendar API.
- **Events:** CES (Jan), JP Morgan Healthcare (Jan), ASCO (Jun).
- **Logic:** Boost `Sector Score` for related stocks 1 month before event.

### 5.0.3 Integration
- **Update `InformationFusionEngine`:**
    -   Add `context_score` to the final formula.
    -   **Context Override:** If `MarketSentimentMeter` indicates "Panic" or `MacroCalendarFetcher` indicates "Major Event Today", force **DEFENSIVE MODE** (reduce weights for aggressive strategies).

## 📐 Phase 5.0: Advanced Market Context & Calendar
**Objective:** Enhance decision quality by incorporating "Time" (Economic Calendar) and "Sentiment" (Market Overheat/Fear) into the AEGIS system, primarily for display on **page 3 of `realtime_dashboard.pdf`** without altering the fundamental file structure.

### 5.0.1 Architecture
- **Module Path:** `src/aegis/context/`
- **Core Components:**
    1.  **`MacroCalendarFetcher`**: Tracks major economic events (FOMC, CPI, Options Expiry).
    2.  **`PassiveFundTracker`**: Monitors index rebalancing events (MSCI, KOSPI200).
    3.  **`MarketSentimentMeter`**: Gauges market fear/greed using VIX, Credit Balance, Market RSI.
    4.  **`SectorEventMonitor`**: Tracks industry-specific events (CES, Medical Conferences).

### 5.0.2 Detailed Specs

#### A. `MacroCalendarFetcher`
- **Source:** Investing.com (via crawling) or public APIs.
- **Key Events:** FOMC Meeting, CPI/PPI Release, Quadruple Witching Day.
- **Output:** List of upcoming high-impact events with `d_day` count.
- **Logic:**
    -   If `d_day == 0` for High Impact Event -> **Reduce Position Size / Hold Signal**.

#### B. `PassiveFundTracker`
- **Source:** KRX Information Data System.
- **Logic:**
    -   Identify stocks added/deleted from MSCI/KOSPI200.
    -   **Strategy:** Buy 'Added' stocks 2 weeks prior to effective date.

#### C. `MarketSentimentMeter`
- **Metrics:**
    -   **VIX (Volatilty):** > 30 (Extreme Fear), < 15 (Complacency).
    -   **Market RSI:** Avg RSI of KOSPI200. > 70 (Overbought), < 30 (Oversold).
    -   **Credit Balance Ratio:** Total Credit Balance / Market Cap. High ratio -> Risk of liquidation.
-   **Output:** `market_condition` (Overheated / Neutral / Fear / Panic).

#### D. `SectorEventMonitor`
- **Source:** Manual input list or specialized calendar API.
- **Events:** CES (Jan), JP Morgan Healthcare (Jan), ASCO (Jun).
- **Logic:** Boost `Sector Score` for related stocks 1 month before event.

### 5.0.3 Integration
- **Update `InformationFusionEngine`:**
    -   Add `context_score` to the final formula.
    -   **Context Override:** If `MarketSentimentMeter` indicates "Panic" or `MacroCalendarFetcher` indicates "Major Event Today", force **DEFENSIVE MODE** (reduce weights for aggressive strategies).
- **PDF 3페이지 반영 (`scripts/generate_realtime_dashboard_terminal_style.py` 수정):**
    -   **`create_aegis_dashboard_page()` 함수 내 추가:**
    -   **상단 "시장 기상도" 섹션:**
        -   가로로 긴 1행 3열 `Table` 형태로 구현.
        -   **좌측:** 🌡️ 시장 심리 (`MarketSentimentMeter` 결과): "공포 (VIX 28.5)"
        -   **중앙:** 📅 주요 경제 일정 (`MacroCalendarFetcher` 결과): "FOMC D-5"
        -   **우측:** 📊 패시브/섹터 이벤트 (`PassiveFundTracker`, `SectorEventMonitor` 결과): "MSCI 편입 (종목명)"
    -   각 셀에 배경색, 폰트 스타일, 이모지 등을 활용하여 시각적 강조.

---

## 📐 Phase 6: Battle-Hardened Optimization (Real-world Reinforcement)
**Objective:** Bridge the gap between theoretical alpha and real-world execution by adding safety valves, realistic cost modeling, and data redundancy.

### 6.1 Architecture
- **Module Path:** `src/aegis/optimization/real_world/`
- **Core Components:**
    1.  **`FinalSignalValidator`**: The "Gatekeeper". Applies Veto/Hard Cutoff rules.
    2.  **`DataIntegrityManager`**: Manages data source failover and latency.
    3.  **`ExecutionSimulator`**: Calculates realistic P&L with slippage and taxes.

### 6.2 Detailed Specs

#### A. `FinalSignalValidator` (Veto System)
- **Role:** Filters out "Trap" signals that passed the scoring engine.
- **Logic (Hard Rules):**
    -   **Financial Risk:** If `Fundamental Score < -2.0` -> **BLOCK BUY**.
    -   **Market Panic:** If `Market Context < -2.0` (Crash) -> **BLOCK NEW BUY**.
    -   **Liquidity Trap:** If `Avg Daily Traded Value (5d) < 10B KRW` -> **BLOCK BUY**.
    -   **Disclosure Risk:** If `Disclosure Score == TRADING_HALT` -> **FORCE SELL**.
-   **Output:** `final_decision` (Pass / Block / Force Sell) + `reason`.

#### B. `DataIntegrityManager`
- **Role:** Ensures data availability and accuracy.
- **Features:**
    -   **Source Failover:** If `pykrx` times out/fails -> Switch to `KIS API` (or secondary source).
    -   **Globex Integration:** Fetch Real-time Nasdaq 100 Futures (`NQ=F`) via `yfinance` every 1 minute (Critical for 08:50-09:00 pre-market analysis).

#### C. `ExecutionSimulator` & Time-Segment
- **Realistic P&L:**
    -   Buy Price = Current + 1 tick (Slippage).
    -   Sell Price = Current - 1 tick (Slippage).
    -   Net Profit = Raw Profit - (0.23% Tax+Fee).
-   **Time-Segmented Logic:**
    -   **09:00 ~ 09:30:** Volatility Breakout weights increased.
    -   **10:00 ~ 14:30:** Trend Following / Supply-based weights increased.
    -   **14:30 ~ 15:20:** Closing bet weights.

### 6.3 Integration
- **Flow:** `InformationFusionEngine` -> `DynamicWeightOptimizer` -> **`FinalSignalValidator`** -> Execution.

---

## 📐 Phase 7: Advanced Verification & Self-Evolution
**Objective:** Rigorously validate every signal generated by AEGIS, track its performance in real-time, and use this data to self-correct and improve future accuracy.

### 7.1 Architecture
- **Module Path:** `src/aegis/verification/`
- **Core Components:**
    1.  **`SignalTraceManager`**: The "Black Box" recorder. Tracks post-signal price movements in minute detail.
    2.  **`VerificationDashboard`**: Transforms raw data into actionable insights (Win-Rate Heatmaps, Equity Curves).
    3.  **`AutoCorrectionLoop`**: The feedback mechanism that adjusts weights based on verified performance.

### 7.2 Detailed Specs

#### A. `SignalTraceManager`
- **Function:** Monitors active signals until exit conditions are met.
- **Metrics to Track:**
    -   **Time-based Returns:** 1m, 5m, 10m, 30m, 60m, End-of-Day.
    -   **MFE (Max Favorable Excursion):** Highest profit reached during the trade. (Did we miss a selling chance?)
    -   **MAE (Max Adverse Excursion):** Lowest drawdown during the trade. (Was the stop-loss too tight?)
-   **Failure Tagging:** If a trade fails, tag the likely cause (e.g., "Market Crash", "Sector Rotation", "Fake Breakout").

#### B. `VerificationDashboard` (PDF Page 4 Overhaul)
- **Visualizations:**
    -   **Win-Rate Heatmap:** Grid showing win rates by **Time of Day** (rows) and **Signal Score** (cols).
    -   **Equity Curve:** A line chart showing cumulative profit if all AEGIS signals were traded.
    -   **Worst Case Review:** Top 3 losses with AI commentary on *why* it failed.

#### C. `AutoCorrectionLoop`
- **Logic:**
    -   Analyze `aegis_signal_history` weekly.
    -   **Rule Generation:**
        -   If `Win Rate < 40%` for "9 AM trades" on "Tech Sector" -> **Create Rule: "Reduce Tech weights at 9 AM"**.
        -   Update `DynamicWeightOptimizer` configuration automatically.

### 7.3 Action Plan
1.  Expand `aegis_signal_history` table schema (MFE, MAE, 5m_return, etc.).
2.  Implement `SignalTraceManager` to run as a background daemon.
3.  Redesign PDF Page 4 to display the Heatmap and Equity Curve.
4.  Implement the `AutoCorrectionLoop` to close the learning cycle.

## 📐 Phase 7.5: System Optimization & Lightweighting
**Objective:** Ensure system stability and responsiveness on a personal laptop environment by reducing resource consumption (CPU, RAM) and API costs.

### 7.5.1 Strategy
- **Module Path:** `src/aegis/optimization/system/`
- **Focus Areas:** API Efficiency, Scraper Throttling, DB Tuning.

### 7.5.2 Detailed Specs

#### A. Gemini API Optimization (`SmartNewsFilter`)
- **Logic:**
    -   Do NOT send every news item to Gemini.
    -   **1st Pass (Regex):** Check for high-impact keywords ("Supply Contract", "Capital Increase", "Earnings Shock").
    -   **2nd Pass (API):** Only call Gemini if keywords match OR news source is "Major Tier".
    -   **Caching:** Strict deduping before API calls.

#### B. Resource Management (`ResourceController`)
- **Browser Automation:**
    -   Limit `Playwright` instances to max 1 concurrent context.
    -   Replace browser scraping with direct HTTP requests (`aiohttp`) where possible.
-   **PDF Generation:**
    -   Optimize chart rendering (lower DPI for thumbnails).
    -   Skip chart regeneration if price change < 0.1%.

#### C. Database Maintenance (`DBOptimizer`)
- **Indexing:** Ensure `(stock_code, timestamp)` composite indexes exist on all high-volume tables (`min_ticks`, `stock_news`).
- **Retention:**
    -   `min_ticks`: Keep hot data (1 month), archive/delete older data.
    -   `logs`: Rotate and compress logs weekly.

### 7.5.3 Action Plan
1.  Implement `SmartNewsFilter` in `NewsSentimentAnalyzer`.
2.  Review and refactor fetchers to minimize `Playwright` usage.
3.  Apply DB indexes and create a cleanup script.

## 📐 Phase 8: Daily Performance Analysis & Reporting
**Objective:** Automate the "End-of-Day Review". Generate a comprehensive PDF report tracking realized P&L, asset growth, and strategy performance.

### 8.1 Architecture
- **Module Path:** `src/reporting/performance/`
- **Script:** `scripts/generate_daily_performance_report.py`
- **Output:** `reports/performance/YYYY-MM-DD_Performance_Report.pdf`

### 8.2 Detailed Specs

#### A. Database Schema (`daily_summary`)
- **Columns:**
    -   `date` (PK)
    -   `total_asset`: Total account value (Cash + Stock Eval).
    -   `realized_pnl`: Daily realized profit/loss.
    -   `unrealized_pnl`: Daily unrealized profit/loss.
    -   `trade_count`: Number of trades executed.
    -   `win_rate`: Win rate of closed trades today.
    -   `best_trade`: (JSON) {symbol, pnl}
    -   `worst_trade`: (JSON) {symbol, pnl}

#### B. Report Structure (PDF)
-   **Page 1: Daily Dashboard**
    -   **Key Metrics:** Big numbers for Daily P&L, Win Rate, Total Asset.
    -   **Charts:**
        -   Intraday P&L Curve (if data available).
        -   Asset Growth Chart (Last 30 days).
    -   **Trade Log:** List of all trades executed today with P&L.
-   **Page 2: Portfolio & Strategy Analysis**
    -   **Portfolio Pie Chart:** Sector/Stock allocation.
    -   **AEGIS Review:** Table comparing "Signals Generated" vs "Actual Price Move".
-   **Page 3: Weekly/Monthly Summary**
    -   Calendar view of daily P&L (Green/Red boxes).

### 8.3 Action Plan
1.  Create `daily_summary` table (`sql/create_daily_summary.sql`).
2.  Implement `DailyPerformanceAnalyzer` to aggregate data from `trade_history` and `stock_assets`.
3.  Develop `generate_daily_performance_report.py` using ReportLab and Matplotlib.
4.  Schedule cron job for 16:00 KST.
**Objective:** Full automation with a real-time web interface.

### 5.1 Architecture
- **Backend:** FastAPI (`src/web/api/`)
- **Frontend:** React (`web/dashboard/`)
- **State:** Redis (for sharing state between Python processes and Web UI).

### 5.2 Detailed Specs

#### A. `OrderExecutor` (Backend)
- **Logic:** Async wrapper around KIS/OpenAPI.
- **Features:** Retry logic, Order status polling, Slack/Telegram notifications.

#### C. PDF Generation Enhancement: Direct Chart Embedding
- **Objective:** Generate PDFs with embedded charts directly from memory, eliminating intermediate chart image files.
- **Scope:** Applies to all PDF generation scripts (e.g., `scripts/generate_realtime_dashboard_terminal_style.py`, `scripts/gemini/generate_pdf_report.py`).
- **Design:**
    - **Chart Generation:** Modify plotting code (e.g., Matplotlib) to render charts into an in-memory buffer (`io.BytesIO`) as a PNG or SVG format, instead of saving to disk.
    - **PDF Integration:** PDF generation library should directly read image data from the `io.BytesIO` buffer and embed it into the PDF document.
- **Benefits:** Reduces disk I/O, cleans up `charts/` directory, improves atomicity of PDF generation.

---

## ✅ Action Plan for Claude
Please implement these phases sequentially.
1.  **Start with Phase 1 (Backtesting).** Do not proceed to Phase 2 until Phase 1 is verified with at least one basic strategy.
2.  Use the existing database (`joungwon.stocks`) and `asyncpg` where necessary, but Phase 1 can rely mostly on Pandas.
