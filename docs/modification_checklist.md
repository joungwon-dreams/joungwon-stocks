# 데이터 수집 및 PDF 리포트 개선 체크리스트

**작성일**: 2025-11-25
**요청 내용**: 네이버/다음 증권 페이지에서 추가 데이터 수집 여부 확인 및 PDF 리포트 개선

---

## ✅ 완료된 작업

### 1. 뉴스 섹션 추가 (완료)
- **파일**: `scripts/gemini/generate_pdf_report.py`
- **수정 내용**:
  - `NaverNewsFetcher` 임포트 추가
  - `fetch_all_data()` 메서드에 뉴스 수집 로직 추가
  - `generate_pdf()` 메서드에 뉴스 테이블 생성 로직 추가 (새 페이지)
- **결과**: PDF 리포트에 최근 뉴스 10건 표시 (일시, 제목)

---

## 📊 데이터 수집 현황 분석

### Image #1: 2025년 실적 전망 (Naver)
**수집 여부**: ✅ **부분 수집**

**현황**:
- `stock_financials` 테이블에 2025년 Q1, Q2, Q3 데이터 존재
- 실적 발표일, 발표 직전 Surprise 데이터는 **미수집**

**Fetcher**: `scripts/gemini/naver/financials.py` - `NaverFinancialsFetcher`
- API: `https://m.stock.naver.com/api/stock/{stock_code}/finance/annual`
- API: `https://m.stock.naver.com/api/stock/{stock_code}/finance/quarter`
- 현재: 매출액, 영업이익, 순이익만 수집

**추가 필요 데이터**:
1. 실적발표일 (Earnings Date)
2. 발표직전 (Before Announcement)
3. Surprise 데이터 (실적 서프라이즈)

**DB 수정**:
```sql
ALTER TABLE stock_financials ADD COLUMN earnings_date DATE;
ALTER TABLE stock_financials ADD COLUMN earnings_before_status VARCHAR(20);
ALTER TABLE stock_financials ADD COLUMN earnings_surprise DECIMAL(10, 2);
```

**Fetcher 수정**:
- `NaverFinancialsFetcher._parse_finance_info()` 메서드 확장
- Naver API 응답에서 추가 필드 파싱

---

### Image #2: 동종업계 비교 (Naver)
**수집 여부**: ✅ **수집 중**

**현황**:
- `stock_peers` 테이블에 데이터 존재 (한국전력: 4개 peer)
- `stock_fundamentals`와 조인하여 PER, PBR, ROE 비교 가능

**Fetcher**: **확인 필요** (어떤 fetcher가 peers 데이터를 수집하는지 불명확)

**추가 확인 필요**:
1. Peers 데이터 수집 fetcher 확인
2. 더 많은 peer 회사 수집 (현재 4개)
3. Naver API에서 추가 동종업계 데이터 수집 가능 여부 확인

**추천 작업**:
- Naver에서 동종업계 목록 API 찾기
- API: `https://m.stock.naver.com/api/stock/{stock_code}/similar` (예상)

---

### Image #3: 신용등급 (Naver)
**수집 여부**: ❌ **미수집**

**필요 데이터**:
- KIS 신용등급 (AAA, AA 등)
- KR 신용등급
- NICE 신용등급
- 평가 날짜
- 주요주주 정보

**DB 생성 필요**:
```sql
CREATE TABLE credit_ratings (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL REFERENCES stocks(stock_code),
    rating_agency VARCHAR(50) NOT NULL,  -- KIS, KR, NICE
    credit_rating VARCHAR(10),           -- AAA, AA, A 등
    rating_date DATE,
    outlook VARCHAR(20),                 -- Stable, Positive, Negative
    collected_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(stock_code, rating_agency, rating_date)
);

CREATE TABLE major_shareholders (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL REFERENCES stocks(stock_code),
    shareholder_name VARCHAR(200) NOT NULL,
    shares_held BIGINT,
    ownership_percentage DECIMAL(5, 2),
    relationship VARCHAR(100),           -- 최대주주, 특수관계인 등
    as_of_date DATE,
    collected_at TIMESTAMP DEFAULT NOW()
);
```

