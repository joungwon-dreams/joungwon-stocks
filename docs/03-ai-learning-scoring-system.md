---
created: 2025-11-24 11:29:49
updated: 2025-11-24 11:29:49
tags: [ai, machine-learning, scoring, weighting, data-sources]
author: wonny
status: critical
priority: highest
---

# AI 학습 및 점수화 시스템 설계

> 다중 데이터 소스 통합, 수치화, 역추적, 동적 가중치 조정 시스템

## 🎯 핵심 개념

### 시스템 목표

```yaml
문제:
  - 41개 사이트에서 수집한 데이터의 신뢰도가 다름
  - 어떤 소스가 정확한지 사전에 알 수 없음
  - 시간이 지나면서 신뢰도가 변할 수 있음

해결:
  - 모든 데이터를 0-100 점수로 수치화
  - AI 판단 결과를 역추적하여 정확도 측정
  - 정확한 소스에 높은 가중치 부여
  - 가중치를 지속적으로 업데이트 (학습)

결과:
  - 시간이 지날수록 더 정확한 예측
  - 잘못된 정보의 영향력 자동 감소
  - 종목별 맞춤형 가중치 (삼성전자는 차트 중요, 바이오는 뉴스 중요 등)
```

---

## 📊 데이터 소스 분류

### 1. 기본 데이터 (필수)

| 소스 | 테이블 | 점수 범위 | 가중치 초기값 |
|------|--------|-----------|---------------|
| **가격** | `min_ticks`, `daily_ohlcv` | 0-100 | 20% |
| **거래량** | `min_ticks` | 0-100 | 15% |
| **수급** | `stock_supply_demand` | 0-100 | 30% |
| **차트** | `stock_prices_10min` | 0-100 | 35% |

**합계**: 100%

### 2. 확장 데이터 (추가 분석)

| 소스 | 수집 방법 | 점수 범위 | 초기 가중치 |
|------|-----------|-----------|-------------|
| **증권사 리포트** | Tier 3 Web Scraping | 0-100 | 0.7 |
| **연기금 매매** | `stock_supply_demand` | 0-100 | 0.9 |
| **뉴스 감성** | Tier 3 News + Gemini | 0-100 | 0.5 |
| **국민연금 공시** | Tier 3 DART | 0-100 | 0.8 |
| **외국인 수급** | `stock_supply_demand` | 0-100 | 0.85 |

**가중치**: 0.0 ~ 1.0 (신뢰도 점수)

---

## 🏗️ 시스템 아키텍처

### 전체 흐름

```
┌─────────────────────────────────────────────────────┐
│  1. 데이터 수집 (41개 소스)                         │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│  2. 데이터 정규화 (0-100 점수화)                    │
│     - 가격: 이평선 대비 위치                        │
│     - 거래량: 평균 대비 비율                        │
│     - 수급: 순매수 강도                             │
│     - 차트: RSI, MACD 신호                          │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│  3. 가중치 적용 (소스별 신뢰도 반영)                │
│     총점 = Σ(점수 × 가중치)                         │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│  4. AI 판단 (Gemini + 총점)                         │
│     → 매수/매도/관망 결정                           │
│     → recommendation_history 저장                   │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│  5. 역추적 (7일 후)                                 │
│     실제 가격 변동 vs AI 예측 비교                  │
│     → verification_results 저장                     │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│  6. 가중치 업데이트                                 │
│     정확도 → 가중치 증가                            │
│     오차 → 가중치 감소                              │
│     → data_sources.reliability_score 업데이트       │
└─────────────────────────────────────────────────────┘
```

---

## 📐 점수화 시스템 (0-100)

### 1. 가격 점수 (Price Score)

**목적**: 현재가가 이평선 대비 어느 위치에 있는지

