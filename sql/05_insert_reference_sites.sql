-- ============================================================
-- Reference Sites Initial Data (41 Sites)
-- 한국 주식 투자 데이터 수집을 위한 41개 사이트 등록
-- ============================================================

-- ⚠️ WARNING: 기존 데이터 삭제 (CASCADE)
-- collected_data, site_analysis_mapping, fetch_execution_logs 등 모두 삭제됨

-- Delete existing data
DELETE FROM site_analysis_mapping;
DELETE FROM collected_data;
DELETE FROM fetch_execution_logs;
DELETE FROM site_health_status;
DELETE FROM site_scraping_config;
DELETE FROM site_structure_snapshots;
DELETE FROM reference_sites CASCADE;

-- Reset sequence
ALTER SEQUENCE reference_sites_id_seq RESTART WITH 1;

-- ============================================================
-- Tier 1: Official Libraries (공식 라이브러리)
-- ============================================================

INSERT INTO reference_sites (
    site_name_ko, site_name_en, url,
    category, reliability_rating, data_quality_score,
    tier, is_official, is_active, description
) VALUES
('한국거래소(KRX)', 'Korea Exchange', 'https://www.krx.co.kr',
 'official', 5, 1.00, 1, TRUE, TRUE,
 'pykrx 라이브러리로 수집 - 주가, 시가총액, 거래량 등 공식 데이터'),

('금융감독원 전자공시', 'DART', 'https://dart.fss.or.kr',
 'official', 5, 1.00, 1, TRUE, TRUE,
 'dart-fss 라이브러리로 수집 - 사업보고서, 감사보고서, 공시자료'),

('FinanceDataReader', 'FinanceDataReader', 'https://github.com/FinanceData/FinanceDataReader',
 'data', 4, 0.95, 1, FALSE, TRUE,
 '오픈소스 금융 데이터 라이브러리 - 종목 리스트, 일봉 데이터'),

('OpenDART API', 'OpenDART', 'https://opendart.fss.or.kr/api/developer.do',
 'official', 5, 1.00, 1, TRUE, TRUE,
 'opendartreader 라이브러리로 수집 - DART API 공식 인터페이스'),

-- ============================================================
-- Tier 2: Official APIs (공식 API)
-- ============================================================

('한국투자증권', 'Korea Investment', 'https://apiportal.koreainvestment.com',
 'securities', 5, 0.98, 2, TRUE, TRUE,
 'python-kis 라이브러리 - 실시간 주가, 호가, 체결, 자동매매'),

('네이버 금융', 'Naver Finance', 'https://finance.naver.com',
 'data', 4, 0.90, 2, TRUE, TRUE,
 'Naver Finance API - 뉴스, 종목 토론, 외국인/기관 매매'),

('다음 금융', 'Daum Finance', 'https://finance.daum.net',
 'data', 4, 0.88, 2, TRUE, TRUE,
 '다음 금융 데이터 - 뉴스, 시세, 차트'),

('KRX 정보데이터시스템', 'KRX Data', 'http://data.krx.co.kr',
 'official', 5, 0.95, 2, TRUE, TRUE,
 'KRX 공식 데이터 조회 시스템 - 업종별/테마별 지수'),

('금융투자협회', 'KOFIA', 'https://www.kofia.or.kr',
 'official', 4, 0.92, 2, TRUE, TRUE,
 '증권사 리포트, 통계 데이터'),

-- ============================================================
-- Tier 3: Web Scraping - Securities Firms (증권사)
-- ============================================================

('삼성증권', 'Samsung Securities', 'https://www.samsungpop.com',
 'securities', 4, 0.88, 3, FALSE, TRUE,
 '리서치센터 리포트, 종목 분석, 투자의견'),

('NH투자증권', 'NH Investment', 'https://www.nhqv.com',
 'securities', 4, 0.87, 3, FALSE, TRUE,
 'WM Biz 리포트, 업종 분석, 종목 레포트'),

('미래에셋증권', 'Mirae Asset', 'https://securities.miraeasset.com',
 'securities', 4, 0.89, 3, FALSE, TRUE,
 '리서치센터 - Equity Research, 산업분석'),

('KB증권', 'KB Securities', 'https://www.kbsec.com',
 'securities', 4, 0.86, 3, FALSE, TRUE,
 '투자정보 - 리서치, 종목 분석'),

('신한투자증권', 'Shinhan Securities', 'https://open.shinhaninvest.com',
 'securities', 4, 0.87, 3, FALSE, TRUE,
 '리서치센터 - 기업분석, 산업분석'),

