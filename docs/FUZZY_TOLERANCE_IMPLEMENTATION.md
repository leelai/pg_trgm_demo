[← 返回主頁](../README.md)

# 容錯搜尋功能實作說明

## 📋 更新日期
2025-11-26

## 🎯 問題描述

原本的專案雖然使用了 PostgreSQL pg_trgm 擴充功能，但實際上**沒有容錯功能**。搜尋邏輯使用 `ILIKE` 進行精確匹配（僅不區分大小寫），無法找到拼錯的字串。

### 範例問題
- 搜尋 `"harri"` 無法找到 `"Harry"`（少了一個字母）
- 搜尋 `"hary"` 無法找到 `"Harry"`（拼錯）
- 搜尋 `"harrry"` 無法找到 `"Harry"`（多了一個字母）

## 🔧 解決方案

### 1. 設定 pg_trgm 相似度閾值

**檔案**: `init.sql`

在資料庫初始化時加入相似度閾值設定：

```sql
-- 設定 pg_trgm 相似度閾值
-- similarity_threshold: 用於 % 操作符，預設 0.3（範圍 0-1，越小越寬鬆）
-- word_similarity_threshold: 用於 <<% 操作符，預設 0.6
ALTER DATABASE testdb SET pg_trgm.similarity_threshold = 0.3;
ALTER DATABASE testdb SET pg_trgm.word_similarity_threshold = 0.6;
```

### 2. 連線池會話級別設定

**檔案**: `backend/server.js`

確保每個資料庫連線都使用相同的閾值：

```javascript
// 設定 pg_trgm 相似度閾值（會話級別）
pool.on('connect', (client) => {
  client.query('SET pg_trgm.similarity_threshold = 0.3');
  client.query('SET pg_trgm.word_similarity_threshold = 0.6');
});
```

### 3. 重新設計搜尋邏輯

**檔案**: `backend/server.js`

改用真正的 trigram 相似度匹配，實作四種匹配方式：

#### 修改前（無容錯）
```sql
-- 使用 ILIKE，只能精確匹配
WHERE title ILIKE '%' || $1 || '%'
```

#### 修改後（有容錯）
```sql
WITH search_results AS (
  -- 1. 精確前綴匹配 (最高優先級)
  SELECT id, title, description,
         similarity(title, $1) + 0.5 AS sim,
         'exact_prefix' AS match_type
  FROM worlds
  WHERE title ILIKE $1 || '%'

  UNION ALL

  -- 2. Trigram 相似度匹配 (容錯！使用 % 操作符)
  SELECT id, title, description,
         similarity(title, $1) + 0.3 AS sim,
         'similarity' AS match_type
  FROM worlds
  WHERE title % $1
    AND NOT (title ILIKE $1 || '%')

  UNION ALL

  -- 3. Word similarity 匹配 (使用 <<% 操作符)
  SELECT id, title, description,
         word_similarity($1, title) + 0.2 AS sim,
         'word_similarity' AS match_type
  FROM worlds
  WHERE $1 <<% title
    AND NOT (title ILIKE $1 || '%')
    AND NOT (title % $1)

  UNION ALL

  -- 4. 包含匹配 (後備方案)
  SELECT id, title, description,
         similarity(title, $1) + 0.1 AS sim,
         'contains' AS match_type
  FROM worlds
  WHERE title ILIKE '%' || $1 || '%'
    AND NOT (title ILIKE $1 || '%')
    AND NOT (title % $1)
    AND NOT ($1 <<% title)
)
SELECT DISTINCT ON (id)
  id, title, description, sim, match_type
FROM search_results
WHERE sim > 0.2
ORDER BY id, sim DESC
LIMIT 20;
```

## 📊 關鍵技術

### pg_trgm 操作符

| 操作符 | 說明 | 用途 |
|--------|------|------|
| `%` | Trigram 相似度匹配 | 容錯搜尋，找到拼錯的字串 |
| `<<%` | Word similarity | 搜尋詞在較長字串中的部分匹配 |
| `ILIKE` | 不區分大小寫的模式匹配 | 精確匹配（無容錯） |

### 相似度函數

| 函數 | 說明 |
|------|------|
| `similarity(text1, text2)` | 計算兩個字串的 trigram 相似度（0-1） |
| `word_similarity(text1, text2)` | 計算 text1 在 text2 中的詞彙相似度 |

## ✅ 測試結果

使用 `scripts/test_fuzzy_tolerance.py` 進行測試：

| 測試項目 | 搜尋詞 | 目標 | 結果 | 狀態 |
|---------|-------|------|------|------|
| 測試 1 | `harri` (少一個字母) | Harry, Harold, Harriett, Harrison, Harris | 全部找到 | ✅ |
| 測試 2 | `hary` (少一個 r) | Harry | 找到 (相似度: 0.871) | ✅ |
| 測試 3 | `hari` (少一個 r) | Harry | 找到 (相似度: 0.675) | ✅ |
| 測試 4 | `harrry` (多一個 r) | Harry | 找到 (相似度: 1.157) | ✅ |

### 範例輸出

搜尋 `"harri"` 的結果：
```
1. Harris    (相似度: 1.125, 類型: exact_prefix)   ← 精確前綴匹配
2. Harriett  (相似度: 1.000, 類型: exact_prefix)
3. Harrison  (相似度: 1.000, 類型: exact_prefix)
4. Harry     (相似度: 0.800, 類型: similarity)    ← 容錯匹配！
5. Harold    (相似度: 0.600, 類型: similarity)    ← 容錯匹配！
```

搜尋 `"hary"` (拼錯) 的結果：
```
1. Harry     (相似度: 0.871, 類型: similarity)    ← 容錯成功！
```

## 🚀 如何執行測試

```bash
cd /Users/leelai/work/aloha/pg_trgm_demo
source venv/bin/activate
python scripts/test_fuzzy_tolerance.py
```

## 📝 修改檔案清單

1. `init.sql` - 加入資料庫級別的相似度閾值設定
2. `backend/server.js` - 加入連線池會話設定 + 重新設計搜尋邏輯
3. `scripts/test_fuzzy_tolerance.py` - 新增容錯搜尋測試腳本

## 🎉 效果

✅ **容錯搜尋功能完全正常運作**
- 拼錯的搜尋詞可以找到正確結果
- 相似度評分合理
- 查詢速度快（10-18ms）
- 結果依相似度排序

## 📚 參考資料

- [PostgreSQL pg_trgm Documentation](https://www.postgresql.org/docs/current/pgtrgm.html)
- pg_trgm 透過將字串切成 trigram（三字元片段）來計算相似度
- 例如 "Harry" 的 trigrams: `{har, arr, rry}`
- "harri" 的 trigrams: `{har, arr, rri}`
- 兩者有 2/3 重疊，因此相似度高，可以找到彼此

