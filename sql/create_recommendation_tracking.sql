-- =====================================================
-- Phase 9.5: 신규종목추천 검증 시스템 DB 스키마
-- Created: 2025-11-29
-- Purpose: 추천 이력 저장 및 2주간 성과 추적
-- =====================================================

-- =====================================================
-- 1. 신규종목 추천 이력 테이블
-- =====================================================
CREATE TABLE IF NOT EXISTS new_stock_recommendations (
    id SERIAL PRIMARY KEY,
    recommended_at TIMESTAMP NOT NULL,      -- 추천 시각
    stock_code VARCHAR(10) NOT NULL,        -- 종목코드
    stock_name VARCHAR(50) NOT NULL,        -- 종목명
    market VARCHAR(10) DEFAULT 'KOSPI',     -- KOSPI/KOSDAQ

    -- 추천 시점 정보
    recommended_price INT NOT NULL,         -- 추천 시점 현재가
    change_rate FLOAT,                      -- 추천 시점 등락률
    aegis_score FLOAT,                      -- AEGIS 점수
    scanner_score FLOAT,                    -- Scanner 점수

    -- 추천 근거
    key_reasons JSONB,                      -- ["골든크로스", "외인순매수", ...]
    detailed_analysis TEXT,                 -- 상세 분석 내용

    -- 기술적 지표
    rsi_14 FLOAT,
    ma_5 FLOAT,
    ma_20 FLOAT,
    ma_60 FLOAT,
    golden_cross BOOLEAN DEFAULT FALSE,

    -- 수급 정보
    foreigner_net BIGINT DEFAULT 0,
    institution_net BIGINT DEFAULT 0,
    traded_value BIGINT,                    -- 거래대금

    -- 추적 상태
    tracking_status VARCHAR(20) DEFAULT 'active',  -- active/completed/cancelled
    tracking_end_date DATE,                 -- 2주 후 (추적 종료일)

    -- 최종 성과 (추적 완료 후 업데이트)
    final_price INT,                        -- 2주 후 종가
    final_return FLOAT,                     -- 2주 후 최종 수익률
    max_return FLOAT,                       -- 기간 내 최고 수익률 (MFE)
    min_return FLOAT,                       -- 기간 내 최저 수익률 (MAE)
    best_day INT,                           -- 최고 수익 발생일 (D+?)
    worst_day INT,                          -- 최저 수익 발생일 (D+?)

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 중복 추천 방지 (같은 날 같은 종목은 1회만)
CREATE UNIQUE INDEX IF NOT EXISTS idx_rec_unique
ON new_stock_recommendations(stock_code, DATE(recommended_at));

-- =====================================================
-- 2. 일일 가격 추적 테이블
-- =====================================================
CREATE TABLE IF NOT EXISTS new_stock_tracking (
    id SERIAL PRIMARY KEY,
    recommendation_id INT REFERENCES new_stock_recommendations(id) ON DELETE CASCADE,
    tracking_date DATE NOT NULL,
    day_number INT NOT NULL,                -- D+1, D+2, ... D+14

    -- 가격 정보
    open_price INT,
    high_price INT,
    low_price INT,
    close_price INT,
    volume BIGINT,

    -- 수익률 계산
    daily_return FLOAT,                     -- 당일 수익률 (전일 종가 대비)
    cumulative_return FLOAT,                -- 누적 수익률 (추천가 대비)

    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(recommendation_id, tracking_date)
);

-- =====================================================
-- 3. 인덱스
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_rec_date ON new_stock_recommendations(recommended_at);
CREATE INDEX IF NOT EXISTS idx_rec_status ON new_stock_recommendations(tracking_status);
CREATE INDEX IF NOT EXISTS idx_rec_market ON new_stock_recommendations(market);
CREATE INDEX IF NOT EXISTS idx_rec_code ON new_stock_recommendations(stock_code);
CREATE INDEX IF NOT EXISTS idx_tracking_rec ON new_stock_tracking(recommendation_id);
CREATE INDEX IF NOT EXISTS idx_tracking_date ON new_stock_tracking(tracking_date);

-- =====================================================
-- 4. updated_at 자동 갱신 트리거
-- =====================================================
CREATE OR REPLACE FUNCTION update_recommendation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_rec_timestamp ON new_stock_recommendations;
CREATE TRIGGER trigger_update_rec_timestamp
    BEFORE UPDATE ON new_stock_recommendations
    FOR EACH ROW
    EXECUTE FUNCTION update_recommendation_timestamp();

-- =====================================================
-- 5. 검증 요약 뷰
-- =====================================================
CREATE OR REPLACE VIEW v_recommendation_performance AS
SELECT
    DATE(recommended_at) as rec_date,
    market,
    COUNT(*) as total_recommendations,
    COUNT(CASE WHEN tracking_status = 'completed' THEN 1 END) as completed,
    COUNT(CASE WHEN final_return > 0 THEN 1 END) as wins,
    COUNT(CASE WHEN final_return <= 0 THEN 1 END) as losses,
    ROUND(AVG(final_return)::numeric, 2) as avg_return,
    ROUND(MAX(max_return)::numeric, 2) as best_mfe,
    ROUND(MIN(min_return)::numeric, 2) as worst_mae,
    ROUND(
        (COUNT(CASE WHEN final_return > 0 THEN 1 END)::float /
         NULLIF(COUNT(CASE WHEN tracking_status = 'completed' THEN 1 END), 0) * 100)::numeric, 1
    ) as win_rate
FROM new_stock_recommendations
GROUP BY DATE(recommended_at), market
ORDER BY rec_date DESC;

-- =====================================================
-- 6. 완료 메시지
-- =====================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Phase 9.5 DB Schema created';
    RAISE NOTICE '   - new_stock_recommendations table';
    RAISE NOTICE '   - new_stock_tracking table';
    RAISE NOTICE '   - v_recommendation_performance view';
END $$;