('한국투자증권 리포트', 'Korea Investment Reports', 'https://securities.koreainvestment.com',
 'securities', 4, 0.88, 3, FALSE, TRUE,
 '투자정보 - 리서치 리포트, Market Briefing'),

('대신증권', 'Daishin Securities', 'https://www.daishin.com',
 'securities', 3, 0.84, 3, FALSE, TRUE,
 '투자정보 - 종목 리포트, 시장 전망'),

('하나증권', 'Hana Securities', 'https://www.hanaw.com',
 'securities', 3, 0.83, 3, FALSE, TRUE,
 '투자정보 - 리서치 자료'),

('키움증권', 'Kiwoom Securities', 'https://www.kiwoom.com',
 'securities', 4, 0.85, 3, FALSE, TRUE,
 '투자정보 - 종목분석, 시장분석'),

('이베스트투자증권', 'eBest Securities', 'https://www.ebestsec.co.kr',
 'securities', 3, 0.82, 3, FALSE, TRUE,
 '투자정보 - 리서치센터'),

('메리츠증권', 'Meritz Securities', 'https://www.meritz.co.kr',
 'securities', 3, 0.84, 3, FALSE, TRUE,
 '투자정보 - 종목 리포트'),

('유진투자증권', 'Eugene Investment', 'https://www.eugenefn.com',
 'securities', 3, 0.83, 3, FALSE, TRUE,
 '리서치센터 - Equity Research'),

-- ============================================================
-- Tier 3: Web Scraping - News Sites (뉴스 사이트)
-- ============================================================

('네이버 증권뉴스', 'Naver Stock News', 'https://finance.naver.com/news',
 'news', 4, 0.87, 3, FALSE, TRUE,
 '실시간 증권 뉴스 - 종목 뉴스, 시황'),

('다음 증권뉴스', 'Daum Stock News', 'https://finance.daum.net/news',
 'news', 4, 0.86, 3, FALSE, TRUE,
 '실시간 증권 뉴스 - 종목별, 테마별'),

('한국경제', 'Korea Economy', 'https://www.hankyung.com/stock-market',
 'news', 4, 0.88, 3, FALSE, TRUE,
 '증권 뉴스, 시황 분석, 기업 심층 분석'),

('매일경제', 'Maeil Business', 'https://www.mk.co.kr/stock',
 'news', 4, 0.87, 3, FALSE, TRUE,
 '증권 뉴스, 종목 분석, 시장 전망'),

('서울경제', 'Seoul Economy', 'https://www.sedaily.com/Stock',
 'news', 4, 0.85, 3, FALSE, TRUE,
 '증권 뉴스, 증시 전망'),

('파이낸셜뉴스', 'Financial News', 'https://www.fnnews.com/stock',
 'news', 4, 0.86, 3, FALSE, TRUE,
 '증권 뉴스, 종목 정보'),

('이데일리', 'Edaily', 'https://www.edaily.co.kr/stock',
 'news', 4, 0.85, 3, FALSE, TRUE,
 '실시간 증권 뉴스, 시황'),

('연합인포맥스', 'Yonhap Infomax', 'https://www.einfomax.co.kr',
 'news', 4, 0.88, 3, FALSE, TRUE,
 '금융 전문 뉴스통신 - 실시간 시황, 속보'),

('뉴스핌', 'Newspim', 'https://www.newspim.com/stock',
 'news', 3, 0.84, 3, FALSE, TRUE,
 '증권 뉴스, 기업 분석'),

('머니투데이', 'Money Today', 'https://stock.mt.co.kr',
 'news', 4, 0.86, 3, FALSE, TRUE,
 '증권 뉴스, 시황 분석, 투자 정보'),

-- ============================================================
-- Tier 3: Web Scraping - Investment Info Sites (투자정보)
-- ============================================================

('38커뮤니케이션', '38 Communication', 'http://www.38.co.kr',
 'data', 4, 0.90, 3, FALSE, TRUE,
 '애널리스트 컨센서스, 목표주가, 투자의견 집계'),

('에프앤가이드', 'FnGuide', 'https://www.fnguide.com',
 'data', 4, 0.92, 3, FALSE, TRUE,
 '기업 재무정보, 컨센서스, 업종 분석'),

('WISEfn', 'WISEfn', 'https://www.wisefn.com',
 'data', 4, 0.91, 3, FALSE, TRUE,
 '기업 재무 데이터, 산업 분석'),

