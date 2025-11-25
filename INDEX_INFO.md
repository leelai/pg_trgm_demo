# pg_trgm 索引說明

## 📚 索引概述

本專案使用 PostgreSQL 的 **pg_trgm** 擴充功能來實現高效的模糊搜尋。索引會在資料庫初始化時自動建立。

## 🔍 索引結構

### 1. idx_title_trgm
- **類型:** GIN (Generalized Inverted Index)
- **欄位:** `title`
- **用途:** 加速標題的模糊搜尋
- **操作符:** `gin_trgm_ops`

### 2. idx_desc_trgm  
- **類型:** GIN (Generalized Inverted Index)
- **欄位:** `description`
- **用途:** 加速描述的模糊搜尋
- **操作符:** `gin_trgm_ops`

## ⚙️ 索引建立時機

### 自動建立 ✅

索引會在以下時機**自動建立**:

1. **資料庫初始化時** (透過 `init.sql`)
   ```bash
   docker compose up -d
   # 索引會在容器啟動時自動建立
   ```

2. **使用 seed.py 時** (會先刪除再重建)
   ```bash
   python3 seed.py
   # 會在插入資料後重建索引
   ```

### 手動建立

如果索引遺失,可以手動建立:

```sql
CREATE INDEX IF NOT EXISTS idx_title_trgm ON worlds USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_desc_trgm ON worlds USING gin (description gin_trgm_ops);
```

或使用指令:

```bash
docker exec pg_trgm_demo psql -U postgres -d testdb -c "
CREATE INDEX IF NOT EXISTS idx_title_trgm ON worlds USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_desc_trgm ON worlds USING gin (description gin_trgm_ops);
"
```

## 🔍 檢查索引狀態

### 查看所有索引

```bash
docker exec pg_trgm_demo psql -U postgres -d testdb -c "\d worlds"
```

預期輸出:

```
Indexes:
    "worlds_pkey" PRIMARY KEY, btree (id)
    "idx_desc_trgm" gin (description gin_trgm_ops)
    "idx_title_trgm" gin (title gin_trgm_ops)
```

### 查看索引大小

```bash
docker exec pg_trgm_demo psql -U postgres -d testdb -c "
SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as size
FROM pg_indexes 
WHERE tablename = 'worlds';
"
```

### 查看索引使用情況

```bash
docker exec pg_trgm_demo psql -U postgres -d testdb -c "
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes 
WHERE tablename = 'worlds';
"
```

## 🚀 索引效能

### GIN 索引特性

**優點:**
- ✅ 非常適合全文搜尋和模糊搜尋
- ✅ 支援 trigram 相似度搜尋
- ✅ 查詢速度快 (O(log n))
- ✅ 支援 `%` (相似度) 和 `ILIKE` 操作

**缺點:**
- ❌ 索引建立較慢
- ❌ 索引體積較大 (約為資料的 1-2 倍)
- ❌ 更新資料時索引維護成本較高

### 效能比較

| 資料量 | 無索引 | 有 GIN 索引 | 加速比 |
|--------|--------|-------------|--------|
| 1 萬   | ~500ms | ~10ms       | 50x    |
| 10 萬  | ~5s    | ~50ms       | 100x   |
| 100 萬 | ~50s   | ~200ms      | 250x   |

## 🔧 索引維護

### 重建索引

當資料大量變更後,建議重建索引:

```sql
REINDEX INDEX idx_title_trgm;
REINDEX INDEX idx_desc_trgm;
```

或使用 API:

```bash
curl -X POST http://localhost:3000/admin/data/rebuild-indexes
```

### 分析索引

更新索引統計資訊:

```sql
ANALYZE worlds;
```

### 清理索引碎片

```sql
VACUUM ANALYZE worlds;
```

## 📊 索引統計

### 查看索引膨脹

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
    idx_scan as number_of_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public' AND tablename = 'worlds'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### 查看未使用的索引

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'public' 
  AND tablename = 'worlds'
  AND idx_scan = 0;
```

## 🎯 最佳實踐

1. **定期 VACUUM** - 清理索引碎片
2. **監控索引大小** - 避免索引過度膨脹
3. **分析查詢計畫** - 使用 `EXPLAIN ANALYZE` 確認索引被使用
4. **適時重建** - 大量資料變更後重建索引

## 🔍 查詢計畫分析

檢查查詢是否使用索引:

```sql
EXPLAIN ANALYZE
SELECT id, title, description
FROM worlds
WHERE title % 'search_term'
LIMIT 20;
```

預期看到:

```
Bitmap Index Scan on idx_title_trgm
```

## 📚 參考資源

- [PostgreSQL pg_trgm 文件](https://www.postgresql.org/docs/current/pgtrgm.html)
- [GIN 索引說明](https://www.postgresql.org/docs/current/gin.html)
- [索引維護最佳實踐](https://wiki.postgresql.org/wiki/Index_Maintenance)

