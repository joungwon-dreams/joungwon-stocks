-- ============================================================
-- Update Existing Site Management Tables
-- 기존 테이블에 누락된 컬럼 추가
-- ============================================================

-- reference_sites 테이블 업데이트
ALTER TABLE reference_sites
ADD COLUMN IF NOT EXISTS site_name_en VARCHAR(100),
ADD COLUMN IF NOT EXISTS category VARCHAR(50),
ADD COLUMN IF NOT EXISTS reliability_rating INTEGER,
ADD COLUMN IF NOT EXISTS data_quality_score DECIMAL(3,2),
ADD COLUMN IF NOT EXISTS tier INTEGER,
ADD COLUMN IF NOT EXISTS is_official BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS notes TEXT;

-- analysis_domains 테이블 업데이트
ALTER TABLE analysis_domains
ADD COLUMN IF NOT EXISTS domain_name_en VARCHAR(100),
ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 5;

-- site_analysis_mapping 테이블 업데이트
ALTER TABLE site_analysis_mapping
ADD COLUMN IF NOT EXISTS suitability_score INTEGER,
ADD COLUMN IF NOT EXISTS is_primary_source BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS notes TEXT;

-- collected_data 테이블에 인덱스 추가 (없으면)
DO $$
BEGIN
    -- site_domain 복합 인덱스
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_collected_data_site_domain') THEN
        CREATE INDEX idx_collected_data_site_domain ON collected_data(site_id, domain_id);
    END IF;

    -- expires_at 인덱스
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_collected_data_expires') THEN
        CREATE INDEX idx_collected_data_expires ON collected_data(expires_at) WHERE expires_at IS NOT NULL;
    END IF;
END $$;

-- fetch_execution_logs 인덱스 추가
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_fetch_logs_ticker') THEN
        CREATE INDEX idx_fetch_logs_ticker ON fetch_execution_logs(ticker) WHERE ticker IS NOT NULL;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_fetch_logs_error_type') THEN
        CREATE INDEX idx_fetch_logs_error_type ON fetch_execution_logs(error_type) WHERE error_type IS NOT NULL;
    END IF;
END $$;

-- site_health_status 인덱스 추가
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_site_health_failures') THEN
        CREATE INDEX idx_site_health_failures ON site_health_status(consecutive_failures DESC)
            WHERE consecutive_failures > 0;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_site_health_last_checked') THEN
        CREATE INDEX idx_site_health_last_checked ON site_health_status(last_checked_at DESC);
    END IF;
END $$;

-- site_structure_snapshots 인덱스 추가
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_structure_snapshots_baseline') THEN
        CREATE INDEX idx_structure_snapshots_baseline ON site_structure_snapshots(is_baseline)
            WHERE is_baseline = TRUE;
    END IF;
END $$;

-- ============================================================
-- Recreate Views (DROP first to avoid column errors)
-- ============================================================

-- 기존 뷰 삭제
DROP VIEW IF EXISTS v_reference_sites_by_category CASCADE;
DROP VIEW IF EXISTS v_site_health_dashboard CASCADE;
DROP VIEW IF EXISTS v_failed_sites_analysis CASCADE;
DROP VIEW IF EXISTS v_analysis_domain_statistics CASCADE;
DROP VIEW IF EXISTS v_analysis_domain_top_sites CASCADE;
DROP VIEW IF EXISTS v_site_analysis_capabilities CASCADE;
DROP VIEW IF EXISTS v_high_reliability_sites CASCADE;

-- View 1: 사이트 카테고리별 통계
CREATE VIEW v_reference_sites_by_category AS
SELECT
    category,
    COUNT(*) AS site_count,
    COUNT(*) FILTER (WHERE is_active = TRUE) AS active_count,
    AVG(reliability_rating) AS avg_rating,
    AVG(data_quality_score) AS avg_quality
FROM reference_sites
GROUP BY category
ORDER BY site_count DESC;

-- View 2: 사이트 헬스 대시보드
CREATE VIEW v_site_health_dashboard AS
SELECT
    rs.id AS site_id,
    rs.site_name_ko,
    rs.category,
    rs.tier,
    shs.status,
    shs.consecutive_failures,
    shs.success_rate,
    shs.avg_response_time_ms,
    shs.last_success_at,
    shs.last_failure_at,
    shs.structure_change_detected,
    shs.last_checked_at
