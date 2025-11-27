-- smart_feedback 테이블: AI 회고 결과 저장
-- 실패한 추천에 대해 AI가 분석한 "놓친 리스크", "교훈" 등을 저장

CREATE TABLE IF NOT EXISTS smart_feedback (
    id SERIAL PRIMARY KEY,

    -- 연결 정보
    performance_id INTEGER REFERENCES smart_performance(id),
    recommendation_id INTEGER REFERENCES smart_recommendations(id),
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100),

    -- 추천 당시 정보
    rec_date DATE NOT NULL,
    rec_grade CHAR(1),
    rec_score NUMERIC(6,2),
    original_key_material TEXT,
    original_risk_factor TEXT,

    -- 실제 결과
    actual_return NUMERIC(8,2),
    max_drawdown NUMERIC(8,2),
    days_held INTEGER,

    -- AI 회고 분석 결과
    missed_risks TEXT,            -- 놓친 리스크 요인
    actual_cause TEXT,            -- 실제 하락 원인
    lesson_learned TEXT,          -- 학습된 교훈
    improvement_suggestion TEXT,  -- 향후 개선 제안
    confidence_adjustment NUMERIC(4,2),  -- 신뢰도 조정 제안 (-10 ~ +10)

    -- AI 원본 응답
    ai_raw_response JSONB,

    -- 메타데이터
    analyzed_at TIMESTAMP DEFAULT NOW(),
    model_used VARCHAR(50) DEFAULT 'gemini-2.0-flash',

    -- 유니크 제약
    CONSTRAINT unique_feedback_per_performance UNIQUE (performance_id)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_feedback_stock ON smart_feedback(stock_code);
CREATE INDEX IF NOT EXISTS idx_feedback_date ON smart_feedback(rec_date DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_grade ON smart_feedback(rec_grade);
CREATE INDEX IF NOT EXISTS idx_feedback_return ON smart_feedback(actual_return);

COMMENT ON TABLE smart_feedback IS 'AI 회고 분석 결과 - 실패한 추천에서 학습';
COMMENT ON COLUMN smart_feedback.missed_risks IS '당시 분석에서 놓친 리스크 요인';
COMMENT ON COLUMN smart_feedback.actual_cause IS '실제 주가 하락의 원인';
COMMENT ON COLUMN smart_feedback.lesson_learned IS 'AI가 학습한 교훈';
COMMENT ON COLUMN smart_feedback.improvement_suggestion IS '향후 분석 개선 제안';
COMMENT ON COLUMN smart_feedback.confidence_adjustment IS '해당 패턴에 대한 신뢰도 조정치 (-10 ~ +10)';