```python
def calculate_price_score(current_price: int, ma5: int, ma20: int, ma60: int) -> float:
    """
    가격 점수 계산 (0-100)

    기준:
    - 100점: 60일 이평선 > 20일 이평선 > 5일 이평선 > 현재가 (정배열)
    - 50점: 이평선 혼조
    - 0점: 현재가 < 5일 이평선 < 20일 이평선 < 60일 이평선 (역배열)
    """
    # 정배열 체크
    if ma5 > ma20 > ma60:
        # 현재가가 5일선 위: 70-100점
        if current_price >= ma5:
            position = (current_price - ma5) / (ma5 * 0.05)  # 5% 위까지
            return min(70 + position * 30, 100)
        # 현재가가 5일선 아래: 50-70점
        else:
            position = (current_price - ma20) / (ma5 - ma20)
            return 50 + position * 20

    # 역배열
    elif ma5 < ma20 < ma60:
        # 현재가가 5일선 아래: 0-30점
        if current_price <= ma5:
            position = (ma5 - current_price) / (ma5 * 0.05)
            return max(30 - position * 30, 0)
        # 현재가가 5일선 위: 30-50점
        else:
            position = (current_price - ma5) / (ma20 - ma5)
            return 30 + position * 20

    # 혼조
    else:
        return 50
```

### 2. 거래량 점수 (Volume Score)

**목적**: 거래량 증가 여부 (관심도 증가 = 상승 가능성)

```python
def calculate_volume_score(current_volume: int, avg_volume_5d: int, avg_volume_20d: int) -> float:
    """
    거래량 점수 (0-100)

    기준:
    - 100점: 평균의 3배 이상 (급등 전조)
    - 70점: 평균의 2배 (관심 증가)
    - 50점: 평균 수준
    - 30점: 평균의 50% (관심 저하)
    - 0점: 평균의 30% 이하 (거래 부진)
    """
    ratio_5d = current_volume / avg_volume_5d if avg_volume_5d > 0 else 0
    ratio_20d = current_volume / avg_volume_20d if avg_volume_20d > 0 else 0

    # 평균 비율
    avg_ratio = (ratio_5d + ratio_20d) / 2

    if avg_ratio >= 3.0:
        return 100
    elif avg_ratio >= 2.0:
        return 70 + (avg_ratio - 2.0) * 30
    elif avg_ratio >= 1.0:
        return 50 + (avg_ratio - 1.0) * 20
    elif avg_ratio >= 0.5:
        return 30 + (avg_ratio - 0.5) * 40
    else:
        return max(avg_ratio * 100, 0)
```

### 3. 수급 점수 (Supply/Demand Score)

**목적**: 외국인/기관/개인 매매 동향

```python
def calculate_supply_score(
    foreigner_net: int,
    institution_net: int,
    individual_net: int,
    avg_trading_value: int
) -> float:
    """
    수급 점수 (0-100)

    기준:
    - 외국인 + 기관 = 스마트머니 (가중치 높음)
    - 개인 = 대중심리 (가중치 낮음)

    100점: 스마트머니 강한 순매수
    50점: 중립
    0점: 스마트머니 강한 순매도
    """
    # 스마트머니 (외국인 60% + 기관 40%)
    smart_money = (foreigner_net * 0.6 + institution_net * 0.4)

    # 거래대금 대비 비율
    if avg_trading_value > 0:
        smart_ratio = smart_money / avg_trading_value
    else:
        smart_ratio = 0

    # 점수 계산 (±10% 기준)
    if smart_ratio >= 0.10:  # +10% 이상 순매수
        return 100
    elif smart_ratio >= 0.05:  # +5% 이상
        return 70 + (smart_ratio - 0.05) * 600
    elif smart_ratio >= 0:  # 0~5%
        return 50 + (smart_ratio) * 400
    elif smart_ratio >= -0.05:  # 0~-5%
        return 30 + (smart_ratio + 0.05) * 400
    elif smart_ratio >= -0.10:  # -5~-10%
        return (smart_ratio + 0.10) * 600
    else:  # -10% 이하
        return 0
```

### 4. 차트 점수 (Technical Score)

**목적**: RSI, MACD 등 기술적 지표 종합

