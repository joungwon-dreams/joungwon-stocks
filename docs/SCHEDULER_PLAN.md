# 📊 보유종목 PDF 자동 생성 스케줄러 계획

## 🎯 목표
- 보유종목별 실시간 데이터 수집 및 분석 자동화
- 시간 단위별 최적화된 데이터 업데이트
- 새로운 종목 추가 시 즉시 PDF 생성
- 효율적인 리소스 사용 (DB, API, Gemini)

---

## 📋 PDF 구성 요소 분석

### 현재 PDF 포함 내용
1. **기본 정보**
   - 종목명, 종목코드, 현재가, 전일대비, 등락률
   - 보유수량, 평균매수가, 평가금액, 손익률

2. **차트 이미지** (5개)
   - price_trend.png (가격 추세)
   - financial_performance.png (재무 성과)
   - investor_trends.png (투자자 동향)
   - peer_comparison.png (동종업계 비교)
   - mini_2week_chart.png (2주 미니 차트)

3. **분석 텍스트**
   - 네이버 금융 투자의견
   - 재무제표 분석
   - 뉴스 및 공시 요약
   - AI 투자 의견 (Gemini)

---

## ⏰ 시간 단위별 업데이트 전략

### 📌 1분 주기 (고빈도 데이터)
**수집 대상**:
- 현재가, 등락률, 거래량
- 매수호가/매도호가
- 체결 데이터

**테이블**: `min_ticks`
```sql
INSERT INTO min_ticks (stock_code, timestamp, price, change_rate, volume, ...)
```

**처리 방식**:
- Korea Investment Securities WebSocket 실시간 스트림
- `cron/1min.py` 스크립트 (장 중 09:00-15:30)
- Trigger로 `stock_assets.current_price` 자동 업데이트

**Cron 설정**:
```bash
# 장 중 1분마다 실행
* 9-15 * * 1-5 /path/to/venv/bin/python cron/1min.py
```

**PDF 업데이트**: ❌ (PDF 재생성 안 함, DB만 업데이트)

---

### 📌 10분 주기 (동종업계 비교)
**수집 대상**:
- 동종업계 종목들의 현재가 변화
- 섹터 평균 등락률
- 상대 강도 지수

**테이블**: `peer_comparison` (신규 생성 필요)
```sql
CREATE TABLE peer_comparison (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6),
    peer_stock_code VARCHAR(6),
    timestamp TIMESTAMP,
    relative_strength NUMERIC(5,2),
    sector_avg_change NUMERIC(5,2)
);
```

**처리 방식**:
- 보유종목의 섹터/업종 정보 조회
- 동일 섹터 종목 10-20개 가격 수집
- 상대 성과 계산 및 저장

**Cron 설정**:
```bash
# 장 중 10분마다 실행
*/10 9-15 * * 1-5 /path/to/venv/bin/python scripts/update_peer_comparison.py
```

**PDF 업데이트**: ❌ (차트 데이터 갱신만)

---

### 📌 30분 주기 (뉴스 및 공시)
**수집 대상**:
- 네이버 뉴스 크롤링
- DART 전자공시 조회
- 증권사 리포트 링크

**테이블**: `news` (기존 활용)
```sql
SELECT * FROM news
WHERE stock_code = ?
  AND published_at >= NOW() - INTERVAL '30 minutes'
ORDER BY published_at DESC;
```

**처리 방식**:
- Scrapy 뉴스 크롤러 실행
- DART API 호출
- 중요도 필터링 (Gemini 또는 키워드)

**Cron 설정**:
```bash
# 30분마다 실행
*/30 * * * * /path/to/venv/bin/python scripts/collect_news.py
```

**PDF 업데이트**: ⚠️ (뉴스 섹션만 부분 업데이트 가능)

---

### 📌 1시간 주기 (기술적 지표)
**수집 대상**:
- 1시간봉 OHLCV 데이터
- RSI, MACD, 볼린저밴드
- 거래량 프로필

**테이블**: `hourly_ohlcv` (신규 생성)
```sql
CREATE TABLE hourly_ohlcv (
    stock_code VARCHAR(6),
    hour_timestamp TIMESTAMP,
    open NUMERIC(10,2),
    high NUMERIC(10,2),
    low NUMERIC(10,2),
    close NUMERIC(10,2),
    volume BIGINT,
    rsi_14 NUMERIC(5,2),
    macd NUMERIC(5,2),
    PRIMARY KEY (stock_code, hour_timestamp)
);
```

