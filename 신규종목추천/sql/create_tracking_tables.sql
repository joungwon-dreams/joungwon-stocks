-- 신규종목추천 성과 추적 테이블 생성
-- 실행: psql -U wonny -d stock_investment_db -f 신규종목추천/sql/create_tracking_tables.sql

-- 1. 일일 주가 추적 테이블
CREATE TABLE IF NOT EXISTS smart_price_tracking (
    id SERIAL PRIMARY KEY,
    recommendation_id INTEGER REFERENCES smart_recommendations(id),
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100),
    rec_date DATE NOT NULL,
    rec_price INTEGER NOT NULL,
    rec_grade CHAR(1),
    track_date DATE NOT NULL,
    track_price INTEGER NOT NULL,
    return_rate NUMERIC(8,2),      -- 수익률 (%)
    days_held INTEGER,             -- 경과일
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(recommendation_id, track_date)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_price_tracking_stock ON smart_price_tracking(stock_code);
CREATE INDEX IF NOT EXISTS idx_price_tracking_date ON smart_price_tracking(track_date);
CREATE INDEX IF NOT EXISTS idx_price_tracking_rec_id ON smart_price_tracking(recommendation_id);
CREATE INDEX IF NOT EXISTS idx_price_tracking_rec_date ON smart_price_tracking(rec_date);

COMMENT ON TABLE smart_price_tracking IS '일일 주가 추적 기록';
COMMENT ON COLUMN smart_price_tracking.return_rate IS '추천가 대비 현재가 수익률 (%)';
COMMENT ON COLUMN smart_price_tracking.days_held IS '추천일 이후 경과일';

-- 2. 기간별 성과 추적 테이블 (7/14/30일)
CREATE TABLE IF NOT EXISTS smart_performance (
    id SERIAL PRIMARY KEY,
    recommendation_id INTEGER REFERENCES smart_recommendations(id),
    stock_code VARCHAR(10) NOT NULL,
    rec_date DATE NOT NULL,
    rec_price INTEGER NOT NULL,
    rec_grade CHAR(1),
    rec_score NUMERIC(6,2),
    check_date DATE NOT NULL,
    check_price INTEGER NOT NULL,
    return_rate NUMERIC(8,2),      -- 수익률 (%)
    max_profit NUMERIC(8,2),       -- 기간 중 최대 수익
    max_drawdown NUMERIC(8,2),     -- 기간 중 최대 손실
    status VARCHAR(20),            -- success/active/warning/failed
    days_held INTEGER,             -- 보유 일수 (7, 14, 30)
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_performance_stock ON smart_performance(stock_code);
CREATE INDEX IF NOT EXISTS idx_performance_days ON smart_performance(days_held);
CREATE INDEX IF NOT EXISTS idx_performance_status ON smart_performance(status);
CREATE INDEX IF NOT EXISTS idx_performance_rec_id ON smart_performance(recommendation_id);

COMMENT ON TABLE smart_performance IS '기간별 성과 추적 (7/14/30일)';
COMMENT ON COLUMN smart_performance.status IS '상태: success(+10%↑), active(0%↑), warning(-5%↑), failed(-5%↓)';

-- 3. AI 회고 분석 테이블
CREATE TABLE IF NOT EXISTS smart_ai_retrospective (
    id SERIAL PRIMARY KEY,
    performance_id INTEGER REFERENCES smart_performance(id),
    recommendation_id INTEGER REFERENCES smart_recommendations(id),
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100),
    rec_date DATE NOT NULL,
    rec_grade CHAR(1),
    rec_score NUMERIC(6,2),

    -- 추천 당시 AI 분석 결과
    original_key_material TEXT,    -- 당시 핵심 재료
    original_risk_factor TEXT,     -- 당시 리스크 요인
    original_buy_point TEXT,       -- 당시 매수 포인트

    -- 실제 성과
    actual_return NUMERIC(8,2),    -- 실제 수익률
    max_drawdown NUMERIC(8,2),     -- 최대 손실률
    days_held INTEGER,             -- 보유 일수

    -- AI 회고 분석 결과
    missed_risks TEXT,             -- 놓친 리스크
    actual_cause TEXT,             -- 실제 하락 원인
    lesson_learned TEXT,           -- 학습된 교훈
    improvement_suggestion TEXT,   -- 개선 제안
    confidence_adjustment NUMERIC(4,2),  -- 신뢰도 조정 (-10 ~ +10)

    -- 메타데이터
    ai_raw_response JSONB,         -- AI 원본 응답
    analyzed_at TIMESTAMP DEFAULT NOW(),
    model_used VARCHAR(50) DEFAULT 'gemini-2.0-flash'
);