```python
def calculate_chart_score(
    rsi: float,
    macd: float,
    macd_signal: float,
    bb_position: float
) -> float:
    """
    차트 점수 (0-100)

    기준:
    - RSI: 30 이하 과매도(매수), 70 이상 과매수(매도)
    - MACD: 골든크로스(매수), 데드크로스(매도)
    - 볼린저밴드: 하단 근접(매수), 상단 근접(매도)
    """
    score = 50  # 기본 중립

    # 1. RSI 점수 (±20점)
    if rsi <= 30:
        score += 20  # 과매도 → 매수 신호
    elif rsi <= 40:
        score += 10
    elif rsi >= 70:
        score -= 20  # 과매수 → 매도 신호
    elif rsi >= 60:
        score -= 10

    # 2. MACD 점수 (±15점)
    macd_diff = macd - macd_signal
    if macd_diff > 0:  # 골든크로스
        score += min(macd_diff * 100, 15)
    else:  # 데드크로스
        score += max(macd_diff * 100, -15)

    # 3. 볼린저밴드 점수 (±15점)
    if bb_position <= 20:  # 하단 근접
        score += 15
    elif bb_position <= 40:
        score += 7
    elif bb_position >= 80:  # 상단 근접
        score -= 15
    elif bb_position >= 60:
        score -= 7

    return max(min(score, 100), 0)
```

### 5. 뉴스 감성 점수 (News Sentiment Score)

**목적**: Gemini AI 뉴스 감성 분석

```python
def calculate_news_score(news_list: List[Dict]) -> float:
    """
    뉴스 감성 점수 (0-100)

    기준:
    - 긍정 뉴스: +1점
    - 중립 뉴스: 0점
    - 부정 뉴스: -1점

    최근 7일 뉴스 평균
    """
    if not news_list:
        return 50  # 뉴스 없으면 중립

    sentiment_map = {
        'positive': 1,
        'neutral': 0,
        'negative': -1
    }

    total_score = sum(sentiment_map.get(news['sentiment'], 0) for news in news_list)
    avg_score = total_score / len(news_list)

    # -1 ~ +1 → 0 ~ 100
    return (avg_score + 1) * 50
```

### 6. 증권사 리포트 점수 (Analyst Report Score)

**목적**: 증권사 애널리스트 의견 (목표가, 투자의견)

```python
def calculate_analyst_score(reports: List[Dict], current_price: int) -> float:
    """
    증권사 리포트 점수 (0-100)

    기준:
    - 목표가 > 현재가: 상승 여력
    - 투자의견: 매수(100), 보유(50), 매도(0)
    """
    if not reports:
        return 50

    opinion_map = {
        'buy': 100,
        'hold': 50,
        'sell': 0
    }

    scores = []
    for report in reports:
        # 투자의견 점수
        opinion_score = opinion_map.get(report.get('opinion', 'hold'), 50)

        # 목표가 점수
        target_price = report.get('target_price', current_price)
        upside = ((target_price - current_price) / current_price) * 100
        target_score = 50 + min(max(upside, -50), 50)  # ±50% 범위

        # 평균
        scores.append((opinion_score + target_score) / 2)

    return sum(scores) / len(scores)
```

---

## ⚖️ 가중치 시스템

### 1. 데이터 소스별 가중치 (data_sources 테이블)

```sql
-- data_sources 테이블 구조
CREATE TABLE data_sources (
    source_id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) UNIQUE,        -- 예: '삼성증권_리포트', 'Gemini_뉴스'
    source_type VARCHAR(20),                -- nps, realtime, report, technical, theme, ai
    reliability_score DECIMAL(3,2),         -- 0.0 ~ 1.0 (신뢰도)
    total_recommendations INTEGER,          -- 총 추천 수
    correct_predictions INTEGER,            -- 적중 수
    average_error_rate DECIMAL(10,2),       -- 평균 오차율 (%)
    last_updated TIMESTAMP
);

-- 초기 데이터 예시
INSERT INTO data_sources (source_name, source_type, reliability_score) VALUES
('가격_이평선', 'technical', 0.70),
('거래량', 'technical', 0.60),
('외국인_수급', 'realtime', 0.85),
('기관_수급', 'realtime', 0.75),
('RSI_MACD', 'technical', 0.80),
('삼성증권_리포트', 'report', 0.65),
('미래에셋_리포트', 'report', 0.70),
('국민연금_공시', 'nps', 0.90),
('네이버_뉴스_Gemini', 'ai', 0.50),
('이데일리_뉴스_Gemini', 'ai', 0.55);
```

