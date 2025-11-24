---
created: 2025-11-24 11:29:49
updated: 2025-11-24 11:29:49
tags: [commands, cli, implementation, user-interface]
author: wonny
status: active
---

# 사용자 명령어 구현 계획

> 6개 핵심 명령어 구현 로드맵 및 기술 스펙

## 📋 목차

1. [명령어 개요](#명령어-개요)
2. [아키텍처 설계](#아키텍처-설계)
3. [명령어별 구현 계획](#명령어별-구현-계획)
4. [CLI 인터페이스](#cli-인터페이스)
5. [구현 우선순위](#구현-우선순위)

---

## 🎯 명령어 개요

### 6개 핵심 명령어

| No  | 명령어               | 기능               | 난이도    | 우선순위 |
| --- | -------------------- | ------------------ | --------- | -------- |
| 1   | `00종목등록해`       | 종목 수동 등록     | 🟢 Easy   | P1       |
| 2   | `거래 데이터 입력해` | 매매 기록 저장     | 🟡 Medium | P1       |
| 3   | `보유종목 분석해`    | AI 보유종목 분석   | 🟡 Medium | P2       |
| 4   | `신규종목추천해`     | AI 신규종목 추천   | 🔴 Hard   | P2       |
| 5   | `1min 수집 실행해`   | 실시간 데이터 수집 | 🟢 Easy   | P1       |
| 6   | `20분마다 의견 줘`   | 자동 분석 스케줄러 | 🟡 Medium | P3       |

---

## 🏗️ 아키텍처 설계

### 전체 구조

```
사용자 입력 (자연어 명령어)
    ↓
CLI 인터페이스 (Typer 또는 Click)
    ↓
명령어 파서 (정규표현식 또는 LLM)
    ↓
명령어 핸들러 (각 명령어별 로직)
    ↓
데이터베이스 (PostgreSQL)
    ↓
결과 출력 (터미널 또는 Slack)
```

### 기술 스택

```yaml
CLI Framework:
  - Typer (추천) - 타입 힌트 기반, 자동 문서 생성
  - Click (대안) - 성숙한 생태계

명령어 파싱:
  - 정규표현식 (간단한 패턴)
  - Gemini API (복잡한 자연어)

스케줄러:
  - APScheduler (20분 주기 실행)

데이터베이스:
  - asyncpg (비동기 PostgreSQL)
```

---

## 📝 명령어별 구현 계획

### 1️⃣ 명령어: "00종목등록해"

#### 요구사항

```
입력 예시:
  - "005930 종목등록해"
  - "삼성전자 등록해"
  - "종목코드 000660 등록"

출력 예시:
  - "✅ 삼성전자(005930) 종목이 등록되었습니다."
  - "⚠️ 이미 등록된 종목입니다."
```

#### 구현 스펙

**파일**: `src/commands/register_stock.py`

```python
import typer
from typing import Optional
import asyncpg

app = typer.Typer()


async def register_stock(code: str, name: Optional[str] = None):
    """
    종목 등록

    Args:
        code: 종목코드 (6자리)
        name: 종목명 (선택, 없으면 FinanceDataReader로 조회)
    """
    # 1. 종목코드 검증 (6자리)
    if len(code) != 6:
        typer.echo("❌ 종목코드는 6자리여야 합니다.")
        return

    # 2. 종목명 조회 (없으면 FDR로 자동 조회)
    if not name:
        import FinanceDataReader as fdr
        krx = fdr.StockListing('KRX')
        stock = krx[krx['Code'] == code]
        if stock.empty:
            typer.echo(f"❌ {code} 종목을 찾을 수 없습니다.")
            return
        name = stock.iloc[0]['Name']

    # 3. DB 저장
    conn = await asyncpg.connect(**db_config)
    try:
        await conn.execute("""
            INSERT INTO stocks (code, name, market, category, is_active)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (code) DO UPDATE
            SET name = EXCLUDED.name,
                updated_at = CURRENT_TIMESTAMP
        """, code, name, 'KRX', 'Growth', True)

        typer.echo(f"✅ {name}({code}) 종목이 등록되었습니다.")

    except Exception as e:
        typer.echo(f"❌ 등록 실패: {e}")
    finally:
        await conn.close()


@app.command()
def register(code: str, name: Optional[str] = None):
    """종목 등록 명령어"""
    import asyncio
    asyncio.run(register_stock(code, name))


if __name__ == "__main__":
    app()
```

#### 사용법

```bash
# 종목코드만 입력 (종목명 자동 조회)
python src/commands/register_stock.py register 005930

# 종목코드 + 종목명
python src/commands/register_stock.py register 005930 "삼성전자"
```

---

### 2️⃣ 명령어: "거래 데이터 입력해"

#### 요구사항

```
입력 예시:
  - "삼성전자 10주 65000원에 매수"
  - "SK하이닉스 5주 시장가 매도, 수익률 +8%"
  - 거래 내역 복사/붙여넣기 (CSV 형식)

출력 예시:
  - "✅ 매수 기록이 저장되었습니다: 삼성전자 10주 @ 65,000원"
```

#### 구현 스펙

**파일**: `src/commands/input_trade.py`

```python
import typer
import re
from datetime import datetime
import asyncpg

app = typer.Typer()


class TradeParser:
    """거래 데이터 파서"""

    @staticmethod
    def parse_simple_text(text: str) -> dict:
        """
        간단한 텍스트 파싱
        예: "삼성전자 10주 65000원에 매수"
        """
        # 패턴 1: 종목명 + 수량 + 가격 + 매수/매도
        pattern = r'(\S+)\s+(\d+)주\s+(\d+)원에?\s+(매수|매도)'
        match = re.search(pattern, text)

        if match:
            return {
                'stock_name': match.group(1),
                'quantity': int(match.group(2)),
                'price': int(match.group(3)),
                'trade_type': 'BUY' if match.group(4) == '매수' else 'SELL'
            }

        # 패턴 2: 시장가
        pattern = r'(\S+)\s+(\d+)주\s+시장가\s+(매수|매도)'
        match = re.search(pattern, text)

        if match:
            return {
                'stock_name': match.group(1),
                'quantity': int(match.group(2)),
                'price': None,  # 시장가는 나중에 현재가로
                'trade_type': 'BUY' if match.group(3) == '매수' else 'SELL'
            }

        return None

    @staticmethod
    async def parse_with_gemini(text: str) -> dict:
        """
        Gemini API로 복잡한 텍스트 파싱
        """
        import google.generativeai as genai

        prompt = f"""
다음 거래 내역을 JSON 형식으로 파싱하세요.

거래 내역: {text}

JSON 형식:
{{
    "stock_name": "종목명",
    "quantity": 수량,
    "price": 가격,
    "trade_type": "BUY" 또는 "SELL"
}}

시장가인 경우 price는 null로 설정하세요.
"""

        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)

        # JSON 파싱
        import json
        try:
            return json.loads(response.text)
        except:
            return None


async def input_trade(text: str, use_gemini: bool = False):
    """
    거래 데이터 입력

    Args:
        text: 거래 내역 텍스트
        use_gemini: Gemini API 사용 여부
    """
    parser = TradeParser()

    # 1. 파싱
    if use_gemini:
        trade_data = await parser.parse_with_gemini(text)
    else:
        trade_data = parser.parse_simple_text(text)

    if not trade_data:
        typer.echo("❌ 거래 내역을 파싱할 수 없습니다.")
        return

    # 2. 종목코드 조회
    conn = await asyncpg.connect(**db_config)

    stock_code = await conn.fetchval(
        "SELECT code FROM stocks WHERE name = $1",
        trade_data['stock_name']
    )

    if not stock_code:
        typer.echo(f"❌ {trade_data['stock_name']} 종목을 찾을 수 없습니다.")
        await conn.close()
        return

    # 3. 시장가인 경우 현재가 조회
    if trade_data['price'] is None:
        trade_data['price'] = await conn.fetchval(
            "SELECT price FROM stock_assets WHERE code = $1",
            stock_code
        )

    # 4. DB 저장
    try:
        await conn.execute("""
            INSERT INTO trade_history (
                stock_code, stock_name, trade_time, trade_type,
                quantity, price, total_amount, trading_method
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
            stock_code,
            trade_data['stock_name'],
            datetime.now(),
            trade_data['trade_type'],
            trade_data['quantity'],
            trade_data['price'],
            trade_data['quantity'] * trade_data['price'],
            'Manual'
        )

        typer.echo(
            f"✅ {trade_data['trade_type']} 기록 저장: "
            f"{trade_data['stock_name']} {trade_data['quantity']}주 "
            f"@ {trade_data['price']:,}원"
        )

    except Exception as e:
        typer.echo(f"❌ 저장 실패: {e}")
    finally:
        await conn.close()


@app.command()
def input(text: str, gemini: bool = False):
    """거래 데이터 입력 명령어"""
    import asyncio
    asyncio.run(input_trade(text, gemini))


if __name__ == "__main__":
    app()
```

#### 사용법

```bash
# 간단한 텍스트 파싱
python src/commands/input_trade.py input "삼성전자 10주 65000원에 매수"

# Gemini API 사용 (복잡한 텍스트)
python src/commands/input_trade.py input "삼성전자를 오늘 아침에 10주 65000원에 샀어요" --gemini
```

---

### 3️⃣ 명령어: "보유종목 분석해"

#### 요구사항

```
입력: "보유종목 분석해"

출력 예시:
  보유종목 분석 결과 (2025-11-24 11:30)

  ✅ 삼성전자 (005930)
    - 보유: 10주 @ 평단 64,500원
    - 현재가: 65,000원 (+0.78%)
    - 평가금액: 650,000원 (수익 +5,000원)
    - AI 의견: 보유 추천
    - 근거: RSI 과매수 구간 진입, 외국인 순매수 지속

  ⚠️ SK하이닉스 (000660)
    - 보유: 5주 @ 평단 128,000원
    - 현재가: 125,000원 (-2.34%)
    - 평가금액: 625,000원 (손실 -15,000원)
    - AI 의견: 손절 검토
    - 근거: 5일 이평선 하향 돌파, 거래량 감소
```

#### 구현 스펙

**파일**: `src/commands/analyze_holdings.py`

```python
import typer
from typing import List, Dict
import asyncpg
import google.generativeai as genai

app = typer.Typer()


HOLDINGS_ANALYSIS_PROMPT = """
다음 보유 종목을 분석하고 매매 의견을 제시하세요.

종목: {stock_name} ({stock_code})
보유 수량: {quantity}주
평균 매수가: {avg_price:,}원
현재가: {current_price:,}원
수익률: {return_pct:.2f}%

기술적 지표:
- RSI(14): {rsi}
- MACD: {macd}
- 볼린저밴드 위치: {bb_position}%

수급 데이터 (최근 5일):
- 외국인 순매수: {foreigner_net:,}원
- 기관 순매수: {institution_net:,}원

의견 (보유/매도/손절검토/추가매수 중 선택):
근거 (200자 이내):
"""


async def analyze_single_stock(conn, stock_code: str) -> Dict:
    """단일 종목 분석"""

    # 1. 보유 정보 조회
    holding = await conn.fetchrow("""
        SELECT sa.*, s.name
        FROM stock_assets sa
        JOIN stocks s ON sa.code = s.code
        WHERE sa.code = $1 AND sa.quantity > 0
    """, stock_code)

    if not holding:
        return None

    # 2. 기술적 지표 조회 (최근)
    indicators = await conn.fetchrow("""
        SELECT rsi, macd, bb_position
        FROM stock_prices_10min
        WHERE stock_code = $1
        ORDER BY timestamp DESC
        LIMIT 1
    """, stock_code)

    # 3. 수급 데이터 조회 (최근 5일)
    supply = await conn.fetchrow("""
        SELECT foreigner_net_buy, institution_net_buy
        FROM stock_supply_demand
        WHERE stock_code = $1 AND period_days = 5
        ORDER BY timestamp DESC
        LIMIT 1
    """, stock_code)

    # 4. Gemini 분석
    return_pct = ((holding['price'] - holding['avg_price']) / holding['avg_price']) * 100

    prompt = HOLDINGS_ANALYSIS_PROMPT.format(
        stock_name=holding['name'],
        stock_code=stock_code,
        quantity=holding['quantity'],
        avg_price=holding['avg_price'],
        current_price=holding['price'],
        return_pct=return_pct,
        rsi=indicators['rsi'] if indicators else 'N/A',
        macd=indicators['macd'] if indicators else 'N/A',
        bb_position=indicators['bb_position'] if indicators else 'N/A',
        foreigner_net=supply['foreigner_net_buy'] if supply else 0,
        institution_net=supply['institution_net_buy'] if supply else 0
    )

    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)

    return {
        'stock_name': holding['name'],
        'stock_code': stock_code,
        'quantity': holding['quantity'],
        'avg_price': holding['avg_price'],
        'current_price': holding['price'],
        'return_pct': return_pct,
        'ai_opinion': response.text
    }


async def analyze_all_holdings():
    """전체 보유종목 분석"""
    conn = await asyncpg.connect(**db_config)

    # 보유 종목 목록 조회
    holdings = await conn.fetch("""
        SELECT code FROM stock_assets WHERE quantity > 0
    """)

    typer.echo(f"\n📊 보유종목 분석 결과 ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n")

    for holding in holdings:
        result = await analyze_single_stock(conn, holding['code'])

        if result:
            # 출력 포맷팅
            status = "✅" if result['return_pct'] >= 0 else "⚠️"

            typer.echo(f"{status} {result['stock_name']} ({result['stock_code']})")
            typer.echo(f"  - 보유: {result['quantity']}주 @ 평단 {result['avg_price']:,}원")
            typer.echo(f"  - 현재가: {result['current_price']:,}원 ({result['return_pct']:+.2f}%)")
            typer.echo(f"  - AI 의견:\n{result['ai_opinion']}\n")

    await conn.close()


@app.command()
def analyze():
    """보유종목 분석 명령어"""
    import asyncio
    asyncio.run(analyze_all_holdings())


if __name__ == "__main__":
    app()
```

#### 사용법

```bash
python src/commands/analyze_holdings.py analyze
```

---

### 4️⃣ 명령어: "신규종목추천해"

#### 요구사항

```
입력: "신규종목추천해"

출력 예시:
  🎯 신규종목 추천 (2025-11-24)

  1. LG전자 (066570)
     - 추천가: 128,000원
     - 목표가: 145,000원 (+13.3%)
     - 근거:
       * 실적 개선 기대 (TV 사업 흑자 전환)
       * 외국인 순매수 3일 연속
       * RSI 30 과매도 구간 (반등 가능성)
     - 리스크: 환율 변동성

  2. 현대차 (005380)
     - 추천가: 245,000원
     - 목표가: 270,000원 (+10.2%)
     - 근거: ...
```

#### 구현 스펙

**파일**: `src/commands/recommend_stocks.py`

```python
import typer
from typing import List
import asyncpg
import google.generativeai as genai
from datetime import datetime, timedelta

app = typer.Typer()


NEW_STOCK_RECOMMENDATION_PROMPT = """
한국 주식 시장에서 투자할 만한 신규 종목 3개를 추천하세요.

현재 시장 상황:
- KOSPI: {kospi_index}
- KOSDAQ: {kosdaq_index}
- 최근 트렌드: {market_trend}

제외할 종목 (이미 보유 중):
{holding_codes}

추천 기준:
1. 최근 실적 개선 또는 호재
2. 기술적 지표 긍정적 (RSI, MACD)
3. 외국인/기관 순매수
4. 거래량 증가

출력 형식 (3개 종목):
1. 종목명 (종목코드)
   - 추천가: X원
   - 목표가: Y원 (+Z%)
   - 근거: [200자 이내]
   - 리스크: [100자 이내]
"""


async def get_market_status(conn):
    """시장 상황 조회"""
    # KOSPI, KOSDAQ 지수 조회 (임시)
    return {
        'kospi_index': 2500,  # 실제로는 API에서 조회
        'kosdaq_index': 850,
        'market_trend': '상승세'
    }


async def get_holding_codes(conn) -> List[str]:
    """보유 종목 코드 조회"""
    rows = await conn.fetch("""
        SELECT code FROM stock_assets WHERE quantity > 0
    """)
    return [row['code'] for row in rows]


async def recommend_new_stocks():
    """신규 종목 추천"""
    conn = await asyncpg.connect(**db_config)

    # 1. 시장 상황 조회
    market = await get_market_status(conn)

    # 2. 보유 종목 제외
    holding_codes = await get_holding_codes(conn)

    # 3. Gemini 추천
    prompt = NEW_STOCK_RECOMMENDATION_PROMPT.format(
        kospi_index=market['kospi_index'],
        kosdaq_index=market['kosdaq_index'],
        market_trend=market['market_trend'],
        holding_codes=', '.join(holding_codes) if holding_codes else '없음'
    )

    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)

    # 4. 출력
    typer.echo(f"\n🎯 신규종목 추천 ({datetime.now().strftime('%Y-%m-%d')})\n")
    typer.echo(response.text)

    # 5. recommendation_history에 저장
    await conn.execute("""
        INSERT INTO recommendation_history (
            stock_code, stock_name, recommendation_date,
            recommended_price, recommendation_type, source_id, gemini_reasoning
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
    """, '000000', '신규추천', datetime.now().date(), 0, 'buy', 1, response.text)

    await conn.close()


@app.command()
def recommend():
    """신규종목 추천 명령어"""
    import asyncio
    asyncio.run(recommend_new_stocks())


if __name__ == "__main__":
    app()
```

#### 사용법

```bash
python src/commands/recommend_stocks.py recommend
```

---

### 5️⃣ 명령어: "1min 종목 가격, 거래량 수집 실행해"

#### 요구사항

```
입력: "1min 수집 시작"

출력:
  🚀 실시간 데이터 수집 시작

  [11:30:01] 삼성전자(005930): 65,000원 (거래량: 1,234,567)
  [11:30:02] SK하이닉스(000660): 125,000원 (거래량: 567,890)
  [11:31:01] 삼성전자(005930): 65,100원 (거래량: 1,235,000)
  ...

  Ctrl+C to stop
```

#### 구현 스펙

**파일**: `src/commands/collect_realtime.py`

```python
import typer
from pykis import PyKis
import asyncpg
from datetime import datetime

app = typer.Typer()


async def collect_realtime_data(stock_codes: List[str]):
    """실시간 데이터 수집"""

    conn = await asyncpg.connect(**db_config)
    kis = PyKis()

    typer.echo("\n🚀 실시간 데이터 수집 시작\n")

    for code in stock_codes:
        stock = kis.stock(code)

        @stock.on_price
        async def on_price(price):
            """실시간 가격 수신 콜백"""
            timestamp = datetime.now()

            # DB 저장
            await conn.execute("""
                INSERT INTO min_ticks (stock_code, timestamp, price, volume)
                VALUES ($1, $2, $3, $4)
            """, price.code, timestamp, price.price, price.volume)

            # 출력
            typer.echo(
                f"[{timestamp.strftime('%H:%M:%S')}] "
                f"{price.name}({price.code}): "
                f"{price.price:,}원 (거래량: {price.volume:,})"
            )

    typer.echo("\nCtrl+C to stop")

    try:
        # 무한 실행 (Ctrl+C로 종료)
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        typer.echo("\n\n✅ 수집 종료")
    finally:
        await conn.close()


@app.command()
def collect():
    """실시간 데이터 수집 명령어"""
    import asyncio

    # 보유 종목 코드 조회
    conn = asyncpg.connect(**db_config)
    codes = conn.fetch("SELECT code FROM stock_assets WHERE quantity > 0")
    stock_codes = [row['code'] for row in codes]
    conn.close()

    asyncio.run(collect_realtime_data(stock_codes))


if __name__ == "__main__":
    app()
```

#### 사용법

```bash
# 보유 종목 자동 수집
python src/commands/collect_realtime.py collect

# Ctrl+C로 종료
```

---

### 6️⃣ 명령어: "20분마다 보유종목 실시간으로 파악해 매도매수유지관망등의 의견 줘"

#### 요구사항

```
입력: "20분 자동 분석 시작"

출력 (20분마다):
  ⏰ 20분 주기 분석 (11:40)

  ✅ 삼성전자 (005930)
    - 의견: 보유
    - 현재가: 65,100원 (+0.15% from 20분전)
    - 근거: 횡보 중, 추가 변동 기다리기

  ⚠️ SK하이닉스 (000660)
    - 의견: 손절 검토
    - 현재가: 123,000원 (-1.60% from 20분전)
    - 근거: 하락 추세 지속, 손절가 근접
```

#### 구현 스펙

**파일**: `src/commands/auto_analysis.py`

```python
import typer
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncpg
import google.generativeai as genai
from datetime import datetime

app = typer.Typer()


PERIODIC_ANALYSIS_PROMPT = """
다음 종목의 20분 주기 분석 및 매매 의견을 제시하세요.

종목: {stock_name} ({stock_code})
현재가: {current_price:,}원
20분 전 가격: {prev_price:,}원
변동률: {change_pct:+.2f}%

평균 매수가: {avg_price:,}원
수익률: {return_pct:+.2f}%

손절가: {stop_loss:,}원
1차 익절가: {take_profit_1:,}원

의견 (보유/매도/손절/추가매수/관망 중 선택):
근거 (100자 이내):
"""


async def analyze_once():
    """1회 분석 (20분마다 실행)"""
    conn = await asyncpg.connect(**db_config)

    typer.echo(f"\n⏰ 20분 주기 분석 ({datetime.now().strftime('%H:%M')})\n")

    # 보유 종목 조회
    holdings = await conn.fetch("""
        SELECT sa.*, s.name, so.stop_loss_price, so.take_profit_1_price
        FROM stock_assets sa
        JOIN stocks s ON sa.code = s.code
        LEFT JOIN stock_opinions so ON sa.code = so.stock_code
        WHERE sa.quantity > 0
    """)

    for holding in holdings:
        # 20분 전 가격 조회
        prev_price = await conn.fetchval("""
            SELECT price FROM min_ticks
            WHERE stock_code = $1
              AND timestamp <= NOW() - INTERVAL '20 minutes'
            ORDER BY timestamp DESC
            LIMIT 1
        """, holding['code'])

        if not prev_price:
            prev_price = holding['price']

        # 변동률 계산
        change_pct = ((holding['price'] - prev_price) / prev_price) * 100
        return_pct = ((holding['price'] - holding['avg_price']) / holding['avg_price']) * 100

        # Gemini 분석
        prompt = PERIODIC_ANALYSIS_PROMPT.format(
            stock_name=holding['name'],
            stock_code=holding['code'],
            current_price=holding['price'],
            prev_price=prev_price,
            change_pct=change_pct,
            avg_price=holding['avg_price'],
            return_pct=return_pct,
            stop_loss=holding['stop_loss_price'] or 0,
            take_profit_1=holding['take_profit_1_price'] or 0
        )

        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)

        # 출력
        status = "✅" if return_pct >= 0 else "⚠️"
        typer.echo(f"{status} {holding['name']} ({holding['code']})")
        typer.echo(f"  - 현재가: {holding['price']:,}원 ({change_pct:+.2f}% from 20분전)")
        typer.echo(f"  - AI 의견:\n{response.text}\n")

    await conn.close()


async def start_scheduler():
    """스케줄러 시작"""
    scheduler = AsyncIOScheduler()

    # 20분마다 실행
    scheduler.add_job(analyze_once, 'interval', minutes=20)

    # 즉시 1회 실행
    await analyze_once()

    scheduler.start()

    typer.echo("\n🔄 20분 주기 자동 분석 시작 (Ctrl+C to stop)\n")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        typer.echo("\n\n✅ 자동 분석 종료")
        scheduler.shutdown()


@app.command()
def start():
    """20분 주기 자동 분석 시작"""
    import asyncio
    asyncio.run(start_scheduler())


if __name__ == "__main__":
    app()
```

#### 사용법

```bash
# 자동 분석 시작 (20분마다)
python src/commands/auto_analysis.py start

# Ctrl+C로 종료
```

---

## 🖥️ CLI 인터페이스

### 통합 CLI

**파일**: `cli.py` (프로젝트 루트)

```python
import typer
from src.commands import (
    register_stock,
    input_trade,
    analyze_holdings,
    recommend_stocks,
    collect_realtime,
    auto_analysis
)

app = typer.Typer()

# 서브 명령어 등록
app.add_typer(register_stock.app, name="register", help="종목 등록")
app.add_typer(input_trade.app, name="trade", help="거래 데이터 입력")
app.add_typer(analyze_holdings.app, name="analyze", help="보유종목 분석")
app.add_typer(recommend_stocks.app, name="recommend", help="신규종목 추천")
app.add_typer(collect_realtime.app, name="collect", help="실시간 데이터 수집")
app.add_typer(auto_analysis.app, name="auto", help="20분 주기 자동 분석")


@app.command()
def version():
    """버전 정보"""
    typer.echo("joungwon.stocks v1.0.0")


if __name__ == "__main__":
    app()
```

### 사용법

```bash
# 종목 등록
python cli.py register 005930

# 거래 입력
python cli.py trade "삼성전자 10주 65000원에 매수"

# 보유종목 분석
python cli.py analyze

# 신규종목 추천
python cli.py recommend

# 실시간 수집
python cli.py collect

# 자동 분석 (20분 주기)
python cli.py auto
```

---

## 🎯 구현 우선순위

### Phase 1 (Week 1) - 기본 명령어

```yaml
Priority: P1 (High)

Tasks:
  - ✅ CLI 프레임워크 설정 (Typer)
  - ✅ 명령어 1: 종목 등록
  - ✅ 명령어 2: 거래 데이터 입력 (간단한 파싱)
  - ✅ 명령어 5: 실시간 데이터 수집

Deliverables:
  - cli.py (통합 CLI)
  - src/commands/register_stock.py
  - src/commands/input_trade.py
  - src/commands/collect_realtime.py

Estimated Time: 3-5 days
```

### Phase 2 (Week 2) - AI 분석

```yaml
Priority: P2 (Medium)

Tasks:
  - ✅ 명령어 3: 보유종목 AI 분석
  - ✅ 명령어 4: 신규종목 AI 추천
  - ✅ Gemini 프롬프트 최적화

Deliverables:
  - src/commands/analyze_holdings.py
  - src/commands/recommend_stocks.py
  - config/prompts/ (프롬프트 템플릿)

Estimated Time: 5-7 days
```

### Phase 3 (Week 3) - 자동화

```yaml
Priority: P3 (Low)

Tasks:
  - ✅ 명령어 6: 20분 주기 자동 분석
  - ✅ APScheduler 통합
  - ✅ Slack 알림 (선택)

Deliverables:
  - src/commands/auto_analysis.py
  - src/monitoring/slack_notifier.py (선택)

Estimated Time: 3-5 days
```

---

## 📦 의존성 추가

**requirements.txt에 추가**:

```txt
# CLI Framework
typer[all]==0.9.0
rich==13.7.0

# Scheduler
apscheduler==3.10.4

# Korea Investment API
python-kis==0.1.0

# Gemini API
google-generativeai==0.3.0

# Database
asyncpg==0.29.0

# Data
FinanceDataReader==0.9.50
pandas-ta==0.3.14b0
```

---

## ✅ 테스트 계획

### 단위 테스트

```python
# tests/unit/test_commands.py

import pytest
from src.commands.register_stock import register_stock
from src.commands.input_trade import TradeParser


@pytest.mark.asyncio
async def test_register_stock():
    """종목 등록 테스트"""
    result = await register_stock('005930', '삼성전자')
    assert result is True


def test_trade_parser():
    """거래 데이터 파싱 테스트"""
    parser = TradeParser()
    result = parser.parse_simple_text("삼성전자 10주 65000원에 매수")

    assert result['stock_name'] == '삼성전자'
    assert result['quantity'] == 10
    assert result['price'] == 65000
    assert result['trade_type'] == 'BUY'
```

### 통합 테스트

```python
# tests/integration/test_cli.py

from typer.testing import CliRunner
from cli import app

runner = CliRunner()


def test_register_command():
    """CLI 종목 등록 테스트"""
    result = runner.invoke(app, ["register", "005930"])
    assert result.exit_code == 0
    assert "✅" in result.stdout


def test_analyze_command():
    """CLI 보유종목 분석 테스트"""
    result = runner.invoke(app, ["analyze"])
    assert result.exit_code == 0
    assert "📊" in result.stdout
```

---

## 📚 참고 자료

- [Typer 문서](https://typer.tiangolo.com/)
- [APScheduler 가이드](https://apscheduler.readthedocs.io/)
- [python-kis GitHub](https://github.com/Soju06/python-kis)
- [Gemini API 문서](https://ai.google.dev/docs)

---

**작성일**: 2025-11-24 11:29:49
**작성자**: wonny
**버전**: 1.0
**상태**: Planning Phase
