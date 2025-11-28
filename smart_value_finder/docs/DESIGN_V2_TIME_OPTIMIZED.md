# Smart Value Finder v2.0 - 시간 최적화 설계

## 핵심 목표: 시간 효율성 극대화

기존 설계의 문제점:
- 2,500+ 종목 전체 스크리닝 → 수 시간 소요
- 종목별 개별 뉴스 수집 → API Rate Limit 병목
- Gemini AI 호출 횟수 제한 (60 calls/min)
- 피드백 루프 시 전체 파이프라인 재실행

**목표**: 30분 내 결과 도출, 피드백 시 5분 내 재분석

---

## 1. 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                    Smart Value Finder v2.0                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [LAYER 1: 캐시 계층]                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ daily_ohlcv  │  │ stock_supply │  │ collected_   │           │
│  │ (DB 캐시)    │  │ _demand (DB) │  │ data (DB)    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│         ↓                  ↓                  ↓                  │
│  [LAYER 2: 정량 스크리닝] ─────────────────────────────────────   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Phase 1A: DB 기반 1차 필터 (SQL Only, <1초)             │    │
│  │  • PBR/PER → stocks 테이블에서 직접 필터                  │    │
│  │  • 거래량/시총 → daily_ohlcv 최근 1일                     │    │
│  │  결과: ~200개 후보                                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│         ↓                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Phase 1B: 기술적 지표 계산 (Pandas, ~30초)              │    │
│  │  • RSI(14), 이격도(20/60) → daily_ohlcv에서 계산         │    │
│  │  • 수급 데이터 → stock_supply_demand 테이블               │    │
│  │  결과: ~50개 후보                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│         ↓                                                        │
│  [LAYER 3: 배치 데이터 수집] ──────────────────────────────────   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Phase 2A: 병렬 배치 수집 (~5분, 50개 종목)              │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │    │
│  │  │ Naver News  │ │ Daum API    │ │ Wise Report │        │    │
│  │  │ (Rate: 1/s) │ │ (Rate: 2/s) │ │ (Rate: 1/s) │        │    │
│  │  └─────────────┘ └─────────────┘ └─────────────┘        │    │
│  │  전략: 사이트별 병렬 + 사이트내 순차 (Rate Limit 준수)   │    │
│  └─────────────────────────────────────────────────────────┘    │
│         ↓                                                        │
│  [LAYER 4: AI 분석] ──────────────────────────────────────────   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Phase 2B: Gemini 배치 분석 (~10분)                      │    │
│  │  • 5개 종목씩 묶어서 1회 호출 (토큰 효율화)               │    │
│  │  • 50개 종목 = 10회 API 호출                             │    │
│  │  • Rate: 6 calls/min 안전 마진                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│         ↓                                                        │
│  [LAYER 5: 스코어링 & 피드백] ────────────────────────────────   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Phase 3: 최종 스코어링 (<1분)                           │    │
│  │  • 정량 40% + 정성 60%                                   │    │
│  │  • smart_recommendations 테이블 저장                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│         ↓                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Phase 4: 피드백 루프 (증분 재분석 ~5분)                 │    │
│  │  • 사용자 피드백 → 특정 종목만 재분석                    │    │
│  │  • 필터 조건 변경 → Phase 1B부터 재실행                  │    │
│  │  • AI 기준 변경 → Phase 2B만 재실행                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase 1: 정량 스크리닝 (DB 중심)

### 2.1 Phase 1A: SQL 기반 1차 필터 (<1초)

**목표**: 2,500개 → 200개로 즉시 축소

```sql
-- smart_value_phase1a.sql
WITH latest_prices AS (
    SELECT DISTINCT ON (stock_code)
        stock_code,
        close_price,
        volume,
        market_cap
    FROM daily_ohlcv
    WHERE trade_date >= CURRENT_DATE - INTERVAL '3 days'
    ORDER BY stock_code, trade_date DESC
),
fundamental_filter AS (
    SELECT
        s.stock_code,
        s.stock_name,
        s.pbr,
        s.per,
        lp.close_price,
        lp.volume,
        lp.market_cap
    FROM stocks s
    JOIN latest_prices lp ON s.stock_code = lp.stock_code
    WHERE
        s.is_delisted = FALSE
        AND s.pbr BETWEEN 0.2 AND 1.0      -- 저PBR
        AND s.per BETWEEN 3 AND 10          -- 저PER
        AND lp.volume >= 100000             -- 최소 거래량 (유동성)
        AND lp.market_cap >= 100000000000   -- 시총 1000억 이상 (안정성)
)
SELECT * FROM fundamental_filter
ORDER BY pbr ASC, per ASC
LIMIT 200;
```

