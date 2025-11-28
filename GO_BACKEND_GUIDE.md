# Go Backend 使用指南

本專案現在支援兩種 backend 實作：
- **Node.js** (原版，port 3000)
- **Go** (新版，port 3001)

兩者功能完全相同，可以透過前端 UI 自由切換。

## 🚀 快速開始

### 1. 啟動所有服務

```bash
docker compose up -d --build
```

這會啟動三個服務：
- `postgres` - PostgreSQL 資料庫 (port 5432)
- `backend` - Node.js backend (port 3000)
- `backend-go` - Go backend (port 3001)

### 2. 檢查服務狀態

```bash
docker compose ps
```

應該看到三個服務都在運行：

```
NAME                    STATUS
pg_trgm_demo           Up (healthy)
pg_trgm_backend        Up
pg_trgm_backend_go     Up
```

### 3. 查看日誌

```bash
# 查看所有服務日誌
docker compose logs -f

# 只查看 Go backend 日誌
docker compose logs -f backend-go

# 只查看 Node.js backend 日誌
docker compose logs -f backend
```

### 4. 測試 API

使用提供的測試腳本：

```bash
./test_go_backend.sh
```

或手動測試：

```bash
# 測試 Node.js backend
curl http://localhost:3000/health
curl "http://localhost:3000/search?q=test"

# 測試 Go backend
curl http://localhost:3001/health
curl "http://localhost:3001/search?q=test"
```

## 🎨 前端切換功能

### 使用方式

1. 開啟瀏覽器訪問：
   - http://localhost:3000 (透過 Node.js backend)
   - http://localhost:3001 (透過 Go backend)

2. 在頁面上方找到 **Backend Toggle** 切換按鈕

3. 點擊切換按鈕在 Node.js 和 Go 之間切換

4. 當前使用的 backend 會顯示在右側（例如：「當前：Node.js (Port 3000)」）

### 功能特色

- ✅ **即時切換** - 點擊即可切換，無需重新載入頁面
- ✅ **自動重新搜尋** - 切換後會自動使用新 backend 重新執行當前搜尋
- ✅ **記憶選擇** - 使用 localStorage 保存您的選擇
- ✅ **視覺回饋** - 清楚顯示當前使用的 backend 和 port

## 📊 效能比較

您可以使用切換功能來比較兩個 backend 的效能：

1. 在搜尋框輸入查詢
2. 觀察查詢時間（顯示在搜尋結果下方）
3. 切換到另一個 backend
4. 比較兩者的查詢時間

一般來說，Go backend 會有稍微更好的效能和更低的記憶體使用。

## 🛠️ 開發模式

### 本地開發 Go Backend

如果您想在本地開發 Go backend（不使用 Docker）：

```bash
cd backend-go

# 設定環境變數
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=testdb
export DB_USER=postgres
export DB_PASSWORD=password
export PORT=3001

# 執行
go run main.go
```

### 本地開發 Node.js Backend

```bash
cd backend

# 安裝依賴（首次）
npm install

# 設定環境變數
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=testdb
export DB_USER=postgres
export DB_PASSWORD=password

# 執行
node server.js
```

## 🔧 故障排解

### Go Backend 無法啟動

1. 檢查日誌：
```bash
docker compose logs backend-go
```

2. 確認 PostgreSQL 已啟動：
```bash
docker compose ps postgres
```

3. 重新建置：
```bash
docker compose up -d --build backend-go
```

### 前端無法切換 Backend

1. 確認兩個 backend 都在運行
2. 開啟瀏覽器開發者工具檢查 Console 錯誤
3. 清除瀏覽器快取和 localStorage

### Port 衝突

如果 port 3001 被佔用，修改 `docker-compose.yml`：

```yaml
backend-go:
  ports:
    - "3002:3001"  # 改用 3002
```

然後更新前端的 `backendConfig`（在 `frontend/index.html`）：

```javascript
go: {
    baseUrl: 'http://localhost:3002',
    label: 'Go (Port 3002)'
}
```

## 📚 技術細節

### Go Backend 技術堆疊
- Go 1.21
- Gin Web Framework
- GORM ORM
- PostgreSQL Driver

### 專案結構
```
backend-go/
├── main.go           # 主程式
├── config/           # 資料庫配置
├── models/           # 資料模型
├── handlers/         # API 處理函數
└── Dockerfile        # Docker 配置
```

### API 端點對照

| 端點 | Node.js | Go | 說明 |
|------|---------|-----|------|
| Health Check | :3000/health | :3001/health | 健康檢查 |
| Search | :3000/search | :3001/search | 模糊搜尋 |
| Stats | :3000/admin/data/stats | :3001/admin/data/stats | 資料統計 |
| Generate | :3000/admin/data/generate | :3001/admin/data/generate | 產生資料 |
| Clear | :3000/admin/data/clear | :3001/admin/data/clear | 清空資料 |
| Rebuild | :3000/admin/data/rebuild-indexes | :3001/admin/data/rebuild-indexes | 重建索引 |

## 🎯 下一步

- 嘗試在不同 backend 之間切換
- 比較效能差異
- 測試所有管理功能
- 產生大量資料並測試搜尋效能

## 📖 相關文件

- [Go Backend README](backend-go/README.md) - Go backend 詳細說明
- [主要 README](README.md) - 專案整體說明
- [效能測試指南](docs/PERFORMANCE_TEST_QUICKSTART.md) - 效能測試說明

