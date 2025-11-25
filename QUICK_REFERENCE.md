# 快速參考卡 - seed.py 資料來源

## 📊 六大資料來源

| # | 來源 | 類型 | 預設數量 | 佔比 | 特色 |
|---|------|------|---------|------|------|
| 1 | **ArXiv** | 學術論文 | 2,500 | 25% | 長文（300+ 字元） |
| 2 | **Wikipedia** | 百科條目 | 2,500 | 25% | 中長文（100-300 字元） |
| 3 | **Google Books** | 書籍簡介 | 2,000 | 20% | 中長文（100-300 字元） |
| 4 | **Quotable** 🆕 | 名人名言 | 1,500 | 15% | 短文（50-100 字元） |
| 5 | **UselessFacts** 🆕 | 有趣冷知識 | 1,000 | 10% | 短文（50-100 字元） |
| 6 | **ZenQuotes** 🆕 | 額外名言 | 500 | 5% | 短文（50-100 字元） |

---

## ⚡ 常用命令

### 基本使用
```bash
# 預設配置（10,000 筆）
python3 seed.py

# 快速測試（100 筆）
python3 seed.py --total 100

# 查看所有參數
python3 seed.py --help
```

### 自訂配置
```bash
# 完整自訂
python3 seed.py --arxiv 2500 --wikipedia 2500 --books 2000 \
                --quotable 1500 --facts 1000 --zenquotes 500

# 只抓名言和冷知識
python3 seed.py --quotable 500 --facts 500 --zenquotes 100 \
                --arxiv 0 --wikipedia 0 --books 0

# 只抓學術內容
python3 seed.py --arxiv 5000 --wikipedia 0 --books 0 \
                --quotable 0 --facts 0 --zenquotes 0
```

---

## ⏱️ 執行時間參考

| 資料量 | 預估時間 | 適用場景 |
|-------|---------|---------|
| 100 筆 | ~1-2 分鐘 | 快速測試 |
| 1,000 筆 | ~3-5 分鐘 | 功能驗證 |
| 10,000 筆 | ~25-30 分鐘 | 完整測試 |

---

## 🔍 API 狀態

| API | 狀態 | 需要處理 | Rate Limit |
|-----|------|---------|-----------|
| Quotable.io | ✅ 可用 | SSL bypass | 無限制 |
| UselessFacts | ✅ 可用 | 無 | 無限制 |
| ZenQuotes | ✅ 可用 | 無 | 5 次/30秒 |
| ArXiv | ✅ 可用 | 無 | 無限制 |
| Wikipedia | ✅ 可用 | 無 | 無限制 |
| Google Books | ✅ 可用 | 無 | 無限制 |

---

## 📝 資料範例

### Quotable 名言
```
"Only two things are infinite, the universe and human stupidity, 
 and I'm not sure about the former." - Albert Einstein
```

### UselessFacts 冷知識
```
It takes more calories to eat a piece of celery than the celery 
has in it to begin with.
```

### ZenQuotes 名言
```
"Don't let the past steal your present." - Cherralea Morgen
```

---

## 🎯 使用建議

### 測試短文搜尋
```bash
python3 seed.py --quotable 1000 --facts 1000 --zenquotes 500 \
                --arxiv 0 --wikipedia 0 --books 0
```

### 測試長文搜尋
```bash
python3 seed.py --arxiv 5000 --wikipedia 0 --books 0 \
                --quotable 0 --facts 0 --zenquotes 0
```

### 平衡測試
```bash
python3 seed.py --total 1000
# 自動分配: ArXiv 250, Wikipedia 250, Books 200, 
#          Quotable 150, Facts 100, ZenQuotes 50
```

---

## 🚀 效能優化

- ✅ **並行執行**: 所有來源同時抓取
- ✅ **多執行緒**: Wikipedia 使用 30 個 workers
- ✅ **批次 API**: Wikipedia 批次查詢（50 筆/次）
- ✅ **超級批次**: Wikipedia 一次取 500 個 ID
- ✅ **智能去重**: 自動移除重複資料

---

## 📞 搜尋測試

```bash
# 測試名言搜尋
curl "http://localhost:3000/search?q=einstein"

# 測試冷知識搜尋
curl "http://localhost:3000/search?q=calories"

# 測試學術搜尋
curl "http://localhost:3000/search?q=machine+learning"
```

---

## 💾 資料庫備份

```bash
# 備份資料
./dump_data.sh

# 還原資料
./restore_data.sh testdb_backup_YYYYMMDD_HHMMSS.sql
```

---

## 🐛 疑難排解

### 問題: SSL 憑證錯誤
**解決**: 已自動處理（使用 `verify=False`）

### 問題: Rate limit 錯誤
**解決**: ZenQuotes 已自動處理（每 5 次請求等待 6 秒）

### 問題: 資料庫連線失敗
**檢查**: 
```bash
docker compose ps
docker compose logs postgres
```

### 問題: 資料量不足
**調整**: 增加 `target_count` 或使用 `--total` 參數

---

## 📚 相關文件

- `API_TEST_REPORT.md` - 完整的 API 測試報告
- `INTEGRATION_SUMMARY.md` - 整合總結
- `README.md` - 完整使用說明

---

**最後更新**: 2025-11-25

