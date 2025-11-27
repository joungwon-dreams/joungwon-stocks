# 신규종목추천 시스템

AI 기반 한국 주식 신규 투자 종목 발굴 시스템

---

## Quick Start (원라인 실행)

```bash
# 데이터 수집 + 추천 실행 (한 줄)
python scripts/collect_fundamentals_pykrx.py && python scripts/collect_ohlcv_fdr.py && python 신규종목추천/run.py
```

또는 테스트 모드:
```bash
python 신규종목추천/run.py --test
```

---

## 환경 변수 설정

### .env.example

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stock_investment_db
DB_USER=wonny
DB_PASSWORD=

# Gemini AI API
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Slack 알림
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz

# Optional: 한국투자증권 API (자동매매용)
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret
KIS_ACCOUNT_NO=your_account_number
```

### 환경 변수 설정 방법

```bash
# 1. .env 파일 생성
cp .env.example .env

# 2. .env 파일 편집
nano .env

# 3. 또는 직접 export
export GEMINI_API_KEY=your_key_here
```

---

## 디렉토리 구조

```
신규종목추천/
├── README.md                 # 이 파일
├── run.py                    # 메인 실행 스크립트
├── config/
│   ├── __init__.py
│   └── settings.py           # 전역 설정
└── src/
    ├── __init__.py
    ├── utils/
    │   ├── __init__.py
    │   └── database.py       # DB 연결 관리
    ├── phase1/
    │   ├── __init__.py
    │   ├── filter_phase1a.py # SQL 기반 1차 필터
    │   └── filter_phase1b.py # 기술적 지표 필터
    ├── phase2/
    │   ├── __init__.py
    │   ├── batch_collector.py # 뉴스/리포트 수집
    │   └── gemini_analyzer.py # Gemini AI 분석
    ├── phase3/
    │   ├── __init__.py
    │   └── scorer.py          # 스코어링 & 리포트
    └── phase4/
        ├── __init__.py
        └── feedback_runner.py # 피드백 루프 (미구현)
```

---

## 빠른 시작

### 1. 사전 데이터 수집

```bash
# PBR/PER 데이터
python scripts/collect_fundamentals_pykrx.py

# OHLCV 데이터
python scripts/collect_ohlcv_fdr.py
```

### 2. 실행

```bash
# 전체 파이프라인
python 신규종목추천/run.py

# 테스트 모드 (5개 종목)
python 신규종목추천/run.py --test
```

### 3. 결과 확인

```bash
# 리포트 확인
cat reports/new_stock/추천종목_YYYY-MM-DD_HHMM.md
```

---

## 파일별 설명

### run.py

메인 실행 스크립트. 4단계 파이프라인을 순차 실행합니다.

```python
# 주요 함수
async def main(test_mode: bool, skip_ai: bool):
    # Phase 1A → 1B → 2A → 2B → 3 순차 실행
```

**CLI 옵션**:
- `--test`: 5개 종목만 분석
- `--skip-ai`: AI 분석 스킵 (정량 점수만)

### config/settings.py

전역 설정을 dataclass로 관리합니다.

```python
@dataclass
class Settings:
    db: DatabaseConfig          # DB 연결
    phase1a: Phase1AConfig      # Phase 1A 필터
    phase1b: Phase1BConfig      # Phase 1B 필터
    phase2a: Phase2AConfig      # 데이터 수집
    phase2b: Phase2BConfig      # AI 분석
    phase3: Phase3Config        # 스코어링

settings = Settings()  # 전역 인스턴스
```

### src/utils/database.py

asyncpg 기반 DB 연결 풀 관리.

```python
class Database:
    async def connect()      # 연결 풀 생성
    async def disconnect()   # 연결 풀 종료
    async def execute()      # 쿼리 실행
    async def fetch()        # SELECT 결과 반환
    async def fetchval()     # 단일 값 반환

db = Database()  # 전역 인스턴스
```

### src/phase1/filter_phase1a.py

SQL 기반 1차 필터. 밸류에이션 기준으로 후보 선정.

```python
class Phase1AFilter:
    async def filter(batch_id: str) -> List[Dict]:
        # PBR, PER, 거래량, 시총 조건으로 필터링
        # 보유 종목 제외
        # 200개 반환
