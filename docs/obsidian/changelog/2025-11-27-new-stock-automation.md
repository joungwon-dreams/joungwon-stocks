---
created: 2025-11-27 17:30:25
updated: 2025-11-27 17:30:25
tags: [changelog, automation, scheduler, fswatch, cron, new-stock-recommendation]
author: wonny
status: active
---

# 2025-11-27 신규종목추천 자동화 시스템 구축

## 작업 요약

신규종목추천 시스템의 자동화 인프라를 구축했습니다:
1. fswatch를 이용한 PDF 파일 자동 동기화
2. LaunchAgent를 이용한 3시간 간격 자동 실행
3. 18시 종가 평가 기능 추가

---

## 1. PDF 파일 자동 동기화 (fswatch)

### 목적
신규종목추천 PDF가 생성되면 자동으로 다른 폴더로 복사

### 설정 내용

**소스 폴더**:
```
/Users/wonny/Dev/joungwon.stocks/reports/new_stock/daily/
```

**타겟 폴더**:
```
/Users/wonny/Dev/joungwon.stocks.report/research_report/new_stock/
```

### 생성된 파일

#### 1) 동기화 스크립트
**경로**: `/Users/wonny/Dev/joungwon.stocks/scripts/sync_new_stock_reports.sh`

```bash
#!/bin/bash
SOURCE_DIR="/Users/wonny/Dev/joungwon.stocks/reports/new_stock/daily"
TARGET_DIR="/Users/wonny/Dev/joungwon.stocks.report/research_report/new_stock"

mkdir -p "$TARGET_DIR"

# 기존 파일 먼저 복사
for file in "$SOURCE_DIR"/*.pdf; do
    if [ -f "$file" ]; then
        cp "$file" "$TARGET_DIR/"
    fi
done

# fswatch로 모니터링
fswatch -0 "$SOURCE_DIR" | while read -d "" file; do
    if [[ "$file" == *.pdf ]] && [ -f "$file" ]; then
        cp "$file" "$TARGET_DIR/"
    fi
done
```

#### 2) LaunchAgent 설정
**경로**: `~/Library/LaunchAgents/com.wonny.sync-new-stock-reports.plist`

- **RunAtLoad**: true (시스템 시작 시 자동 실행)
- **KeepAlive**: true (종료되면 자동 재시작)
- **로그**: `/Users/wonny/Dev/joungwon.stocks/logs/sync_new_stock.log`

### 관리 명령어
```bash
# 상태 확인
launchctl list | grep sync-new-stock

# 중지
launchctl unload ~/Library/LaunchAgents/com.wonny.sync-new-stock-reports.plist

# 시작
launchctl load ~/Library/LaunchAgents/com.wonny.sync-new-stock-reports.plist
```

---

## 2. 신규종목추천 자동 실행 스케줄러

### 스케줄
| 시간 | 모드 | 설명 |
|:---:|:---|:---|
| 04:00 | 일반 | 장 시작 전 사전 분석 |
| 07:00 | 일반 | 장 시작 직전 분석 |
| 10:00 | 일반 | 장중 분석 |
| 13:00 | 일반 | 장중 분석 |
| 16:00 | 일반 | 장 마감 전 분석 |
| **18:00** | **종가 평가** | 종가 확정 후 평가 + 신규 추천 |

### 생성된 파일

#### 1) Cron 실행 스크립트
**경로**: `/Users/wonny/Dev/joungwon.stocks/scripts/cron_new_stock_recommendation.sh`

**일반 모드 (04~16시)**:
```
run.py 실행 → PDF 생성
```

**종가 평가 모드 (18시)**:
```
1. 종가 추적 기록 (smart_price_tracking 테이블)
2. 추적 리포트 생성 (마크다운)
3. 신규 추천 실행 (run.py)
4. 성과 요약 출력 (등급별 평균 수익률, 승률)
```

#### 2) LaunchAgent 설정
**경로**: `~/Library/LaunchAgents/com.wonny.new-stock-recommendation.plist`

```xml
<key>StartCalendarInterval</key>
<array>
    <dict><key>Hour</key><integer>4</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>13</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>16</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>18</integer><key>Minute</key><integer>0</integer></dict>
</array>
```

### 관리 명령어
```bash
# 상태 확인
launchctl list | grep new-stock-recommendation

# 중지
launchctl unload ~/Library/LaunchAgents/com.wonny.new-stock-recommendation.plist

# 시작
launchctl load ~/Library/LaunchAgents/com.wonny.new-stock-recommendation.plist

# 수동 실행
/Users/wonny/Dev/joungwon.stocks/scripts/cron_new_stock_recommendation.sh
```

---

## 3. 18시 종가 평가 기능

### 목적
추천 종목의 실제 성과를 추적하여 AI 등급의 정확도 평가

### 데이터 흐름
```
[18시 트리거]
      ↓
[DailyPriceTracker.record_daily_prices()]
      ↓
[daily_ohlcv에서 종가 조회]
      ↓
[smart_price_tracking 테이블에 저장]
      ↓
[수익률 계산: (종가 - 추천가) / 추천가 × 100]
      ↓
[추적 리포트 생성]
```

### 데이터베이스 테이블

