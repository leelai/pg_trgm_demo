# pg_trgm Fuzzy Search Demo

完整的 PostgreSQL pg_trgm 模糊搜尋示範專案，包含資料爬取、後端 API、前端介面和**效能測試系統**。

## 🆕 新功能: 效能測試系統

測試不同資料量對搜尋效能的影響，使用 k6 進行專業負載測試。

**快速開始:**
```bash
# 安裝 k6
brew install k6  # macOS

# 執行自動化測試 (測試 1萬、5萬、10萬筆)
chmod +x scripts/run-performance-tests.sh
./scripts/run-performance-tests.sh
```

**或使用前端管理面板:**
- 開啟 http://localhost:3000
- 點擊 "⚙️ 管理面板" → "顯示"
- 一鍵產生測試資料並查看統計

**詳細說明:**
- 📖 [效能測試快速指南](./PERFORMANCE_TEST_QUICKSTART.md)
- 📚 [完整效能測試文件](./PERFORMANCE_TEST.md)
- 📋 [實作總結](./IMPLEMENTATION_SUMMARY.md)
- 🔍 [索引說明文件](./INDEX_INFO.md)
- 🐛 [疑難排解指南](./TROUBLESHOOTING.md)

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
# 建立虛擬環境（建議）
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安裝依賴
pip3 install -r requirements.txt

# 執行資料填充（預設 10,000 筆）
python3 seed.py
```

> **重要！** 執行 seed.py 前，請確保你沒有本機的 PostgreSQL 服務在 port 5432 運行，否則會連接到錯誤的資料庫。

#### 資料來源策略

此腳本會從**六個**高品質來源抓取資料：
1. **ArXiv 學術論文** (25%) - 電腦科學、物理、數學等領域的學術摘要
2. **Wikipedia 條目** (25%) - 各種主題的百科全書條目
3. **Google Books** (20%) - 各類書籍的詳細簡介
4. **Quotable.io 名言** (15%) - 名人勵志名言 🆕
5. **UselessFacts 冷知識** (10%) - 有趣的隨機事實 🆕
6. **ZenQuotes 名言** (5%) - 額外的名言來源 🆕

#### 命令列參數

`seed.py` 支援靈活的參數配置，無需修改程式碼：

```bash
# 查看所有參數說明
python3 seed.py --help

# 抓取 10,000 筆資料（預設）
python3 seed.py

# 抓取 1,000 筆資料（快速測試）
python3 seed.py --total 1000

# 抓取 100 筆資料（極速測試）
python3 seed.py --total 100

# 自訂各來源數量（完整配置）
python3 seed.py --arxiv 2500 --wikipedia 2500 --books 2000 \
                --quotable 1500 --facts 1000 --zenquotes 500

# 只抓取名言和冷知識（適合短文測試）
python3 seed.py --quotable 500 --facts 500 --zenquotes 100 \
                --arxiv 0 --wikipedia 0 --books 0

# 只抓取 ArXiv 論文（適合學術領域測試）
python3 seed.py --arxiv 5000 --wikipedia 0 --books 0

# 只抓取 Wikipedia 條目（適合百科內容測試）
python3 seed.py --arxiv 0 --wikipedia 5000 --books 0

# 使用非並行模式（依序抓取，較慢但更穩定）
python3 seed.py --no-parallel

# 使用非並行模式抓取 1000 筆
python3 seed.py --total 1000 --no-parallel

