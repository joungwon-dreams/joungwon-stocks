-- ============================================================
-- Site Management Tables (41개 사이트 관리)
-- 기존 13개 테이블에 7개 테이블 추가 → 총 20개 테이블
-- ============================================================

-- ============================================================
-- Group 6: Site Management Tables (사이트 관리)
-- ============================================================

-- 14. reference_sites: 41개 데이터 수집 사이트 마스터
CREATE TABLE IF NOT EXISTS reference_sites (
    id SERIAL PRIMARY KEY,
    site_name_ko VARCHAR(100) NOT NULL,         -- 사이트명 (한글)
    site_name_en VARCHAR(100),                  -- 사이트명 (영문)
    site_url TEXT NOT NULL,                     -- 사이트 URL
    category VARCHAR(50),                       -- 카테고리 (official/securities/news/data)

    -- 신뢰도 평가
    reliability_rating INTEGER,                 -- 1-5 (5가 가장 신뢰)
    data_quality_score DECIMAL(3,2),            -- 0.0 ~ 1.0

    -- Tier 분류
    tier INTEGER,                               -- 1: Official, 2: API, 3: Scraping, 4: Browser

    -- 상태
    is_active BOOLEAN DEFAULT TRUE,
    is_official BOOLEAN DEFAULT FALSE,          -- 공식 데이터 소스 여부

    -- 메타
    description TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reference_sites_name ON reference_sites(site_name_ko);
CREATE INDEX idx_reference_sites_category ON reference_sites(category);
CREATE INDEX idx_reference_sites_active ON reference_sites(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_reference_sites_rating ON reference_sites(reliability_rating DESC);

COMMENT ON TABLE reference_sites IS '41개 데이터 수집 사이트 마스터';
COMMENT ON COLUMN reference_sites.tier IS 'Tier 1: Official Libs, 2: API, 3: Scraping, 4: Browser';


-- 15. analysis_domains: 분석 도메인 (가격, 수급, 뉴스 등)
CREATE TABLE IF NOT EXISTS analysis_domains (
    id SERIAL PRIMARY KEY,
    domain_code VARCHAR(50) UNIQUE NOT NULL,    -- price/supply/news/report/chart
    domain_name_ko VARCHAR(100) NOT NULL,       -- 도메인명 (한글)
    domain_name_en VARCHAR(100),                -- 도메인명 (영문)
    description TEXT,

    -- 우선순위
    priority INTEGER DEFAULT 5,                 -- 1(높음) ~ 10(낮음)

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_analysis_domains_code ON analysis_domains(domain_code);
CREATE INDEX idx_analysis_domains_priority ON analysis_domains(priority);

COMMENT ON TABLE analysis_domains IS '분석 도메인 분류 (가격/수급/뉴스/리포트/차트)';


-- 16. site_analysis_mapping: 사이트-도메인 매핑
CREATE TABLE IF NOT EXISTS site_analysis_mapping (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES reference_sites(id) ON DELETE CASCADE,
    domain_id INTEGER NOT NULL REFERENCES analysis_domains(id) ON DELETE CASCADE,

    -- 적합도 평가
    suitability_score INTEGER,                  -- 1-5 (해당 도메인 데이터 품질)
    is_primary_source BOOLEAN DEFAULT FALSE,    -- 주요 소스 여부

    -- 메타
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(site_id, domain_id)
);

CREATE INDEX idx_site_analysis_mapping_site ON site_analysis_mapping(site_id);
CREATE INDEX idx_site_analysis_mapping_domain ON site_analysis_mapping(domain_id);
CREATE INDEX idx_site_analysis_mapping_score ON site_analysis_mapping(suitability_score DESC);

COMMENT ON TABLE site_analysis_mapping IS '사이트-도메인 매핑 (어떤 사이트가 어떤 도메인 데이터 제공)';


-- 17. collected_data: 원시 수집 데이터 (JSONB)
CREATE TABLE IF NOT EXISTS collected_data (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,                -- 종목코드 (stock_code와 호환)
    site_id INTEGER NOT NULL REFERENCES reference_sites(id) ON DELETE CASCADE,
    domain_id INTEGER NOT NULL REFERENCES analysis_domains(id) ON DELETE CASCADE,

    -- 데이터
    data_type VARCHAR(30) NOT NULL,             -- ohlcv/supply/news/report
    data_content JSONB NOT NULL,                -- 원시 JSON 데이터
    data_date DATE,                             -- 데이터 날짜

    -- 수집 정보
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validity_period INTERVAL,                   -- 데이터 유효기간
    expires_at TIMESTAMP,                       -- 만료 시각

    -- 품질 평가
    completeness_score INTEGER,                 -- 1-5 (데이터 완전성)
    reliability_score INTEGER,                  -- 1-5 (데이터 신뢰성)

    UNIQUE(ticker, site_id, domain_id, data_type, data_date),

    CHECK (completeness_score IS NULL OR (completeness_score >= 1 AND completeness_score <= 5)),
    CHECK (reliability_score IS NULL OR (reliability_score >= 1 AND reliability_score <= 5))
);

CREATE INDEX idx_collected_data_ticker ON collected_data(ticker);
CREATE INDEX idx_collected_data_site_domain ON collected_data(site_id, domain_id);
CREATE INDEX idx_collected_data_date ON collected_data(data_date DESC);
CREATE INDEX idx_collected_data_expires ON collected_data(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_collected_data_jsonb ON collected_data USING GIN(data_content);

COMMENT ON TABLE collected_data IS '원시 수집 데이터 (JSONB), ETL 전 단계';
COMMENT ON COLUMN collected_data.data_content IS 'JSONB 원시 데이터 (크롤링/API 결과)';


-- 18. fetch_execution_logs: 크롤링 실행 로그
CREATE TABLE IF NOT EXISTS fetch_execution_logs (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES reference_sites(id) ON DELETE CASCADE,
    domain_id INTEGER REFERENCES analysis_domains(id) ON DELETE SET NULL,
    ticker VARCHAR(20),                         -- 특정 종목 크롤링인 경우

    -- 실행 정보
    execution_status VARCHAR(20) NOT NULL,      -- success/failed/timeout/skipped
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    execution_time_ms INTEGER,                  -- 실행 시간 (밀리초)

    -- 결과
    records_fetched INTEGER DEFAULT 0,          -- 수집된 레코드 수
    data_quality_score INTEGER,                 -- 1-5

    -- 에러 정보
    error_type VARCHAR(50),                     -- network/parsing/timeout/auth
    error_message TEXT,
    error_stack_trace TEXT,

    -- 재시도
    retry_count INTEGER DEFAULT 0,
    retry_strategy VARCHAR(50),                 -- exponential/linear/fixed

    -- 환경 정보
    fetcher_version VARCHAR(20),
    python_version VARCHAR(20),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CHECK (execution_status IN ('success', 'failed', 'timeout', 'skipped')),
    CHECK (data_quality_score IS NULL OR (data_quality_score >= 1 AND data_quality_score <= 5))
);

CREATE INDEX idx_fetch_logs_site_status ON fetch_execution_logs(site_id, execution_status);
CREATE INDEX idx_fetch_logs_started_at ON fetch_execution_logs(started_at DESC);
CREATE INDEX idx_fetch_logs_ticker ON fetch_execution_logs(ticker) WHERE ticker IS NOT NULL;
CREATE INDEX idx_fetch_logs_error_type ON fetch_execution_logs(error_type) WHERE error_type IS NOT NULL;

COMMENT ON TABLE fetch_execution_logs IS '크롤링 실행 로그 (성공/실패/에러 추적)';


-- 19. site_health_status: 사이트 헬스체크
CREATE TABLE IF NOT EXISTS site_health_status (
    id SERIAL PRIMARY KEY,
    site_id INTEGER UNIQUE NOT NULL REFERENCES reference_sites(id) ON DELETE CASCADE,

    -- 상태
    status VARCHAR(20) NOT NULL,                -- active/degraded/failed/maintenance
    last_success_at TIMESTAMP,
    last_failure_at TIMESTAMP,
    consecutive_failures INTEGER DEFAULT 0,

    -- 구조 변경 감지
    structure_hash VARCHAR(64),                 -- 최근 HTML 구조 해시
    structure_verified_at TIMESTAMP,
    structure_change_detected BOOLEAN DEFAULT FALSE,

    -- 성능 지표
    avg_response_time_ms INTEGER,              -- 평균 응답시간
    success_rate DECIMAL(5,2),                 -- 성공률 (%)

    -- 현재 에러
    current_error_message TEXT,

    -- 메타
    last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CHECK (status IN ('active', 'degraded', 'failed', 'maintenance')),
    CHECK (success_rate IS NULL OR (success_rate >= 0 AND success_rate <= 100))
);

CREATE INDEX idx_site_health_status ON site_health_status(status);
CREATE INDEX idx_site_health_failures ON site_health_status(consecutive_failures DESC)
    WHERE consecutive_failures > 0;
CREATE INDEX idx_site_health_last_checked ON site_health_status(last_checked_at DESC);

COMMENT ON TABLE site_health_status IS '사이트 헬스체크 (가용성, 성능, 구조 변경 모니터링)';


-- 20. site_scraping_config: 크롤링 설정
CREATE TABLE IF NOT EXISTS site_scraping_config (
    id SERIAL PRIMARY KEY,
    site_id INTEGER UNIQUE NOT NULL REFERENCES reference_sites(id) ON DELETE CASCADE,

    -- 접근 방법
    access_method VARCHAR(20) NOT NULL,         -- api/web_scraping/selenium/playwright
    requires_login BOOLEAN DEFAULT FALSE,
    requires_javascript BOOLEAN DEFAULT FALSE,

    -- API 설정
    api_base_url TEXT,
    api_key_required BOOLEAN DEFAULT FALSE,
    api_rate_limit_per_minute INTEGER,

    -- HTML 파싱 설정
    html_selectors JSONB,                       -- CSS/XPath 셀렉터
    expected_elements JSONB,                    -- 예상되는 HTML 요소

    -- 재시도 설정
    max_retries INTEGER DEFAULT 3,
    retry_delay_seconds INTEGER DEFAULT 5,
    timeout_seconds INTEGER DEFAULT 30,

    -- User-Agent 설정
    custom_user_agent TEXT,
    use_random_user_agent BOOLEAN DEFAULT TRUE,

    -- 헬스체크
    health_check_url TEXT,
    health_check_interval_minutes INTEGER DEFAULT 60,

    -- 상태
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CHECK (access_method IN ('api', 'web_scraping', 'selenium', 'playwright'))
);

CREATE INDEX idx_scraping_config_method ON site_scraping_config(access_method);
CREATE INDEX idx_scraping_config_active ON site_scraping_config(is_active);

COMMENT ON TABLE site_scraping_config IS '크롤링 설정 (접근 방법, 재시도, 파싱 규칙)';


-- 21. site_structure_snapshots: HTML 구조 스냅샷
CREATE TABLE IF NOT EXISTS site_structure_snapshots (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES reference_sites(id) ON DELETE CASCADE,

    -- 스냅샷 정보
    snapshot_type VARCHAR(20) NOT NULL,         -- baseline/change_detection
    structure_hash VARCHAR(64) NOT NULL,        -- HTML 구조 해시 (SHA-256)
    structure_sample TEXT,                      -- HTML 샘플 (처음 1000자)

    -- 요소 분석
    elements_found JSONB,                       -- 발견된 HTML 요소 목록

    -- 유효성
    is_valid BOOLEAN DEFAULT TRUE,
    is_baseline BOOLEAN DEFAULT FALSE,          -- 기준 스냅샷 여부

    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_structure_snapshots_site ON site_structure_snapshots(site_id);
CREATE INDEX idx_structure_snapshots_hash ON site_structure_snapshots(structure_hash);
CREATE INDEX idx_structure_snapshots_captured ON site_structure_snapshots(captured_at DESC);
CREATE INDEX idx_structure_snapshots_baseline ON site_structure_snapshots(is_baseline)
    WHERE is_baseline = TRUE;

COMMENT ON TABLE site_structure_snapshots IS 'HTML 구조 스냅샷 (변경 감지용)';


-- ============================================================
-- 기존 data_sources 테이블에 reference_sites 연결 (FK 추가)
-- ============================================================

-- data_sources에 reference_site_id 컬럼 추가
ALTER TABLE data_sources
ADD COLUMN IF NOT EXISTS reference_site_id INTEGER REFERENCES reference_sites(id) ON DELETE SET NULL;

CREATE INDEX idx_data_sources_site ON data_sources(reference_site_id)
    WHERE reference_site_id IS NOT NULL;

COMMENT ON COLUMN data_sources.reference_site_id IS '데이터 소스가 특정 사이트에서 수집된 경우 연결';


-- ============================================================
-- Triggers: Auto-update timestamps
-- ============================================================

-- reference_sites
CREATE TRIGGER update_reference_sites_timestamp
    BEFORE UPDATE ON reference_sites
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- analysis_domains
CREATE TRIGGER update_analysis_domains_timestamp
    BEFORE UPDATE ON analysis_domains
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- site_analysis_mapping
CREATE TRIGGER update_site_analysis_mapping_timestamp
    BEFORE UPDATE ON site_analysis_mapping
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- site_health_status
CREATE TRIGGER update_site_health_timestamp
    BEFORE UPDATE ON site_health_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- site_scraping_config
CREATE TRIGGER update_scraping_config_timestamp
    BEFORE UPDATE ON site_scraping_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================
-- Views: Site Management
-- ============================================================

-- View: 사이트 카테고리별 통계
CREATE OR REPLACE VIEW v_reference_sites_by_category AS
SELECT
    category,
    COUNT(*) AS site_count,
    COUNT(*) FILTER (WHERE is_active = TRUE) AS active_count,
    AVG(reliability_rating) AS avg_rating,
    AVG(data_quality_score) AS avg_quality
FROM reference_sites
GROUP BY category
ORDER BY site_count DESC;

COMMENT ON VIEW v_reference_sites_by_category IS '사이트 카테고리별 통계';


-- View: 사이트 헬스 대시보드
CREATE OR REPLACE VIEW v_site_health_dashboard AS
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
ORDER BY shs.consecutive_failures DESC, shs.success_rate ASC;

COMMENT ON VIEW v_site_health_dashboard IS '사이트 헬스 대시보드 (장애 우선 정렬)';


-- View: 최근 실패한 사이트 분석
CREATE OR REPLACE VIEW v_failed_sites_analysis AS
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

COMMENT ON VIEW v_failed_sites_analysis IS '최근 7일 실패 사이트 분석';


-- View: 분석 도메인별 사이트 수
CREATE OR REPLACE VIEW v_analysis_domain_statistics AS
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

COMMENT ON VIEW v_analysis_domain_statistics IS '분석 도메인별 사이트 통계';


-- View: 도메인별 최고 품질 사이트
CREATE OR REPLACE VIEW v_analysis_domain_top_sites AS
WITH ranked_sites AS (
    SELECT
        ad.domain_code,
        ad.domain_name_ko,
        rs.site_name_ko,
        rs.tier,
        sam.suitability_score,
        rs.reliability_rating,
        ROW_NUMBER() OVER (PARTITION BY ad.domain_code ORDER BY sam.suitability_score DESC, rs.reliability_rating DESC) AS rank
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

COMMENT ON VIEW v_analysis_domain_top_sites IS '도메인별 상위 3개 사이트';


-- View: 사이트별 분석 능력
CREATE OR REPLACE VIEW v_site_analysis_capabilities AS
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
ORDER BY domain_count DESC, avg_suitability DESC;

COMMENT ON VIEW v_site_analysis_capabilities IS '사이트별 분석 능력 (지원 도메인)';


-- View: 고신뢰도 사이트 목록
CREATE OR REPLACE VIEW v_high_reliability_sites AS
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
ORDER BY rs.reliability_rating DESC, shs.success_rate DESC;

COMMENT ON VIEW v_high_reliability_sites IS '고신뢰도 사이트 (rating>=4, success>=90%)';


-- ============================================================
-- Initial Data: analysis_domains (분석 도메인)
-- ============================================================

INSERT INTO analysis_domains (domain_code, domain_name_ko, domain_name_en, priority) VALUES
('price', '가격 데이터', 'Price Data', 1),
('supply', '수급 데이터', 'Supply & Demand', 2),
('chart', '차트 기술지표', 'Technical Indicators', 3),
('news', '뉴스 감성', 'News Sentiment', 4),
('report', '증권사 리포트', 'Analyst Reports', 5),
('financial', '재무제표', 'Financial Statements', 6),
('theme', '테마/섹터', 'Theme & Sector', 7),
('disclosure', '공시정보', 'Disclosure', 8)
ON CONFLICT (domain_code) DO NOTHING;


-- ============================================================
-- Success Message
-- ============================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Site Management Tables added successfully!';
    RAISE NOTICE '📊 New tables: 8 (reference_sites + 7 related)';
    RAISE NOTICE '🔗 Updated tables: 1 (data_sources FK added)';
    RAISE NOTICE '👁️  New views: 7';
    RAISE NOTICE '⚡ New triggers: 5';
    RAISE NOTICE '📝 Initial analysis_domains: 8';
    RAISE NOTICE '';
    RAISE NOTICE '📋 Total tables: 20 (13 기존 + 7 신규)';
END $$;
