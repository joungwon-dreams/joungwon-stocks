-- =====================================================
-- Phase 8: Daily Performance Summary Table
-- Created: 2025-11-29
-- Purpose: Store daily trading performance metrics
-- =====================================================

-- 일일 성과 요약 테이블
CREATE TABLE IF NOT EXISTS daily_summary (
    date DATE PRIMARY KEY,

    -- 자산 현황
    total_asset NUMERIC(15,2) DEFAULT 0,           -- 총 자산 (현금 + 평가금액)
    cash_balance NUMERIC(15,2) DEFAULT 0,          -- 현금 잔고
    stock_value NUMERIC(15,2) DEFAULT 0,           -- 주식 평가금액

    -- 손익
    realized_pnl NUMERIC(15,2) DEFAULT 0,          -- 실현 손익 (당일)
    unrealized_pnl NUMERIC(15,2) DEFAULT 0,        -- 미실현 손익 (평가손익)
    daily_pnl NUMERIC(15,2) DEFAULT 0,             -- 일일 총 손익 (전일 대비)
    daily_pnl_rate NUMERIC(6,3) DEFAULT 0,         -- 일일 수익률 (%)

    -- 누적 손익
    cumulative_realized_pnl NUMERIC(15,2) DEFAULT 0,   -- 누적 실현 손익
    cumulative_pnl_rate NUMERIC(8,4) DEFAULT 0,        -- 누적 수익률 (%)

    -- 매매 통계
    trade_count INTEGER DEFAULT 0,                 -- 당일 매매 건수
    buy_count INTEGER DEFAULT 0,                   -- 매수 건수
    sell_count INTEGER DEFAULT 0,                  -- 매도 건수
    buy_amount NUMERIC(15,2) DEFAULT 0,            -- 매수 금액
    sell_amount NUMERIC(15,2) DEFAULT 0,           -- 매도 금액

    -- 승률
    win_trades INTEGER DEFAULT 0,                  -- 익절 건수
    lose_trades INTEGER DEFAULT 0,                 -- 손절 건수
    win_rate NUMERIC(5,2) DEFAULT 0,               -- 승률 (%)

    -- AEGIS 신호 성과
    aegis_signal_count INTEGER DEFAULT 0,          -- 당일 발생 신호 수
    aegis_accuracy NUMERIC(5,2) DEFAULT 0,         -- 신호 적중률 (%)

    -- 시장 지표
    kospi_close NUMERIC(10,2),                     -- KOSPI 종가
    kospi_change_rate NUMERIC(6,3),                -- KOSPI 등락률
    kosdaq_close NUMERIC(10,2),                    -- KOSDAQ 종가
    kosdaq_change_rate NUMERIC(6,3),               -- KOSDAQ 등락률

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT                                     -- 특이사항 메모
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_daily_summary_month
ON daily_summary (date_trunc('month', date));

CREATE INDEX IF NOT EXISTS idx_daily_summary_year
ON daily_summary (date_trunc('year', date));

-- 코멘트
COMMENT ON TABLE daily_summary IS 'Phase 8: 일일 매매 성과 요약 테이블';
COMMENT ON COLUMN daily_summary.total_asset IS '총 자산 (현금 + 주식 평가금액)';
COMMENT ON COLUMN daily_summary.realized_pnl IS '당일 실현 손익';
COMMENT ON COLUMN daily_summary.unrealized_pnl IS '미실현 손익 (평가손익)';
COMMENT ON COLUMN daily_summary.daily_pnl IS '전일 대비 총 손익';
COMMENT ON COLUMN daily_summary.win_rate IS '당일 매매 승률 (%)';
COMMENT ON COLUMN daily_summary.aegis_accuracy IS 'AEGIS 신호 적중률 (%)';


-- =====================================================
-- 일별 종목별 성과 테이블 (상세)
-- =====================================================
CREATE TABLE IF NOT EXISTS daily_stock_performance (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    stock_code VARCHAR(6) NOT NULL,
    stock_name VARCHAR(100),

    -- 포지션
    start_quantity INTEGER DEFAULT 0,              -- 장 시작 보유량
    end_quantity INTEGER DEFAULT 0,                -- 장 마감 보유량

    -- 가격
    open_price NUMERIC(10,2),                      -- 시가
    close_price NUMERIC(10,2),                     -- 종가
    high_price NUMERIC(10,2),                      -- 고가
    low_price NUMERIC(10,2),                       -- 저가
    change_rate NUMERIC(6,3),                      -- 등락률 (%)

    -- 매매 내역
    buy_quantity INTEGER DEFAULT 0,                -- 매수 수량
    buy_amount NUMERIC(15,2) DEFAULT 0,            -- 매수 금액
    sell_quantity INTEGER DEFAULT 0,               -- 매도 수량
    sell_amount NUMERIC(15,2) DEFAULT 0,           -- 매도 금액

    -- 손익
    realized_pnl NUMERIC(15,2) DEFAULT 0,          -- 실현 손익
    unrealized_pnl NUMERIC(15,2) DEFAULT 0,        -- 미실현 손익

    -- AEGIS 신호
    aegis_signal VARCHAR(20),                      -- 당일 최종 신호
    aegis_score INTEGER,                           -- 신호 점수

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_daily_stock_perf UNIQUE (date, stock_code)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_daily_stock_perf_date
ON daily_stock_performance (date DESC);

CREATE INDEX IF NOT EXISTS idx_daily_stock_perf_stock
ON daily_stock_performance (stock_code, date DESC);

COMMENT ON TABLE daily_stock_performance IS 'Phase 8: 일별 종목별 성과 상세';


-- =====================================================
-- 완료 메시지
-- =====================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Phase 8: Daily performance tables created';
    RAISE NOTICE '   - daily_summary: 일일 성과 요약';
    RAISE NOTICE '   - daily_stock_performance: 종목별 상세 성과';
END $$;
