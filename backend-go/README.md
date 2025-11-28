# Go Backend for pg_trgm Demo

這是使用 Go + Gin + GORM 實作的 backend，與 Node.js 版本功能完全相同。

## 技術堆疊

- **語言**: Go 1.21
- **Web 框架**: Gin
- **ORM**: GORM
- **資料庫**: PostgreSQL 16 + pg_trgm

## 專案結構

```
backend-go/
├── main.go              # 主程式入口
├── go.mod               # Go 模組依賴
├── Dockerfile           # Docker 映像配置
├── config/
│   └── database.go      # 資料庫連線配置
├── models/
│   └── world.go         # 資料模型
└── handlers/
    ├── health.go        # 健康檢查
    ├── search.go        # 搜尋功能
    └── admin.go         # 管理功能
```

## API 端點

### 核心功能
- `GET /health` - 健康檢查
- `GET /search?q={query}` - 模糊搜尋

### 管理功能
- `GET /admin/data/stats` - 取得資料統計
- `POST /admin/data/generate` - 產生測試資料
- `DELETE /admin/data/clear` - 清空所有資料
- `POST /admin/data/rebuild-indexes` - 重建索引

## 本地開發

### 前置需求
- Go 1.21+
- PostgreSQL 16

### 安裝依賴
```bash
cd backend-go
go mod download
```

### 執行
```bash
# 設定環境變數（可選）
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=testdb
export DB_USER=postgres
export DB_PASSWORD=password
export PORT=3001

# 執行
go run main.go
```

## Docker 部署

使用 docker-compose 啟動所有服務：

```bash
# 從專案根目錄
docker compose up -d --build
```

這會啟動：
- PostgreSQL (port 5432)
- Node.js Backend (port 3000)
- Go Backend (port 3001)

## 功能特色

### 模糊搜尋
實作四種匹配類型：
1. **Exact Prefix** - 精確前綴匹配（最高優先級）
2. **Similarity** - Trigram 相似度匹配（容錯）
3. **Word Similarity** - 詞彙相似度匹配
4. **Contains** - 包含匹配（較低優先級）

### 連線池管理
- 最大連線數：20
- 最大閒置連線：10
- 自動設定 pg_trgm 閾值

### CORS 支援
允許跨域請求，方便前端整合。

## 與 Node.js 版本的差異

### 相同點
- API 端點完全相同
- 回應格式一致
- 功能完全對等

### 優勢
- 更好的效能（編譯語言）
- 更低的記憶體使用
- 更簡單的部署（單一二進位檔）
- 強型別安全

## 測試

### 健康檢查
```bash
curl http://localhost:3001/health
```

### 搜尋測試
```bash
curl "http://localhost:3001/search?q=harry"
```

### 管理功能測試
```bash
# 取得統計
curl http://localhost:3001/admin/data/stats

# 產生測試資料
curl -X POST http://localhost:3001/admin/data/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 1000}'
```

## 前端整合

前端已經整合了 backend 切換功能：
1. 開啟 http://localhost:3000 或 http://localhost:3001
2. 使用頁面上方的 Toggle 按鈕切換 Node.js 或 Go backend
3. 切換時會自動重新執行當前搜尋
4. 選擇會保存在 localStorage

## 疑難排解

### 無法連接資料庫
- 確認 PostgreSQL 正在運行
- 檢查環境變數設定
- 查看 Docker logs: `docker logs pg_trgm_backend_go`

### Port 衝突
修改 docker-compose.yml 中的 port mapping 或設定 PORT 環境變數。

### 編譯錯誤
```bash
go mod tidy
go mod download
```

