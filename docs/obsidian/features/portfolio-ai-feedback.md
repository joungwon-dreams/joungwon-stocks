---
created: 2025-11-27 17:50:04
updated: 2025-11-27 17:50:04
tags: [feature, ai, portfolio, feedback, gemini, pdf]
author: wonny
status: active
---

# Portfolio AI Feedback System (보유종목 AI 피드백)

## 개요

보유종목에 대해 AI가 매일 투자 판단(BUY_MORE/HOLD/SELL/CUT_LOSS)을 제시하고, 다음날 결과로 검증하는 시스템입니다.

## 핵심 기능

### 1. 일일 투자 전략 (오늘의 전략)
- AI가 평단가 대비 현재가, 수급, 뉴스를 분석
- **BUY_MORE** (추가 매수): 저평가 구간, 수급 양호
- **HOLD** (관망): 추세 불분명
- **SELL** (일부 매도): 고점 근처, 차익실현
- **CUT_LOSS** (손절): 하락 추세 지속

### 2. 일일 회고 (어제 회고)
- 어제 AI 판단을 오늘 결과로 검증
- **검증 주기: 1일** (어제 → 오늘)
- 검증 로직:
  - BUY_MORE → 오늘 상승 = ✅
  - SELL/CUT_LOSS → 오늘 하락 = ✅
  - HOLD → ±1% 이내 = ✅

## 데이터베이스

### portfolio_ai_history 테이블
```sql
CREATE TABLE portfolio_ai_history (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL,
    report_date DATE DEFAULT CURRENT_DATE,

    -- Snapshot
    my_avg_price DECIMAL(15,2),
    market_price DECIMAL(15,2),
    return_rate DECIMAL(5,2),

    -- AI Output
    recommendation VARCHAR(20),  -- BUY_MORE, HOLD, SELL, CUT_LOSS
    rationale TEXT,
    confidence DECIMAL(3,2),     -- 0.0 ~ 1.0

    -- Verification (다음날)
    is_verified BOOLEAN DEFAULT FALSE,
    next_day_price DECIMAL(15,2),
    next_day_return DECIMAL(5,2),
    was_correct BOOLEAN,

    created_at TIMESTAMP DEFAULT NOW(),
    verified_at TIMESTAMP,
    UNIQUE(stock_code, report_date)
);
```

## 컴포넌트

### PortfolioAdvisor 클래스
**경로**: `scripts/gemini/components/portfolio_advisor.py`

주요 메서드:
- `get_yesterday_advice()`: 어제 AI 판단 조회
- `verify_yesterday_advice()`: 어제 판단을 오늘 가격으로 검증
- `generate_strategy()`: Gemini AI로 오늘 전략 생성
- `save_decision()`: 오늘 판단 DB 저장
- `process_daily_feedback()`: 전체 프로세스 실행

## PDF 통합

### 위치
종목명.pdf → 2페이지 → "Recent 2-Week Trend" 다음

### 표시 내용
1. **오늘의 전략 박스**
   - 추천 (색상 코딩)
   - 판단 이유
   - 신뢰도 바

2. **어제 회고 박스** (있는 경우)
   - 어제 의견
   - 가격 변화
   - 적중 여부
   - AI 코멘트

## 사용 방법

### PDF 생성 시 자동 실행
```bash
python scripts/gemini/generate_pdf_report.py 015760
```

### 단독 테스트
```python
from scripts.gemini.components.portfolio_advisor import PortfolioAdvisor

advisor = PortfolioAdvisor()
result = await advisor.process_daily_feedback(
    stock_code='015760',
    stock_name='한국전력',
    avg_buy_price=22000,
    current_price=21500,
    investor_data={'foreign_5d': -50000, 'institutional_5d': 30000},
    news_summary='전기요금 인상 논의 중'
)
```

## 데이터 흐름

```
[PDF 생성 시작]
      ↓
[fetch_all_data()]
      ↓
[PortfolioAdvisor.process_daily_feedback()]
      ↓
  1. 어제 판단 조회 (is_verified=FALSE)
  2. 오늘 가격으로 검증 → DB 업데이트
  3. Gemini AI로 오늘 전략 생성
  4. 오늘 판단 DB 저장
      ↓
[generate_pdf()]
      ↓
[AI Portfolio Feedback 섹션 렌더링]
```

## 주의사항

1. **Gemini API 필요**: `GEMINI_API_KEY` 환경변수 필수
2. **보유종목만**: `stock_assets` 테이블에 있는 종목만 피드백 생성
3. **평단가 필수**: `avg_buy_price`가 있어야 분석 가능
4. **Rate Limit**: Gemini API 요청 제한 주의

## 관련 문서

- [[PORTFOLIO_FEEDBACK_SPEC]] - 상세 스펙 문서
- [[generate-pdf-report]] - PDF 생성기 문서
- [[new-stock-recommendation-scheduler]] - 자동화 스케줄러

---

*작성일: 2025-11-27 17:50:04*