**핵심 포인트**:
- Fetcher 호출 없음 (기존 수집 데이터 활용)
- stocks 테이블에 PBR/PER가 없으면 collected_data에서 조인
- 인덱스: `(is_delisted, pbr, per)` 복합 인덱스 필요

### 2.2 Phase 1B: 기술적 지표 필터 (~30초)

**목표**: 200개 → 50개로 축소

```python
# smart_value_finder/src/analysis/technical_filter.py
import pandas as pd
import numpy as np
from typing import List, Dict

class TechnicalFilter:
    """
    DB에서 OHLCV 데이터 로드 후 기술적 지표 계산
    Fetcher 호출 없음 - 100% DB 기반
    """

    def __init__(self, db_pool):
        self.db = db_pool

    async def filter_candidates(self, candidates: List[str]) -> List[Dict]:
        """
        Phase 1A 결과에 기술적 필터 적용

        Args:
            candidates: Phase 1A에서 나온 종목 코드 리스트 (200개)

        Returns:
            기술적 조건 통과한 종목 리스트 (50개 이하)
        """
        results = []

        # 배치로 60일 OHLCV 로드 (1회 쿼리)
        ohlcv_data = await self._load_batch_ohlcv(candidates, days=60)

        # 수급 데이터 배치 로드 (1회 쿼리)
        supply_data = await self._load_batch_supply_demand(candidates, days=20)

        for code in candidates:
            df = ohlcv_data.get(code)
            if df is None or len(df) < 60:
                continue

            # 기술적 지표 계산 (Pandas, 메모리 내)
            rsi = self._calculate_rsi(df['close'], period=14)
            disparity_20 = df['close'].iloc[-1] / df['close'].rolling(20).mean().iloc[-1] * 100
            disparity_60 = df['close'].iloc[-1] / df['close'].rolling(60).mean().iloc[-1] * 100

            # 수급 데이터 확인
            supply = supply_data.get(code, {})
            pension_net_buy = supply.get('pension_net_buy', 0)
            institution_net_buy = supply.get('institution_net_buy', 0)

            # 필터 조건
            if (30 <= rsi <= 60 and                    # 과매수/과매도 아닌 구간
                disparity_20 <= 105 and               # 20일선 대비 5% 이하 이격
                disparity_60 <= 110 and               # 60일선 대비 10% 이하 이격
                (pension_net_buy > 0 or institution_net_buy > 0)):  # 기관/연기금 순매수

                results.append({
                    'code': code,
                    'rsi': rsi,
                    'disparity_20': disparity_20,
                    'disparity_60': disparity_60,
                    'pension_net_buy': pension_net_buy,
                    'institution_net_buy': institution_net_buy,
                    'quant_score': self._calculate_quant_score(...)
                })

        # 상위 50개만 반환
        results.sort(key=lambda x: x['quant_score'], reverse=True)
        return results[:50]

    async def _load_batch_ohlcv(self, codes: List[str], days: int) -> Dict[str, pd.DataFrame]:
        """200개 종목 60일 OHLCV를 1회 쿼리로 로드"""
        query = """
            SELECT stock_code, trade_date, open_price, high_price,
                   low_price, close_price, volume
            FROM daily_ohlcv
            WHERE stock_code = ANY($1)
              AND trade_date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY stock_code, trade_date
        """ % days

        rows = await self.db.fetch(query, codes)

        # 종목별로 DataFrame 그룹화
        result = {}
        df = pd.DataFrame(rows)
        for code, group in df.groupby('stock_code'):
            result[code] = group.reset_index(drop=True)

        return result
```

**시간 분석**:
- SQL 배치 로드: ~5초 (200종목 × 60일 = 12,000 rows)
- Pandas 계산: ~25초 (종목당 ~0.125초)
- **총 소요: ~30초**

---

## 3. Phase 2: 데이터 수집 (Rate Limit 최적화)

### 3.1 Fetcher Rate Limit 현황

| Tier | 소스 | Rate Limit | 안전 마진 |
|------|------|-----------|----------|
| Tier 1 | pykrx | ~10/min (추정) | 5/min |
| Tier 2 | Naver API | 60/min | 30/min |
| Tier 2 | Daum API | 60/min | 30/min |
| Tier 3 | Scrapers | 20/min (IP ban 위험) | 12/min |
| Tier 4 | Playwright | 10/min (리소스) | 6/min |
| AI | Gemini Pro | 60/min | 30/min |

