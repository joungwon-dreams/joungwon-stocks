-- =====================================================
-- 신규종목추천 시스템 데이터베이스 스키마
-- 기존 테이블과 분리된 독립 테이블
-- =====================================================

-- 1. 추천 이력 테이블 (Phase 3 결과 저장)
CREATE TABLE IF NOT EXISTS smart_recommendations (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100),
    recommendation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    batch_id VARCHAR(36),  -- 실행 배치 식별자 (UUID)

    -- Phase 1A: 기본 정량 데이터
    pbr DECIMAL(8,3),
    per DECIMAL(8,2),
    market_cap BIGINT,
    volume BIGINT,
    close_price INTEGER,

    -- Phase 1B: 기술적 지표
    rsi_14 DECIMAL(6,2),
    disparity_20 DECIMAL(6,2),
    disparity_60 DECIMAL(6,2),
    ma_20 INTEGER,
    ma_60 INTEGER,

    -- 수급 데이터
    pension_net_buy BIGINT DEFAULT 0,
    institution_net_buy BIGINT DEFAULT 0,
    foreign_net_buy BIGINT DEFAULT 0,
    individual_net_buy BIGINT DEFAULT 0,
    net_buy_days INTEGER DEFAULT 0,

    -- Phase 1 점수
    quant_score DECIMAL(6,2),

    -- Phase 2A: 수집 데이터 요약
    news_count INTEGER DEFAULT 0,
    news_sentiment DECIMAL(4,2),  -- -1.0 ~ 1.0
    report_count INTEGER DEFAULT 0,
    avg_target_price INTEGER,
    consensus_buy INTEGER DEFAULT 0,
    consensus_hold INTEGER DEFAULT 0,
    consensus_sell INTEGER DEFAULT 0,

    -- Phase 2B: AI 분석 결과
    ai_grade CHAR(1),  -- S, A, B, C, D
    ai_confidence DECIMAL(4,2),  -- 0.0 ~ 1.0
    ai_key_material TEXT,
    ai_policy_alignment TEXT,
    ai_buy_point TEXT,
    ai_risk_factor TEXT,
    ai_raw_response JSONB,

    -- Phase 3: 최종 점수
    qual_score DECIMAL(6,2),
    final_score DECIMAL(6,2),
    rank_in_batch INTEGER,

    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(stock_code, recommendation_date, batch_id)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_smart_rec_date ON smart_recommendations(recommendation_date DESC);
CREATE INDEX IF NOT EXISTS idx_smart_rec_score ON smart_recommendations(final_score DESC);
CREATE INDEX IF NOT EXISTS idx_smart_rec_grade ON smart_recommendations(ai_grade);
CREATE INDEX IF NOT EXISTS idx_smart_rec_batch ON smart_recommendations(batch_id);

-- 2. Phase 1 후보 캐시 테이블 (필터링 결과 임시 저장)
CREATE TABLE IF NOT EXISTS smart_phase1_candidates (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(36) NOT NULL,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100),

    -- Phase 1A 결과
    pbr DECIMAL(8,3),
    per DECIMAL(8,2),
    market_cap BIGINT,
    volume BIGINT,
    close_price INTEGER,
    phase1a_passed BOOLEAN DEFAULT FALSE,

    -- Phase 1B 결과
    rsi_14 DECIMAL(6,2),
    disparity_20 DECIMAL(6,2),
    disparity_60 DECIMAL(6,2),
    pension_net_buy BIGINT,
    institution_net_buy BIGINT,
    quant_score DECIMAL(6,2),
    phase1b_passed BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(batch_id, stock_code)
);

CREATE INDEX IF NOT EXISTS idx_phase1_batch ON smart_phase1_candidates(batch_id);
CREATE INDEX IF NOT EXISTS idx_phase1_passed ON smart_phase1_candidates(phase1b_passed);

-- 3. 수집 데이터 캐시 테이블 (Phase 2A 결과)
CREATE TABLE IF NOT EXISTS smart_collected_data (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    data_type VARCHAR(20) NOT NULL,  -- 'news', 'report', 'consensus'
    source VARCHAR(50) NOT NULL,      -- 'naver', 'daum', 'fnguide', etc.

    -- 데이터 내용
    title TEXT,
    content TEXT,
    url TEXT,
    sentiment DECIMAL(4,2),
    target_price INTEGER,
    rating VARCHAR(20),
    firm_name VARCHAR(50),

    data_date DATE,
    collected_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '6 hours'),

    -- 원본 JSON
    raw_data JSONB
);

