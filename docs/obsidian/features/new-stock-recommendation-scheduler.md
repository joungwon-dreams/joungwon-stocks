---
created: 2025-11-27 17:26:57
updated: 2025-11-27 17:26:57
tags: [feature, scheduler, cron, new-stock-recommendation, automation]
author: wonny
status: active
---

# 신규종목추천 자동화 스케줄러

## 개요

신규종목추천 시스템을 자동으로 실행하는 스케줄러입니다. macOS LaunchAgent를 사용하여 하루 6회 자동 실행되며, 마지막 실행(18시)에는 종가 평가 기능이 추가로 실행됩니다.

## 스케줄 설정

| 시간 | 모드 | 설명 |
|:---:|:---|:---|
| 04:00 | 일반 | 장 시작 전 분석 |
| 07:00 | 일반 | 장 시작 직전 분석 |
| 10:00 | 일반 | 장중 분석 |
| 13:00 | 일반 | 장중 분석 |
| 16:00 | 일반 | 장 마감 전 분석 |
| **18:00** | **종가 평가** | 종가 확정 후 평가 + 신규 추천 |

## 18시 종가 평가 모드

18시에는 다음 4단계로 실행됩니다:

1. **종가 추적 기록**: 기존 추천 종목의 당일 종가를 `smart_price_tracking` 테이블에 기록
2. **추적 리포트 생성**: 마크다운 형식의 성과 추적 리포트 생성
3. **신규 추천 실행**: 일반 추천 파이프라인 실행
4. **성과 요약 출력**: 등급별 평균 수익률, 승률 출력

## 파일 구조

```
joungwon.stocks/
├── scripts/
│   ├── cron_new_stock_recommendation.sh   # Cron 실행 스크립트
│   └── sync_new_stock_reports.sh          # PDF 동기화 스크립트
├── logs/
│   ├── cron_new_stock_*.log               # Cron 실행 로그
│   ├── launchd_new_stock.log              # LaunchAgent stdout
│   ├── launchd_new_stock_error.log        # LaunchAgent stderr
│   └── sync_new_stock.log                 # PDF 동기화 로그
├── reports/
│   └── new_stock/
│       ├── daily/                          # 일일 PDF 리포트
│       └── tracking/                       # 추적 마크다운 리포트
└── 신규종목추천/
    ├── run.py                              # 메인 실행 스크립트
    └── src/
        └── reports/
            ├── pdf_generator.py            # PDF 생성기
            └── daily_tracker.py            # 일일 가격 추적기
```

## LaunchAgent 설정 파일

### 신규종목추천 스케줄러
```
~/Library/LaunchAgents/com.wonny.new-stock-recommendation.plist
```

### PDF 동기화 (fswatch)
```
~/Library/LaunchAgents/com.wonny.sync-new-stock-reports.plist
```

## 관리 명령어

### 스케줄러 상태 확인
```bash
# 스케줄러 목록
launchctl list | grep wonny

# 개별 상태
launchctl list | grep new-stock-recommendation
launchctl list | grep sync-new-stock
```

### 스케줄러 제어
```bash
# 중지
launchctl unload ~/Library/LaunchAgents/com.wonny.new-stock-recommendation.plist

# 시작
launchctl load ~/Library/LaunchAgents/com.wonny.new-stock-recommendation.plist

# 재시작
launchctl unload ~/Library/LaunchAgents/com.wonny.new-stock-recommendation.plist && \
launchctl load ~/Library/LaunchAgents/com.wonny.new-stock-recommendation.plist
```

### 수동 실행
```bash
# 일반 모드 (04~16시와 동일)
/Users/wonny/Dev/joungwon.stocks/scripts/cron_new_stock_recommendation.sh

# 18시 모드 테스트 (환경변수로 시간 조작 불가, 스크립트 수정 필요)
```

### 로그 확인
```bash
# 최신 cron 로그
ls -lt /Users/wonny/Dev/joungwon.stocks/logs/cron_new_stock_*.log | head -1 | xargs tail -100

# LaunchAgent 로그
tail -100 /Users/wonny/Dev/joungwon.stocks/logs/launchd_new_stock.log

# PDF 동기화 로그
tail -20 /Users/wonny/Dev/joungwon.stocks/logs/sync_new_stock.log
```