**처리 방식**:
- `min_ticks`에서 1시간 집계
- 기술적 지표 계산
- 차트 이미지 재생성

**Cron 설정**:
```bash
# 매시 정각에 실행
0 * * * * /path/to/venv/bin/python scripts/update_hourly_indicators.py
```

**PDF 업데이트**: ❌ (차트 데이터만)

---

### 📌 2시간 주기 (투자자 동향)
**수집 대상**:
- 기관/외국인/개인 매매 동향
- 수급 데이터
- 공매도 잔고

**테이블**: `investor_trends` (활용)
```sql
SELECT * FROM stock_supply_demand
WHERE stock_code = ?
ORDER BY trade_date DESC
LIMIT 30;
```

**처리 방식**:
- KRX API 또는 네이버 금융 크롤링
- 누적 수급 계산
- 차트 업데이트

**Cron 설정**:
```bash
# 2시간마다 실행 (10시, 12시, 14시)
0 10,12,14 * * 1-5 /path/to/venv/bin/python scripts/update_investor_trends.py
```

**PDF 업데이트**: ❌

---

### 📌 4시간 주기 (재무 데이터)
**수집 대상**:
- PER, PBR, ROE 등 재무비율
- 영업이익률, 순이익률
- 부채비율, 유동비율

**테이블**: 기존 테이블 활용
```sql
-- 이미 수집된 재무 데이터 활용
```

**처리 방식**:
- 분기 재무제표는 이미 수집됨
- 차트만 재생성

**Cron 설정**:
```bash
# 4시간마다 (10시, 14시)
0 10,14 * * 1-5 /path/to/venv/bin/python scripts/update_financial_charts.py
```

**PDF 업데이트**: ❌

---

### 📌 6시간 주기 (종합 차트 재생성)
**수집 대상**:
- 모든 차트 이미지 재생성
- 가격 추세, 재무 성과, 투자자 동향, 동종업계 비교

**처리 방식**:
- 최신 DB 데이터로 5개 차트 모두 재생성
- `charts/` 폴더에 저장
- 자동으로 sync_reports.py가 복사

**Cron 설정**:
```bash
# 6시간마다 (09:00, 15:00)
0 9,15 * * 1-5 /path/to/venv/bin/python scripts/regenerate_all_charts.py
```

**PDF 업데이트**: ✅ (전체 PDF 재생성)

---

### 📌 24시간 주기 (완전 재분석)
**수집 대상**:
- Gemini AI 종합 분석
- 투자 의견 재생성
- 목표가 재산정

**처리 방식**:
- 모든 데이터 종합
- Gemini API 호출 (비용 발생)
- 완전히 새로운 PDF 생성

**Cron 설정**:
```bash
# 매일 장 마감 후 (16:00)
0 16 * * 1-5 /path/to/venv/bin/python scripts/daily_full_report_generation.py
```

**PDF 업데이트**: ✅ (전체 PDF 완전 재생성)

---

### 📌 7일 주기 (주간 리뷰)
**수집 대상**:
- 주간 성과 분석
- 포트폴리오 리밸런싱 제안
- 장기 전략 업데이트

**처리 방식**:
- 주간 수익률 계산
- 섹터별 배분 분석
- Gemini로 주간 리포트 생성

**Cron 설정**:
```bash
# 매주 금요일 17:00
0 17 * * 5 /path/to/venv/bin/python scripts/weekly_portfolio_review.py
```

**PDF 업데이트**: ✅ (주간 리포트 별도 PDF)

---

## 🆕 신규 종목 추가 시 즉시 PDF 생성

### Trigger 기반 자동 생성

**데이터베이스 트리거**:
```sql
CREATE OR REPLACE FUNCTION auto_generate_new_stock_pdf()
RETURNS TRIGGER AS $$
BEGIN
    -- stock_assets에 새 종목이 quantity > 0으로 추가되면
    IF NEW.quantity > 0 AND (OLD IS NULL OR OLD.quantity = 0) THEN
        -- Python 스크립트 비동기 실행
        PERFORM pg_notify('new_stock_added', NEW.stock_code);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_new_stock_pdf
AFTER INSERT OR UPDATE ON stock_assets
FOR EACH ROW
EXECUTE FUNCTION auto_generate_new_stock_pdf();
```

