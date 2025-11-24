---
created: 2025-11-24 11:29:49
updated: 2025-11-24 11:29:49
tags: [analysis, opensource, integration, architecture]
author: wonny
status: active
---

# 오픈소스 프로젝트 통합 분석 및 적용 방안

> 한국 주식 투자 관련 4개 오픈소스 프로젝트 분석 및 joungwon.stocks 프로젝트 적용 전략

## 📋 목차

1. [개요](#개요)
2. [프로젝트별 분석](#프로젝트별-분석)
3. [통합 적용 로드맵](#통합-적용-로드맵)
4. [디렉토리 구조 설계](#디렉토리-구조-설계)
5. [즉시 적용 가능한 코드](#즉시-적용-가능한-코드)
6. [참고 자료](#참고-자료)

---

## 🎯 개요

### 분석 대상 프로젝트

| No | 프로젝트 | 카테고리 | 주요 기능 |
|----|----------|----------|-----------|
| 1 | **quantylab/rltrader** | 강화학습 | A2C 알고리즘, 45개 기술지표, 모델 학습 |
| 2 | **Korea Investment API** | 실시간 데이터 | WebSocket, REST API, 자동매매 |
| 3 | **FinanceDataReader** | 데이터 수집 | 종목 리스트, OHLCV, 글로벌 시장 |
| 4 | **FinGPT** | AI 분석 | LLM 금융 분석, 감성 분석, 프롬프트 엔지니어링 |

### 적용 목표

```yaml
Phase 1 (1-2주):
  - FinanceDataReader 통합 (종목 리스트, 기술 지표)
  - Korea Investment API 연동 (WebSocket, 실시간 데이터)

Phase 2 (2-3주):
  - FinGPT 프롬프트 엔지니어링 (뉴스 감성 분석)
  - RLTrader 강화학습 모델 (A2C 에이전트)

Phase 3 (1-2주):
  - 실시간 매매 시스템 통합
  - 백테스팅 및 성과 분석
```

---

## 📊 프로젝트별 분석

### 1️⃣ quantylab/rltrader - 강화학습 주식투자 시스템

**Repository**: https://github.com/quantylab/rltrader

#### 핵심 특징

- **강화학습 알고리즘**: A2C (Advantage Actor-Critic)
- **네트워크 아키텍처**: DNN (Dense Neural Networks), LSTM
- **데이터 버전**:
  - v3: 주식 데이터 + 시장 지표 (45개)
  - v4: 확장 시장 데이터
- **프레임워크**: TensorFlow 2.7.0, PyTorch 1.10.1

#### 프로젝트 구조

```python
rltrader/
├── data/                    # CSV 파일 기반 데이터 저장
│   ├── stock_data.csv      # 주식 데이터
│   └── market_data.csv     # 시장 지표
├── models/                  # 학습된 모델 체크포인트
│   └── a2c_model.h5
├── data_manager.py          # ⭐ 데이터 로드 및 전처리
├── main.py                  # CLI 엔트리 포인트
├── learners/                # 강화학습 에이전트
└── notebooks/               # Jupyter 실험
```

#### 🎯 Copy Point 1: data_manager.py 구조

```python
# data_manager.py - 주식 데이터 + 시장 데이터 병합
class DataManager:
    """
    stock_fields (45+ 지표):
      - 가격 비율: 시가/종가, 고가/종가, 저가/종가
      - 이동평균: 5일, 20일, 60일, 120일 MA
      - 거래량 비율: 당일/5일평균, 당일/20일평균
      - 투자자 수급: 기관 순매수, 외국인 순매수

    market_fields:
      - KOSPI/채권 비율 추이
      - 5/20/60/120일 이동평균
    """

    def load_chart_data(self, stock_code: str, start_date: str, end_date: str):
        """주식 차트 데이터 로드"""
        stock_df = self._load_stock_data(stock_code, start_date, end_date)
        market_df = self._load_market_data(start_date, end_date)

        # 데이터 병합 (날짜 기준)
        merged_df = pd.merge(stock_df, market_df, on='date', how='left')
        return merged_df

    def preprocess(self, df):
        """데이터 전처리 (정규화, 결측치 처리)"""
        # Min-Max Normalization
        for col in df.columns:
            if col != 'date':
                df[col] = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
        return df
```

#### 🎯 Copy Point 2: 폴더 구조

```
src/
├── data/              # 수집된 데이터 저장
│   ├── stocks/       # 종목별 데이터
│   └── market/       # 시장 지표
├── models/            # AI 모델 저장
│   ├── rl_models/    # 강화학습 모델
│   └── checkpoints/  # 학습 체크포인트
├── learners/          # 강화학습 에이전트
│   ├── a2c_agent.py
│   └── dqn_agent.py
└── data_manager.py    # 데이터 통합 관리
```

#### 적용 방안

**현재 프로젝트에 적용**:
```yaml
1. 디렉토리 구조:
   - src/models/rl_models/ 생성
   - src/learners/ 생성

2. 기술 지표 확장:
   - 45개 기술 지표 → stock_prices_10min 테이블에 추가
   - data_manager.py 참고하여 src/utils/data_loader.py 개선

3. 강화학습 에이전트:
   - A2C 알고리즘 구현
   - 백테스팅 시스템 구축
```

---

### 2️⃣ Korea Investment Securities API - 실시간 데이터 및 자동매매

**Official Repository**: https://github.com/koreainvestment/open-trading-api
**Python Libraries**:
- https://github.com/Soju06/python-kis
- https://github.com/pjueon/pykis

#### 핵심 특징

- **실시간 WebSocket**: 자동 재연결, 끊김 복구
- **REST API**: 주문, 잔고 조회, 시세 조회
- **모의투자**: 실전 투자 전 테스트 가능
- **라이브러리**: `python-kis` (Soju06), `pykis` (pjueon)

#### 🎯 Copy Point 1: WebSocket 실시간 수신

```python
# 공식 API 사용 (kis_auth)
import kis_auth as ka

# WebSocket 선언
kws = ka.KISWebSocket(api_url="/tryitout")

# 구독 (삼성전자, SK하이닉스)
kws.subscribe(request=asking_price_krx, data=["005930", "000660"])

# 콜백 함수
def on_message(data):
    print(f"종목코드: {data['stock_code']}, 현재가: {data['price']}")
    # PostgreSQL에 실시간 INSERT
    insert_to_min_ticks(data)

kws.on_message = on_message
kws.start()
```

#### 🎯 Copy Point 2: python-kis 라이브러리 (복구 가능 WebSocket)

```python
from pykis import PyKis

# 인증
kis = PyKis()
stock = kis.stock("005930")  # 삼성전자

# 실시간 호가/체결 자동 복구
@stock.on_price
def on_price(price):
    """
    네트워크 끊김 시 자동 재연결 + 구독 복원
    """
    print(f"현재가: {price.price}, 거래량: {price.volume}")

    # PostgreSQL에 실시간 INSERT → 트리거 자동 발동
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO min_ticks (stock_code, timestamp, price, volume)
        VALUES (%s, NOW(), %s, %s)
    """, (price.code, price.price, price.volume))
    conn.commit()
```

#### 🎯 Copy Point 3: 매수/매도 주문 함수

```python
# 시장가 매수
stock.buy(qty=1)

# 지정가 매수
stock.buy(price=194700, qty=1)

# 전량 시장가 매도
stock.sell()

# 전량 지정가 매도
stock.sell(price=194700)

# 가격 정정
order = stock.buy(price=194700, qty=1)
order.modify(price=195000)

# 주문 취소
order.cancel()

# 잔고 조회
balance = kis.balance()
for holding in balance.holdings:
    print(f"{holding.name}: {holding.quantity}주, 평가금액: {holding.value:,}원")
```

#### 적용 방안

**현재 프로젝트에 적용**:
```yaml
1. 디렉토리 구조:
   - src/fetchers/tier2_official_apis/kis_api_fetcher.py
   - src/fetchers/tier2_official_apis/kis_websocket.py

2. WebSocket 통합:
   - 실시간 수신 → min_ticks 테이블 INSERT
   - 트리거 자동 발동 → stock_assets.price 업데이트

3. 자동매매:
   - trade_history 테이블에 실제 매매 기록
   - AI 판단 근거 (gemini_reasoning) 저장

4. 설정 파일:
   - config/kis_config.yaml
   - 모의투자 계정 정보 (kis_devlp.yaml)
```

---

### 3️⃣ FinanceDataReader - 차트 및 기술적 분석 데이터

**Repository**: https://github.com/FinanceData/FinanceDataReader

#### 핵심 특징

- **종목 리스트**: KOSPI/KOSDAQ/KONEX 전 종목 1줄 코드
- **글로벌 시장**: NASDAQ, NYSE, S&P500, 상해/선전/홍콩/도쿄
- **pandas 호환**: pandas-ta와 완벽 호환
- **데이터 소스**: 다양한 소스 선택 가능 (KRX, NAVER, YAHOO)

#### 🎯 Copy Point 1: 종목 리스트업

```python
import FinanceDataReader as fdr

# 전체 KRX 종목 (약 2,663개)
krx = fdr.StockListing('KRX')
print(krx.head())
#   Code     Name  Market    Dept  Marcap
# 005930  삼성전자   KOSPI   대형주  457조

# KOSPI만 (약 940개)
kospi = fdr.StockListing('KOSPI')

# KOSDAQ만 (약 1,597개)
kosdaq = fdr.StockListing('KOSDAQ')

# 상장폐지 종목
delisted = fdr.StockListing('KRX-DELISTING')

# stocks 테이블에 INSERT
import psycopg2

conn = psycopg2.connect(
    dbname="stock_investment_db",
    user="wonny",
    host="localhost"
)
cursor = conn.cursor()

for _, row in krx.iterrows():
    cursor.execute("""
        INSERT INTO stocks (code, name, market, category, is_active)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (code) DO UPDATE
        SET name = EXCLUDED.name,
            market = EXCLUDED.market,
            updated_at = CURRENT_TIMESTAMP
    """, (
        row['Code'],
        row['Name'],
        row['Market'],
        'Growth',  # 기본 카테고리
        True
    ))

conn.commit()
print(f"✅ {len(krx)}개 종목 저장 완료")
```

#### 🎯 Copy Point 2: OHLCV 데이터 수집

```python
import FinanceDataReader as fdr

# 삼성전자 2024년 데이터
df = fdr.DataReader('005930', '2024')

# 특정 기간 지정
df = fdr.DataReader('005930', '2024-01-01', '2024-12-31')

# 미국 주식 (Apple)
apple = fdr.DataReader('AAPL', '2024')

# daily_ohlcv 테이블에 저장
for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO daily_ohlcv (code, date, open, high, low, close, volume, change_rate)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (code, date) DO NOTHING
    """, (
        '005930',
        row.name,  # index가 날짜
        row['Open'],
        row['High'],
        row['Low'],
        row['Close'],
        row['Volume'],
        row['Change']
    ))
conn.commit()
```

#### 🎯 Copy Point 3: pandas-ta 연동 (기술적 지표)

```python
import FinanceDataReader as fdr
import pandas_ta as ta

# 데이터 가져오기
df = fdr.DataReader('005930', '2024')

# RSI(14) 계산
df.ta.rsi(length=14, append=True)

# MACD 계산
df.ta.macd(append=True)

# 볼린저 밴드
df.ta.bbands(append=True)

# 이동평균선 (5, 20, 60일)
df.ta.sma(length=5, append=True)
df.ta.sma(length=20, append=True)
df.ta.sma(length=60, append=True)

# stock_prices_10min 테이블에 저장 (10분봉으로 변환)
# 또는 새로운 테이블 생성: daily_indicators

for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO daily_indicators (
            stock_code, date, rsi, macd, macd_signal, macd_hist,
            bb_upper, bb_middle, bb_lower, ma5, ma20, ma60
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (stock_code, date) DO UPDATE
        SET rsi = EXCLUDED.rsi,
            macd = EXCLUDED.macd,
            updated_at = CURRENT_TIMESTAMP
    """, (
        '005930',
        row.name,
        row['RSI_14'],
        row['MACD_12_26_9'],
        row['MACDs_12_26_9'],
        row['MACDh_12_26_9'],
        row['BBU_20_2.0'],
        row['BBM_20_2.0'],
        row['BBL_20_2.0'],
        row['SMA_5'],
        row['SMA_20'],
        row['SMA_60']
    ))
conn.commit()
```

#### 적용 방안

**현재 프로젝트에 적용**:
```yaml
1. 디렉토리 구조:
   - src/fetchers/tier1_official_libs/fdr_fetcher.py
   - src/utils/technical_indicators.py (pandas-ta 래퍼)

2. 초기화 스크립트:
   - scripts/initialize_stocks.py (stocks 테이블 초기화)
   - scripts/collect_daily_ohlcv.py (일봉 데이터 수집)

3. 기술 지표 자동 계산:
   - 일봉 수집 시 pandas-ta로 자동 계산
   - daily_indicators 테이블 또는 stock_prices_10min 확장

4. 의존성 추가:
   - pip install finance-datareader pandas-ta
```

---

### 4️⃣ FinGPT - AI 금융 분석 및 감성 분석

**Repository**: https://github.com/AI4Finance-Foundation/FinGPT

#### 핵심 특징

- **오픈소스 LLM**: Llama2, Falcon, ChatGLM2, Qwen 기반
- **LoRA Fine-tuning**: $300 비용 (vs BloombergGPT $3M)
- **실시간 뉴스**: 월/주간 업데이트
- **금융 특화**: 76.8K+ 감성 분석 예제

#### 🎯 Copy Point 1: 감성 분석 프롬프트 템플릿

```python
# FinGPT 스타일 프롬프트
SENTIMENT_PROMPT = """
What is the sentiment of this news?
Please choose an answer from {negative/neutral/positive}.

News: {news_headline}

Answer:
"""

HEADLINE_ANALYSIS_PROMPT = """
Does the news headline talk about price going up?
Please choose an answer from {Yes/No}.

Headline: {headline}

Answer:
"""

RELATION_EXTRACTION_PROMPT = """
Please extract entities and their relationships from the input sentence.
Entity types should be chosen from {person/organization/location}.
Relationship types include: manufacturer, distributed by, industry, product/material produced, etc.

Sentence: {sentence}

Answer:
"""

# Gemini에 적용
import google.generativeai as genai

def analyze_news_sentiment(news_text: str) -> str:
    """뉴스 감성 분석 (Gemini)"""
    prompt = SENTIMENT_PROMPT.format(news_headline=news_text)

    response = genai.generate_content(prompt)
    sentiment = response.text.strip().lower()

    # data_sources 테이블에 저장
    cursor.execute("""
        INSERT INTO recommendation_history (
            stock_code, stock_name, recommendation_date,
            recommended_price, recommendation_type, source_id,
            gemini_reasoning, note
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        stock_code,
        stock_name,
        datetime.now().date(),
        current_price,
        'buy' if sentiment == 'positive' else 'hold',
        source_id,  # Gemini_AI source_id
        response.text,
        news_text
    ))
    conn.commit()

    return sentiment
```

#### 🎯 Copy Point 2: 뉴스 수집 파이프라인

```python
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

class NewsCollector:
    """뉴스 수집 및 분석 파이프라인"""

    def __init__(self, gemini_api_key: str):
        self.gemini_api_key = gemini_api_key
        genai.configure(api_key=gemini_api_key)

    def collect_daily_news(self, stock_code: str, stock_name: str) -> List[Dict]:
        """네이버 뉴스 크롤링"""
        url = f"https://finance.naver.com/item/news.naver?code={stock_code}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        news_list = []
        for item in soup.select('.articleSubject a'):
            news_list.append({
                'title': item.text.strip(),
                'url': item['href'],
                'stock_code': stock_code,
                'stock_name': stock_name
            })

        return news_list[:10]  # 최근 10개

    def vectorize_news(self, news_list: List[Dict]) -> List[Dict]:
        """텍스트 → 벡터화 (선택적)"""
        # 간단한 구현: 단어 빈도수 기반
        # 고급 구현: Sentence Transformers, OpenAI Embeddings
        for news in news_list:
            # 벡터화 로직
            pass
        return news_list

    def analyze_sentiment_batch(self, news_list: List[Dict]) -> List[Dict]:
        """배치 감성 분석"""
        for news in news_list:
            sentiment = self.analyze_news_sentiment(news['title'])
            news['sentiment'] = sentiment
            news['sentiment_score'] = {
                'positive': 1.0,
                'neutral': 0.0,
                'negative': -1.0
            }[sentiment]

        return news_list

    def store_to_db(self, news_list: List[Dict], source_id: int):
        """recommendation_history 테이블에 저장"""
        for news in news_list:
            cursor.execute("""
                INSERT INTO recommendation_history (
                    stock_code, stock_name, recommendation_date,
                    recommended_price, recommendation_type, source_id,
                    gemini_reasoning, note
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                news['stock_code'],
                news['stock_name'],
                datetime.now().date(),
                0,  # 뉴스는 가격 정보 없음
                'buy' if news['sentiment'] == 'positive' else 'hold',
                source_id,
                f"Sentiment: {news['sentiment']} (Score: {news['sentiment_score']})",
                news['title']
            ))
        conn.commit()

    def run_daily_pipeline(self, stock_codes: List[str]):
        """일일 뉴스 분석 파이프라인"""
        for code in stock_codes:
            # 1. 뉴스 수집
            news_list = self.collect_daily_news(code, get_stock_name(code))

            # 2. 감성 분석
            news_list = self.analyze_sentiment_batch(news_list)

            # 3. DB 저장
            self.store_to_db(news_list, source_id=1)  # Gemini_AI source_id

            print(f"✅ {code} 뉴스 {len(news_list)}개 분석 완료")
```

#### 🎯 Copy Point 3: 프롬프트 엔지니어링 (한국어 최적화)

```python
# 한국어 감성 분석 프롬프트
KOREAN_SENTIMENT_PROMPT = """
다음 뉴스 제목의 감성을 분석하세요.
반드시 {긍정/중립/부정} 중 하나만 선택하세요.

뉴스 제목: {news_headline}

분석:
1. 주요 키워드 추출
2. 긍정적 요소 / 부정적 요소 파악
3. 최종 감성 판단

답변 (긍정/중립/부정만 출력):
"""

# 목표가 예측 프롬프트
TARGET_PRICE_PROMPT = """
다음 종목의 목표가를 분석하세요.

종목명: {stock_name}
현재가: {current_price:,}원
최근 뉴스:
{news_summary}

재무 정보:
- PER: {per}
- PBR: {pbr}
- ROE: {roe}%

질문: 3개월 후 목표가는?

답변 형식:
목표가: [숫자]원
근거: [200자 이내]
"""
```

#### 적용 방안

**현재 프로젝트에 적용**:
```yaml
1. 디렉토리 구조:
   - src/ai/sentiment_analyzer.py (감성 분석)
   - src/ai/gemini_client.py (Gemini API 래퍼)
   - src/fetchers/tier3_web_scraping/news_spider.py (뉴스 크롤링)

2. 프롬프트 템플릿:
   - config/prompts/sentiment.txt
   - config/prompts/target_price.txt
   - config/prompts/recommendation.txt

3. 데이터 흐름:
   - 뉴스 수집 → 감성 분석 → recommendation_history
   - 일정 기간 후 → verification_results (정확도 검증)
   - data_sources.reliability_score 자동 업데이트

4. 스케줄링:
   - 매일 장 마감 후 뉴스 수집 및 분석
   - APScheduler 활용
```

---

## 🚀 통합 적용 로드맵

### Phase 1: 데이터 수집 강화 (1-2주)

#### Week 1: FinanceDataReader 통합

**목표**: 종목 리스트 자동화 + 일봉 데이터 수집

```yaml
Tasks:
  1. 환경 설정:
     - pip install finance-datareader pandas-ta
     - src/fetchers/tier1_official_libs/fdr_fetcher.py 생성

  2. 종목 리스트 초기화:
     - scripts/initialize_stocks.py 작성
     - KRX 전 종목 (2,663개) → stocks 테이블

  3. 일봉 데이터 수집:
     - scripts/collect_daily_ohlcv.py 작성
     - 과거 1년치 데이터 → daily_ohlcv 테이블

  4. 기술 지표 계산:
     - pandas-ta 연동
     - RSI, MACD, 볼린저밴드 → 새로운 컬럼 추가

  5. 스케줄링:
     - APScheduler로 매일 장 마감 후 자동 실행

Deliverables:
  - ✅ stocks 테이블 2,663개 종목 저장
  - ✅ daily_ohlcv 테이블 1년치 데이터
  - ✅ 기술 지표 자동 계산 파이프라인
```

#### Week 2: Korea Investment API 연동

**목표**: 실시간 WebSocket + REST API 통합

```yaml
Tasks:
  1. API 계정 발급:
     - KIS Developers 포털 회원가입
     - 모의투자 계정 생성
     - App Key/Secret 발급

  2. python-kis 설치:
     - pip install python-kis
     - auth.save() 인증 정보 저장

  3. WebSocket 실시간 수신:
     - src/fetchers/tier2_official_apis/kis_websocket.py
     - 보유 종목 실시간 호가/체결 수신
     - min_ticks 테이블 자동 INSERT

  4. REST API 통합:
     - src/fetchers/tier2_official_apis/kis_api_fetcher.py
     - 잔고 조회, 주문 함수 구현

  5. 트리거 테스트:
     - min_ticks INSERT → stock_assets.price 자동 업데이트 확인

Deliverables:
  - ✅ WebSocket 실시간 수신 (자동 재연결)
  - ✅ 매수/매도 주문 함수
  - ✅ min_ticks 테이블 실시간 데이터
```

---

### Phase 2: AI 분석 고도화 (2-3주)

#### Week 3-4: FinGPT 프롬프트 엔지니어링

**목표**: 뉴스 감성 분석 파이프라인 구축

```yaml
Tasks:
  1. 뉴스 크롤러 개발:
     - src/fetchers/tier3_web_scraping/news_spider.py
     - 네이버 뉴스, 이데일리, 한경 뉴스 수집

  2. Gemini 프롬프트 최적화:
     - src/ai/sentiment_analyzer.py
     - FinGPT 템플릿 참고 → 한국어 최적화

  3. 감성 분석 파이프라인:
     - 뉴스 수집 → 감성 분석 → DB 저장
     - recommendation_history 테이블 자동 입력

  4. 정확도 검증:
     - 7일 후 실제 가격 변동과 비교
     - verification_results 테이블 업데이트
     - data_sources.reliability_score 자동 갱신

  5. 스케줄링:
     - 매일 장 마감 후 뉴스 분석 실행

Deliverables:
  - ✅ 뉴스 크롤러 (3개 사이트)
  - ✅ Gemini 감성 분석 파이프라인
  - ✅ recommendation_history 자동 저장
  - ✅ 정확도 검증 시스템
```

#### Week 5: RLTrader 강화학습 모델

**목표**: A2C 에이전트 학습 및 백테스팅

```yaml
Tasks:
  1. 데이터 준비:
     - data_manager.py 구조 참고
     - 45개 기술 지표 계산
     - 학습 데이터셋 생성 (2023-2024)

  2. A2C 에이전트 구현:
     - src/learners/a2c_agent.py
     - TensorFlow 또는 PyTorch 선택

  3. 학습 환경 구축:
     - src/core/trading_env.py (Gym 환경)
     - 보상 함수 설계 (수익률, 샤프지수)

  4. 모델 학습:
     - 삼성전자, 네이버 등 10개 종목
     - 에포크당 성능 기록

  5. 백테스팅:
     - 2024년 데이터로 성능 검증
     - 매매 신호 정확도 측정

Deliverables:
  - ✅ A2C 에이전트 구현
  - ✅ 학습된 모델 (10개 종목)
  - ✅ 백테스팅 결과 리포트
```

---

### Phase 3: 실전 배포 (1-2주)

#### Week 6-7: 실시간 매매 시스템 통합

**목표**: WebSocket → AI 분석 → 자동 주문

```yaml
Tasks:
  1. 통합 오케스트레이터:
     - src/core/trading_orchestrator.py
     - WebSocket 수신 → AI 분석 → 주문 실행

  2. 리스크 관리:
     - src/trading/risk_manager.py
     - 최대 손실 한도, 포지션 한도 체크

  3. 모니터링:
     - src/monitoring/slack_notifier.py
     - 매매 발생 시 Slack 알림
     - Prometheus + Grafana 대시보드

  4. 로깅:
     - trade_history 테이블 자동 기록
     - gemini_reasoning 필드에 AI 판단 근거

  5. 모의투자 실전 테스트:
     - 1주일 모의투자 운영
     - 성과 분석 및 파라미터 튜닝

Deliverables:
  - ✅ 실시간 자동매매 시스템
  - ✅ 리스크 관리 모듈
  - ✅ Slack 알림 시스템
  - ✅ 모의투자 성과 리포트
```

---

## 🏗️ 디렉토리 구조 설계

### 최종 프로젝트 구조

```
joungwon.stocks/
├── docs/                                    # 📝 개발 문서
│   ├── 01-opensource-integration-analysis.md
│   ├── 02-database-schema.md
│   ├── 03-api-documentation.md
│   └── 04-deployment-guide.md
│
├── config/                                  # ⚙️ 설정 파일
│   ├── database.yaml                       # DB 연결 정보
│   ├── kis_config.yaml                     # 한국투자증권 API
│   ├── prompts/                            # Gemini 프롬프트
│   │   ├── sentiment.txt
│   │   ├── target_price.txt
│   │   └── recommendation.txt
│   └── logging.yaml                        # 로깅 설정
│
├── src/                                     # 💻 소스 코드
│   ├── core/                               # 핵심 모듈
│   │   ├── orchestrator.py                 # 전체 시스템 조율
│   │   ├── trading_env.py                  # 강화학습 환경
│   │   └── database.py                     # asyncpg 연결 풀
│   │
│   ├── fetchers/                           # 데이터 수집
│   │   ├── tier1_official_libs/            # Tier 1: 공식 라이브러리
│   │   │   ├── pykrx_fetcher.py           # KRX 데이터
│   │   │   ├── fdr_fetcher.py             # ✅ NEW: FinanceDataReader
│   │   │   └── tier1_manager.py
│   │   │
│   │   ├── tier2_official_apis/            # Tier 2: 공식 API
│   │   │   ├── kis_api_fetcher.py         # ✅ NEW: Korea Investment API
│   │   │   ├── kis_websocket.py           # ✅ NEW: 실시간 WebSocket
│   │   │   └── tier2_manager.py
│   │   │
│   │   └── tier3_web_scraping/             # Tier 3: 웹 스크래핑
│   │       ├── spiders/
│   │       │   └── news_spider.py          # ✅ NEW: 뉴스 크롤링
│   │       └── tier3_manager.py
│   │
│   ├── ai/                                  # ✅ NEW: AI 분석
│   │   ├── sentiment_analyzer.py           # 감성 분석 (FinGPT)
│   │   ├── gemini_client.py                # Gemini API 래퍼
│   │   └── prompt_templates.py             # 프롬프트 관리
│   │
│   ├── learners/                            # ✅ NEW: 강화학습
│   │   ├── a2c_agent.py                    # A2C 에이전트
│   │   ├── dqn_agent.py                    # DQN 에이전트
│   │   └── base_agent.py                   # 베이스 클래스
│   │
│   ├── trading/                             # ✅ NEW: 매매 모듈
│   │   ├── order_manager.py                # 주문 관리
│   │   ├── position_manager.py             # 포지션 관리
│   │   └── risk_manager.py                 # 리스크 관리
│   │
│   ├── utils/                               # 유틸리티
│   │   ├── data_loader.py                  # ✅ 개선: data_manager.py 참고
│   │   ├── technical_indicators.py         # ✅ NEW: pandas-ta 래퍼
│   │   ├── logger.py                       # structlog
│   │   └── retry_handler.py                # 재시도 로직
│   │
│   ├── models/                              # 데이터 모델
│   │   ├── schemas/                         # Pydantic 스키마
│   │   │   ├── ohlcv_schema.py
│   │   │   └── news_schema.py
│   │   │
│   │   └── rl_models/                       # ✅ NEW: 강화학습 모델
│   │       ├── checkpoints/                 # 학습 체크포인트
│   │       └── trained_models/              # 학습 완료 모델
│   │
│   ├── pipelines/                           # 데이터 파이프라인
│   │   ├── validation_pipeline.py          # Pydantic 검증
│   │   ├── transformation_pipeline.py      # 데이터 변환
│   │   └── storage_pipeline.py             # DB 저장
│   │
│   └── monitoring/                          # 모니터링
│       ├── metrics_collector.py            # Prometheus
│       ├── slack_notifier.py               # Slack 알림
│       └── health_checker.py               # 헬스 체크
│
├── scripts/                                 # 🛠️ 스크립트
│   ├── initialize_stocks.py                # ✅ NEW: stocks 테이블 초기화
│   ├── collect_daily_ohlcv.py              # ✅ NEW: 일봉 수집
│   ├── run_news_analysis.py                # ✅ NEW: 뉴스 분석
│   └── train_rl_agent.py                   # ✅ NEW: 강화학습 학습
│
├── tests/                                   # 🧪 테스트
│   ├── unit/                                # 단위 테스트
│   │   ├── test_fetchers.py
│   │   └── test_ai_analysis.py
│   └── integration/                         # 통합 테스트
│       └── test_end_to_end.py
│
├── data/                                    # 📊 데이터 (gitignore)
│   ├── stocks/                              # 종목별 데이터
│   ├── market/                              # 시장 지표
│   └── news/                                # 뉴스 데이터
│
├── logs/                                    # 📋 로그 (gitignore)
│   ├── app.log
│   ├── error.log
│   └── trading.log
│
├── .env                                     # 환경 변수
├── .gitignore
├── requirements.txt                         # Python 의존성
├── CLAUDE.md                                # Claude Code 가이드
└── README.md                                # 프로젝트 소개
```

---

## 💻 즉시 적용 가능한 코드

### 1. FinanceDataReader 통합 (5분)

#### 설치

```bash
pip install finance-datareader pandas-ta
```

#### src/fetchers/tier1_official_libs/fdr_fetcher.py

```python
"""
FinanceDataReader 통합 Fetcher
- 종목 리스트 가져오기
- OHLCV 데이터 수집
- pandas-ta 기술 지표 계산
"""

import FinanceDataReader as fdr
import pandas as pd
import pandas_ta as ta
from typing import List, Dict
import psycopg2


class FDRFetcher:
    """FinanceDataReader Fetcher"""

    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.conn = None

    def connect_db(self):
        """PostgreSQL 연결"""
        self.conn = psycopg2.connect(**self.db_config)

    def fetch_krx_stocks(self) -> pd.DataFrame:
        """KRX 전 종목 리스트 가져오기"""
        krx = fdr.StockListing('KRX')
        return krx

    def save_stocks_to_db(self, krx: pd.DataFrame):
        """stocks 테이블에 저장"""
        cursor = self.conn.cursor()

        for _, row in krx.iterrows():
            cursor.execute("""
                INSERT INTO stocks (code, name, market, category, is_active)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (code) DO UPDATE
                SET name = EXCLUDED.name,
                    market = EXCLUDED.market,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                row['Code'],
                row['Name'],
                row['Market'],
                'Growth',  # 기본 카테고리
                True
            ))

        self.conn.commit()
        print(f"✅ {len(krx)}개 종목 저장 완료")

    def fetch_ohlcv(self, stock_code: str, start_date: str = '2024') -> pd.DataFrame:
        """OHLCV 데이터 가져오기"""
        df = fdr.DataReader(stock_code, start_date)
        return df

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산 (pandas-ta)"""
        # RSI(14)
        df.ta.rsi(length=14, append=True)

        # MACD
        df.ta.macd(append=True)

        # 볼린저 밴드
        df.ta.bbands(append=True)

        # 이동평균선 (5, 20, 60일)
        df.ta.sma(length=5, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=60, append=True)

        return df

    def save_ohlcv_to_db(self, stock_code: str, df: pd.DataFrame):
        """daily_ohlcv 테이블에 저장"""
        cursor = self.conn.cursor()

        for date, row in df.iterrows():
            cursor.execute("""
                INSERT INTO daily_ohlcv (
                    code, date, open, high, low, close, volume, change_rate
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (code, date) DO NOTHING
            """, (
                stock_code,
                date,
                int(row['Open']),
                int(row['High']),
                int(row['Low']),
                int(row['Close']),
                int(row['Volume']),
                row['Change'] if 'Change' in row else 0.0
            ))

        self.conn.commit()
        print(f"✅ {stock_code} 일봉 데이터 {len(df)}개 저장 완료")

    def run(self):
        """전체 실행"""
        self.connect_db()

        # 1. 종목 리스트 가져오기
        krx = self.fetch_krx_stocks()
        self.save_stocks_to_db(krx)

        # 2. OHLCV 데이터 수집 (보유 종목만)
        cursor = self.conn.cursor()
        cursor.execute("SELECT code FROM stock_assets WHERE quantity > 0")
        holding_codes = [row[0] for row in cursor.fetchall()]

        for code in holding_codes:
            df = self.fetch_ohlcv(code)
            df = self.calculate_technical_indicators(df)
            self.save_ohlcv_to_db(code, df)

        self.conn.close()


# 사용 예시
if __name__ == "__main__":
    db_config = {
        'dbname': 'stock_investment_db',
        'user': 'wonny',
        'host': 'localhost'
    }

    fetcher = FDRFetcher(db_config)
    fetcher.run()
```

---

### 2. Korea Investment API 통합 (10분)

#### 설치

```bash
pip install python-kis
```

#### src/fetchers/tier2_official_apis/kis_websocket.py

```python
"""
Korea Investment Securities WebSocket
- 실시간 호가/체결 수신
- 자동 재연결 (네트워크 끊김 복구)
- min_ticks 테이블 자동 INSERT
"""

from pykis import PyKis
from typing import List
import psycopg2
from datetime import datetime


class KISWebSocket:
    """한국투자증권 WebSocket 클라이언트"""

    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.conn = None
        self.kis = PyKis()

    def connect_db(self):
        """PostgreSQL 연결"""
        self.conn = psycopg2.connect(**self.db_config)

    def start_realtime_feed(self, stock_codes: List[str]):
        """실시간 호가/체결 수신 시작"""
        self.connect_db()

        for code in stock_codes:
            stock = self.kis.stock(code)

            # 실시간 호가/체결 이벤트
            @stock.on_price
            def on_price(price):
                """
                실시간 가격 수신 콜백
                - 네트워크 끊김 시 자동 재연결
                - min_ticks 테이블 자동 INSERT
                """
                print(f"[{price.code}] 현재가: {price.price:,}원, 거래량: {price.volume:,}")

                # min_ticks 테이블에 INSERT
                cursor = self.conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO min_ticks (stock_code, timestamp, price, volume)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        price.code,
                        datetime.now(),
                        price.price,
                        price.volume
                    ))
                    self.conn.commit()

                    # 트리거 자동 발동 → stock_assets.price 업데이트

                except Exception as e:
                    print(f"❌ DB 저장 실패: {e}")
                    self.conn.rollback()

        print(f"✅ {len(stock_codes)}개 종목 실시간 수신 시작")


# 사용 예시
if __name__ == "__main__":
    db_config = {
        'dbname': 'stock_investment_db',
        'user': 'wonny',
        'host': 'localhost'
    }

    ws = KISWebSocket(db_config)
    ws.start_realtime_feed(['005930', '000660', '035420'])  # 삼성전자, SK하이닉스, NAVER
```

#### src/fetchers/tier2_official_apis/kis_api_fetcher.py

```python
"""
Korea Investment Securities REST API
- 매수/매도 주문
- 잔고 조회
- 주문 정정/취소
"""

from pykis import PyKis
from typing import Dict, List
import psycopg2
from datetime import datetime


class KISAPIFetcher:
    """한국투자증권 REST API 클라이언트"""

    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.conn = None
        self.kis = PyKis()

    def connect_db(self):
        """PostgreSQL 연결"""
        self.conn = psycopg2.connect(**self.db_config)

    def buy_market(self, stock_code: str, quantity: int, strategy_name: str = "Manual"):
        """시장가 매수"""
        stock = self.kis.stock(stock_code)
        order = stock.buy(qty=quantity)

        # trade_history 테이블에 기록
        self._save_trade_history(
            stock_code=stock_code,
            trade_type='BUY',
            quantity=quantity,
            price=order.price,
            trading_method='Manual',
            strategy_name=strategy_name
        )

        return order

    def buy_limit(self, stock_code: str, price: int, quantity: int):
        """지정가 매수"""
        stock = self.kis.stock(stock_code)
        order = stock.buy(price=price, qty=quantity)

        self._save_trade_history(
            stock_code=stock_code,
            trade_type='BUY',
            quantity=quantity,
            price=price,
            trading_method='Manual'
        )

        return order

    def sell_market(self, stock_code: str, quantity: int = None):
        """시장가 매도 (전량 또는 일부)"""
        stock = self.kis.stock(stock_code)

        if quantity is None:
            # 전량 매도
            order = stock.sell()
        else:
            # 일부 매도
            order = stock.sell(qty=quantity)

        # 손익 계산
        avg_buy_price = self._get_avg_buy_price(stock_code)
        profit_loss = (order.price - avg_buy_price) * order.quantity
        profit_rate = ((order.price - avg_buy_price) / avg_buy_price) * 100

        self._save_trade_history(
            stock_code=stock_code,
            trade_type='SELL',
            quantity=order.quantity,
            price=order.price,
            trading_method='Manual',
            profit_loss=profit_loss,
            profit_rate=profit_rate
        )

        return order

    def get_balance(self) -> Dict:
        """잔고 조회"""
        balance = self.kis.balance()

        result = {
            'total_value': balance.total_value,
            'cash': balance.cash,
            'holdings': []
        }

        for holding in balance.holdings:
            result['holdings'].append({
                'code': holding.code,
                'name': holding.name,
                'quantity': holding.quantity,
                'avg_price': holding.avg_price,
                'current_price': holding.current_price,
                'value': holding.value,
                'profit_loss': holding.profit_loss,
                'profit_rate': holding.profit_rate
            })

        return result

    def _save_trade_history(self, stock_code: str, trade_type: str, quantity: int,
                           price: int, trading_method: str, strategy_name: str = None,
                           profit_loss: int = 0, profit_rate: float = 0.0):
        """trade_history 테이블에 저장"""
        cursor = self.conn.cursor()

        # 종목명 조회
        cursor.execute("SELECT name FROM stocks WHERE code = %s", (stock_code,))
        stock_name = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO trade_history (
                stock_code, stock_name, trade_time, trade_type, quantity, price,
                total_amount, trading_method, profit_loss, profit_rate, strategy_name
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            stock_code,
            stock_name,
            datetime.now(),
            trade_type,
            quantity,
            price,
            quantity * price,
            trading_method,
            profit_loss,
            profit_rate,
            strategy_name
        ))

        self.conn.commit()
        print(f"✅ {trade_type} 주문 기록 저장: {stock_name} {quantity}주 @ {price:,}원")

    def _get_avg_buy_price(self, stock_code: str) -> int:
        """평균 매수가 조회"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT avg_price FROM stock_assets WHERE code = %s", (stock_code,))
        result = cursor.fetchone()
        return result[0] if result else 0


# 사용 예시
if __name__ == "__main__":
    db_config = {
        'dbname': 'stock_investment_db',
        'user': 'wonny',
        'host': 'localhost'
    }

    api = KISAPIFetcher(db_config)
    api.connect_db()

    # 삼성전자 1주 시장가 매수
    api.buy_market('005930', 1, strategy_name='테스트매수')

    # 잔고 조회
    balance = api.get_balance()
    print(balance)
```

---

### 3. Gemini 프롬프트 최적화 (5분)

#### src/ai/sentiment_analyzer.py

```python
"""
Gemini 감성 분석
- FinGPT 프롬프트 템플릿 참고
- 한국어 최적화
- recommendation_history 자동 저장
"""

import google.generativeai as genai
from typing import Dict, List
import psycopg2
from datetime import datetime


# 한국어 감성 분석 프롬프트
SENTIMENT_PROMPT = """
다음 뉴스 제목의 감성을 분석하세요.
반드시 {긍정/중립/부정} 중 하나만 선택하세요.

뉴스 제목: {news_headline}

분석 과정:
1. 주요 키워드 추출
2. 긍정적 요소 / 부정적 요소 파악
3. 최종 감성 판단

답변 (긍정/중립/부정만 출력):
"""


class SentimentAnalyzer:
    """Gemini 감성 분석기"""

    def __init__(self, api_key: str, db_config: dict):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.db_config = db_config
        self.conn = None

    def connect_db(self):
        """PostgreSQL 연결"""
        self.conn = psycopg2.connect(**self.db_config)

    def analyze_sentiment(self, news_headline: str) -> str:
        """뉴스 제목 감성 분석"""
        prompt = SENTIMENT_PROMPT.format(news_headline=news_headline)

        try:
            response = self.model.generate_content(prompt)
            sentiment = response.text.strip().lower()

            # 정규화
            if '긍정' in sentiment:
                return 'positive'
            elif '부정' in sentiment:
                return 'negative'
            else:
                return 'neutral'

        except Exception as e:
            print(f"❌ Gemini API 오류: {e}")
            return 'neutral'

    def analyze_batch(self, news_list: List[Dict]) -> List[Dict]:
        """배치 감성 분석"""
        for news in news_list:
            sentiment = self.analyze_sentiment(news['title'])
            news['sentiment'] = sentiment
            news['sentiment_score'] = {
                'positive': 1.0,
                'neutral': 0.0,
                'negative': -1.0
            }[sentiment]

        return news_list

    def save_to_recommendation_history(self, news: Dict, source_id: int):
        """recommendation_history 테이블에 저장"""
        cursor = self.conn.cursor()

        recommendation_type = 'buy' if news['sentiment'] == 'positive' else 'hold'

        cursor.execute("""
            INSERT INTO recommendation_history (
                stock_code, stock_name, recommendation_date,
                recommended_price, recommendation_type, source_id,
                gemini_reasoning, note
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            news['stock_code'],
            news['stock_name'],
            datetime.now().date(),
            0,  # 뉴스는 가격 정보 없음
            recommendation_type,
            source_id,
            f"Sentiment: {news['sentiment']} (Score: {news['sentiment_score']})",
            news['title']
        ))

        self.conn.commit()


# 사용 예시
if __name__ == "__main__":
    api_key = "YOUR_GEMINI_API_KEY"
    db_config = {
        'dbname': 'stock_investment_db',
        'user': 'wonny',
        'host': 'localhost'
    }

    analyzer = SentimentAnalyzer(api_key, db_config)
    analyzer.connect_db()

    # 뉴스 예시
    news_list = [
        {
            'stock_code': '005930',
            'stock_name': '삼성전자',
            'title': '삼성전자, 3분기 영업익 10조 원 돌파 전망'
        },
        {
            'stock_code': '005930',
            'stock_name': '삼성전자',
            'title': '삼성전자 반도체 부문, 재고 부담 지속'
        }
    ]

    # 감성 분석
    news_list = analyzer.analyze_batch(news_list)

    # DB 저장
    for news in news_list:
        analyzer.save_to_recommendation_history(news, source_id=1)  # Gemini_AI
        print(f"{news['title']}: {news['sentiment']}")
```

---

## 📚 참고 자료

### 오픈소스 프로젝트

1. **RLTrader (강화학습)**
   - Repository: https://github.com/quantylab/rltrader
   - 교과서급 프로젝트, 데이터 관리 구조 참고

2. **Korea Investment API (공식)**
   - Repository: https://github.com/koreainvestment/open-trading-api
   - 공식 예제, LLM 통합 예제

3. **Python-KIS (래퍼 라이브러리)**
   - Repository: https://github.com/Soju06/python-kis
   - 복구 가능 WebSocket, 타입 힌트 지원

4. **PyKIS (래퍼 라이브러리)**
   - Repository: https://github.com/pjueon/pykis
   - 간편한 API, 파일 기반 인증

5. **FinanceDataReader**
   - Repository: https://github.com/FinanceData/FinanceDataReader
   - 종목 리스트, OHLCV, 글로벌 시장

6. **FinGPT**
   - Repository: https://github.com/AI4Finance-Foundation/FinGPT
   - LLM 금융 분석, 프롬프트 템플릿

7. **KIS Developers 포털**
   - URL: https://apiportal.koreainvestment.com/intro
   - API 문서, 모의투자 계정 발급

### 추가 리소스

- **pandas-ta**: https://github.com/twopirllc/pandas-ta (기술 지표)
- **APScheduler**: https://apscheduler.readthedocs.io (스케줄링)
- **Prometheus**: https://prometheus.io (모니터링)
- **Grafana**: https://grafana.com (대시보드)

---

## ✅ 다음 단계

### 즉시 시작 가능

1. **FinanceDataReader 통합** (가장 쉬움, 5분)
   ```bash
   pip install finance-datareader pandas-ta
   python scripts/initialize_stocks.py
   ```

2. **Korea Investment API 연동** (실전 필수, 10분)
   ```bash
   pip install python-kis
   # KIS Developers 포털에서 계정 발급
   python src/fetchers/tier2_official_apis/kis_api_fetcher.py
   ```

3. **Gemini 프롬프트 최적화** (AI 고도화, 5분)
   ```bash
   python src/ai/sentiment_analyzer.py
   ```

### 추천 순서

```yaml
Week 1:
  Day 1-2: FinanceDataReader 통합 (종목 리스트, 일봉 수집)
  Day 3-5: Korea Investment API 연동 (WebSocket, REST API)
  Day 6-7: 통합 테스트 및 버그 수정

Week 2:
  Day 8-10: Gemini 감성 분석 파이프라인
  Day 11-14: 정확도 검증 시스템 구축

Week 3-4:
  Day 15-21: RLTrader A2C 에이전트 학습
  Day 22-28: 백테스팅 및 파라미터 튜닝

Week 5-6:
  Day 29-35: 실시간 자동매매 시스템 통합
  Day 36-42: 모의투자 실전 테스트
```

---

**작성일**: 2025-11-24 11:29:49
**작성자**: wonny
**버전**: 1.0
**상태**: Active
