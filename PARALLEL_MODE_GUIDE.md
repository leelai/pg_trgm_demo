# 並行/非並行模式使用指南

## 🎯 功能說明

`seed.py` 現在支援兩種執行模式，讓你可以根據不同需求選擇最適合的方式：

---

## 🚀 並行模式（預設）

### 特點
- **所有資料來源同時抓取**
- 使用 `ThreadPoolExecutor` 並行執行
- 最多 7 個並行 workers（對應 7 個資料來源）
- 充分利用網路頻寬

### 使用方式
```bash
# 預設就是並行模式
python3 seed.py --total 1000

# 或明確指定（效果相同）
python3 seed.py --total 1000 --parallel
```

### 執行畫面
```
============================================================
pg_trgm Fuzzy Search Demo - Data Seeding
============================================================
Target Configuration:
  ...
  Execution Mode: PARALLEL
  ...
============================================================

🚀 PARALLEL MODE: All sources fetching simultaneously!

Scraping ArXiv papers (Target: 2500)...
Scraping Wikipedia articles (Target: 2500)...
Scraping Google Books (Target: 2000)...
Scraping quotes from Quotable.io (Target: 1500)...
Scraping random facts from UselessFacts (Target: 1000)...
Scraping quotes from ZenQuotes (Target: 500)...
```

### 優點
- ⚡ **速度最快**：10,000 筆約 25-30 分鐘
- 🚀 **效率最高**：充分利用網路頻寬
- 💪 **適合大量資料**：快速完成任務

### 缺點
- 🔥 **資源消耗較高**：同時 7 個網路連線
- ⚠️ **進度顯示交錯**：多個來源同時輸出
- 🐛 **除錯較困難**：錯誤訊息可能交錯

### 適用場景
- ✅ 網路連線穩定
- ✅ 系統資源充足
- ✅ 需要快速完成
- ✅ 一般日常使用

---

## ⏳ 非並行模式（依序執行）

### 特點
- **資料來源依序抓取**
- 一次只執行一個資料來源
- 進度清晰，易於追蹤
- 資源消耗低

### 使用方式
```bash
# 使用 --no-parallel 參數
python3 seed.py --total 1000 --no-parallel
```

### 執行畫面
```
============================================================
pg_trgm Fuzzy Search Demo - Data Seeding
============================================================
Target Configuration:
  ...
  Execution Mode: SEQUENTIAL
  ...
============================================================

⏳ SEQUENTIAL MODE: Fetching sources one by one...

Scraping ArXiv papers (Target: 2500)...
  [1/16] Category: cs.AI - Parallel fetching... ✓ Added 29, Total: 29/2500
  ...
✓ Total ArXiv papers collected: 2500

Scraping Wikipedia articles (Target: 2500)...
  → Launching 14 parallel super-batches...
  ...
✓ Total Wikipedia articles collected: 2500

Scraping Google Books (Target: 2000)...
  [1/30] Subject: fiction - Parallel fetching... ✓ +24 (Total: 24/2000)
  ...
✓ Total Google Books collected: 2000

... (依序執行其他來源)
```

### 優點
- 💚 **資源友善**：一次只有一個主要連線
- 🔍 **進度清晰**：依序顯示，易於閱讀
- 🛠️ **易於除錯**：錯誤訊息清楚
- ✅ **穩定性高**：網路問題影響較小

### 缺點
- 🐢 **速度較慢**：10,000 筆約 60-90 分鐘
- ⏰ **等待時間長**：需要依序等待每個來源完成

### 適用場景
- ✅ 網路連線不穩定
- ✅ 系統資源有限
- ✅ 需要清晰的進度顯示
- ✅ 除錯或測試特定來源
- ✅ 第一次使用，想觀察執行過程

---

## 📊 效能比較

### 執行時間（10,000 筆資料）

| 模式 | 預估時間 | 實際速度 |
|-----|---------|---------|
| 並行模式 | 25-30 分鐘 | 約 350-400 筆/分鐘 |
| 非並行模式 | 60-90 分鐘 | 約 110-170 筆/分鐘 |

### 資源使用