**Python Listener** (`scripts/new_stock_listener.py`):
```python
import asyncio
import asyncpg

async def listen_for_new_stocks():
    conn = await asyncpg.connect(user='wonny', database='stock_investment_db')

    async def handle_notification(connection, pid, channel, payload):
        stock_code = payload
        print(f"🆕 New stock added: {stock_code}")

        # 즉시 PDF 생성
        await generate_initial_pdf(stock_code)

    await conn.add_listener('new_stock_added', handle_notification)

    # Keep running
    while True:
        await asyncio.sleep(1)

async def generate_initial_pdf(stock_code):
    """신규 종목 PDF 즉시 생성"""
    # 1. 기본 데이터 수집 (5분 소요)
    await collect_basic_data(stock_code)

    # 2. 차트 생성 (2분 소요)
    await generate_charts(stock_code)

    # 3. Gemini 분석 (3분 소요)
    await gemini_analysis(stock_code)

    # 4. PDF 생성 (1분 소요)
    await create_pdf(stock_code)

    print(f"✅ PDF generated for {stock_code}")
```

**백그라운드 실행**:
```bash
# 항상 실행 (systemd 또는 nohup)
nohup /path/to/venv/bin/python scripts/new_stock_listener.py &
```

---

## 📊 데이터 수집 우선순위

### 우선순위 1 (실시간)
- 현재가 (`min_ticks`)
- 체결 데이터
- 호가 데이터

### 우선순위 2 (10분)
- 동종업계 비교
- 섹터 동향

### 우선순위 3 (30분)
- 뉴스 및 공시
- 리포트 링크

### 우선순위 4 (1-2시간)
- 기술적 지표
- 투자자 동향

### 우선순위 5 (일 1회)
- Gemini AI 분석
- 완전한 PDF 재생성

---

## 🗄️ 필요한 신규 테이블

### 1. `hourly_ohlcv` (1시간봉 데이터)
```sql
CREATE TABLE hourly_ohlcv (
    stock_code VARCHAR(6),
    hour_timestamp TIMESTAMP,
    open NUMERIC(10,2),
    high NUMERIC(10,2),
    low NUMERIC(10,2),
    close NUMERIC(10,2),
    volume BIGINT,
    rsi_14 NUMERIC(5,2),
    macd NUMERIC(5,2),
    signal NUMERIC(5,2),
    PRIMARY KEY (stock_code, hour_timestamp)
);

CREATE INDEX idx_hourly_stock_time ON hourly_ohlcv(stock_code, hour_timestamp DESC);
```

### 2. `peer_comparison` (동종업계 비교)
```sql
CREATE TABLE peer_comparison (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6),
    timestamp TIMESTAMP,
    peer_stock_code VARCHAR(6),
    relative_strength NUMERIC(5,2),
    sector_avg_change NUMERIC(5,2),
    rank_in_sector INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_peer_stock_time ON peer_comparison(stock_code, timestamp DESC);
```

### 3. `pdf_generation_log` (PDF 생성 로그)
```sql
CREATE TABLE pdf_generation_log (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6),
    generation_type VARCHAR(20), -- 'full', 'partial', 'initial'
    file_path TEXT,
    generation_time INTERVAL,
    gemini_tokens_used INTEGER,
    status VARCHAR(20), -- 'success', 'failed', 'pending'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔄 Cron 작업 전체 요약

```bash
# crontab -e

# ========== 1분 주기 ==========
# 실시간 가격 수집 (장 중)
* 9-15 * * 1-5 /Users/wonny/Dev/joungwon.stocks/venv/bin/python /Users/wonny/Dev/joungwon.stocks/cron/1min.py >> /Users/wonny/Dev/joungwon.stocks/logs/1min.log 2>&1

# ========== 5분 주기 ==========
# Reports 자동 동기화
*/5 * * * * /Users/wonny/Dev/joungwon.stocks/venv/bin/python /Users/wonny/Dev/joungwon.stocks/scripts/sync_reports.py >> /Users/wonny/Dev/joungwon.stocks/logs/sync_reports.log 2>&1

# ========== 10분 주기 ==========
# 동종업계 비교 데이터 수집
*/10 9-15 * * 1-5 /Users/wonny/Dev/joungwon.stocks/venv/bin/python /Users/wonny/Dev/joungwon.stocks/scripts/update_peer_comparison.py >> /Users/wonny/Dev/joungwon.stocks/logs/peer_comparison.log 2>&1

