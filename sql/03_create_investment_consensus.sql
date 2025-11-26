-- Investment Consensus Table
-- 투자의견 컨센서스 (Naver Finance 출처)

CREATE TABLE IF NOT EXISTS investment_consensus (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    data_date DATE NOT NULL,  -- 데이터 기준일

    -- 투자의견 점수
    consensus_score DECIMAL(3,2),  -- 예: 3.95

    -- 애널리스트 수
    buy_count INTEGER DEFAULT 0,  -- 매수
    hold_count INTEGER DEFAULT 0,  -- 보유
    sell_count INTEGER DEFAULT 0,  -- 매도
    strong_buy_count INTEGER DEFAULT 0,  -- 강력매수 (있는 경우)

    -- 컨센서스 상세
    target_price INTEGER,  -- 목표주가 (평균)
    eps INTEGER,  -- EPS (원)
    per DECIMAL(5,2),  -- PER (배)
    analyst_count INTEGER,  -- 참여 애널리스트 수

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE(stock_code, data_date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_consensus_stock_code ON investment_consensus(stock_code);
CREATE INDEX IF NOT EXISTS idx_consensus_data_date ON investment_consensus(data_date DESC);
CREATE INDEX IF NOT EXISTS idx_consensus_stock_date ON investment_consensus(stock_code, data_date DESC);

-- Comments
COMMENT ON TABLE investment_consensus IS '투자의견 컨센서스 (Naver Finance)';
COMMENT ON COLUMN investment_consensus.stock_code IS '종목코드 (예: 015760)';
COMMENT ON COLUMN investment_consensus.data_date IS '데이터 기준일';
COMMENT ON COLUMN investment_consensus.consensus_score IS '투자의견 점수 (1.0=매도 ~ 5.0=매수)';
COMMENT ON COLUMN investment_consensus.target_price IS '목표주가 (원)';
COMMENT ON COLUMN investment_consensus.eps IS 'EPS (원)';
COMMENT ON COLUMN investment_consensus.per IS 'PER (배)';