## 데이터 흐름

```
[스케줄러 트리거]
      ↓
[cron_new_stock_recommendation.sh]
      ↓
  ┌───────────────────────────────────┐
  │  04~16시: 일반 모드               │
  │  → run.py 실행                    │
  │  → PDF 생성                       │
  └───────────────────────────────────┘
  ┌───────────────────────────────────┐
  │  18시: 종가 평가 모드             │
  │  → 종가 추적 기록                 │
  │  → 추적 리포트 생성               │
  │  → run.py 실행                    │
  │  → 성과 요약 출력                 │
  └───────────────────────────────────┘
      ↓
[fswatch 트리거]
      ↓
[PDF 동기화]
/reports/new_stock/daily/*.pdf
      ↓
/joungwon.stocks.report/research_report/new_stock/
```

## 데이터베이스 테이블

### smart_recommendations
추천 종목 저장

### smart_price_tracking
일별 가격 추적 (종가 평가용)

| 컬럼 | 설명 |
|:---|:---|
| recommendation_id | 추천 레코드 FK |
| stock_code | 종목코드 |
| rec_date | 추천일 |
| rec_price | 추천가 |
| track_date | 추적일 |
| track_price | 추적가 (종가) |
| return_rate | 수익률 (%) |
| days_held | 보유일수 |

## 성과 평가 기준

- **승률**: 수익률 > 0인 종목 비율
- **평균 수익률**: 등급별 평균 수익률
- **추적 기간**: 추천일로부터 30일까지 추적

## 주의사항

1. **휴장일 처리**: 주말/공휴일에는 자동 스킵됨 (pykrx로 거래일 확인)
2. **종가 확정 시간**: 실제 종가는 15:30 확정, 18시면 충분히 반영됨
3. **fswatch 의존성**: PDF 동기화는 fswatch 필요 (`brew install fswatch`)
4. **가상환경**: 스크립트 내에서 venv 활성화함

## 장중 변동성 대응 정책

### 현재 동작
- 각 시간대(04, 07, 10, 13, 16, 18시) 분석은 **독립적**으로 실행
- 이전 추천 종목이 장중에 급락해도 자동 철회 알림 없음

### 권장 운영 방식
1. **04시, 07시 추천**: 장 시작 전 참고용
2. **10시, 13시 추천**: 장중 새로운 기회 발굴
3. **16시 추천**: 마감 전 최종 점검
4. **18시 종가 평가**: 당일 성과 확정 + 실패 분석

### 향후 개선 (Future Work)
- 장중 급락 종목 실시간 모니터링
- 추천 철회 알림 시스템 (Slack/Telegram)
- 손절 기준 도달 시 자동 알림

## 트러블슈팅

### 스케줄러가 실행되지 않음
```bash
# plist 문법 검증
plutil ~/Library/LaunchAgents/com.wonny.new-stock-recommendation.plist

# 권한 확인
ls -la /Users/wonny/Dev/joungwon.stocks/scripts/cron_new_stock_recommendation.sh
```

### 로그에 에러 없는데 PDF 없음
```bash
# 추천 종목 확인 (S/A 등급만 PDF 생성)
psql -d stock_investment_db -c "SELECT ai_grade, COUNT(*) FROM smart_recommendations GROUP BY ai_grade"
```

### fswatch 동기화 안됨
```bash
# fswatch 프로세스 확인
ps aux | grep fswatch

# 재시작
launchctl unload ~/Library/LaunchAgents/com.wonny.sync-new-stock-reports.plist
launchctl load ~/Library/LaunchAgents/com.wonny.sync-new-stock-reports.plist
```

---

## 관련 문서

- [[new-stock-recommendation-system]] - 신규종목추천 시스템 전체 구조
- [[ai-grading-criteria]] - AI 등급 기준
- [[daily-tracker]] - 일일 가격 추적 시스템

---

*본 문서는 2025-11-27 자동 생성되었습니다.*
