# 신규종목추천 추적 대시보드 가이드

## 📋 개요

이 가이드는 신규종목추천 시스템의 **성과 추적** 및 **사후 분석** 기능을 설명합니다.
매일 주가를 추적하고, 실패한 추천의 원인을 분석하여 시스템을 개선합니다.

---

## 🗂️ 폴더 구조

```
reports/new_stock/
├── daily/           # 일일 PDF 추천 리포트
│   └── 신규종목추천_YYYY-MM-DD_HHMM.pdf
├── tracking/        # 추적 대시보드 (마크다운)
│   └── 추적현황_YYYY-MM-DD_HHMM.md
├── archive/         # 성과 분석 리포트
│   └── 성과분석_YYYY-MM-DD_HHMM.md
└── charts/          # 차트 이미지 (향후 확장)
```

---

## 🚀 사용법

### 전체 실행 (권장)
```bash
# 모든 단계 실행: 일일 추적 → 기간별 추적 → AI 회고 → 리포트 생성
python 신규종목추천/run_phase4.py
```

### 개별 실행
```bash
# 일일 주가 추적만 (매일 실행 권장)
python 신규종목추천/run_phase4.py --daily

# 기간별 수익률 추적 (7/14/30일)
python 신규종목추천/run_phase4.py --track-only

# AI 회고 분석 (실패 종목 분석)
python 신규종목추천/run_phase4.py --retrospective-only --limit 10

# 추적 대시보드 생성
python 신규종목추천/run_phase4.py --dashboard

# PDF 리포트 생성
python 신규종목추천/run_phase4.py --pdf

# 전체 성과 분석 리포트
python 신규종목추천/run_phase4.py --report
```

---

## 📊 생성되는 리포트

### 1. PDF 추천 리포트 (`daily/`)
- **용도**: 일일 신규 추천 종목 확인
- **내용**:
  - Top 10 추천 종목 요약
  - A등급 이상 종목 상세 분석
  - 주가 추적 테이블 (수기 기록용)
  - 등급 분포

### 2. 추적 대시보드 (`tracking/`)
- **용도**: 매일 주가 확인 및 성과 추적
- **내용**:
  - 등급별 현황 (종목수, 평균 수익률, 승률)
  - 종목별 추적 현황 (추천가 → 현재가 → 수익률)
  - 수익률 분포 통계
  - ⚠️ 주의 필요 종목 (손실 -5% 이상)

### 3. 성과 분석 리포트 (`archive/`)
- **용도**: 사후 분석 및 시스템 개선
- **내용**:
  - 기간별 성과 요약 (7일/14일/30일)
  - AI 회고 분석 결과 (놓친 리스크, 실제 원인, 학습 교훈)
  - 분석 체크리스트

---

## 📈 분석 항목

### 1. 놓친 리스크 (Missed Risks)
AI가 추천 당시 간과했던 위험 요인들:
- 업황 악화 가능성
- 경쟁사 동향
- 규제 리스크
- 수급 불안정성

### 2. 실제 원인 (Actual Cause)
주가 하락의 실제 원인:
- 실적 발표 부진
- 대외 악재 (환율, 금리, 지정학)
- 내부 악재 (경영진 이슈, 소송)
- 시장 전체 하락

### 3. 학습 교훈 (Lesson Learned)
이 실패에서 배운 점:
- 특정 업종/테마의 리스크 패턴
- 밸류에이션 함정
- 타이밍 이슈

### 4. 개선 제안 (Improvement Suggestion)
향후 분석 개선점:
- 필터 조건 조정
- AI 프롬프트 개선
- 리스크 평가 강화

---

## 📋 일일 체크리스트

### 매일 (장 마감 후)
```bash
# 1. 일일 주가 추적
python 신규종목추천/run_phase4.py --daily

# 2. 대시보드 확인
open reports/new_stock/tracking/추적현황_*.md
```

### 매주 (주말)
```bash
# 1. 전체 성과 분석
python 신규종목추천/run_phase4.py

# 2. AI 회고 결과 확인
open reports/new_stock/archive/성과분석_*.md

# 3. 개선점 검토
```

---

## 🔍 추적 대시보드 예시

```markdown
# 신규종목 추적 대시보드

**추천일**: 2025-11-27
**배치 ID**: 20251127_1530

## 📊 등급별 현황

| 등급 | 종목수 | 평균 수익률 | 승률 |
|:---:|:---:|:---:|:---:|
| S | 3 | +5.23% | 100.0% |
| A | 12 | +2.45% | 75.0% |
| B | 18 | +0.32% | 55.6% |
| C | 10 | -1.87% | 40.0% |
| D | 5 | -4.12% | 20.0% |

## 📈 종목별 추적 현황

| 순위 | 종목명 | 등급 | 추천가 | 현재가 | 수익률 | 경과일 |
|:---:|:---|:---:|---:|---:|---:|:---:|
| 1 | 한국자산신탁 | S | 4,500 | 4,950 | 🟢 +10.00% | 7일 |
| 2 | HL만도 | A | 45,000 | 48,500 | 🟢 +7.78% | 7일 |
| 3 | 한국전력 | B | 22,000 | 20,500 | 🔴 -6.82% | 7일 |

## ⚠️ 주의 필요 종목 (손실 -5% 이상)

### 한국전력 (015760)
- **등급**: B | **점수**: 65.2
- **추천가**: 22,000원 → **현재가**: 20,500원 (-6.82%)
- **핵심재료**: 전력 요금 인상 기대
- **리스크 요인**: 정책 불확실성
- **분석 필요**: 놓친 리스크, 실제 원인 확인 필요
```