FROM reference_sites rs
LEFT JOIN site_health_status shs ON rs.id = shs.site_id
WHERE rs.is_active = TRUE
ORDER BY shs.consecutive_failures DESC NULLS LAST, shs.success_rate ASC NULLS LAST;

-- View 3: 최근 실패한 사이트 분석
CREATE VIEW v_failed_sites_analysis AS
SELECT
    rs.site_name_ko,
    rs.category,
    fel.error_type,
    COUNT(*) AS failure_count,
    MAX(fel.started_at) AS last_failure,
    STRING_AGG(DISTINCT fel.error_message, ' | ') AS error_messages
FROM reference_sites rs
JOIN fetch_execution_logs fel ON rs.id = fel.site_id
WHERE fel.execution_status = 'failed'
    AND fel.started_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY rs.site_name_ko, rs.category, fel.error_type
ORDER BY failure_count DESC
LIMIT 20;

-- View 4: 분석 도메인별 사이트 수
CREATE VIEW v_analysis_domain_statistics AS
SELECT
    ad.domain_code,
    ad.domain_name_ko,
    COUNT(sam.site_id) AS total_sites,
    COUNT(sam.site_id) FILTER (WHERE sam.is_primary_source = TRUE) AS primary_sources,
    AVG(sam.suitability_score) AS avg_suitability
FROM analysis_domains ad
LEFT JOIN site_analysis_mapping sam ON ad.id = sam.domain_id
GROUP BY ad.domain_code, ad.domain_name_ko
ORDER BY total_sites DESC;

-- View 5: 도메인별 최고 품질 사이트
CREATE VIEW v_analysis_domain_top_sites AS
WITH ranked_sites AS (
    SELECT
        ad.domain_code,
        ad.domain_name_ko,
        rs.site_name_ko,
        rs.tier,
        sam.suitability_score,
        rs.reliability_rating,
        ROW_NUMBER() OVER (PARTITION BY ad.domain_code ORDER BY sam.suitability_score DESC NULLS LAST, rs.reliability_rating DESC NULLS LAST) AS rank
    FROM analysis_domains ad
    JOIN site_analysis_mapping sam ON ad.id = sam.domain_id
    JOIN reference_sites rs ON sam.site_id = rs.id
    WHERE rs.is_active = TRUE
)
SELECT
    domain_code,
    domain_name_ko,
    site_name_ko,
    tier,
    suitability_score,
    reliability_rating
FROM ranked_sites
WHERE rank <= 3
ORDER BY domain_code, rank;

-- View 6: 사이트별 분석 능력
CREATE VIEW v_site_analysis_capabilities AS
SELECT
    rs.id AS site_id,
    rs.site_name_ko,
    rs.tier,
    STRING_AGG(ad.domain_code, ', ' ORDER BY ad.domain_code) AS supported_domains,
    COUNT(sam.domain_id) AS domain_count,
    AVG(sam.suitability_score) AS avg_suitability
FROM reference_sites rs
LEFT JOIN site_analysis_mapping sam ON rs.id = sam.site_id
LEFT JOIN analysis_domains ad ON sam.domain_id = ad.id
WHERE rs.is_active = TRUE
GROUP BY rs.id, rs.site_name_ko, rs.tier
ORDER BY domain_count DESC, avg_suitability DESC NULLS LAST;

-- View 7: 고신뢰도 사이트 목록
CREATE VIEW v_high_reliability_sites AS
SELECT
    rs.site_name_ko,
    rs.category,
    rs.tier,
    rs.reliability_rating,
    rs.data_quality_score,
    shs.success_rate,
    shs.avg_response_time_ms,
    shs.last_success_at
FROM reference_sites rs
LEFT JOIN site_health_status shs ON rs.id = shs.site_id
WHERE rs.is_active = TRUE
    AND rs.reliability_rating >= 4
    AND (shs.success_rate IS NULL OR shs.success_rate >= 90)
ORDER BY rs.reliability_rating DESC NULLS LAST, shs.success_rate DESC NULLS LAST;

-- ============================================================
-- Success Message
-- ============================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Existing tables updated successfully!';
    RAISE NOTICE '📊 Columns added to reference_sites, analysis_domains, site_analysis_mapping';
    RAISE NOTICE '🔍 Missing indexes created';
    RAISE NOTICE '👁️  7 views recreated';
    RAISE NOTICE '';
    RAISE NOTICE '📋 Database is now fully integrated (20 tables)';
END $$;
