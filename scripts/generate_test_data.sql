-- ============================================================================
-- 測試資料產生腳本
-- 用於快速產生大量測試資料,測試不同資料量對 pg_trgm 搜尋效能的影響
-- ============================================================================

-- 函數: 產生指定數量的測試資料
-- 使用 md5(random()::text) 產生隨機字串
-- 參數: record_count - 要產生的資料筆數
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

-- ============================================================================
-- 使用範例
-- ============================================================================

-- 產生 10,000 筆測試資料
-- SELECT * FROM generate_test_data(10000);

-- 產生 50,000 筆測試資料
-- SELECT * FROM generate_test_data(50000);

-- 產生 100,000 筆測試資料
-- SELECT * FROM generate_test_data(100000);

-- 清空所有資料
-- SELECT * FROM clear_all_data();

-- 取得資料統計
-- SELECT * FROM get_data_stats();

-- 重建索引
-- SELECT * FROM rebuild_indexes();

-- ============================================================================
-- 直接執行 SQL (不使用函數)
-- ============================================================================

-- 直接插入 10,000 筆
-- INSERT INTO worlds (title, description)
-- SELECT
--     md5(random()::text) AS title,
--     md5(random()::text) || ' ' || md5(random()::text) AS description
-- FROM generate_series(1, 10000);

-- 直接插入 50,000 筆
-- INSERT INTO worlds (title, description)
-- SELECT
--     md5(random()::text) AS title,
--     md5(random()::text) || ' ' || md5(random()::text) AS description
-- FROM generate_series(1, 50000);

-- 直接插入 100,000 筆
-- INSERT INTO worlds (title, description)
-- SELECT
--     md5(random()::text) AS title,
--     md5(random()::text) || ' ' || md5(random()::text) AS description
-- FROM generate_series(1, 100000);