('증권플러스', 'Stock Plus', 'https://www.stockplus.com',
 'data', 3, 0.83, 3, FALSE, TRUE,
 '종목 정보, 투자 의견'),

('Quantiwise', 'Quantiwise', 'https://www.quantiwise.com',
 'data', 4, 0.89, 3, FALSE, TRUE,
 '퀀트 투자 정보, 팩터 분석'),

('와이즈리포트', 'Wise Report', 'http://www.wisereport.co.kr',
 'data', 3, 0.84, 3, FALSE, TRUE,
 '증권사 리포트 통합 검색'),

-- ============================================================
-- Tier 4: Browser Automation (브라우저 자동화)
-- ============================================================

('증권사 HTS 웹', 'Securities HTS Web', 'https://various',
 'securities', 3, 0.80, 4, FALSE, TRUE,
'Playwright - 증권사 웹 HTS (동적 데이터)'),

('복잡한 차트 사이트', 'Chart Sites', 'https://various',
 'data', 3, 0.79, 4, FALSE, TRUE,
 'Playwright - JavaScript 기반 차트, 기술적 지표'),

('커뮤니티 사이트', 'Community Sites', 'https://various',
 'news', 2, 0.75, 4, FALSE, TRUE,
 'DrissionPage - 종목 토론방, 투자자 심리'),

('소셜 미디어 분석', 'Social Media', 'https://various',
 'news', 2, 0.73, 4, FALSE, TRUE,
 'Playwright - 트위터, 네이버 카페 등 투자 심리 분석');

-- ============================================================
-- Analysis Domains Data (already inserted in 03_add_site_management_tables.sql)
-- But verify if exists
-- ============================================================

-- Check if analysis_domains are already populated
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM analysis_domains WHERE domain_code = 'price') THEN
        -- Insert analysis domains if not exists
        INSERT INTO analysis_domains (domain_code, domain_name_ko, domain_name_en, priority, is_active) VALUES
        ('price', '가격/시세', 'Price Data', 1, TRUE),
        ('supply', '수급 분석', 'Supply/Demand', 2, TRUE),
        ('chart', '차트/기술', 'Technical Analysis', 3, TRUE),
        ('news', '뉴스/속보', 'News', 4, TRUE),
        ('report', '리포트/의견', 'Research Reports', 5, TRUE),
        ('financial', '재무/실적', 'Financial Data', 6, TRUE),
        ('theme', '테마/이슈', 'Theme Analysis', 7, TRUE),
        ('disclosure', '공시', 'Disclosure', 8, TRUE);
    END IF;
END $$;

-- ============================================================
-- Site-Domain Mapping (사이트별 제공 가능 분석 도메인)
-- ============================================================

-- Helper function to get IDs
DO $$
DECLARE
    v_site_id INTEGER;
    v_domain_id INTEGER;
