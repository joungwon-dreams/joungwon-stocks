--
-- PostgreSQL database dump
--

\restrict CGlJH1BKpZym4mttqdbGvBwDc0A9JLT3akuX5vIIwRrgblBfnbRNPMFf866ZFft

-- Dumped from database version 14.20 (Homebrew)
-- Dumped by pg_dump version 14.20 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: update_analysis_domain_timestamp(); Type: FUNCTION; Schema: public; Owner: wonny
--

CREATE FUNCTION public.update_analysis_domain_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_analysis_domain_timestamp() OWNER TO wonny;

--
-- Name: update_assets_price_from_ticks(); Type: FUNCTION; Schema: public; Owner: wonny
--

CREATE FUNCTION public.update_assets_price_from_ticks() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE stock_assets
    SET
        price = NEW.price,
        updated_at = NEW.timestamp
    WHERE code = NEW.stock_code
      AND EXISTS (SELECT 1 FROM stock_assets WHERE code = NEW.stock_code);
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_assets_price_from_ticks() OWNER TO wonny;

--
-- Name: update_recommendation_timestamp(); Type: FUNCTION; Schema: public; Owner: wonny
--

CREATE FUNCTION public.update_recommendation_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_recommendation_timestamp() OWNER TO wonny;

--
-- Name: update_reference_sites_timestamp(); Type: FUNCTION; Schema: public; Owner: wonny
--

CREATE FUNCTION public.update_reference_sites_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_reference_sites_timestamp() OWNER TO wonny;

--
-- Name: update_scraping_config_timestamp(); Type: FUNCTION; Schema: public; Owner: wonny
--

CREATE FUNCTION public.update_scraping_config_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_scraping_config_timestamp() OWNER TO wonny;

--
-- Name: update_site_health_timestamp(); Type: FUNCTION; Schema: public; Owner: wonny
--

CREATE FUNCTION public.update_site_health_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_site_health_timestamp() OWNER TO wonny;

--
-- Name: update_stock_assets_price(); Type: FUNCTION; Schema: public; Owner: wonny
--

CREATE FUNCTION public.update_stock_assets_price() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE stock_assets
    SET current_price = NEW.price,
        updated_at = CURRENT_TIMESTAMP
    WHERE stock_code = NEW.stock_code;

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_stock_assets_price() OWNER TO wonny;

--
-- Name: FUNCTION update_stock_assets_price(); Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON FUNCTION public.update_stock_assets_price() IS 'min_ticks 데이터 삽입 시 stock_assets.current_price 자동 업데이트';


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: wonny
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO wonny;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: aegis_signal_history; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.aegis_signal_history (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    stock_name character varying(50) NOT NULL,
    signal_type character varying(20) NOT NULL,
    signal_score integer NOT NULL,
    current_price integer NOT NULL,
    ma_score integer,
    vwap_score integer,
    rsi_score integer,
    ma_reason character varying(100),
    vwap_reason character varying(100),
    rsi_reason character varying(100),
    recorded_at timestamp without time zone DEFAULT now(),
    result_1h numeric(5,2),
    result_1d numeric(5,2),
    is_success boolean,
    verified_at timestamp without time zone,
    return_5m numeric(6,2),
    return_10m numeric(6,2),
    return_30m numeric(6,2),
    return_60m numeric(6,2),
    mfe numeric(6,2),
    mae numeric(6,2),
    trace_status character varying(20) DEFAULT 'pending'::character varying,
    trace_started_at timestamp without time zone,
    trace_completed_at timestamp without time zone,
    failure_tag character varying(50),
    market_context jsonb
);


ALTER TABLE public.aegis_signal_history OWNER TO wonny;

--
-- Name: COLUMN aegis_signal_history.market_context; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.aegis_signal_history.market_context IS '신호 발생/종료 시점의 시장 컨텍스트 (KOSPI 등락률, 섹터 동향, 뉴스 감성 등)';


--
-- Name: aegis_signal_history_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.aegis_signal_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.aegis_signal_history_id_seq OWNER TO wonny;

--
-- Name: aegis_signal_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.aegis_signal_history_id_seq OWNED BY public.aegis_signal_history.id;


