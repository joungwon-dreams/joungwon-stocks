-- ============================================================
-- Tier 3 Web Scraping Sites (Batch 2: Data/Analysis)
-- ============================================================
-- Tier 3 데이터/분석 스크래퍼 6개 등록
-- - 한국투자증권 리포트 (Korea Investment Reports)
-- - NH투자증권 (NH Investment)
-- - QuantiWise
-- - 와이즈리포트 (Wise Report)
-- - 이베스트투자증권 (eBest Securities)
-- - 유진투자증권 (Eugene Investment)
-- ============================================================

-- Tier 3: Web Scraping (Data/Analysis - Batch 2)
-- Note: Some may already exist, using ON CONFLICT DO NOTHING
INSERT INTO reference_sites (
    site_name_ko, site_name_en, url,
    category, reliability_rating, data_quality_score,
    tier, is_official, is_active, description
) VALUES
('QuantiWise', 'QuantiWise', 'https://www.quantiwise.com',
 'data', 4, 0.84, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 퀀트 분석, 정량적 투자지표, 기술적 분석')

ON CONFLICT (site_name_ko, site_name_en) DO NOTHING;

-- eBest and Eugene if not already registered
INSERT INTO reference_sites (
    site_name_ko, site_name_en, url,
    category, reliability_rating, data_quality_score,
    tier, is_official, is_active, description
) VALUES
('와이즈리포트', 'Wise Report', 'https://www.wisereport.co.kr',
 'data', 4, 0.84, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 기업분석 리포트, 컨센서스, 목표가, 애널리스트 의견')

ON CONFLICT (site_name_ko, site_name_en) DO NOTHING;

-- ============================================================
-- Verify Batch 2 Data/Analysis Sites Insertion
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
WHERE tier = 3 AND category = 'data'
ORDER BY data_quality_score DESC;

-- ============================================================
-- Initialize Site Health Status for Batch 2 Sites
-- ============================================================
INSERT INTO site_health_status (
    site_id,
    status,
    consecutive_failures,
    success_rate,
    avg_response_time_ms
)
SELECT
    id,
    'healthy',
    0,
    0.0,
    0
FROM reference_sites
WHERE tier = 3
  AND category = 'data'
  AND site_name_en IN (
      'QuantiWise',
      'Wise Report'
  )
ON CONFLICT (site_id) DO NOTHING;

-- ============================================================
-- Summary: All Tier 3 Sites
-- ============================================================
SELECT
    tier,
    category,
    COUNT(*) as site_count,
    AVG(data_quality_score) as avg_quality,
    COUNT(CASE WHEN is_active THEN 1 END) as active_count
FROM reference_sites
WHERE tier = 3
GROUP BY tier, category
ORDER BY tier, category;

-- ============================================================
-- Total Tier 3 Implementation Progress
-- ============================================================
SELECT
    COUNT(*) as total_tier3_sites,
    COUNT(CASE WHEN category = 'securities' THEN 1 END) as securities_count,
    COUNT(CASE WHEN category = 'data' THEN 1 END) as data_provider_count,
    COUNT(CASE WHEN category = 'news' THEN 1 END) as news_count
FROM reference_sites
WHERE tier = 3;