---

## 🤖 AI 회고 예시

```markdown
## 한국전력 (015760) 회고 분석

### 추천 당시 분석
- **등급**: B
- **핵심재료**: 전력 요금 인상 기대, 적자 축소 전망
- **리스크 요인**: 정책 불확실성

### 회고 결과
- **놓친 리스크**: 요금 인상 결정의 정치적 민감성을 과소평가.
  국회 및 여론의 반발로 인상 폭이 제한될 가능성.
- **실제 원인**: 정부의 요금 인상 유보 발표로 투자 심리 급랭.
  외국인 대규모 매도세 발생.
- **학습 교훈**: 정책 관련주는 정책 '발표'와 '실현' 사이의 괴리를
  항상 고려해야 함. 정치적 변수에 취약한 업종은 신중한 접근 필요.
- **개선 제안**: 정책 관련 종목은 정책 실현 가능성 평가를 강화하고,
  정치 일정(선거 등)과의 연관성을 분석에 포함할 것.
- **신뢰도 조정**: -3 (정책 관련주 전반에 적용)
```

---

## ⚙️ 데이터베이스 테이블

### smart_price_tracking
일일 주가 추적 기록

```sql
CREATE TABLE smart_price_tracking (
    id SERIAL PRIMARY KEY,
    recommendation_id INTEGER,  -- smart_recommendations.id 참조
    stock_code VARCHAR(10),
    stock_name VARCHAR(100),
    rec_date DATE,              -- 추천일
    rec_price INTEGER,          -- 추천가
    rec_grade CHAR(1),          -- AI 등급
    track_date DATE,            -- 추적일
    track_price INTEGER,        -- 현재가
    return_rate NUMERIC(8,2),   -- 수익률 (%)
    days_held INTEGER,          -- 경과일
    UNIQUE(recommendation_id, track_date)
);
```

### smart_ai_retrospective
AI 회고 분석 결과

```sql
CREATE TABLE smart_ai_retrospective (
    id SERIAL PRIMARY KEY,
    performance_id INTEGER,
    recommendation_id INTEGER,
    stock_code VARCHAR(10),
    stock_name VARCHAR(100),
    rec_date DATE,
    rec_grade CHAR(1),
    rec_score NUMERIC(6,2),
    original_key_material TEXT,   -- 당시 핵심 재료
    original_risk_factor TEXT,    -- 당시 리스크 요인
    actual_return NUMERIC(8,2),   -- 실제 수익률
    max_drawdown NUMERIC(8,2),    -- 최대 손실률

    -- AI 회고 분석 결과
    missed_risks TEXT,            -- 놓친 리스크
    actual_cause TEXT,            -- 실제 하락 원인
    lesson_learned TEXT,          -- 학습된 교훈
    improvement_suggestion TEXT,  -- 개선 제안
    confidence_adjustment NUMERIC(4,2),  -- 신뢰도 조정

    analyzed_at TIMESTAMP DEFAULT NOW()
);
```

---

## 📝 수동 분석 가이드

### 실패 종목 분석 순서

1. **대시보드에서 주의 종목 확인**
   - 손실률 -5% 이상 종목 리스트

2. **뉴스 검색**
   - 네이버 금융에서 해당 종목 뉴스 확인
   - 추천일 이후 악재성 뉴스 파악

3. **차트 분석**
   - 급락 시점과 원인 이벤트 매칭
   - 거래량 패턴 확인

4. **AI 회고 실행**
   ```bash
   python 신규종목추천/run_phase4.py --retrospective-only --limit 5
   ```

5. **교훈 정리**
   - 놓친 리스크 기록
   - 향후 필터 조건 개선점 정리

---

## 🔄 시스템 개선 사이클

```
추천 생성 (Phase 1-3)
    ↓
일일 주가 추적 (Phase 4A)
    ↓
기간별 성과 측정 (7/14/30일)
    ↓
실패 종목 AI 회고 (Phase 4B)
    ↓
공통 패턴 추출
    ↓
필터/AI 개선 → 추천 생성 (반복)
```

---

## ⚠️ 주의사항

1. **데이터 지연**: OHLCV 데이터 수집 후 추적 실행 권장
2. **API 제한**: AI 회고 시 Gemini API 호출 간격 준수 (2초)
3. **성과 해석**: 단기 성과만으로 판단하지 말고 장기 추이 확인

---

**Last Updated**: 2025-11-27
**Version**: 1.0
