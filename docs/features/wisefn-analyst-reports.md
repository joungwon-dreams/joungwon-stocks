# WISEfn Analyst Reports Integration

**Created**: 2025-11-25 20:37:12
**Updated**: 2025-11-25 20:37:12
**Status**: Active
**Author**: wonny

## Overview

Database-first architecture for collecting and storing analyst reports from WISEfn (Daum Finance). This feature eliminates redundant scraping by fetching data once and storing it in PostgreSQL for efficient reuse across PDF generation and other analysis tools.

## Architecture

### Database-First Design

```
┌─────────────────┐
│  WISEfn Source  │  (https://wisefn.finance.daum.net)
└────────┬────────┘
         │
         │ Playwright Browser Automation
         │ (JavaScript rendering required)
         ↓
┌────────────────────────┐
│  WISEfnReportsScraper  │  (scripts/gemini/wisefn/reports_scraper.py)
└───────┬────────────────┘
        │
        │ fetch_and_save()
        ↓
┌────────────────────────────────┐
│  wisefn_analyst_reports table  │  (PostgreSQL)
│  - stock_code, report_date     │
│  - brokerage, target_price     │
│  - opinion, title              │
└───────┬────────────────────────┘
        │
        │ get_from_db() - Fast retrieval
        ↓
┌─────────────────────┐
│  PDF Generation     │  (generate_pdf_report.py)
│  Analysis Tools     │
│  Research Reports   │
└─────────────────────┘
```

## Database Schema

### wisefn_analyst_reports Table

```sql
CREATE TABLE wisefn_analyst_reports (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    report_date DATE NOT NULL,
    brokerage VARCHAR(50) NOT NULL,
    target_price INTEGER NOT NULL,
    price_change VARCHAR(20),
    opinion VARCHAR(20) NOT NULL,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, report_date, brokerage)
);
```

**Indexes**:
- `idx_wisefn_stock_code`: Fast stock lookups
- `idx_wisefn_report_date`: Time-based queries
- `idx_wisefn_stock_date`: Combined stock+date queries

**Key Features**:
- Unique constraint prevents duplicate reports
- ON CONFLICT DO UPDATE enables upsert behavior
- Timestamp tracking for data freshness

## API

### WISEfnReportsScraper

**Location**: `scripts/gemini/wisefn/reports_scraper.py`

#### Methods

##### 1. fetch_reports(stock_code: str) → List[Dict]

Scrapes analyst reports from WISEfn using Playwright.

```python
from scripts.gemini.wisefn.reports_scraper import WISEfnReportsScraper

scraper = WISEfnReportsScraper()
reports = await scraper.fetch_reports("015760")
```

**Returns**:
```python
[
    {
        'date': '25.11.25',
        'target_price': 63000,
        'price_change': '▲ 15,000',
        'opinion': '매수',
        'brokerage': '유진',
        'title': '지역별차등요금제가 불러올 나비효과'
    },
    ...
]
```

##### 2. save_to_db(stock_code: str, reports: List[Dict]) → int

Saves scraped reports to database with upsert logic.

```python
saved_count = await scraper.save_to_db("015760", reports)
print(f"Saved {saved_count} reports")
```

##### 3. fetch_and_save(stock_code: str) → List[Dict]

Convenience method: scrapes and saves in one call.

```python
reports = await scraper.fetch_and_save("015760")
```

##### 4. get_from_db(stock_code: str, limit: int = 10) → List[Dict]

**Static method** - Retrieves reports from database (no scraping).

```python
# Fast database retrieval
db_reports = await WISEfnReportsScraper.get_from_db("015760", limit=10)
```

**Returns**: Same format as `fetch_reports()` but from database.

## Usage

### Initial Data Collection

Run once to populate database for all stock holdings:

```bash
source venv/bin/activate
python scripts/collect_wisefn_reports.py
```

This script:
1. Queries `stock_assets` table for stocks with `quantity > 0`
2. Scrapes WISEfn reports for each stock
3. Saves to database with 3-second delay between requests
4. Provides summary statistics

### PDF Generation (Database-Only)

The PDF generator now reads from database instead of scraping:

