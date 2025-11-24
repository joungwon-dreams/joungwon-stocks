# 🚀 joungwon.stocks - AI 기반 한국 주식 투자 자동화 시스템

> 강화학습, 실시간 데이터, Gemini AI를 활용한 차세대 주식 투자 플랫폼

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14.20-blue)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-Private-red)](./LICENSE)

---

## 📋 목차

- [프로젝트 소개](#프로젝트-소개)
- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [시스템 아키텍처](#시스템-아키텍처)
- [시작하기](#시작하기)
- [개발 가이드](#개발-가이드)
- [문서](#문서)
- [로드맵](#로드맵)

---

## 🎯 프로젝트 소개

**joungwon.stocks**는 한국 주식 시장을 위한 엔터프라이즈급 AI 자동매매 시스템입니다.

### 핵심 목표

```yaml
데이터 수집:
  - 41개 사이트 실시간 데이터 수집 (3-4초 목표)
  - KRX, DART, 증권사, 뉴스 등 통합 수집

AI 분석:
  - 강화학습 (A2C) 기반 매매 전략
  - Gemini AI 감성 분석 (뉴스, 리포트)
  - 45개 기술 지표 자동 계산

자동매매:
  - 한국투자증권 API 실시간 연동
  - WebSocket 자동 재연결
  - 리스크 관리 및 포지션 제어

성과 분석:
  - 백테스팅 시스템
  - 매매 방식별 수익률 비교
  - AI 추천 정확도 추적
```

### 기반 오픈소스

| 프로젝트 | 역할 | 링크 |
|---------|------|------|
| **quantylab/rltrader** | 강화학습 구조 참고 | [GitHub](https://github.com/quantylab/rltrader) |
| **Korea Investment API** | 실시간 매매 | [GitHub](https://github.com/koreainvestment/open-trading-api) |
| **FinanceDataReader** | 데이터 수집 | [GitHub](https://github.com/FinanceData/FinanceDataReader) |
| **FinGPT** | AI 금융 분석 | [GitHub](https://github.com/AI4Finance-Foundation/FinGPT) |

---

## ✨ 주요 기능

### 1. 📊 실시간 데이터 수집

- **Tier 1 (공식 라이브러리)**: pykrx, dart-fss, FinanceDataReader
- **Tier 2 (공식 API)**: 한국투자증권, Naver Finance
- **Tier 3 (웹 스크래핑)**: 증권사 리포트, 뉴스 수집
- **Tier 4 (브라우저 자동화)**: Playwright, DrissionPage

### 2. 🧠 AI 분석

- **강화학습**: A2C 알고리즘 기반 매매 전략
- **감성 분석**: Gemini AI 뉴스 감성 분석
- **기술 지표**: RSI, MACD, 볼린저밴드 등 45개
- **수급 분석**: 외국인/기관/개인 순매수 추적

### 3. 🤖 자동매매

- **실시간 WebSocket**: 1초 단위 호가/체결 수신
- **자동 재연결**: 네트워크 끊김 시 자동 복구
- **리스크 관리**: 손절가, 목표가, 최대 포지션 제어
- **모의투자**: 실전 전 충분한 테스트

### 4. 📈 성과 분석

- **백테스팅**: 과거 데이터 기반 전략 검증
- **정확도 추적**: AI 추천 성과 자동 검증
- **수익률 비교**: 매매 방식별 성과 분석
- **대시보드**: Grafana 실시간 모니터링

---

## 🛠️ 기술 스택

### Backend & Data

```yaml
Language: Python 3.9+
Async: asyncio, aiohttp, asyncpg
Database: PostgreSQL 14.20
Validation: Pydantic
Monitoring: Prometheus, Grafana
Logging: structlog
```

### Data Collection

```yaml
Official:
  - pykrx (KRX 데이터)
  - dart-fss (DART 공시)
  - FinanceDataReader (종목 리스트)
  - python-kis (한국투자증권)

Web Scraping:
  - Scrapy (증권사 리포트)
  - BeautifulSoup (뉴스)
  - Playwright (JavaScript 사이트)
```

### AI & Machine Learning

```yaml
Framework: TensorFlow 2.x / PyTorch 1.10+
LLM: Google Gemini Pro
RL: A2C (Advantage Actor-Critic)
Technical Indicators: pandas-ta
```

---

## 🏗️ 시스템 아키텍처

### 데이터 흐름

```
┌─────────────────┐
│  Data Sources   │  41개 사이트
└────────┬────────┘
         │
    ┌────▼─────┐
    │ Fetchers │  Tier 1-4 수집기
    └────┬─────┘
         │
    ┌────▼────────┐
    │  Pipelines  │  검증, 변환, 저장
    └────┬────────┘
         │
    ┌────▼──────────┐
    │  PostgreSQL   │  13개 테이블
    └────┬──────────┘
         │
    ┌────▼─────┐
    │ AI 분석  │  강화학습, 감성 분석
    └────┬─────┘
         │
    ┌────▼──────┐
    │ 자동매매  │  실시간 주문
    └───────────┘
```

### 디렉토리 구조

```
joungwon.stocks/
├── docs/                    # 📝 개발 문서
│   └── 01-opensource-integration-analysis.md
├── config/                  # ⚙️ 설정 파일
├── src/                     # 💻 소스 코드
│   ├── core/               # 핵심 모듈
│   ├── fetchers/           # 데이터 수집 (Tier 1-4)
│   ├── ai/                 # AI 분석 (감성, 강화학습)
│   ├── trading/            # 매매 모듈
│   ├── learners/           # 강화학습 에이전트
│   └── monitoring/         # 모니터링
├── scripts/                 # 🛠️ 유틸리티 스크립트
├── tests/                   # 🧪 테스트
└── data/                    # 📊 데이터 저장
```

---

## 🚀 시작하기

### 사전 요구사항

- Python 3.9+
- PostgreSQL 14.20+
- 한국투자증권 API 계정 (모의투자)
- Google Gemini API Key

### 설치

```bash
# 1. 저장소 클론
git clone https://github.com/wonny/joungwon.stocks.git
cd joungwon.stocks

# 2. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. PostgreSQL 데이터베이스 생성
createdb stock_investment_db

# 5. 테이블 생성
psql -U wonny -d stock_investment_db -f sql/01_create_tables.sql

# 6. 환경 변수 설정
cp .env.example .env
# .env 파일 편집 (DB, API 키 설정)
```

### 초기 데이터 수집

```bash
# 종목 리스트 초기화 (KRX 전 종목)
python scripts/initialize_stocks.py

# 일봉 데이터 수집 (과거 1년)
python scripts/collect_daily_ohlcv.py
```

### 실행

```bash
# 데이터 수집 시작
python src/core/orchestrator.py

# 실시간 WebSocket (별도 터미널)
python src/fetchers/tier2_official_apis/kis_websocket.py

# 뉴스 분석 (별도 터미널)
python scripts/run_news_analysis.py
```

---

## 📖 개발 가이드

### 새로운 Fetcher 추가

```python
# src/fetchers/tier1_official_libs/my_fetcher.py

from src.core.base_fetcher import BaseFetcher

class MyFetcher(BaseFetcher):
    """새로운 데이터 소스 Fetcher"""

    async def fetch(self):
        """데이터 수집 로직"""
        data = await self.fetch_data()
        validated_data = self.validate(data)
        await self.save_to_db(validated_data)
```

### 새로운 프롬프트 추가

```python
# config/prompts/my_prompt.txt

다음 뉴스를 분석하세요.

뉴스: {news}

답변 형식:
- 감성: 긍정/중립/부정
- 근거: [200자 이내]
```

### 테스트 실행

```bash
# 단위 테스트
pytest tests/unit/

# 통합 테스트
pytest tests/integration/

# 커버리지 리포트
pytest --cov=src --cov-report=html
```

---

## 📚 문서

### 개발 문서

- [오픈소스 통합 분석](./docs/01-opensource-integration-analysis.md) - 4개 프로젝트 분석 및 적용 방안
- [데이터베이스 스키마](./docs/02-database-schema.md) - PostgreSQL 테이블 설계
- [API 문서](./docs/03-api-documentation.md) - REST API 명세
- [배포 가이드](./docs/04-deployment-guide.md) - 프로덕션 배포

### 외부 문서

- [한국투자증권 API 문서](https://apiportal.koreainvestment.com)
- [FinanceDataReader 가이드](https://github.com/FinanceData/FinanceDataReader)
- [Gemini API 문서](https://ai.google.dev/docs)

---

## 🗺️ 로드맵

### Phase 1: 데이터 수집 강화 (1-2주) ✅

- [x] FinanceDataReader 통합
- [x] Korea Investment API 연동
- [x] WebSocket 실시간 수신
- [x] 기술 지표 자동 계산

### Phase 2: AI 분석 고도화 (2-3주) 🚧

- [ ] Gemini 감성 분석 파이프라인
- [ ] 뉴스 크롤러 개발 (3개 사이트)
- [ ] RLTrader A2C 에이전트 학습
- [ ] 백테스팅 시스템 구축

### Phase 3: 실전 배포 (1-2주) 📅

- [ ] 실시간 자동매매 시스템
- [ ] 리스크 관리 모듈
- [ ] Slack 알림 시스템
- [ ] 모의투자 실전 테스트

### Phase 4: 확장 기능 (TBD) 💡

- [ ] 포트폴리오 리밸런싱
- [ ] 멀티 종목 동시 분석
- [ ] 딥러닝 모델 (LSTM, Transformer)
- [ ] 웹 대시보드 (React)

---

## 📊 성과 목표

| 지표 | 현재 | 목표 |
|------|------|------|
| 데이터 수집 속도 | 41초 | **3-4초** (10배) |
| 1000 종목 분석 | N/A | **5분** |
| 백테스팅 (1년) | 6분 | **6초** (60배) |
| AI 추천 정확도 | N/A | **70%+** |

---

## 🤝 기여

현재 비공개 프로젝트입니다.

---

## 📄 라이선스

Private - All Rights Reserved

---

## 📞 문의

- **작성자**: wonny
- **이메일**: wonny@example.com
- **프로젝트 시작**: 2025-11-24

---

**Made with ❤️ by wonny**
