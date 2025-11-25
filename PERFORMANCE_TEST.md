# pg_trgm 效能測試指南

本文件說明如何測試不同資料量對 pg_trgm 模糊搜尋效能的影響。

## 📋 目錄

- [快速開始](#快速開始)
- [測試工具](#測試工具)
- [手動測試](#手動測試)
- [自動化測試](#自動化測試)
- [測試場景](#測試場景)
- [效能指標](#效能指標)
- [結果分析](#結果分析)

## 🚀 快速開始

### 前置需求

1. **服務運行中**
   ```bash
   docker compose up -d
   ```

2. **安裝 k6** (負載測試工具)
   ```bash
   # macOS
   brew install k6
   
   # Linux (Debian/Ubuntu)
   sudo gpg -k
   sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
     --keyserver hkp://keyserver.ubuntu.com:80 \
     --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
   echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | \
     sudo tee /etc/apt/sources.list.d/k6.list
   sudo apt-get update
   sudo apt-get install k6
   
   # Windows
   choco install k6
   ```

3. **驗證安裝**
   ```bash
   k6 version
   ```

### 一鍵自動化測試

```bash
# 賦予執行權限
chmod +x scripts/run-performance-tests.sh

# 執行測試 (預設: 1萬、5萬、10萬筆)
./scripts/run-performance-tests.sh
```

測試完成後會產生報告於 `test-results/performance_report_*.md`

## 🛠️ 測試工具

### 1. SQL 腳本

位置: `scripts/generate_test_data.sql`

提供的 PostgreSQL 函數:
- `generate_test_data(count)` - 產生指定數量的測試資料
- `clear_all_data()` - 清空所有資料
- `get_data_stats()` - 取得資料統計
- `rebuild_indexes()` - 重建索引

### 2. 管理 API

後端提供以下管理端點:

#### 取得資料統計
```bash
curl http://localhost:3000/admin/data/stats
```

回應範例:
```json
{
  "success": true,
  "data": {
    "totalRecords": 10000,
    "tableSize": "1.2 MB",
    "indexSize": "896 kB",
    "totalSize": "2.1 MB"
  }
}
```

#### 產生測試資料
```bash
curl -X POST http://localhost:3000/admin/data/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 10000}'
```

回應範例:
```json
{
  "success": true,
  "data": {
    "insertedCount": 10000,
    "executionTimeMs": 1234.56
  }
}
```

#### 清空資料
```bash
curl -X DELETE http://localhost:3000/admin/data/clear
```

#### 重建索引
```bash
curl -X POST http://localhost:3000/admin/data/rebuild-indexes
```

### 3. k6 負載測試腳本

位置: `k6-tests/search-performance.js`

支援多種測試場景 (詳見[測試場景](#測試場景))

## 📝 手動測試

### 步驟 1: 產生測試資料

使用 API 產生資料:

```bash
# 產生 1 萬筆
curl -X POST http://localhost:3000/admin/data/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 10000}'

# 產生 5 萬筆
curl -X POST http://localhost:3000/admin/data/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 50000}'

# 產生 10 萬筆
curl -X POST http://localhost:3000/admin/data/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 100000}'
```

或使用 SQL:

```bash
docker exec -it pg_trgm_demo psql -U postgres -d testdb -c "SELECT * FROM generate_test_data(10000);"
```

### 步驟 2: 執行 k6 測試

```bash
# 基本負載測試 (10 使用者, 2 分鐘)
k6 run k6-tests/search-performance.js

# Smoke test (1 使用者, 30 秒)
k6 run -e SCENARIO=smoke k6-tests/search-performance.js

# Stress test (最高 50 使用者)
k6 run -e SCENARIO=stress k6-tests/search-performance.js

# Spike test (突然 100 使用者)
k6 run -e SCENARIO=spike k6-tests/search-performance.js
```

### 步驟 3: 清空資料並重複測試

```bash
# 清空資料
curl -X DELETE http://localhost:3000/admin/data/clear

# 產生不同數量的資料並重新測試
curl -X POST http://localhost:3000/admin/data/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 50000}'

k6 run k6-tests/search-performance.js
```

## 🤖 自動化測試

自動化腳本會依序測試 1萬、5萬、10萬筆資料，並產生完整報告。

### 基本用法

```bash
./scripts/run-performance-tests.sh
```

### 自訂配置

```bash
# 自訂測試場景
K6_SCENARIO=stress ./scripts/run-performance-tests.sh

# 自訂目標 URL
BASE_URL=http://your-server:3000 ./scripts/run-performance-tests.sh

# 組合使用
K6_SCENARIO=spike BASE_URL=http://localhost:3000 ./scripts/run-performance-tests.sh
```

### 修改測試資料量

編輯 `scripts/run-performance-tests.sh`:

```bash
# 找到這一行並修改
DATA_VOLUMES=(10000 50000 100000)

# 例如測試更大的資料量
DATA_VOLUMES=(10000 50000 100000 200000 500000)
```

## 🎯 測試場景

k6 腳本支援以下測試場景:

### 1. Smoke Test (煙霧測試)
- **目的:** 驗證系統基本功能
- **配置:** 1 使用者, 30 秒
- **用法:** `k6 run -e SCENARIO=smoke k6-tests/search-performance.js`

### 2. Load Test (負載測試) - 預設
- **目的:** 測試正常負載下的效能
- **配置:** 10 使用者, 2 分鐘
- **用法:** `k6 run k6-tests/search-performance.js`

### 3. Stress Test (壓力測試)
- **目的:** 找出系統極限
- **配置:** 逐步增加到 50 使用者
- **用法:** `k6 run -e SCENARIO=stress k6-tests/search-performance.js`

### 4. Spike Test (尖峰測試)
- **目的:** 測試突然流量暴增
- **配置:** 突然 100 使用者, 持續 30 秒
- **用法:** `k6 run -e SCENARIO=spike k6-tests/search-performance.js`

## 📊 效能指標

### k6 輸出指標

執行 k6 測試後會看到以下關鍵指標:

```
http_req_duration.............: avg=45ms  min=12ms med=38ms max=250ms p(90)=85ms p(95)=120ms
http_req_failed...............: 0.00%
iterations....................: 1234
vus...........................: 10
```

**關鍵指標說明:**

- **http_req_duration**: HTTP 請求時間
  - `avg`: 平均回應時間
  - `p(95)`: 95% 的請求在此時間內完成
  - `p(99)`: 99% 的請求在此時間內完成
  
- **http_req_failed**: 失敗率 (應該 < 1%)

- **iterations**: 完成的請求總數

- **vus**: 虛擬使用者數量

### 搜尋 API 回應格式

搜尋 API 現在會回傳查詢時間:

```json
{
  "results": [...],
  "meta": {
    "queryTimeMs": 45,
    "resultCount": 20,
    "query": "test"
  }
}
```

## 📈 結果分析

### 預期效能基準

以下是參考基準 (實際結果會因硬體而異):

| 資料量 | 表格大小 | 索引大小 | p95 回應時間 | p99 回應時間 |
|--------|----------|----------|--------------|--------------|
| 1 萬   | ~1 MB    | ~800 KB  | < 50ms       | < 100ms      |
| 5 萬   | ~5 MB    | ~4 MB    | < 100ms      | < 200ms      |
| 10 萬  | ~10 MB   | ~8 MB    | < 150ms      | < 300ms      |
| 20 萬  | ~20 MB   | ~16 MB   | < 250ms      | < 500ms      |
| 50 萬  | ~50 MB   | ~40 MB   | < 500ms      | < 1000ms     |

### 分析重點

1. **線性擴展性**
   - 資料量增加時，查詢時間是否線性增長?
   - 索引大小與資料量的關係

2. **索引效果**
   - 有索引 vs 無索引的效能差異
   - GIN trigram 索引的效率

3. **並發效能**
   - 多使用者同時搜尋時的效能表現
   - 資料庫連線池的影響

4. **查詢類型**
   - 前綴搜尋 (prefix) vs 模糊搜尋 (fuzzy)
   - 短查詢 vs 長查詢

## 🔍 進階測試

### 1. 測試不同查詢類型

修改 `k6-tests/search-performance.js` 中的 `searchQueries` 陣列:

```javascript
const searchQueries = [
  'a',           // 極短查詢
  'abc',         // 短查詢
  'abcdefgh',    // 長查詢
  '12345',       // 純數字
];
```

### 2. 測試更大的資料量

```bash
# 產生 20 萬筆
curl -X POST http://localhost:3000/admin/data/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 200000}'

# 產生 50 萬筆
curl -X POST http://localhost:3000/admin/data/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 500000}'

# 產生 100 萬筆
curl -X POST http://localhost:3000/admin/data/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 1000000}'
```

### 3. 使用 EXPLAIN ANALYZE

直接在資料庫中分析查詢計畫:

```sql
EXPLAIN ANALYZE
SELECT id, title, description
FROM worlds
WHERE title % 'test'
LIMIT 20;
```

### 4. 輸出 k6 結果到檔案

```bash
# JSON 格式
k6 run --out json=results.json k6-tests/search-performance.js

# CSV 格式
k6 run --out csv=results.csv k6-tests/search-performance.js
```

### 5. 整合 InfluxDB + Grafana

```bash
# 啟動 InfluxDB (需要 Docker)
docker run -d -p 8086:8086 influxdb:1.8

# 執行 k6 並輸出到 InfluxDB
k6 run --out influxdb=http://localhost:8086/k6 k6-tests/search-performance.js

# 在 Grafana 中視覺化結果
```

## 📝 測試結果記錄模板

### 測試環境

- **日期:** YYYY-MM-DD
- **硬體:** CPU / RAM / 磁碟類型
- **PostgreSQL 版本:** 16
- **資料庫配置:** 預設 / 調整過的參數

### 測試結果

#### 資料量: 10,000 筆

```
資料統計:
- 總筆數: 10,000
- 表格大小: 1.2 MB
- 索引大小: 896 kB
- 總大小: 2.1 MB

k6 測試結果 (Load Test):
- http_req_duration (avg): 45ms
- http_req_duration (p95): 85ms
- http_req_duration (p99): 120ms
- http_req_failed: 0.00%
- iterations: 1234
```

#### 資料量: 50,000 筆

```
(填入測試結果)
```

#### 資料量: 100,000 筆

```
(填入測試結果)
```

### 結論

(分析結果，找出效能瓶頸和優化建議)

## 🐛 疑難排解

### 問題 1: k6 測試失敗

**錯誤:** `Service is not available`

**解決方法:**
```bash
# 檢查服務狀態
curl http://localhost:3000/health

# 重啟服務
docker compose restart
```

### 問題 2: 產生資料太慢

**原因:** 大量資料插入時索引更新較慢

**解決方法:**
```sql
-- 暫時移除索引
DROP INDEX idx_title_trgm;
DROP INDEX idx_desc_trgm;

-- 插入資料
SELECT * FROM generate_test_data(1000000);

-- 重建索引
CREATE INDEX idx_title_trgm ON worlds USING gin (title gin_trgm_ops);
CREATE INDEX idx_desc_trgm ON worlds USING gin (description gin_trgm_ops);
```

### 問題 3: 記憶體不足

**解決方法:** 調整 PostgreSQL 記憶體設定

編輯 `docker-compose.yml`:
```yaml
postgres:
  command:
    - "postgres"
    - "-c"
    - "shared_buffers=256MB"
    - "-c"
    - "work_mem=16MB"
```

## 📚 參考資源

- [k6 官方文件](https://k6.io/docs/)
- [PostgreSQL pg_trgm 文件](https://www.postgresql.org/docs/current/pgtrgm.html)
- [GIN 索引說明](https://www.postgresql.org/docs/current/gin.html)
- [效能調校指南](https://wiki.postgresql.org/wiki/Performance_Optimization)

## 💡 最佳實踐

1. **測試前先清空資料** - 確保每次測試的起始狀態一致
2. **多次測試取平均** - 避免單次測試的偶然誤差
3. **記錄環境資訊** - 方便日後比較和重現
4. **監控系統資源** - 觀察 CPU、記憶體、磁碟 I/O
5. **逐步增加負載** - 從小資料量開始，逐步增加

## 🎓 下一步

- 嘗試不同的 PostgreSQL 配置參數
- 測試不同的索引策略 (GIN vs GiST)
- 比較 pg_trgm 與其他搜尋方案 (Elasticsearch, Full-text search)
- 實作快取層 (Redis) 並比較效能

