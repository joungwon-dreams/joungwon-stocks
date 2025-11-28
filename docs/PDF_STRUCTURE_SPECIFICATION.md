# PDF 문서 구조 명세서 (Structure Specification)

> **CRITICAL WARNING**: 이 문서에 정의된 PDF 구조는 **절대 변경 금지**입니다.
> 구조 변경이 필요한 경우 반드시 사용자 승인을 받아야 합니다.
>
> **Last Updated**: 2025-11-28 08:41:50
> **Version**: 1.0.0 (Locked)
> **Maintainer**: wonny

---

## 1. realtime_dashboard.pdf (실시간 대시보드)

### 1.1 개요
- **생성 스크립트**: `scripts/generate_realtime_dashboard_terminal_style.py`
- **호출 스크립트**: `cron/1min.py` (1분 간격 실행)
- **출력 위치**: `reports/holding_stock/realtime_dashboard.pdf`
- **페이지 크기**: A4 Landscape (가로 방향)
- **폰트**: AppleGothic (한글), 크기 12pt

### 1.2 페이지 구조

#### 페이지 1-2: 요약 대시보드 (기존 PDF에서 병합)
- holding_stock/realtime_dashboard.pdf의 처음 2페이지 그대로 유지
- 전체 보유종목 요약 정보

#### 페이지 3+: 종목별 상세 (각 종목당 1페이지)

**헤더 영역** (y: page_height - 30):
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 {종목명} ({종목코드}) ⏰ YYYY-MM-DD HH:MM  (수집: N)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
- 종목명: 28pt, 수익률에 따라 색상 (양수: 빨강, 음수: 파랑)
- 시간 정보: 12pt, 검정색

