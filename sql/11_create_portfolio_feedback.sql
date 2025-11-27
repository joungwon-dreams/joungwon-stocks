-- Portfolio AI Feedback History Table
-- 보유종목 AI 피드백 이력 테이블
-- 매일 AI 판단을 기록하고 다음날 검증

CREATE TABLE IF NOT EXISTS portfolio_ai_history (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL,
    report_date DATE DEFAULT CURRENT_DATE,

    -- Snapshot (당시 상태)
    my_avg_price DECIMAL(15,2),          -- 내 평단가
    market_price DECIMAL(15,2),          -- 당시 시장가
    return_rate DECIMAL(5,2),            -- 당시 수익률

    -- AI Output (AI 판단)
    recommendation VARCHAR(20),           -- 'BUY_MORE', 'HOLD', 'SELL', 'CUT_LOSS'
    rationale TEXT,                       -- AI 판단 이유
    confidence DECIMAL(3,2),              -- 신뢰도 0.0 ~ 1.0

    -- Verification (다음날 검증)
    is_verified BOOLEAN DEFAULT FALSE,
    next_day_price DECIMAL(15,2),         -- 다음날 종가
    next_day_return DECIMAL(5,2),         -- 다음날 수익률 (당일 대비)
    was_correct BOOLEAN,                   -- 판단 적중 여부

    created_at TIMESTAMP DEFAULT NOW(),
    verified_at TIMESTAMP,

    UNIQUE(stock_code, report_date)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pf_history_code_date ON portfolio_ai_history(stock_code, report_date);
CREATE INDEX IF NOT EXISTS idx_pf_history_unverified ON portfolio_ai_history(is_verified) WHERE is_verified = FALSE;
CREATE INDEX IF NOT EXISTS idx_pf_history_stock ON portfolio_ai_history(stock_code);

COMMENT ON TABLE portfolio_ai_history IS '보유종목 AI 피드백 이력 - 매일 판단/다음날 검증';
COMMENT ON COLUMN portfolio_ai_history.recommendation IS 'BUY_MORE(추가매수), HOLD(관망), SELL(일부매도), CUT_LOSS(손절)';
COMMENT ON COLUMN portfolio_ai_history.confidence IS '신뢰도 0.0 ~ 1.0';
COMMENT ON COLUMN portfolio_ai_history.was_correct IS 'BUY_MORE→상승=TRUE, SELL→하락=TRUE, HOLD→±1%=TRUE';