--
-- Name: analysis_domains; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.analysis_domains (
    id integer NOT NULL,
    domain_code character varying(20) NOT NULL,
    domain_name_ko character varying(50) NOT NULL,
    domain_name_en character varying(50) NOT NULL,
    description text,
    data_sources text,
    analysis_methods text,
    ai_usage text,
    priority integer DEFAULT 1,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.analysis_domains OWNER TO wonny;

--
-- Name: TABLE analysis_domains; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.analysis_domains IS '분석 도메인 분류 (가격/수급/뉴스/리포트/차트)';


--
-- Name: analysis_domains_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.analysis_domains_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.analysis_domains_id_seq OWNER TO wonny;

--
-- Name: analysis_domains_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.analysis_domains_id_seq OWNED BY public.analysis_domains.id;


--
-- Name: analyst_reports; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.analyst_reports (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    securities_firm character varying(100) NOT NULL,
    analyst_name character varying(100),
    target_price integer,
    opinion character varying(20),
    report_title text,
    report_date date NOT NULL,
    report_url text,
    collected_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.analyst_reports OWNER TO wonny;

--
-- Name: TABLE analyst_reports; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.analyst_reports IS '증권사별 상세 리포트 및 목표가 (일 1회 업데이트)';


--
-- Name: COLUMN analyst_reports.securities_firm; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.analyst_reports.securities_firm IS '증권사명 (삼성증권, KB증권 등)';


--
-- Name: COLUMN analyst_reports.opinion; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.analyst_reports.opinion IS '투자의견 (매수/중립/매도/BUY/HOLD/SELL)';


--
-- Name: COLUMN analyst_reports.report_date; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.analyst_reports.report_date IS '리포트 발행일자';


--
-- Name: analyst_reports_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.analyst_reports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.analyst_reports_id_seq OWNER TO wonny;

--
-- Name: analyst_reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.analyst_reports_id_seq OWNED BY public.analyst_reports.id;


--
-- Name: analyst_target_prices; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.analyst_target_prices (
    id integer NOT NULL,
    stock_code character varying(10),
    brokerage character varying(50),
    target_price integer,
    opinion character varying(20),
    report_date character varying(8),
    title text,
    url text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.analyst_target_prices OWNER TO wonny;

--
-- Name: analyst_target_prices_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.analyst_target_prices_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.analyst_target_prices_id_seq OWNER TO wonny;

--
-- Name: analyst_target_prices_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.analyst_target_prices_id_seq OWNED BY public.analyst_target_prices.id;


--
-- Name: cash_balance; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.cash_balance (
    id integer NOT NULL,
    balance numeric(15,2) DEFAULT 0 NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.cash_balance OWNER TO wonny;

--
-- Name: cash_balance_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.cash_balance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.cash_balance_id_seq OWNER TO wonny;

--
-- Name: cash_balance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.cash_balance_id_seq OWNED BY public.cash_balance.id;


--
-- Name: collected_data; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.collected_data (
    id integer NOT NULL,
    ticker character varying(20) NOT NULL,
    site_id integer NOT NULL,
    domain_id integer NOT NULL,
    data_type character varying(30) NOT NULL,
    data_content jsonb NOT NULL,
    data_date date,
    collected_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    validity_period interval,
    expires_at timestamp without time zone,
    completeness_score integer,
    reliability_score integer,
    CONSTRAINT collected_data_completeness_score_check CHECK (((completeness_score IS NULL) OR ((completeness_score >= 1) AND (completeness_score <= 5)))),
    CONSTRAINT collected_data_reliability_score_check CHECK (((reliability_score IS NULL) OR ((reliability_score >= 1) AND (reliability_score <= 5))))
);


ALTER TABLE public.collected_data OWNER TO wonny;

--
-- Name: TABLE collected_data; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.collected_data IS '원시 수집 데이터 (JSONB), ETL 전 단계';


--
-- Name: COLUMN collected_data.data_type; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.collected_data.data_type IS 'ohlcv=시세, financial_statement=재무제표, news=뉴스, investor_trading=투자자별매매, etc';


--
-- Name: COLUMN collected_data.data_content; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.collected_data.data_content IS 'JSONB 원시 데이터 (크롤링/API 결과)';


--
-- Name: COLUMN collected_data.validity_period; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.collected_data.validity_period IS 'PostgreSQL INTERVAL 타입, 예: ''1 day''::interval, ''1 week''::interval';


--
-- Name: COLUMN collected_data.completeness_score; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.collected_data.completeness_score IS '데이터 완전성 점수 (1=매우 낮음 ~ 5=매우 높음)';


--
-- Name: collected_data_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.collected_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.collected_data_id_seq OWNER TO wonny;

--
-- Name: collected_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.collected_data_id_seq OWNED BY public.collected_data.id;


--
-- Name: daily_ohlcv; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.daily_ohlcv (
    id integer NOT NULL,
    stock_code character varying(6) NOT NULL,
    date date NOT NULL,
    open numeric(10,2) NOT NULL,
    high numeric(10,2) NOT NULL,
    low numeric(10,2) NOT NULL,
    close numeric(10,2) NOT NULL,
    volume bigint NOT NULL,
    trading_value bigint,
    ma5 numeric(10,2),
    ma20 numeric(10,2),
    ma60 numeric(10,2),
    ma120 numeric(10,2),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.daily_ohlcv OWNER TO wonny;

--
-- Name: TABLE daily_ohlcv; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.daily_ohlcv IS '일봉 데이터 (1년 보관)';


--
-- Name: COLUMN daily_ohlcv.trading_value; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.daily_ohlcv.trading_value IS '거래대금 = close * volume';


--
-- Name: daily_ohlcv_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.daily_ohlcv_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.daily_ohlcv_id_seq OWNER TO wonny;

--
-- Name: daily_ohlcv_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.daily_ohlcv_id_seq OWNED BY public.daily_ohlcv.id;


--
-- Name: daily_stock_performance; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.daily_stock_performance (
    id integer NOT NULL,
    date date NOT NULL,
    stock_code character varying(6) NOT NULL,
    stock_name character varying(100),
    start_quantity integer DEFAULT 0,
    end_quantity integer DEFAULT 0,
    open_price numeric(10,2),
    close_price numeric(10,2),
    high_price numeric(10,2),
    low_price numeric(10,2),
    change_rate numeric(6,3),
    buy_quantity integer DEFAULT 0,
    buy_amount numeric(15,2) DEFAULT 0,
    sell_quantity integer DEFAULT 0,
    sell_amount numeric(15,2) DEFAULT 0,
    realized_pnl numeric(15,2) DEFAULT 0,
    unrealized_pnl numeric(15,2) DEFAULT 0,
    aegis_signal character varying(20),
    aegis_score integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.daily_stock_performance OWNER TO wonny;

--
-- Name: TABLE daily_stock_performance; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.daily_stock_performance IS 'Phase 8: 일별 종목별 성과 상세';


--
-- Name: daily_stock_performance_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.daily_stock_performance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.daily_stock_performance_id_seq OWNER TO wonny;

--
-- Name: daily_stock_performance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.daily_stock_performance_id_seq OWNED BY public.daily_stock_performance.id;


--
-- Name: daily_summary; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.daily_summary (
    date date NOT NULL,
    total_asset numeric(15,2) DEFAULT 0,
    cash_balance numeric(15,2) DEFAULT 0,
    stock_value numeric(15,2) DEFAULT 0,
    realized_pnl numeric(15,2) DEFAULT 0,
    unrealized_pnl numeric(15,2) DEFAULT 0,
    daily_pnl numeric(15,2) DEFAULT 0,
    daily_pnl_rate numeric(6,3) DEFAULT 0,
    cumulative_realized_pnl numeric(15,2) DEFAULT 0,
    cumulative_pnl_rate numeric(8,4) DEFAULT 0,
    trade_count integer DEFAULT 0,
    buy_count integer DEFAULT 0,
    sell_count integer DEFAULT 0,
    buy_amount numeric(15,2) DEFAULT 0,
    sell_amount numeric(15,2) DEFAULT 0,
    win_trades integer DEFAULT 0,
    lose_trades integer DEFAULT 0,
    win_rate numeric(5,2) DEFAULT 0,
    aegis_signal_count integer DEFAULT 0,
    aegis_accuracy numeric(5,2) DEFAULT 0,
    kospi_close numeric(10,2),
    kospi_change_rate numeric(6,3),
    kosdaq_close numeric(10,2),
    kosdaq_change_rate numeric(6,3),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    notes text
);


ALTER TABLE public.daily_summary OWNER TO wonny;

--
-- Name: TABLE daily_summary; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.daily_summary IS 'Phase 8: 일일 매매 성과 요약 테이블';


--
-- Name: COLUMN daily_summary.total_asset; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.daily_summary.total_asset IS '총 자산 (현금 + 주식 평가금액)';


--
-- Name: COLUMN daily_summary.realized_pnl; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.daily_summary.realized_pnl IS '당일 실현 손익';


--
-- Name: COLUMN daily_summary.unrealized_pnl; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.daily_summary.unrealized_pnl IS '미실현 손익 (평가손익)';


--
-- Name: COLUMN daily_summary.daily_pnl; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.daily_summary.daily_pnl IS '전일 대비 총 손익';


--
-- Name: COLUMN daily_summary.win_rate; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.daily_summary.win_rate IS '당일 매매 승률 (%)';


--
-- Name: COLUMN daily_summary.aegis_accuracy; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.daily_summary.aegis_accuracy IS 'AEGIS 신호 적중률 (%)';


--
-- Name: daily_supply; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.daily_supply (
    id integer NOT NULL,
    stock_code character varying(20) NOT NULL,
    date date NOT NULL,
    foreign_buy_volume bigint DEFAULT 0,
    foreign_sell_volume bigint DEFAULT 0,
    foreign_net_volume bigint DEFAULT 0,
    foreign_holding_ratio numeric(10,4),
    institution_buy_volume bigint DEFAULT 0,
    institution_sell_volume bigint DEFAULT 0,
    institution_net_volume bigint DEFAULT 0,
    investment_trust_net bigint DEFAULT 0,
    pension_fund_net bigint DEFAULT 0,
    private_equity_net bigint DEFAULT 0,
    bank_net bigint DEFAULT 0,
    insurance_net bigint DEFAULT 0,
    financial_invest_net bigint DEFAULT 0,
    other_finance_net bigint DEFAULT 0,
    other_corp_net bigint DEFAULT 0,
    individual_net_volume bigint DEFAULT 0,
    program_buy_volume bigint DEFAULT 0,
    program_sell_volume bigint DEFAULT 0,
    program_net_volume bigint DEFAULT 0,
    data_source character varying(50),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.daily_supply OWNER TO wonny;

--
-- Name: TABLE daily_supply; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.daily_supply IS 'Phase 11.5: 일별 투자자별 수급 데이터';


--
-- Name: daily_supply_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.daily_supply_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.daily_supply_id_seq OWNER TO wonny;

--
-- Name: daily_supply_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.daily_supply_id_seq OWNED BY public.daily_supply.id;


--
-- Name: data_source_priority; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.data_source_priority (
    id integer NOT NULL,
    data_type character varying(50) NOT NULL,
    time_context character varying(50) NOT NULL,
    primary_source character varying(50) NOT NULL,
    fallback_source character varying(50),
    description text
);


ALTER TABLE public.data_source_priority OWNER TO wonny;

--
-- Name: TABLE data_source_priority; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.data_source_priority IS 'Phase 11.5: 데이터 소스 우선순위 설정';


--
-- Name: data_source_priority_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.data_source_priority_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.data_source_priority_id_seq OWNER TO wonny;

--
-- Name: data_source_priority_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.data_source_priority_id_seq OWNED BY public.data_source_priority.id;


--
-- Name: data_sources; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.data_sources (
    source_id integer NOT NULL,
    source_name character varying(100) NOT NULL,
    source_type character varying(20) NOT NULL,
    reliability_score numeric(3,2) DEFAULT 0.50,
    total_recommendations integer DEFAULT 0,
    correct_predictions integer DEFAULT 0,
    accuracy_rate numeric(5,2) GENERATED ALWAYS AS (
CASE
    WHEN (total_recommendations > 0) THEN (((correct_predictions)::numeric / (total_recommendations)::numeric) * (100)::numeric)
    ELSE (0)::numeric
END) STORED,
    average_error_rate numeric(10,2) DEFAULT 0,
    is_active boolean DEFAULT true,
    last_updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    reference_site_id integer
);


ALTER TABLE public.data_sources OWNER TO wonny;

--
-- Name: TABLE data_sources; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.data_sources IS '데이터 소스 신뢰도 추적 (학습 시스템 핵심)';


--
-- Name: COLUMN data_sources.reliability_score; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.data_sources.reliability_score IS '신뢰도 (0.0~1.0), 검증 후 동적 조정';


--
-- Name: COLUMN data_sources.reference_site_id; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.data_sources.reference_site_id IS '데이터 소스가 특정 사이트에서 수집된 경우 연결';


--
-- Name: data_sources_source_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.data_sources_source_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.data_sources_source_id_seq OWNER TO wonny;

--
-- Name: data_sources_source_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.data_sources_source_id_seq OWNED BY public.data_sources.source_id;


--
-- Name: faiss_index_meta; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.faiss_index_meta (
    id integer NOT NULL,
    index_name character varying(100) NOT NULL,
    index_path character varying(500),
    dimension integer NOT NULL,
    total_vectors integer DEFAULT 0,
    last_updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    description text
);


ALTER TABLE public.faiss_index_meta OWNER TO wonny;

--
-- Name: TABLE faiss_index_meta; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.faiss_index_meta IS 'Phase 11.5: FAISS 벡터 인덱스 메타데이터';


--
-- Name: faiss_index_meta_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.faiss_index_meta_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.faiss_index_meta_id_seq OWNER TO wonny;

--
-- Name: faiss_index_meta_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.faiss_index_meta_id_seq OWNED BY public.faiss_index_meta.id;


--
-- Name: fetch_execution_logs; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.fetch_execution_logs (
    id integer NOT NULL,
    site_id integer NOT NULL,
    domain_id integer,
    ticker character varying(20),
    execution_status character varying(20) NOT NULL,
    started_at timestamp without time zone NOT NULL,
    completed_at timestamp without time zone,
    execution_time_ms integer,
    records_fetched integer DEFAULT 0,
    data_quality_score integer,
    error_type character varying(50),
    error_message text,
    error_stack_trace text,
    retry_count integer DEFAULT 0,
    retry_strategy character varying(50),
    fetcher_version character varying(20),
    python_version character varying(20),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fetch_execution_logs_data_quality_score_check CHECK (((data_quality_score IS NULL) OR ((data_quality_score >= 1) AND (data_quality_score <= 5)))),
    CONSTRAINT fetch_execution_logs_execution_status_check CHECK (((execution_status)::text = ANY ((ARRAY['success'::character varying, 'failed'::character varying, 'timeout'::character varying, 'skipped'::character varying])::text[])))
);


ALTER TABLE public.fetch_execution_logs OWNER TO wonny;

--
-- Name: TABLE fetch_execution_logs; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.fetch_execution_logs IS '크롤링 실행 로그 (성공/실패/에러 추적)';


--
-- Name: COLUMN fetch_execution_logs.execution_status; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.fetch_execution_logs.execution_status IS 'success=성공, failed=실패, timeout=타임아웃, skipped=건너뜀';


--
-- Name: COLUMN fetch_execution_logs.error_type; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.fetch_execution_logs.error_type IS 'network=네트워크 오류, parsing=파싱 오류, auth=인증 오류, structure_changed=구조 변경, no_data=데이터 없음, rate_limit=요청 제한, timeout=타임아웃';


--
-- Name: COLUMN fetch_execution_logs.retry_strategy; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.fetch_execution_logs.retry_strategy IS 'exponential_backoff=지수 백오프, immediate=즉시 재시도, delayed=지연 재시도, none=재시도 없음';


--
-- Name: fetch_execution_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.fetch_execution_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.fetch_execution_logs_id_seq OWNER TO wonny;

--
-- Name: fetch_execution_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.fetch_execution_logs_id_seq OWNED BY public.fetch_execution_logs.id;


--
-- Name: institutional_holdings; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.institutional_holdings (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    stock_name character varying(100) NOT NULL,
    investor_type character varying(50) NOT NULL,
    holding_shares bigint NOT NULL,
    holding_percentage numeric(5,2) NOT NULL,
    change_shares bigint,
    change_percentage numeric(5,2),
    disclosure_date date NOT NULL,
    source_url text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.institutional_holdings OWNER TO wonny;

--
-- Name: institutional_holdings_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.institutional_holdings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.institutional_holdings_id_seq OWNER TO wonny;

--
-- Name: institutional_holdings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.institutional_holdings_id_seq OWNED BY public.institutional_holdings.id;


--
-- Name: investment_consensus; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.investment_consensus (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    data_date date NOT NULL,
    consensus_score numeric(3,2),
    buy_count integer DEFAULT 0,
    hold_count integer DEFAULT 0,
    sell_count integer DEFAULT 0,
    strong_buy_count integer DEFAULT 0,
    target_price integer,
    eps integer,
    per numeric(5,2),
    analyst_count integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.investment_consensus OWNER TO wonny;

--
-- Name: TABLE investment_consensus; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.investment_consensus IS '투자의견 컨센서스 (Naver Finance)';


--
-- Name: COLUMN investment_consensus.stock_code; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.investment_consensus.stock_code IS '종목코드 (예: 015760)';


--
-- Name: COLUMN investment_consensus.data_date; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.investment_consensus.data_date IS '데이터 기준일';


--
-- Name: COLUMN investment_consensus.consensus_score; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.investment_consensus.consensus_score IS '투자의견 점수 (1.0=매도 ~ 5.0=매수)';


--
-- Name: COLUMN investment_consensus.target_price; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.investment_consensus.target_price IS '목표주가 (원)';


--
-- Name: COLUMN investment_consensus.eps; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.investment_consensus.eps IS 'EPS (원)';


--
-- Name: COLUMN investment_consensus.per; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.investment_consensus.per IS 'PER (배)';


--
-- Name: investment_consensus_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.investment_consensus_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.investment_consensus_id_seq OWNER TO wonny;

--
-- Name: investment_consensus_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.investment_consensus_id_seq OWNED BY public.investment_consensus.id;


--
-- Name: investor_trends; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.investor_trends (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    trade_date date NOT NULL,
    individual bigint,
    "foreign" bigint,
    institutional bigint,
    collected_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.investor_trends OWNER TO wonny;

--
-- Name: TABLE investor_trends; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.investor_trends IS '투자자별 순매수 동향 (일 1회 업데이트, 최근 10일)';


--
-- Name: COLUMN investor_trends.individual; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.investor_trends.individual IS '개인 순매수 (주)';


--
-- Name: COLUMN investor_trends."foreign"; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.investor_trends."foreign" IS '외국인 순매수 (주)';


--
-- Name: COLUMN investor_trends.institutional; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.investor_trends.institutional IS '기관 순매수 (주)';


--
-- Name: investor_trends_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.investor_trends_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.investor_trends_id_seq OWNER TO wonny;

--
-- Name: investor_trends_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.investor_trends_id_seq OWNED BY public.investor_trends.id;


--
-- Name: min_ticks; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.min_ticks (
    id bigint NOT NULL,
    stock_code character varying(6) NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    price numeric(10,2) NOT NULL,
    change_rate numeric(5,2),
    volume bigint,
    bid_price numeric(10,2),
    ask_price numeric(10,2),
    bid_volume bigint,
    ask_volume bigint,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.min_ticks OWNER TO wonny;

--
-- Name: TABLE min_ticks; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.min_ticks IS '실시간 틱 데이터 (WebSocket 수신, 1일 보관)';


--
-- Name: min_ticks_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.min_ticks_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.min_ticks_id_seq OWNER TO wonny;

--
-- Name: min_ticks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.min_ticks_id_seq OWNED BY public.min_ticks.id;


--
-- Name: multiscale_patterns; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.multiscale_patterns (
    id integer NOT NULL,
    stock_code character varying(20) NOT NULL,
    stock_name character varying(100),
    pattern_date date NOT NULL,
    pattern_type character varying(50),
    embedding_5d jsonb,
    embedding_20d jsonb,
    embedding_60d jsonb,
    return_5d numeric(10,4),
    return_10d numeric(10,4),
    return_20d numeric(10,4),
    return_60d numeric(10,4),
    max_return numeric(10,4),
    foreign_flow_5d bigint,
    institution_flow_5d bigint,
    market character varying(10),
    sector character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.multiscale_patterns OWNER TO wonny;

--
-- Name: TABLE multiscale_patterns; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.multiscale_patterns IS 'Phase 11.5: 멀티 타임프레임 패턴 저장';


--
-- Name: multiscale_patterns_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.multiscale_patterns_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.multiscale_patterns_id_seq OWNER TO wonny;

--
-- Name: multiscale_patterns_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.multiscale_patterns_id_seq OWNED BY public.multiscale_patterns.id;


--
-- Name: new_stock_recommendations; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.new_stock_recommendations (
    id integer NOT NULL,
    recommended_at timestamp without time zone NOT NULL,
    stock_code character varying(10) NOT NULL,
    stock_name character varying(50) NOT NULL,
    market character varying(10) DEFAULT 'KOSPI'::character varying,
    recommended_price integer NOT NULL,
    change_rate double precision,
    aegis_score double precision,
    scanner_score double precision,
    key_reasons jsonb,
    detailed_analysis text,
    rsi_14 double precision,
    ma_5 double precision,
    ma_20 double precision,
    ma_60 double precision,
    golden_cross boolean DEFAULT false,
    foreigner_net bigint DEFAULT 0,
    institution_net bigint DEFAULT 0,
    traded_value bigint,
    tracking_status character varying(20) DEFAULT 'active'::character varying,
    tracking_end_date date,
    final_price integer,
    final_return double precision,
    max_return double precision,
    min_return double precision,
    best_day integer,
    worst_day integer,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.new_stock_recommendations OWNER TO wonny;

--
-- Name: new_stock_recommendations_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.new_stock_recommendations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.new_stock_recommendations_id_seq OWNER TO wonny;

--
-- Name: new_stock_recommendations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.new_stock_recommendations_id_seq OWNED BY public.new_stock_recommendations.id;


--
-- Name: new_stock_tracking; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.new_stock_tracking (
    id integer NOT NULL,
    recommendation_id integer,
    tracking_date date NOT NULL,
    day_number integer NOT NULL,
    open_price integer,
    high_price integer,
    low_price integer,
    close_price integer,
    volume bigint,
    daily_return double precision,
    cumulative_return double precision,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.new_stock_tracking OWNER TO wonny;

--
-- Name: new_stock_tracking_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.new_stock_tracking_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.new_stock_tracking_id_seq OWNER TO wonny;

--
-- Name: new_stock_tracking_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.new_stock_tracking_id_seq OWNED BY public.new_stock_tracking.id;


--
-- Name: news; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.news (
    id integer NOT NULL,
    stock_code character varying(6) NOT NULL,
    title character varying(500) NOT NULL,
    url character varying(1000),
    content text,
    published_at timestamp without time zone,
    source character varying(50) DEFAULT 'naver'::character varying,
    sentiment character varying(20),
    sentiment_score numeric(3,2),
    is_disclosure boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.news OWNER TO wonny;

--
-- Name: TABLE news; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.news IS '종목별 뉴스 및 공시 데이터';


--
-- Name: COLUMN news.sentiment; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.news.sentiment IS '감성 분석 결과 (Gemini AI)';


--
-- Name: COLUMN news.is_disclosure; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.news.is_disclosure IS 'DART 전자공시 여부';


--
-- Name: news_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.news_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.news_id_seq OWNER TO wonny;

--
-- Name: news_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.news_id_seq OWNED BY public.news.id;


--
-- Name: news_impact_history; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.news_impact_history (
    id integer NOT NULL,
    stock_code character varying(20) NOT NULL,
    stock_name character varying(100),
    news_date date NOT NULL,
    headline text NOT NULL,
    keywords jsonb,
    source character varying(100),
    return_1d numeric(10,4) DEFAULT 0,
    return_3d numeric(10,4) DEFAULT 0,
    return_5d numeric(10,4) DEFAULT 0,
    return_10d numeric(10,4) DEFAULT 0,
    max_return numeric(10,4) DEFAULT 0,
    impact_type character varying(20),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.news_impact_history OWNER TO wonny;

--
-- Name: news_impact_history_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.news_impact_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.news_impact_history_id_seq OWNER TO wonny;

--
-- Name: news_impact_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.news_impact_history_id_seq OWNED BY public.news_impact_history.id;


--
-- Name: pattern_match_results; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.pattern_match_results (
    id integer NOT NULL,
    scan_date date NOT NULL,
    current_stock_code character varying(20) NOT NULL,
    current_stock_name character varying(100),
    matched_pattern_id integer,
    matched_stock_code character varying(20),
    matched_stock_name character varying(100),
    matched_pattern_date date,
    similarity_score numeric(10,6),
    predicted_return numeric(10,4),
    confidence_level character varying(20),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.pattern_match_results OWNER TO wonny;

--
-- Name: TABLE pattern_match_results; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.pattern_match_results IS 'Phase 11: 패턴 매칭 결과 (AI 추천 근거)';


--
-- Name: pattern_match_results_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.pattern_match_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.pattern_match_results_id_seq OWNER TO wonny;

--
-- Name: pattern_match_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.pattern_match_results_id_seq OWNED BY public.pattern_match_results.id;


--
-- Name: portfolio_ai_history; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.portfolio_ai_history (
    id integer NOT NULL,
    stock_code character varying(6) NOT NULL,
    report_date date DEFAULT CURRENT_DATE,
    my_avg_price numeric(15,2),
    market_price numeric(15,2),
    return_rate numeric(5,2),
    recommendation character varying(20),
    rationale text,
    confidence numeric(3,2),
    is_verified boolean DEFAULT false,
    next_day_price numeric(15,2),
    next_day_return numeric(5,2),
    was_correct boolean,
    created_at timestamp without time zone DEFAULT now(),
    verified_at timestamp without time zone
);


ALTER TABLE public.portfolio_ai_history OWNER TO wonny;

--
-- Name: TABLE portfolio_ai_history; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.portfolio_ai_history IS '보유종목 AI 피드백 이력 - 매일 판단/다음날 검증';


--
-- Name: COLUMN portfolio_ai_history.recommendation; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.portfolio_ai_history.recommendation IS 'BUY_MORE(추가매수), HOLD(관망), SELL(일부매도), CUT_LOSS(손절)';


--
-- Name: COLUMN portfolio_ai_history.confidence; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.portfolio_ai_history.confidence IS '신뢰도 0.0 ~ 1.0';


--
-- Name: COLUMN portfolio_ai_history.was_correct; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.portfolio_ai_history.was_correct IS 'BUY_MORE→상승=TRUE, SELL→하락=TRUE, HOLD→±1%=TRUE';


--
-- Name: portfolio_ai_history_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.portfolio_ai_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.portfolio_ai_history_id_seq OWNER TO wonny;

--
-- Name: portfolio_ai_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.portfolio_ai_history_id_seq OWNED BY public.portfolio_ai_history.id;


--
-- Name: recommendation_history; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.recommendation_history (
    id integer NOT NULL,
    stock_code character varying(6) NOT NULL,
    stock_name character varying(100),
    recommendation_date date NOT NULL,
    recommended_price numeric(10,2) NOT NULL,
    recommendation_type character varying(10) NOT NULL,
    target_price numeric(10,2),
    total_score numeric(5,2),
    price_score numeric(5,2),
    volume_score numeric(5,2),
    supply_score numeric(5,2),
    chart_score numeric(5,2),
    news_score numeric(5,2),
    analyst_score numeric(5,2),
    source_id integer,
    gemini_reasoning text,
    note text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.recommendation_history OWNER TO wonny;

--
-- Name: TABLE recommendation_history; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.recommendation_history IS 'AI/전문가 추천 기록 (역추적 검증용)';


--
-- Name: COLUMN recommendation_history.gemini_reasoning; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.recommendation_history.gemini_reasoning IS 'Gemini Pro 최종 판단 (200자)';


--
-- Name: recommendation_history_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.recommendation_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.recommendation_history_id_seq OWNER TO wonny;

--
-- Name: recommendation_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.recommendation_history_id_seq OWNED BY public.recommendation_history.id;


--
-- Name: reference_sites; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.reference_sites (
    id integer NOT NULL,
    site_name_ko character varying(100) NOT NULL,
    site_name_en character varying(100),
    url text NOT NULL,
    category character varying(50) NOT NULL,
    main_features text,
    usage_tips text,
    reliability_rating integer,
    has_python_fetcher boolean DEFAULT false,
    is_active boolean DEFAULT true,
    last_checked date,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_quality_score numeric(3,2),
    tier integer,
    is_official boolean DEFAULT false,
    description text,
    CONSTRAINT reference_sites_reliability_rating_check CHECK (((reliability_rating >= 1) AND (reliability_rating <= 5)))
);


ALTER TABLE public.reference_sites OWNER TO wonny;

--
-- Name: TABLE reference_sites; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.reference_sites IS '41개 데이터 수집 사이트 마스터';


--
-- Name: COLUMN reference_sites.category; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.reference_sites.category IS '공시/공식정보, 포털/뉴스/차트, 기술적분석, 리포트통합, 증권사리서치, 고급분석도구';


--
-- Name: COLUMN reference_sites.reliability_rating; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.reference_sites.reliability_rating IS '1(낮음) ~ 5(매우높음)';


--
-- Name: COLUMN reference_sites.has_python_fetcher; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.reference_sites.has_python_fetcher IS '자동 데이터 수집 스크립트 존재 여부';


--
-- Name: reference_sites_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.reference_sites_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.reference_sites_id_seq OWNER TO wonny;

--
-- Name: reference_sites_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.reference_sites_id_seq OWNED BY public.reference_sites.id;


--
-- Name: site_analysis_mapping; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.site_analysis_mapping (
    id integer NOT NULL,
    site_id integer NOT NULL,
    domain_id integer NOT NULL,
    suitability_score integer,
    data_type character varying(20),
    data_quality_score integer,
    api_support boolean DEFAULT false,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    is_primary_source boolean DEFAULT false,
    CONSTRAINT site_analysis_mapping_data_quality_score_check CHECK (((data_quality_score >= 1) AND (data_quality_score <= 5))),
    CONSTRAINT site_analysis_mapping_suitability_score_check CHECK (((suitability_score >= 1) AND (suitability_score <= 5)))
);


ALTER TABLE public.site_analysis_mapping OWNER TO wonny;

--
-- Name: TABLE site_analysis_mapping; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.site_analysis_mapping IS '사이트-도메인 매핑 (어떤 사이트가 어떤 도메인 데이터 제공)';


--
-- Name: COLUMN site_analysis_mapping.suitability_score; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.site_analysis_mapping.suitability_score IS '분석 영역별 사이트 적합도 (1-5, 5=최적)';


--
-- Name: COLUMN site_analysis_mapping.data_type; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.site_analysis_mapping.data_type IS 'realtime/daily/weekly/monthly';


--
-- Name: COLUMN site_analysis_mapping.data_quality_score; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.site_analysis_mapping.data_quality_score IS '데이터 품질 점수 (1-5)';


--
-- Name: site_analysis_mapping_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.site_analysis_mapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.site_analysis_mapping_id_seq OWNER TO wonny;

--
-- Name: site_analysis_mapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.site_analysis_mapping_id_seq OWNED BY public.site_analysis_mapping.id;


--
-- Name: site_health_status; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.site_health_status (
    id integer NOT NULL,
    site_id integer NOT NULL,
    status character varying(20) NOT NULL,
    last_success_at timestamp without time zone,
    last_failure_at timestamp without time zone,
    consecutive_failures integer DEFAULT 0,
    structure_hash character varying(64),
    structure_verified_at timestamp without time zone,
    structure_change_detected boolean DEFAULT false,
    avg_response_time_ms integer,
    success_rate numeric(5,2),
    current_error_message text,
    last_checked_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT site_health_status_status_check CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'degraded'::character varying, 'failed'::character varying, 'maintenance'::character varying])::text[]))),
    CONSTRAINT site_health_status_success_rate_check CHECK (((success_rate >= (0)::numeric) AND (success_rate <= (100)::numeric)))
);


ALTER TABLE public.site_health_status OWNER TO wonny;

--
-- Name: TABLE site_health_status; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.site_health_status IS '사이트 헬스체크 (가용성, 성능, 구조 변경 모니터링)';


--
-- Name: COLUMN site_health_status.status; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.site_health_status.status IS 'active=정상, degraded=성능저하, failed=실패, maintenance=점검중';


--
-- Name: COLUMN site_health_status.consecutive_failures; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.site_health_status.consecutive_failures IS '연속 실패 횟수, 3회 이상 시 알림 필요';


--
-- Name: COLUMN site_health_status.structure_hash; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.site_health_status.structure_hash IS 'HTML selector 또는 API response 구조의 MD5 해시, 변경 감지용';


--
-- Name: COLUMN site_health_status.success_rate; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.site_health_status.success_rate IS '최근 100회 시도 중 성공률 (백분율)';


--
-- Name: site_health_status_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.site_health_status_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.site_health_status_id_seq OWNER TO wonny;

--
-- Name: site_health_status_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.site_health_status_id_seq OWNED BY public.site_health_status.id;


--
-- Name: site_scraping_config; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.site_scraping_config (
    id integer NOT NULL,
    site_id integer NOT NULL,
    access_method character varying(20) NOT NULL,
    requires_login boolean DEFAULT false,
    requires_javascript boolean DEFAULT false,
    api_base_url text,
    api_key_required boolean DEFAULT false,
    api_rate_limit_per_minute integer,
    html_selectors jsonb,
    expected_elements jsonb,
    max_retries integer DEFAULT 3,
    retry_delay_seconds integer DEFAULT 5,
    timeout_seconds integer DEFAULT 30,
    custom_user_agent text,
    use_random_user_agent boolean DEFAULT true,
    health_check_url text,
    health_check_interval_minutes integer DEFAULT 60,
    is_active boolean DEFAULT true,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT site_scraping_config_access_method_check CHECK (((access_method)::text = ANY ((ARRAY['api'::character varying, 'web_scraping'::character varying, 'selenium'::character varying, 'playwright'::character varying])::text[])))
);


ALTER TABLE public.site_scraping_config OWNER TO wonny;

--
-- Name: TABLE site_scraping_config; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.site_scraping_config IS '크롤링 설정 (접근 방법, 재시도, 파싱 규칙)';


--
-- Name: COLUMN site_scraping_config.access_method; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.site_scraping_config.access_method IS 'api=API 호출, web_scraping=BeautifulSoup, selenium=Selenium, playwright=Playwright';


--
-- Name: COLUMN site_scraping_config.html_selectors; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.site_scraping_config.html_selectors IS 'JSON 형식 예: {"price": "div.price", "title": "h1.title"}';


--
-- Name: COLUMN site_scraping_config.expected_elements; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.site_scraping_config.expected_elements IS 'JSON 배열 예: ["div.price", "h1.title"], 구조 변경 감지용';


--
-- Name: COLUMN site_scraping_config.health_check_url; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.site_scraping_config.health_check_url IS '헬스체크 전용 URL, 미설정 시 사이트 메인 URL 사용';


--
-- Name: site_scraping_config_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.site_scraping_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.site_scraping_config_id_seq OWNER TO wonny;

--
-- Name: site_scraping_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.site_scraping_config_id_seq OWNED BY public.site_scraping_config.id;


--
-- Name: site_structure_snapshots; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.site_structure_snapshots (
    id integer NOT NULL,
    site_id integer NOT NULL,
    snapshot_type character varying(20) NOT NULL,
    structure_hash character varying(64) NOT NULL,
    structure_sample text,
    full_structure text,
    elements_found jsonb,
    elements_missing jsonb,
    is_valid boolean DEFAULT true,
    captured_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    is_baseline boolean DEFAULT false,
    CONSTRAINT site_structure_snapshots_snapshot_type_check CHECK (((snapshot_type)::text = ANY ((ARRAY['html'::character varying, 'api_response'::character varying])::text[])))
);


ALTER TABLE public.site_structure_snapshots OWNER TO wonny;

--
-- Name: TABLE site_structure_snapshots; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.site_structure_snapshots IS 'HTML 구조 스냅샷 (변경 감지용)';


--
-- Name: COLUMN site_structure_snapshots.snapshot_type; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.site_structure_snapshots.snapshot_type IS 'html=HTML 구조, api_response=API 응답 구조';


--
-- Name: COLUMN site_structure_snapshots.structure_hash; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.site_structure_snapshots.structure_hash IS 'MD5 해시, 구조 변경 감지용';


--
-- Name: COLUMN site_structure_snapshots.structure_sample; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.site_structure_snapshots.structure_sample IS '구조 샘플 (처음 500자), 빠른 확인용';


--
-- Name: COLUMN site_structure_snapshots.is_baseline; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.site_structure_snapshots.is_baseline IS 'true=기준 스냅샷, 이후 스냅샷과 비교 대상';


--
-- Name: site_structure_snapshots_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.site_structure_snapshots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.site_structure_snapshots_id_seq OWNER TO wonny;

--
-- Name: site_structure_snapshots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.site_structure_snapshots_id_seq OWNED BY public.site_structure_snapshots.id;


--
-- Name: smart_ai_retrospective; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.smart_ai_retrospective (
    id integer NOT NULL,
    performance_id integer,
    recommendation_id integer,
    stock_code character varying(10) NOT NULL,
    stock_name character varying(100),
    rec_date date NOT NULL,
    rec_grade character(1),
    rec_score numeric(6,2),
    original_key_material text,
    original_risk_factor text,
    actual_return numeric(8,2),
    max_drawdown numeric(8,2),
    days_held integer,
    missed_risks text,
    actual_cause text,
    lesson_learned text,
    improvement_suggestion text,
    confidence_adjustment numeric(4,2),
    ai_raw_response jsonb,
    analyzed_at timestamp without time zone DEFAULT now(),
    model_used character varying(50) DEFAULT 'gemini-2.0-flash'::character varying
);


ALTER TABLE public.smart_ai_retrospective OWNER TO wonny;

--
-- Name: TABLE smart_ai_retrospective; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.smart_ai_retrospective IS 'AI 회고 분석 결과 (실패 종목 원인 분석)';


--
-- Name: COLUMN smart_ai_retrospective.missed_risks; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.smart_ai_retrospective.missed_risks IS 'AI가 추천 당시 놓친 리스크 요인';


--
-- Name: COLUMN smart_ai_retrospective.actual_cause; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.smart_ai_retrospective.actual_cause IS '주가 하락의 실제 원인';


--
-- Name: COLUMN smart_ai_retrospective.lesson_learned; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.smart_ai_retrospective.lesson_learned IS '이 실패에서 배운 교훈';


--
-- Name: COLUMN smart_ai_retrospective.improvement_suggestion; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.smart_ai_retrospective.improvement_suggestion IS '향후 분석 개선 제안';


--
-- Name: COLUMN smart_ai_retrospective.confidence_adjustment; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.smart_ai_retrospective.confidence_adjustment IS '해당 패턴에 대한 신뢰도 조정 (-10 ~ +10)';


--
-- Name: smart_ai_retrospective_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.smart_ai_retrospective_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.smart_ai_retrospective_id_seq OWNER TO wonny;

--
-- Name: smart_ai_retrospective_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.smart_ai_retrospective_id_seq OWNED BY public.smart_ai_retrospective.id;


--
-- Name: smart_collected_data; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.smart_collected_data (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    data_type character varying(20) NOT NULL,
    source character varying(50) NOT NULL,
    title text,
    content text,
    url text,
    sentiment numeric(4,2),
    target_price integer,
    rating character varying(20),
    firm_name character varying(50),
    data_date date,
    collected_at timestamp without time zone DEFAULT now(),
    expires_at timestamp without time zone DEFAULT (now() + '06:00:00'::interval),
    raw_data jsonb
);


ALTER TABLE public.smart_collected_data OWNER TO wonny;

--
-- Name: smart_collected_data_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.smart_collected_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.smart_collected_data_id_seq OWNER TO wonny;

--
-- Name: smart_collected_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.smart_collected_data_id_seq OWNED BY public.smart_collected_data.id;


--
-- Name: smart_feedback; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.smart_feedback (
    id integer NOT NULL,
    batch_id character varying(36),
    stock_code character varying(10),
    feedback_type character varying(30) NOT NULL,
    feedback_reason text,
    before_grade character(1),
    after_grade character(1),
    before_score numeric(6,2),
    after_score numeric(6,2),
    created_at timestamp without time zone DEFAULT now(),
    created_by character varying(50) DEFAULT 'user'::character varying
);


ALTER TABLE public.smart_feedback OWNER TO wonny;

--
-- Name: TABLE smart_feedback; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.smart_feedback IS 'AI 회고 분석 결과 - 실패한 추천에서 학습';


--
-- Name: smart_feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.smart_feedback_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.smart_feedback_id_seq OWNER TO wonny;

--
-- Name: smart_feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.smart_feedback_id_seq OWNED BY public.smart_feedback.id;


--
-- Name: smart_performance; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.smart_performance (
    id integer NOT NULL,
    recommendation_id integer,
    stock_code character varying(10) NOT NULL,
    rec_date date NOT NULL,
    rec_price integer NOT NULL,
    rec_grade character(1),
    rec_score numeric(6,2),
    check_date date NOT NULL,
    check_price integer NOT NULL,
    return_rate numeric(8,2),
    max_profit numeric(8,2),
    max_drawdown numeric(8,2),
    status character varying(20) DEFAULT 'active'::character varying,
    days_held integer,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.smart_performance OWNER TO wonny;

--
-- Name: TABLE smart_performance; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.smart_performance IS '기간별 성과 추적 (7/14/30일)';


--
-- Name: COLUMN smart_performance.status; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.smart_performance.status IS '상태: success(+10%↑), active(0%↑), warning(-5%↑), failed(-5%↓)';


--
-- Name: smart_performance_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.smart_performance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.smart_performance_id_seq OWNER TO wonny;

--
-- Name: smart_performance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.smart_performance_id_seq OWNED BY public.smart_performance.id;


--
-- Name: smart_phase1_candidates; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.smart_phase1_candidates (
    id integer NOT NULL,
    batch_id character varying(36) NOT NULL,
    stock_code character varying(10) NOT NULL,
    stock_name character varying(100),
    pbr numeric(8,3),
    per numeric(8,2),
    market_cap bigint,
    volume bigint,
    close_price integer,
    phase1a_passed boolean DEFAULT false,
    rsi_14 numeric(6,2),
    disparity_20 numeric(6,2),
    disparity_60 numeric(6,2),
    pension_net_buy bigint,
    institution_net_buy bigint,
    quant_score numeric(6,2),
    phase1b_passed boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.smart_phase1_candidates OWNER TO wonny;

--
-- Name: smart_phase1_candidates_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.smart_phase1_candidates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.smart_phase1_candidates_id_seq OWNER TO wonny;

--
-- Name: smart_phase1_candidates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.smart_phase1_candidates_id_seq OWNED BY public.smart_phase1_candidates.id;


--
-- Name: smart_price_tracking; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.smart_price_tracking (
    id integer NOT NULL,
    recommendation_id integer,
    stock_code character varying(10) NOT NULL,
    stock_name character varying(100),
    rec_date date NOT NULL,
    rec_price integer NOT NULL,
    rec_grade character(1),
    track_date date NOT NULL,
    track_price integer NOT NULL,
    return_rate numeric(8,2),
    days_held integer,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.smart_price_tracking OWNER TO wonny;

--
-- Name: TABLE smart_price_tracking; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.smart_price_tracking IS '일일 주가 추적 기록';


--
-- Name: COLUMN smart_price_tracking.return_rate; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.smart_price_tracking.return_rate IS '추천가 대비 현재가 수익률 (%)';


--
-- Name: COLUMN smart_price_tracking.days_held; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.smart_price_tracking.days_held IS '추천일 이후 경과일';


--
-- Name: smart_price_tracking_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.smart_price_tracking_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.smart_price_tracking_id_seq OWNER TO wonny;

--
-- Name: smart_price_tracking_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.smart_price_tracking_id_seq OWNED BY public.smart_price_tracking.id;


--
-- Name: smart_recommendations; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.smart_recommendations (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    stock_name character varying(100),
    recommendation_date date DEFAULT CURRENT_DATE NOT NULL,
    batch_id character varying(36),
    pbr numeric(8,3),
    per numeric(8,2),
    market_cap bigint,
    volume bigint,
    close_price integer,
    rsi_14 numeric(6,2),
    disparity_20 numeric(6,2),
    disparity_60 numeric(6,2),
    ma_20 integer,
    ma_60 integer,
    pension_net_buy bigint DEFAULT 0,
    institution_net_buy bigint DEFAULT 0,
    foreign_net_buy bigint DEFAULT 0,
    individual_net_buy bigint DEFAULT 0,
    net_buy_days integer DEFAULT 0,
    quant_score numeric(6,2),
    news_count integer DEFAULT 0,
    news_sentiment numeric(4,2),
    report_count integer DEFAULT 0,
    avg_target_price integer,
    consensus_buy integer DEFAULT 0,
    consensus_hold integer DEFAULT 0,
    consensus_sell integer DEFAULT 0,
    ai_grade character(1),
    ai_confidence numeric(4,2),
    ai_key_material text,
    ai_policy_alignment text,
    ai_buy_point text,
    ai_risk_factor text,
    ai_raw_response jsonb,
    qual_score numeric(6,2),
    final_score numeric(6,2),
    rank_in_batch integer,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.smart_recommendations OWNER TO wonny;

--
-- Name: smart_recommendations_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.smart_recommendations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.smart_recommendations_id_seq OWNER TO wonny;

--
-- Name: smart_recommendations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.smart_recommendations_id_seq OWNED BY public.smart_recommendations.id;


--
-- Name: smart_run_history; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.smart_run_history (
    id integer NOT NULL,
    batch_id character varying(36) NOT NULL,
    run_type character varying(20) NOT NULL,
    phase1a_input integer,
    phase1a_output integer,
    phase1b_output integer,
    phase2a_collected integer,
    phase2b_analyzed integer,
    phase3_scored integer,
    filter_config jsonb,
    started_at timestamp without time zone DEFAULT now(),
    phase1_completed_at timestamp without time zone,
    phase2_completed_at timestamp without time zone,
    phase3_completed_at timestamp without time zone,
    finished_at timestamp without time zone,
    status character varying(20) DEFAULT 'running'::character varying,
    error_message text
);


ALTER TABLE public.smart_run_history OWNER TO wonny;

--
-- Name: smart_run_history_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.smart_run_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.smart_run_history_id_seq OWNER TO wonny;

--
-- Name: smart_run_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.smart_run_history_id_seq OWNED BY public.smart_run_history.id;


--
-- Name: stock_assets; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.stock_assets (
    stock_code character varying(6) NOT NULL,
    stock_name character varying(100) NOT NULL,
    quantity integer DEFAULT 0,
    avg_buy_price numeric(10,2) DEFAULT 0,
    current_price numeric(10,2) DEFAULT 0,
    total_value numeric(15,2) GENERATED ALWAYS AS (((quantity)::numeric * current_price)) STORED,
    total_cost numeric(15,2) GENERATED ALWAYS AS (((quantity)::numeric * avg_buy_price)) STORED,
    profit_loss numeric(15,2) GENERATED ALWAYS AS (((quantity)::numeric * (current_price - avg_buy_price))) STORED,
    profit_loss_rate numeric(5,2) GENERATED ALWAYS AS (
CASE
    WHEN (avg_buy_price > (0)::numeric) THEN (((current_price - avg_buy_price) / avg_buy_price) * (100)::numeric)
    ELSE (0)::numeric
END) STORED,
    stop_loss_rate numeric(5,2) DEFAULT '-5.0'::numeric,
    target_profit_rate numeric(5,2) DEFAULT 10.0,
    max_position numeric(15,2) DEFAULT 0,
    is_active boolean DEFAULT true,
    auto_trading boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.stock_assets OWNER TO wonny;

--
-- Name: TABLE stock_assets; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.stock_assets IS '보유 종목 및 매매 설정';


--
-- Name: COLUMN stock_assets.avg_buy_price; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_assets.avg_buy_price IS '평균 매수가 (누적 평단가)';


--
-- Name: COLUMN stock_assets.current_price; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_assets.current_price IS 'min_ticks에서 실시간 업데이트';


--
-- Name: stock_consensus; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.stock_consensus (
    stock_code character varying(10) NOT NULL,
    target_price integer,
    opinion character varying(20),
    analyst_count integer,
    buy_count integer,
    hold_count integer,
    sell_count integer,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    eps_consensus integer,
    per_consensus numeric,
    target_high integer,
    target_low integer
);


ALTER TABLE public.stock_consensus OWNER TO wonny;

--
-- Name: TABLE stock_consensus; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.stock_consensus IS '증권사 컨센서스 캐시 (일 1회 업데이트)';


--
-- Name: COLUMN stock_consensus.target_price; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_consensus.target_price IS '평균 목표가 (원)';


--
-- Name: COLUMN stock_consensus.opinion; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_consensus.opinion IS '투자의견 (매수/중립/매도)';


--
-- Name: stock_credit_rating; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.stock_credit_rating (
    id integer NOT NULL,
    stock_code character varying(20) NOT NULL,
    agency character varying(50),
    rating character varying(20),
    date date,
    collected_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.stock_credit_rating OWNER TO wonny;

--
-- Name: stock_credit_rating_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.stock_credit_rating_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_credit_rating_id_seq OWNER TO wonny;

--
-- Name: stock_credit_rating_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.stock_credit_rating_id_seq OWNED BY public.stock_credit_rating.id;


--
-- Name: stock_financials; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.stock_financials (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    period_type character varying(10) NOT NULL,
    fiscal_year integer NOT NULL,
    fiscal_quarter integer,
    revenue bigint,
    operating_profit bigint,
    net_profit bigint,
    operating_margin numeric(10,2),
    net_margin numeric(10,2),
    total_assets bigint,
    total_liabilities bigint,
    total_equity bigint,
    debt_ratio numeric(10,2),
    operating_cashflow bigint,
    investing_cashflow bigint,
    financing_cashflow bigint,
    dividend_per_share integer,
    dividend_yield numeric(10,2),
    collected_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.stock_financials OWNER TO wonny;

--
-- Name: TABLE stock_financials; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.stock_financials IS '종목별 재무제표 (분기별/연간별)';


--
-- Name: COLUMN stock_financials.period_type; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_financials.period_type IS 'annual: 연간, quarter: 분기';


--
-- Name: COLUMN stock_financials.fiscal_year; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_financials.fiscal_year IS '회계년도 (예: 2024)';


--
-- Name: COLUMN stock_financials.fiscal_quarter; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_financials.fiscal_quarter IS '분기 (1~4, 연간일 경우 NULL)';


--
-- Name: COLUMN stock_financials.operating_margin; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_financials.operating_margin IS '영업이익률 = 영업이익/매출액 * 100';


--
-- Name: COLUMN stock_financials.debt_ratio; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_financials.debt_ratio IS '부채비율 = 총부채/자본총계 * 100';


--
-- Name: stock_financials_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.stock_financials_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_financials_id_seq OWNER TO wonny;

--
-- Name: stock_financials_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.stock_financials_id_seq OWNED BY public.stock_financials.id;


--
-- Name: stock_fundamentals; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.stock_fundamentals (
    stock_code character varying(10) NOT NULL,
    current_price integer,
    change_rate numeric(10,2),
    change_price integer,
    open_price integer,
    high_price integer,
    low_price integer,
    acc_trade_volume bigint,
    acc_trade_price bigint,
    week52_high integer,
    week52_low integer,
    market_cap bigint,
    foreign_ratio numeric(10,2),
    per numeric(10,2),
    pbr numeric(10,2),
    eps integer,
    roe numeric(10,2),
    bps integer,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    sector text,
    dividend_yield numeric,
    company_summary text
);


ALTER TABLE public.stock_fundamentals OWNER TO wonny;

--
-- Name: TABLE stock_fundamentals; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.stock_fundamentals IS '종목별 재무지표 캐시 (일 1회 업데이트)';


--
-- Name: COLUMN stock_fundamentals.current_price; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_fundamentals.current_price IS '현재가 (원)';


--
-- Name: COLUMN stock_fundamentals.per; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_fundamentals.per IS '주가수익비율';


--
-- Name: COLUMN stock_fundamentals.pbr; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_fundamentals.pbr IS '주가순자산비율';


--
-- Name: COLUMN stock_fundamentals.eps; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_fundamentals.eps IS '주당순이익 (원)';


--
-- Name: COLUMN stock_fundamentals.roe; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_fundamentals.roe IS '자기자본이익률 (%)';


--
-- Name: COLUMN stock_fundamentals.bps; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_fundamentals.bps IS '주당순자산 (원)';


--
-- Name: stock_news; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.stock_news (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    title text NOT NULL,
    summary text,
    sentiment character varying(20) NOT NULL,
    publisher character varying(100),
    published_at timestamp without time zone NOT NULL,
    source_url text NOT NULL,
    collected_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.stock_news OWNER TO wonny;

--
-- Name: TABLE stock_news; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.stock_news IS '종목별 뉴스 캐시 (일 1회 업데이트)';


--
-- Name: COLUMN stock_news.stock_code; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_news.stock_code IS '종목 코드 (6자리)';


--
-- Name: COLUMN stock_news.title; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_news.title IS '뉴스 제목';


--
-- Name: COLUMN stock_news.summary; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_news.summary IS '뉴스 요약 (첫 문장 or AI 생성)';


--
-- Name: COLUMN stock_news.sentiment; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_news.sentiment IS '호재/악재/중립 (AI 자동 분류)';


--
-- Name: COLUMN stock_news.publisher; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_news.publisher IS '언론사명';


--
-- Name: COLUMN stock_news.published_at; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_news.published_at IS '뉴스 발행 시각';


--
-- Name: COLUMN stock_news.source_url; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_news.source_url IS '뉴스 원문 URL';


--
-- Name: stock_news_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.stock_news_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_news_id_seq OWNER TO wonny;

--
-- Name: stock_news_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.stock_news_id_seq OWNED BY public.stock_news.id;


--
-- Name: stock_opinions; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.stock_opinions (
    id integer NOT NULL,
    stock_code character varying(6) NOT NULL,
    stock_name character varying(100),
    opinion_date date NOT NULL,
    opinion character varying(10) NOT NULL,
    target_price numeric(10,2),
    current_price numeric(10,2),
    expected_return numeric(5,2) GENERATED ALWAYS AS (
CASE
    WHEN (current_price > (0)::numeric) THEN (((target_price - current_price) / current_price) * (100)::numeric)
    ELSE (0)::numeric
END) STORED,
    source character varying(100),
    analyst_name character varying(50),
    summary text,
    reasoning text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.stock_opinions OWNER TO wonny;

--
-- Name: TABLE stock_opinions; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.stock_opinions IS '증권사 리포트 (투자 의견 및 목표가)';


--
-- Name: stock_opinions_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.stock_opinions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_opinions_id_seq OWNER TO wonny;

--
-- Name: stock_opinions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.stock_opinions_id_seq OWNED BY public.stock_opinions.id;


--
-- Name: stock_patterns; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.stock_patterns (
    id integer NOT NULL,
    stock_code character varying(20) NOT NULL,
    stock_name character varying(100),
    pattern_date date NOT NULL,
    pattern_type character varying(50),
    embedding jsonb NOT NULL,
    return_5d numeric(10,4),
    return_10d numeric(10,4),
    return_20d numeric(10,4),
    max_return numeric(10,4),
    market character varying(10),
    sector character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.stock_patterns OWNER TO wonny;

--
-- Name: TABLE stock_patterns; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.stock_patterns IS 'Phase 11: 과거 급등 종목 차트 패턴 벡터 저장';


--
-- Name: stock_patterns_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.stock_patterns_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_patterns_id_seq OWNER TO wonny;

--
-- Name: stock_patterns_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.stock_patterns_id_seq OWNED BY public.stock_patterns.id;


--
-- Name: stock_peers; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.stock_peers (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    peer_code character varying(10) NOT NULL,
    peer_name character varying(100) NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.stock_peers OWNER TO wonny;

--
-- Name: TABLE stock_peers; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.stock_peers IS '동종업종 비교 종목 캐시 (주 1회 업데이트)';


--
-- Name: stock_peers_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.stock_peers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_peers_id_seq OWNER TO wonny;

--
-- Name: stock_peers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.stock_peers_id_seq OWNED BY public.stock_peers.id;


--
-- Name: stock_prices_10min; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.stock_prices_10min (
    id integer NOT NULL,
    stock_code character varying(6) NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    open numeric(10,2),
    high numeric(10,2),
    low numeric(10,2),
    close numeric(10,2),
    volume bigint,
    rsi_14 numeric(5,2),
    macd numeric(10,4),
    macd_signal numeric(10,4),
    macd_hist numeric(10,4),
    bb_upper numeric(10,2),
    bb_middle numeric(10,2),
    bb_lower numeric(10,2),
    bb_position numeric(5,2),
    stoch_k numeric(5,2),
    stoch_d numeric(5,2),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.stock_prices_10min OWNER TO wonny;

--
-- Name: TABLE stock_prices_10min; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.stock_prices_10min IS '10분 단위 기술 지표 (pandas-ta 계산)';


--
-- Name: stock_prices_10min_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.stock_prices_10min_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_prices_10min_id_seq OWNER TO wonny;

--
-- Name: stock_prices_10min_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.stock_prices_10min_id_seq OWNED BY public.stock_prices_10min.id;


--
-- Name: stock_score_history; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.stock_score_history (
    id integer NOT NULL,
    stock_code character varying(6) NOT NULL,
    date date NOT NULL,
    total_score numeric(5,2) NOT NULL,
    price_score numeric(5,2),
    volume_score numeric(5,2),
    supply_score numeric(5,2),
    chart_score numeric(5,2),
    news_score numeric(5,2),
    analyst_score numeric(5,2),
    signal character varying(20),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.stock_score_history OWNER TO wonny;

--
-- Name: TABLE stock_score_history; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.stock_score_history IS '일별 종목 점수 기록 (추이 분석용)';


--
-- Name: stock_score_history_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.stock_score_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_score_history_id_seq OWNER TO wonny;

--
-- Name: stock_score_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.stock_score_history_id_seq OWNED BY public.stock_score_history.id;


--
-- Name: stock_score_weights; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.stock_score_weights (
    stock_code character varying(6) NOT NULL,
    price_weight numeric(5,2) DEFAULT 20.0,
    volume_weight numeric(5,2) DEFAULT 15.0,
    supply_weight numeric(5,2) DEFAULT 30.0,
    chart_weight numeric(5,2) DEFAULT 35.0,
    news_weight numeric(5,2) DEFAULT 1.0,
    analyst_weight numeric(5,2) DEFAULT 1.0,
    accuracy_score numeric(5,2) DEFAULT 50.0,
    sample_count integer DEFAULT 0,
    last_updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_weights_sum CHECK (((((price_weight + volume_weight) + supply_weight) + chart_weight) = 100.0))
);


ALTER TABLE public.stock_score_weights OWNER TO wonny;

--
-- Name: TABLE stock_score_weights; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.stock_score_weights IS '종목별 가중치 (학습으로 동적 조정)';


--
-- Name: COLUMN stock_score_weights.price_weight; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_score_weights.price_weight IS '가격 가중치 (%), 합계 100%';


--
-- Name: stock_supply_demand; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.stock_supply_demand (
    id integer NOT NULL,
    stock_code character varying(6) NOT NULL,
    date date NOT NULL,
    foreigner_net bigint DEFAULT 0,
    institution_net bigint DEFAULT 0,
    individual_net bigint DEFAULT 0,
    foreigner_holding_rate numeric(5,2),
    pension_net bigint DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.stock_supply_demand OWNER TO wonny;

--
-- Name: TABLE stock_supply_demand; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.stock_supply_demand IS '수급 데이터 (pykrx 수집)';


--
-- Name: COLUMN stock_supply_demand.foreigner_net; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stock_supply_demand.foreigner_net IS '외국인 순매수 금액 (원)';


--
-- Name: stock_supply_demand_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.stock_supply_demand_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_supply_demand_id_seq OWNER TO wonny;

--
-- Name: stock_supply_demand_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.stock_supply_demand_id_seq OWNED BY public.stock_supply_demand.id;


--
-- Name: stocks; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.stocks (
    stock_code character varying(6) NOT NULL,
    stock_name character varying(100) NOT NULL,
    market character varying(10),
    sector character varying(50),
    industry character varying(100),
    listing_date date,
    is_managed boolean DEFAULT false,
    is_delisted boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.stocks OWNER TO wonny;

--
-- Name: TABLE stocks; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.stocks IS '종목 마스터 데이터 (KRX 전 종목)';


--
-- Name: COLUMN stocks.stock_code; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stocks.stock_code IS '종목코드 6자리 (예: 005930)';


--
-- Name: COLUMN stocks.market; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.stocks.market IS '시장구분 (KOSPI/KOSDAQ/KONEX)';


--
-- Name: trade_history; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.trade_history (
    id integer NOT NULL,
    stock_code character varying(6) NOT NULL,
    stock_name character varying(100),
    trade_type character varying(4) NOT NULL,
    trade_date timestamp without time zone NOT NULL,
    quantity integer NOT NULL,
    price numeric(10,2) NOT NULL,
    total_amount numeric(15,2) GENERATED ALWAYS AS (((quantity)::numeric * price)) STORED,
    fee numeric(10,2) DEFAULT 0,
    tax numeric(10,2) DEFAULT 0,
    recommendation_id integer,
    total_score numeric(5,2),
    gemini_reasoning text,
    status character varying(20) DEFAULT 'executed'::character varying,
    order_type character varying(20),
    created_by character varying(50) DEFAULT 'user'::character varying,
    note text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.trade_history OWNER TO wonny;

--
-- Name: TABLE trade_history; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.trade_history IS '매매 내역 + AI 판단 근거';


--
-- Name: COLUMN trade_history.gemini_reasoning; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.trade_history.gemini_reasoning IS 'Gemini AI가 생성한 매매 근거 (200자)';


--
-- Name: trade_history_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.trade_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.trade_history_id_seq OWNER TO wonny;

--
-- Name: trade_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.trade_history_id_seq OWNED BY public.trade_history.id;


--
-- Name: v_analysis_domain_statistics; Type: VIEW; Schema: public; Owner: wonny
--

CREATE VIEW public.v_analysis_domain_statistics AS
 SELECT ad.domain_code,
    ad.domain_name_ko,
    count(sam.site_id) AS total_sites,
    count(sam.site_id) FILTER (WHERE (sam.is_primary_source = true)) AS primary_sources,
    avg(sam.suitability_score) AS avg_suitability
   FROM (public.analysis_domains ad
     LEFT JOIN public.site_analysis_mapping sam ON ((ad.id = sam.domain_id)))
  GROUP BY ad.domain_code, ad.domain_name_ko
  ORDER BY (count(sam.site_id)) DESC;


ALTER TABLE public.v_analysis_domain_statistics OWNER TO wonny;

--
-- Name: v_analysis_domain_top_sites; Type: VIEW; Schema: public; Owner: wonny
--

CREATE VIEW public.v_analysis_domain_top_sites AS
 WITH ranked_sites AS (
         SELECT ad.domain_code,
            ad.domain_name_ko,
            rs.site_name_ko,
            rs.tier,
            sam.suitability_score,
            rs.reliability_rating,
            row_number() OVER (PARTITION BY ad.domain_code ORDER BY sam.suitability_score DESC NULLS LAST, rs.reliability_rating DESC NULLS LAST) AS rank
           FROM ((public.analysis_domains ad
             JOIN public.site_analysis_mapping sam ON ((ad.id = sam.domain_id)))
             JOIN public.reference_sites rs ON ((sam.site_id = rs.id)))
          WHERE (rs.is_active = true)
        )
 SELECT ranked_sites.domain_code,
    ranked_sites.domain_name_ko,
    ranked_sites.site_name_ko,
    ranked_sites.tier,
    ranked_sites.suitability_score,
    ranked_sites.reliability_rating
   FROM ranked_sites
  WHERE (ranked_sites.rank <= 3)
  ORDER BY ranked_sites.domain_code, ranked_sites.rank;


ALTER TABLE public.v_analysis_domain_top_sites OWNER TO wonny;

--
-- Name: v_data_sources_ranking; Type: VIEW; Schema: public; Owner: wonny
--

CREATE VIEW public.v_data_sources_ranking AS
 SELECT data_sources.source_id,
    data_sources.source_name,
    data_sources.source_type,
    data_sources.reliability_score,
    data_sources.accuracy_rate,
    data_sources.total_recommendations,
    data_sources.correct_predictions
   FROM public.data_sources
  WHERE (data_sources.is_active = true)
  ORDER BY data_sources.reliability_score DESC, data_sources.accuracy_rate DESC;


ALTER TABLE public.v_data_sources_ranking OWNER TO wonny;

--
-- Name: VIEW v_data_sources_ranking; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON VIEW public.v_data_sources_ranking IS '데이터 소스 신뢰도 순위';


--
-- Name: v_failed_sites_analysis; Type: VIEW; Schema: public; Owner: wonny
--

CREATE VIEW public.v_failed_sites_analysis AS
 SELECT rs.site_name_ko,
    rs.category,
    fel.error_type,
    count(*) AS failure_count,
    max(fel.started_at) AS last_failure,
    string_agg(DISTINCT fel.error_message, ' | '::text) AS error_messages
   FROM (public.reference_sites rs
     JOIN public.fetch_execution_logs fel ON ((rs.id = fel.site_id)))
  WHERE (((fel.execution_status)::text = 'failed'::text) AND (fel.started_at >= (CURRENT_DATE - '7 days'::interval)))
  GROUP BY rs.site_name_ko, rs.category, fel.error_type
  ORDER BY (count(*)) DESC
 LIMIT 20;


ALTER TABLE public.v_failed_sites_analysis OWNER TO wonny;

--
-- Name: v_high_reliability_sites; Type: VIEW; Schema: public; Owner: wonny
--

CREATE VIEW public.v_high_reliability_sites AS
 SELECT rs.site_name_ko,
    rs.category,
    rs.tier,
    rs.reliability_rating,
    rs.data_quality_score,
    shs.success_rate,
    shs.avg_response_time_ms,
    shs.last_success_at
   FROM (public.reference_sites rs
     LEFT JOIN public.site_health_status shs ON ((rs.id = shs.site_id)))
  WHERE ((rs.is_active = true) AND (rs.reliability_rating >= 4) AND ((shs.success_rate IS NULL) OR (shs.success_rate >= (90)::numeric)))
  ORDER BY rs.reliability_rating DESC NULLS LAST, shs.success_rate DESC NULLS LAST;


ALTER TABLE public.v_high_reliability_sites OWNER TO wonny;

--
-- Name: v_holdings_summary; Type: VIEW; Schema: public; Owner: wonny
--

CREATE VIEW public.v_holdings_summary AS
 SELECT sa.stock_code,
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
   FROM (public.stock_assets sa
     JOIN public.stocks s ON (((sa.stock_code)::text = (s.stock_code)::text)))
  WHERE (sa.quantity > 0)
  ORDER BY sa.profit_loss_rate DESC;


ALTER TABLE public.v_holdings_summary OWNER TO wonny;

--
-- Name: VIEW v_holdings_summary; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON VIEW public.v_holdings_summary IS '보유 종목 현황 (수익률 높은 순)';


--
-- Name: v_latest_recommendations; Type: VIEW; Schema: public; Owner: wonny
--

CREATE VIEW public.v_latest_recommendations AS
 SELECT sr.id,
    sr.stock_code,
    sr.stock_name,
    sr.recommendation_date,
    sr.batch_id,
    sr.pbr,
    sr.per,
    sr.market_cap,
    sr.volume,
    sr.close_price,
    sr.rsi_14,
    sr.disparity_20,
    sr.disparity_60,
    sr.ma_20,
    sr.ma_60,
    sr.pension_net_buy,
    sr.institution_net_buy,
    sr.foreign_net_buy,
    sr.individual_net_buy,
    sr.net_buy_days,
    sr.quant_score,
    sr.news_count,
    sr.news_sentiment,
    sr.report_count,
    sr.avg_target_price,
    sr.consensus_buy,
    sr.consensus_hold,
    sr.consensus_sell,
    sr.ai_grade,
    sr.ai_confidence,
    sr.ai_key_material,
    sr.ai_policy_alignment,
    sr.ai_buy_point,
    sr.ai_risk_factor,
    sr.ai_raw_response,
    sr.qual_score,
    sr.final_score,
    sr.rank_in_batch,
    sr.created_at,
    sr.updated_at,
    s.stock_name AS name_from_stocks,
    s.sector,
    s.industry
   FROM (public.smart_recommendations sr
     LEFT JOIN public.stocks s ON (((sr.stock_code)::text = (s.stock_code)::text)))
  WHERE (sr.recommendation_date = ( SELECT max(smart_recommendations.recommendation_date) AS max
           FROM public.smart_recommendations))
  ORDER BY sr.final_score DESC;


ALTER TABLE public.v_latest_recommendations OWNER TO wonny;

--
-- Name: v_learning_summary; Type: VIEW; Schema: public; Owner: wonny
--

CREATE VIEW public.v_learning_summary AS
 SELECT smart_ai_retrospective.rec_grade,
    count(*) AS total_failed,
    avg(smart_ai_retrospective.actual_return) AS avg_loss,
    avg(smart_ai_retrospective.confidence_adjustment) AS avg_confidence_adj,
    string_agg(DISTINCT smart_ai_retrospective.missed_risks, ' | '::text) AS common_missed_risks
   FROM public.smart_ai_retrospective
  WHERE (smart_ai_retrospective.actual_return < ('-5'::integer)::numeric)
  GROUP BY smart_ai_retrospective.rec_grade
  ORDER BY smart_ai_retrospective.rec_grade;


ALTER TABLE public.v_learning_summary OWNER TO wonny;

--
-- Name: VIEW v_learning_summary; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON VIEW public.v_learning_summary IS '등급별 학습 교훈 요약';


--
-- Name: v_performance_summary; Type: VIEW; Schema: public; Owner: wonny
--

CREATE VIEW public.v_performance_summary AS
 SELECT smart_performance.rec_grade,
    count(*) AS total_count,
    avg(smart_performance.return_rate) AS avg_return,
    count(
        CASE
            WHEN (smart_performance.return_rate > (0)::numeric) THEN 1
            ELSE NULL::integer
        END) AS profit_count,
    count(
        CASE
            WHEN (smart_performance.return_rate <= (0)::numeric) THEN 1
            ELSE NULL::integer
        END) AS loss_count,
    round((((count(
        CASE
            WHEN (smart_performance.return_rate > (0)::numeric) THEN 1
            ELSE NULL::integer
        END))::numeric / (count(*))::numeric) * (100)::numeric), 2) AS win_rate
   FROM public.smart_performance
  WHERE ((smart_performance.status)::text <> 'active'::text)
  GROUP BY smart_performance.rec_grade
  ORDER BY smart_performance.rec_grade;


ALTER TABLE public.v_performance_summary OWNER TO wonny;

--
-- Name: VIEW v_performance_summary; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON VIEW public.v_performance_summary IS '등급별/기간별 성과 요약';


--
-- Name: v_recommendation_performance; Type: VIEW; Schema: public; Owner: wonny
--

CREATE VIEW public.v_recommendation_performance AS
 SELECT date(new_stock_recommendations.recommended_at) AS rec_date,
    new_stock_recommendations.market,
    count(*) AS total_recommendations,
    count(
        CASE
            WHEN ((new_stock_recommendations.tracking_status)::text = 'completed'::text) THEN 1
            ELSE NULL::integer
        END) AS completed,
    count(
        CASE
            WHEN (new_stock_recommendations.final_return > (0)::double precision) THEN 1
            ELSE NULL::integer
        END) AS wins,
    count(
        CASE
            WHEN (new_stock_recommendations.final_return <= (0)::double precision) THEN 1
            ELSE NULL::integer
        END) AS losses,
    round((avg(new_stock_recommendations.final_return))::numeric, 2) AS avg_return,
    round((max(new_stock_recommendations.max_return))::numeric, 2) AS best_mfe,
    round((min(new_stock_recommendations.min_return))::numeric, 2) AS worst_mae,
    round(((((count(
        CASE
            WHEN (new_stock_recommendations.final_return > (0)::double precision) THEN 1
            ELSE NULL::integer
        END))::double precision / (NULLIF(count(
        CASE
            WHEN ((new_stock_recommendations.tracking_status)::text = 'completed'::text) THEN 1
            ELSE NULL::integer
        END), 0))::double precision) * (100)::double precision))::numeric, 1) AS win_rate
   FROM public.new_stock_recommendations
  GROUP BY (date(new_stock_recommendations.recommended_at)), new_stock_recommendations.market
  ORDER BY (date(new_stock_recommendations.recommended_at)) DESC;


ALTER TABLE public.v_recommendation_performance OWNER TO wonny;

--
-- Name: v_reference_sites_by_category; Type: VIEW; Schema: public; Owner: wonny
--

CREATE VIEW public.v_reference_sites_by_category AS
 SELECT reference_sites.category,
    count(*) AS site_count,
    count(*) FILTER (WHERE (reference_sites.is_active = true)) AS active_count,
    avg(reference_sites.reliability_rating) AS avg_rating,
    avg(reference_sites.data_quality_score) AS avg_quality
   FROM public.reference_sites
  GROUP BY reference_sites.category
  ORDER BY (count(*)) DESC;


ALTER TABLE public.v_reference_sites_by_category OWNER TO wonny;

--
-- Name: v_site_analysis_capabilities; Type: VIEW; Schema: public; Owner: wonny
--

CREATE VIEW public.v_site_analysis_capabilities AS
 SELECT rs.id AS site_id,
    rs.site_name_ko,
    rs.tier,
    string_agg((ad.domain_code)::text, ', '::text ORDER BY (ad.domain_code)::text) AS supported_domains,
    count(sam.domain_id) AS domain_count,
    avg(sam.suitability_score) AS avg_suitability
   FROM ((public.reference_sites rs
     LEFT JOIN public.site_analysis_mapping sam ON ((rs.id = sam.site_id)))
     LEFT JOIN public.analysis_domains ad ON ((sam.domain_id = ad.id)))
  WHERE (rs.is_active = true)
  GROUP BY rs.id, rs.site_name_ko, rs.tier
  ORDER BY (count(sam.domain_id)) DESC, (avg(sam.suitability_score)) DESC NULLS LAST;


ALTER TABLE public.v_site_analysis_capabilities OWNER TO wonny;

--
-- Name: v_site_health_dashboard; Type: VIEW; Schema: public; Owner: wonny
--

CREATE VIEW public.v_site_health_dashboard AS
 SELECT rs.id AS site_id,
    rs.site_name_ko,
    rs.category,
    rs.tier,
    shs.status,
    shs.consecutive_failures,
    shs.success_rate,
    shs.avg_response_time_ms,
    shs.last_success_at,
    shs.last_failure_at,
    shs.structure_change_detected,
    shs.last_checked_at
   FROM (public.reference_sites rs
     LEFT JOIN public.site_health_status shs ON ((rs.id = shs.site_id)))
  WHERE (rs.is_active = true)
  ORDER BY shs.consecutive_failures DESC NULLS LAST, shs.success_rate;


ALTER TABLE public.v_site_health_dashboard OWNER TO wonny;

--
-- Name: verification_results; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.verification_results (
    id integer NOT NULL,
    recommendation_id integer NOT NULL,
    verification_date date NOT NULL,
    actual_price numeric(10,2) NOT NULL,
    price_change_rate numeric(5,2) NOT NULL,
    prediction_correct boolean,
    error_rate numeric(10,2),
    note text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.verification_results OWNER TO wonny;

--
-- Name: TABLE verification_results; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.verification_results IS '추천 정확도 검증 (7일 후 역추적)';


--
-- Name: COLUMN verification_results.prediction_correct; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.verification_results.prediction_correct IS '5% 이상 상승 여부 (매수 추천 기준)';


--
-- Name: verification_results_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.verification_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.verification_results_id_seq OWNER TO wonny;

--
-- Name: verification_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.verification_results_id_seq OWNED BY public.verification_results.id;


--
-- Name: wisefn_analyst_reports; Type: TABLE; Schema: public; Owner: wonny
--

CREATE TABLE public.wisefn_analyst_reports (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    report_date date NOT NULL,
    brokerage character varying(50) NOT NULL,
    target_price integer NOT NULL,
    price_change character varying(20),
    opinion character varying(20) NOT NULL,
    title text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.wisefn_analyst_reports OWNER TO wonny;

--
-- Name: TABLE wisefn_analyst_reports; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON TABLE public.wisefn_analyst_reports IS 'WISEfn 증권사 애널리스트 리포트 (Daum Finance 종목리포트 출처)';


--
-- Name: COLUMN wisefn_analyst_reports.stock_code; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.wisefn_analyst_reports.stock_code IS '종목코드 (예: 015760)';


--
-- Name: COLUMN wisefn_analyst_reports.report_date; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.wisefn_analyst_reports.report_date IS '리포트 발행일';


--
-- Name: COLUMN wisefn_analyst_reports.brokerage; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.wisefn_analyst_reports.brokerage IS '증권사 이름';


--
-- Name: COLUMN wisefn_analyst_reports.target_price; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.wisefn_analyst_reports.target_price IS '목표주가 (원)';


--
-- Name: COLUMN wisefn_analyst_reports.price_change; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.wisefn_analyst_reports.price_change IS '이전 대비 변화 (0, ▲ 15,000 등)';


--
-- Name: COLUMN wisefn_analyst_reports.opinion; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.wisefn_analyst_reports.opinion IS '투자의견 (매수/보유/매도)';


--
-- Name: COLUMN wisefn_analyst_reports.title; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON COLUMN public.wisefn_analyst_reports.title IS '리포트 제목';


--
-- Name: wisefn_analyst_reports_id_seq; Type: SEQUENCE; Schema: public; Owner: wonny
--

CREATE SEQUENCE public.wisefn_analyst_reports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.wisefn_analyst_reports_id_seq OWNER TO wonny;

--
-- Name: wisefn_analyst_reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wonny
--

ALTER SEQUENCE public.wisefn_analyst_reports_id_seq OWNED BY public.wisefn_analyst_reports.id;


--
-- Name: aegis_signal_history id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.aegis_signal_history ALTER COLUMN id SET DEFAULT nextval('public.aegis_signal_history_id_seq'::regclass);


--
-- Name: analysis_domains id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.analysis_domains ALTER COLUMN id SET DEFAULT nextval('public.analysis_domains_id_seq'::regclass);


--
-- Name: analyst_reports id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.analyst_reports ALTER COLUMN id SET DEFAULT nextval('public.analyst_reports_id_seq'::regclass);


--
-- Name: analyst_target_prices id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.analyst_target_prices ALTER COLUMN id SET DEFAULT nextval('public.analyst_target_prices_id_seq'::regclass);


--
-- Name: cash_balance id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.cash_balance ALTER COLUMN id SET DEFAULT nextval('public.cash_balance_id_seq'::regclass);


--
-- Name: collected_data id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.collected_data ALTER COLUMN id SET DEFAULT nextval('public.collected_data_id_seq'::regclass);


--
-- Name: daily_ohlcv id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.daily_ohlcv ALTER COLUMN id SET DEFAULT nextval('public.daily_ohlcv_id_seq'::regclass);


--
-- Name: daily_stock_performance id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.daily_stock_performance ALTER COLUMN id SET DEFAULT nextval('public.daily_stock_performance_id_seq'::regclass);


--
-- Name: daily_supply id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.daily_supply ALTER COLUMN id SET DEFAULT nextval('public.daily_supply_id_seq'::regclass);


--
-- Name: data_source_priority id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.data_source_priority ALTER COLUMN id SET DEFAULT nextval('public.data_source_priority_id_seq'::regclass);


--
-- Name: data_sources source_id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.data_sources ALTER COLUMN source_id SET DEFAULT nextval('public.data_sources_source_id_seq'::regclass);


--
-- Name: faiss_index_meta id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.faiss_index_meta ALTER COLUMN id SET DEFAULT nextval('public.faiss_index_meta_id_seq'::regclass);


--
-- Name: fetch_execution_logs id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.fetch_execution_logs ALTER COLUMN id SET DEFAULT nextval('public.fetch_execution_logs_id_seq'::regclass);


--
-- Name: institutional_holdings id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.institutional_holdings ALTER COLUMN id SET DEFAULT nextval('public.institutional_holdings_id_seq'::regclass);


--
-- Name: investment_consensus id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.investment_consensus ALTER COLUMN id SET DEFAULT nextval('public.investment_consensus_id_seq'::regclass);


--
-- Name: investor_trends id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.investor_trends ALTER COLUMN id SET DEFAULT nextval('public.investor_trends_id_seq'::regclass);


--
-- Name: min_ticks id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.min_ticks ALTER COLUMN id SET DEFAULT nextval('public.min_ticks_id_seq'::regclass);


--
-- Name: multiscale_patterns id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.multiscale_patterns ALTER COLUMN id SET DEFAULT nextval('public.multiscale_patterns_id_seq'::regclass);


--
-- Name: new_stock_recommendations id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.new_stock_recommendations ALTER COLUMN id SET DEFAULT nextval('public.new_stock_recommendations_id_seq'::regclass);


--
-- Name: new_stock_tracking id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.new_stock_tracking ALTER COLUMN id SET DEFAULT nextval('public.new_stock_tracking_id_seq'::regclass);


--
-- Name: news id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.news ALTER COLUMN id SET DEFAULT nextval('public.news_id_seq'::regclass);


--
-- Name: news_impact_history id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.news_impact_history ALTER COLUMN id SET DEFAULT nextval('public.news_impact_history_id_seq'::regclass);


--
-- Name: pattern_match_results id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.pattern_match_results ALTER COLUMN id SET DEFAULT nextval('public.pattern_match_results_id_seq'::regclass);


--
-- Name: portfolio_ai_history id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.portfolio_ai_history ALTER COLUMN id SET DEFAULT nextval('public.portfolio_ai_history_id_seq'::regclass);


--
-- Name: recommendation_history id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.recommendation_history ALTER COLUMN id SET DEFAULT nextval('public.recommendation_history_id_seq'::regclass);


--
-- Name: reference_sites id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.reference_sites ALTER COLUMN id SET DEFAULT nextval('public.reference_sites_id_seq'::regclass);


--
-- Name: site_analysis_mapping id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.site_analysis_mapping ALTER COLUMN id SET DEFAULT nextval('public.site_analysis_mapping_id_seq'::regclass);


--
-- Name: site_health_status id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.site_health_status ALTER COLUMN id SET DEFAULT nextval('public.site_health_status_id_seq'::regclass);


--
-- Name: site_scraping_config id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.site_scraping_config ALTER COLUMN id SET DEFAULT nextval('public.site_scraping_config_id_seq'::regclass);


--
-- Name: site_structure_snapshots id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.site_structure_snapshots ALTER COLUMN id SET DEFAULT nextval('public.site_structure_snapshots_id_seq'::regclass);


--
-- Name: smart_ai_retrospective id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_ai_retrospective ALTER COLUMN id SET DEFAULT nextval('public.smart_ai_retrospective_id_seq'::regclass);


--
-- Name: smart_collected_data id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_collected_data ALTER COLUMN id SET DEFAULT nextval('public.smart_collected_data_id_seq'::regclass);


--
-- Name: smart_feedback id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_feedback ALTER COLUMN id SET DEFAULT nextval('public.smart_feedback_id_seq'::regclass);


--
-- Name: smart_performance id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_performance ALTER COLUMN id SET DEFAULT nextval('public.smart_performance_id_seq'::regclass);


--
-- Name: smart_phase1_candidates id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_phase1_candidates ALTER COLUMN id SET DEFAULT nextval('public.smart_phase1_candidates_id_seq'::regclass);


--
-- Name: smart_price_tracking id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_price_tracking ALTER COLUMN id SET DEFAULT nextval('public.smart_price_tracking_id_seq'::regclass);


--
-- Name: smart_recommendations id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_recommendations ALTER COLUMN id SET DEFAULT nextval('public.smart_recommendations_id_seq'::regclass);


--
-- Name: smart_run_history id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_run_history ALTER COLUMN id SET DEFAULT nextval('public.smart_run_history_id_seq'::regclass);


--
-- Name: stock_credit_rating id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_credit_rating ALTER COLUMN id SET DEFAULT nextval('public.stock_credit_rating_id_seq'::regclass);


--
-- Name: stock_financials id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_financials ALTER COLUMN id SET DEFAULT nextval('public.stock_financials_id_seq'::regclass);


--
-- Name: stock_news id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_news ALTER COLUMN id SET DEFAULT nextval('public.stock_news_id_seq'::regclass);


--
-- Name: stock_opinions id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_opinions ALTER COLUMN id SET DEFAULT nextval('public.stock_opinions_id_seq'::regclass);


--
-- Name: stock_patterns id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_patterns ALTER COLUMN id SET DEFAULT nextval('public.stock_patterns_id_seq'::regclass);


--
-- Name: stock_peers id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_peers ALTER COLUMN id SET DEFAULT nextval('public.stock_peers_id_seq'::regclass);


--
-- Name: stock_prices_10min id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_prices_10min ALTER COLUMN id SET DEFAULT nextval('public.stock_prices_10min_id_seq'::regclass);


--
-- Name: stock_score_history id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_score_history ALTER COLUMN id SET DEFAULT nextval('public.stock_score_history_id_seq'::regclass);


--
-- Name: stock_supply_demand id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_supply_demand ALTER COLUMN id SET DEFAULT nextval('public.stock_supply_demand_id_seq'::regclass);


--
-- Name: trade_history id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.trade_history ALTER COLUMN id SET DEFAULT nextval('public.trade_history_id_seq'::regclass);


--
-- Name: verification_results id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.verification_results ALTER COLUMN id SET DEFAULT nextval('public.verification_results_id_seq'::regclass);


--
-- Name: wisefn_analyst_reports id; Type: DEFAULT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.wisefn_analyst_reports ALTER COLUMN id SET DEFAULT nextval('public.wisefn_analyst_reports_id_seq'::regclass);


--
-- Name: aegis_signal_history aegis_signal_history_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.aegis_signal_history
    ADD CONSTRAINT aegis_signal_history_pkey PRIMARY KEY (id);


--
-- Name: analysis_domains analysis_domains_domain_code_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.analysis_domains
    ADD CONSTRAINT analysis_domains_domain_code_key UNIQUE (domain_code);


--
-- Name: analysis_domains analysis_domains_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.analysis_domains
    ADD CONSTRAINT analysis_domains_pkey PRIMARY KEY (id);


--
-- Name: analyst_reports analyst_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.analyst_reports
    ADD CONSTRAINT analyst_reports_pkey PRIMARY KEY (id);


--
-- Name: analyst_reports analyst_reports_stock_code_securities_firm_report_date_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.analyst_reports
    ADD CONSTRAINT analyst_reports_stock_code_securities_firm_report_date_key UNIQUE (stock_code, securities_firm, report_date);


--
-- Name: analyst_target_prices analyst_target_prices_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.analyst_target_prices
    ADD CONSTRAINT analyst_target_prices_pkey PRIMARY KEY (id);


--
-- Name: analyst_target_prices analyst_target_prices_stock_code_brokerage_report_date_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.analyst_target_prices
    ADD CONSTRAINT analyst_target_prices_stock_code_brokerage_report_date_key UNIQUE (stock_code, brokerage, report_date);


--
-- Name: cash_balance cash_balance_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.cash_balance
    ADD CONSTRAINT cash_balance_pkey PRIMARY KEY (id);


--
-- Name: collected_data collected_data_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.collected_data
    ADD CONSTRAINT collected_data_pkey PRIMARY KEY (id);


--
-- Name: collected_data collected_data_ticker_site_id_domain_id_data_type_data_date_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.collected_data
    ADD CONSTRAINT collected_data_ticker_site_id_domain_id_data_type_data_date_key UNIQUE (ticker, site_id, domain_id, data_type, data_date);


--
-- Name: daily_ohlcv daily_ohlcv_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.daily_ohlcv
    ADD CONSTRAINT daily_ohlcv_pkey PRIMARY KEY (id);


--
-- Name: daily_ohlcv daily_ohlcv_stock_code_date_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.daily_ohlcv
    ADD CONSTRAINT daily_ohlcv_stock_code_date_key UNIQUE (stock_code, date);


--
-- Name: daily_stock_performance daily_stock_performance_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.daily_stock_performance
    ADD CONSTRAINT daily_stock_performance_pkey PRIMARY KEY (id);


--
-- Name: daily_summary daily_summary_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.daily_summary
    ADD CONSTRAINT daily_summary_pkey PRIMARY KEY (date);


--
-- Name: daily_supply daily_supply_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.daily_supply
    ADD CONSTRAINT daily_supply_pkey PRIMARY KEY (id);


--
-- Name: daily_supply daily_supply_stock_code_date_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.daily_supply
    ADD CONSTRAINT daily_supply_stock_code_date_key UNIQUE (stock_code, date);


--
-- Name: data_source_priority data_source_priority_data_type_time_context_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.data_source_priority
    ADD CONSTRAINT data_source_priority_data_type_time_context_key UNIQUE (data_type, time_context);


--
-- Name: data_source_priority data_source_priority_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.data_source_priority
    ADD CONSTRAINT data_source_priority_pkey PRIMARY KEY (id);


--
-- Name: data_sources data_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.data_sources
    ADD CONSTRAINT data_sources_pkey PRIMARY KEY (source_id);


--
-- Name: data_sources data_sources_source_name_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.data_sources
    ADD CONSTRAINT data_sources_source_name_key UNIQUE (source_name);


--
-- Name: faiss_index_meta faiss_index_meta_index_name_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.faiss_index_meta
    ADD CONSTRAINT faiss_index_meta_index_name_key UNIQUE (index_name);


--
-- Name: faiss_index_meta faiss_index_meta_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.faiss_index_meta
    ADD CONSTRAINT faiss_index_meta_pkey PRIMARY KEY (id);


--
-- Name: fetch_execution_logs fetch_execution_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.fetch_execution_logs
    ADD CONSTRAINT fetch_execution_logs_pkey PRIMARY KEY (id);


--
-- Name: institutional_holdings institutional_holdings_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.institutional_holdings
    ADD CONSTRAINT institutional_holdings_pkey PRIMARY KEY (id);


--
-- Name: investment_consensus investment_consensus_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.investment_consensus
    ADD CONSTRAINT investment_consensus_pkey PRIMARY KEY (id);


--
-- Name: investment_consensus investment_consensus_stock_code_data_date_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.investment_consensus
    ADD CONSTRAINT investment_consensus_stock_code_data_date_key UNIQUE (stock_code, data_date);


--
-- Name: investor_trends investor_trends_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.investor_trends
    ADD CONSTRAINT investor_trends_pkey PRIMARY KEY (id);


--
-- Name: investor_trends investor_trends_stock_code_trade_date_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.investor_trends
    ADD CONSTRAINT investor_trends_stock_code_trade_date_key UNIQUE (stock_code, trade_date);


--
-- Name: min_ticks min_ticks_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.min_ticks
    ADD CONSTRAINT min_ticks_pkey PRIMARY KEY (id);


--
-- Name: multiscale_patterns multiscale_patterns_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.multiscale_patterns
    ADD CONSTRAINT multiscale_patterns_pkey PRIMARY KEY (id);


--
-- Name: multiscale_patterns multiscale_patterns_stock_code_pattern_date_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.multiscale_patterns
    ADD CONSTRAINT multiscale_patterns_stock_code_pattern_date_key UNIQUE (stock_code, pattern_date);


--
-- Name: new_stock_recommendations new_stock_recommendations_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.new_stock_recommendations
    ADD CONSTRAINT new_stock_recommendations_pkey PRIMARY KEY (id);


--
-- Name: new_stock_tracking new_stock_tracking_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.new_stock_tracking
    ADD CONSTRAINT new_stock_tracking_pkey PRIMARY KEY (id);


--
-- Name: new_stock_tracking new_stock_tracking_recommendation_id_tracking_date_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.new_stock_tracking
    ADD CONSTRAINT new_stock_tracking_recommendation_id_tracking_date_key UNIQUE (recommendation_id, tracking_date);


--
-- Name: news_impact_history news_impact_history_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.news_impact_history
    ADD CONSTRAINT news_impact_history_pkey PRIMARY KEY (id);


--
-- Name: news_impact_history news_impact_history_stock_code_news_date_headline_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.news_impact_history
    ADD CONSTRAINT news_impact_history_stock_code_news_date_headline_key UNIQUE (stock_code, news_date, headline);


--
-- Name: news news_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.news
    ADD CONSTRAINT news_pkey PRIMARY KEY (id);


--
-- Name: news news_stock_code_url_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.news
    ADD CONSTRAINT news_stock_code_url_key UNIQUE (stock_code, url);


--
-- Name: pattern_match_results pattern_match_results_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.pattern_match_results
    ADD CONSTRAINT pattern_match_results_pkey PRIMARY KEY (id);


--
-- Name: portfolio_ai_history portfolio_ai_history_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.portfolio_ai_history
    ADD CONSTRAINT portfolio_ai_history_pkey PRIMARY KEY (id);


--
-- Name: portfolio_ai_history portfolio_ai_history_stock_code_report_date_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.portfolio_ai_history
    ADD CONSTRAINT portfolio_ai_history_stock_code_report_date_key UNIQUE (stock_code, report_date);


--
-- Name: recommendation_history recommendation_history_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.recommendation_history
    ADD CONSTRAINT recommendation_history_pkey PRIMARY KEY (id);


--
-- Name: reference_sites reference_sites_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.reference_sites
    ADD CONSTRAINT reference_sites_pkey PRIMARY KEY (id);


--
-- Name: site_analysis_mapping site_analysis_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.site_analysis_mapping
    ADD CONSTRAINT site_analysis_mapping_pkey PRIMARY KEY (id);


--
-- Name: site_analysis_mapping site_analysis_mapping_site_id_domain_id_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.site_analysis_mapping
    ADD CONSTRAINT site_analysis_mapping_site_id_domain_id_key UNIQUE (site_id, domain_id);


--
-- Name: site_health_status site_health_status_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.site_health_status
    ADD CONSTRAINT site_health_status_pkey PRIMARY KEY (id);


--
-- Name: site_health_status site_health_status_site_id_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.site_health_status
    ADD CONSTRAINT site_health_status_site_id_key UNIQUE (site_id);


--
-- Name: site_scraping_config site_scraping_config_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.site_scraping_config
    ADD CONSTRAINT site_scraping_config_pkey PRIMARY KEY (id);


--
-- Name: site_scraping_config site_scraping_config_site_id_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.site_scraping_config
    ADD CONSTRAINT site_scraping_config_site_id_key UNIQUE (site_id);


--
-- Name: site_structure_snapshots site_structure_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.site_structure_snapshots
    ADD CONSTRAINT site_structure_snapshots_pkey PRIMARY KEY (id);


--
-- Name: smart_ai_retrospective smart_ai_retrospective_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_ai_retrospective
    ADD CONSTRAINT smart_ai_retrospective_pkey PRIMARY KEY (id);


--
-- Name: smart_collected_data smart_collected_data_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_collected_data
    ADD CONSTRAINT smart_collected_data_pkey PRIMARY KEY (id);


--
-- Name: smart_feedback smart_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_feedback
    ADD CONSTRAINT smart_feedback_pkey PRIMARY KEY (id);


--
-- Name: smart_performance smart_performance_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_performance
    ADD CONSTRAINT smart_performance_pkey PRIMARY KEY (id);


--
-- Name: smart_phase1_candidates smart_phase1_candidates_batch_id_stock_code_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_phase1_candidates
    ADD CONSTRAINT smart_phase1_candidates_batch_id_stock_code_key UNIQUE (batch_id, stock_code);


--
-- Name: smart_phase1_candidates smart_phase1_candidates_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_phase1_candidates
    ADD CONSTRAINT smart_phase1_candidates_pkey PRIMARY KEY (id);


--
-- Name: smart_price_tracking smart_price_tracking_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_price_tracking
    ADD CONSTRAINT smart_price_tracking_pkey PRIMARY KEY (id);


--
-- Name: smart_price_tracking smart_price_tracking_recommendation_id_track_date_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_price_tracking
    ADD CONSTRAINT smart_price_tracking_recommendation_id_track_date_key UNIQUE (recommendation_id, track_date);


--
-- Name: smart_recommendations smart_recommendations_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_recommendations
    ADD CONSTRAINT smart_recommendations_pkey PRIMARY KEY (id);


--
-- Name: smart_recommendations smart_recommendations_stock_code_recommendation_date_batch__key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_recommendations
    ADD CONSTRAINT smart_recommendations_stock_code_recommendation_date_batch__key UNIQUE (stock_code, recommendation_date, batch_id);


--
-- Name: smart_run_history smart_run_history_batch_id_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_run_history
    ADD CONSTRAINT smart_run_history_batch_id_key UNIQUE (batch_id);


--
-- Name: smart_run_history smart_run_history_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_run_history
    ADD CONSTRAINT smart_run_history_pkey PRIMARY KEY (id);


--
-- Name: stock_assets stock_assets_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_assets
    ADD CONSTRAINT stock_assets_pkey PRIMARY KEY (stock_code);


--
-- Name: stock_consensus stock_consensus_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_consensus
    ADD CONSTRAINT stock_consensus_pkey PRIMARY KEY (stock_code);


--
-- Name: stock_credit_rating stock_credit_rating_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_credit_rating
    ADD CONSTRAINT stock_credit_rating_pkey PRIMARY KEY (id);


--
-- Name: stock_credit_rating stock_credit_rating_stock_code_agency_date_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_credit_rating
    ADD CONSTRAINT stock_credit_rating_stock_code_agency_date_key UNIQUE (stock_code, agency, date);


--
-- Name: stock_financials stock_financials_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_financials
    ADD CONSTRAINT stock_financials_pkey PRIMARY KEY (id);


--
-- Name: stock_financials stock_financials_stock_code_period_type_fiscal_year_fiscal__key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_financials
    ADD CONSTRAINT stock_financials_stock_code_period_type_fiscal_year_fiscal__key UNIQUE (stock_code, period_type, fiscal_year, fiscal_quarter);


--
-- Name: stock_fundamentals stock_fundamentals_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_fundamentals
    ADD CONSTRAINT stock_fundamentals_pkey PRIMARY KEY (stock_code);


--
-- Name: stock_news stock_news_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_news
    ADD CONSTRAINT stock_news_pkey PRIMARY KEY (id);


--
-- Name: stock_opinions stock_opinions_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_opinions
    ADD CONSTRAINT stock_opinions_pkey PRIMARY KEY (id);


--
-- Name: stock_patterns stock_patterns_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_patterns
    ADD CONSTRAINT stock_patterns_pkey PRIMARY KEY (id);


--
-- Name: stock_patterns stock_patterns_stock_code_pattern_date_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_patterns
    ADD CONSTRAINT stock_patterns_stock_code_pattern_date_key UNIQUE (stock_code, pattern_date);


--
-- Name: stock_peers stock_peers_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_peers
    ADD CONSTRAINT stock_peers_pkey PRIMARY KEY (id);


--
-- Name: stock_peers stock_peers_stock_code_peer_code_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_peers
    ADD CONSTRAINT stock_peers_stock_code_peer_code_key UNIQUE (stock_code, peer_code);


--
-- Name: stock_prices_10min stock_prices_10min_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_prices_10min
    ADD CONSTRAINT stock_prices_10min_pkey PRIMARY KEY (id);


--
-- Name: stock_prices_10min stock_prices_10min_stock_code_timestamp_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_prices_10min
    ADD CONSTRAINT stock_prices_10min_stock_code_timestamp_key UNIQUE (stock_code, "timestamp");


--
-- Name: stock_score_history stock_score_history_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_score_history
    ADD CONSTRAINT stock_score_history_pkey PRIMARY KEY (id);


--
-- Name: stock_score_history stock_score_history_stock_code_date_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_score_history
    ADD CONSTRAINT stock_score_history_stock_code_date_key UNIQUE (stock_code, date);


--
-- Name: stock_score_weights stock_score_weights_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_score_weights
    ADD CONSTRAINT stock_score_weights_pkey PRIMARY KEY (stock_code);


--
-- Name: stock_supply_demand stock_supply_demand_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_supply_demand
    ADD CONSTRAINT stock_supply_demand_pkey PRIMARY KEY (id);


--
-- Name: stock_supply_demand stock_supply_demand_stock_code_date_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_supply_demand
    ADD CONSTRAINT stock_supply_demand_stock_code_date_key UNIQUE (stock_code, date);


--
-- Name: stocks stocks_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stocks
    ADD CONSTRAINT stocks_pkey PRIMARY KEY (stock_code);


--
-- Name: trade_history trade_history_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.trade_history
    ADD CONSTRAINT trade_history_pkey PRIMARY KEY (id);


--
-- Name: smart_ai_retrospective unique_retro_per_performance; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_ai_retrospective
    ADD CONSTRAINT unique_retro_per_performance UNIQUE (performance_id);


--
-- Name: daily_stock_performance uq_daily_stock_perf; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.daily_stock_performance
    ADD CONSTRAINT uq_daily_stock_perf UNIQUE (date, stock_code);


--
-- Name: stock_news uq_news; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_news
    ADD CONSTRAINT uq_news UNIQUE (stock_code, title, published_at);


--
-- Name: verification_results verification_results_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.verification_results
    ADD CONSTRAINT verification_results_pkey PRIMARY KEY (id);


--
-- Name: wisefn_analyst_reports wisefn_analyst_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.wisefn_analyst_reports
    ADD CONSTRAINT wisefn_analyst_reports_pkey PRIMARY KEY (id);


--
-- Name: wisefn_analyst_reports wisefn_analyst_reports_stock_code_report_date_brokerage_key; Type: CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.wisefn_analyst_reports
    ADD CONSTRAINT wisefn_analyst_reports_stock_code_report_date_brokerage_key UNIQUE (stock_code, report_date, brokerage);


--
-- Name: idx_aegis_signal_active; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_aegis_signal_active ON public.aegis_signal_history USING btree (stock_code, recorded_at DESC) WHERE ((trace_status)::text = ANY ((ARRAY['pending'::character varying, 'tracking'::character varying])::text[]));


--
-- Name: INDEX idx_aegis_signal_active; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON INDEX public.idx_aegis_signal_active IS 'Phase 7.5: 활성 신호 추적 조회 최적화';


--
-- Name: idx_aegis_signal_failure; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_aegis_signal_failure ON public.aegis_signal_history USING btree (failure_tag, recorded_at DESC) WHERE (failure_tag IS NOT NULL);


--
-- Name: INDEX idx_aegis_signal_failure; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON INDEX public.idx_aegis_signal_failure IS 'Phase 7.5: 실패 원인 분석 조회 최적화';


--
-- Name: idx_aegis_signal_history_recorded; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_aegis_signal_history_recorded ON public.aegis_signal_history USING btree (recorded_at DESC);


--
-- Name: idx_aegis_signal_history_stock; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_aegis_signal_history_stock ON public.aegis_signal_history USING btree (stock_code, recorded_at DESC);


--
-- Name: idx_aegis_signal_unique_hourly; Type: INDEX; Schema: public; Owner: wonny
--

CREATE UNIQUE INDEX idx_aegis_signal_unique_hourly ON public.aegis_signal_history USING btree (stock_code, signal_type, date(recorded_at), EXTRACT(hour FROM recorded_at));


--
-- Name: idx_aegis_signal_verification; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_aegis_signal_verification ON public.aegis_signal_history USING btree (signal_type, recorded_at DESC);


--
-- Name: INDEX idx_aegis_signal_verification; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON INDEX public.idx_aegis_signal_verification IS 'Phase 7.5: 검증 대시보드 조회 최적화';


--
-- Name: idx_aegis_trace_status; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_aegis_trace_status ON public.aegis_signal_history USING btree (trace_status) WHERE ((trace_status)::text <> 'completed'::text);


--
-- Name: idx_analysis_domains_code; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_analysis_domains_code ON public.analysis_domains USING btree (domain_code);


--
-- Name: idx_analysis_domains_priority; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_analysis_domains_priority ON public.analysis_domains USING btree (priority);


--
-- Name: idx_analyst_reports_code_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_analyst_reports_code_date ON public.analyst_reports USING btree (stock_code, report_date DESC);


--
-- Name: idx_analyst_reports_collected; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_analyst_reports_collected ON public.analyst_reports USING btree (collected_at);


--
-- Name: idx_analyst_reports_firm; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_analyst_reports_firm ON public.analyst_reports USING btree (securities_firm);


--
-- Name: idx_collected_code; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_collected_code ON public.smart_collected_data USING btree (stock_code);


--
-- Name: idx_collected_data_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_collected_data_date ON public.collected_data USING btree (data_date DESC);


--
-- Name: idx_collected_data_expires; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_collected_data_expires ON public.collected_data USING btree (expires_at) WHERE (expires_at IS NOT NULL);


--
-- Name: idx_collected_data_jsonb; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_collected_data_jsonb ON public.collected_data USING gin (data_content);


--
-- Name: idx_collected_data_site_domain; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_collected_data_site_domain ON public.collected_data USING btree (site_id, domain_id);


--
-- Name: idx_collected_data_ticker; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_collected_data_ticker ON public.collected_data USING btree (ticker);


--
-- Name: idx_collected_expires; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_collected_expires ON public.smart_collected_data USING btree (expires_at);


--
-- Name: idx_collected_type; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_collected_type ON public.smart_collected_data USING btree (data_type);


--
-- Name: idx_consensus_data_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_consensus_data_date ON public.investment_consensus USING btree (data_date DESC);


--
-- Name: idx_consensus_stock_code; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_consensus_stock_code ON public.investment_consensus USING btree (stock_code);


--
-- Name: idx_consensus_stock_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_consensus_stock_date ON public.investment_consensus USING btree (stock_code, data_date DESC);


--
-- Name: idx_daily_ohlcv_code_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_daily_ohlcv_code_date ON public.daily_ohlcv USING btree (stock_code, date DESC);


--
-- Name: idx_daily_ohlcv_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_daily_ohlcv_date ON public.daily_ohlcv USING btree (date DESC);


--
-- Name: idx_daily_ohlcv_date_brin; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_daily_ohlcv_date_brin ON public.daily_ohlcv USING brin (date);


--
-- Name: idx_daily_ohlcv_stock_date_v2; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_daily_ohlcv_stock_date_v2 ON public.daily_ohlcv USING btree (stock_code, date DESC) WHERE (date > '2024-01-01'::date);


--
-- Name: idx_daily_stock_perf_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_daily_stock_perf_date ON public.daily_stock_performance USING btree (date DESC);


--
-- Name: idx_daily_stock_perf_stock; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_daily_stock_perf_stock ON public.daily_stock_performance USING btree (stock_code, date DESC);


--
-- Name: idx_daily_supply_code; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_daily_supply_code ON public.daily_supply USING btree (stock_code);


--
-- Name: idx_daily_supply_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_daily_supply_date ON public.daily_supply USING btree (date DESC);


--
-- Name: idx_daily_supply_foreign_net; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_daily_supply_foreign_net ON public.daily_supply USING btree (foreign_net_volume DESC);


--
-- Name: idx_daily_supply_inst_net; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_daily_supply_inst_net ON public.daily_supply USING btree (institution_net_volume DESC);


--
-- Name: idx_data_sources_reliability; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_data_sources_reliability ON public.data_sources USING btree (reliability_score DESC);


--
-- Name: idx_data_sources_site; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_data_sources_site ON public.data_sources USING btree (reference_site_id) WHERE (reference_site_id IS NOT NULL);


--
-- Name: idx_data_sources_type; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_data_sources_type ON public.data_sources USING btree (source_type);


--
-- Name: idx_feedback_stock; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_feedback_stock ON public.smart_feedback USING btree (stock_code);


--
-- Name: idx_fetch_logs_error_type; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_fetch_logs_error_type ON public.fetch_execution_logs USING btree (error_type) WHERE (error_type IS NOT NULL);


--
-- Name: idx_fetch_logs_site_status; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_fetch_logs_site_status ON public.fetch_execution_logs USING btree (site_id, execution_status);


--
-- Name: idx_fetch_logs_started_at; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_fetch_logs_started_at ON public.fetch_execution_logs USING btree (started_at DESC);


--
-- Name: idx_fetch_logs_ticker; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_fetch_logs_ticker ON public.fetch_execution_logs USING btree (ticker) WHERE (ticker IS NOT NULL);


--
-- Name: idx_institutional_holdings_disclosure_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_institutional_holdings_disclosure_date ON public.institutional_holdings USING btree (disclosure_date);


--
-- Name: idx_institutional_holdings_investor_type; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_institutional_holdings_investor_type ON public.institutional_holdings USING btree (investor_type);


--
-- Name: idx_institutional_holdings_stock_code; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_institutional_holdings_stock_code ON public.institutional_holdings USING btree (stock_code);


--
-- Name: idx_investor_trends_code_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_investor_trends_code_date ON public.investor_trends USING btree (stock_code, trade_date DESC);


--
-- Name: idx_min_ticks_code_timestamp; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_min_ticks_code_timestamp ON public.min_ticks USING btree (stock_code, "timestamp" DESC);


--
-- Name: idx_min_ticks_code_ts_optimized; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_min_ticks_code_ts_optimized ON public.min_ticks USING btree (stock_code, "timestamp" DESC);


--
-- Name: idx_min_ticks_stock_timestamp; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_min_ticks_stock_timestamp ON public.min_ticks USING btree (stock_code, "timestamp" DESC);


--
-- Name: INDEX idx_min_ticks_stock_timestamp; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON INDEX public.idx_min_ticks_stock_timestamp IS 'Phase 7.5: 종목별 시계열 데이터 조회 최적화';


--
-- Name: idx_min_ticks_timestamp; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_min_ticks_timestamp ON public.min_ticks USING btree ("timestamp" DESC);


--
-- Name: idx_min_ticks_timestamp_brin; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_min_ticks_timestamp_brin ON public.min_ticks USING brin ("timestamp");


--
-- Name: INDEX idx_min_ticks_timestamp_brin; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON INDEX public.idx_min_ticks_timestamp_brin IS 'Phase 7.5: 시계열 데이터 범위 조회 최적화 (BRIN index)';


--
-- Name: idx_multiscale_code; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_multiscale_code ON public.multiscale_patterns USING btree (stock_code);


--
-- Name: idx_multiscale_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_multiscale_date ON public.multiscale_patterns USING btree (pattern_date);


--
-- Name: idx_multiscale_return; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_multiscale_return ON public.multiscale_patterns USING btree (max_return DESC);


--
-- Name: idx_news_impact_code_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_news_impact_code_date ON public.news_impact_history USING btree (stock_code, news_date DESC);


--
-- Name: idx_news_impact_keywords; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_news_impact_keywords ON public.news_impact_history USING gin (keywords);


--
-- Name: idx_news_impact_type; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_news_impact_type ON public.news_impact_history USING btree (impact_type);


--
-- Name: idx_news_published_at; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_news_published_at ON public.news USING btree (published_at DESC);


--
-- Name: idx_news_source; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_news_source ON public.news USING btree (source);


--
-- Name: idx_news_stock_code; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_news_stock_code ON public.news USING btree (stock_code);


--
-- Name: idx_news_stock_published; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_news_stock_published ON public.news USING btree (stock_code, published_at DESC);


--
-- Name: idx_pattern_match_current; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_pattern_match_current ON public.pattern_match_results USING btree (current_stock_code);


--
-- Name: idx_pattern_match_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_pattern_match_date ON public.pattern_match_results USING btree (scan_date);


--
-- Name: idx_pattern_match_similarity; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_pattern_match_similarity ON public.pattern_match_results USING btree (similarity_score DESC);


--
-- Name: idx_perf_rec; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_perf_rec ON public.smart_performance USING btree (recommendation_id);


--
-- Name: idx_perf_status; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_perf_status ON public.smart_performance USING btree (status);


--
-- Name: idx_perf_stock; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_perf_stock ON public.smart_performance USING btree (stock_code);


--
-- Name: idx_performance_days; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_performance_days ON public.smart_performance USING btree (days_held);


--
-- Name: idx_performance_rec_id; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_performance_rec_id ON public.smart_performance USING btree (recommendation_id);


--
-- Name: idx_performance_status; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_performance_status ON public.smart_performance USING btree (status);


--
-- Name: idx_performance_stock; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_performance_stock ON public.smart_performance USING btree (stock_code);


--
-- Name: idx_pf_history_cache_lookup; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_pf_history_cache_lookup ON public.portfolio_ai_history USING btree (stock_code, report_date) INCLUDE (recommendation, rationale, confidence);


--
-- Name: idx_pf_history_code_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_pf_history_code_date ON public.portfolio_ai_history USING btree (stock_code, report_date);


--
-- Name: idx_pf_history_stock; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_pf_history_stock ON public.portfolio_ai_history USING btree (stock_code);


--
-- Name: idx_pf_history_unverified; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_pf_history_unverified ON public.portfolio_ai_history USING btree (is_verified) WHERE (is_verified = false);


--
-- Name: idx_phase1_batch; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_phase1_batch ON public.smart_phase1_candidates USING btree (batch_id);


--
-- Name: idx_phase1_passed; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_phase1_passed ON public.smart_phase1_candidates USING btree (phase1b_passed);


--
-- Name: idx_price_tracking_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_price_tracking_date ON public.smart_price_tracking USING btree (track_date);


--
-- Name: idx_price_tracking_rec_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_price_tracking_rec_date ON public.smart_price_tracking USING btree (rec_date);


--
-- Name: idx_price_tracking_rec_id; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_price_tracking_rec_id ON public.smart_price_tracking USING btree (recommendation_id);


--
-- Name: idx_price_tracking_stock; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_price_tracking_stock ON public.smart_price_tracking USING btree (stock_code);


--
-- Name: idx_rec_code; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_rec_code ON public.new_stock_recommendations USING btree (stock_code);


--
-- Name: idx_rec_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_rec_date ON public.new_stock_recommendations USING btree (recommended_at);


--
-- Name: idx_rec_market; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_rec_market ON public.new_stock_recommendations USING btree (market);


--
-- Name: idx_rec_status; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_rec_status ON public.new_stock_recommendations USING btree (tracking_status);


--
-- Name: idx_rec_unique; Type: INDEX; Schema: public; Owner: wonny
--

CREATE UNIQUE INDEX idx_rec_unique ON public.new_stock_recommendations USING btree (stock_code, date(recommended_at));


--
-- Name: idx_recommendation_history_code; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_recommendation_history_code ON public.recommendation_history USING btree (stock_code);


--
-- Name: idx_recommendation_history_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_recommendation_history_date ON public.recommendation_history USING btree (recommendation_date DESC);


--
-- Name: idx_recommendation_history_source; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_recommendation_history_source ON public.recommendation_history USING btree (source_id);


--
-- Name: idx_reference_sites_active; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_reference_sites_active ON public.reference_sites USING btree (is_active) WHERE (is_active = true);


--
-- Name: idx_reference_sites_category; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_reference_sites_category ON public.reference_sites USING btree (category);


--
-- Name: idx_reference_sites_name; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_reference_sites_name ON public.reference_sites USING btree (site_name_ko);


--
-- Name: idx_reference_sites_rating; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_reference_sites_rating ON public.reference_sites USING btree (reliability_rating DESC);


--
-- Name: idx_retro_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_retro_date ON public.smart_ai_retrospective USING btree (rec_date DESC);


--
-- Name: idx_retro_return; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_retro_return ON public.smart_ai_retrospective USING btree (actual_return);


--
-- Name: idx_retro_stock; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_retro_stock ON public.smart_ai_retrospective USING btree (stock_code);


--
-- Name: idx_retrospective_grade; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_retrospective_grade ON public.smart_ai_retrospective USING btree (rec_grade);


--
-- Name: idx_retrospective_return; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_retrospective_return ON public.smart_ai_retrospective USING btree (actual_return);


--
-- Name: idx_retrospective_stock; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_retrospective_stock ON public.smart_ai_retrospective USING btree (stock_code);


--
-- Name: idx_run_history_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_run_history_date ON public.smart_run_history USING btree (started_at DESC);


--
-- Name: idx_run_history_status; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_run_history_status ON public.smart_run_history USING btree (status);


--
-- Name: idx_scraping_config_active; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_scraping_config_active ON public.site_scraping_config USING btree (is_active);


--
-- Name: idx_scraping_config_method; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_scraping_config_method ON public.site_scraping_config USING btree (access_method);


--
-- Name: idx_site_analysis_mapping_domain; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_site_analysis_mapping_domain ON public.site_analysis_mapping USING btree (domain_id);


--
-- Name: idx_site_analysis_mapping_score; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_site_analysis_mapping_score ON public.site_analysis_mapping USING btree (suitability_score DESC);


--
-- Name: idx_site_analysis_mapping_site; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_site_analysis_mapping_site ON public.site_analysis_mapping USING btree (site_id);


--
-- Name: idx_site_health_failures; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_site_health_failures ON public.site_health_status USING btree (consecutive_failures DESC) WHERE (consecutive_failures > 0);


--
-- Name: idx_site_health_last_checked; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_site_health_last_checked ON public.site_health_status USING btree (last_checked_at DESC);


--
-- Name: idx_site_health_status; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_site_health_status ON public.site_health_status USING btree (status);


--
-- Name: idx_smart_rec_batch; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_smart_rec_batch ON public.smart_recommendations USING btree (batch_id);


--
-- Name: idx_smart_rec_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_smart_rec_date ON public.smart_recommendations USING btree (recommendation_date DESC);


--
-- Name: idx_smart_rec_grade; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_smart_rec_grade ON public.smart_recommendations USING btree (ai_grade);


--
-- Name: idx_stock_assets_active; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_assets_active ON public.stock_assets USING btree (is_active) WHERE (is_active = true);


--
-- Name: idx_stock_assets_holding; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_assets_holding ON public.stock_assets USING btree (stock_code) WHERE (quantity > 0);


--
-- Name: INDEX idx_stock_assets_holding; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON INDEX public.idx_stock_assets_holding IS 'Phase 7.5: 보유종목 조회 최적화 (partial index)';


--
-- Name: idx_stock_assets_quantity; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_assets_quantity ON public.stock_assets USING btree (quantity) WHERE (quantity > 0);


--
-- Name: idx_stock_consensus_updated; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_consensus_updated ON public.stock_consensus USING btree (updated_at);


--
-- Name: idx_stock_financials_code_period; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_financials_code_period ON public.stock_financials USING btree (stock_code, fiscal_year DESC, fiscal_quarter DESC);


--
-- Name: idx_stock_financials_collected; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_financials_collected ON public.stock_financials USING btree (collected_at);


--
-- Name: idx_stock_news_code; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_news_code ON public.stock_news USING btree (stock_code);


--
-- Name: idx_stock_news_code_published; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_news_code_published ON public.stock_news USING btree (stock_code, published_at DESC);


--
-- Name: idx_stock_news_collected; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_news_collected ON public.stock_news USING btree (collected_at);


--
-- Name: idx_stock_news_published; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_news_published ON public.stock_news USING btree (published_at DESC);


--
-- Name: idx_stock_news_published_brin; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_news_published_brin ON public.stock_news USING brin (published_at);


--
-- Name: INDEX idx_stock_news_published_brin; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON INDEX public.idx_stock_news_published_brin IS 'Phase 7.5: 뉴스 범위 조회 최적화 (BRIN index)';


--
-- Name: idx_stock_news_publisher; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_news_publisher ON public.stock_news USING btree (publisher);


--
-- Name: idx_stock_news_sentiment; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_news_sentiment ON public.stock_news USING btree (sentiment);


--
-- Name: idx_stock_news_stock_published; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_news_stock_published ON public.stock_news USING btree (stock_code, published_at DESC);


--
-- Name: INDEX idx_stock_news_stock_published; Type: COMMENT; Schema: public; Owner: wonny
--

COMMENT ON INDEX public.idx_stock_news_stock_published IS 'Phase 7.5: 종목별 뉴스 시계열 조회 최적화';


--
-- Name: idx_stock_opinions_code; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_opinions_code ON public.stock_opinions USING btree (stock_code);


--
-- Name: idx_stock_opinions_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_opinions_date ON public.stock_opinions USING btree (opinion_date DESC);


--
-- Name: idx_stock_patterns_code; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_patterns_code ON public.stock_patterns USING btree (stock_code);


--
-- Name: idx_stock_patterns_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_patterns_date ON public.stock_patterns USING btree (pattern_date);


--
-- Name: idx_stock_patterns_return; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_patterns_return ON public.stock_patterns USING btree (max_return DESC);


--
-- Name: idx_stock_patterns_type; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_patterns_type ON public.stock_patterns USING btree (pattern_type);


--
-- Name: idx_stock_peers_code; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_peers_code ON public.stock_peers USING btree (stock_code);


--
-- Name: idx_stock_prices_10min_code_time; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_prices_10min_code_time ON public.stock_prices_10min USING btree (stock_code, "timestamp" DESC);


--
-- Name: idx_stock_score_history_code_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_score_history_code_date ON public.stock_score_history USING btree (stock_code, date DESC);


--
-- Name: idx_stock_score_history_signal; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stock_score_history_signal ON public.stock_score_history USING btree (signal);


--
-- Name: idx_stocks_market; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stocks_market ON public.stocks USING btree (market);


--
-- Name: idx_stocks_name; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stocks_name ON public.stocks USING btree (stock_name);


--
-- Name: idx_stocks_sector; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_stocks_sector ON public.stocks USING btree (sector);


--
-- Name: idx_structure_snapshots_baseline; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_structure_snapshots_baseline ON public.site_structure_snapshots USING btree (is_baseline) WHERE (is_baseline = true);


--
-- Name: idx_structure_snapshots_captured; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_structure_snapshots_captured ON public.site_structure_snapshots USING btree (captured_at DESC);


--
-- Name: idx_structure_snapshots_hash; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_structure_snapshots_hash ON public.site_structure_snapshots USING btree (structure_hash);


--
-- Name: idx_structure_snapshots_site; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_structure_snapshots_site ON public.site_structure_snapshots USING btree (site_id);


--
-- Name: idx_supply_demand_code_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_supply_demand_code_date ON public.stock_supply_demand USING btree (stock_code, date DESC);


--
-- Name: idx_tracking_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_tracking_date ON public.new_stock_tracking USING btree (tracking_date);


--
-- Name: idx_tracking_rec; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_tracking_rec ON public.new_stock_tracking USING btree (recommendation_id);


--
-- Name: idx_trade_history_code; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_trade_history_code ON public.trade_history USING btree (stock_code);


--
-- Name: idx_trade_history_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_trade_history_date ON public.trade_history USING btree (trade_date DESC);


--
-- Name: idx_trade_history_type; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_trade_history_type ON public.trade_history USING btree (trade_type);


--
-- Name: idx_verification_results_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_verification_results_date ON public.verification_results USING btree (verification_date DESC);


--
-- Name: idx_verification_results_rec_id; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_verification_results_rec_id ON public.verification_results USING btree (recommendation_id);


--
-- Name: idx_wisefn_report_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_wisefn_report_date ON public.wisefn_analyst_reports USING btree (report_date DESC);


--
-- Name: idx_wisefn_stock_code; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_wisefn_stock_code ON public.wisefn_analyst_reports USING btree (stock_code);


--
-- Name: idx_wisefn_stock_date; Type: INDEX; Schema: public; Owner: wonny
--

CREATE INDEX idx_wisefn_stock_date ON public.wisefn_analyst_reports USING btree (stock_code, report_date DESC);


--
-- Name: analysis_domains trigger_update_analysis_domains_timestamp; Type: TRIGGER; Schema: public; Owner: wonny
--

CREATE TRIGGER trigger_update_analysis_domains_timestamp BEFORE UPDATE ON public.analysis_domains FOR EACH ROW EXECUTE FUNCTION public.update_analysis_domain_timestamp();


--
-- Name: new_stock_recommendations trigger_update_rec_timestamp; Type: TRIGGER; Schema: public; Owner: wonny
--

CREATE TRIGGER trigger_update_rec_timestamp BEFORE UPDATE ON public.new_stock_recommendations FOR EACH ROW EXECUTE FUNCTION public.update_recommendation_timestamp();


--
-- Name: reference_sites trigger_update_reference_sites_timestamp; Type: TRIGGER; Schema: public; Owner: wonny
--

CREATE TRIGGER trigger_update_reference_sites_timestamp BEFORE UPDATE ON public.reference_sites FOR EACH ROW EXECUTE FUNCTION public.update_reference_sites_timestamp();


--
-- Name: site_scraping_config trigger_update_scraping_config_timestamp; Type: TRIGGER; Schema: public; Owner: wonny
--

CREATE TRIGGER trigger_update_scraping_config_timestamp BEFORE UPDATE ON public.site_scraping_config FOR EACH ROW EXECUTE FUNCTION public.update_scraping_config_timestamp();


--
-- Name: site_analysis_mapping trigger_update_site_analysis_mapping_timestamp; Type: TRIGGER; Schema: public; Owner: wonny
--

CREATE TRIGGER trigger_update_site_analysis_mapping_timestamp BEFORE UPDATE ON public.site_analysis_mapping FOR EACH ROW EXECUTE FUNCTION public.update_analysis_domain_timestamp();


--
-- Name: site_health_status trigger_update_site_health_timestamp; Type: TRIGGER; Schema: public; Owner: wonny
--

CREATE TRIGGER trigger_update_site_health_timestamp BEFORE UPDATE ON public.site_health_status FOR EACH ROW EXECUTE FUNCTION public.update_site_health_timestamp();


--
-- Name: min_ticks trigger_update_stock_assets_price; Type: TRIGGER; Schema: public; Owner: wonny
--

CREATE TRIGGER trigger_update_stock_assets_price AFTER INSERT ON public.min_ticks FOR EACH ROW EXECUTE FUNCTION public.update_stock_assets_price();


--
-- Name: analysis_domains update_analysis_domains_timestamp; Type: TRIGGER; Schema: public; Owner: wonny
--

CREATE TRIGGER update_analysis_domains_timestamp BEFORE UPDATE ON public.analysis_domains FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: reference_sites update_reference_sites_timestamp; Type: TRIGGER; Schema: public; Owner: wonny
--

CREATE TRIGGER update_reference_sites_timestamp BEFORE UPDATE ON public.reference_sites FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: site_scraping_config update_scraping_config_timestamp; Type: TRIGGER; Schema: public; Owner: wonny
--

CREATE TRIGGER update_scraping_config_timestamp BEFORE UPDATE ON public.site_scraping_config FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: site_analysis_mapping update_site_analysis_mapping_timestamp; Type: TRIGGER; Schema: public; Owner: wonny
--

CREATE TRIGGER update_site_analysis_mapping_timestamp BEFORE UPDATE ON public.site_analysis_mapping FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: site_health_status update_site_health_timestamp; Type: TRIGGER; Schema: public; Owner: wonny
--

CREATE TRIGGER update_site_health_timestamp BEFORE UPDATE ON public.site_health_status FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: stock_assets update_stock_assets_updated_at; Type: TRIGGER; Schema: public; Owner: wonny
--

CREATE TRIGGER update_stock_assets_updated_at BEFORE UPDATE ON public.stock_assets FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: stock_score_weights update_stock_score_weights_updated_at; Type: TRIGGER; Schema: public; Owner: wonny
--

CREATE TRIGGER update_stock_score_weights_updated_at BEFORE UPDATE ON public.stock_score_weights FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: stocks update_stocks_updated_at; Type: TRIGGER; Schema: public; Owner: wonny
--

CREATE TRIGGER update_stocks_updated_at BEFORE UPDATE ON public.stocks FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: analyst_reports analyst_reports_stock_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.analyst_reports
    ADD CONSTRAINT analyst_reports_stock_code_fkey FOREIGN KEY (stock_code) REFERENCES public.stocks(stock_code) ON DELETE CASCADE;


--
-- Name: collected_data collected_data_domain_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.collected_data
    ADD CONSTRAINT collected_data_domain_id_fkey FOREIGN KEY (domain_id) REFERENCES public.analysis_domains(id) ON DELETE CASCADE;


--
-- Name: collected_data collected_data_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.collected_data
    ADD CONSTRAINT collected_data_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.reference_sites(id) ON DELETE CASCADE;


--
-- Name: daily_ohlcv daily_ohlcv_stock_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.daily_ohlcv
    ADD CONSTRAINT daily_ohlcv_stock_code_fkey FOREIGN KEY (stock_code) REFERENCES public.stocks(stock_code);


--
-- Name: data_sources data_sources_reference_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.data_sources
    ADD CONSTRAINT data_sources_reference_site_id_fkey FOREIGN KEY (reference_site_id) REFERENCES public.reference_sites(id) ON DELETE SET NULL;


--
-- Name: fetch_execution_logs fetch_execution_logs_domain_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.fetch_execution_logs
    ADD CONSTRAINT fetch_execution_logs_domain_id_fkey FOREIGN KEY (domain_id) REFERENCES public.analysis_domains(id) ON DELETE SET NULL;


--
-- Name: fetch_execution_logs fetch_execution_logs_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.fetch_execution_logs
    ADD CONSTRAINT fetch_execution_logs_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.reference_sites(id) ON DELETE CASCADE;


--
-- Name: investor_trends investor_trends_stock_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.investor_trends
    ADD CONSTRAINT investor_trends_stock_code_fkey FOREIGN KEY (stock_code) REFERENCES public.stocks(stock_code) ON DELETE CASCADE;


--
-- Name: min_ticks min_ticks_stock_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.min_ticks
    ADD CONSTRAINT min_ticks_stock_code_fkey FOREIGN KEY (stock_code) REFERENCES public.stocks(stock_code);


--
-- Name: new_stock_tracking new_stock_tracking_recommendation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.new_stock_tracking
    ADD CONSTRAINT new_stock_tracking_recommendation_id_fkey FOREIGN KEY (recommendation_id) REFERENCES public.new_stock_recommendations(id) ON DELETE CASCADE;


--
-- Name: news news_stock_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.news
    ADD CONSTRAINT news_stock_code_fkey FOREIGN KEY (stock_code) REFERENCES public.stocks(stock_code);


--
-- Name: pattern_match_results pattern_match_results_matched_pattern_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.pattern_match_results
    ADD CONSTRAINT pattern_match_results_matched_pattern_id_fkey FOREIGN KEY (matched_pattern_id) REFERENCES public.stock_patterns(id);


--
-- Name: recommendation_history recommendation_history_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.recommendation_history
    ADD CONSTRAINT recommendation_history_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.data_sources(source_id);


--
-- Name: recommendation_history recommendation_history_stock_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.recommendation_history
    ADD CONSTRAINT recommendation_history_stock_code_fkey FOREIGN KEY (stock_code) REFERENCES public.stocks(stock_code);


--
-- Name: site_analysis_mapping site_analysis_mapping_domain_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.site_analysis_mapping
    ADD CONSTRAINT site_analysis_mapping_domain_id_fkey FOREIGN KEY (domain_id) REFERENCES public.analysis_domains(id) ON DELETE CASCADE;


--
-- Name: site_analysis_mapping site_analysis_mapping_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.site_analysis_mapping
    ADD CONSTRAINT site_analysis_mapping_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.reference_sites(id) ON DELETE CASCADE;


--
-- Name: site_health_status site_health_status_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.site_health_status
    ADD CONSTRAINT site_health_status_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.reference_sites(id) ON DELETE CASCADE;


--
-- Name: site_scraping_config site_scraping_config_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.site_scraping_config
    ADD CONSTRAINT site_scraping_config_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.reference_sites(id) ON DELETE CASCADE;


--
-- Name: site_structure_snapshots site_structure_snapshots_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.site_structure_snapshots
    ADD CONSTRAINT site_structure_snapshots_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.reference_sites(id) ON DELETE CASCADE;


--
-- Name: smart_ai_retrospective smart_ai_retrospective_performance_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_ai_retrospective
    ADD CONSTRAINT smart_ai_retrospective_performance_id_fkey FOREIGN KEY (performance_id) REFERENCES public.smart_performance(id);


--
-- Name: smart_ai_retrospective smart_ai_retrospective_recommendation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_ai_retrospective
    ADD CONSTRAINT smart_ai_retrospective_recommendation_id_fkey FOREIGN KEY (recommendation_id) REFERENCES public.smart_recommendations(id);


--
-- Name: smart_performance smart_performance_recommendation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_performance
    ADD CONSTRAINT smart_performance_recommendation_id_fkey FOREIGN KEY (recommendation_id) REFERENCES public.smart_recommendations(id);


--
-- Name: smart_price_tracking smart_price_tracking_recommendation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.smart_price_tracking
    ADD CONSTRAINT smart_price_tracking_recommendation_id_fkey FOREIGN KEY (recommendation_id) REFERENCES public.smart_recommendations(id);


--
-- Name: stock_assets stock_assets_stock_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_assets
    ADD CONSTRAINT stock_assets_stock_code_fkey FOREIGN KEY (stock_code) REFERENCES public.stocks(stock_code);


--
-- Name: stock_consensus stock_consensus_stock_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_consensus
    ADD CONSTRAINT stock_consensus_stock_code_fkey FOREIGN KEY (stock_code) REFERENCES public.stocks(stock_code) ON DELETE CASCADE;


--
-- Name: stock_financials stock_financials_stock_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_financials
    ADD CONSTRAINT stock_financials_stock_code_fkey FOREIGN KEY (stock_code) REFERENCES public.stocks(stock_code) ON DELETE CASCADE;


--
-- Name: stock_fundamentals stock_fundamentals_stock_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_fundamentals
    ADD CONSTRAINT stock_fundamentals_stock_code_fkey FOREIGN KEY (stock_code) REFERENCES public.stocks(stock_code) ON DELETE CASCADE;


--
-- Name: stock_opinions stock_opinions_stock_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_opinions
    ADD CONSTRAINT stock_opinions_stock_code_fkey FOREIGN KEY (stock_code) REFERENCES public.stocks(stock_code);


--
-- Name: stock_peers stock_peers_stock_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_peers
    ADD CONSTRAINT stock_peers_stock_code_fkey FOREIGN KEY (stock_code) REFERENCES public.stocks(stock_code) ON DELETE CASCADE;


--
-- Name: stock_prices_10min stock_prices_10min_stock_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_prices_10min
    ADD CONSTRAINT stock_prices_10min_stock_code_fkey FOREIGN KEY (stock_code) REFERENCES public.stocks(stock_code);


--
-- Name: stock_score_history stock_score_history_stock_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_score_history
    ADD CONSTRAINT stock_score_history_stock_code_fkey FOREIGN KEY (stock_code) REFERENCES public.stocks(stock_code);


--
-- Name: stock_score_weights stock_score_weights_stock_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_score_weights
    ADD CONSTRAINT stock_score_weights_stock_code_fkey FOREIGN KEY (stock_code) REFERENCES public.stocks(stock_code);


--
-- Name: stock_supply_demand stock_supply_demand_stock_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.stock_supply_demand
    ADD CONSTRAINT stock_supply_demand_stock_code_fkey FOREIGN KEY (stock_code) REFERENCES public.stocks(stock_code);


--
-- Name: trade_history trade_history_stock_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.trade_history
    ADD CONSTRAINT trade_history_stock_code_fkey FOREIGN KEY (stock_code) REFERENCES public.stocks(stock_code);


--
-- Name: verification_results verification_results_recommendation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: wonny
--

ALTER TABLE ONLY public.verification_results
    ADD CONSTRAINT verification_results_recommendation_id_fkey FOREIGN KEY (recommendation_id) REFERENCES public.recommendation_history(id);


--
-- PostgreSQL database dump complete
--

\unrestrict CGlJH1BKpZym4mttqdbGvBwDc0A9JLT3akuX5vIIwRrgblBfnbRNPMFf866ZFft

