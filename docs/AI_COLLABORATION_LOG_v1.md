## [2025-11-29 09:00] Phase 7.5: 시스템 최적화 및 경량화 지시

### 📢 To: Claude (Implementer)

사용자의 노트북 환경을 고려하여 시스템 부하를 줄이는 **Phase 7.5: System Optimization & Lightweighting**을 긴급 진행합니다.

**작업 내용:**

1.  **Gemini API 호출 최적화 (`src/aegis/fusion/news_sentiment.py` 수정):**
    -   모든 뉴스를 분석하지 마세요. 비용과 부하가 큽니다.
    -   **Smart Filtering:** 제목에 '특징주', '공시', '단독', '속보' 등의 키워드가 있거나, 주요 언론사(연합, 이데일리 등)인 경우에만 Gemini API를 호출하도록 로직을 변경하세요.
    -   나머지 뉴스는 키워드 기반 점수만 부여하고 API 호출은 생략(Skip)하세요.

2.  **DB 성능 최적화 (`sql/optimize_indexes.sql` 생성):**
    -   `min_ticks` 테이블의 `(stock_code, timestamp)` 복합 인덱스 생성.
    -   `stock_news` 테이블의 `(stock_code, published_at)` 인덱스 생성.
    -   `aegis_signal_history` 조회 속도 개선을 위한 인덱스 추가.

3.  **PDF 생성 최적화:**
    -   `generate_realtime_dashboard_terminal_style.py`에서 차트 이미지 생성 시 DPI를 조절하거나, 불필요한 고해상도 렌더링을 줄이세요.

**목표:** 시스템이 가볍고 빠르게 돌아가도록 군더더기를 제거하는 것입니다.

---

*Last Updated: 2025-11-29 09:00*