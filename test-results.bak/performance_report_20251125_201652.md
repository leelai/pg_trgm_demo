# pg_trgm 效能測試報告

**測試時間:** 2025-11-25 20:16:52  
**測試場景:** load  
**目標 URL:** http://[::1]:3000

## 測試配置

- **資料量級別:** 100 500 1000
- **k6 場景:** load
- **測試工具:** k6

## 測試結果

### 資料量: 100 筆

```
總筆數: 100
表格大小: 48 kB
索引大小: 256 kB
總大小: 304 kB
```

**k6 測試結果:**

詳見: `test-results/k6_100_20251125_201652.json`

---

### 資料量: 500 筆

```
總筆數: 500
表格大小: 104 kB
索引大小: 1072 kB
總大小: 1176 kB
```

**k6 測試結果:**

詳見: `test-results/k6_500_20251125_201652.json`

---

### 資料量: 1000 筆

```
總筆數: 1000
表格大小: 168 kB
索引大小: 2080 kB
總大小: 2248 kB
```

**k6 測試結果:**

詳見: `test-results/k6_1000_20251125_201652.json`

---


## 結論

請查看各個 k6 JSON 輸出檔案以獲取詳細的效能指標，包括:
- http_req_duration (p50, p95, p99)
- http_req_failed
- iterations
- vus (virtual users)

## 視覺化建議

1. 使用 k6 Cloud: 上傳結果到 k6 Cloud 進行視覺化
2. 使用 Grafana: 整合 InfluxDB 即時監控
3. 使用 jq: 解析 JSON 檔案提取關鍵指標

範例 jq 指令:
```bash
cat test-results/k6_*.json | jq -s 'group_by(.metric) | map({metric: .[0].metric, values: map(.data.value)}) | .[]'
```