### 3.2 Phase 2A: 병렬 배치 수집 전략 (~5분)

**핵심 전략**: 사이트 간 병렬, 사이트 내 순차

```python
# smart_value_finder/src/collectors/batch_collector.py
import asyncio
from typing import List, Dict
from src.core.rate_limiter import MultiRateLimiter

class BatchCollector:
    """
    50개 종목을 5분 내 수집하는 배치 컬렉터

    전략:
    1. 사이트별 독립 큐 운영
    2. 사이트 간 완전 병렬 (6개 사이트 동시)
    3. 사이트 내 Rate Limit 준수 (순차)
    4. 캐시 우선 조회
    """

    def __init__(self):
        self.rate_limiters = MultiRateLimiter()
        self.cache_ttl = 3600  # 1시간 캐시

        # 수집 소스 우선순위 (빠른 순)
        self.sources = [
            {'name': 'naver_api', 'rate': 30, 'priority': 1},
            {'name': 'daum_api', 'rate': 30, 'priority': 2},
            {'name': 'wise_report', 'rate': 12, 'priority': 3},
            {'name': 'fnguide', 'rate': 12, 'priority': 4},
            {'name': 'securities', 'rate': 12, 'priority': 5},  # 증권사 리포트
            {'name': 'news_aggregate', 'rate': 12, 'priority': 6},  # 뉴스 통합
        ]

    async def collect_all(self, candidates: List[Dict]) -> Dict[str, Dict]:
        """
        50개 종목의 뉴스/리포트/컨센서스 수집

        Args:
            candidates: Phase 1B 결과

        Returns:
            종목별 수집 데이터
        """
        results = {}
        codes = [c['code'] for c in candidates]

        # 1. 캐시 먼저 확인
        cached = await self._check_cache(codes)
        uncached_codes = [c for c in codes if c not in cached]
        results.update(cached)

        if not uncached_codes:
            return results  # 전부 캐시 히트

        # 2. 소스별 병렬 수집
        source_tasks = []
        for source in self.sources:
            task = self._collect_from_source(source, uncached_codes)
            source_tasks.append(task)

        # 병렬 실행 (6개 소스 동시)
        source_results = await asyncio.gather(*source_tasks, return_exceptions=True)

        # 3. 결과 병합
        for code in uncached_codes:
            results[code] = self._merge_source_data(code, source_results)

        # 4. 캐시 저장
        await self._save_cache(results)

        return results

    async def _collect_from_source(self, source: Dict, codes: List[str]) -> Dict:
        """단일 소스에서 순차 수집 (Rate Limit 준수)"""
        result = {}
        rate_per_min = source['rate']
        delay = 60 / rate_per_min  # 초 단위 딜레이

        for code in codes:
            try:
                async with self.rate_limiters.get(source['name']):
                    data = await self._fetch_single(source['name'], code)
                    result[code] = data
                    await asyncio.sleep(delay)  # Rate limit 준수
            except Exception as e:
                result[code] = {'error': str(e)}

        return result

    async def _check_cache(self, codes: List[str]) -> Dict:
        """collected_data 테이블에서 최근 데이터 확인"""
        query = """
            SELECT stock_code, data_content, collected_at
            FROM collected_data
            WHERE stock_code = ANY($1)
              AND collected_at >= NOW() - INTERVAL '1 hour'
              AND data_type IN ('news', 'report', 'consensus')
            ORDER BY stock_code, collected_at DESC
        """
        # ... 캐시 로직
```

**시간 계산** (50개 종목, 6개 소스):
- 소스별 Rate: 12~30 calls/min
- 가장 느린 소스: 12/min → 50개 = ~4.2분
- 병렬 실행이므로 **총 ~5분**

### 3.3 수집 데이터 구조

```json
{
  "015760": {
    "code": "015760",
    "name": "한국전력",
    "news": [
      {"title": "정부, 전기요금 인상 계획 발표", "date": "2024-11-27", "sentiment": 0.6},
      {"title": "한전, 3분기 적자 축소", "date": "2024-11-26", "sentiment": 0.8}
    ],
    "reports": [
      {"firm": "미래에셋", "target_price": 25000, "rating": "매수", "date": "2024-11-25"}
    ],
    "consensus": {
      "avg_target_price": 24500,
      "buy_count": 8,
      "hold_count": 2,
      "sell_count": 0
    },
    "policy_keywords": ["전기요금", "에너지", "공공요금"],
    "collected_at": "2024-11-27T15:30:00"
  }
}
```

