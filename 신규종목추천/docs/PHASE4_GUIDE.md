# Phase 4: 성과 추적 및 AI 회고 가이드

## 📋 개요

Phase 4는 신규종목추천 시스템의 **사후 검증 및 학습** 단계입니다.
추천 종목의 실제 수익률을 추적하고, 실패한 추천에서 AI가 스스로 학습하여
향후 분석 정확도를 높입니다.

```
Phase 1-3: 추천 생성
    ↓
Phase 4A: 수익률 추적 (7일, 14일, 30일)
    ↓
Phase 4B: AI 회고 (실패 원인 분석)
    ↓
피드백 루프 → Phase 1-3 개선
```

---

## 🎯 주요 기능

### Phase 4A: 수익률 추적기 (ProfitTracker)

추천 후 일정 기간이 지난 종목의 실제 수익률을 측정합니다.

#### 추적 기간
- **7일 (1주)**: 단기 모멘텀 검증
- **14일 (2주)**: 중기 추세 확인
- **30일 (1개월)**: 테마/재료 지속성 검증

#### 측정 지표
| 지표 | 설명 |
|:---|:---|
| `return_rate` | 추천가 대비 현재가 수익률 (%) |
| `max_profit` | 보유 기간 중 최대 수익률 (%) |
| `max_drawdown` | 보유 기간 중 최대 손실률 (%) |
| `status` | 상태 (success/active/warning/failed) |

#### 상태 분류
```python
if return_rate >= 10%:   status = 'success'   # 성공
elif return_rate >= 0%:  status = 'active'    # 보합/소폭 수익
elif return_rate >= -5%: status = 'warning'   # 소폭 손실
else:                    status = 'failed'    # 실패 (-5% 이하)
```

---

### Phase 4B: AI 회고 (AIRetrospective)

`failed` 상태(-5% 이하 손실) 종목에 대해 Gemini AI가 자동으로 회고 분석을 수행합니다.

#### 분석 내용
1. **놓친 리스크** (`missed_risks`): 당시 분석에서 간과한 위험 요인
2. **실제 원인** (`actual_cause`): 주가 하락의 실제 원인
3. **학습 교훈** (`lesson_learned`): 이 실패에서 배운 점
4. **개선 제안** (`improvement_suggestion`): 향후 분석 개선점
5. **신뢰도 조정** (`confidence_adjustment`): 해당 패턴에 대한 신뢰도 조정 (-10 ~ +10)

#### 회고 프로세스
```
1. smart_performance에서 failed 종목 조회
2. 추천 당시 AI 분석 결과 로드
3. 추천 이후 관련 뉴스/악재 수집
4. Gemini에 회고 프롬프트 전달
5. AI 응답 파싱 및 smart_ai_retrospective에 저장
6. 공통 패턴 추출 및 학습
```

---

## 🗄️ 데이터베이스 스키마

### smart_performance
수익률 추적 결과 저장

```sql
CREATE TABLE smart_performance (
    id SERIAL PRIMARY KEY,
    recommendation_id INTEGER REFERENCES smart_recommendations(id),
    stock_code VARCHAR(10) NOT NULL,
    rec_date DATE NOT NULL,
    rec_price INTEGER NOT NULL,
    rec_grade CHAR(1),
    rec_score NUMERIC(6,2),
    check_date DATE NOT NULL,
    check_price INTEGER NOT NULL,
    return_rate NUMERIC(8,2),      -- 수익률 (%)
    max_profit NUMERIC(8,2),       -- 최대 수익
    max_drawdown NUMERIC(8,2),     -- 최대 손실
    status VARCHAR(20),            -- success/active/warning/failed
    days_held INTEGER,             -- 보유 일수 (7, 14, 30)
    created_at TIMESTAMP DEFAULT NOW()
);
```

### smart_ai_retrospective
AI 회고 분석 결과 저장

```sql
CREATE TABLE smart_ai_retrospective (
    id SERIAL PRIMARY KEY,
    performance_id INTEGER REFERENCES smart_performance(id),
    recommendation_id INTEGER REFERENCES smart_recommendations(id),
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100),
    rec_date DATE NOT NULL,
    rec_grade CHAR(1),
    rec_score NUMERIC(6,2),
    original_key_material TEXT,    -- 당시 핵심 재료
    original_risk_factor TEXT,     -- 당시 리스크 요인
    actual_return NUMERIC(8,2),    -- 실제 수익률
    max_drawdown NUMERIC(8,2),     -- 최대 손실률
    days_held INTEGER,

    -- AI 회고 분석 결과
    missed_risks TEXT,             -- 놓친 리스크
    actual_cause TEXT,             -- 실제 하락 원인
    lesson_learned TEXT,           -- 학습된 교훈
    improvement_suggestion TEXT,   -- 개선 제안
    confidence_adjustment NUMERIC(4,2),  -- 신뢰도 조정 (-10 ~ +10)

    ai_raw_response JSONB,
    analyzed_at TIMESTAMP DEFAULT NOW(),
    model_used VARCHAR(50) DEFAULT 'gemini-2.0-flash'
);
```

---

## 💻 사용법

### 명령줄 실행

