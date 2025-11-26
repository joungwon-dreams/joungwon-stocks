-- ============================================================
-- News Table Schema
-- 뉴스 데이터 저장 테이블
-- Created: 2025-11-27
-- ============================================================

-- 뉴스 테이블
CREATE TABLE IF NOT EXISTS news (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL REFERENCES stocks(stock_code),
    title VARCHAR(500) NOT NULL,                    -- 뉴스 제목
    url VARCHAR(1000),                              -- 뉴스 URL
    content TEXT,                                   -- 뉴스 본문 (요약)
    published_at TIMESTAMP,                         -- 발행 시간
    source VARCHAR(50) DEFAULT 'naver',             -- 출처 (naver, daum, dart 등)
    sentiment VARCHAR(20),                          -- 감성 분석 결과 (positive/negative/neutral)
    sentiment_score DECIMAL(3,2),                   -- 감성 점수 (-1.0 ~ 1.0)
    is_disclosure BOOLEAN DEFAULT FALSE,            -- DART 공시 여부

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 중복 방지 (같은 종목, 같은 URL)
    UNIQUE(stock_code, url)
);

-- 인덱스
CREATE INDEX idx_news_stock_code ON news(stock_code);
CREATE INDEX idx_news_published_at ON news(published_at DESC);
CREATE INDEX idx_news_source ON news(source);
CREATE INDEX idx_news_stock_published ON news(stock_code, published_at DESC);

COMMENT ON TABLE news IS '종목별 뉴스 및 공시 데이터';
COMMENT ON COLUMN news.sentiment IS '감성 분석 결과 (Gemini AI)';
COMMENT ON COLUMN news.is_disclosure IS 'DART 전자공시 여부';

-- 성공 메시지
DO $$
BEGIN
    RAISE NOTICE '✅ News table created successfully!';
END $$;