---

## 4. Phase 2B: AI 분석 (배치 최적화)

### 4.1 배치 프롬프트 전략

**문제**: 50개 종목 × 개별 호출 = 50회 API 호출 → ~5분 (Rate Limit 문제)

**해결**: 5개 종목씩 묶어서 1회 호출 = 10회 API 호출 → ~2분

```python
# smart_value_finder/src/analysis/gemini_batch_analyzer.py
import google.generativeai as genai
from typing import List, Dict

class GeminiBatchAnalyzer:
    """
    Gemini AI를 이용한 배치 분석

    핵심 전략:
    1. 5개 종목씩 묶어서 1회 호출 (토큰 효율화)
    2. 구조화된 JSON 응답 요청
    3. Rate Limit: 6 calls/min 안전 마진
    """

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.batch_size = 5
        self.rate_delay = 10  # 10초 간격 (6/min)

    async def analyze_batch(self, candidates: List[Dict]) -> List[Dict]:
        """
        50개 종목 배치 분석

        Args:
            candidates: 수집 데이터가 포함된 종목 리스트

        Returns:
            AI 분석 결과가 추가된 종목 리스트
        """
        results = []

        # 5개씩 배치로 분할
        batches = [
            candidates[i:i+self.batch_size]
            for i in range(0, len(candidates), self.batch_size)
        ]

        for batch in batches:
            batch_result = await self._analyze_single_batch(batch)
            results.extend(batch_result)
            await asyncio.sleep(self.rate_delay)

        return results

    async def _analyze_single_batch(self, batch: List[Dict]) -> List[Dict]:
        """5개 종목 단일 배치 분석"""
        prompt = self._build_batch_prompt(batch)

        try:
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            return self._parse_batch_response(response.text, batch)
        except Exception as e:
            # 실패 시 개별 결과에 에러 표시
            return [{'code': c['code'], 'ai_error': str(e)} for c in batch]

    def _build_batch_prompt(self, batch: List[Dict]) -> str:
        """배치용 프롬프트 생성"""
        stocks_info = "\n\n".join([
            f"""### 종목 {i+1}: {s['name']} ({s['code']})
**정량 지표:**
- PBR: {s.get('pbr', 'N/A')}, PER: {s.get('per', 'N/A')}
- RSI(14): {s.get('rsi', 'N/A'):.1f}
- 연기금 순매수: {s.get('pension_net_buy', 0):,}원

**최근 뉴스:**
{self._format_news(s.get('news', []))}

**애널리스트 의견:**
{self._format_consensus(s.get('consensus', {}))}
"""
            for i, s in enumerate(batch)
        ])

        return f"""당신은 한국 주식 시장 전문 애널리스트입니다.
아래 5개 종목에 대해 각각 투자 분석을 수행하세요.

{stocks_info}

---
각 종목에 대해 다음 JSON 형식으로 응답하세요:

```json
[
  {{
    "code": "종목코드",
    "grade": "S/A/B/C/D",
    "key_material": "핵심 투자 포인트 1줄",
    "policy_alignment": "정책 관련성 설명 1줄",
    "buy_point": "매수 포인트 1줄",
    "risk": "주요 리스크 1줄",
    "confidence": 0.0-1.0
  }},
  ...
]
```

**등급 기준:**
- S등급: 강력 매수 (정책 수혜 + 실적 턴어라운드 + 저평가)
- A등급: 매수 (2개 이상 조건 충족)
- B등급: 관심 (1개 조건 충족)
- C등급: 중립 (특별한 재료 없음)
- D등급: 관망 (리스크 요인 존재)
"""
```

**시간 계산**:
- 10배치 × 10초 간격 = ~100초
- API 응답 시간 포함 = ~150초
- **총 ~2.5분**

---

## 5. Phase 3: 스코어링 & 저장

### 5.1 최종 점수 계산

