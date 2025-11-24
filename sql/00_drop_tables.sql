-- ============================================================
-- Drop All Tables Script
-- WARNING: This will delete ALL data in the database!
-- ============================================================

-- Drop views first
DROP VIEW IF EXISTS v_holdings_summary CASCADE;
DROP VIEW IF EXISTS v_data_sources_ranking CASCADE;

-- Drop triggers
DROP TRIGGER IF EXISTS update_stocks_updated_at ON stocks;
DROP TRIGGER IF EXISTS update_stock_assets_updated_at ON stock_assets;
DROP TRIGGER IF EXISTS update_stock_score_weights_updated_at ON stock_score_weights;
DROP TRIGGER IF EXISTS trigger_update_stock_assets_price ON min_ticks;

-- Drop functions
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
DROP FUNCTION IF EXISTS update_stock_assets_price() CASCADE;

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS verification_results CASCADE;
DROP TABLE IF EXISTS recommendation_history CASCADE;
DROP TABLE IF EXISTS stock_score_history CASCADE;
DROP TABLE IF EXISTS stock_score_weights CASCADE;
DROP TABLE IF EXISTS stock_opinions CASCADE;
DROP TABLE IF EXISTS trade_history CASCADE;
DROP TABLE IF EXISTS stock_supply_demand CASCADE;
DROP TABLE IF EXISTS stock_prices_10min CASCADE;
DROP TABLE IF EXISTS min_ticks CASCADE;
DROP TABLE IF EXISTS daily_ohlcv CASCADE;
DROP TABLE IF EXISTS stock_assets CASCADE;
DROP TABLE IF EXISTS data_sources CASCADE;
DROP TABLE IF EXISTS stocks CASCADE;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ All tables dropped successfully!';
    RAISE NOTICE '⚠️  All data has been deleted!';
END $$;