### 2. 종목별 가중치 (stock_score_weights 테이블)

```sql
-- stock_score_weights 테이블 구조
CREATE TABLE stock_score_weights (
    stock_code VARCHAR(6) PRIMARY KEY,

    -- 기본 가중치 (합계 100%)
    price_weight DECIMAL(5,2) DEFAULT 20.0,     -- 가격 가중치
    volume_weight DECIMAL(5,2) DEFAULT 15.0,    -- 거래량 가중치
    supply_weight DECIMAL(5,2) DEFAULT 30.0,    -- 수급 가중치
    chart_weight DECIMAL(5,2) DEFAULT 35.0,     -- 차트 가중치

    -- 확장 가중치 (개별 소스별 신뢰도 승수)
    news_weight DECIMAL(5,2) DEFAULT 1.0,       -- 뉴스 영향력
    analyst_weight DECIMAL(5,2) DEFAULT 1.0,    -- 애널리스트 영향력

    -- 메타 정보
    accuracy_score DECIMAL(5,2) DEFAULT 50.0,   -- 전체 예측 정확도
    sample_count INTEGER DEFAULT 0,             -- 학습 샘플 수
    last_updated TIMESTAMP
);

-- 종목별 특성 예시
INSERT INTO stock_score_weights (stock_code, price_weight, volume_weight, supply_weight, chart_weight) VALUES
('005930', 25.0, 10.0, 40.0, 25.0),  -- 삼성전자: 수급 중요 (외국인 비중 높음)
('000660', 20.0, 20.0, 35.0, 25.0),  -- SK하이닉스: 거래량 중요
('035420', 15.0, 15.0, 30.0, 40.0),  -- NAVER: 차트 중요 (기술적 분석)
('207940', 10.0, 10.0, 20.0, 60.0);  -- 삼성바이오: 차트 + 뉴스 중요 (바이오)
```

### 3. 총점 계산 알고리즘