```python
# smart_value_finder/src/analysis/scorer.py

class ValueScorer:
    """정량 + 정성 통합 스코어링"""

    def calculate_final_score(self, stock: Dict) -> float:
        """
        최종 점수 계산 (0-100)

        구성:
        - 정량 점수 40%: PBR 깊이, 수급 강도, 기술적 위치
        - 정성 점수 60%: AI 등급, 정책 관련성, 뉴스 센티멘트
        """
        quant_score = self._calculate_quant_score(stock) * 0.4
        qual_score = self._calculate_qual_score(stock) * 0.6

        return quant_score + qual_score

    def _calculate_quant_score(self, stock: Dict) -> float:
        """정량 점수 (0-100)"""
        score = 0

        # PBR 깊이 (0.2 = 40점, 0.5 = 30점, 1.0 = 10점)
        pbr = stock.get('pbr', 1.0)
        score += max(0, 50 - pbr * 40)

        # 수급 강도 (연기금 순매수액 기준)
        pension = stock.get('pension_net_buy', 0)
        if pension > 10_000_000_000:  # 100억 이상
            score += 30
        elif pension > 1_000_000_000:  # 10억 이상
            score += 20
        elif pension > 0:
            score += 10

        # RSI 위치 (40~50 최적)
        rsi = stock.get('rsi', 50)
        if 40 <= rsi <= 50:
            score += 20
        elif 30 <= rsi <= 60:
            score += 10

        return min(100, score)

    def _calculate_qual_score(self, stock: Dict) -> float:
        """정성 점수 (0-100)"""
        ai_grade = stock.get('ai_grade', 'C')
        grade_scores = {'S': 100, 'A': 80, 'B': 60, 'C': 40, 'D': 20}

        ai_score = grade_scores.get(ai_grade, 40)
        confidence = stock.get('ai_confidence', 0.5)

        return ai_score * confidence
```

### 5.2 결과 저장

```sql
-- smart_recommendations 테이블
CREATE TABLE IF NOT EXISTS smart_recommendations (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    recommendation_date DATE NOT NULL DEFAULT CURRENT_DATE,

    -- 정량 데이터
    pbr DECIMAL(5,2),
    per DECIMAL(5,2),
    rsi DECIMAL(5,2),
    pension_net_buy BIGINT,
    quant_score DECIMAL(5,2),

    -- 정성 데이터
    ai_grade CHAR(1),
    ai_confidence DECIMAL(3,2),
    key_material TEXT,
    policy_alignment TEXT,
    buy_point TEXT,
    risk_factor TEXT,
    qual_score DECIMAL(5,2),

    -- 최종 점수
    final_score DECIMAL(5,2),
    rank_in_batch INTEGER,

    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(stock_code, recommendation_date)
);
```

---

## 6. Phase 4: 피드백 루프 (증분 재분석)

### 6.1 피드백 유형별 재실행 범위

| 피드백 유형 | 재실행 Phase | 예상 시간 |
|------------|-------------|----------|
| "이 종목 다시 분석해줘" | Phase 2B만 (AI 재분석) | ~30초 |
| "PBR 기준 0.5로 변경" | Phase 1A부터 | ~5분 |
| "수급 데이터 최신화 필요" | Phase 2A부터 | ~7분 |
| "뉴스 센티멘트 재평가" | Phase 2B만 | ~30초 |
| "전체 다시 돌려줘" | 전체 | ~15분 |

### 6.2 증분 재분석 구현

```python
# smart_value_finder/src/feedback/incremental_runner.py

class IncrementalRunner:
    """
    피드백 기반 증분 재분석

    핵심: 전체 파이프라인 재실행 없이 필요한 Phase만 실행
    """

    async def handle_feedback(self, feedback_type: str, params: Dict) -> Dict:
        """
        피드백 유형에 따라 최소 범위만 재실행

        Args:
            feedback_type: 'reanalyze_stock', 'change_filter', 'refresh_data', 'full'
            params: 피드백 파라미터

        Returns:
            업데이트된 추천 결과
        """
        if feedback_type == 'reanalyze_stock':
            # 특정 종목만 AI 재분석
            return await self._reanalyze_single(params['code'])

        elif feedback_type == 'change_filter':
            # 필터 조건 변경 → Phase 1부터
            return await self._run_from_phase1(params['new_filters'])

        elif feedback_type == 'refresh_data':
            # 데이터 새로고침 → Phase 2A부터
            codes = params.get('codes', self._get_current_candidates())
            return await self._run_from_phase2a(codes)

        elif feedback_type == 'full':
            # 전체 재실행
            return await self._run_full_pipeline()

    async def _reanalyze_single(self, code: str) -> Dict:
        """단일 종목 AI 재분석 (~30초)"""
        # 기존 수집 데이터 로드 (DB)
        collected_data = await self._load_collected_data(code)

        # AI 재분석 (단일 호출)
        ai_result = await self.gemini.analyze_single(collected_data)

        # 점수 재계산
        score = self.scorer.calculate_final_score({**collected_data, **ai_result})

        # DB 업데이트
        await self._update_recommendation(code, ai_result, score)

        return {'code': code, 'updated': True, 'new_score': score}

    async def _run_from_phase2a(self, codes: List[str]) -> Dict:
        """Phase 2A부터 재실행 (~7분)"""
        # 기존 Phase 1 결과 로드
        phase1_results = await self._load_phase1_results(codes)

        # Phase 2A: 데이터 재수집
        collected = await self.batch_collector.collect_all(phase1_results)

        # Phase 2B: AI 분석
        analyzed = await self.gemini.analyze_batch(collected)

        # Phase 3: 스코어링
        scored = await self.scorer.score_all(analyzed)

        return {'updated_count': len(scored), 'top_picks': scored[:10]}
```