| 資源 | 並行模式 | 非並行模式 |
|-----|---------|-----------|
| 網路連線 | 7 個同時 | 1 個主要 |
| CPU 使用 | 中等 | 低 |
| 記憶體 | 中等 | 低 |

---

## 💡 使用建議

### 一般使用（推薦並行模式）
```bash
# 快速抓取 10,000 筆
python3 seed.py

# 快速抓取 1,000 筆
python3 seed.py --total 1000
```

### 網路不穩定時（推薦非並行模式）
```bash
# 穩定抓取 10,000 筆
python3 seed.py --no-parallel

# 穩定抓取 1,000 筆
python3 seed.py --total 1000 --no-parallel
```

### 除錯特定來源（推薦非並行模式）
```bash
# 只測試名言來源，使用非並行模式
python3 seed.py --quotable 100 --facts 100 --zenquotes 50 \
                --arxiv 0 --wikipedia 0 --books 0 --no-parallel
```

### 快速測試（並行模式即可）
```bash
# 快速測試 100 筆
python3 seed.py --total 100
```

---

## 🔧 技術細節

### 並行模式實作
```python
# 使用 ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=7) as executor:
    futures = {}
    
    # 提交所有任務
    if config['arxiv'] > 0:
        futures['arxiv'] = executor.submit(scrape_arxiv_papers, config['arxiv'])
    if config['wikipedia'] > 0:
        futures['wikipedia'] = executor.submit(scrape_wikipedia_bulk, config['wikipedia'])
    # ... 其他來源
    
    # 收集結果
    for source, future in futures.items():
        result = future.result()
```

### 非並行模式實作
```python
# 依序執行
if config['arxiv'] > 0:
    arxiv_papers = scrape_arxiv_papers(config['arxiv'])

if config['wikipedia'] > 0:
    wiki_articles = scrape_wikipedia_bulk(config['wikipedia'])

# ... 其他來源依序執行
```

---

## 🎯 常見問題

### Q: 預設是哪種模式？
**A**: 預設是**並行模式**，因為速度最快，適合大多數情況。

### Q: 如何切換模式？
**A**: 加上 `--no-parallel` 參數即可切換到非並行模式。

### Q: 非並行模式會更穩定嗎？
**A**: 是的，非並行模式一次只有一個主要連線，網路問題的影響較小，而且錯誤更容易追蹤。

### Q: 兩種模式的資料品質有差異嗎？
**A**: 沒有差異，兩種模式抓取的資料完全相同，只是執行方式不同。

### Q: 可以中途切換模式嗎？
**A**: 不行，模式必須在執行前決定。如果需要切換，請停止當前執行，重新以新模式啟動。

### Q: 非並行模式真的需要 2-3 倍時間嗎？
**A**: 是的，因為需要依序等待每個來源完成。但如果網路不穩定，並行模式可能會因為重試而變慢，這時非並行模式可能更快。

---

## 📝 範例場景

### 場景 1: 正常使用
```bash
# 需求：快速填充 10,000 筆測試資料
# 建議：使用並行模式（預設）
python3 seed.py
```

### 場景 2: 網路不穩定
```bash
# 需求：在網路不穩定的環境填充資料
# 建議：使用非並行模式
python3 seed.py --no-parallel
```

### 場景 3: 除錯問題
```bash
# 需求：某個資料來源有問題，需要除錯
# 建議：只抓取該來源，使用非並行模式
python3 seed.py --quotable 100 --arxiv 0 --wikipedia 0 \
                --books 0 --facts 0 --zenquotes 0 --no-parallel
```

### 場景 4: 系統資源有限
```bash
# 需求：在資源有限的機器上執行
# 建議：使用非並行模式，減少資源消耗
python3 seed.py --total 5000 --no-parallel
```

### 場景 5: 快速測試
```bash
# 需求：快速測試功能是否正常
# 建議：使用並行模式，少量資料
python3 seed.py --total 100
```

---

## 🎉 總結

- **一般使用**：並行模式（預設）⚡
- **網路不穩**：非並行模式 💚
- **除錯測試**：非並行模式 🔍
- **資源有限**：非並行模式 🛠️

選擇適合你的模式，享受高效的資料填充體驗！

