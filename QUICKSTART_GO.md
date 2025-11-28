# Go Backend 快速開始指南

## 🚀 5 分鐘快速啟動

### 1. 啟動所有服務

```bash
docker compose up -d --build
```

等待約 30 秒讓所有服務啟動完成。

### 2. 檢查服務狀態

```bash
docker compose ps
```

應該看到三個服務都在運行：
- ✅ `pg_trgm_demo` (PostgreSQL)
- ✅ `pg_trgm_backend` (Node.js)
- ✅ `pg_trgm_backend_go` (Go)

### 3. 測試 API

```bash
# 測試 Go backend
curl http://localhost:3001/health

# 測試 Node.js backend
curl http://localhost:3000/health
```

### 4. 開啟前端

在瀏覽器開啟：
- http://localhost:3000 (透過 Node.js)
- http://localhost:3001 (透過 Go)

### 5. 切換 Backend

在頁面上方找到 **Backend Toggle** 按鈕：
- 點擊 "Node.js" 使用 Node.js backend (port 3000)
- 點擊 "Go" 使用 Go backend (port 3001)

## 🎯 快速測試

### 測試搜尋功能

1. 確保有資料（如果沒有，請先產生）：
   - 點擊 "⚙️ 管理面板" → "顯示"
   - 點擊 "產生 1 萬筆" 按鈕

2. 在搜尋框輸入關鍵字，例如：
   - `quantum`
   - `neural`
   - `machine learning`

3. 切換 backend 並比較查詢時間

### 測試 Backend 切換

1. 在搜尋框輸入查詢
2. 觀察查詢時間
3. 點擊 Toggle 按鈕切換到另一個 backend
4. 觀察查詢是否自動重新執行
5. 比較兩個 backend 的效能

## 📊 效能比較

使用 Toggle 功能可以即時比較兩個 backend 的效能：

| 測試項目 | Node.js | Go |
|---------|---------|-----|
| 啟動時間 | ~2-3 秒 | ~1-2 秒 |
| 記憶體使用 | ~50-80 MB | ~20-40 MB |
| 查詢速度 | 快 | 更快 |

## 🛠️ 常用命令

```bash
# 啟動服務
docker compose up -d

# 停止服務
docker compose down

# 重新建置並啟動
docker compose up -d --build

# 查看日誌
docker compose logs -f

# 只查看 Go backend 日誌
docker compose logs -f backend-go

# 只查看 Node.js backend 日誌
docker compose logs -f backend

# 重啟特定服務
docker compose restart backend-go
```

## 🧪 API 測試

### 使用測試腳本

```bash
./test_go_backend.sh
```

### 手動測試

```bash
# Go Backend (port 3001)
curl http://localhost:3001/health
curl "http://localhost:3001/search?q=quantum"
curl http://localhost:3001/admin/data/stats

# Node.js Backend (port 3000)
curl http://localhost:3000/health
curl "http://localhost:3000/search?q=quantum"
curl http://localhost:3000/admin/data/stats
```

## 🔧 疑難排解

### 服務無法啟動

```bash
# 檢查 port 是否被佔用
lsof -i :3000
lsof -i :3001
lsof -i :5432

# 停止所有服務並重新啟動
docker compose down
docker compose up -d --build
```

### 前端無法連接

1. 確認服務都在運行：`docker compose ps`
2. 檢查瀏覽器 Console 是否有錯誤
3. 清除瀏覽器快取和 localStorage
4. 重新載入頁面

### 資料庫連線錯誤

```bash
# 檢查 PostgreSQL 日誌
docker compose logs postgres

# 重啟資料庫
docker compose restart postgres
```

## 📚 更多資訊

- [Go Backend 詳細說明](backend-go/README.md)
- [完整使用指南](GO_BACKEND_GUIDE.md)
- [實作完成報告](IMPLEMENTATION_COMPLETE_GO.md)
- [主要 README](README.md)

## 🎉 開始使用

現在您已經準備好了！

1. ✅ 服務已啟動
2. ✅ 前端可以訪問
3. ✅ 可以切換 backend
4. ✅ 可以測試搜尋

享受使用雙 backend 架構的 pg_trgm 模糊搜尋 Demo！

