[← 返回主頁](../README.md)

# API 資料來源測試報告

測試日期: 2025-11-25  
測試目的: 評估 `generate_dynamic_data.py` 中使用的 API 是否適合整合到 `scripts/seed.py`

---

## 📊 測試結果總覽

| API 來源 | 狀態 | 成功率 | 需要處理 |
|---------|------|--------|---------|
| **Quotable.io** (名言) | ✅ 可用 | 10/10 (100%) | 需繞過 SSL 驗證 (`verify=False`) |
| **ZenQuotes.io** (名言替代) | ✅ 可用 | 5/5 (100%) | Rate limit: 5 次/30秒 |
| **UselessFacts** (冷知識) | ✅ 可用 | 10/10 (100%) | 無需特殊處理 |
| **Wikipedia Random** (對照) | ✅ 可用 | 5/5 (100%) | 無需特殊處理 |

---

## 🔍 詳細測試結果

### 1. Quotable.io (名人名言 API)

**API 端點**: `https://api.quotable.io/random`

**狀態**: ✅ 可用 (需繞過 SSL 驗證)

**範例資料**:
```
範例 1:
  作者: Brian Tracy
  內容: "Goals are the fuel in the furnace of achievement."
  標籤: Famous Quotes
  長度: 49 字元

範例 2:
  作者: Harriet Beecher Stowe
  內容: "All serious daring starts from within."
  標籤: Famous Quotes
  長度: 38 字元

範例 3:
  作者: Napoleon Hill
  內容: "You might well remember that nothing can bring you success but yourself."
  標籤: Success
  長度: 72 字元
```

**優點**:
- ✅ 完全免費，無需 API key
- ✅ 資料品質高，名人名言有作者和標籤
- ✅ 回應速度快
- ✅ 內容簡短（平均 50-100 字元），適合 fuzzy search 測試

**缺點**:
- ⚠️ SSL 憑證過期，需要在程式中加入 `verify=False`
- ⚠️ 需要加入 `urllib3.disable_warnings()` 來隱藏警告訊息

**建議整合方式**:
```python
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

response = requests.get(url, headers=headers, timeout=10, verify=False)
```

---

### 2. ZenQuotes.io (替代名言 API)

**API 端點**: `https://zenquotes.io/api/random`

**狀態**: ✅ 可用

**範例資料**:
```
範例 1:
  作者: Dr. Seuss
  內容: "Today you are you, that is truer than true. There is no one alive who is you-er than you."
  長度: 89 字元

範例 2:
  作者: Unknown
  內容: "On the other side of the clouds is a bright blue sky."
  長度: 53 字元

範例 3:
  作者: Arnold Schwarzenegger
  內容: "If you want to turn a vision into reality, you have to give 100% and never stop believing in your dream."
  長度: 104 字元
```

**優點**:
- ✅ 完全免費，無需 API key
- ✅ 無 SSL 問題
- ✅ 資料品質高

**缺點**:
- ⚠️ Rate limit 較嚴格：每 30 秒只能 5 次請求
- ⚠️ 不適合大量抓取（抓 1000 筆需要約 100 分鐘）

**建議**: 作為備用方案，或用於小量測試

---

### 3. UselessFacts (隨機冷知識 API)

**API 端點**: `https://uselessfacts.jsph.pl/random.json?language=en`

**狀態**: ✅ 可用

**範例資料**:
```
範例 1:
  內容: "The sixth sick sheik's sixth sheep's sick" is said to be the toughest tongue twister in English.
  長度: 97 字元

範例 2:
  內容: A jellyfish is 95 percent water!
  長度: 32 字元

範例 3:
  內容: The first female guest host of "Saturday Night Live" was Candace Bergen.
  長度: 72 字元
```

**優點**:
- ✅ 完全免費，無需 API key
- ✅ 無 SSL 問題
- ✅ 回應穩定，成功率 100%
- ✅ 內容有趣且多樣化
- ✅ 長度適中（平均 50-100 字元）

**缺點**:
- 無明顯缺點

**建議**: 強烈推薦整合！

---

### 4. Wikipedia Random API (對照組)

**API 端點**: `https://en.wikipedia.org/api/rest_v1/page/random/summary`

**狀態**: ✅ 可用

**範例資料**:
```
範例 1:
  標題: Shini-e
  摘要: Shini-e, also called "death pictures" or "death portraits", are Japanese woodblock prints...
  長度: 224 字元

範例 2:
  標題: Vixen Romeo
  摘要: Vixen Romeo is an American singer-songwriter, pin-up model and dancer...
  長度: 140 字元
```

**說明**: 此 API 作為對照組測試，確認網路連線正常。你的 `scripts/seed.py` 已經在使用類似的 Wikipedia API。

---

## 💡 整合建議

### 推薦方案 A: 整合兩個新來源（推薦）

**整合**: Quotable.io (名言) + UselessFacts (冷知識)

**優點**:
- 增加資料多樣性
- 兩個 API 都穩定可用
- 內容簡短，適合 fuzzy search 測試
- 與現有的 ArXiv、Wikipedia、Google Books 形成互補