BEGIN
    -- Tier 1: Official Libraries

    -- KRX: price, supply, chart
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'Korea Exchange';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 5, TRUE FROM analysis_domains WHERE domain_code IN ('price', 'supply', 'chart');

    -- DART: financial, disclosure
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'DART';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 5, TRUE FROM analysis_domains WHERE domain_code IN ('financial', 'disclosure');

    -- FinanceDataReader: price
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'FinanceDataReader';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 4, FALSE FROM analysis_domains WHERE domain_code = 'price';

    -- OpenDART: disclosure, financial
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'OpenDART';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 5, TRUE FROM analysis_domains WHERE domain_code IN ('disclosure', 'financial');

    -- Tier 2: Official APIs

    -- Korea Investment: price, supply, chart (실시간)
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'Korea Investment';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 5, TRUE FROM analysis_domains WHERE domain_code IN ('price', 'supply', 'chart');

    -- Naver Finance: price, news, theme, supply
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'Naver Finance';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 4, FALSE FROM analysis_domains WHERE domain_code IN ('price', 'news', 'theme', 'supply');

    -- Daum Finance: price, news
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'Daum Finance';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 4, FALSE FROM analysis_domains WHERE domain_code IN ('price', 'news');

    -- KRX Data: price, supply, theme
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'KRX Data';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 5, TRUE FROM analysis_domains WHERE domain_code IN ('price', 'supply', 'theme');

    -- KOFIA: report, financial
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'KOFIA';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 4, FALSE FROM analysis_domains WHERE domain_code IN ('report', 'financial');

    -- Tier 3: Securities Firms (증권사 - all provide reports)
    FOR v_site_id IN
        SELECT id FROM reference_sites WHERE category = 'securities' AND tier = 3
    LOOP
        INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
        SELECT v_site_id, id, 4, FALSE FROM analysis_domains WHERE domain_code IN ('report', 'financial', 'theme');
    END LOOP;

    -- Tier 3: News Sites (뉴스 - all provide news and theme)
    FOR v_site_id IN
        SELECT id FROM reference_sites WHERE category = 'news' AND tier = 3
    LOOP
        INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
        SELECT v_site_id, id, 4, FALSE FROM analysis_domains WHERE domain_code IN ('news', 'theme');
    END LOOP;

    -- Tier 3: Investment Info Sites (투자정보)

    -- 38커뮤니케이션: report (컨센서스)
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = '38 Communication';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 5, TRUE FROM analysis_domains WHERE domain_code = 'report';

    -- FnGuide: financial, report
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'FnGuide';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 5, TRUE FROM analysis_domains WHERE domain_code IN ('financial', 'report');

    -- WISEfn: financial
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'WISEfn';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 4, FALSE FROM analysis_domains WHERE domain_code = 'financial';

    -- Stock Plus: report
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'Stock Plus';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 3, FALSE FROM analysis_domains WHERE domain_code = 'report';

    -- Quantiwise: chart
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'Quantiwise';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 4, FALSE FROM analysis_domains WHERE domain_code = 'chart';

    -- Wise Report: report
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'Wise Report';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 3, FALSE FROM analysis_domains WHERE domain_code = 'report';

    -- Tier 4: Browser Automation

    -- Securities HTS Web: price, chart
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'Securities HTS Web';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 3, FALSE FROM analysis_domains WHERE domain_code IN ('price', 'chart');

    -- Chart Sites: chart
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'Chart Sites';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 3, FALSE FROM analysis_domains WHERE domain_code = 'chart';

    -- Community Sites: theme
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'Community Sites';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 2, FALSE FROM analysis_domains WHERE domain_code = 'theme';

    -- Social Media: theme, news
    SELECT id INTO v_site_id FROM reference_sites WHERE site_name_en = 'Social Media';
    INSERT INTO site_analysis_mapping (site_id, domain_id, suitability_score, is_primary_source)
    SELECT v_site_id, id, 2, FALSE FROM analysis_domains WHERE domain_code IN ('theme', 'news');

END $$;

-- ============================================================
-- Verification Queries
-- ============================================================

-- Show summary
SELECT
    '총 사이트 수' AS metric,
    COUNT(*)::TEXT AS value
FROM reference_sites
UNION ALL
SELECT
    'Tier ' || tier AS metric,
    COUNT(*)::TEXT || '개' AS value
FROM reference_sites
GROUP BY tier
ORDER BY metric, value;

-- Show sites by category
SELECT
    category,
    COUNT(*) AS site_count,
    AVG(reliability_rating) AS avg_rating,
    AVG(data_quality_score) AS avg_quality
FROM reference_sites
GROUP BY category
ORDER BY site_count DESC;

-- Show domain coverage
SELECT
    ad.domain_name_ko,
    COUNT(sam.site_id) AS site_count,
    COUNT(CASE WHEN sam.is_primary_source = TRUE THEN 1 END) AS primary_sources
FROM analysis_domains ad
LEFT JOIN site_analysis_mapping sam ON ad.id = sam.domain_id
GROUP BY ad.domain_name_ko
ORDER BY site_count DESC;

-- ============================================================
-- Success Message
-- ============================================================

DO $$
BEGIN
    RAISE NOTICE '✅ 41개 사이트 등록 완료!';
    RAISE NOTICE '';
    RAISE NOTICE '📊 Tier 분포:';
    RAISE NOTICE '  - Tier 1 (공식 라이브러리): 4개';
    RAISE NOTICE '  - Tier 2 (공식 API): 5개';
    RAISE NOTICE '  - Tier 3 (웹 스크래핑): 28개';
    RAISE NOTICE '    • 증권사: 12개';
    RAISE NOTICE '    • 뉴스: 10개';
    RAISE NOTICE '    • 투자정보: 6개';
    RAISE NOTICE '  - Tier 4 (브라우저 자동화): 4개';
    RAISE NOTICE '';
    RAISE NOTICE '🔗 사이트-도메인 매핑 완료';
    RAISE NOTICE '📋 8개 분석 도메인별 사이트 매핑 생성';
END $$;