CREATE INDEX IF NOT EXISTS idx_collected_code ON smart_collected_data(stock_code);
CREATE INDEX IF NOT EXISTS idx_collected_type ON smart_collected_data(data_type);
CREATE INDEX IF NOT EXISTS idx_collected_expires ON smart_collected_data(expires_at);

-- 4. 실행 이력 테이블 (배치 실행 기록)
CREATE TABLE IF NOT EXISTS smart_run_history (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(36) UNIQUE NOT NULL,
    run_type VARCHAR(20) NOT NULL,  -- 'full', 'incremental', 'reanalyze'

    -- 실행 통계
    phase1a_input INTEGER,
    phase1a_output INTEGER,
    phase1b_output INTEGER,
    phase2a_collected INTEGER,
    phase2b_analyzed INTEGER,
    phase3_scored INTEGER,

    -- 필터 설정
    filter_config JSONB,

    -- 시간 기록
    started_at TIMESTAMP DEFAULT NOW(),
    phase1_completed_at TIMESTAMP,
    phase2_completed_at TIMESTAMP,
    phase3_completed_at TIMESTAMP,
    finished_at TIMESTAMP,

    -- 상태
    status VARCHAR(20) DEFAULT 'running',  -- running, completed, failed
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_run_history_status ON smart_run_history(status);
CREATE INDEX IF NOT EXISTS idx_run_history_date ON smart_run_history(started_at DESC);

-- 5. 성과 추적 테이블 (Phase 4 피드백용)
CREATE TABLE IF NOT EXISTS smart_performance (
    id SERIAL PRIMARY KEY,
    recommendation_id INTEGER REFERENCES smart_recommendations(id),
    stock_code VARCHAR(10) NOT NULL,

    -- 추천 시점 데이터
    rec_date DATE NOT NULL,
    rec_price INTEGER NOT NULL,
    rec_grade CHAR(1),
    rec_score DECIMAL(6,2),

    -- 성과 체크 데이터
    check_date DATE NOT NULL,
    check_price INTEGER NOT NULL,
    return_rate DECIMAL(8,2),  -- %
    max_profit DECIMAL(8,2),   -- 기간 내 최대 수익률
    max_drawdown DECIMAL(8,2), -- 기간 내 최대 손실률

    -- 상태
    status VARCHAR(20) DEFAULT 'active',  -- active, closed_profit, closed_loss
    days_held INTEGER,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_perf_stock ON smart_performance(stock_code);
CREATE INDEX IF NOT EXISTS idx_perf_status ON smart_performance(status);
CREATE INDEX IF NOT EXISTS idx_perf_rec ON smart_performance(recommendation_id);

-- 6. 피드백 이력 테이블
CREATE TABLE IF NOT EXISTS smart_feedback (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(36),
    stock_code VARCHAR(10),

    feedback_type VARCHAR(30) NOT NULL,  -- 'reanalyze', 'filter_change', 'exclude', 'include'
    feedback_reason TEXT,

    -- 변경 전후
    before_grade CHAR(1),
    after_grade CHAR(1),
    before_score DECIMAL(6,2),
    after_score DECIMAL(6,2),

    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(50) DEFAULT 'user'
);

-- 7. 뷰: 최신 추천 결과
CREATE OR REPLACE VIEW v_latest_recommendations AS
SELECT
    sr.*,
    s.stock_name as name_from_stocks,
    s.sector,
    s.industry
FROM smart_recommendations sr
LEFT JOIN stocks s ON sr.stock_code = s.stock_code
WHERE sr.recommendation_date = (
    SELECT MAX(recommendation_date)
    FROM smart_recommendations
)
ORDER BY sr.final_score DESC;

-- 8. 뷰: 성과 요약
CREATE OR REPLACE VIEW v_performance_summary AS
SELECT
    rec_grade,
    COUNT(*) as total_count,
    AVG(return_rate) as avg_return,
    COUNT(CASE WHEN return_rate > 0 THEN 1 END) as profit_count,
    COUNT(CASE WHEN return_rate <= 0 THEN 1 END) as loss_count,
    ROUND(COUNT(CASE WHEN return_rate > 0 THEN 1 END)::DECIMAL / COUNT(*) * 100, 2) as win_rate
FROM smart_performance
WHERE status != 'active'
GROUP BY rec_grade
ORDER BY rec_grade;

-- 초기화 완료 메시지
DO $$
BEGIN
    RAISE NOTICE '신규종목추천 데이터베이스 스키마 생성 완료';
END $$;
