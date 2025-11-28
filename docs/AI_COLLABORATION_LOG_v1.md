
## [2025-11-29 11:00] Phase 9: AI 신규 종목 발굴 (AI Sniper) 구현 지시

### 📢 To: Claude (Implementer)

AEGIS 엔진을 활용하여 시장 전체에서 유망 종목을 발굴하는 **"AI Sniper"** 기능을 구현합니다.

**작업 지시:**

1.  **설계 문서 확인:** `docs/SYSTEM_EVOLUTION_DESIGN_SPEC.md`의 **Phase 9** 섹션을 확인하세요.
2.  **패키지 생성:** `src/aegis/discovery/`
3.  **구현 내용:**
    *   **`MarketScanner` (`scanner.py`):**
        -   `pykrx`를 사용하여 KOSPI/KOSDAQ 전 종목 리스트를 가져옵니다.
        -   거래대금(100억 이상), 수급(외인/기관 매수), 기술적 지표(RSI, 이평선)로 1차 후보군(50개 내외)을 필터링하세요.
    *   **`OpportunityFinder` (`finder.py`):**
        -   1차 후보군 각각에 대해 `InformationFusionEngine`을 실행합니다. (Multi-modal 분석)
        -   최종 점수(`Final Score`)가 높은 순서대로 정렬하여 **Top 5**를 선정하세요.
    *   **실행 스크립트 (`scripts/run_market_scan.py`):**
        -   위 과정을 실행하고 결과를 콘솔에 출력 및 `reports/aegis_picks.json` (또는 유사한 파일)에 저장하세요.

**목표:** 매일 장이 끝나면 "내일 살 만한 종목"을 AI가 추천해주는 것입니다.

---

*Last Updated: 2025-11-29 11:00*