# ========== 30분 주기 ==========
# 뉴스 및 공시 수집
*/30 * * * * /Users/wonny/Dev/joungwon.stocks/venv/bin/python /Users/wonny/Dev/joungwon.stocks/scripts/collect_news.py >> /Users/wonny/Dev/joungwon.stocks/logs/news.log 2>&1

# ========== 1시간 주기 ==========
# 기술적 지표 계산
0 * * * * /Users/wonny/Dev/joungwon.stocks/venv/bin/python /Users/wonny/Dev/joungwon.stocks/scripts/update_hourly_indicators.py >> /Users/wonny/Dev/joungwon.stocks/logs/hourly_indicators.log 2>&1

# ========== 2시간 주기 ==========
# 투자자 동향 업데이트
0 10,12,14 * * 1-5 /Users/wonny/Dev/joungwon.stocks/venv/bin/python /Users/wonny/Dev/joungwon.stocks/scripts/update_investor_trends.py >> /Users/wonny/Dev/joungwon.stocks/logs/investor_trends.log 2>&1

# ========== 6시간 주기 ==========
# 전체 차트 재생성 + PDF 생성
0 9,15 * * 1-5 /Users/wonny/Dev/joungwon.stocks/venv/bin/python /Users/wonny/Dev/joungwon.stocks/scripts/regenerate_all_charts_and_pdfs.py >> /Users/wonny/Dev/joungwon.stocks/logs/chart_regen.log 2>&1

# ========== 24시간 주기 ==========
# 완전 재분석 및 PDF 생성 (장 마감 후)
0 16 * * 1-5 /Users/wonny/Dev/joungwon.stocks/venv/bin/python /Users/wonny/Dev/joungwon.stocks/scripts/daily_full_report_generation.py >> /Users/wonny/Dev/joungwon.stocks/logs/daily_report.log 2>&1

# ========== 주간 리뷰 ==========
# 주간 포트폴리오 리뷰 (금요일 17:00)
0 17 * * 5 /Users/wonny/Dev/joungwon.stocks/venv/bin/python /Users/wonny/Dev/joungwon.stocks/scripts/weekly_portfolio_review.py >> /Users/wonny/Dev/joungwon.stocks/logs/weekly_review.log 2>&1
```

---

## 💰 비용 최적화

### Gemini API 사용 최소화
- **일 1회만 전체 분석** (16:00)
- 신규 종목 추가 시에만 즉시 분석
- 캐싱 적극 활용

### 네이버/KRX API 효율화
- 배치 처리로 API 호출 횟수 줄이기
- 결과 캐싱 (Redis 또는 DB)

---

## 📁 스크립트 구조

```
scripts/
├── cron/
│   ├── 1min.py                              # ✅ 기존
│   └── README.md                             # ✅ 기존
├── update_peer_comparison.py                 # 🆕 작성 필요
├── collect_news.py                           # 🆕 작성 필요
├── update_hourly_indicators.py               # 🆕 작성 필요
├── update_investor_trends.py                 # 🆕 작성 필요
├── regenerate_all_charts_and_pdfs.py         # 🆕 작성 필요
├── daily_full_report_generation.py           # 🆕 작성 필요
├── weekly_portfolio_review.py                # 🆕 작성 필요
├── new_stock_listener.py                     # 🆕 작성 필요 (백그라운드)
└── sync_reports.py                           # ✅ 기존
```

---

## 🎯 구현 우선순위

### Phase 1 (즉시)
1. ✅ `sync_reports.py` - 완료
2. ✅ `cron/1min.py` - 완료
3. 🆕 신규 테이블 생성 (`hourly_ohlcv`, `peer_comparison`, `pdf_generation_log`)

### Phase 2 (1주 내)
4. 🆕 `update_peer_comparison.py`
5. 🆕 `collect_news.py`
6. 🆕 `update_hourly_indicators.py`

### Phase 3 (2주 내)
7. 🆕 `regenerate_all_charts_and_pdfs.py`
8. 🆕 `daily_full_report_generation.py`

### Phase 4 (3주 내)
9. 🆕 `new_stock_listener.py`
10. 🆕 `weekly_portfolio_review.py`

---

**마지막 업데이트**: 2025-11-26 07:40:00
**작성자**: Claude Code Assistant