```python
async def calculate_total_score(stock_code: str) -> Dict:
    """
    종목 총점 계산

    Returns:
        {
            'total_score': 0-100,
            'breakdown': {
                'price_score': 0-100,
                'volume_score': 0-100,
                'supply_score': 0-100,
                'chart_score': 0-100,
                'news_score': 0-100,
                'analyst_score': 0-100
            },
            'weights': {...},
            'signal': '강력매수' | '분할매수' | '관망' | '매도'
        }
    """
    conn = await asyncpg.connect(**db_config)

    # 1. 종목별 가중치 조회
    weights = await conn.fetchrow("""
        SELECT * FROM stock_score_weights WHERE stock_code = $1
    """, stock_code)

    if not weights:
        # 기본 가중치 사용
        weights = {
            'price_weight': 20.0,
            'volume_weight': 15.0,
            'supply_weight': 30.0,
            'chart_weight': 35.0,
            'news_weight': 1.0,
            'analyst_weight': 1.0
        }

    # 2. 각 점수 계산
    price_score = await calculate_price_score_from_db(stock_code)
    volume_score = await calculate_volume_score_from_db(stock_code)
    supply_score = await calculate_supply_score_from_db(stock_code)
    chart_score = await calculate_chart_score_from_db(stock_code)

    # 3. 확장 점수 (소스별 신뢰도 적용)
    news_score = await calculate_news_score_from_db(stock_code)
    analyst_score = await calculate_analyst_score_from_db(stock_code)

    # 뉴스 신뢰도 조회
    news_reliability = await conn.fetchval("""
        SELECT AVG(reliability_score)
        FROM data_sources
        WHERE source_type = 'ai' AND source_name LIKE '%뉴스%'
    """)

    # 애널리스트 신뢰도 조회
    analyst_reliability = await conn.fetchval("""
        SELECT AVG(reliability_score)
        FROM data_sources
        WHERE source_type = 'report'
    """)

    # 4. 가중 평균 계산
    base_score = (
        price_score * weights['price_weight'] +
        volume_score * weights['volume_weight'] +
        supply_score * weights['supply_weight'] +
        chart_score * weights['chart_weight']
    ) / 100  # 가중치 합계 100%

    # 확장 점수 반영 (신뢰도 곱하기)
    extended_score = (
        news_score * news_reliability * weights['news_weight'] +
        analyst_score * analyst_reliability * weights['analyst_weight']
    ) / 2  # 평균

    # 최종 점수 (base 80% + extended 20%)
    total_score = base_score * 0.8 + extended_score * 0.2

    # 5. 매매 신호 판단
    if total_score >= 80:
        signal = '강력매수'
    elif total_score >= 65:
        signal = '분할매수'
    elif total_score >= 45:
        signal = '관망'
    else:
        signal = '매도'

    await conn.close()

    return {
        'total_score': total_score,
        'breakdown': {
            'price_score': price_score,
            'volume_score': volume_score,
            'supply_score': supply_score,
            'chart_score': chart_score,
            'news_score': news_score,
            'analyst_score': analyst_score
        },
        'weights': weights,
        'signal': signal
    }
```

---

## 🔄 역추적 및 학습 시스템

### 1. 추천 기록 (recommendation_history)

```python
async def save_recommendation(stock_code: str, total_score: float, signal: str):
    """
    AI 추천 기록 저장
    """
    conn = await asyncpg.connect(**db_config)

    # 현재가 조회
    current_price = await conn.fetchval("""
        SELECT price FROM stock_assets WHERE code = $1
    """, stock_code)

    # 추천 기록 저장
    rec_id = await conn.fetchval("""
        INSERT INTO recommendation_history (
            stock_code, stock_name, recommendation_date,
            recommended_price, recommendation_type, source_id,
            gemini_reasoning, note
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING rec_id
    """,
        stock_code,
        await get_stock_name(stock_code),
        datetime.now().date(),
        current_price,
        'buy' if signal in ['강력매수', '분할매수'] else 'hold',
        1,  # AI source_id
        f"총점: {total_score:.2f}, 신호: {signal}",
        f"가격:{current_price}, 날짜:{datetime.now()}"
    )

    await conn.close()
    return rec_id
```

### 2. 역추적 검증 (7일 후)

```python
async def verify_recommendations():
    """
    7일 전 추천을 검증하고 정확도 측정
    """
    conn = await asyncpg.connect(**db_config)

    # 7일 전 추천 조회
    recommendations = await conn.fetch("""
        SELECT * FROM recommendation_history
        WHERE recommendation_date = CURRENT_DATE - INTERVAL '7 days'
          AND recommendation_type = 'buy'
    """)

    for rec in recommendations:
        # 현재가 조회
        current_price = await conn.fetchval("""
            SELECT price FROM stock_assets WHERE code = $1
        """, rec['stock_code'])

        # 가격 변동 계산
        price_change = current_price - rec['recommended_price']
        price_change_rate = (price_change / rec['recommended_price']) * 100

        # 예측 적중 여부
        # 매수 추천 → 가격 상승(+5% 이상) = 적중
        prediction_correct = price_change_rate >= 5.0

        # 검증 결과 저장
        await conn.execute("""
            INSERT INTO verification_results (
                rec_id, verification_date, actual_price,
                price_change, price_change_rate, prediction_correct, days_elapsed
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
            rec['rec_id'],
            datetime.now().date(),
            current_price,
            price_change,
            price_change_rate,
            prediction_correct,
            7
        )

        # 가중치 업데이트
        await update_weights_after_verification(
            rec['stock_code'],
            rec['source_id'],
            prediction_correct,
            price_change_rate
        )

    await conn.close()
```

