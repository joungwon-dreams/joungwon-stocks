---
created: 2025-11-24 14:16:05
updated: 2025-11-27 17:55:23
tags: [dev-ops, structure, organization, documentation]
author: wonny
status: active
---

# Project Structure (프로젝트 폴더 구조)

## 📂 전체 구조

```
joungwon.stocks/
│
├── 📚 docs/                                    # 문서
│   ├── 01-opensource-integration-analysis.md   # 오픈소스 통합 분석
│   ├── 02-user-commands-implementation-plan.md # 사용자 명령 구현 계획
│   ├── 03-ai-learning-scoring-system.md        # AI 학습/스코어링 시스템
│   ├── 04-database-schema.md                   # DB 스키마 설계
│   ├── 05-fetcher-test-report.md               # Fetcher 테스트 리포트
│   ├── PORTFOLIO_FEEDBACK_SPEC.md              # ⭐ 보유종목 AI 피드백 스펙
│   ├── SCHEDULER_PLAN.md                       # 스케줄러 계획
│   ├── 신규종목추천-시스템-설계.md              # 신규종목추천 설계
│   │
│   ├── features/
│   │   └── wisefn-analyst-reports.md           # WISEfn 애널리스트 리포트
│   │
│   └── obsidian/                               # 📝 Obsidian Vault
│       ├── changelog/                          # 변경 이력
│       │   ├── 2025-11-24-changes.md
│       │   ├── 2025-11-27-new-stock-automation.md
│       │   ├── 2025-11-27-portfolio-ai-feedback.md  # ⭐ AI 피드백
│       │   └── 2025-11-27-신규종목추천-시스템.md
│       │
│       ├── features/                           # 기능 문서
│       │   ├── holding-stock-research-report.md
│       │   ├── new-stock-recommendation-scheduler.md  # 스케줄러
│       │   ├── portfolio-ai-feedback.md               # ⭐ AI 피드백
│       │   ├── tier3-web-scraping.md
│       │   ├── trading-report-pdf.md
│       │   └── 신규종목추천-기능.md
│       │
│       ├── troubleshooting/                    # 오류 해결
│       │   ├── database-integration-errors.md
│       │   ├── pdf-generation-errors.md
│       │   ├── tier3-url-errors.md
│       │   └── 신규종목추천-오류.md
│       │
│       └── dev-ops/
│           └── project-structure.md            # 본 문서
│
├── 🗄️ sql/                                     # 데이터베이스 스키마
│   ├── 01_create_tables.sql                    # 기본 테이블
│   ├── 02_create_wisefn_reports.sql            # WISEfn 리포트
│   ├── 03_create_investment_consensus.sql      # 투자 컨센서스
│   ├── 07_create_financial_tables.sql          # 재무 테이블
│   ├── 10_create_news_table.sql                # 뉴스 테이블
│   └── 11_create_portfolio_feedback.sql        # ⭐ AI 피드백 테이블
│
├── 🐍 src/                                     # 소스 코드
│   ├── config/
│   │   └── database.py                         # DB 연결
│   ├── core/
│   │   ├── base_fetcher.py
│   │   └── orchestrator.py                     # 데이터 수집 오케스트레이터
│   ├── fetchers/
│   │   ├── tier1_libraries/                    # pykrx, dart-fss
│   │   ├── tier2_official_apis/                # KIS, Naver API
│   │   ├── tier3_web_scraping/                 # Scrapy 스파이더
│   │   └── tier4_browser_automation/           # Playwright
│   └── learners/                               # RL 에이전트
│
├── 📜 scripts/                                 # 실행 스크립트
│   ├── cron_new_stock_recommendation.sh        # 신규종목추천 Cron
│   ├── sync_new_stock_reports.sh               # PDF 동기화
│   ├── analyze_ai_performance.py               # ⭐ AI 성과 분석
│   │
│   ├── gemini/                                 # Gemini AI 관련
│   │   ├── generate_pdf_report.py              # ⭐ PDF 생성기
│   │   ├── naver/
│   │   │   ├── news.py
│   │   │   └── consensus.py
│   │   ├── wisefn/
│   │   │   └── reports_scraper.py
│   │   └── components/
│   │       ├── portfolio_advisor.py            # ⭐ AI 어드바이저
│   │       ├── consensus.py
│   │       ├── holding.py
│   │       ├── peer.py
│   │       └── realtime.py
│   │
│   └── naver/                                  # 네이버 스크래퍼
│       └── consensus_scraper.py
│
├── 🎯 신규종목추천/                             # 신규종목추천 패키지
│   ├── run.py                                  # 메인 실행
│   ├── run_phase4.py                           # Phase4 실행
│   ├── config/
│   │   └── settings.py
│   ├── src/
│   │   ├── phase1/                             # 필터링
│   │   ├── phase2/                             # 데이터 수집 & AI 분석
│   │   ├── phase3/                             # 스코어링
│   │   ├── phase4/                             # 피드백 & 회고
│   │   ├── reports/
│   │   │   ├── pdf_generator.py
│   │   │   └── daily_tracker.py
│   │   └── utils/
│   ├── docs/
│   │   ├── MOMENTUM_FILTER_SPEC.md
│   │   ├── PHASE4_GUIDE.md
│   │   └── TRACKING_DASHBOARD_GUIDE.md
│   └── sql/
│       ├── 01_create_tables.sql
│       └── create_tracking_tables.sql
│
├── 📊 reports/                                 # 생성된 리포트
│   ├── 한국전력.pdf                            # 보유종목 PDF
│   ├── charts/                                 # 차트 이미지
│   ├── new_stock/                              # 신규종목추천 PDF
│   │   ├── daily/
│   │   └── tracking/
│   └── ai_performance/                         # ⭐ AI 성과 리포트
│       └── weekly_YYYYMMDD.md
│
├── 📋 logs/                                    # 로그
│   ├── cron_new_stock_*.log
│   ├── launchd_new_stock.log
│   └── sync_new_stock.log
│
├── 🔧 venv/                                    # Python 가상환경
│
├── CLAUDE.md                                   # Claude Code 가이드
├── README.md                                   # 프로젝트 소개
└── requirements.txt                            # 의존성
```

