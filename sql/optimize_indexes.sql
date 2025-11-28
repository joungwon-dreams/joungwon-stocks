-- =====================================================
-- Phase 7.5: Database Performance Optimization Indexes
-- Created: 2025-11-29
-- Purpose: Improve query performance for high-frequency tables
-- =====================================================

-- =====================================================
-- 1. min_ticks 테이블 인덱스 최적화
-- 실시간 1분봉 데이터 조회 성능 개선
-- =====================================================

-- 기존 인덱스 확인 후 생성 (stock_code, timestamp 복합 인덱스)
CREATE INDEX IF NOT EXISTS idx_min_ticks_stock_timestamp
ON min_ticks (stock_code, timestamp DESC);

-- 최근 데이터 조회용 (timestamp 기반 BRIN 인덱스 - 시계열 데이터에 효율적)
CREATE INDEX IF NOT EXISTS idx_min_ticks_timestamp_brin
ON min_ticks USING BRIN (timestamp);

COMMENT ON INDEX idx_min_ticks_stock_timestamp IS
'Phase 7.5: 종목별 시계열 데이터 조회 최적화';

COMMENT ON INDEX idx_min_ticks_timestamp_brin IS
'Phase 7.5: 시계열 데이터 범위 조회 최적화 (BRIN index)';


-- =====================================================
-- 2. stock_news 테이블 인덱스 최적화
-- 뉴스 감성 분석 조회 성능 개선
-- =====================================================

-- stock_code + published_at 복합 인덱스
CREATE INDEX IF NOT EXISTS idx_stock_news_stock_published
ON stock_news (stock_code, published_at DESC);

-- 뉴스 시계열 BRIN 인덱스 (범위 조회 최적화)
CREATE INDEX IF NOT EXISTS idx_stock_news_published_brin
ON stock_news USING BRIN (published_at);

COMMENT ON INDEX idx_stock_news_stock_published IS
'Phase 7.5: 종목별 뉴스 시계열 조회 최적화';

COMMENT ON INDEX idx_stock_news_published_brin IS
'Phase 7.5: 뉴스 범위 조회 최적화 (BRIN index)';


-- =====================================================
-- 3. aegis_signal_history 테이블 인덱스 최적화
-- 신호 추적 및 검증 조회 성능 개선
-- =====================================================

-- 활성 신호 조회용 인덱스 (trace_status != 'completed')
-- 이미 존재하면 생략
CREATE INDEX IF NOT EXISTS idx_aegis_signal_active
ON aegis_signal_history (stock_code, recorded_at DESC)
WHERE trace_status IN ('pending', 'tracking');

-- 검증 대시보드용 인덱스 (신호 타입 + 시간)
CREATE INDEX IF NOT EXISTS idx_aegis_signal_verification
ON aegis_signal_history (signal_type, recorded_at DESC);

-- 실패 원인 분석용 인덱스
CREATE INDEX IF NOT EXISTS idx_aegis_signal_failure
ON aegis_signal_history (failure_tag, recorded_at DESC)
WHERE failure_tag IS NOT NULL;

COMMENT ON INDEX idx_aegis_signal_active IS
'Phase 7.5: 활성 신호 추적 조회 최적화';

COMMENT ON INDEX idx_aegis_signal_verification IS
'Phase 7.5: 검증 대시보드 조회 최적화';

COMMENT ON INDEX idx_aegis_signal_failure IS
'Phase 7.5: 실패 원인 분석 조회 최적화';


-- =====================================================
-- 4. stock_assets 테이블 인덱스 최적화
-- 보유종목 대시보드 조회 성능 개선
-- =====================================================

-- 보유종목만 조회 (quantity > 0)
CREATE INDEX IF NOT EXISTS idx_stock_assets_holding
ON stock_assets (stock_code)
WHERE quantity > 0;

COMMENT ON INDEX idx_stock_assets_holding IS
'Phase 7.5: 보유종목 조회 최적화 (partial index)';


-- =====================================================
-- 5. daily_ohlcv 테이블 인덱스 최적화
-- 일봉 데이터 조회 성능 개선
-- =====================================================

-- 최근 데이터 조회용 (stock_code + date 복합)
CREATE INDEX IF NOT EXISTS idx_daily_ohlcv_stock_date
ON daily_ohlcv (stock_code, date DESC);

COMMENT ON INDEX idx_daily_ohlcv_stock_date IS
'Phase 7.5: 종목별 일봉 데이터 조회 최적화';


-- =====================================================
-- 6. 인덱스 통계 갱신 (ANALYZE)
-- 쿼리 플래너가 최적의 실행 계획을 세우도록 함
-- =====================================================

ANALYZE min_ticks;
ANALYZE stock_news;
ANALYZE aegis_signal_history;
ANALYZE stock_assets;
ANALYZE daily_ohlcv;


-- =====================================================
-- 완료 메시지
-- =====================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Phase 7.5: Database optimization indexes created successfully';
    RAISE NOTICE '   - min_ticks: 2 indexes';
    RAISE NOTICE '   - stock_news: 2 indexes';
    RAISE NOTICE '   - aegis_signal_history: 3 indexes';
    RAISE NOTICE '   - stock_assets: 1 index';
    RAISE NOTICE '   - daily_ohlcv: 1 index';
    RAISE NOTICE '   Total: 9 new indexes for performance optimization';
END $$;
