# 疑難排解指南

本文件記錄常見問題和解決方案。

## 🐛 問題 1: k6 測試失敗 - "Service not ready (status: 400)"

### 症狀

```bash
INFO[0000] 🔍 Checking service health (attempt 1/5)...
INFO[0000] ⚠️  Service not ready (status: 400), waiting 3 seconds...
ERRO[0015] ❌ Service is not available after 5 attempts
```

但是手動測試卻正常:

```bash
$ curl http://localhost:3000/health
{"status":"ok","database":"connected","records":10000}
```

### 根本原因

**IPv4 vs IPv6 衝突**

- `localhost` 在你的系統上解析到 **IPv6 (::1)** → 連到 Docker 後端 ✅
- k6 預設使用 **IPv4 (127.0.0.1)** → 連到本機的其他服務 (如 nginx) ❌

驗證方式:

```bash
# 測試 IPv6 (正常)
curl http://[::1]:3000/health
# 回應: {"status":"ok",...}

# 測試 IPv4 (錯誤)
curl http://127.0.0.1:3000/health
# 回應: 400 The plain HTTP request was sent to HTTPS port
```

### 解決方案

**方案 1: 修改測試腳本使用 IPv6 (已實施)**

我們已經修改了:
- `k6-tests/search-performance.js`
- `scripts/run-performance-tests.sh`

使用 `http://[::1]:3000` 代替 `http://localhost:3000`

**方案 2: 停止佔用 3000 端口的其他服務**

```bash
# 查看誰在使用 3000 端口
lsof -i :3000

# 如果是 nginx
sudo nginx -s stop
# 或
sudo killall nginx
```

**方案 3: 修改 Docker 端口映射**

編輯 `docker-compose.yml`:

```yaml
backend:
  ports:
    - "3001:3000"  # 改用 3001
```

然後:

```bash
docker compose up -d --force-recreate backend
export BASE_URL=http://localhost:3001
./scripts/run-performance-tests.sh
```

---

## 🐛 問題 2: VACUUM 錯誤 - "cannot be executed from a function"

### 症狀

```
Clear error: VACUUM cannot be executed from a function
```

### 根本原因

PostgreSQL 的 `VACUUM` 指令不能在 PL/pgSQL 函數內執行。

### 解決方案

**已實施的修復:**

1. **SQL 函數**: 使用 `TRUNCATE` 代替 `DELETE` (更快且自動回收空間)
2. **後端 API**: 在函數外執行 `VACUUM ANALYZE`

```javascript
// 在 backend/server.js 中
await pool.query('SELECT * FROM clear_all_data()');  // TRUNCATE
await pool.query('VACUUM ANALYZE worlds');           // 回收空間
```

---

## 🐛 問題 3: 資料大小異常大

### 症狀

```
總筆數: 10000
表格大小: 181 MB    ← 異常!應該只有 1-2 MB
索引大小: 626 MB    ← 異常!應該只有 1 MB
```

### 根本原因

1. **未執行 VACUUM**: 刪除資料後空間未回收
2. **索引碎片化**: 大量插入/刪除導致索引膨脹

### 解決方案

**自動清理 (推薦)**

使用 API 清空資料,會自動執行 VACUUM:

```bash
curl -X DELETE http://localhost:3000/admin/data/clear
```

**手動清理**

```bash
# 方法 1: 標準 VACUUM
docker exec -it pg_trgm_demo psql -U postgres -d testdb -c "
DELETE FROM worlds;
VACUUM ANALYZE worlds;
"

# 方法 2: VACUUM FULL (完全重建,較慢但效果最好)
docker exec -it pg_trgm_demo psql -U postgres -d testdb -c "
DELETE FROM worlds;
VACUUM FULL ANALYZE worlds;
"

# 方法 3: TRUNCATE (最快,自動回收空間)
docker exec -it pg_trgm_demo psql -U postgres -d testdb -c "
TRUNCATE TABLE worlds;
"
```

---

## 🐛 問題 4: 前端產生資料失敗

### 症狀

網頁顯示:

```
❌ 產生資料失敗: Failed to generate data
```

### 可能原因

1. **SQL 函數未建立**
2. **後端服務未重啟**
3. **資料類型轉換錯誤**

### 解決方案

**執行設定腳本:**

```bash
chmod +x scripts/setup-performance-test.sh
./scripts/setup-performance-test.sh
```

這會:
1. ✅ 建立所有 SQL 函數
2. ✅ 重啟後端服務
3. ✅ 驗證服務正常

**手動修復:**

```bash
# 1. 建立 SQL 函數
docker exec -i pg_trgm_demo psql -U postgres -d testdb < scripts/generate_test_data.sql

# 2. 重啟後端
docker compose restart backend

# 3. 等待服務啟動
sleep 5

# 4. 驗證
curl http://localhost:3000/admin/data/stats
```

---

## 🐛 問題 5: Docker 容器無法啟動

### 症狀

```bash
docker compose up -d
# 容器啟動失敗或不斷重啟
```

### 檢查步驟

```bash
# 1. 查看容器狀態
docker compose ps

# 2. 查看後端日誌
docker logs pg_trgm_backend --tail 50

# 3. 查看資料庫日誌
docker logs pg_trgm_demo --tail 50

# 4. 檢查端口佔用
lsof -i :3000
lsof -i :5432
```

### 常見解決方案

**端口被佔用:**

```bash
# 停止佔用端口的服務
sudo lsof -ti:3000 | xargs kill -9
sudo lsof -ti:5432 | xargs kill -9

# 重啟 Docker 服務
docker compose down
docker compose up -d
```

**資料庫初始化失敗:**

```bash
# 完全清理並重建
docker compose down -v  # 刪除 volumes
docker compose up -d --build
```

---

## 📋 健康檢查清單

執行測試前,確認以下項目:

- [ ] Docker 服務運行中: `docker compose ps`
- [ ] 後端健康: `curl http://[::1]:3000/health`
- [ ] SQL 函數已建立: `./scripts/setup-performance-test.sh`
- [ ] k6 已安裝: `k6 version`
- [ ] 沒有端口衝突: `lsof -i :3000`
- [ ] 資料庫可連接: `docker exec pg_trgm_demo psql -U postgres -d testdb -c "SELECT 1"`
- [ ] 索引已建立: `docker exec pg_trgm_demo psql -U postgres -d testdb -c "\d worlds"`

---

## 🆘 快速修復指令

```bash
# 完整重置
docker compose down -v
docker compose up -d --build
sleep 10
./scripts/setup-performance-test.sh

# 清空資料並重新測試
curl -X DELETE http://[::1]:3000/admin/data/clear
./scripts/run-performance-tests.sh

# 檢查服務狀態
curl http://[::1]:3000/health
curl http://[::1]:3000/admin/data/stats
```

---

## 📞 需要更多幫助?

1. 查看日誌: `docker logs pg_trgm_backend --tail 100`
2. 查看測試報告: `cat test-results/performance_report_*.md`
3. 檢查文件: `PERFORMANCE_TEST.md`, `PERFORMANCE_TEST_QUICKSTART.md`

