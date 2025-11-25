# 效能測試快速開始指南

本指南幫助你快速開始測試不同資料量對 pg_trgm 搜尋效能的影響。

## 🎯 目標

測試 1萬、5萬、10萬筆資料對搜尋效能的影響,並使用 k6 進行專業負載測試。

## 🚀 快速開始 (4 步驟)

### 步驟 1: 啟動服務

```bash
docker compose up -d
```

等待約 10 秒讓服務完全啟動。

### 步驟 2: 初始化效能測試系統

```bash
# 賦予執行權限
chmod +x scripts/setup-performance-test.sh

# 執行設定腳本 (建立 SQL 函數並重啟後端)
./scripts/setup-performance-test.sh
```

這個腳本會:
- ✅ 在資料庫中建立 SQL 函數
- ✅ 重啟後端服務載入新的 API
- ✅ 驗證所有服務正常運作

### 步驟 3: 安裝 k6

```bash
# macOS
brew install k6

# Linux
sudo apt-get install k6

# Windows
choco install k6
```

### 步驟 4: 執行自動化測試

```bash
# 賦予執行權限
chmod +x scripts/run-performance-tests.sh

# 執行測試
./scripts/run-performance-tests.sh
```

測試將自動:
1. 產生 1 萬筆資料 → 執行 k6 測試
2. 產生 5 萬筆資料 → 執行 k6 測試
3. 產生 10 萬筆資料 → 執行 k6 測試
4. 產生效能比較報告

## 📊 查看結果

測試完成後:

```bash
# 查看報告
cat test-results/performance_report_*.md

# 查看最新報告
ls -lt test-results/performance_report_*.md | head -1 | awk '{print $9}' | xargs cat
```

## 🎨 使用前端管理面板

開啟瀏覽器訪問 http://localhost:3000

1. 點擊 **"⚙️ 管理面板"** 的 **"顯示"** 按鈕
2. 查看當前資料統計
3. 點擊 **"產生 1 萬筆"** / **"產生 5 萬筆"** / **"產生 10 萬筆"**
4. 在搜尋框輸入關鍵字測試搜尋效能
5. 觀察回應時間 (顯示在搜尋結果統計中)

## 🔧 手動測試 (使用 API)

### 產生測試資料

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

### 執行 k6 測試

```bash
# Load test (10 使用者, 2 分鐘)
k6 run k6-tests/search-performance.js

# Smoke test (1 使用者, 30 秒)
k6 run -e SCENARIO=smoke k6-tests/search-performance.js

# Stress test (最高 50 使用者)
k6 run -e SCENARIO=stress k6-tests/search-performance.js
```

### 查看統計

```bash
curl http://localhost:3000/admin/data/stats | jq
```

### 清空資料

```bash
curl -X DELETE http://localhost:3000/admin/data/clear
```

## 📈 預期結果

| 資料量 | 產生時間 | p95 回應時間 | p99 回應時間 |
|--------|----------|--------------|--------------|
| 1 萬   | ~1-2 秒  | < 50ms       | < 100ms      |
| 5 萬   | ~5-8 秒  | < 100ms      | < 200ms      |
| 10 萬  | ~10-15秒 | < 150ms      | < 300ms      |

*實際結果會因硬體配置而異*

## 🎯 測試場景

### 1. Smoke Test (煙霧測試)
```bash
k6 run -e SCENARIO=smoke k6-tests/search-performance.js
```
- 1 使用者, 30 秒
- 驗證基本功能

### 2. Load Test (負載測試) - 預設
```bash
k6 run k6-tests/search-performance.js
```
- 10 使用者, 2 分鐘
- 測試正常負載

### 3. Stress Test (壓力測試)
```bash
k6 run -e SCENARIO=stress k6-tests/search-performance.js
```
- 逐步增加到 50 使用者
- 找出系統極限

### 4. Spike Test (尖峰測試)
```bash
k6 run -e SCENARIO=spike k6-tests/search-performance.js
```
- 突然 100 使用者
- 測試突發流量

## 🔍 關鍵指標說明

k6 測試輸出的關鍵指標:

```
✓ http_req_duration.............: avg=45ms  p(95)=85ms  p(99)=120ms
✓ http_req_failed...............: 0.00%
✓ iterations....................: 1234
```

- **http_req_duration**: HTTP 請求時間
  - `avg`: 平均回應時間
  - `p(95)`: 95% 的請求在此時間內完成
  - `p(99)`: 99% 的請求在此時間內完成
- **http_req_failed**: 失敗率 (應該 < 1%)
- **iterations**: 完成的請求總數

## 📝 測試建議

1. **從小資料量開始** - 先測試 1 萬筆,確認系統正常
2. **逐步增加** - 依序測試 1萬 → 5萬 → 10萬
3. **觀察趨勢** - 記錄每個資料量級別的效能指標
4. **多次測試** - 每個級別測試 2-3 次取平均值
5. **清空資料** - 每次測試前清空舊資料,確保乾淨的測試環境

## 🐛 疑難排解

### 問題: 服務未運行
```bash
# 檢查服務狀態
docker compose ps

# 重啟服務
docker compose restart
```

### 問題: k6 未安裝
```bash
# 驗證安裝
k6 version

# macOS 安裝
brew install k6
```

### 問題: 產生資料太慢
對於大量資料 (> 10萬筆),可以使用 SQL 直接插入:

```bash
docker exec -it pg_trgm_demo psql -U postgres -d testdb -c "
INSERT INTO worlds (title, description)
SELECT
    md5(random()::text) AS title,
    md5(random()::text) || ' ' || md5(random()::text) AS description
FROM generate_series(1, 100000);
"
```

## 📚 完整文件

詳細說明請參考:
- [PERFORMANCE_TEST.md](./PERFORMANCE_TEST.md) - 完整效能測試指南
- [README.md](./README.md) - 專案說明文件

## 💡 提示

- 使用前端管理面板可以更直觀地管理測試資料
- 搜尋 API 現在會回傳查詢時間 (`queryTimeMs`)
- 自動化腳本會產生詳細的測試報告
- 可以自訂測試資料量,修改 `scripts/run-performance-tests.sh` 中的 `DATA_VOLUMES` 陣列

