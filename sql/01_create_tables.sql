-- ============================================================
-- joungwon.stocks Database Schema
-- PostgreSQL 14.20+
--
-- Description: AI-powered Korean stock trading system
-- Author: wonny
-- Created: 2025-11-24
-- ============================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- Group 1: Master Tables (종목 마스터 데이터)
-- ============================================================

-- 1. stocks: 종목 마스터 (KRX 전 종목)
CREATE TABLE IF NOT EXISTS stocks (
    stock_code VARCHAR(6) PRIMARY KEY,              -- 종목코드 (6자리)
    stock_name VARCHAR(100) NOT NULL,               -- 종목명
    market VARCHAR(10),                             -- 시장구분 (KOSPI/KOSDAQ/KONEX)
    sector VARCHAR(50),                             -- 업종
    industry VARCHAR(100),                          -- 세부업종
    listing_date DATE,                              -- 상장일
    is_managed BOOLEAN DEFAULT FALSE,               -- 관리종목 여부
    is_delisted BOOLEAN DEFAULT FALSE,              -- 상장폐지 여부
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stocks_market ON stocks(market);
CREATE INDEX idx_stocks_sector ON stocks(sector);
CREATE INDEX idx_stocks_name ON stocks(stock_name);

COMMENT ON TABLE stocks IS '종목 마스터 데이터 (KRX 전 종목)';
COMMENT ON COLUMN stocks.stock_code IS '종목코드 6자리 (예: 005930)';
COMMENT ON COLUMN stocks.market IS '시장구분 (KOSPI/KOSDAQ/KONEX)';


-- 2. stock_assets: 보유 종목 및 매매 설정
CREATE TABLE IF NOT EXISTS stock_assets (
    stock_code VARCHAR(6) PRIMARY KEY REFERENCES stocks(stock_code),
    stock_name VARCHAR(100) NOT NULL,
    quantity INTEGER DEFAULT 0,                     -- 보유수량
    avg_buy_price DECIMAL(10,2) DEFAULT 0,         -- 평균매수가
    current_price DECIMAL(10,2) DEFAULT 0,         -- 현재가 (실시간 업데이트)

    -- 손익 계산
    total_value DECIMAL(15,2) GENERATED ALWAYS AS (quantity * current_price) STORED,
    total_cost DECIMAL(15,2) GENERATED ALWAYS AS (quantity * avg_buy_price) STORED,
    profit_loss DECIMAL(15,2) GENERATED ALWAYS AS (quantity * (current_price - avg_buy_price)) STORED,
    profit_loss_rate DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE
            WHEN avg_buy_price > 0 THEN ((current_price - avg_buy_price) / avg_buy_price * 100)
            ELSE 0
        END
    ) STORED,

    -- 매매 설정
    stop_loss_rate DECIMAL(5,2) DEFAULT -5.0,      -- 손절가율 (%)
    target_profit_rate DECIMAL(5,2) DEFAULT 10.0,  -- 목표수익률 (%)
    max_position DECIMAL(15,2) DEFAULT 0,          -- 최대 투자금액

    -- 상태
    is_active BOOLEAN DEFAULT TRUE,                 -- 활성 종목 여부
    auto_trading BOOLEAN DEFAULT FALSE,             -- 자동매매 활성화

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stock_assets_quantity ON stock_assets(quantity) WHERE quantity > 0;
CREATE INDEX idx_stock_assets_active ON stock_assets(is_active) WHERE is_active = TRUE;

COMMENT ON TABLE stock_assets IS '보유 종목 및 매매 설정';
COMMENT ON COLUMN stock_assets.avg_buy_price IS '평균 매수가 (누적 평단가)';
COMMENT ON COLUMN stock_assets.current_price IS 'min_ticks에서 실시간 업데이트';


-- ============================================================
-- Group 2: Price Data Tables (가격 데이터)
-- ============================================================

-- 3. daily_ohlcv: 일봉 데이터 (과거 1년)
CREATE TABLE IF NOT EXISTS daily_ohlcv (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL REFERENCES stocks(stock_code),
    date DATE NOT NULL,
    open DECIMAL(10,2) NOT NULL,
    high DECIMAL(10,2) NOT NULL,
    low DECIMAL(10,2) NOT NULL,
    close DECIMAL(10,2) NOT NULL,
    volume BIGINT NOT NULL,
    trading_value BIGINT,                           -- 거래대금 (원)

    -- 이동평균선
    ma5 DECIMAL(10,2),                              -- 5일 이평
    ma20 DECIMAL(10,2),                             -- 20일 이평
    ma60 DECIMAL(10,2),                             -- 60일 이평
    ma120 DECIMAL(10,2),                            -- 120일 이평

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(stock_code, date)
);

CREATE INDEX idx_daily_ohlcv_code_date ON daily_ohlcv(stock_code, date DESC);
CREATE INDEX idx_daily_ohlcv_date ON daily_ohlcv(date DESC);

COMMENT ON TABLE daily_ohlcv IS '일봉 데이터 (1년 보관)';
COMMENT ON COLUMN daily_ohlcv.trading_value IS '거래대금 = close * volume';


-- 4. min_ticks: 실시간 틱 데이터 (1분 단위)
CREATE TABLE IF NOT EXISTS min_ticks (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL REFERENCES stocks(stock_code),
    timestamp TIMESTAMP NOT NULL,
    price DECIMAL(10,2) NOT NULL,                   -- 현재가
    change_rate DECIMAL(5,2),                       -- 등락률 (%)
    volume BIGINT,                                  -- 거래량
    bid_price DECIMAL(10,2),                        -- 매수호가
    ask_price DECIMAL(10,2),                        -- 매도호가
    bid_volume BIGINT,                              -- 매수잔량
    ask_volume BIGINT,                              -- 매도잔량

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Partitioning by date for performance (optional, 향후 적용)
CREATE INDEX idx_min_ticks_code_timestamp ON min_ticks(stock_code, timestamp DESC);
CREATE INDEX idx_min_ticks_timestamp ON min_ticks(timestamp DESC);

COMMENT ON TABLE min_ticks IS '실시간 틱 데이터 (WebSocket 수신, 1일 보관)';


-- 5. stock_prices_10min: 10분 단위 기술 지표
CREATE TABLE IF NOT EXISTS stock_prices_10min (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL REFERENCES stocks(stock_code),
    timestamp TIMESTAMP NOT NULL,

    -- OHLCV
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,

    -- 기술 지표 (45개 중 주요 지표만)
    rsi_14 DECIMAL(5,2),                            -- RSI (14)
    macd DECIMAL(10,4),                             -- MACD
    macd_signal DECIMAL(10,4),                      -- MACD Signal
    macd_hist DECIMAL(10,4),                        -- MACD Histogram
    bb_upper DECIMAL(10,2),                         -- 볼린저밴드 상단
    bb_middle DECIMAL(10,2),                        -- 볼린저밴드 중간
    bb_lower DECIMAL(10,2),                         -- 볼린저밴드 하단
    bb_position DECIMAL(5,2),                       -- BB 내 위치 (0-100)
    stoch_k DECIMAL(5,2),                           -- Stochastic %K
    stoch_d DECIMAL(5,2),                           -- Stochastic %D

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(stock_code, timestamp)
);

CREATE INDEX idx_stock_prices_10min_code_time ON stock_prices_10min(stock_code, timestamp DESC);

COMMENT ON TABLE stock_prices_10min IS '10분 단위 기술 지표 (pandas-ta 계산)';


-- 6. stock_supply_demand: 수급 데이터 (외국인/기관/개인)
CREATE TABLE IF NOT EXISTS stock_supply_demand (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL REFERENCES stocks(stock_code),
    date DATE NOT NULL,

    -- 순매수 금액 (원)
    foreigner_net BIGINT DEFAULT 0,                 -- 외국인 순매수
    institution_net BIGINT DEFAULT 0,               -- 기관 순매수
    individual_net BIGINT DEFAULT 0,                -- 개인 순매수

    -- 보유 비율 (%)
    foreigner_holding_rate DECIMAL(5,2),            -- 외국인 보유비율

    -- 기타
    pension_net BIGINT DEFAULT 0,                   -- 연기금 순매수

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(stock_code, date)
);

CREATE INDEX idx_supply_demand_code_date ON stock_supply_demand(stock_code, date DESC);

COMMENT ON TABLE stock_supply_demand IS '수급 데이터 (pykrx 수집)';
COMMENT ON COLUMN stock_supply_demand.foreigner_net IS '외국인 순매수 금액 (원)';


-- ============================================================
-- Group 3: Trading Tables (매매 기록)
-- ============================================================

-- 7. trade_history: 매매 내역 + AI 판단 근거
CREATE TABLE IF NOT EXISTS trade_history (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL REFERENCES stocks(stock_code),
    stock_name VARCHAR(100),

    -- 거래 정보
    trade_type VARCHAR(4) NOT NULL,                 -- BUY/SELL
    trade_date TIMESTAMP NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    total_amount DECIMAL(15,2) GENERATED ALWAYS AS (quantity * price) STORED,
    fee DECIMAL(10,2) DEFAULT 0,                    -- 수수료
    tax DECIMAL(10,2) DEFAULT 0,                    -- 세금

    -- AI 판단 근거
    recommendation_id INTEGER,                      -- recommendation_history FK (나중에 추가)
    total_score DECIMAL(5,2),                       -- AI 총점 (0-100)
    gemini_reasoning TEXT,                          -- Gemini AI 판단 근거

    -- 상태
    status VARCHAR(20) DEFAULT 'executed',          -- executed/pending/cancelled
    order_type VARCHAR(20),                         -- market/limit/stop

    -- 메타
    created_by VARCHAR(50) DEFAULT 'user',          -- user/ai/auto
    note TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trade_history_code ON trade_history(stock_code);
CREATE INDEX idx_trade_history_date ON trade_history(trade_date DESC);
CREATE INDEX idx_trade_history_type ON trade_history(trade_type);

COMMENT ON TABLE trade_history IS '매매 내역 + AI 판단 근거';
COMMENT ON COLUMN trade_history.gemini_reasoning IS 'Gemini AI가 생성한 매매 근거 (200자)';


-- 8. stock_opinions: 투자 의견 및 목표가
CREATE TABLE IF NOT EXISTS stock_opinions (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL REFERENCES stocks(stock_code),
    stock_name VARCHAR(100),
    opinion_date DATE NOT NULL,

    -- 투자 의견
    opinion VARCHAR(10) NOT NULL,                   -- buy/hold/sell
    target_price DECIMAL(10,2),                     -- 목표가
    current_price DECIMAL(10,2),                    -- 현재가
    expected_return DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE
            WHEN current_price > 0 THEN ((target_price - current_price) / current_price * 100)
            ELSE 0
        END
    ) STORED,

    -- 출처
    source VARCHAR(100),                            -- 예: '삼성증권', 'NH투자증권'
    analyst_name VARCHAR(50),

    -- 상세
    summary TEXT,
    reasoning TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stock_opinions_code ON stock_opinions(stock_code);
CREATE INDEX idx_stock_opinions_date ON stock_opinions(opinion_date DESC);

COMMENT ON TABLE stock_opinions IS '증권사 리포트 (투자 의견 및 목표가)';


-- ============================================================
-- Group 4: AI Recommendation Tables (AI 추천 및 검증)
-- ============================================================

-- 9. data_sources: 데이터 소스 신뢰도 추적
CREATE TABLE IF NOT EXISTS data_sources (
    source_id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) UNIQUE NOT NULL,       -- 예: '삼성증권_리포트', 'Gemini_뉴스'
    source_type VARCHAR(20) NOT NULL,               -- nps/realtime/report/technical/theme/ai

    -- 신뢰도 점수
    reliability_score DECIMAL(3,2) DEFAULT 0.50,    -- 0.0 ~ 1.0 (초기값 0.5)

    -- 통계
    total_recommendations INTEGER DEFAULT 0,        -- 총 추천 수
    correct_predictions INTEGER DEFAULT 0,          -- 적중 수
    accuracy_rate DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE
            WHEN total_recommendations > 0 THEN (correct_predictions::DECIMAL / total_recommendations * 100)
            ELSE 0
        END
    ) STORED,
    average_error_rate DECIMAL(10,2) DEFAULT 0,     -- 평균 오차율 (%)

    -- 메타
    is_active BOOLEAN DEFAULT TRUE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_data_sources_type ON data_sources(source_type);
CREATE INDEX idx_data_sources_reliability ON data_sources(reliability_score DESC);

COMMENT ON TABLE data_sources IS '데이터 소스 신뢰도 추적 (학습 시스템 핵심)';
COMMENT ON COLUMN data_sources.reliability_score IS '신뢰도 (0.0~1.0), 검증 후 동적 조정';


-- 10. recommendation_history: AI/전문가 추천 기록
CREATE TABLE IF NOT EXISTS recommendation_history (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL REFERENCES stocks(stock_code),
    stock_name VARCHAR(100),
    recommendation_date DATE NOT NULL,

    -- 추천 내용
    recommended_price DECIMAL(10,2) NOT NULL,       -- 추천 당시 가격
    recommendation_type VARCHAR(10) NOT NULL,       -- buy/hold/sell
    target_price DECIMAL(10,2),                     -- 목표가

    -- AI 점수 (0-100)
    total_score DECIMAL(5,2),
    price_score DECIMAL(5,2),
    volume_score DECIMAL(5,2),
    supply_score DECIMAL(5,2),
    chart_score DECIMAL(5,2),
    news_score DECIMAL(5,2),
    analyst_score DECIMAL(5,2),

    -- 출처
    source_id INTEGER REFERENCES data_sources(source_id),
    gemini_reasoning TEXT,                          -- Gemini AI 최종 판단

    -- 메타
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_recommendation_history_code ON recommendation_history(stock_code);
CREATE INDEX idx_recommendation_history_date ON recommendation_history(recommendation_date DESC);
CREATE INDEX idx_recommendation_history_source ON recommendation_history(source_id);

COMMENT ON TABLE recommendation_history IS 'AI/전문가 추천 기록 (역추적 검증용)';
COMMENT ON COLUMN recommendation_history.gemini_reasoning IS 'Gemini Pro 최종 판단 (200자)';


-- 11. verification_results: 추천 정확도 검증 (7일 후)
CREATE TABLE IF NOT EXISTS verification_results (
    id SERIAL PRIMARY KEY,
    recommendation_id INTEGER NOT NULL REFERENCES recommendation_history(id),
    verification_date DATE NOT NULL,                -- 검증 날짜 (추천일 + 7일)

    -- 실제 결과
    actual_price DECIMAL(10,2) NOT NULL,            -- 7일 후 실제 가격
    price_change_rate DECIMAL(5,2) NOT NULL,        -- 실제 변동률 (%)

    -- 정확도 평가
    prediction_correct BOOLEAN,                     -- 5% 이상 상승했는지
    error_rate DECIMAL(10,2),                       -- 오차율 (목표가 대비)

    -- 메타
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_verification_results_rec_id ON verification_results(recommendation_id);
CREATE INDEX idx_verification_results_date ON verification_results(verification_date DESC);

COMMENT ON TABLE verification_results IS '추천 정확도 검증 (7일 후 역추적)';
COMMENT ON COLUMN verification_results.prediction_correct IS '5% 이상 상승 여부 (매수 추천 기준)';


-- ============================================================
-- Group 5: Scoring Tables (점수 및 가중치)
-- ============================================================

-- 12. stock_score_weights: 종목별 가중치 (동적 조정)
CREATE TABLE IF NOT EXISTS stock_score_weights (
    stock_code VARCHAR(6) PRIMARY KEY REFERENCES stocks(stock_code),

    -- 기본 가중치 (합계 100%)
    price_weight DECIMAL(5,2) DEFAULT 20.0,         -- 가격 가중치
    volume_weight DECIMAL(5,2) DEFAULT 15.0,        -- 거래량 가중치
    supply_weight DECIMAL(5,2) DEFAULT 30.0,        -- 수급 가중치
    chart_weight DECIMAL(5,2) DEFAULT 35.0,         -- 차트 가중치

    -- 확장 가중치 (개별 소스별 신뢰도 승수, 0.0~2.0)
    news_weight DECIMAL(5,2) DEFAULT 1.0,           -- 뉴스 영향력
    analyst_weight DECIMAL(5,2) DEFAULT 1.0,        -- 애널리스트 영향력

    -- 학습 메타 정보
    accuracy_score DECIMAL(5,2) DEFAULT 50.0,       -- 전체 예측 정확도 (0-100)
    sample_count INTEGER DEFAULT 0,                 -- 학습 샘플 수

    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 가중치 합계 체크 (100%)
    CONSTRAINT chk_weights_sum CHECK (
        price_weight + volume_weight + supply_weight + chart_weight = 100.0
    )
);

COMMENT ON TABLE stock_score_weights IS '종목별 가중치 (학습으로 동적 조정)';
COMMENT ON COLUMN stock_score_weights.price_weight IS '가격 가중치 (%), 합계 100%';


-- 13. stock_score_history: 일별 점수 기록
CREATE TABLE IF NOT EXISTS stock_score_history (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL REFERENCES stocks(stock_code),
    date DATE NOT NULL,

    -- 점수 (0-100)
    total_score DECIMAL(5,2) NOT NULL,
    price_score DECIMAL(5,2),
    volume_score DECIMAL(5,2),
    supply_score DECIMAL(5,2),
    chart_score DECIMAL(5,2),
    news_score DECIMAL(5,2),
    analyst_score DECIMAL(5,2),

    -- 신호
    signal VARCHAR(20),                             -- 강력매수/분할매수/관망/매도

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(stock_code, date)
);

CREATE INDEX idx_stock_score_history_code_date ON stock_score_history(stock_code, date DESC);
CREATE INDEX idx_stock_score_history_signal ON stock_score_history(signal);

COMMENT ON TABLE stock_score_history IS '일별 종목 점수 기록 (추이 분석용)';


-- ============================================================
-- Triggers: Auto-update timestamps
-- ============================================================

-- Function: Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables with updated_at
CREATE TRIGGER update_stocks_updated_at BEFORE UPDATE ON stocks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stock_assets_updated_at BEFORE UPDATE ON stock_assets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stock_score_weights_updated_at BEFORE UPDATE ON stock_score_weights
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================
-- Triggers: Auto-update stock_assets.current_price from min_ticks
-- ============================================================

CREATE OR REPLACE FUNCTION update_stock_assets_price()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE stock_assets
    SET current_price = NEW.price,
        updated_at = CURRENT_TIMESTAMP
    WHERE stock_code = NEW.stock_code;

    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_update_stock_assets_price
    AFTER INSERT ON min_ticks
    FOR EACH ROW
    EXECUTE FUNCTION update_stock_assets_price();

COMMENT ON FUNCTION update_stock_assets_price IS 'min_ticks 데이터 삽입 시 stock_assets.current_price 자동 업데이트';


-- ============================================================
-- Views: Useful aggregations
-- ============================================================

-- View: 보유 종목 현황 (수익률 포함)
CREATE OR REPLACE VIEW v_holdings_summary AS
SELECT
    sa.stock_code,
    sa.stock_name,
    sa.quantity,
    sa.avg_buy_price,
    sa.current_price,
    sa.total_value,
    sa.total_cost,
    sa.profit_loss,
    sa.profit_loss_rate,
    s.market,
    s.sector
FROM stock_assets sa
JOIN stocks s ON sa.stock_code = s.stock_code
WHERE sa.quantity > 0
ORDER BY sa.profit_loss_rate DESC;

COMMENT ON VIEW v_holdings_summary IS '보유 종목 현황 (수익률 높은 순)';


-- View: 데이터 소스 정확도 순위
CREATE OR REPLACE VIEW v_data_sources_ranking AS
SELECT
    source_id,
    source_name,
    source_type,
    reliability_score,
    accuracy_rate,
    total_recommendations,
    correct_predictions
FROM data_sources
WHERE is_active = TRUE
ORDER BY reliability_score DESC, accuracy_rate DESC;

COMMENT ON VIEW v_data_sources_ranking IS '데이터 소스 신뢰도 순위';


-- ============================================================
-- Initial Data: data_sources 기본 소스 등록
-- ============================================================

INSERT INTO data_sources (source_name, source_type, reliability_score) VALUES
-- Technical indicators (기술적 지표)
('가격_이평선', 'technical', 0.70),
('거래량_분석', 'technical', 0.60),
('RSI_MACD', 'technical', 0.80),
('볼린저밴드', 'technical', 0.75),

-- Real-time supply/demand (실시간 수급)
('외국인_수급', 'realtime', 0.85),
('기관_수급', 'realtime', 0.75),
('연기금_수급', 'nps', 0.90),

-- Analyst reports (증권사 리포트)
('삼성증권_리포트', 'report', 0.65),
('미래에셋_리포트', 'report', 0.70),
('NH투자증권_리포트', 'report', 0.68),
('키움증권_리포트', 'report', 0.66),

-- AI analysis (AI 분석)
('Gemini_뉴스_감성분석', 'ai', 0.50),
('Gemini_최종판단', 'ai', 0.55),

-- Theme/Trend (테마/트렌드)
('테마_분석', 'theme', 0.45)

ON CONFLICT (source_name) DO NOTHING;


-- ============================================================
-- Performance Optimization
-- ============================================================

-- Analyze tables for query optimization
ANALYZE stocks;
ANALYZE stock_assets;
ANALYZE daily_ohlcv;
ANALYZE data_sources;


-- ============================================================
-- Permissions (Optional, for multi-user setup)
-- ============================================================

-- Grant permissions to wonny user (if needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO wonny;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO wonny;


-- ============================================================
-- Success Message
-- ============================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Database schema created successfully!';
    RAISE NOTICE '📊 Tables created: 13';
    RAISE NOTICE '🔍 Views created: 2';
    RAISE NOTICE '⚡ Triggers created: 4';
    RAISE NOTICE '📝 Initial data_sources: 14';
END $$;