### 3. 가중치 업데이트 알고리즘

```python
async def update_weights_after_verification(
    stock_code: str,
    source_id: int,
    prediction_correct: bool,
    price_change_rate: float
):
    """
    검증 결과에 따라 가중치 업데이트

    원리:
    - 적중 → 가중치 증가 (최대 1.0)
    - 오차 → 가중치 감소 (최소 0.1)
    - 변화량은 오차 크기에 비례
    """
    conn = await asyncpg.connect(**db_config)

    # 1. 데이터 소스 신뢰도 업데이트
    current_reliability = await conn.fetchval("""
        SELECT reliability_score FROM data_sources WHERE source_id = $1
    """, source_id)

    if prediction_correct:
        # 적중: +0.05 증가 (최대 1.0)
        delta = 0.05 * (1 + abs(price_change_rate) / 100)  # 큰 수익일수록 더 증가
        new_reliability = min(current_reliability + delta, 1.0)
    else:
        # 오차: -0.05 감소 (최소 0.1)
        delta = 0.05 * (1 + abs(price_change_rate) / 100)  # 큰 손실일수록 더 감소
        new_reliability = max(current_reliability - delta, 0.1)

    await conn.execute("""
        UPDATE data_sources
        SET reliability_score = $1,
            total_recommendations = total_recommendations + 1,
            correct_predictions = correct_predictions + $2,
            average_error_rate = (
                (average_error_rate * total_recommendations + $3) /
                (total_recommendations + 1)
            ),
            last_updated = CURRENT_TIMESTAMP
        WHERE source_id = $4
    """, new_reliability, 1 if prediction_correct else 0, abs(price_change_rate), source_id)

    # 2. 종목별 가중치 업데이트 (어떤 요소가 중요했는지)
    # 예: 수급이 맞았으면 수급 가중치 증가
    weights = await conn.fetchrow("""
        SELECT * FROM stock_score_weights WHERE stock_code = $1
    """, stock_code)

    # 이번 추천에서 가장 높은 점수를 준 요소 파악
    breakdown = await get_score_breakdown(stock_code)  # 각 요소별 점수
    max_score_element = max(breakdown, key=breakdown.get)

    if prediction_correct:
        # 해당 요소 가중치 +2% 증가
        if max_score_element == 'supply_score':
            new_supply_weight = min(weights['supply_weight'] + 2.0, 50.0)
            await conn.execute("""
                UPDATE stock_score_weights
                SET supply_weight = $1, last_updated = CURRENT_TIMESTAMP
                WHERE stock_code = $2
            """, new_supply_weight, stock_code)
        # 다른 요소들도 유사하게 처리...

    await conn.close()
```

### 4. 자동 학습 스케줄러

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def start_learning_scheduler():
    """
    자동 학습 스케줄러
    - 매일 장 마감 후 (오후 4시) 7일 전 추천 검증
    """
    scheduler = AsyncIOScheduler()

    # 매일 오후 4시 실행
    scheduler.add_job(
        verify_recommendations,
        'cron',
        hour=16,
        minute=0,
        timezone='Asia/Seoul'
    )

    scheduler.start()
    print("✅ 자동 학습 스케줄러 시작 (매일 16:00)")