**가격 정보 영역**:
```
시가: XX,XXX | 현재가: XX,XXX +X.XX% 🔺 | 거래량: XXX,XXX
최고: XX,XXX +X.XX% 🔺 | 최저: XX,XXX -X.XX% 🔹
평단가: XX,XXX +X.XX%🔺 XX주 | XX,XXX,XXX +XXX,XXX원🔺
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
- 색상 규칙: 양수 = 빨강(COLOR_RED), 음수 = 파랑(COLOR_BLUE), 0 = 검정

**테이블 헤더** (고정):
```
시간    거래량        현재가      직전        변동률      전일        전일률      평단가      평가율
----------------------------------------------------------------------------------------------------------------------------
```

**틱 데이터 행** (최대 20개):
- 컬럼 순서: 시간 → 거래량 → 현재가 → 직전 → 변동률 → 전일 → 전일률 → 평단가 → 평가율
- 거래량: 이전 대비 증가율(%) 표시 (빨강)
- 가격 변동: 🔺(상승, 빨강), 🔹(하락, 파랑), ⚪(변동없음)

**푸터**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 1.3 데이터 소스
- `min_ticks` 테이블: 분봉 데이터
- `stock_assets` 테이블: 보유 정보

### 1.4 색상 코드 (절대 변경 금지)
```python
COLOR_RED = colors.red      # 상승
COLOR_BLUE = colors.blue    # 하락
COLOR_BLACK = colors.black  # 기본
```

---

## 2. 종목명.pdf (개별 종목 리포트)

### 2.1 개요
- **생성 스크립트**: `scripts/gemini/generate_pdf_report.py`
- **호출 스크립트**: `cron/10min.py` (10분 간격 실행)
- **출력 위치**: `reports/holding_stock/{종목명}.pdf`
- **페이지 크기**: A4 Portrait (세로 방향)
- **폰트**: AppleGothic (한글)

### 2.2 페이지 구조 (v1.0.0 - LOCKED)

#### 페이지 1: 핵심 정보

**헤더** (모든 페이지 공통):
- 좌측: `{종목명} ({종목코드})` - 16pt
- 우측: DATE / TIME / PAGE
- 하단: 2pt 검정선

**섹션 1: Sub-header**
```
Generative AI Equity Research
```
- Helvetica-Bold, 10pt, #555555

**섹션 2: Investment Opinion Box** (테이블)
```
┌─────────────────┬──────────┬──────────┬──────────┬────────┐
│ INVESTMENT      │ Current  │ Average  │ Target   │ Upside │
│ OPINION         │ Price    │ Price    │ Price    │        │
├─────────────────┼──────────┼──────────┼──────────┼────────┤
│ 🐂 STRONG BUY   │ XX,XXX   │ XX,XXX   │ XX,XXX   │ +XX.X% │
└─────────────────┴──────────┴──────────┴──────────┴────────┘
```
- 헤더 배경: opinion 색상 (RED/BLUE/GREY)
- 컬럼 너비: 4.5cm, 3.5cm, 3.5cm, 3.5cm, 2.5cm

**섹션 3: Key Metrics (주요 투자지표)**
- 제목: `📊 Key Metrics (주요 투자지표)` - #1565C0, 15pt
- 2x4 테이블: PER, PBR, ROE, Dividend Yield, Market Cap, Foreign Ratio, Sector, 52W High

**섹션 4: Company Overview (기업 개요)**
- 제목: `🏢 Company Overview (기업 개요)` - #1565C0, 15pt
- 본문: company_summary (최대 350자 + '...')

**섹션 5: Recent 2-Week Trend**
- 변화율 텍스트: `Change (2W): +X.XX%` - 12pt, 색상 적용
- 차트 이미지: `mini_2week_chart.png` - 14cm x 5.5cm

**섹션 6: AI Portfolio Feedback** (선택)
- 제목: `🤖 AI Portfolio Feedback` - #1565C0, 15pt
- 오늘의 전략 박스 (색상: 추천에 따라)
- 어제 회고 박스 (있는 경우)

**섹션 7: 투자의견 컨센서스**
- 제목: `투자의견 컨센서스 (기준:YY.MM.DD)` - #1565C0, 15pt
- create_consensus_detail_section() 결과

**섹션 8: 증권사 목표가** (테이블)
```
┌────────┬──────────┬────────┬─────────────┬────────┬──────────────┐
│ 일자   │ 목표주가 │ 이전대비│ 투자의견    │ 증권사 │ 리포트       │
├────────┼──────────┼────────┼─────────────┼────────┼──────────────┤
│ YY.MM.DD│ XXX,XXX │ ▲ X,XXX│ [바] [매수] │ XX증권 │ 제목...      │
└────────┴──────────┴────────┴─────────────┴────────┴──────────────┘
```
- 컬럼 너비: 2.0cm, 2.0cm, 1.5cm, 3.5cm, 1.5cm, 6.0cm

#### 페이지 2: 보유 현황 / 실시간 틱

**섹션 9: Holding Status (보유 현황)**
- 제목: `💼 Holding Status (보유 현황)` - #1565C0, 15pt
- create_holding_status_table() 결과

**섹션 10: Claude Code 선정 정보** (있는 경우)
- 제목: `🤖 Claude Code 선정 정보` - #1565C0, 15pt
- 선정일, 매수가, AI 점수, AI 등급 테이블
- 추천 이유 (gemini_reasoning)

**섹션 11: Real-time Ticks**
- 제목: `⏱️ Real-time Ticks` - #1565C0, 15pt
- create_stock_realtime_dashboard() 결과

#### 페이지 3: 주가 및 재무

**섹션 12: Price Trend (주가 추이)**
- 제목: `📈 Price Trend (주가 추이)` - #1565C0, 15pt
- 차트 이미지: `price_trend.png` - 16cm x 9cm

**섹션 13: Financial Performance (재무 실적)**
- 제목: `💰 Financial Performance (재무 실적)` - #1565C0, 15pt
- 차트 이미지: `financial_performance.png` - 16cm x 8cm
- 재무 테이블: Year, Revenue(억), Op. Profit(억), Net Profit(억), OPM(%)

#### 페이지 4: 수급 동향

**섹션 14: Investor Trends (수급 동향)**
- 제목: `👥 Investor Trends (수급 동향)` - #1565C0, 15pt
- 30일 차트: `investor_trends.png` - 16cm x 8cm
- 1년 차트: `investor_trends_year.png` - 16cm x 8cm
- 요약 텍스트: `최근 30일 순매수: 외국인 +X,XXX주 | 기관 +X,XXX주`

#### 페이지 5: 동종업계 비교

**섹션 15: 동종업계 비교**
- 제목: `동종업계 비교` - #1565C0, 15pt
- 차트 이미지: `peer_comparison.png` - 16cm x 8cm
- 비교 테이블: 기업명, PER, PBR, ROE(%)

#### 페이지 6+: 뉴스

**섹션 16: 최근 뉴스 분석**
- 제목: `최근 뉴스 분석` - 24pt, center
- 뉴스 카드 (최대 10개):
  ```
  ┌────────────────────────────────────────────────────────────────────┐
  │ X. 뉴스 제목                                                       │
  │ 일시: YYYY-MM-DD HH:MM | 출처: 언론사                               │
  │ 감성: 호재/악재/중립                                                │
  │ 요약: ...                                                          │
  │ 원문 보기 >>                                                        │
  └────────────────────────────────────────────────────────────────────┘
  ```
  - 감성 색상: 호재=#dc3545, 악재=#0056b3, 중립=#6c757d

**푸터** (마지막):
```
본 리포트는 AI 기반 자동 생성 리포트입니다. | 생성일시: YYYY-MM-DD HH:MM:SS
```
- 8pt, grey, center

### 2.3 차트 스펙

#### price_trend.png (주가 추이 120일)
- 크기: 10 x 6.6 inches
- 서브플롯: 2행 (가격 3 : 거래량 1)
- 가격선: 상승 = #D32F2F, 하락 = #1976D2
- 평단가선: purple, linewidth=2
- 거래량: 상승일 = #D32F2F, 하락일 = #1976D2
- X축: MaxNLocator(6)

#### mini_2week_chart.png (2주 차트)
- 크기: 8 x 5.5 inches
- 마커: 'o', 크기 4
- 평단가선: #9C27B0, linewidth=3.5
- 평단가 라벨: 14pt, bold

#### financial_performance.png (재무 실적)
- 크기: 10 x 2.8 inches
- 바 차트: 매출액(#757575), 영업이익(#D32F2F), 순이익(#1976D2)

#### investor_trends.png (수급 30일)
- 크기: 10 x 6 inches
- 서브플롯: 2행 (가격 1 : 수급 1)
- 외국인: #E64A19, 기관: #512DA8
- 평단가선: #9C27B0, linewidth=3.5

#### investor_trends_year.png (수급 1년)
- 크기: 10 x 6 inches
- 서브플롯: 2행 (가격 1 : 누적 수급 1)
- 외국인 누적: #E64A19, 기관 누적: #512DA8

#### peer_comparison.png (동종업계 비교)
- generate_peer_comparison_chart() 함수로 생성

---

## 3. 변경 금지 사항 체크리스트

### 3.1 절대 변경 금지
- [ ] 섹션 순서
- [ ] 섹션 제목 (이모지 포함)
- [ ] 테이블 컬럼 순서
- [ ] 테이블 컬럼 너비
- [ ] 색상 코드
- [ ] 폰트 크기
- [ ] 페이지 브레이크 위치
- [ ] 차트 크기 및 비율

### 3.2 데이터만 변경 가능
- [ ] 종목 데이터 값
- [ ] 차트 데이터 포인트
- [ ] 뉴스 내용
- [ ] 날짜/시간

### 3.3 변경 시 필요 절차
1. 사용자 승인 필수
2. 이 명세서 버전 업데이트
3. 변경 이력 기록
4. 테스트 후 배포

---

## 4. 파일 버전 관리

| 파일 | 버전 | 최종 수정일 | 체크섬 (첫 100줄) |
|------|------|------------|------------------|
| generate_pdf_report.py | v1.0.0 | 2025-11-28 | - |
| generate_realtime_dashboard_terminal_style.py | v1.0.0 | 2025-11-28 | - |

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 | 승인자 |
|------|------|----------|--------|
| 2025-11-28 | 1.0.0 | 최초 작성 (구조 잠금) | wonny |