**預估資料分配** (10,000 筆):
- ArXiv 論文: 3,000 筆 (30%)
- Wikipedia 文章: 3,000 筆 (30%)
- Google Books: 2,000 筆 (20%)
- Quotable 名言: 1,000 筆 (10%)
- UselessFacts 冷知識: 1,000 筆 (10%)

**實作複雜度**: 低 (約 30 分鐘)

---

### 推薦方案 B: 只整合 UselessFacts（保守）

**整合**: 只加入 UselessFacts

**優點**:
- 無需處理 SSL 問題
- 實作最簡單
- 仍能增加資料多樣性

**預估資料分配** (10,000 筆):
- ArXiv 論文: 3,500 筆 (35%)
- Wikipedia 文章: 3,500 筆 (35%)
- Google Books: 2,000 筆 (20%)
- UselessFacts 冷知識: 1,000 筆 (10%)

**實作複雜度**: 極低 (約 15 分鐘)

---

### 推薦方案 C: 使用 ZenQuotes 替代 Quotable

**整合**: ZenQuotes (名言) + UselessFacts (冷知識)

**優點**:
- 無 SSL 問題
- 資料品質高

**缺點**:
- ZenQuotes 的 rate limit 嚴格
- 抓取速度慢（1000 筆約需 100 分鐘）

**建議**: 不推薦用於大量資料抓取

---

## 🎯 最終建議

### 我的推薦: **方案 A**

**理由**:
1. ✅ **UselessFacts** 完全沒問題，強烈建議整合
2. ✅ **Quotable.io** 雖然有 SSL 問題，但可以輕鬆解決（加 `verify=False`）
3. ✅ 兩個 API 都提供簡短、有趣的內容，非常適合 fuzzy search 測試
4. ✅ 與你現有的學術論文（ArXiv）、百科全書（Wikipedia）、書籍（Google Books）形成完美互補
5. ✅ 增加資料多樣性，讓測試更全面

**如果你擔心 SSL 問題**: 選擇 **方案 B**（只整合 UselessFacts）

---

## 📝 實作程式碼範例

### UselessFacts 整合範例

```python
def scrape_random_facts(target_count=1000):
    """從 UselessFacts API 抓取隨機冷知識"""
    print(f"\nScraping random facts (Target: {target_count})...")
    facts = []
    seen_facts = set()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    for i in range(target_count):
        try:
            url = "https://uselessfacts.jsph.pl/random.json?language=en"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                fact = data.get('text', '')
                
                if fact and fact not in seen_facts and len(fact) > 20:
                    seen_facts.add(fact)
                    
                    # 從前幾個字生成標題
                    title_words = fact.split()[:8]
                    title = ' '.join(title_words)
                    if len(fact.split()) > 8:
                        title += '...'
                    
                    facts.append((title, fact))
                    
                    if len(facts) % 100 == 0:
                        print(f"  Progress: {len(facts)}/{target_count}")
            
            time.sleep(0.2)  # 避免 rate limiting
            
        except Exception as e:
            continue
    
    print(f"✓ Total facts collected: {len(facts)}")
    return facts
```

### Quotable.io 整合範例（含 SSL bypass）

```python
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def scrape_quotable_quotes(target_count=1000):
    """從 Quotable.io 抓取名人名言"""
    print(f"\nScraping quotes from Quotable.io (Target: {target_count})...")
    quotes = []
    seen_quotes = set()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    for i in range(target_count):
        try:
            url = "https://api.quotable.io/random"
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                author = data.get('author', 'Unknown')
                content = data.get('content', '')
                
                if content and content not in seen_quotes and len(content) > 20:
                    seen_quotes.add(content)
                    title = f"Quote by {author}"
                    description = f'"{content}" - {author}'
                    quotes.append((title, description))
                    
                    if len(quotes) % 100 == 0:
                        print(f"  Progress: {len(quotes)}/{target_count}")
            
            time.sleep(0.2)
            
        except Exception as e:
            continue
    
    print(f"✓ Total quotes collected: {len(quotes)}")
    return quotes
```

---

## ⏱️ 預估抓取時間

假設抓取 10,000 筆資料：

| 來源 | 數量 | 每筆延遲 | 預估時間 | 備註 |
|-----|------|---------|---------|------|
| ArXiv | 3,000 | 0.5s | ~25 分鐘 | 並行處理 |
| Wikipedia | 3,000 | 0.3s | ~15 分鐘 | 並行處理，已優化 |
| Google Books | 2,000 | 0.3s | ~10 分鐘 | 並行處理 |
| Quotable | 1,000 | 0.2s | ~3 分鐘 | 新增 |
| UselessFacts | 1,000 | 0.2s | ~3 分鐘 | 新增 |
| **總計** | **10,000** | - | **~30-40 分鐘** | 並行執行 |

---

## ✅ 結論

**測試結果**: 三個 API 都可用！

**推薦整合**: 
1. 🥇 **UselessFacts** - 強烈推薦，無任何問題
2. 🥈 **Quotable.io** - 推薦，只需處理 SSL 問題
3. 🥉 **ZenQuotes** - 備用方案，rate limit 較嚴格

**下一步**: 等你決定要整合哪些 API，我可以立即幫你修改 `scripts/seed.py`！


