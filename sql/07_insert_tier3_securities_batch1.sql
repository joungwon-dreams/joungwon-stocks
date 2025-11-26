-- ============================================================
-- Tier 3 Web Scraping Sites (Batch 1: Securities Firms)
-- ============================================================
-- Tier 3 증권사 스크래퍼 6개 등록
-- - 키움증권 (Kiwoom Securities)
-- - KB증권 (KB Securities)
-- - 신한투자증권 (Shinhan Securities)
-- - 메리츠증권 (Meritz Securities)
-- - 하나증권 (Hana Securities)
-- - 대신증권 (Daishin Securities)
-- ============================================================

-- Tier 3: Web Scraping (Securities Firms - Batch 1)
INSERT INTO reference_sites (
    site_name_ko, site_name_en, url,
    category, reliability_rating, data_quality_score,
    tier, is_official, is_active, description
) VALUES
('키움증권', 'Kiwoom Securities', 'https://www.kiwoom.com',
 'securities', 4, 0.87, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 리서치 보고서, 투자의견, 목표가, 애널리스트 추천'),

('KB증권', 'KB Securities', 'https://www.kbsec.com',
 'securities', 4, 0.87, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 기업분석 리포트, 투자의견, 목표주가, 애널리스트 의견'),

('신한투자증권', 'Shinhan Securities', 'https://www.shinhansec.com',
 'securities', 4, 0.86, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 리서치 보고서, 투자 추천, 목표가, 시장 분석'),

('메리츠증권', 'Meritz Securities', 'https://www.meritz.co.kr',
 'securities', 4, 0.86, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 기업분석, 리서치 리포트, 투자의견, 목표주가'),

('하나증권', 'Hana Securities', 'https://www.hanafn.com',
 'securities', 4, 0.85, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 리서치 보고서, 투자 추천, 애널리스트 의견'),

('대신증권', 'Daishin Securities', 'https://www.daishin.com',
 'securities', 4, 0.85, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 기업분석 리포트, 투자의견, 목표가 분석');

-- ============================================================
-- Verify Batch 1 Securities Sites Insertion
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
WHERE tier = 3 AND category = 'securities'
ORDER BY data_quality_score DESC;

-- ============================================================
-- Initialize Site Health Status for Batch 1 Sites
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
  AND category = 'securities'
  AND site_name_en IN (
      'Kiwoom Securities',
      'KB Securities',
      'Shinhan Securities',
      'Meritz Securities',
      'Hana Securities',
      'Daishin Securities'
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
    COUNT(CASE WHEN category = 'data' THEN 1 END) as data_provider_count
FROM reference_sites
WHERE tier = 3;
