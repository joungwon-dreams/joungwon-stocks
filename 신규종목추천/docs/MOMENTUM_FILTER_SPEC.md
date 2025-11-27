# 모멘텀 필터 기술 명세

## 📋 개요

기존의 "저평가 가치주(Deep Value)" 위주 필터에서 **"시세 초입 종목"**을 포착할 수 있도록
모멘텀 기반 필터를 추가했습니다.

### 변경 배경
- **문제점**: PBR < 0.5, PER < 10 조건은 "언제 오를지 모르는 잠자는 종목"을 많이 선정
- **밸류 트랩**: 저평가된 데에는 이유가 있는 종목들이 상위권 차지
- **해결책**: 가치투자(Value) + 모멘텀(Momentum) 결합 전략

```
기존: 싼 주식 찾기 → "언젠가 오를 주식"
개선: 싸면서 움직이기 시작한 주식 → "지금 오를 명분이 생긴 주식"
```

---

## 🔧 Phase 1A 설정 변경

### config/settings.py

```python
@dataclass
class Phase1AConfig:
    # 밸류에이션 필터 (완화: 모멘텀 종목 포함)
    pbr_min: float = 0.1
    pbr_max: float = 1.5      # 0.5 → 1.5 (성장주 포함)
    per_min: float = 1.0
    per_max: float = 20.0     # 15 → 20 (적정 성장성)

    # 유동성 필터
    min_volume: int = 50_000  # 최소 5만주
    min_market_cap: int = 50_000_000_000  # 최소 500억

    # 거래대금 필터
    min_trading_value: int = 5_000_000_000  # 최소 50억원

    # 시장 필터
    include_kosdaq: bool = False  # 코스닥 제외 (KOSPI만)

    # 결과 제한
    max_candidates: int = 300  # 200 → 300 (풀 확대)
```

### 변경 효과
| 항목 | 기존 | 변경 | 효과 |
|:---|:---:|:---:|:---|
| PBR 상한 | 0.5 | **1.5** | 성장주 포함 가능 |
| PER 상한 | 15 | **20** | 적정 성장성 종목 포함 |
| KOSDAQ | 포함 | **제외** | 대형주 집중, 안정성 확보 |
| 후보 수 | 200 | **300** | 모멘텀 필터용 풀 확대 |

---

## 🚀 Phase 1B 모멘텀 필터

### 3가지 핵심 지표

#### 1. 거래량 활력 (Volume Dynamics) - 30점
```python
# 거래량 급증 (5일 평균 대비)
volume_surge_ratio = current_volume / volume_ma_5

# 점수 배분
if volume_surge_ratio >= 3.0:   +20점  # 3배 이상 폭발
elif volume_surge_ratio >= 2.0: +15점  # 2배 이상 급증
elif volume_surge_ratio >= 1.5: +10점  # 1.5배 이상 증가

# 거래대금
if trading_value >= 10억원:     +10점
elif trading_value >= 5억원:    +5점
```

#### 2. 추세 돌파 (Trend & Breakout) - 40점
```python
# 정배열 (Moving Average Alignment)
ma_alignment = (current_price > ma_5) and (ma_5 > ma_20)
if ma_alignment: +15점

# 52주 고가 대비
high_52w_ratio = current_price / high_52w
if high_52w_ratio >= 0.95: +15점   # 52주 고가 근접
elif high_52w_ratio >= 0.85: +10점

# 20일 신고가 돌파
if current_price > high_20d: +10점
```

#### 3. 변동성 (Volatility) - 30점
```python
# 일중 변동폭
intraday_range = ((high - low) / open) * 100
if intraday_range >= 5.0%: +10점
elif intraday_range >= 3.0%: +5점

# 5일 평균 변동폭
avg_5d_range = average(daily_ranges[-5:])
if avg_5d_range >= 3.0%: +10점
elif avg_5d_range >= 2.0%: +5점

# 장대양봉 (3일 내 +3% 이상 양봉)
if has_bullish_candle_3days: +5점

# 3일 상승률
price_change_3d = ((close[-1] - close[-4]) / close[-4]) * 100
if price_change_3d >= 5.0%: +5점
```

### 종합 점수 계산

```python
# 정량 점수 (기존)
quant_score = calculate_quant_score(pbr, per, rsi, pension_buy, ...)

# 모멘텀 점수 (신규)
momentum_score = calculate_momentum_score(
    volume_surge_ratio,
    trading_value,
    ma_alignment,
    high_52w_ratio,
    breakout_20d,
    intraday_range,
    has_bullish_candle,
    price_change_3d
)

# 총점: 정량 40% + 모멘텀 60%
total_score = quant_score * 0.4 + momentum_score * 0.6
```

