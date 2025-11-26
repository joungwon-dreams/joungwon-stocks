-- ============================================================
-- Tier 3 Web Scraping Sites (Batch 3: News/Media)
-- ============================================================
-- Tier 3 뉴스/미디어 스크래퍼 11개 등록
-- - 한국경제 (Korea Economy)
-- - 매일경제 (Maeil Business)
-- - 서울경제 (Seoul Economy)
-- - 파이낸셜뉴스 (Financial News)
-- - 머니투데이 (Money Today)
-- - 이데일리 (Edaily)
-- - 연합인포맥스 (Yonhap Infomax)
-- - 뉴스핌 (Newspim)
-- - 다음 증권뉴스 (Daum Stock News)
-- - 네이버 증권뉴스 (Naver Stock News)
-- - 스톡플러스 (Stock Plus)
-- ============================================================

-- Tier 3: Web Scraping (News/Media - Batch 3)
INSERT INTO reference_sites (
    site_name_ko, site_name_en, url,
    category, reliability_rating, data_quality_score,
    tier, is_official, is_active, description
) VALUES
('한국경제', 'Korea Economy', 'https://www.hankyung.com',
 'news', 4, 0.85, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 기업뉴스, 시장분석, 증권뉴스'),

('매일경제', 'Maeil Business', 'https://www.mk.co.kr',
 'news', 4, 0.85, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 경제뉴스, 기업분석, 증권정보'),

('서울경제', 'Seoul Economy', 'https://www.sedaily.com',
 'news', 4, 0.84, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 증권뉴스, 기업동향, 시장분석'),

('파이낸셜뉴스', 'Financial News', 'https://www.fnnews.com',
 'news', 4, 0.84, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 금융뉴스, 증권정보, 기업분석'),

('머니투데이', 'Money Today', 'https://www.mt.co.kr',
 'news', 4, 0.85, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 증권뉴스, 시장동향, 기업정보'),

('이데일리', 'Edaily', 'https://www.edaily.co.kr',
 'news', 4, 0.84, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 경제뉴스, 증권정보, 기업분석'),

('연합인포맥스', 'Yonhap Infomax', 'https://news.einfomax.co.kr',
 'news', 4, 0.85, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 금융뉴스, 증권정보, 시장분석'),

('뉴스핌', 'Newspim', 'https://www.newspim.com',
 'news', 4, 0.83, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 경제뉴스, 증권동향, 기업정보'),

('다음 증권뉴스', 'Daum Stock News', 'https://finance.daum.net',
 'news', 4, 0.86, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 다음 증권뉴스, 기업정보, 시장동향'),

('네이버 증권뉴스', 'Naver Stock News', 'https://finance.naver.com',
 'news', 5, 0.90, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 네이버 증권뉴스, 기업정보, 실시간 뉴스'),

('스톡플러스', 'Stock Plus', 'https://www.stockplus.com',
 'news', 4, 0.82, 3, FALSE, TRUE,
 'BeautifulSoup4로 수집 - 증권뉴스, 기업분석, 투자정보')

ON CONFLICT (site_name_ko, site_name_en) DO NOTHING;

-- ============================================================
-- Verify Batch 3 News/Media Sites Insertion
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
WHERE tier = 3 AND category = 'news'
ORDER BY data_quality_score DESC;

-- ============================================================
-- Initialize Site Health Status for Batch 3 Sites
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
  AND category = 'news'
  AND site_name_en IN (
      'Korea Economy',
      'Maeil Business',
      'Seoul Economy',
      'Financial News',
      'Money Today',
      'Edaily',
      'Yonhap Infomax',
      'Newspim',
      'Daum Stock News',
      'Naver Stock News',
      'Stock Plus'
  )
ON CONFLICT (site_id) DO NOTHING;

-- ============================================================
-- Summary: All Tier 3 Sites (Final Count)
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
-- Total Tier 3 Implementation Progress (COMPLETE: 28/28)
-- ============================================================
SELECT
    COUNT(*) as total_tier3_sites,
    COUNT(CASE WHEN category = 'securities' THEN 1 END) as securities_count,
    COUNT(CASE WHEN category = 'data' THEN 1 END) as data_provider_count,
    COUNT(CASE WHEN category = 'news' THEN 1 END) as news_count,
    ROUND(AVG(data_quality_score), 2) as avg_quality_score
FROM reference_sites
WHERE tier = 3;
