-- 데이터 캐싱 테이블 생성
-- 목적: API 호출 최소화 및 리포트 생성 속도 향상
-- 생성일: 2025-11-25 11:24:02

-- 재무 지표 캐시 테이블
CREATE TABLE IF NOT EXISTS stock_fundamentals (
    stock_code VARCHAR(10) PRIMARY KEY,
    -- 시세 정보
    current_price INTEGER,
    change_rate NUMERIC(10, 2),
    change_price INTEGER,
    open_price INTEGER,
    high_price INTEGER,
    low_price INTEGER,
    acc_trade_volume BIGINT,
    acc_trade_price BIGINT,
    -- 52주 고저
    week52_high INTEGER,
    week52_low INTEGER,
    -- 시가총액 및 외국인
    market_cap BIGINT,
    foreign_ratio NUMERIC(10, 2),
    -- 재무 지표
    per NUMERIC(10, 2),
    pbr NUMERIC(10, 2),
    eps INTEGER,
    roe NUMERIC(10, 2),
    bps INTEGER,
    -- 메타데이터
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stock_fundamentals_updated ON stock_fundamentals(updated_at);

COMMENT ON TABLE stock_fundamentals IS '종목별 재무지표 캐시 (일 1회 업데이트)';
COMMENT ON COLUMN stock_fundamentals.current_price IS '현재가 (원)';
COMMENT ON COLUMN stock_fundamentals.per IS '주가수익비율';
COMMENT ON COLUMN stock_fundamentals.pbr IS '주가순자산비율';
COMMENT ON COLUMN stock_fundamentals.eps IS '주당순이익 (원)';
COMMENT ON COLUMN stock_fundamentals.roe IS '자기자본이익률 (%)';
COMMENT ON COLUMN stock_fundamentals.bps IS '주당순자산 (원)';

-- 컨센서스 캐시 테이블
CREATE TABLE IF NOT EXISTS stock_consensus (
    stock_code VARCHAR(10) PRIMARY KEY,
    target_price INTEGER,
    opinion VARCHAR(20),
    analyst_count INTEGER,
    buy_count INTEGER,
    hold_count INTEGER,
    sell_count INTEGER,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stock_consensus_updated ON stock_consensus(updated_at);

COMMENT ON TABLE stock_consensus IS '증권사 컨센서스 캐시 (일 1회 업데이트)';
COMMENT ON COLUMN stock_consensus.target_price IS '평균 목표가 (원)';
COMMENT ON COLUMN stock_consensus.opinion IS '투자의견 (매수/중립/매도)';

-- 동종업종 비교 캐시 테이블
CREATE TABLE IF NOT EXISTS stock_peers (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    peer_code VARCHAR(10) NOT NULL,
    peer_name VARCHAR(100) NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE,
    UNIQUE(stock_code, peer_code)
);

CREATE INDEX IF NOT EXISTS idx_stock_peers_code ON stock_peers(stock_code);

COMMENT ON TABLE stock_peers IS '동종업종 비교 종목 캐시 (주 1회 업데이트)';

-- 투자자 매매동향 캐시 테이블
CREATE TABLE IF NOT EXISTS investor_trends (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    individual BIGINT,
    "foreign" BIGINT,
    institutional BIGINT,
    collected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE,
    UNIQUE(stock_code, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_investor_trends_code_date ON investor_trends(stock_code, trade_date DESC);

COMMENT ON TABLE investor_trends IS '투자자별 순매수 동향 (일 1회 업데이트, 최근 10일)';
COMMENT ON COLUMN investor_trends.individual IS '개인 순매수 (주)';
COMMENT ON COLUMN investor_trends."foreign" IS '외국인 순매수 (주)';
COMMENT ON COLUMN investor_trends.institutional IS '기관 순매수 (주)';
