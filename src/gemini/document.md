# Gemini AI Investment Report System

## 1. System Overview
This system automatically generates comprehensive investment analysis reports for holding stocks using Google's Gemini AI. It combines internal database records with real-time market data and news to provide actionable insights.

## 2. Folder Structure
```
src/gemini/
├── client.py          # Gemini API Client (Analysis)
├── generator.py       # PDF Report Generator (Charts, Layout)
└── document.md        # System Documentation

scripts/gemini/
├── run_report.py             # Main Orchestration Script
├── generate_single_report.py # Single Stock Report Generator
├── test_fetchers.py          # Fetcher Verification Script
├── daum/                     # Daum Finance Fetchers
│   ├── base.py               # Base Class
│   ├── price.py              # Price & History (OHLCV)
│   ├── supply.py             # Investor Trends (Foreign/Institutional)
│   └── financials.py         # Financial Statements & Peers
└── naver/                    # Naver Finance Fetchers
    ├── consensus.py          # Market Consensus (Target Price)
    └── news.py               # Real-time News (Mobile API)
```

## 3. Component Details

### Core Modules (`src/gemini/`)

#### `client.py` (GeminiClient)
-   **Purpose**: Handles all interactions with Google Gemini API (`gemini-pro`).
-   **Key Features**:
    -   Constructs prompts using real-time market data and news.
    -   Generates structured analysis:
        1.  **Comprehensive Analysis**: Fundamentals, Supply/Demand, Momentum.
        2.  **Market Sentiment**: Positive/Neutral/Negative.
        3.  **Investment Recommendation**: Buy/Sell/Hold with rationale.
-   **Configuration**: Requires `GEMINI_API_KEY` in `.env`.

#### `generator.py` (ReportGenerator)
-   **Purpose**: Creates professional PDF reports.
-   **Key Features**:
    -   **Library**: Uses `reportlab` for PDF creation and `matplotlib` for charts.
    -   **Content**:
        -   AI Analysis Summary & Sentiment Table.
        -   Holding Status (Profit/Loss, Quantity) & Visual Charts (Bar/Pie).
        -   Real-time Market Data Table (Price, Volume, Consensus).
    -   **Styling**: Supports Korean fonts (NanumGothic) and clean, modern formatting.

### Scripts (`scripts/gemini/`)

#### `run_report.py`
-   **Purpose**: Main entry point for generating reports.
-   **Workflow**:
    1.  **Fetch Holdings**: Retrieves active stocks from PostgreSQL (`stock_assets`).
    2.  **Collect Data**:
        -   Fetches real-time price/financials from **Daum**.
        -   Fetches consensus/peer data from **Naver**.
        -   Fetches latest news from **Naver News**.
    3.  **AI Analysis**: Sends aggregated data to `GeminiClient`.
    4.  **Generate PDF**: Passes all data and AI results to `ReportGenerator`.

#### `daum_fetcher.py`
-   **Source**: Daum Finance API (Unofficial).
-   **Data**: Real-time quotes, Financial ratios (PER, PBR, ROE), Investor trends (Foreign/Institutional net buy).

#### `naver_fetcher.py`
-   **Source**: Naver Finance (Browser Automation via Playwright).
-   **Data**: Consensus (Target Price, Opinion), Peer Comparison (Competitors).

#### `news_fetcher.py`
-   **Source**: Naver Finance News (Browser Automation via Playwright).
-   **Data**: Real-time news headlines and content for the specific stock.

## 4. Usage

### Prerequisites
-   Python 3.9+
-   `GEMINI_API_KEY` set in `.env`
-   Playwright browsers installed: `playwright install chromium`

### Generate Reports
Run the main script to generate reports for all holding stocks:
```bash
python scripts/gemini/run_report.py
```

### Check News Data
Verify if news data exists in the database (optional utility):
```bash
python scripts/gemini/check_news_count.py
```

## 5. Output
Generated PDF reports are saved in:
`/Users/wonny/Dev/joungwon.stocks.report/ai_reports/`
Format: `{StockName}_{StockCode}_AI_Report.pdf`
