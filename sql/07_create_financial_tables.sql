-- 재무제표 및 상세 컨센서스 테이블 생성
-- 생성일: 2025-11-25 11:24:02

-- 재무제표 캐시 테이블 (연간/분기별)
CREATE TABLE IF NOT EXISTS stock_financials (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    period_type VARCHAR(10) NOT NULL, -- 'annual' or 'quarter'
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER, -- 1,2,3,4 (분기일 경우)
    -- 손익계산서
    revenue BIGINT, -- 매출액
    operating_profit BIGINT, -- 영업이익
    net_profit BIGINT, -- 당기순이익
    operating_margin NUMERIC(10, 2), -- 영업이익률 (%)
    net_margin NUMERIC(10, 2), -- 순이익률 (%)
    -- 재무상태표
    total_assets BIGINT, -- 총자산
    total_liabilities BIGINT, -- 총부채
    total_equity BIGINT, -- 자본총계
    debt_ratio NUMERIC(10, 2), -- 부채비율 (%)
    -- 현금흐름표
    operating_cashflow BIGINT, -- 영업활동현금흐름
    investing_cashflow BIGINT, -- 투자활동현금흐름
    financing_cashflow BIGINT, -- 재무활동현금흐름
    -- 배당
    dividend_per_share INTEGER, -- 주당배당금 (원)
    dividend_yield NUMERIC(10, 2), -- 배당수익률 (%)
    -- 메타데이터
    collected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE,
    UNIQUE(stock_code, period_type, fiscal_year, fiscal_quarter)
);

CREATE INDEX IF NOT EXISTS idx_stock_financials_code_period ON stock_financials(stock_code, fiscal_year DESC, fiscal_quarter DESC);
CREATE INDEX IF NOT EXISTS idx_stock_financials_collected ON stock_financials(collected_at);

COMMENT ON TABLE stock_financials IS '종목별 재무제표 (분기별/연간별)';
COMMENT ON COLUMN stock_financials.period_type IS 'annual: 연간, quarter: 분기';
COMMENT ON COLUMN stock_financials.fiscal_year IS '회계년도 (예: 2024)';
COMMENT ON COLUMN stock_financials.fiscal_quarter IS '분기 (1~4, 연간일 경우 NULL)';
COMMENT ON COLUMN stock_financials.operating_margin IS '영업이익률 = 영업이익/매출액 * 100';
COMMENT ON COLUMN stock_financials.debt_ratio IS '부채비율 = 총부채/자본총계 * 100';

-- 증권사별 상세 컨센서스 테이블
CREATE TABLE IF NOT EXISTS analyst_reports (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    securities_firm VARCHAR(100) NOT NULL, -- 증권사명 (예: 삼성증권)
    analyst_name VARCHAR(100), -- 애널리스트명
    target_price INTEGER, -- 목표주가 (원)
    opinion VARCHAR(20), -- 투자의견 (매수/중립/매도/BUY/HOLD/SELL)
    report_title TEXT, -- 리포트 제목
    report_date DATE NOT NULL, -- 리포트 발행일
    report_url TEXT, -- 리포트 링크 (있을 경우)
    collected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE,
    UNIQUE(stock_code, securities_firm, report_date)
);

CREATE INDEX IF NOT EXISTS idx_analyst_reports_code_date ON analyst_reports(stock_code, report_date DESC);
CREATE INDEX IF NOT EXISTS idx_analyst_reports_firm ON analyst_reports(securities_firm);
CREATE INDEX IF NOT EXISTS idx_analyst_reports_collected ON analyst_reports(collected_at);

COMMENT ON TABLE analyst_reports IS '증권사별 상세 리포트 및 목표가 (일 1회 업데이트)';
COMMENT ON COLUMN analyst_reports.securities_firm IS '증권사명 (삼성증권, KB증권 등)';
COMMENT ON COLUMN analyst_reports.opinion IS '투자의견 (매수/중립/매도/BUY/HOLD/SELL)';
COMMENT ON COLUMN analyst_reports.report_date IS '리포트 발행일자';