**Fetcher 생성 필요**:
- 파일: `scripts/gemini/naver/credit_rating.py`
- API 찾기: Naver에서 신용등급 API 확인 필요

---

### Image #4: 투자의견 컨센서스 상세 (Naver)
**수집 여부**: ✅ **수집 중 (기본 정보만)**

**현황**:
- `stock_consensus` 테이블에 기본 컨센서스 데이터 있음
  - 평균 투자의견 (opinion)
  - 평균 목표주가 (target_price)
  - 애널리스트 수 (analyst_count)

**추가 필요 데이터**:
- EPS 컨센서스
- PER 컨센서스
- 추정기관수

**Fetcher**: `scripts/gemini/naver/consensus.py` - `NaverConsensusFetcher`
- API: `https://m.stock.naver.com/api/stock/{stock_code}/integration`

**DB 수정**:
```sql
ALTER TABLE stock_consensus ADD COLUMN consensus_eps DECIMAL(10, 2);
ALTER TABLE stock_consensus ADD COLUMN consensus_per DECIMAL(10, 2);
ALTER TABLE stock_consensus ADD COLUMN estimate_firms_count INTEGER;
```

**Fetcher 수정**:
- `fetch_consensus()` 메서드에서 추가 필드 파싱

---

### Image #5: 종목리포트 목록 (Daum)
**수집 여부**: ✅ **부분 수집**

**현황**:
- `analyst_reports` 테이블 존재하지만 **데이터 없음** (count=0)
- 테이블 스키마는 완벽 (securities_firm, analyst_name, target_price, opinion, report_title, report_date, report_url)

**문제**: Fetcher가 없거나 실행되지 않음

**Fetcher 생성/수정 필요**:
- 파일: `scripts/gemini/daum/reports.py` (신규 생성 필요)
- API 찾기: Daum에서 리포트 목록 API 확인
- 또는 `scripts/gemini/naver/consensus.py`의 `fetch_analyst_reports()` 활용
  - 현재는 뉴스 API를 프록시로 사용 중

**추천 작업**:
1. Daum 리포트 API 찾기
2. Fetcher 구현: `DaumReportsFetcher` 클래스
3. `collect_and_cache_data.py`에 통합

---

### Image #6: 주가 컨센서스 (Daum)
**수집 여부**: ✅ **기본 정보 수집 중**

**현황**:
- `stock_consensus` 테이블에 목표주가, 투자의견 있음

**추가 필요 데이터**:
- 최근 목표주가 (Recent Target)
- 최고 목표주가 (High Target)
- 최저 목표주가 (Low Target)

**DB 수정**:
```sql
ALTER TABLE stock_consensus ADD COLUMN target_price_high INTEGER;
ALTER TABLE stock_consensus ADD COLUMN target_price_low INTEGER;
ALTER TABLE stock_consensus ADD COLUMN target_price_recent INTEGER;
```

**Fetcher 수정**:
- Daum 또는 Naver API에서 추가 컨센서스 정보 수집

---

### Image #9: 증권사별 리포트 상세 목록 (Daum)
**수집 여부**: ⚠️ **테이블은 있으나 데이터 없음**