CREATE INDEX IF NOT EXISTS idx_retrospective_stock ON smart_ai_retrospective(stock_code);
CREATE INDEX IF NOT EXISTS idx_retrospective_grade ON smart_ai_retrospective(rec_grade);
CREATE INDEX IF NOT EXISTS idx_retrospective_return ON smart_ai_retrospective(actual_return);

COMMENT ON TABLE smart_ai_retrospective IS 'AI 회고 분석 결과 (실패 종목 원인 분석)';
COMMENT ON COLUMN smart_ai_retrospective.missed_risks IS 'AI가 추천 당시 놓친 리스크 요인';
COMMENT ON COLUMN smart_ai_retrospective.actual_cause IS '주가 하락의 실제 원인';
COMMENT ON COLUMN smart_ai_retrospective.lesson_learned IS '이 실패에서 배운 교훈';
COMMENT ON COLUMN smart_ai_retrospective.improvement_suggestion IS '향후 분석 개선 제안';
COMMENT ON COLUMN smart_ai_retrospective.confidence_adjustment IS '해당 패턴에 대한 신뢰도 조정 (-10 ~ +10)';

-- 4. 학습 교훈 집계 뷰
CREATE OR REPLACE VIEW v_learning_summary AS
SELECT
    rec_grade,
    COUNT(*) as total_failed,
    AVG(actual_return) as avg_loss,
    AVG(confidence_adjustment) as avg_confidence_adj,
    string_agg(DISTINCT missed_risks, ' | ') as common_missed_risks
FROM smart_ai_retrospective
WHERE actual_return < -5
GROUP BY rec_grade
ORDER BY rec_grade;

COMMENT ON VIEW v_learning_summary IS '등급별 학습 교훈 요약';

-- 5. 성과 요약 뷰
CREATE OR REPLACE VIEW v_performance_summary AS
SELECT
    sr.ai_grade,
    sp.days_held,
    COUNT(*) as total,
    AVG(sp.return_rate) as avg_return,
    MIN(sp.return_rate) as min_return,
    MAX(sp.return_rate) as max_return,
    COUNT(CASE WHEN sp.return_rate > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate,
    COUNT(CASE WHEN sp.status = 'success' THEN 1 END) as success_count,
    COUNT(CASE WHEN sp.status = 'failed' THEN 1 END) as failed_count
FROM smart_performance sp
JOIN smart_recommendations sr ON sp.recommendation_id = sr.id
GROUP BY sr.ai_grade, sp.days_held
ORDER BY sr.ai_grade, sp.days_held;

COMMENT ON VIEW v_performance_summary IS '등급별/기간별 성과 요약';

-- 6. 권한 설정 (필요시)
-- GRANT SELECT, INSERT, UPDATE ON smart_price_tracking TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE ON smart_performance TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE ON smart_ai_retrospective TO your_app_user;
-- GRANT SELECT ON v_learning_summary TO your_app_user;
-- GRANT SELECT ON v_performance_summary TO your_app_user;

-- 완료 메시지
DO $$
BEGIN
    RAISE NOTICE '✅ 성과 추적 테이블 생성 완료';
    RAISE NOTICE '  - smart_price_tracking: 일일 주가 추적';
    RAISE NOTICE '  - smart_performance: 기간별 성과 추적 (7/14/30일)';
    RAISE NOTICE '  - smart_ai_retrospective: AI 회고 분석';
    RAISE NOTICE '  - v_learning_summary: 학습 교훈 뷰';
    RAISE NOTICE '  - v_performance_summary: 성과 요약 뷰';
END $$;
