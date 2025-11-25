# pg_trgm Fuzzy Search Demo

完整的 PostgreSQL pg_trgm 模糊搜尋示範專案，包含資料爬取、後端 API 和前端介面。

## 🚀 快速開始

### 前置需求

- Docker 與 Docker Compose
- Python 3.x（含 pip，用於資料填充）

### 1. 啟動所有服務（資料庫 + 後端）

```bash
docker compose up -d --build
```

這會自動啟動：
- PostgreSQL 16 資料庫（port 5432）
- Express.js 後端伺服器（port 3000）

等待約 10-15 秒讓所有服務完全啟動。

### 2. 安裝 Python 依賴並執行資料填充

```bash
pip3 install -r requirements.txt
python3 seed.py
```

> **重要！** 執行 seed.py 前，請確保你沒有本機的 PostgreSQL 服務在 port 5432 運行，否則會連接到錯誤的資料庫。

此腳本會使用多種策略抓取資料：
1. 從多個主題分類（50+ 主題）使用分頁抓取
2. 從熱門作者的作品集抓取
3. 從不同年代的出版品抓取

**預期會插入約 10,000 筆書籍資料**（執行時間約 5-10 分鐘）。

### 3. 開啟瀏覽器測試

在瀏覽器開啟 http://localhost:3000，你會看到一個搜尋介面。

試著輸入以下關鍵字測試模糊搜尋：
- `dracula` → Dracula
- `dune` → Dune
- `hobbit` → The Hobbit
- `foundation` → Foundation

## 📁 專案結構

```
.
├── docker-compose.yml      # Docker Compose 配置（PostgreSQL + Backend）
├── init.sql                # 資料庫初始化（建立 pg_trgm extension 與 table）
├── requirements.txt        # Python 依賴清單
├── seed.py                 # 資料爬取與填充腳本
├── backend/
│   ├── Dockerfile          # Backend Docker 映像配置
│   ├── package.json        # Node.js 依賴
│   └── server.js           # Express.js API 伺服器
└── frontend/
    └── index.html          # 搜尋介面
```

## 🔍 模糊搜尋機制

本專案實作了三種模糊搜尋方式：

1. **Prefix Autocomplete（前綴匹配）**
   - 使用 `title ILIKE $1 || '%'`
   - 最高優先級（sim + 0.5）
   - 適合自動完成功能

2. **Contains Keyword（包含關鍵字）**
   - 使用 `title ILIKE '%' || $1 || '%'`
   - 中等優先級（sim + 0.3）
   - 適合部分匹配

3. **Fuzzy Similarity（相似度排序）**
   - 使用 `title % $1` (pg_trgm 相似度運算子)
   - 基礎優先級（原始 similarity）
   - 適合拼字錯誤容錯

所有結果會根據相似度分數排序後回傳前 20 筆。

## 🛠️ API 端點

### GET /search?q={query}

搜尋書籍。

**參數：**
- `q`: 搜尋關鍵字

**回應範例：**
```json
[
  {
    "title": "Harry Potter and the Philosopher's Stone",
    "description": "Harry Potter is a series of seven fantasy novels...",
    "similarity": 0.856,
    "matchType": "prefix"
  }
]
```

### GET /health

檢查伺服器與資料庫狀態。

**使用方式：**
```bash
curl http://localhost:3000/health
```

**回應範例：**
```json
{
  "status": "ok",
  "database": "connected",
  "records": 9628
}
```

## 🎨 前端功能

- ✅ 即時搜尋（300ms debounce）
- ✅ 相似度分數顯示
- ✅ 匹配類型標記（Prefix / Contains / Fuzzy）
- ✅ 現代化漸層 UI 設計
- ✅ 響應式動畫效果

## 📦 技術堆疊

- **資料庫**: PostgreSQL 16 + pg_trgm extension
- **後端**: Express.js + node-postgres
- **前端**: Vanilla HTML/CSS/JavaScript
- **資料來源**: Wikipedia + OpenLibrary API
- **容器化**: Docker Compose

## 🧪 測試建議

1. 測試完全匹配：輸入完整書名
2. 測試部分匹配：輸入書名的一部分
3. 測試拼字錯誤：例如 "harrypotter"（沒有空格）
4. 測試相似詞：例如 "fantastic" 可能找到 "fantasy" 相關書籍

## ⚠️ 注意事項

- seed.py 會清空現有資料後重新插入
- 爬蟲腳本包含延遲（0.3-0.5 秒）以避免對目標網站造成負擔
- 確保 5432 port 未被佔用
- 首次執行 `npm install` 需要一些時間下載依賴

## 🔧 故障排除

### 無法連接資料庫
```bash
# 檢查容器狀態
docker ps

# 檢查資料庫 log
docker logs pg_trgm_demo
```

### seed.py 失敗
- 檢查網路連線
- 確認 PostgreSQL 已啟動
- 確認已安裝所有 Python 依賴

### 前端無結果
- 開啟瀏覽器 DevTools Console 查看錯誤
- 確認後端伺服器正在運行（`docker compose ps` 查看狀態）
- 訪問 http://localhost:3000/health 檢查狀態

### Port 衝突
如果你的 port 5432 或 3000 被佔用：
```bash
# 檢查 port 使用情況
lsof -i :5432
lsof -i :3000

# 修改 docker-compose.yml 中的端口映射
```

## 📄 授權

MIT License