```python
# scripts/gemini/generate_pdf_report.py (lines 112-133)
from scripts.gemini.wisefn.reports_scraper import WISEfnReportsScraper

# Retrieves from database - no web scraping!
wisefn_reports = await WISEfnReportsScraper.get_from_db(self.stock_code, limit=10)

# Convert format for PDF generation
self.analyst_targets = []
for report in wisefn_reports:
    self.analyst_targets.append({
        'brokerage': report['brokerage'],
        'target_price': report['target_price'],
        'opinion': report['opinion'],
        'report_date': convert_date(report['date']),
        'title': report['title']
    })
```

### Testing Database Integration

```bash
# Test database read + PDF generation
python scripts/test_wisefn_db_read.py
```

Expected output:
```
✅ Retrieved 3 reports from database
Reports from database:
1. 25.11.25 | 유진 | 63,000원
   매수 | ▲ 15,000 | 지역별차등요금제가 불러올 나비효과
...
✅ PDF generated: /Users/wonny/Dev/joungwon.stocks/reports/한국전력_11252035.pdf
```

## Data Format Conversions

### Date Formats

- **WISEfn Display**: `25.11.25` (YY.MM.DD)
- **Database Storage**: `2025-11-25` (DATE type)
- **PDF Internal**: `20251125` (YYYYMMDD string)

Conversion handled automatically by scraper methods.

### Price Change Format

- **Database**: Stored as-is (`▲ 15,000`, `▼ 5,000`, `0`, `-`)
- **PDF Display**: Formatted with comma separators

## Files Modified

### New Files

1. `sql/02_create_wisefn_reports.sql` - Database schema
2. `scripts/gemini/wisefn/reports_scraper.py` - Enhanced with DB methods
3. `scripts/collect_wisefn_reports.py` - Initial data collection
4. `scripts/test_wisefn_db_read.py` - Database integration test

### Modified Files

1. `scripts/gemini/generate_pdf_report.py:112-133`
   - **Before**: Called `fetch_reports()` - scraped on every PDF generation
   - **After**: Calls `get_from_db()` - fast database read

## Performance Benefits

| Operation | Before (Scraping) | After (Database) |
|-----------|-------------------|------------------|
| PDF Generation | ~10-30s per stock | ~0.1s per stock |
| Network Requests | Every PDF run | Initial collection only |
| Rate Limiting Risk | High | None (DB reads) |
| Data Consistency | Varies by timing | Consistent snapshot |

## Future Enhancements

As mentioned by user, scheduled updates will be implemented:

### Planned Update Frequencies

- **Real-time**: 1분, 10분, 30분, 1시간, 2시간 intervals
- **Periodic**: Daily, Weekly, Monthly
- **Trigger-based**: On-demand for specific stocks

### Implementation Strategy

1. Create update scheduler service
2. Configure update frequency per data source
3. Track last_updated timestamp
4. Implement differential updates
5. Add monitoring and alerts

## Troubleshooting

### Issue: No reports in database

**Solution**: Run initial data collection:
```bash
python scripts/collect_wisefn_reports.py
```

### Issue: Playwright timeout errors

**Cause**: WISEfn page takes >30s to load JavaScript

**Solution**: Increase timeout in `reports_scraper.py:47`:
```python
await page.goto(url, wait_until='networkidle', timeout=60000)  # 60s
```

### Issue: Rate limiting from WISEfn

**Solution**: Adjust delay in `collect_wisefn_reports.py:61`:
```python
await asyncio.sleep(5)  # Increase from 3 to 5 seconds
```

## Related Documentation

- [Database Schema](../sql/02_create_wisefn_reports.sql)
- [PDF Generator](../../scripts/gemini/generate_pdf_report.py)
- [Project Architecture](../01-opensource-integration-analysis.md)

## Changelog

### 2025-11-25 20:37:12 - Initial Implementation

- ✅ Created `wisefn_analyst_reports` table with proper indexes
- ✅ Added database methods to `WISEfnReportsScraper`
- ✅ Updated `generate_pdf_report.py` to use database reads
- ✅ Created `collect_wisefn_reports.py` for initial data population
- ✅ Verified database integration with test script
- ✅ Inserted sample test data for 한국전력 (015760)

---

**Last Updated**: 2025-11-25 20:37:12