---

## 🤖 Phase 2B AI 프롬프트 변경

### 모멘텀 지표 제공
```python
stock_info = f"""
**🚀 모멘텀 지표:**
- 거래량 급증: {vol_surge:.1f}배 (5일 평균 대비)
- 거래대금: {trading_val / 100_000_000:.0f}억원
- 이평선: {ma_aligned} (주가 > 5일선 > 20일선)
- 52주 고가 대비: {high_52w * 100:.1f}%
- 20일 신고가: {breakout}
- 장대양봉(3%+): {bullish}
- 3일 상승률: {price_chg_3d:.1f}%
- 모멘텀 점수: {momentum_score}점
"""
```

### AI 등급 기준 개정

```markdown
**S등급 (강력 매수) - [필수] 기술적 돌파 + 다음 중 2개 이상:**
- [필수] 거래량 급증(2배↑) 또는 20일 신고가 돌파 또는 정배열 상태
- 명확한 실적 개선/신사업 재료
- 정책 수혜 (정부 정책, 규제 완화)
- 기관/외국인 대규모 순매수

**A등급 (매수 유망) - [필수] 기술적 지표 긍정적 + 다음 중 1개 이상:**
- [필수] 정배열 또는 52주 고가 85% 이상
- 저평가(PBR<0.5 또는 PER<8) + 움직임 시작
- 배당/자사주 매입 등 주주환원 정책

**⚠️ 핵심 원칙 (시세 초입 포착):**
1. 저평가만으로는 S등급 불가! 반드시 '움직이기 시작한 징후'가 있어야 함
2. 거래량 급증 + 정배열 = 시세 초입의 강력한 신호
3. 52주 고가 근접 = 저항대 돌파 가능성 시사
4. 역배열 종목은 아무리 저평가라도 C등급 이하!
```

---

## 📊 결과 비교

### 기존 결과 (저평가 위주)
| 순위 | 종목 | 특징 |
|:---:|:---|:---|
| 1 | 세아홀딩스 | PBR 0.21, 철강 업황 부진 |
| 2 | 삼천리 | PBR 0.26, 가스 사업 성숙기 |
| 3 | KISCO홀딩스 | PBR 0.28, 주주환원 기대 |

**문제**: 모두 "움직임 없는 소외주"

### 변경 후 결과 (모멘텀 포함)
| 순위 | 종목 | 특징 |
|:---:|:---|:---|
| 1 | 한국자산신탁 | 재건축 수주 + RSI 79 |
| 2 | 제이에스코퍼레이션 | 주주환원 + 정배열 |
| 3 | HL만도 | 로봇 사업 진출 + 거래량 증가 |

**개선**: "움직이기 시작한 종목" 포착

---

## 🔄 백테스팅 권장

변경된 필터의 효과를 검증하기 위해 다음 백테스팅을 권장합니다:

```python
# 백테스팅 시나리오
periods = ['2024-Q1', '2024-Q2', '2024-Q3', '2024-Q4']

for period in periods:
    # 1. 기존 필터로 추천 종목 선정
    old_picks = run_old_filter(period)

    # 2. 새 필터로 추천 종목 선정
    new_picks = run_new_filter(period)

    # 3. 7일, 14일, 30일 수익률 비교
    compare_returns(old_picks, new_picks, [7, 14, 30])
```

---

## ⚠️ 리스크 및 주의사항

### 1. 고점 매수 위험
- 거래량이 터지고 주가가 이미 5~10% 오른 상태에서 포착될 수 있음
- **대응**: RSI 80 이하 조건으로 과매수 필터링

### 2. 거짓 신호 (False Signal)
- 단발성 루머나 일시적 뉴스로 거래량 급증 후 재급락
- **대응**: Phase 2B AI 분석에서 재료의 지속성 평가

### 3. 테마 편중
- 핫한 테마(AI, 로봇 등)에 종목이 쏠릴 수 있음
- **대응**: 섹터 분산 권장 (수동 검토)

---

## 📁 관련 파일

```
신규종목추천/
├── config/
│   └── settings.py              # Phase1A, Phase1B 설정
├── src/
│   ├── phase1/
│   │   ├── filter_phase1a.py    # 시장 필터 (KOSPI만)
│   │   └── filter_phase1b.py    # 모멘텀 지표 계산
│   └── phase2/
│       └── gemini_analyzer.py   # AI 프롬프트 개정
└── docs/
    └── MOMENTUM_FILTER_SPEC.md  # 이 문서
```

---

**Last Updated**: 2025-11-27
**Version**: 1.0
**Author**: AI Stock Recommendation System