```bash
# 가상환경 활성화
source venv/bin/activate

# 전체 실행 (수익률 추적 + AI 회고 + 리포트)
python 신규종목추천/run_phase4.py

# 수익률 추적만
python 신규종목추천/run_phase4.py --track-only

# AI 회고만 (최대 5건)
python 신규종목추천/run_phase4.py --retrospective-only --limit 5

# 리포트 생성만
python 신규종목추천/run_phase4.py --report
```

### Python 코드에서 사용

```python
import asyncio
from 신규종목추천.src.phase4 import ProfitTracker, AIRetrospective
from 신규종목추천.src.utils.database import db

async def main():
    await db.connect()

    # 수익률 추적
    tracker = ProfitTracker()
    results = await tracker.track_all()
    print(f"추적: {results['total_tracked']}건")

    # AI 회고
    retrospective = AIRetrospective()
    retro_results = await retrospective.analyze_failures(limit=10)
    print(f"회고: {retro_results['analyzed_count']}건")

    # 실패 종목 직접 조회
    failed = await tracker.get_failed_recommendations(threshold=-5.0)
    for f in failed:
        print(f"{f['stock_name']}: {f['return_rate']}%")

    await db.disconnect()

asyncio.run(main())
```

---

## 📊 출력 예시

### 수익률 추적 결과
```
=== Phase 4: 수익률 추적 시작 ===
[7일] 2025-11-20 추천 종목 수익률 추적 중...
[7일] 48개 종목 추적 대상
  - 한국자산신탁: +8.5% (active)
  - HL만도: +12.3% (success)
  - 한국전력: -7.2% (failed)
[7일] 48개 종목 추적 완료

📊 기간별 요약:
  7d: 48건, 평균 +2.34%, 승률 62.5%
  14d: 35건, 평균 +4.12%, 승률 68.6%
  30d: 22건, 평균 +6.78%, 승률 72.7%
```

### AI 회고 결과
```
=== AI 회고 분석 시작 (최대 5건) ===
  - 한국전력: 회고 완료
    놓친 리스크: 전력 요금 인상 지연에 따른 실적 악화 가능성
    실제 원인: 정책 불확실성으로 인한 투자 심리 악화
    교훈: 정책 관련주는 정책 실현 가능성을 더 엄격히 평가해야 함
    신뢰도 조정: -3

공통 교훈:
  - 총 실패: 5건
  - 평균 손실: -8.3%
  - 자주 놓친 리스크: [('정책', 3), ('유동성', 2), ('변동성', 2)]
```

---

## 🔄 피드백 루프

Phase 4에서 수집된 데이터는 Phase 1-3 개선에 활용됩니다:

### 1. 등급별 성과 분석
```sql
-- AI 등급별 실제 성과 비교
SELECT ai_grade,
       AVG(return_rate) as avg_return,
       COUNT(CASE WHEN return_rate > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate
FROM smart_performance sp
JOIN smart_recommendations sr ON sp.recommendation_id = sr.id
WHERE days_held = 7
GROUP BY ai_grade
ORDER BY ai_grade;
```

### 2. 신뢰도 조정 적용 (향후 개선)
- AI 회고에서 도출된 `confidence_adjustment`를 해당 패턴에 적용
- 자주 실패하는 유형의 종목은 자동으로 신뢰도 하향

### 3. 공통 실패 패턴 학습
- `common_missed_risks`에서 반복되는 키워드를 Phase 2B 프롬프트에 추가
- 예: "정책 관련주는 정책 실현 가능성을 반드시 평가할 것"

---

## ⚙️ 설정

### config/settings.py

```python
@dataclass
class Phase4Config:
    """Phase 4: 성과 추적 설정"""
    # 추적 기간
    tracking_periods: List[int] = field(default_factory=lambda: [7, 14, 30])

    # 실패 기준
    failure_threshold: float = -5.0  # -5% 이하 손실

    # AI 회고 설정
    max_retrospective_per_run: int = 10
    retrospective_delay_seconds: int = 2  # API 호출 간격
```

---

## 📁 파일 구조

```
신규종목추천/
├── src/
│   └── phase4/
│       ├── __init__.py           # 모듈 초기화
│       ├── profit_tracker.py     # 수익률 추적기
│       ├── retrospective.py      # AI 회고 분석기
│       └── feedback_runner.py    # 증분 재분석 (기존)
├── sql/
│   └── create_smart_feedback.sql # 테이블 생성 SQL
├── run_phase4.py                 # 통합 실행 스크립트
└── docs/
    └── PHASE4_GUIDE.md           # 이 문서
```

---

## 📈 모니터링

### 일일 체크리스트
- [ ] 7일 전 추천 종목 수익률 확인
- [ ] 실패 종목(-5% 이하) 개수 모니터링
- [ ] AI 회고 분석 실행
- [ ] 등급별 승률 확인

### 주간 리뷰
- [ ] 기간별 평균 수익률 추이
- [ ] 공통 실패 패턴 분석
- [ ] Phase 1-3 설정 조정 검토

---

## 🚨 주의사항

1. **데이터 지연**: 수익률 추적은 OHLCV 데이터 업데이트 이후 실행 권장
2. **API Rate Limit**: AI 회고 시 Gemini API 호출 간격 준수 (2초)
3. **성과 해석**: 단기(7일) 성과와 장기(30일) 성과를 종합적으로 평가

---

**Last Updated**: 2025-11-27
**Version**: 1.0
