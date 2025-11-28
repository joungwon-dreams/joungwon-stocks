# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**joungwon.stocks** is an enterprise-grade AI-powered automated stock trading system for the Korean stock market. The system collects data from 41+ Korean investment analysis websites through a 4-tier architecture, analyzes them using Gemini AI, and executes automated trades via Korea Investment Securities API.

**Status**: Phase 1 (Data Collection Enhancement) - In Progress

## Development Commands

```bash
# Installation
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Database setup
createdb stock_investment_db
psql -U wonny -d stock_investment_db -f sql/01_create_tables.sql

# Run orchestrator (collects from all 41 sites)
python src/core/orchestrator.py

# Test specific tier
python scripts/test_tier3_scrapers.py      # Web scraping
python scripts/test_tier4_fnguide.py       # Browser automation

# Test specific fetcher
python scripts/test_fetchers.py

# Run orchestrator tests
python scripts/test_orchestrator.py

# Initialize stock list from KRX
python scripts/initialize_stocks.py

# Generate reports
python scripts/generate_comprehensive_holdings_report.py
python scripts/generate_holding_research_pdf.py

# WebSocket real-time feed
python src/fetchers/tier2_official_apis/kis_websocket.py
```

## Architecture

### 4-Tier Data Collection System

```
                    ORCHESTRATOR
                (src/core/orchestrator.py)
        Manages rate limiting, concurrency (semaphore),
           retry logic, and tier execution order
                        │
    ┌───────────────────┼───────────────────┐
    │                   │                   │
    ▼                   ▼                   ▼
┌─────────┐      ┌─────────────┐      ┌─────────────┐
│ Tier 1  │      │   Tier 2    │      │ Tier 3 + 4  │
│Official │      │Official APIs│      │Web Scraping │
│Libraries│      │             │      │+ Playwright │
└────┬────┘      └──────┬──────┘      └──────┬──────┘
     │                  │                    │
     └──────────────────┼────────────────────┘
                        ▼
            ┌─────────────────────┐
            │   PostgreSQL DB     │
            │   (13 tables)       │
            └──────────┬──────────┘
                       ▼
            ┌─────────────────────┐
            │   Gemini AI         │
            │   Analysis          │
            └──────────┬──────────┘
                       ▼
            ┌─────────────────────┐
            │   Auto Trading      │
            │   (KIS API)         │
            └─────────────────────┘
```

### Tier Details

| Tier | Type | Sources | Technology |
|------|------|---------|------------|
| 1 | Official Libraries | pykrx, dart-fss, FinanceDataReader, OpenDART | Python packages |
| 2 | Official APIs | Korea Investment, Naver Finance, Daum Finance, KRX Data, KOFIA | REST + WebSocket |
| 3 | Web Scraping | 24+ securities/news sites | aiohttp + BeautifulSoup |
| 4 | Browser Automation | FnGuide, Naver News (JS-heavy) | Playwright with anti-detection |

### Key Modules

```
src/
├── core/
│   ├── orchestrator.py    # Main coordinator (rate limiting, concurrency)
│   ├── base_fetcher.py    # Abstract base for all fetchers
│   ├── rate_limiter.py    # Token bucket algorithm per site
│   └── retry.py           # Exponential backoff decorators
├── config/
│   ├── database.py        # AsyncPG connection pool (5-20 connections)
│   └── settings.py        # Pydantic settings from .env
├── fetchers/
│   ├── tier1_official_libs/   # 4 fetchers
│   ├── tier2_official_apis/   # 5 fetchers
│   ├── tier3_web_scraping/    # 24+ scrapers
│   └── tier4_browser_automation/  # 4 Playwright fetchers
└── gemini/
    └── client.py          # Google Gemini API wrapper
```

## Core Patterns

### BaseFetcher Pattern

All data collectors inherit from `BaseFetcher` (`src/core/base_fetcher.py`):

```python
from src.core.base_fetcher import BaseFetcher

class MyFetcher(BaseFetcher):
    async def fetch(self, ticker: str) -> Dict[str, Any]:
        # Implement data fetching logic
        pass

    async def validate_structure(self) -> bool:
        # Check if site structure matches expectations
        pass
```

The `execute()` method wraps `fetch()` with logging, health updates, and error handling.

### Rate Limiting

Token bucket algorithm in `src/core/rate_limiter.py`:

```python
# Per-site rate limiting
limiters = MultiRateLimiter()
limiters.set_limit(site_id=1, calls_per_minute=20)

async with limiters.get(site_id):
    await fetcher.execute(ticker)
```

### Retry Decorators

Three presets in `src/core/retry.py`:

