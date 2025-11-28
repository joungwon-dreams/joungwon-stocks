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

---

## 📐 Phase 4: AI Prediction Model
**Objective:** Use Deep Learning to predict short-term price direction and volatility.

### 4.1 Architecture
- **Module Path:** `src/ai/prediction/`
- **Tech Stack:** PyTorch.

### 4.2 Detailed Specs

#### A. `DataPreprocessor`
- **Logic:** Create sliding windows (Sequence Length = 60 mins).
- **Features:** OHLCV + Technical Indicators (RSI, MACD) + **Gemini Sentiment Score** (0.0 to 1.0).

#### B. `LSTMPredictor` (Model)
- **Architecture:**
    - Input Layer: (Batch, Seq_Len, Features)
    - LSTM Layers: 2 layers, 64 hidden units, Dropout 0.2.
    - Output Layer: 1 unit (Sigmoid) -> Probability of "Upward Move > 0.5% in next 10 mins".

#### C. `InferenceEngine`
- **Logic:** Loads trained model. Runs inference on live 1-min data. Returns `probability`.
- **Integration:** Acts as a filter for Phase 3. If `probability < 0.6`, ignore Buy signals.

---

## 📐 Phase 5: Automation & Dashboard
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