**smart_price_tracking**:
| 컬럼 | 타입 | 설명 |
|:---|:---|:---|
| id | SERIAL | PK |
| recommendation_id | INTEGER | smart_recommendations FK |
| stock_code | VARCHAR(10) | 종목코드 |
| stock_name | VARCHAR(100) | 종목명 |
| rec_date | DATE | 추천일 |
| rec_price | INTEGER | 추천가 |
| rec_grade | CHAR(1) | 추천 등급 |
| track_date | DATE | 추적일 |
| track_price | INTEGER | 추적가 (종가) |
| return_rate | NUMERIC(8,2) | 수익률 (%) |
| days_held | INTEGER | 보유일수 |

### 성과 요약 출력 예시
```
===== 등급별 성과 요약 =====
S등급: 3종목, 평균수익 +5.32%, 승률 66.7%
A등급: 8종목, 평균수익 +2.15%, 승률 62.5%
```

---

## 전체 폴더 구조

```
joungwon.stocks/
├── 신규종목추천/                          # 신규종목추천 메인 패키지
│   ├── run.py                            # 메인 실행 스크립트
│   ├── run_phase4.py                     # Phase4 별도 실행
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py                   # 설정값
│   └── src/
│       ├── __init__.py
│       ├── phase1/                       # Phase 1: 필터링
│       │   ├── __init__.py
│       │   ├── filter_phase1a.py         # SQL 기반 1차 필터
│       │   └── filter_phase1b.py         # 기술적 지표 필터
│       ├── phase2/                       # Phase 2: 데이터 수집 & AI 분석
│       │   ├── __init__.py
│       │   ├── batch_collector.py        # 배치 데이터 수집기
│       │   └── gemini_analyzer.py        # Gemini AI 분석기 ⭐수정됨
│       ├── phase3/                       # Phase 3: 스코어링
│       │   ├── __init__.py
│       │   └── scorer.py                 # 가치 스코어러
│       ├── phase4/                       # Phase 4: 피드백 & 회고
│       │   ├── __init__.py
│       │   ├── profit_tracker.py         # 수익률 추적
│       │   ├── retrospective.py          # AI 회고
│       │   └── feedback_runner.py        # 피드백 실행
│       ├── reports/                      # 리포트 생성
│       │   ├── __init__.py
│       │   ├── pdf_generator.py          # PDF 생성기 ⭐수정됨
│       │   └── daily_tracker.py          # 일일 가격 추적기
│       └── utils/
│           ├── __init__.py
│           └── database.py               # DB 연결
│
├── scripts/                              # 실행 스크립트
│   ├── cron_new_stock_recommendation.sh  # ⭐신규: Cron 실행 스크립트
│   └── sync_new_stock_reports.sh         # ⭐신규: PDF 동기화 스크립트
│
├── reports/
│   └── new_stock/
│       ├── daily/                        # 일일 PDF 리포트
│       │   └── 신규종목추천_2025-11-27_1713.pdf
│       └── tracking/                     # 추적 마크다운 리포트
│
├── logs/                                 # 로그 파일
│   ├── cron_new_stock_*.log             # Cron 실행 로그
│   ├── launchd_new_stock.log            # LaunchAgent stdout
│   ├── launchd_new_stock_error.log      # LaunchAgent stderr
│   └── sync_new_stock.log               # PDF 동기화 로그
│
├── docs/
│   └── obsidian/
│       ├── features/
│       │   └── new-stock-recommendation-scheduler.md  # ⭐신규
│       └── changelog/
│           └── 2025-11-27-new-stock-automation.md     # ⭐신규 (본 문서)
│
└── CLAUDE.md                             # 프로젝트 가이드

~/Library/LaunchAgents/                   # macOS LaunchAgent 설정
├── com.wonny.new-stock-recommendation.plist  # ⭐신규: 스케줄러
└── com.wonny.sync-new-stock-reports.plist    # ⭐신규: PDF 동기화
```

---

## 수정된 파일 상세

### 1. gemini_analyzer.py (이전 세션에서 수정)
- AI 등급 기준 극히 엄격하게 변경
- S등급: 5가지 조건 **모두** 충족 필수
- A등급: 4가지 조건 **모두** 충족 필수
- 목표: 하루 5개 이내 S/A 등급

### 2. pdf_generator.py (이전 세션에서 수정)
- S/A 등급만 PDF에 포함
- None 값 처리 (PBR, PER, RSI)
- 핵심재료 전체 표시

### 3. daily_tracker.py
- S/A 등급만 추적 대상으로 필터링
- 종가 기록 및 수익률 계산

---

## 활성화된 LaunchAgent 목록

```bash
$ launchctl list | grep wonny
-	0	com.wonny.new-stock-recommendation    # 신규종목추천 스케줄러
-	0	com.wonny.sync-new-stock-reports      # PDF 동기화
```

---

## 다음 단계 (선택사항)

1. **주말/공휴일 제외**: 현재는 매일 실행됨
2. **알림 연동**: Slack/Telegram 알림 추가
3. **대시보드**: 웹 기반 성과 대시보드 구축
4. **AI 등급 정확도 분석**: 등급별 실제 승률 통계 리포트

---

*작성일: 2025-11-27 17:30:25*
