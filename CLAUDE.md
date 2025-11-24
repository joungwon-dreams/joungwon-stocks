# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**joungwon.stocks** is an enterprise-grade AI-powered automated stock trading system for the Korean stock market. The system integrates:

- **Real-time data collection** from 41+ Korean investment analysis websites
- **Reinforcement learning** (A2C) for trading strategies
- **Gemini AI** for news sentiment analysis
- **Korea Investment Securities API** for automated trading

### Technology Stack

- **Language**: Python 3.9+
- **Database**: PostgreSQL 14.20
- **Async**: asyncio, aiohttp, asyncpg
- **ML/AI**: TensorFlow 2.x / PyTorch, Google Gemini Pro
- **Data Collection**: pykrx, FinanceDataReader, Scrapy, Playwright

### Project Status

Phase 1 (Data Collection Enhancement) - In Progress

## Development Commands

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
createdb stock_investment_db
psql -U wonny -d stock_investment_db -f sql/01_create_tables.sql
```

### Data Collection

```bash
# Initialize stock list (KRX all stocks)
python scripts/initialize_stocks.py

# Collect daily OHLCV data
python scripts/collect_daily_ohlcv.py

# Run orchestrator (all tiers)
python src/core/orchestrator.py
```

### Real-time Trading

```bash
# Start WebSocket real-time feed
python src/fetchers/tier2_official_apis/kis_websocket.py

# Run news analysis
python scripts/run_news_analysis.py
```

### Testing

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Generate coverage report
pytest --cov=src --cov-report=html
```

## Architecture

### 4-Tier Data Collection System

```
Tier 1 (Official Libraries):
  - pykrx (KRX data)
  - dart-fss (DART filings)
  - FinanceDataReader (stock listings)

Tier 2 (Official APIs):
  - Korea Investment Securities API (WebSocket + REST)
  - Naver Finance API

Tier 3 (Web Scraping):
  - Scrapy spiders (30+ sites)
  - News crawlers

Tier 4 (Browser Automation):
  - Playwright (JavaScript-heavy sites)
  - DrissionPage (bot detection bypass)
```

### Data Flow

```
Data Sources (41 sites)
  ↓
Fetchers (Tier 1-4)
  ↓
Pipelines (Validation, Transformation, Storage)
  ↓
PostgreSQL (13 tables)
  ↓
AI Analysis (RL, Sentiment)
  ↓
Automated Trading
```

## Database Schema

### Primary Tables

1. **Master Group**
   - `stocks`: Stock master data
   - `stock_assets`: Holdings and trading settings

2. **Price Data Group**
   - `daily_ohlcv`: Daily OHLCV (1 year)
   - `min_ticks`: Real-time ticks (1 minute)
   - `stock_prices_10min`: 10-minute technical indicators
   - `stock_supply_demand`: Institutional trading data

3. **Trading Group**
   - `trade_history`: All buy/sell records + AI reasoning
   - `stock_opinions`: Investment opinions and price targets

4. **AI Recommendation Group**
   - `data_sources`: Data source reliability tracking
   - `recommendation_history`: AI/expert recommendations
   - `verification_results`: Accuracy verification

5. **Scoring Group**
   - `stock_score_weights`: Per-stock weights (chart/supply/value)
   - `stock_score_history`: Daily scores and signals

### Key Features

- **Real-time triggers**: `min_ticks` INSERT → `stock_assets.price` auto-update
- **Composite indexes**: Optimized for time-series queries
- **AI reasoning storage**: `gemini_reasoning` field in `trade_history`

## API Routes

### Korea Investment Securities API

**Authentication**:
```python
from pykis import PyKis
kis = PyKis()
```

**WebSocket** (Real-time):
```python
stock = kis.stock("005930")

@stock.on_price
def on_price(price):
    # Handle real-time price updates
    pass
```

**REST API**:
```python
# Buy/Sell
stock.buy(price=194700, qty=1)
stock.sell(price=195000)

# Balance
balance = kis.balance()
```

### Gemini API

```python
import google.generativeai as genai

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content(prompt)
```

## Important Patterns

### Fetcher Pattern

All fetchers inherit from `BaseFetcher`:

```python
from src.core.base_fetcher import BaseFetcher

class MyFetcher(BaseFetcher):
    async def fetch(self):
        data = await self.fetch_data()
        validated_data = self.validate(data)
        await self.save_to_db(validated_data)
```

### Data Validation (Pydantic)

```python
from pydantic import BaseModel

class OHLCVSchema(BaseModel):
    code: str
    date: str
    open: int
    high: int
    low: int
    close: int
    volume: int
```

### Async Database Operations

```python
import asyncpg

async with asyncpg.create_pool(**db_config) as pool:
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO ...")
```

### Reinforcement Learning (A2C)

```python
from src.learners.a2c_agent import A2CAgent

agent = A2CAgent(state_dim=45, action_dim=3)
agent.train(env, episodes=1000)
```

## Environment Variables

Create `.env` file with:

```bash
# Database
DB_NAME=stock_investment_db
DB_USER=wonny
DB_HOST=localhost
DB_PORT=5432

# Korea Investment Securities API
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret
KIS_ACCOUNT_NO=your_account_number

# Gemini API
GEMINI_API_KEY=your_gemini_api_key

# Monitoring
SLACK_WEBHOOK_URL=your_slack_webhook
```

## Key Documentation

- [Opensource Integration Analysis](./docs/01-opensource-integration-analysis.md) - Detailed analysis of 4 opensource projects
- [README.md](./README.md) - Project overview and quick start

## Open Source References

1. **quantylab/rltrader**: Reinforcement learning architecture
   - https://github.com/quantylab/rltrader

2. **Korea Investment Securities API**: Real-time trading
   - https://github.com/koreainvestment/open-trading-api
   - https://github.com/Soju06/python-kis

3. **FinanceDataReader**: Data collection
   - https://github.com/FinanceData/FinanceDataReader

4. **FinGPT**: AI financial analysis
   - https://github.com/AI4Finance-Foundation/FinGPT

## Coding Standards

- **Python Style**: PEP 8
- **Docstrings**: Google style
- **Type Hints**: Required for all functions
- **Async/Await**: Use for all I/O operations
- **Error Handling**: Try-except with logging
- **Testing**: Pytest with 80%+ coverage

## Development Workflow

1. Read documentation in `docs/` folder
2. Create feature branch from `main`
3. Write tests first (TDD)
4. Implement feature
5. Run tests and linting
6. Create pull request

---

**Last Updated**: 2025-11-24 11:29:49
**Project Start**: 2025-11-24
**Status**: Phase 1 - Data Collection Enhancement
