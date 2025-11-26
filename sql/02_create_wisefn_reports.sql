-- WISEfn Analyst Reports Table
-- 증권사 애널리스트 리포트 (WISEfn 출처)

CREATE TABLE IF NOT EXISTS wisefn_analyst_reports (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    report_date DATE NOT NULL,  -- 리포트 발행일
    brokerage VARCHAR(50) NOT NULL,  -- 증권사 (유진, KB, 교보, iM, 대신, 메리츠 등)
    target_price INTEGER NOT NULL,  -- 목표주가
    price_change VARCHAR(20),  -- 아진대비 (0, ▲ 15,000, ▼ 5,000, -)
    opinion VARCHAR(20) NOT NULL,  -- 투자의견 (매수, 보유, 매도)
    title TEXT,  -- 리포트 제목

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE(stock_code, report_date, brokerage)  -- 종목별, 날짜별, 증권사별 유니크
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_wisefn_stock_code ON wisefn_analyst_reports(stock_code);
CREATE INDEX IF NOT EXISTS idx_wisefn_report_date ON wisefn_analyst_reports(report_date DESC);
CREATE INDEX IF NOT EXISTS idx_wisefn_stock_date ON wisefn_analyst_reports(stock_code, report_date DESC);

-- Comments
COMMENT ON TABLE wisefn_analyst_reports IS 'WISEfn 증권사 애널리스트 리포트 (Daum Finance 종목리포트 출처)';
COMMENT ON COLUMN wisefn_analyst_reports.stock_code IS '종목코드 (예: 015760)';
COMMENT ON COLUMN wisefn_analyst_reports.report_date IS '리포트 발행일';
COMMENT ON COLUMN wisefn_analyst_reports.brokerage IS '증권사 이름';
COMMENT ON COLUMN wisefn_analyst_reports.target_price IS '목표주가 (원)';
COMMENT ON COLUMN wisefn_analyst_reports.price_change IS '이전 대비 변화 (0, ▲ 15,000 등)';
COMMENT ON COLUMN wisefn_analyst_reports.opinion IS '투자의견 (매수/보유/매도)';
COMMENT ON COLUMN wisefn_analyst_reports.title IS '리포트 제목';
