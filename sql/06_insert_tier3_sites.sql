-- ============================================================
-- Tier 3 Web Scraping Sites (Top 5 Priority)
-- ============================================================
-- Tier 3 웹 스크래핑 사이트 5개 등록
-- - FnGuide (에프앤가이드)
-- - WISEfn
-- - 38커뮤니케이션
-- - 미래에셋증권
-- - 삼성증권
-- ============================================================

-- Tier 3: Web Scraping (Priority Sites)
INSERT INTO reference_sites (
    site_name_ko, site_name_en, url,
    category, reliability_rating, data_quality_score,
    tier, is_official, is_active, description
) VALUES
('에프앤가이드', 'FnGuide', 'https://comp.fnguide.com',
 'data', 4, 0.92, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 기업 펀더멘털, 재무제표, 애널리스트 컨센서스, 밸류에이션 지표'),

('WISEfn', 'WISEfn', 'https://www.wisefn.com',
 'data', 4, 0.91, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 기업지배구조 지표(ESG), 재무분석, 투자분석 요약'),

('38커뮤니케이션', '38 Communication', 'http://www.38.co.kr',
 'data', 4, 0.90, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 매매신호, 기술적 지표, 추세 분석, 투자 추천'),

('미래에셋증권', 'Mirae Asset Securities', 'https://securities.miraeasset.com',
 'securities', 4, 0.89, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 애널리스트 리서치 보고서, 투자의견, 목표가, 재무예측'),

('삼성증권', 'Samsung Securities', 'https://www.samsungpop.com',
 'securities', 4, 0.88, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 리서치 보고서, 시장 인사이트, 투자 추천, 밸류에이션');

-- ============================================================
-- Verify Tier 3 Sites Insertion
-- ============================================================
SELECT
    id,
    site_name_ko,
    site_name_en,
    category,
    tier,
    reliability_rating,
    data_quality_score,
    is_active
FROM reference_sites
WHERE tier = 3
ORDER BY data_quality_score DESC;

-- ============================================================
-- Initialize Site Health Status for Tier 3 Sites
-- ============================================================
INSERT INTO site_health_status (
    site_id,
    status,
    consecutive_failures,
    success_rate,
    avg_response_time_ms,
    last_check_at,
    last_success_at
)
SELECT
    id,
    'healthy',
    0,
    0.0,
    0,
    NOW(),
    NULL
FROM reference_sites
WHERE tier = 3
ON CONFLICT (site_id) DO NOTHING;

-- ============================================================
-- Summary
-- ============================================================
SELECT
    tier,
    COUNT(*) as site_count,
    AVG(data_quality_score) as avg_quality,
    COUNT(CASE WHEN is_active THEN 1 END) as active_count
FROM reference_sites
GROUP BY tier
ORDER BY tier;