```python
from src.core.retry import quick_retry, standard_retry, persistent_retry

@quick_retry        # 2 attempts, 0.5s delay
@standard_retry     # 3 attempts, 1.0s delay, 2x backoff
@persistent_retry   # 5 attempts, 2.0s delay, 2x backoff
async def fetch_data():
    pass
```

### Database Operations

Global async database instance in `src/config/database.py`:

```python
from src.config.database import db

await db.connect()
rows = await db.fetch("SELECT * FROM stocks WHERE market = $1", "KOSPI")
await db.execute("INSERT INTO daily_ohlcv ...")
await db.disconnect()
```

## Database Schema (13 Tables)

**Master**: `stocks`, `stock_assets` (with auto-calculated P/L columns)

**Price Data**: `daily_ohlcv`, `min_ticks`, `stock_prices_10min`, `stock_supply_demand`

**Trading**: `trade_history` (includes `gemini_reasoning`), `stock_opinions`

**AI Recommendations**: `data_sources` (reliability tracking), `recommendation_history`, `verification_results`

**Scoring**: `stock_score_weights`, `stock_score_history`

Key features:
- `min_ticks` INSERT triggers auto-update of `stock_assets.current_price`
- Generated columns for P/L calculations in `stock_assets`
- Composite indexes on (stock_code, date) for time-series queries

## Environment Variables

Create `.env` file:

```bash
# Database
DB_NAME=stock_investment_db
DB_USER=wonny
DB_HOST=localhost
DB_PORT=5432

# Required APIs
DART_API_KEY=your_dart_api_key

# Trading (optional)
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret
KIS_ACCOUNT_NO=your_account_number
KIS_CANO=your_cano
KIS_ACNT_PRDT_CD=your_product_code

# AI Analysis
GEMINI_API_KEY=your_gemini_api_key

# Monitoring (optional)
SLACK_WEBHOOK_URL=your_slack_webhook
```

## Key Files Reference

| File | Purpose |
|------|---------|
| `src/core/orchestrator.py` | Main data collection coordinator |
| `src/core/base_fetcher.py` | Abstract base class for all fetchers |
| `src/config/database.py` | AsyncPG connection manager |
| `sql/01_create_tables.sql` | Complete database schema (13 tables) |
| `src/gemini/client.py` | Google Gemini API wrapper |
| `scripts/generate_comprehensive_holdings_report.py` | Main report generator |

---

## PDF 문서 구조 변경 금지 (CRITICAL)

**⚠️ 절대 변경 금지**: 아래 PDF 파일들의 구조는 잠겨 있습니다.

### 대상 파일
1. **realtime_dashboard.pdf** - 실시간 대시보드
   - 경로: `reports/holding_stock/realtime_dashboard.pdf`
   - 생성: `scripts/generate_realtime_dashboard_terminal_style.py`
   - 호출: `cron/1min.py`
   - 구조: 페이지 1,2 (포트폴리오 요약/구성) + 페이지 3+ (종목별 틱 데이터)

2. **종목명.pdf** - 개별 종목 리포트
   - 경로: `reports/holding_stock/종목명.pdf`
   - 생성: `scripts/gemini/generate_pdf_report.py`
   - 호출: `cron/10min.py`

### 변경 금지 항목
- 섹션 순서 및 제목 (이모지 포함)
- 테이블 컬럼 순서/너비
- 색상 코드
- 폰트 크기
- 페이지 브레이크 위치
- 차트 크기/비율

### 변경이 필요한 경우
1. **반드시** `docs/PDF_STRUCTURE_SPECIFICATION.md` 확인
2. 사용자 승인 필수
3. 명세서 버전 업데이트 필수

### 명세서 위치
- `docs/PDF_STRUCTURE_SPECIFICATION.md` - 전체 PDF 구조 명세

---

## Auto Git Commit (MANDATORY)

**작업 완료 후 자동 커밋**: 모든 코드 변경 작업이 완료되면 사용자 지시 없이 자동으로 git commit을 수행합니다.

```yaml
TRIGGER: 작업 완료 시점 (코드 수정, 파일 생성/삭제, 설정 변경 등)
ACTION: git add -A && git commit -m "커밋 메시지"
FORMAT: |
  type: 간단한 제목

  - 변경 내용 1
  - 변경 내용 2

  🤖 Generated with [Claude Code](https://claude.com/claude-code)
  Co-Authored-By: Claude <noreply@anthropic.com>
```

**커밋 타입**:
- `feat`: 새 기능
- `fix`: 버그 수정
- `refactor`: 리팩토링
- `docs`: 문서 변경
- `chore`: 설정/유지보수

---

**Last Updated**: 2025-11-28
**Project Start**: 2025-11-24
