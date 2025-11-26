-- Enable pg_trgm extension for trigram-based fuzzy search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 設定 pg_trgm 相似度閾值
-- similarity_threshold: 用於 % 操作符，預設 0.3（範圍 0-1，越小越寬鬆）
-- word_similarity_threshold: 用於 <<% 操作符，預設 0.6
ALTER DATABASE testdb SET pg_trgm.similarity_threshold = 0.3;
ALTER DATABASE testdb SET pg_trgm.word_similarity_threshold = 0.6;

-- Create worlds table to store book data
CREATE TABLE IF NOT EXISTS worlds (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT
);

-- Create trigram indexes for fuzzy search
-- These indexes enable fast similarity searches using pg_trgm
CREATE INDEX IF NOT EXISTS idx_title_trgm ON worlds USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_desc_trgm ON worlds USING gin (description gin_trgm_ops);

-- ============================================================================
-- 管理函數
-- ============================================================================

-- 函數: 產生指定數量的測試資料
CREATE OR REPLACE FUNCTION generate_test_data(record_count INTEGER)
RETURNS TABLE(
    inserted_count INTEGER,
    execution_time_ms NUMERIC
) AS $$
DECLARE
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    actual_count INTEGER;
BEGIN
    start_time := clock_timestamp();
    
    -- 插入測試資料
    INSERT INTO worlds (title, description)
    SELECT
        md5(random()::text) AS title,
        md5(random()::text) || ' ' || md5(random()::text) AS description
    FROM generate_series(1, record_count);
    
    GET DIAGNOSTICS actual_count = ROW_COUNT;
    end_time := clock_timestamp();
    
    -- 回傳結果
    RETURN QUERY SELECT 
        actual_count,
        EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;
END;
$$ LANGUAGE plpgsql;

-- 函數: 清空所有資料
CREATE OR REPLACE FUNCTION clear_all_data()
RETURNS TABLE(
    deleted_count INTEGER,
    execution_time_ms NUMERIC
) AS $$
DECLARE
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    actual_count INTEGER;
BEGIN
    start_time := clock_timestamp();
    
    -- 先取得當前數量
    SELECT COUNT(*) INTO actual_count FROM worlds;
    
    -- 使用 TRUNCATE 代替 DELETE (更快且自動回收空間)
    TRUNCATE TABLE worlds;
    
    end_time := clock_timestamp();
    
    -- 回傳結果
    RETURN QUERY SELECT 
        actual_count,
        EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;
END;
$$ LANGUAGE plpgsql;

-- 函數: 取得資料統計
CREATE OR REPLACE FUNCTION get_data_stats()
RETURNS TABLE(
    total_records BIGINT,
    table_size TEXT,
    index_size TEXT,
    total_size TEXT
) AS $$
BEGIN
    RETURN QUERY 
    SELECT 
        COUNT(*)::BIGINT as total_records,
        pg_size_pretty(pg_total_relation_size('worlds') - pg_indexes_size('worlds')) as table_size,
        pg_size_pretty(pg_indexes_size('worlds')) as index_size,
        pg_size_pretty(pg_total_relation_size('worlds')) as total_size
    FROM worlds;
END;
$$ LANGUAGE plpgsql;

-- 函數: 重建索引 (在資料量變化後使用)
CREATE OR REPLACE FUNCTION rebuild_indexes()
RETURNS TABLE(
    status TEXT,
    execution_time_ms NUMERIC
) AS $$
DECLARE
    start_time TIMESTAMP;
    end_time TIMESTAMP;
BEGIN
    start_time := clock_timestamp();
    
    -- 重建 trigram 索引
    REINDEX INDEX idx_title_trgm;
    REINDEX INDEX idx_desc_trgm;
    
    end_time := clock_timestamp();
    
    -- 回傳結果
    RETURN QUERY SELECT 
        'Indexes rebuilt successfully'::TEXT,
        EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;
END;
$$ LANGUAGE plpgsql;