```

**필터 조건**:
- PBR: 0.1 ~ 3.0
- PER: 1.0 ~ 30.0
- 거래량: > 10,000
- 보유 종목: 제외

### src/phase1/filter_phase1b.py

기술적 지표 필터. RSI, 이격도 계산 및 정량 점수 산출.

```python
class Phase1BFilter:
    async def filter(candidates, batch_id) -> List[Dict]:
        # OHLCV 로드
        # RSI(14) 계산
        # 이격도(20일, 60일) 계산
        # 정량 점수 산출
        # 100개 반환

    def _calculate_rsi(prices, period=14) -> float
    def _calculate_disparity(close, ma) -> float
    def _calculate_quant_score(stock) -> float
```

**정량 점수 구성**:
- PBR 점수: 30%
- PER 점수: 30%
- RSI 점수: 20%
- 이격도 점수: 20%

### src/phase2/batch_collector.py

뉴스, 리포트, 컨센서스 데이터 배치 수집.

```python
class BatchCollector:
    async def collect_all(candidates) -> Dict[str, CollectedData]:
        # 네이버 뉴스 수집
        # 다음 뉴스 수집
        # 증권사 리포트 수집
        # 컨센서스 수집

@dataclass
class CollectedData:
    stock_code: str
    news: List[Dict]
    reports: List[Dict]
    consensus: Dict
    policy_keywords: List[str]
```

**Rate Limit**:
- 네이버/다음: 30 calls/min
- 증권사: 12 calls/min

### src/phase2/gemini_analyzer.py

Gemini AI 배치 분석. 5개 종목씩 묶어서 분석.

```python
class GeminiBatchAnalyzer:
    async def analyze_batch(candidates, collected_data) -> List[Dict]:
        # 5개씩 배치 분할
        # Gemini API 호출
        # JSON 파싱
        # 등급, 신뢰도, 핵심 재료 추출

    def _build_batch_prompt(batch, collected_data) -> str
    def _parse_batch_response(response_text, batch) -> List[Dict]
```

**등급 기준**:
| 등급 | 조건 |
|:---:|:---|
| S | PBR 0.3 이하 AND PER 5 이하 |
| A | PBR 0.5 이하 OR PER 7 이하 |
| B | PBR 1.0 이하 OR PER 15 이하 |
| C | 특별한 매력 없음 |
| D | 하락 리스크 존재 |

### src/phase3/scorer.py

최종 스코어링 및 리포트 생성.

```python
class ValueScorer:
    async def score_all(candidates, batch_id) -> List[Dict]:
        # 정량 점수 (40%)
        # 정성 점수 (60%)
        # 최종 점수 계산
        # DB 저장

    def _calculate_qual_score(stock) -> float

class ReportGenerator:
    async def generate_markdown(results, batch_id) -> str:
        # Top 10 테이블
        # S/A 등급 상세
        # 등급 분포
        # 마크다운 파일 저장
```

**점수 공식**:
```
final_score = quant_score * 0.4 + qual_score * 0.6
qual_score = grade_score[ai_grade] * (0.7 + ai_confidence * 0.3)
```

---

## 설정 커스터마이징

### Phase 1A 필터 조건 변경

```python
# config/settings.py
@dataclass
class Phase1AConfig:
    pbr_min: float = 0.1    # 최소 PBR
    pbr_max: float = 3.0    # 최대 PBR
    per_min: float = 1.0    # 최소 PER
    per_max: float = 30.0   # 최대 PER
    min_volume: int = 10_000
    max_candidates: int = 200
```

### Phase 1B 필터 조건 변경

```python
@dataclass
class Phase1BConfig:
    rsi_min: float = 20.0   # 최소 RSI
    rsi_max: float = 80.0   # 최대 RSI
    disparity_20_max: float = 115.0
    disparity_60_max: float = 120.0
    max_candidates: int = 100
```

### AI 등급 기준 변경

```python
# src/phase2/gemini_analyzer.py 프롬프트 수정
**등급 기준 (반드시 준수):**
- S등급: PBR 0.3 이하 AND PER 5 이하
- A등급: PBR 0.5 이하 OR PER 7 이하
...
```

### 점수 가중치 변경

```python
# config/settings.py
@dataclass
class Phase3Config:
    quant_weight: float = 0.4  # 정량 40%
    qual_weight: float = 0.6   # 정성 60%
```

---

## 의존성

```
asyncpg>=0.29.0
pykrx>=1.0.0
FinanceDataReader>=0.9.0
google-generativeai>=0.8.0
pandas>=2.0.0
aiohttp>=3.9.0
```

---

## 관련 문서

- [시스템 설계 문서](../docs/신규종목추천-시스템-설계.md)
- [프로젝트 전체 가이드](../CLAUDE.md)

---

*Last Updated: 2025-11-27*
