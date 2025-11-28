
## [2025-11-29 10:00] Phase 8: 일일 매매 성과 분석 시스템 구축 지시

### 📢 To: Claude (Implementer)

사용자가 장 마감 후(15:40~) 하루의 매매 성과를 정리해주는 **"일일 리포트 시스템"**을 요청했습니다.

**작업 지시:**

1.  **설계 문서 확인:** `docs/SYSTEM_EVOLUTION_DESIGN_SPEC.md`의 **Phase 8** 섹션을 확인하세요.
2.  **DB 작업:** `sql/create_daily_summary.sql`을 작성하고 실행하여 `daily_summary` 테이블을 만드세요.
3.  **분석 모듈 (`src/reporting/performance/analyzer.py`):**
    -   `trade_history` 테이블에서 당일 거래 내역을 조회하여 실현 손익, 승률 등을 계산하세요.
    -   `stock_assets` 테이블에서 현재 총 자산 가치를 계산하세요.
4.  **리포트 생성 스크립트 (`scripts/generate_daily_performance_report.py`):**
    -   위 분석 결과를 바탕으로 PDF 리포트를 생성하세요.
    -   **구성:**
        -   1p: 오늘의 손익 요약, 자산 추이 그래프
        -   2p: 포트폴리오 파이차트, 매매 일지(Trade Log)
        -   3p: 주간/월간 누적 성과 (캘린더 형태)
    -   저장 경로: `reports/performance/YYYY-MM-DD_Daily_Report.pdf`

**목표:** 사용자가 퇴근길에 "오늘 얼마 벌었는지"를 한눈에 볼 수 있는 깔끔한 리포트를 제공하는 것입니다.

---

*Last Updated: 2025-11-29 10:00*