---

## ⭐ 보유종목 AI 피드백 관련 파일

| 파일 | 경로 | 설명 |
|:---|:---|:---|
| **portfolio_advisor.py** | scripts/gemini/components/ | AI 어드바이저 클래스 |
| **11_create_portfolio_feedback.sql** | sql/ | DB 스키마 |
| **analyze_ai_performance.py** | scripts/ | 성과 분석 스크립트 |
| **PORTFOLIO_FEEDBACK_SPEC.md** | docs/ | 상세 스펙 |
| **portfolio-ai-feedback.md** | docs/obsidian/features/ | 기능 문서 |

---

## 🔄 PDF 생성 흐름

```
generate_pdf_report.py
├── fetch_all_data()
│   ├── 주가/재무/컨센서스 데이터
│   ├── 뉴스 (NaverNewsFetcher)
│   └── ⭐ AI 피드백 (PortfolioAdvisor)
│
├── generate_charts()
│   ├── price_trend.png
│   ├── mini_2week_chart.png
│   ├── financial_performance.png
│   ├── investor_trends.png
│   └── peer_comparison.png
│
└── generate_pdf()
    ├── Page 1: Header, Opinion, Key Metrics, Company Overview
    ├── Page 1-2: 2-Week Trend, ⭐AI Feedback, Consensus, Analyst Targets
    ├── Page 2: Holding Status, Real-time Ticks
    ├── Page 3: Price Chart, Financial Performance
    ├── Page 4: Investor Trends (30d + 1yr)
    ├── Page 5: Peer Comparison
    └── Page 6+: News Analysis
```

---

## 🗄️ 데이터베이스 테이블

### 핵심 테이블 (13개)
| 테이블 | 설명 |
|:---|:---|
| `stocks` | 종목 마스터 |
| `stock_assets` | 보유 종목 |
| `daily_ohlcv` | 일봉 데이터 |
| `min_ticks` | 실시간 틱 |
| `stock_fundamentals` | 펀더멘탈 |
| `stock_financials` | 재무제표 |
| `investor_trends` | 수급 동향 |
| `stock_peers` | 동종업계 |
| `investment_consensus` | 컨센서스 |
| `wisefn_reports` | WISEfn 리포트 |
| `stock_news` | 뉴스 |
| `recommendation_history` | 추천 이력 |
| **`portfolio_ai_history`** | ⭐ AI 피드백 이력 |

### 신규종목추천 테이블
- `smart_recommendations` - 추천 종목
- `smart_price_tracking` - 가격 추적
- `smart_feedback_history` - 피드백 이력

---

## 📋 스케줄러

### LaunchAgents (~/Library/LaunchAgents/)
| 파일 | 용도 |
|:---|:---|
| com.wonny.new-stock-recommendation.plist | 신규종목추천 (04,07,10,13,16,18시) |
| com.wonny.sync-new-stock-reports.plist | PDF 동기화 (fswatch) |

---

## 🛠️ 주요 명령어

```bash
# PDF 생성
python scripts/gemini/generate_pdf_report.py          # 전체 보유종목
python scripts/gemini/generate_pdf_report.py 015760   # 특정 종목

# AI 성과 분석
python scripts/analyze_ai_performance.py              # 최근 7일
python scripts/analyze_ai_performance.py --days 30    # 최근 30일
python scripts/analyze_ai_performance.py --weekly     # 주간 리포트

# 신규종목추천
python 신규종목추천/run.py                            # 수동 실행

# 스케줄러 관리
launchctl list | grep wonny                           # 상태 확인
```

---

## 📝 문서 위치 가이드

| 문서 유형 | 위치 |
|:---|:---|
| 기능 스펙 | docs/obsidian/features/ |
| 변경 이력 | docs/obsidian/changelog/ |
| 오류 해결 | docs/obsidian/troubleshooting/ |
| 상세 설계 | docs/ (루트) |
| 프로젝트 구조 | docs/obsidian/dev-ops/ |

---

**Last Updated**: 2025-11-27 17:55:23