# 跳過 Wikipedia 暢銷書清單
python3 seed.py --skip-wiki-bestsellers
```

**預設會插入約 10,000 筆資料**（執行時間約 25-30 分鐘，包含新增的名言和冷知識來源）。使用 `--total 1000` 可縮短至約 3-5 分鐘。

#### 新增資料來源 🆕

為了增加資料多樣性和測試覆蓋範圍，我們新增了三個免費公開 API：

**1. Quotable.io - 名人名言**
- 提供高品質的勵志名言和哲理語錄
- 包含作者資訊
- 內容簡短（平均 50-100 字元），適合測試短文搜尋
- 免費，無需 API key

**2. UselessFacts - 有趣冷知識**
- 提供各種有趣的隨機事實和冷知識
- 內容多樣化，涵蓋科學、歷史、娛樂等領域
- 文字長度適中（平均 50-100 字元）
- 免費，無需 API key

**3. ZenQuotes - 額外名言來源**
- 補充的名言來源，提供更多元的引言內容
- 品質優良但有 rate limit（每 30 秒 5 次請求）
- 適合少量使用
- 免費，無需 API key

**資料長度分布**：
- 短文（20-100 字元）：Quotable、UselessFacts、ZenQuotes
- 中文（100-300 字元）：Google Books、Wikipedia 摘要
- 長文（300+ 字元）：ArXiv 學術論文

這樣的組合可以更全面地測試 pg_trgm 在不同長度和類型文字上的模糊搜尋效果。

#### 執行模式選擇 🆕

`seed.py` 支援兩種執行模式：

**1. 並行模式（預設，推薦）**
```bash
python3 seed.py --total 1000
# 或明確指定
python3 seed.py --total 1000 --parallel
```
- ⚡ **速度快**：所有資料來源同時抓取
- 🚀 **效率高**：充分利用網路頻寬
- ⏱️ **時間短**：10,000 筆約 25-30 分鐘
- 📊 **適用場景**：網路穩定、一般使用

**2. 非並行模式（依序執行）**
```bash
python3 seed.py --total 1000 --no-parallel
```
- 🐢 **速度較慢**：資料來源依序抓取
- 💚 **資源友善**：一次只有一個連線
- 🔍 **進度清晰**：依序顯示，易於追蹤
- 🛠️ **適用場景**：網路不穩定、除錯、系統資源有限

**模式比較**：

| 特性 | 並行模式 | 非並行模式 |
|-----|---------|-----------|
| 速度 | ⚡ 快（25-30 分鐘/10k） | 🐢 慢（60-90 分鐘/10k） |
| 資源 | 🔥 高（7 個並行連線） | 💚 低（1 個連線） |
| 穩定性 | ⚠️ 中 | ✅ 高 |
| 進度顯示 | 交錯顯示 | 清晰依序 |
| 除錯 | 較困難 | 容易 |

#### 效能優化

資料抓取腳本已經過多重優化，提供極致效能：

1. **來源級別平行處理** 🚀🚀🚀 (NEW!)
   - **所有資料來源同時並行抓取**
   - ArXiv、Wikipedia、Google Books、Quotable、UselessFacts、ZenQuotes 六個來源同時執行
   - 不再依序等待，充分利用網路頻寬
   - **額外提升 2-3 倍速度**

2. **多執行緒平行處理** 🚀
   - ArXiv: 5 個平行 workers 同時抓取不同批次
   - Wikipedia: **30 個平行 workers** 同時請求（已優化）
   - Google Books: 5 個平行 workers 同時抓取不同頁面
   - Quotable、UselessFacts、ZenQuotes: 單執行緒（API 限制）

3. **批次 API 查詢** ⚡
   - Wikipedia 暢銷書：使用批次 API，一次查詢 50 本書（vs 逐一查詢 51 次）
   - Wikipedia 隨機條目：**超級批次模式**
     - 使用 `list=random` 一次取得 500 個頁面 ID
     - 再分 10 批（每批 50 個）查詢內容
     - **每個超級批次獲得 ~180-200 篇文章**（vs 舊版 15-18 篇）
     - **效率提升 10-12 倍**

4. **過濾條件優化**
   - 放寬描述長度要求：50 字（vs 舊版 100 字）
   - 提升有效文章比例 ~15%

5. **實測效能數據** ⚡⚡⚡
   - 500 筆資料：~11 秒
   - 2,000 筆資料（純 Wikipedia）：~40 秒
   - 5,000 筆資料（混合來源）：**~38 秒** 🔥
   - 10,000 筆資料（混合來源）：**~53 秒** 🔥🔥🔥
   - 相比優化前提升 **10-15 倍**

#### 進度提示說明

執行時會顯示詳細的進度資訊，讓您清楚了解當前狀態：

- **ArXiv 抓取**: 顯示平行處理進度和每個類別的貢獻
- **Wikipedia 抓取**: 顯示完成的請求數和文章收集進度
- **Google Books 抓取**: 顯示每個主題的平行抓取結果
- **資料庫寫入**: 顯示批次插入進度和索引建立狀態

### 3. 開啟瀏覽器測試

在瀏覽器開啟 http://localhost:3000，你會看到一個搜尋介面。

試著輸入以下關鍵字測試模糊搜尋：
- `dracula` → Dracula
- `dune` → Dune
- `hobbit` → The Hobbit
- `foundation` → Foundation

## 💾 資料庫備份與還原

專案提供了方便的腳本來備份和還原資料庫：

### 匯出資料庫

```bash
./dump_data.sh
```

這會：
- 自動建立 `backups/` 目錄
- 匯出完整的資料庫結構和資料
- 檔案名稱包含時間戳記（例如：`testdb_dump_20251125_174237.sql`）
- 顯示資料筆數和檔案大小

### 匯入資料庫

```bash
# 查看可用的備份檔案
./restore_data.sh

# 從備份檔案還原
./restore_data.sh backups/testdb_dump_20251125_174237.sql
```

這會：
- 刪除現有的 `testdb` 資料庫
- 重新建立資料庫
- 匯入備份資料
- 顯示匯入結果

**注意**：匯入操作會覆蓋現有資料，請謹慎使用！

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
