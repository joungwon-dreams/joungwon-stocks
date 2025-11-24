---
created: 2025-11-24 12:00:00
updated: 2025-11-24 12:00:00
tags: [database, postgresql, schema, design]
author: wonny
status: active
---

# PostgreSQL 데이터베이스 스키마 설계

> AI 기반 한국 주식 투자 자동화 시스템 데이터베이스

## 📋 목차

- [개요](#개요)
- [데이터베이스 구조](#데이터베이스-구조)
- [테이블 상세](#테이블-상세)
- [Views](#views)
- [Triggers](#triggers)
- [Indexes](#indexes)
- [설치 및 사용](#설치-및-사용)

---

## 🎯 개요

### 데이터베이스 정보

```yaml
Database: stock_investment_db
PostgreSQL: 14.20+
Tables: 13개
Views: 2개
Triggers: 4개
Initial Data Sources: 14개
```

### 5개 테이블 그룹

```yaml
1. Master Group (종목 마스터):
   - stocks: 종목 마스터 데이터
   - stock_assets: 보유 종목 및 매매 설정

2. Price Data Group (가격 데이터):
   - daily_ohlcv: 일봉 데이터 (1년)
   - min_ticks: 실시간 틱 데이터
   - stock_prices_10min: 10분 기술 지표
   - stock_supply_demand: 수급 데이터

3. Trading Group (매매 기록):
   - trade_history: 매매 내역 + AI 판단
   - stock_opinions: 투자 의견 및 목표가

4. AI Recommendation Group (AI 추천):
   - data_sources: 데이터 소스 신뢰도
   - recommendation_history: AI 추천 기록
   - verification_results: 7일 후 검증

5. Scoring Group (점수 및 가중치):
   - stock_score_weights: 종목별 가중치
   - stock_score_history: 일별 점수 기록
```

---

## 🏗️ 데이터베이스 구조

### ERD (주요 관계)

```
┌─────────────┐
│   stocks    │ ← 종목 마스터 (KRX 전 종목)
└──────┬──────┘
       │
       ├─────→ stock_assets (보유 종목)
       ├─────→ daily_ohlcv (일봉)
       ├─────→ min_ticks (실시간 틱)
       ├─────→ stock_prices_10min (10분 지표)
       ├─────→ stock_supply_demand (수급)
       ├─────→ trade_history (매매 내역)
       ├─────→ stock_opinions (투자 의견)
       ├─────→ recommendation_history (AI 추천)
       ├─────→ stock_score_weights (가중치)
       └─────→ stock_score_history (점수)

┌──────────────┐
│ data_sources │ ← 데이터 소스 신뢰도
└──────┬───────┘
       │
       └─────→ recommendation_history (FK)

┌───────────────────────┐
│ recommendation_history│
└──────┬────────────────┘
       │
       └─────→ verification_results (7일 후 검증)
```

---

## 📊 테이블 상세

### Group 1: Master Tables

#### 1. `stocks` - 종목 마스터

KRX에서 수집한 전체 상장 종목 정보

```sql
CREATE TABLE stocks (
    stock_code VARCHAR(6) PRIMARY KEY,
    stock_name VARCHAR(100) NOT NULL,
    market VARCHAR(10),                  -- KOSPI/KOSDAQ/KONEX
    sector VARCHAR(50),
    industry VARCHAR(100),
    listing_date DATE,
    is_managed BOOLEAN DEFAULT FALSE,    -- 관리종목 여부
    is_delisted BOOLEAN DEFAULT FALSE,   -- 상장폐지 여부
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**인덱스**:
- PK: `stock_code`
- IDX: `market`, `sector`, `stock_name`

**데이터 소스**: FinanceDataReader `fdr.StockListing('KRX')`


#### 2. `stock_assets` - 보유 종목

현재 보유 중인 종목 및 매매 설정

```sql
CREATE TABLE stock_assets (
    stock_code VARCHAR(6) PRIMARY KEY,
    stock_name VARCHAR(100) NOT NULL,
    quantity INTEGER DEFAULT 0,
    avg_buy_price DECIMAL(10,2) DEFAULT 0,
    current_price DECIMAL(10,2) DEFAULT 0,  -- min_ticks에서 자동 업데이트

    -- 손익 계산 (GENERATED COLUMNS)
    total_value DECIMAL(15,2),              -- quantity * current_price
    total_cost DECIMAL(15,2),               -- quantity * avg_buy_price
    profit_loss DECIMAL(15,2),              -- total_value - total_cost
    profit_loss_rate DECIMAL(5,2),          -- (profit_loss / total_cost) * 100

    -- 매매 설정
    stop_loss_rate DECIMAL(5,2) DEFAULT -5.0,
    target_profit_rate DECIMAL(5,2) DEFAULT 10.0,
    max_position DECIMAL(15,2) DEFAULT 0,

    -- 상태
    is_active BOOLEAN DEFAULT TRUE,
    auto_trading BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**특징**:
- `current_price`는 `min_ticks` INSERT 시 자동 업데이트 (Trigger)
- 손익 계산은 GENERATED COLUMNS로 자동 계산
- `quantity > 0`인 종목만 INDEX 생성

**Trigger**: `trigger_update_stock_assets_price`


### Group 2: Price Data Tables

#### 3. `daily_ohlcv` - 일봉 데이터

과거 1년간 일봉 데이터

```sql
CREATE TABLE daily_ohlcv (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL REFERENCES stocks(stock_code),
    date DATE NOT NULL,
    open DECIMAL(10,2) NOT NULL,
    high DECIMAL(10,2) NOT NULL,
    low DECIMAL(10,2) NOT NULL,
    close DECIMAL(10,2) NOT NULL,
    volume BIGINT NOT NULL,
    trading_value BIGINT,

    -- 이동평균선
    ma5 DECIMAL(10,2),
    ma20 DECIMAL(10,2),
    ma60 DECIMAL(10,2),
    ma120 DECIMAL(10,2),

    created_at TIMESTAMP,
    UNIQUE(stock_code, date)
);
```

**인덱스**:
- Composite: `(stock_code, date DESC)`
- Single: `date DESC`

**데이터 소스**: FinanceDataReader `fdr.DataReader('005930', '2024')`


#### 4. `min_ticks` - 실시간 틱 데이터

WebSocket으로 수신한 1분 단위 실시간 데이터

```sql
CREATE TABLE min_ticks (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL REFERENCES stocks(stock_code),
    timestamp TIMESTAMP NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    change_rate DECIMAL(5,2),
    volume BIGINT,
    bid_price DECIMAL(10,2),
    ask_price DECIMAL(10,2),
    bid_volume BIGINT,
    ask_volume BIGINT,

    created_at TIMESTAMP
);
```

**인덱스**:
- Composite: `(stock_code, timestamp DESC)`
- Single: `timestamp DESC`

**데이터 소스**: Korea Investment Securities WebSocket API

**Trigger**: INSERT 시 `stock_assets.current_price` 자동 업데이트


#### 5. `stock_prices_10min` - 10분 기술 지표

pandas-ta로 계산한 45개 기술 지표 (주요 지표만 저장)

```sql
CREATE TABLE stock_prices_10min (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL REFERENCES stocks(stock_code),
    timestamp TIMESTAMP NOT NULL,

    -- OHLCV
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,

    -- 기술 지표
    rsi_14 DECIMAL(5,2),
    macd DECIMAL(10,4),
    macd_signal DECIMAL(10,4),
    macd_hist DECIMAL(10,4),
    bb_upper DECIMAL(10,2),
    bb_middle DECIMAL(10,2),
    bb_lower DECIMAL(10,2),
    bb_position DECIMAL(5,2),
    stoch_k DECIMAL(5,2),
    stoch_d DECIMAL(5,2),

    created_at TIMESTAMP,
    UNIQUE(stock_code, timestamp)
);
```

**계산 주기**: 10분 (min_ticks 데이터 기반)

**사용 예시**:
```python
import pandas_ta as ta
df.ta.rsi(length=14, append=True)
df.ta.macd(fast=12, slow=26, signal=9, append=True)
df.ta.bbands(length=20, std=2, append=True)
```


#### 6. `stock_supply_demand` - 수급 데이터

외국인/기관/개인 매매 동향

```sql
CREATE TABLE stock_supply_demand (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL REFERENCES stocks(stock_code),
    date DATE NOT NULL,

    -- 순매수 금액 (원)
    foreigner_net BIGINT DEFAULT 0,
    institution_net BIGINT DEFAULT 0,
    individual_net BIGINT DEFAULT 0,

    -- 보유 비율
    foreigner_holding_rate DECIMAL(5,2),

    -- 연기금
    pension_net BIGINT DEFAULT 0,

    created_at TIMESTAMP,
    UNIQUE(stock_code, date)
);
```

**데이터 소스**: pykrx
```python
from pykrx import stock
df = stock.get_market_trading_value_by_date("20240101", "20241231", "005930")
```


### Group 3: Trading Tables

#### 7. `trade_history` - 매매 내역

모든 매매 기록 + AI 판단 근거

```sql
CREATE TABLE trade_history (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL REFERENCES stocks(stock_code),
    stock_name VARCHAR(100),

    -- 거래 정보
    trade_type VARCHAR(4) NOT NULL,      -- BUY/SELL
    trade_date TIMESTAMP NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    total_amount DECIMAL(15,2),          -- GENERATED
    fee DECIMAL(10,2) DEFAULT 0,
    tax DECIMAL(10,2) DEFAULT 0,

    -- AI 판단 근거
    recommendation_id INTEGER,
    total_score DECIMAL(5,2),
    gemini_reasoning TEXT,               -- Gemini AI 판단 근거

    -- 상태
    status VARCHAR(20) DEFAULT 'executed',
    order_type VARCHAR(20),

    created_by VARCHAR(50) DEFAULT 'user',
    note TEXT,
    created_at TIMESTAMP
);
```

**인덱스**:
- `stock_code`, `trade_date DESC`, `trade_type`

**특징**:
- `gemini_reasoning`: Gemini Pro가 생성한 매매 근거 (200자)
- `created_by`: `user`/`ai`/`auto` (수동/AI추천/자동매매)


#### 8. `stock_opinions` - 투자 의견

증권사 애널리스트 리포트 (목표가, 투자의견)

```sql
CREATE TABLE stock_opinions (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL REFERENCES stocks(stock_code),
    stock_name VARCHAR(100),
    opinion_date DATE NOT NULL,

    -- 투자 의견
    opinion VARCHAR(10) NOT NULL,        -- buy/hold/sell
    target_price DECIMAL(10,2),
    current_price DECIMAL(10,2),
    expected_return DECIMAL(5,2),        -- GENERATED

    -- 출처
    source VARCHAR(100),
    analyst_name VARCHAR(50),

    -- 상세
    summary TEXT,
    reasoning TEXT,

    created_at TIMESTAMP
);
```

**데이터 소스**: Tier 3 Web Scraping (증권사 리포트)


### Group 4: AI Recommendation Tables

#### 9. `data_sources` - 데이터 소스 신뢰도

**핵심 테이블**: AI 학습 시스템의 심장

```sql
CREATE TABLE data_sources (
    source_id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) UNIQUE NOT NULL,
    source_type VARCHAR(20) NOT NULL,    -- nps/realtime/report/technical/theme/ai

    -- 신뢰도 점수 (동적 조정)
    reliability_score DECIMAL(3,2) DEFAULT 0.50,  -- 0.0 ~ 1.0

    -- 통계
    total_recommendations INTEGER DEFAULT 0,
    correct_predictions INTEGER DEFAULT 0,
    accuracy_rate DECIMAL(5,2),          -- GENERATED
    average_error_rate DECIMAL(10,2) DEFAULT 0,

    is_active BOOLEAN DEFAULT TRUE,
    last_updated TIMESTAMP,
    created_at TIMESTAMP
);
```

**초기 데이터 (14개)**:

| source_name | source_type | reliability_score |
|-------------|-------------|-------------------|
| 가격_이평선 | technical | 0.70 |
| 거래량_분석 | technical | 0.60 |
| RSI_MACD | technical | 0.80 |
| 볼린저밴드 | technical | 0.75 |
| 외국인_수급 | realtime | 0.85 |
| 기관_수급 | realtime | 0.75 |
| 연기금_수급 | nps | 0.90 |
| 삼성증권_리포트 | report | 0.65 |
| 미래에셋_리포트 | report | 0.70 |
| NH투자증권_리포트 | report | 0.68 |
| 키움증권_리포트 | report | 0.66 |
| Gemini_뉴스_감성분석 | ai | 0.50 |
| Gemini_최종판단 | ai | 0.55 |
| 테마_분석 | theme | 0.45 |

**학습 로직**:
- 7일 후 검증에서 정확도에 따라 `reliability_score` 자동 조정
- 정확: +0.05 ~ +0.10
- 부정확: -0.05 ~ -0.10


#### 10. `recommendation_history` - AI 추천 기록

AI/전문가 추천 기록 (역추적 검증용)

```sql
CREATE TABLE recommendation_history (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL REFERENCES stocks(stock_code),
    stock_name VARCHAR(100),
    recommendation_date DATE NOT NULL,

    -- 추천 내용
    recommended_price DECIMAL(10,2) NOT NULL,
    recommendation_type VARCHAR(10) NOT NULL,  -- buy/hold/sell
    target_price DECIMAL(10,2),

    -- AI 점수 (0-100)
    total_score DECIMAL(5,2),
    price_score DECIMAL(5,2),
    volume_score DECIMAL(5,2),
    supply_score DECIMAL(5,2),
    chart_score DECIMAL(5,2),
    news_score DECIMAL(5,2),
    analyst_score DECIMAL(5,2),

    -- 출처
    source_id INTEGER REFERENCES data_sources(source_id),
    gemini_reasoning TEXT,

    note TEXT,
    created_at TIMESTAMP
);
```

**인덱스**:
- `stock_code`, `recommendation_date DESC`, `source_id`


#### 11. `verification_results` - 7일 후 검증

추천 정확도 검증 (역추적)

```sql
CREATE TABLE verification_results (
    id SERIAL PRIMARY KEY,
    recommendation_id INTEGER NOT NULL REFERENCES recommendation_history(id),
    verification_date DATE NOT NULL,     -- 추천일 + 7일

    -- 실제 결과
    actual_price DECIMAL(10,2) NOT NULL,
    price_change_rate DECIMAL(5,2) NOT NULL,

    -- 정확도 평가
    prediction_correct BOOLEAN,          -- 5% 이상 상승 여부
    error_rate DECIMAL(10,2),

    note TEXT,
    created_at TIMESTAMP
);
```

**검증 로직**:
```python
# 7일 후 자동 검증
actual_price = get_current_price(stock_code)
price_change_rate = (actual_price - recommended_price) / recommended_price * 100

if recommendation_type == 'buy':
    prediction_correct = price_change_rate >= 5.0
elif recommendation_type == 'sell':
    prediction_correct = price_change_rate <= -5.0
```


### Group 5: Scoring Tables

#### 12. `stock_score_weights` - 종목별 가중치

종목별 맞춤형 가중치 (동적 조정)

```sql
CREATE TABLE stock_score_weights (
    stock_code VARCHAR(6) PRIMARY KEY REFERENCES stocks(stock_code),

    -- 기본 가중치 (합계 100%)
    price_weight DECIMAL(5,2) DEFAULT 20.0,
    volume_weight DECIMAL(5,2) DEFAULT 15.0,
    supply_weight DECIMAL(5,2) DEFAULT 30.0,
    chart_weight DECIMAL(5,2) DEFAULT 35.0,

    -- 확장 가중치 (0.0 ~ 2.0)
    news_weight DECIMAL(5,2) DEFAULT 1.0,
    analyst_weight DECIMAL(5,2) DEFAULT 1.0,

    -- 학습 메타
    accuracy_score DECIMAL(5,2) DEFAULT 50.0,
    sample_count INTEGER DEFAULT 0,

    last_updated TIMESTAMP,
    created_at TIMESTAMP,

    -- 가중치 합계 체크
    CONSTRAINT chk_weights_sum CHECK (
        price_weight + volume_weight + supply_weight + chart_weight = 100.0
    )
);
```

**종목별 특성 예시**:

| stock_code | stock_name | price | volume | supply | chart | 특징 |
|------------|------------|-------|--------|--------|-------|------|
| 005930 | 삼성전자 | 25% | 10% | **40%** | 25% | 외국인 비중 높음 |
| 000660 | SK하이닉스 | 20% | **20%** | 35% | 25% | 거래량 중요 |
| 035420 | NAVER | 15% | 15% | 30% | **40%** | 기술적 분석 |
| 207940 | 삼성바이오 | 10% | 10% | 20% | **60%** | 차트+뉴스 |


#### 13. `stock_score_history` - 점수 히스토리

일별 종목 점수 기록 (추이 분석용)

```sql
CREATE TABLE stock_score_history (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL REFERENCES stocks(stock_code),
    date DATE NOT NULL,

    -- 점수 (0-100)
    total_score DECIMAL(5,2) NOT NULL,
    price_score DECIMAL(5,2),
    volume_score DECIMAL(5,2),
    supply_score DECIMAL(5,2),
    chart_score DECIMAL(5,2),
    news_score DECIMAL(5,2),
    analyst_score DECIMAL(5,2),

    -- 신호
    signal VARCHAR(20),                  -- 강력매수/분할매수/관망/매도

    created_at TIMESTAMP,
    UNIQUE(stock_code, date)
);
```

**신호 기준**:
- 80점 이상: 강력매수
- 65~80점: 분할매수
- 35~65점: 관망
- 35점 미만: 매도


---

## 👁️ Views

### 1. `v_holdings_summary` - 보유 종목 현황

```sql
CREATE VIEW v_holdings_summary AS
SELECT
    sa.stock_code,
    sa.stock_name,
    sa.quantity,
    sa.avg_buy_price,
    sa.current_price,
    sa.total_value,
    sa.total_cost,
    sa.profit_loss,
    sa.profit_loss_rate,
    s.market,
    s.sector
FROM stock_assets sa
JOIN stocks s ON sa.stock_code = s.stock_code
WHERE sa.quantity > 0
ORDER BY sa.profit_loss_rate DESC;
```

**사용 예시**:
```sql
SELECT * FROM v_holdings_summary;
```


### 2. `v_data_sources_ranking` - 데이터 소스 순위

```sql
CREATE VIEW v_data_sources_ranking AS
SELECT
    source_id,
    source_name,
    source_type,
    reliability_score,
    accuracy_rate,
    total_recommendations,
    correct_predictions
FROM data_sources
WHERE is_active = TRUE
ORDER BY reliability_score DESC, accuracy_rate DESC;
```

**사용 예시**:
```sql
-- 신뢰도 높은 상위 5개 소스
SELECT * FROM v_data_sources_ranking LIMIT 5;
```


---

## ⚡ Triggers

### 1. `update_updated_at_column()` (3개 테이블)

테이블 UPDATE 시 `updated_at` 자동 업데이트

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 적용 테이블
CREATE TRIGGER update_stocks_updated_at
    BEFORE UPDATE ON stocks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- stock_assets, stock_score_weights도 동일
```


### 2. `update_stock_assets_price()` (min_ticks)

실시간 틱 데이터 INSERT 시 `stock_assets.current_price` 자동 업데이트

```sql
CREATE OR REPLACE FUNCTION update_stock_assets_price()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE stock_assets
    SET current_price = NEW.price,
        updated_at = CURRENT_TIMESTAMP
    WHERE stock_code = NEW.stock_code;

    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_update_stock_assets_price
    AFTER INSERT ON min_ticks
    FOR EACH ROW
    EXECUTE FUNCTION update_stock_assets_price();
```

**효과**:
- WebSocket으로 실시간 가격 수신 → `min_ticks` INSERT
- 자동으로 `stock_assets.current_price` 업데이트
- 손익률 자동 재계산 (GENERATED COLUMNS)


---

## 🗂️ Indexes

### 성능 최적화를 위한 주요 인덱스

```sql
-- 시계열 쿼리 최적화
CREATE INDEX idx_daily_ohlcv_code_date ON daily_ohlcv(stock_code, date DESC);
CREATE INDEX idx_min_ticks_code_timestamp ON min_ticks(stock_code, timestamp DESC);

-- 실시간 조회 최적화
CREATE INDEX idx_stock_assets_quantity ON stock_assets(quantity) WHERE quantity > 0;
CREATE INDEX idx_stock_assets_active ON stock_assets(is_active) WHERE is_active = TRUE;

-- AI 추천 검색 최적화
CREATE INDEX idx_recommendation_history_date ON recommendation_history(recommendation_date DESC);
CREATE INDEX idx_data_sources_reliability ON data_sources(reliability_score DESC);
```

**Partial Index**:
- `quantity > 0`: 보유 종목만 INDEX
- `is_active = TRUE`: 활성 종목만 INDEX


---

## 🚀 설치 및 사용

### 1. 데이터베이스 생성

```bash
# PostgreSQL 설치 확인
psql --version

# 데이터베이스 생성
createdb -U wonny stock_investment_db
```


### 2. 스키마 적용

```bash
# 기존 테이블 삭제 (WARNING: 모든 데이터 삭제!)
psql -U wonny -d stock_investment_db -f sql/00_drop_tables.sql

# 스키마 생성
psql -U wonny -d stock_investment_db -f sql/01_create_tables.sql
```

**출력**:
```
✅ Database schema created successfully!
📊 Tables created: 13
🔍 Views created: 2
⚡ Triggers created: 4
📝 Initial data_sources: 14
```


### 3. 스키마 검증

```bash
psql -U wonny -d stock_investment_db -f sql/02_verify_schema.sql
```

**확인 항목**:
- 13개 테이블 생성
- 2개 뷰 생성
- 4개 트리거 생성
- 14개 데이터 소스 초기화


### 4. Python 연결 예시

```python
import asyncpg

# 데이터베이스 연결
conn = await asyncpg.connect(
    user='wonny',
    database='stock_investment_db',
    host='localhost'
)

# 종목 조회
stocks = await conn.fetch('SELECT * FROM stocks LIMIT 10')

# 보유 종목 현황
holdings = await conn.fetch('SELECT * FROM v_holdings_summary')

# 연결 종료
await conn.close()
```


---

## 📈 데이터 흐름

### 실시간 가격 업데이트

```
WebSocket 수신
    ↓
min_ticks INSERT
    ↓
trigger_update_stock_assets_price 발동
    ↓
stock_assets.current_price 자동 업데이트
    ↓
GENERATED COLUMNS 자동 재계산
    - total_value
    - profit_loss
    - profit_loss_rate
```


### AI 추천 및 학습 프로세스

```
1. 데이터 수집 (41개 소스)
    ↓
2. 점수 계산 (0-100)
    - calculate_price_score()
    - calculate_volume_score()
    - calculate_supply_score()
    - calculate_chart_score()
    - calculate_news_score()
    - calculate_analyst_score()
    ↓
3. 가중치 적용 (stock_score_weights)
    총점 = Σ(점수 × 가중치)
    ↓
4. AI 판단 (Gemini Pro)
    → recommendation_history 저장
    ↓
5. 역추적 (7일 후)
    → verification_results 저장
    ↓
6. 가중치 업데이트
    → data_sources.reliability_score 조정
    → stock_score_weights 조정
```


---

## 🔐 보안 및 백업

### 백업

```bash
# 전체 백업
pg_dump -U wonny stock_investment_db > backup_$(date +%Y%m%d).sql

# 복원
psql -U wonny stock_investment_db < backup_20241124.sql
```

### 권한 관리

```sql
-- 읽기 전용 사용자 생성
CREATE USER analyst WITH PASSWORD 'password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analyst;
```


---

## 📋 SQL 파일 목록

```
sql/
├── 00_drop_tables.sql          # 테이블 삭제 (초기화)
├── 01_create_tables.sql        # 스키마 생성 (메인)
└── 02_verify_schema.sql        # 스키마 검증
```


---

## 🎯 다음 단계

### Phase 1: 데이터 수집

```bash
# 종목 리스트 초기화
python scripts/initialize_stocks.py

# 일봉 데이터 수집 (1년)
python scripts/collect_daily_ohlcv.py

# 실시간 데이터 수집
python src/fetchers/tier2_official_apis/kis_websocket.py
```


### Phase 2: AI 시스템 구현

```bash
# 점수 계산 시스템
python src/scoring/total_scorer.py

# 역추적 검증
python src/learning/verifier.py

# 가중치 자동 조정
python src/learning/weight_updater.py
```


---

**작성일**: 2025-11-24
**작성자**: wonny
**버전**: 1.0
**상태**: Production Ready