---

## 7. 전체 실행 시간 분석

### 7.1 정상 실행 (전체 파이프라인)

| Phase | 작업 | 소요 시간 |
|-------|-----|----------|
| 1A | SQL 1차 필터 | ~1초 |
| 1B | 기술적 지표 계산 | ~30초 |
| 2A | 배치 데이터 수집 | ~5분 |
| 2B | Gemini 배치 분석 | ~2.5분 |
| 3 | 스코어링 & 저장 | ~10초 |
| **Total** | | **~8분 30초** |

### 7.2 피드백 재실행

| 피드백 유형 | 소요 시간 |
|------------|----------|
| 단일 종목 재분석 | ~30초 |
| 필터 조건 변경 | ~8분 |
| 데이터 새로고침 | ~7분 |
| AI 기준만 변경 | ~3분 |

---

## 8. 기존 인프라 활용

### 8.1 재사용 컴포넌트

| 컴포넌트 | 위치 | 활용 방법 |
|---------|------|----------|
| KRXFetcher | tier1_official_libs/ | Phase 1 OHLCV 업데이트 |
| NaverFetcher | tier2_official_apis/ | Phase 2A 뉴스/시세 |
| DaumFetcher | tier2_official_apis/ | Phase 2A 뉴스/리포트 |
| MultiRateLimiter | src/core/ | 전역 Rate Limit 관리 |
| Orchestrator | src/core/ | 배치 실행 로직 참조 |
| collected_data 테이블 | DB | 캐시 저장소 |

### 8.2 신규 개발 필요

| 컴포넌트 | 설명 | 우선순위 |
|---------|------|---------|
| TechnicalFilter | Phase 1B 기술적 지표 | P0 |
| BatchCollector | Phase 2A 병렬 수집 | P0 |
| GeminiBatchAnalyzer | Phase 2B AI 배치 | P0 |
| ValueScorer | Phase 3 스코어링 | P1 |
| IncrementalRunner | Phase 4 피드백 | P1 |

---

## 9. 일정 계획

### Week 1: 코어 파이프라인
- [ ] Phase 1A SQL 쿼리 최적화
- [ ] Phase 1B TechnicalFilter 구현
- [ ] 테스트 데이터로 파이프라인 검증

### Week 2: 데이터 수집 & AI
- [ ] BatchCollector 구현 (Rate Limit 통합)
- [ ] GeminiBatchAnalyzer 구현 (배치 프롬프트)
- [ ] End-to-End 테스트

### Week 3: 스코어링 & 피드백
- [ ] ValueScorer 구현
- [ ] IncrementalRunner 구현
- [ ] 리포트 생성 (PDF/Markdown)

---

## 10. 결론

**기존 설계 대비 개선점:**

| 항목 | 기존 | v2.0 |
|-----|------|------|
| 전체 실행 시간 | 수 시간 | ~10분 |
| 피드백 재분석 | 전체 재실행 | 증분 실행 |
| Rate Limit 대응 | 순차 실행 | 소스별 병렬 |
| AI 호출 효율 | 종목별 개별 | 5개 배치 |
| 캐시 활용 | 없음 | collected_data 재사용 |

**핵심 원칙:**
1. **DB First**: Fetcher 호출 최소화, 기존 수집 데이터 최대 활용
2. **Batch is Better**: 개별 호출 → 배치 호출
3. **Parallel by Source**: 소스 간 병렬, 소스 내 순차
4. **Incremental Update**: 전체 재실행 → 증분 재분석
