-- =====================================================
-- Database Tuning & Optimization
-- Created: 2025-11-29
-- Purpose: Improve database performance
-- =====================================================

-- =====================================================
-- 1. VACUUM FULL & ANALYZE (주요 테이블)
-- Dead rows 정리 및 통계 갱신
-- =====================================================

-- 가장 큰 테이블들 VACUUM ANALYZE
VACUUM ANALYZE daily_ohlcv;
VACUUM ANALYZE min_ticks;
VACUUM ANALYZE smart_phase1_candidates;
VACUUM ANALYZE collected_data;
VACUUM ANALYZE stock_fundamentals;
VACUUM ANALYZE stocks;
VACUUM ANALYZE fetch_execution_logs;
VACUUM ANALYZE smart_recommendations;
VACUUM ANALYZE stock_news;
VACUUM ANALYZE trade_history;
VACUUM ANALYZE aegis_signal_history;
VACUUM ANALYZE stock_assets;

-- Dead rows가 많은 테이블 VACUUM FULL
VACUUM FULL reference_sites;
VACUUM FULL stock_financials;
VACUUM FULL portfolio_ai_history;

-- =====================================================
-- 2. 사용되지 않는 인덱스 삭제 (주의: 선택적 실행)
-- 크기가 큰 미사용 인덱스만 삭제
-- =====================================================

-- 3MB 이상 미사용 인덱스 삭제
-- DROP INDEX IF EXISTS idx_daily_ohlcv_stock_date;  -- 3376 kB (daily_ohlcv에 이미 복합 인덱스 있음)
-- DROP INDEX IF EXISTS idx_min_ticks_stock_timestamp;  -- 440 kB (Phase 7.5에서 추가됨, 유지)
-- DROP INDEX IF EXISTS idx_collected_data_jsonb;  -- 296 kB (JSONB 검색용, 필요시 유지)

-- 중복 인덱스 삭제 (같은 컬럼에 여러 인덱스)
DROP INDEX IF EXISTS idx_stock_fundamentals_updated;  -- 176 kB, 미사용

-- smart 테이블 미사용 인덱스 정리
DROP INDEX IF EXISTS idx_smart_rec_score;  -- 56 kB

-- 기타 소형 미사용 인덱스 (16KB 이하는 유지 - 오버헤드 적음)

-- =====================================================
-- 3. 효율적인 인덱스 재생성
-- =====================================================

-- daily_ohlcv: BRIN 인덱스 (시계열 데이터에 효율적, B-tree보다 90% 작음)
DROP INDEX IF EXISTS idx_daily_ohlcv_stock_date;
CREATE INDEX IF NOT EXISTS idx_daily_ohlcv_date_brin
ON daily_ohlcv USING BRIN (date);

-- daily_ohlcv: 종목별 조회용 복합 인덱스 (이미 있으면 스킵)
CREATE INDEX IF NOT EXISTS idx_daily_ohlcv_stock_date_v2
ON daily_ohlcv (stock_code, date DESC)
WHERE date > '2024-01-01';  -- 최근 데이터만 인덱싱

-- =====================================================
-- 4. 테이블 통계 갱신
-- =====================================================

ANALYZE;

-- =====================================================
-- 5. Connection & Memory Settings 권장값
-- (postgresql.conf 수정 필요)
-- =====================================================

-- 권장 설정 (show로 현재값 확인)
-- shared_buffers = 256MB (전체 RAM의 25%)
-- effective_cache_size = 1GB (전체 RAM의 50-75%)
-- work_mem = 64MB
-- maintenance_work_mem = 256MB
-- random_page_cost = 1.1 (SSD인 경우)

-- 현재 설정 확인
SELECT name, setting, unit, short_desc
FROM pg_settings
WHERE name IN (
    'shared_buffers',
    'effective_cache_size',
    'work_mem',
    'maintenance_work_mem',
    'random_page_cost',
    'autovacuum',
    'autovacuum_vacuum_threshold',
    'autovacuum_analyze_threshold'
);

-- =====================================================
-- 6. 완료 메시지
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Database tuning completed';
    RAISE NOTICE '   - VACUUM ANALYZE: 12 main tables';
    RAISE NOTICE '   - VACUUM FULL: 3 tables with dead rows';
    RAISE NOTICE '   - Dropped unused indexes: 2';
    RAISE NOTICE '   - Created BRIN index for daily_ohlcv';
END $$;