**현황**:
- `analyst_reports` 테이블 존재 (Image #5와 동일)
- 스키마: securities_firm, report_title, report_date, target_price, opinion
- **데이터 없음** (count=0)

**필요 작업**: Image #5와 동일

---

### Image #10: 증권사별 투자목표 (Daum)
**수집 여부**: ✅ **수집 중**

**현황**:
- `analyst_target_prices` 테이블에 데이터 10개 존재
- 스키마: brokerage, analyst, target_price, opinion, report_date

**추가 필요 데이터**:
- 직전 목표가 (Previous Target Price)
- 변동률 (Change %)
- 직전 투자의견 (Previous Opinion)

**DB 수정**:
```sql
ALTER TABLE analyst_target_prices ADD COLUMN prev_target_price INTEGER;
ALTER TABLE analyst_target_prices ADD COLUMN price_change_rate DECIMAL(10, 2);
ALTER TABLE analyst_target_prices ADD COLUMN prev_opinion VARCHAR(20);
```

**Fetcher 수정**:
- 현재 fetcher가 어디인지 확인 필요
- 추가 필드 파싱 로직 구현

---

## 📝 수정 파일 목록 요약

### 1. 즉시 수정 필요 (뉴스 - 완료)
- ✅ `scripts/gemini/generate_pdf_report.py` - 뉴스 섹션 추가 완료

### 2. DB 스키마 수정
```bash
scripts/sql/
├── 11_add_earnings_forecast_columns.sql   # 2025 실적 전망 필드
├── 12_add_consensus_details.sql          # 컨센서스 상세 필드
├── 13_add_target_price_details.sql       # 목표가 상세 필드
└── 14_create_credit_rating_tables.sql    # 신용등급 테이블 생성
```

### 3. Fetcher 수정/생성
```bash
scripts/gemini/
├── naver/
│   ├── financials.py                    # 실적 전망 추가 필드
│   ├── consensus.py                     # 컨센서스 상세 필드
│   ├── credit_rating.py                 # [신규] 신용등급 fetcher
│   └── peers.py                         # [확인 필요] 동종업계 fetcher
├── daum/
│   ├── reports.py                       # [신규] 증권사 리포트 fetcher
│   └── consensus.py                     # [신규] 주가 컨센서스 상세
└── collect_and_cache_data.py            # 새 fetcher 통합
```

### 4. PDF 리포트 수정
```bash
scripts/gemini/generate_pdf_report.py
# 추가 섹션:
# - 2025 실적 전망 테이블
# - 신용등급 정보
# - 증권사별 리포트 목록 (현재는 컨센서스만)
```

---

## 🎯 우선순위별 작업 계획

### 우선순위 1: 데이터 수집 완성 (1-2주)
1. **신용등급 수집** (Image #3)
   - DB 테이블 생성
   - Naver API 찾기
   - Fetcher 구현

2. **증권사 리포트 수집** (Image #5, #9)
   - Daum/Naver API 찾기
   - Fetcher 구현
   - `analyst_reports` 테이블에 데이터 채우기

3. **실적 전망 상세 수집** (Image #1)
   - DB 컬럼 추가
   - Naver API 확장 파싱

### 우선순위 2: 컨센서스 데이터 보강 (1주)
1. **컨센서스 상세 정보** (Image #4, #6)
   - EPS/PER 컨센서스 추가
   - 목표주가 범위 (최고/최저) 추가

2. **목표가 변동 추적** (Image #10)
   - 직전 목표가/의견 추가
   - 변동률 계산

### 우선순위 3: PDF 리포트 개선 (1주)
1. 수집된 데이터를 PDF에 통합
2. 새 섹션 추가:
   - 2025 실적 전망
   - 신용등급
   - 증권사 리포트 요약

---

## 📌 중요 참고사항

### Naver Finance Mobile API
- Base URL: `https://m.stock.naver.com/api/`
- User-Agent: iPhone 14.0
- Referer: `https://m.stock.naver.com/`

### Daum Finance API
- Base URL: `https://finance.daum.net/api/`
- Referer: `https://finance.daum.net/`

### 데이터 수집 주기
- 정적 데이터 (신용등급, 주요주주): 월 1회
- 느린 변화 (컨센서스, 재무제표): 주 1회
- 빠른 변화 (뉴스, 리포트): 일 1회

---

**작성일**: 2025-11-25
**작성자**: Claude (AI Assistant)
**다음 단계**: 사용자가 우선순위에 따라 파일 수정 진행
