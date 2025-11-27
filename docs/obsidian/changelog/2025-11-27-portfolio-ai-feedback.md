---
created: 2025-11-27 17:50:04
updated: 2025-11-27 17:50:04
tags: [changelog, feature, ai, portfolio, feedback]
author: wonny
status: active
---

# 2025-11-27 Portfolio AI Feedback 시스템 구축

## 작업 요약

보유종목에 대한 AI 피드백 시스템을 구축하여 매일 투자 판단을 제시하고 다음날 검증하는 기능을 추가했습니다.

---

## 1. 데이터베이스 스키마 생성

### 생성 파일
`sql/11_create_portfolio_feedback.sql`

### portfolio_ai_history 테이블
| 컬럼 | 타입 | 설명 |
|:---|:---|:---|
| id | SERIAL | PK |
| stock_code | VARCHAR(6) | 종목코드 |
| report_date | DATE | 판단일 |
| my_avg_price | DECIMAL(15,2) | 내 평단가 |
| market_price | DECIMAL(15,2) | 당시 시장가 |
| return_rate | DECIMAL(5,2) | 수익률 |
| recommendation | VARCHAR(20) | AI 추천 |
| rationale | TEXT | 판단 이유 |
| confidence | DECIMAL(3,2) | 신뢰도 |
| is_verified | BOOLEAN | 검증 완료 |
| next_day_price | DECIMAL(15,2) | 다음날 종가 |
| next_day_return | DECIMAL(5,2) | 다음날 수익률 |
| was_correct | BOOLEAN | 적중 여부 |

---

## 2. PortfolioAdvisor 클래스 구현

### 생성 파일
`scripts/gemini/components/portfolio_advisor.py`

### 주요 기능
- `get_yesterday_advice()`: 어제 판단 조회
- `verify_yesterday_advice()`: 오늘 가격으로 검증
- `generate_strategy()`: Gemini AI 전략 생성
- `save_decision()`: DB 저장
- `process_daily_feedback()`: 전체 프로세스

### 추천 타입
| 추천 | 한글 | 조건 |
|:---|:---|:---|
| BUY_MORE | 추가 매수 | 저평가, 수급 양호 |
| HOLD | 관망 | 추세 불분명 |
| SELL | 일부 매도 | 고점, 차익실현 |
| CUT_LOSS | 손절 | 하락 추세 |

---

## 3. PDF 통합

### 수정 파일
`scripts/gemini/generate_pdf_report.py`

### 변경 내용
1. **PortfolioAdvisor import 추가** (라인 39)
2. **AI 피드백 데이터 수집** (fetch_all_data 메서드)
   - 보유종목인 경우 자동 피드백 생성
   - 수급 데이터, 뉴스 요약 전달
3. **PDF 섹션 추가** (2페이지, 2-Week Trend 다음)
   - 오늘의 전략 박스 (색상 코딩)
   - 어제 회고 박스 (있는 경우)

### PDF 출력 예시
```
🤖 AI Portfolio Feedback

[오늘의 전략: 관망] ⚪
수급이 불안정하고 추세가 불분명합니다.
추가 매수나 매도보다는 관망을 권장합니다.
신뢰도: ███████░░░ 70%

[어제 회고 (11.26)] ✅
어제 의견: 관망
어제 종가: 21,500원 → 오늘 종가: 21,450원 (-0.23%)
판정: ✅ 적중
AI 코멘트: 예상대로 변동폭이 작았습니다.
```

---

## 4. 검증 로직

### 검증 주기
**1일** (어제 판단 → 오늘 검증)

### 적중 기준
| 추천 | 적중 조건 |
|:---|:---|
| BUY_MORE | 오늘 상승 (return > 0) |
| SELL/CUT_LOSS | 오늘 하락 (return < 0) |
| HOLD | 변동폭 ±1% 이내 |

---

## 5. 테스트 결과

### 테스트 명령
```bash
python scripts/gemini/generate_pdf_report.py 015760
```

### 결과
```
✅ AI Feedback generated: HOLD
✅ PDF saved: reports/한국전력.pdf
```

---

## 생성된 파일 목록

| 파일 | 타입 | 설명 |
|:---|:---|:---|
| sql/11_create_portfolio_feedback.sql | SQL | DB 스키마 |
| scripts/gemini/components/portfolio_advisor.py | Python | 어드바이저 클래스 |
| docs/obsidian/features/portfolio-ai-feedback.md | Docs | 기능 문서 |
| docs/obsidian/changelog/2025-11-27-portfolio-ai-feedback.md | Docs | 변경 이력 |

## 수정된 파일 목록

| 파일 | 변경 내용 |
|:---|:---|
| scripts/gemini/generate_pdf_report.py | PortfolioAdvisor 통합 |
| docs/PORTFOLIO_FEEDBACK_SPEC.md | 검증 주기 7일→1일 변경 |

---

## 관련 문서

- [[portfolio-ai-feedback]] - 기능 상세 문서
- [[PORTFOLIO_FEEDBACK_SPEC]] - 스펙 문서
- [[new-stock-recommendation-scheduler]] - 자동화 스케줄러

---

*작성일: 2025-11-27 17:50:04*