```

---

## 📊 통합 분석 파이프라인

### 전체 프로세스

```python
class IntegratedAnalysisPipeline:
    """통합 분석 파이프라인"""

    def __init__(self):
        self.conn = None

    async def connect(self):
        self.conn = await asyncpg.connect(**db_config)

    async def analyze_stock(self, stock_code: str) -> Dict:
        """
        종목 통합 분석

        Returns:
            {
                'stock_code': '005930',
                'stock_name': '삼성전자',
                'total_score': 75.5,
                'signal': '분할매수',
                'breakdown': {...},
                'recommendation': '...',
                'timestamp': '2025-11-24 11:30:00'
            }
        """
        # 1. 데이터 수집 (최신 데이터)
        price_data = await self._get_price_data(stock_code)
        volume_data = await self._get_volume_data(stock_code)
        supply_data = await self._get_supply_data(stock_code)
        chart_data = await self._get_chart_data(stock_code)
        news_data = await self._get_news_data(stock_code)
        analyst_data = await self._get_analyst_data(stock_code)

        # 2. 점수 계산
        price_score = calculate_price_score(**price_data)
        volume_score = calculate_volume_score(**volume_data)
        supply_score = calculate_supply_score(**supply_data)
        chart_score = calculate_chart_score(**chart_data)
        news_score = calculate_news_score(news_data)
        analyst_score = calculate_analyst_score(analyst_data, price_data['current_price'])

        # 3. 가중치 적용 및 총점 계산
        result = await calculate_total_score(stock_code)

        # 4. Gemini AI 최종 판단
        gemini_recommendation = await self._get_gemini_recommendation(
            stock_code,
            result['total_score'],
            result['breakdown']
        )

        # 5. 추천 기록 저장
        rec_id = await save_recommendation(
            stock_code,
            result['total_score'],
            result['signal']
        )

        # 6. stock_score_history에 저장
        await self._save_score_history(stock_code, result)

        return {
            'stock_code': stock_code,
            'stock_name': await self._get_stock_name(stock_code),
            'total_score': result['total_score'],
            'signal': result['signal'],
            'breakdown': result['breakdown'],
            'recommendation': gemini_recommendation,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    async def _get_gemini_recommendation(
        self,
        stock_code: str,
        total_score: float,
        breakdown: Dict
    ) -> str:
        """
        Gemini AI 최종 판단
        """
        prompt = f"""
다음 종목에 대한 최종 매매 의견을 제시하세요.

종목코드: {stock_code}
총점: {total_score:.2f}/100

세부 점수:
- 가격: {breakdown['price_score']:.2f}
- 거래량: {breakdown['volume_score']:.2f}
- 수급: {breakdown['supply_score']:.2f}
- 차트: {breakdown['chart_score']:.2f}
- 뉴스: {breakdown['news_score']:.2f}
- 애널리스트: {breakdown['analyst_score']:.2f}

의견 (매수/매도/관망 중 선택):
근거 (200자 이내, 핵심만):
"""

        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text

    async def analyze_all_holdings(self) -> List[Dict]:
        """
        전체 보유종목 분석
        """
        holdings = await self.conn.fetch("""
            SELECT code FROM stock_assets WHERE quantity > 0
        """)

        results = []
        for holding in holdings:
            result = await self.analyze_stock(holding['code'])
            results.append(result)

        return results
```

---

## 📈 실전 적용 예시

### 삼성전자(005930) 분석 시뮬레이션

```python
# 1. 데이터 수집 (2025-11-24 11:30)
data = {
    'price': {
        'current': 65000,
        'ma5': 64500,
        'ma20': 63000,
        'ma60': 61000
    },
    'volume': {
        'current': 15000000,
        'avg_5d': 12000000,
        'avg_20d': 10000000
    },
    'supply': {
        'foreigner': +500000000,  # 5억 순매수
        'institution': +300000000,  # 3억 순매수
        'individual': -800000000   # 8억 순매도
    },
    'chart': {
        'rsi': 45,
        'macd': 0.5,
        'macd_signal': 0.3,
        'bb_position': 55
    }
}

# 2. 점수 계산
price_score = calculate_price_score(65000, 64500, 63000, 61000)
# → 85점 (정배열 + 5일선 위)

volume_score = calculate_volume_score(15000000, 12000000, 10000000)
# → 70점 (평균의 1.4배)

supply_score = calculate_supply_score(500000000, 300000000, -800000000, 5000000000)
# → 75점 (스마트머니 순매수)

chart_score = calculate_chart_score(45, 0.5, 0.3, 55)
# → 60점 (중립 + 골든크로스)

# 3. 가중치 적용 (삼성전자 가중치)
weights = {
    'price': 25%,
    'volume': 10%,
    'supply': 40%,  # 외국인 비중 높음
    'chart': 25%
}

total_score = (85 * 0.25) + (70 * 0.10) + (75 * 0.40) + (60 * 0.25)
            = 21.25 + 7.0 + 30.0 + 15.0
            = 73.25

# 4. 신호 판단
signal = '분할매수'  # 65~80점

# 5. 추천 기록 저장
recommendation_history에 저장

# 6. 7일 후 검증 (2025-12-01)
actual_price = 67000  # +3.08%
prediction_correct = False  # 5% 미달

# 7. 가중치 업데이트
supply_weight: 40% → 38% (-2%)  # 수급이 틀렸음
chart_weight: 25% → 27% (+2%)   # 차트가 더 정확했음
```

---

## 🎯 구현 우선순위

### Phase 1 (Week 1-2) - 점수화 시스템

```yaml
Priority: P1

Tasks:
  1. 점수 계산 함수 구현 (6개)
     - calculate_price_score()
     - calculate_volume_score()
     - calculate_supply_score()
     - calculate_chart_score()
     - calculate_news_score()
     - calculate_analyst_score()

  2. 총점 계산 함수
     - calculate_total_score()

  3. 테스트
     - 단위 테스트 (각 함수별)
     - 통합 테스트 (전체 파이프라인)

Deliverables:
  - src/scoring/price_scorer.py
  - src/scoring/volume_scorer.py
  - src/scoring/supply_scorer.py
  - src/scoring/chart_scorer.py
  - src/scoring/news_scorer.py
  - src/scoring/analyst_scorer.py
  - src/scoring/total_scorer.py

Estimated Time: 7-10 days
```

### Phase 2 (Week 3-4) - 역추적 및 학습

```yaml
Priority: P2

Tasks:
  1. 추천 기록 시스템
     - save_recommendation()

  2. 역추적 검증
     - verify_recommendations()

  3. 가중치 업데이트
     - update_weights_after_verification()

  4. 자동 스케줄러
     - start_learning_scheduler()

Deliverables:
  - src/learning/recommendation_saver.py
  - src/learning/verifier.py
  - src/learning/weight_updater.py
  - src/learning/scheduler.py

Estimated Time: 7-10 days
```

### Phase 3 (Week 5-6) - 통합 파이프라인

```yaml
Priority: P3

Tasks:
  1. 통합 분석 파이프라인
     - IntegratedAnalysisPipeline 클래스

  2. Gemini 최종 판단
     - _get_gemini_recommendation()

  3. 대시보드 (선택)
     - Grafana 대시보드
     - 점수 추이 차트

Deliverables:
  - src/pipelines/integrated_analysis.py
  - src/ai/gemini_final_judgment.py
  - monitoring/grafana_dashboard.json (선택)

Estimated Time: 7-10 days
```

---

## 📦 의존성 추가

```txt
# requirements.txt에 추가

# 수치 계산
numpy==1.24.0
scipy==1.11.0

# 기계 학습 (가중치 최적화)
scikit-learn==1.3.0

# 통계 분석
statsmodels==0.14.0
```

---

## ✅ 성공 지표

### 1개월 후 목표

```yaml
정확도:
  - AI 추천 적중률 60% 이상
  - 평균 수익률 +3% 이상

학습:
  - 가중치 자동 조정 100회 이상
  - 소스별 신뢰도 0.3 ~ 0.95 범위 분포

성능:
  - 1종목 분석 시간 < 3초
  - 10종목 동시 분석 < 10초
```

---

**작성일**: 2025-11-24 11:29:49
**작성자**: wonny
**버전**: 1.0
**상태**: Critical - Highest Priority
**다음 단계**: Phase 1 점수화 시스템 구현
