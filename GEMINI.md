# GEMINI.md

This file provides comprehensive context for Gemini when working on the `joungwon.stocks` project.

## 1. Project Overview

**joungwon.stocks** is an AI-powered automated stock trading system specifically designed for the Korean stock market. It leverages a tiered data collection strategy, reinforcement learning (A2C), and LLM-based sentiment analysis (Gemini Pro) to make trading decisions.

- **Goal:** Automate data collection, analysis, and trading execution.
- **Status:** Phase 1 (Data Collection Enhancement) is active.
- **Key Integrations:** Korea Investment Securities (KIS) API, Google Gemini API, KRX/DART systems.

## 2. Architecture

The system follows a modular architecture with a strong emphasis on data integrity and asynchronous processing.

### Data Collection (4-Tier System)
*   **Tier 1 (Official Libraries):** `pykrx`, `dart-fss`, `FinanceDataReader`. High reliability, strictly structured data.
*   **Tier 2 (Official APIs):** `python-kis` (KIS API), Naver Finance API. Real-time prices via WebSocket.
*   **Tier 3 (Web Scraping):** `Scrapy`, `BeautifulSoup`. News, reports, and unstructured data.
*   **Tier 4 (Browser Automation):** `Playwright`, `DrissionPage`. Handling complex JS-heavy sites or anti-bot measures.

### Core Components
*   **Orchestrator (`src/core/orchestrator.py`):** Manages the concurrent execution of fetchers.
*   **Pipelines:** Data flows through Validation (Pydantic) -> Transformation -> Storage (PostgreSQL).
*   **Database:** PostgreSQL with `asyncpg`. Schema includes `stocks`, `daily_ohlcv`, `trade_history`, `min_ticks`.
*   **AI Engine:**
    *   **Sentiment:** Gemini Pro analyzes news/reports.
    *   **Strategy:** RL A2C agent (planned integration with `quantylab/rltrader` logic).

## 3. Directory Structure

```text
joungwon.stocks/
├── docs/                    # Documentation & Requirements
│   └── requirements.txt     # Python dependencies
├── config/                  # Configuration files (DB, API keys)
├── src/
│   ├── core/                # Core logic (Orchestrator, BaseFetcher)
│   ├── fetchers/            # Data collectors (Tier 1-4 organized)
│   ├── ai/                  # AI/ML modules (Sentiment, RL)
│   ├── pipelines/           # Data processing pipelines
│   └── config/              # Pydantic settings
├── scripts/                 # Utility and entry-point scripts
├── sql/                     # SQL schemas and migration scripts
├── tests/                   # Pytest suite
└── venv/                    # Virtual environment
```

## 4. Development & Usage

### Setup & Installation
Dependencies are managed in `docs/requirements.txt`.
```bash
source venv/bin/activate
pip install -r docs/requirements.txt
```

### Database Initialization
```bash
psql -U wonny -d stock_investment_db -f sql/01_create_tables.sql
```

### Running the System
*   **Initial Collection:** `python scripts/run_initial_collection.py`
*   **Orchestrator:** `python src/core/orchestrator.py`
*   **Real-time Feed:** `python src/fetchers/tier2_official_apis/kis_websocket.py`

### Testing
Use `pytest` for unit and integration tests.
```bash
pytest tests/unit/
pytest tests/integration/
```

## 5. Conventions & Standards

*   **Language:** Python 3.9+
*   **Style:** PEP 8.
*   **Async:** Extensive use of `asyncio` and `asyncpg`. DB operations should always be non-blocking.
*   **Typing:** Type hints are required for all function signatures.
*   **Configuration:** Use `src/config/settings.py` (Pydantic `BaseSettings`) for env vars. **NEVER hardcode credentials.**
*   **Error Handling:** Use `try-except` blocks with `structlog` logging. Failures in one fetcher should not crash the orchestrator.
*   **Fetcher Pattern:** All fetchers must inherit from `src.core.base_fetcher.BaseFetcher` and implement the `fetch()` method.

## 6. Key Files

*   `src/config/settings.py`: Central configuration.
*   `src/core/orchestrator.py`: Main entry point for batch data collection.
*   `src/core/base_fetcher.py`: Base class for all data collectors.
*   `CLAUDE.md`: Existing context file with detailed roadmap and examples.
*   `docs/01-opensource-integration-analysis.md`: Detailed integration plan for external libraries.

## 7. Common Tasks

*   **Adding a new data source:** Create a new fetcher in the appropriate Tier directory under `src/fetchers/`, inheriting from `BaseFetcher`. Register it in the `Orchestrator`.
*   **Modifying DB Schema:** Add a new SQL script in `sql/` and update Pydantic models in `src/models/` (if applicable).
*   **Debugging:** Check logs in `logs/` (if configured) or standard output.
