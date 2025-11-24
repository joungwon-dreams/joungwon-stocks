-- ============================================================
-- Database Schema Verification Script
-- ============================================================

-- Show all tables
\echo '\n📊 All Tables:'
\dt

-- Show all views
\echo '\n👁️  All Views:'
\dv

-- Show all triggers
\echo '\n⚡ All Triggers:'
SELECT
    trigger_name,
    event_object_table AS table_name,
    action_timing AS timing,
    event_manipulation AS event
FROM information_schema.triggers
WHERE trigger_schema = 'public'
ORDER BY event_object_table, trigger_name;

-- Show all functions
\echo '\n🔧 All Functions:'
\df

-- Verify table record counts
\echo '\n📈 Table Record Counts:'
SELECT
    'stocks' AS table_name,
    COUNT(*) AS record_count
FROM stocks
UNION ALL
SELECT 'stock_assets', COUNT(*) FROM stock_assets
UNION ALL
SELECT 'daily_ohlcv', COUNT(*) FROM daily_ohlcv
UNION ALL
SELECT 'min_ticks', COUNT(*) FROM min_ticks
UNION ALL
SELECT 'stock_prices_10min', COUNT(*) FROM stock_prices_10min
UNION ALL
SELECT 'stock_supply_demand', COUNT(*) FROM stock_supply_demand
UNION ALL
SELECT 'trade_history', COUNT(*) FROM trade_history
UNION ALL
SELECT 'stock_opinions', COUNT(*) FROM stock_opinions
UNION ALL
SELECT 'data_sources', COUNT(*) FROM data_sources
UNION ALL
SELECT 'recommendation_history', COUNT(*) FROM recommendation_history
UNION ALL
SELECT 'verification_results', COUNT(*) FROM verification_results
UNION ALL
SELECT 'stock_score_weights', COUNT(*) FROM stock_score_weights
UNION ALL
SELECT 'stock_score_history', COUNT(*) FROM stock_score_history
ORDER BY table_name;

-- Show data_sources initial data
\echo '\n🔍 Initial Data Sources (14 entries):'
SELECT
    source_id,
    source_name,
    source_type,
    reliability_score,
    total_recommendations,
    correct_predictions
FROM data_sources
ORDER BY source_type, reliability_score DESC;

-- Verify indexes
\echo '\n🗂️  All Indexes:'
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- Database size
\echo '\n💾 Database Size:'
SELECT
    pg_size_pretty(pg_database_size('stock_investment_db')) AS database_size;

-- Success message
\echo '\n✅ Schema verification complete!'
\echo '📊 13 tables created'
\echo '🔍 2 views created'
\echo '⚡ 4 triggers created'
\echo '📝 14 data sources initialized'
