---
created: 2025-11-24 13:32:08
updated: 2025-11-24 13:32:08
tags: [feature, database, integration, asyncpg, postgresql]
author: wonny
status: active
---

# Database Integration Feature

## 개요

PostgreSQL 데이터베이스 통합 기능 구현. 5개 fetcher (Tier 1 & 2)가 수집한 데이터를 자동으로 데이터베이스에 저장하고, 실행 로그 및 헬스 상태를 추적합니다.

## 구현 내용

### 1. BaseFetcher에 save_collected_data() 메서드 추가

**파일**: `src/core/base_fetcher.py`

```python
async def save_collected_data(
    self,
    ticker: str,
    domain_id: int,
    data_type: str,
    data_content: Dict[str, Any],
    data_date: Optional[str] = None
):
    """
    Save raw collected data to collected_data table.

    - Converts data_date string to datetime.date object
    - Stores JSON content as JSONB
    - Uses UPSERT for idempotency
    """
```

**주요 특징**:
- 날짜 문자열 → `datetime.date` 자동 변환
- UPSERT 패턴 (ON CONFLICT DO UPDATE)
- 에러 발생 시 graceful failure (로그만 출력)

### 2. Fetcher별 Domain 매핑

| Fetcher | Site ID | Domain ID | Domain Code | Data Type |
|---------|---------|-----------|-------------|-----------|
| KRX | 1 | 5 | price | ohlcv |
| DART | 2 | 12 | disclosure | disclosure |
| FDR | 3 | 5 | price | ohlcv |
| OpenDART | 4 | 12 | disclosure | disclosure |
| Naver | 6 | 5 | price | price |

### 3. 자동 로깅 및 헬스 모니터링

**이미 구현되어 있던 기능** (BaseFetcher.execute() wrapper):
- `fetch_execution_logs`: 실행 시간, 성공/실패, 에러 타입 자동 기록
- `site_health_status`: 연속 실패 횟수, 평균 응답 시간, 상태 자동 업데이트

## 사용 방법

### 기본 사용 (execute() wrapper 사용)

```python
from src.config.database import db
from src.fetchers.tier1_official_libs.krx_fetcher import KRXFetcher

# 데이터베이스 연결
await db.connect()

# Site 정보 로드
site = await db.fetchrow("SELECT * FROM reference_sites WHERE id = 1")

# Fetcher 생성 및 실행
krx = KRXFetcher(site_id=site['id'], config=site)
data = await krx.execute("005930")  # ✅ 자동으로 로깅 + 저장

# 데이터베이스 연결 종료
await db.disconnect()
```

**execute() wrapper가 자동으로**:
1. `fetch()` 호출하여 데이터 수집
2. `save_collected_data()` 호출하여 JSONB 저장
3. `log_execution()` 호출하여 실행 로그 기록
4. `update_health_status()` 호출하여 헬스 상태 업데이트

### fetch() 직접 호출 (DB 없이 테스트)

```python
krx = KRXFetcher(site_id=1, config={"site_name_ko": "Test"})
data = await krx.fetch("005930")  # ⚠️ DB 없으면 에러 로그만 출력
```

## 데이터베이스 스키마

### collected_data 테이블

```sql
CREATE TABLE collected_data (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    site_id INTEGER NOT NULL REFERENCES reference_sites(id),
    domain_id INTEGER NOT NULL REFERENCES analysis_domains(id),

    data_type VARCHAR(30) NOT NULL,
    data_content JSONB NOT NULL,      -- ✅ 원시 JSON 데이터
    data_date DATE,

    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(ticker, site_id, domain_id, data_type, data_date)
);
```

**JSONB 예시** (KRX OHLCV):
```json
{
  "ticker": "005930",
  "date": "2025-11-24",
  "open": 97800,
  "high": 99000,
  "low": 96800,
  "close": 97000,
  "volume": 14884047,
  "change_rate": 2.32,
  "market_cap": 577756661187200,
  "shares_outstanding": 5919637922,
  "source": "KRX",
  "records_count": 6
}
```

## 성능 지표

**테스트 결과** (Samsung 005930):

| Fetcher | 실행 시간 | 데이터 크기 | 상태 |
|---------|----------|-----------|------|
| KRX | 256ms | 6 레코드 | ✅ Active |
| DART | ~12s | 0 공시 | ✅ Active |
| FDR | <200ms | 4 레코드 | ✅ Active |
| OpenDART | ~500ms | 5 공시 | ✅ Active |
| Naver | <100ms | 1 레코드 | ✅ Active |

## 주의사항

### 1. 데이터베이스 연결 필수

Production 환경에서는 반드시 `db.connect()` 먼저 호출:

```python
# ❌ 나쁜 예
fetcher = KRXFetcher(...)
data = await fetcher.execute("005930")  # DB pool이 None이면 에러

# ✅ 좋은 예
await db.connect()
fetcher = KRXFetcher(...)
data = await fetcher.execute("005930")
await db.disconnect()
```

### 2. UNIQUE 제약 조건

같은 (ticker, site_id, domain_id, data_type, data_date) 조합은 UPSERT:
- 첫 번째 저장: INSERT
- 두 번째 저장: UPDATE (data_content와 collected_at만 갱신)

### 3. JSONB 크기 제한

PostgreSQL JSONB는 최대 약 1GB까지 저장 가능하지만, 실용적으로는:
- 단일 레코드: < 10KB 권장
- 대용량 데이터는 별도 테이블로 정규화 고려

## 관련 문서

- Troubleshooting: [[troubleshooting/database-integration-errors]]
- 변경 이력: [[changelog/2025-11-24-changes]]
- 아키텍처: [[../docs/01-opensource-integration-analysis.md]]
