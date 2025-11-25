#!/bin/bash

# ============================================================================
# pg_trgm 效能測試自動化腳本
# 測試不同資料量對搜尋效能的影響
# ============================================================================

set -e  # 遇到錯誤立即退出

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
# 使用 IPv6 地址避免連到本機的其他服務
BASE_URL="${BASE_URL:-http://[::1]:3000}"
RESULTS_DIR="./test-results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE="${RESULTS_DIR}/performance_report_${TIMESTAMP}.md"

# 測試資料量級別
DATA_VOLUMES=(100 500 1000 5000 10000 50000 100000 200000 500000 1000000)

# k6 測試場景
K6_SCENARIO="${K6_SCENARIO:-load}"

# ============================================================================
# 函數定義
# ============================================================================

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# 檢查服務是否運行
check_service() {
    print_info "檢查服務狀態..."
    
    if ! curl -s "${BASE_URL}/health" > /dev/null; then
        print_error "服務未運行於 ${BASE_URL}"
        print_info "請先啟動服務: docker compose up -d"
        exit 1
    fi
    
    print_success "服務運行正常"
}

# 檢查 k6 是否安裝
check_k6() {
    print_info "檢查 k6 安裝..."
    
    if ! command -v k6 &> /dev/null; then
        print_error "k6 未安裝"
        echo ""
        echo "請安裝 k6:"
        echo "  macOS:   brew install k6"
        echo "  Linux:   sudo gpg -k && sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69 && echo 'deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main' | sudo tee /etc/apt/sources.list.d/k6.list && sudo apt-get update && sudo apt-get install k6"
        echo "  Windows: choco install k6"
        echo ""
        echo "或訪問: https://k6.io/docs/getting-started/installation/"
        exit 1
    fi
    
    K6_VERSION=$(k6 version | head -n 1)
    print_success "k6 已安裝: ${K6_VERSION}"
}

# 清空資料
clear_data() {
    print_info "清空現有資料..."
    
    RESPONSE=$(curl -s -X DELETE "${BASE_URL}/admin/data/clear")
    DELETED_COUNT=$(echo $RESPONSE | grep -o '"deletedCount":[0-9]*' | grep -o '[0-9]*')
    
    print_success "已刪除 ${DELETED_COUNT} 筆資料"
}

# 產生測試資料
generate_data() {
    local count=$1
    print_info "產生 ${count} 筆測試資料..."
    
    RESPONSE=$(curl -s -X POST "${BASE_URL}/admin/data/generate" \
        -H "Content-Type: application/json" \
        -d "{\"count\": ${count}}")
    
    SUCCESS=$(echo $RESPONSE | grep -o '"success":[^,]*' | grep -o '[^:]*$')
    
    if [ "$SUCCESS" = "true" ]; then
        INSERTED=$(echo $RESPONSE | grep -o '"insertedCount":[0-9]*' | grep -o '[0-9]*')
        EXEC_TIME=$(echo $RESPONSE | grep -o '"executionTimeMs":[0-9.]*' | grep -o '[0-9.]*')
        print_success "已產生 ${INSERTED} 筆資料 (耗時: ${EXEC_TIME}ms)"
    else
        print_error "產生資料失敗"
        echo $RESPONSE
        exit 1
    fi
}

# 取得資料統計
get_stats() {
    RESPONSE=$(curl -s "${BASE_URL}/admin/data/stats")
    TOTAL_RECORDS=$(echo $RESPONSE | grep -o '"totalRecords":[0-9]*' | grep -o '[0-9]*')
    TABLE_SIZE=$(echo $RESPONSE | grep -o '"tableSize":"[^"]*"' | sed 's/"tableSize":"//;s/"//')
    INDEX_SIZE=$(echo $RESPONSE | grep -o '"indexSize":"[^"]*"' | sed 's/"indexSize":"//;s/"//')
    TOTAL_SIZE=$(echo $RESPONSE | grep -o '"totalSize":"[^"]*"' | sed 's/"totalSize":"//;s/"//')
    
    echo "總筆數: ${TOTAL_RECORDS}"
    echo "表格大小: ${TABLE_SIZE}"
    echo "索引大小: ${INDEX_SIZE}"
    echo "總大小: ${TOTAL_SIZE}"
}

# 執行 k6 測試
run_k6_test() {
    local data_count=$1
    local output_file="${RESULTS_DIR}/k6_${data_count}_${TIMESTAMP}.json"
    
    print_info "執行 k6 測試 (${K6_SCENARIO} 場景)..."
    
    k6 run \
        -e SCENARIO="${K6_SCENARIO}" \
        -e BASE_URL="${BASE_URL}" \
        --out "json=${output_file}" \
        k6-tests/search-performance.js
    
    print_success "k6 測試完成，結果已儲存至: ${output_file}"
}

# 初始化報告
init_report() {
    mkdir -p "${RESULTS_DIR}"
    
    cat > "${REPORT_FILE}" << EOF
# pg_trgm 效能測試報告

**測試時間:** $(date +"%Y-%m-%d %H:%M:%S")  
**測試場景:** ${K6_SCENARIO}  
**目標 URL:** ${BASE_URL}

## 測試配置

- **資料量級別:** ${DATA_VOLUMES[@]}
- **k6 場景:** ${K6_SCENARIO}
- **測試工具:** k6

## 測試結果

EOF
}

# 新增測試結果到報告
add_result_to_report() {
    local data_count=$1
    local stats=$2
    
    cat >> "${REPORT_FILE}" << EOF
### 資料量: ${data_count} 筆

\`\`\`
${stats}
\`\`\`

**k6 測試結果:**

詳見: \`test-results/k6_${data_count}_${TIMESTAMP}.json\`

---

EOF
}

# 完成報告
finalize_report() {
    cat >> "${REPORT_FILE}" << EOF

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
\`\`\`bash
cat test-results/k6_*.json | jq -s 'group_by(.metric) | map({metric: .[0].metric, values: map(.data.value)}) | .[]'
\`\`\`

EOF
    
    print_success "報告已產生: ${REPORT_FILE}"
}

# ============================================================================
# 主程式
# ============================================================================

main() {
    print_header "pg_trgm 效能測試自動化"
    
    # 前置檢查
    check_service
    check_k6
    
    # 初始化報告
    init_report
    
    # 對每個資料量級別執行測試
    for count in "${DATA_VOLUMES[@]}"; do
        print_header "測試資料量: ${count} 筆"
        
        # 清空並產生新資料
        clear_data
        generate_data $count
        
        # 顯示統計資訊
        print_info "資料統計:"
        STATS=$(get_stats)
        echo "$STATS"
        
        # 等待索引穩定
        print_info "等待 10 秒讓索引穩定..."
        sleep 10
        
        # 驗證服務可用
        print_info "驗證服務狀態..."
        for i in {1..5}; do
            if curl -s "${BASE_URL}/health" > /dev/null 2>&1; then
                print_success "服務正常回應"
                break
            else
                print_info "等待服務回應... (嘗試 $i/5)"
                sleep 2
            fi
        done
        
        # 執行 k6 測試
        run_k6_test $count
        
        # 新增結果到報告
        add_result_to_report $count "$STATS"
        
        echo ""
    done
    
    # 完成報告
    finalize_report
    
    print_header "測試完成！"
    print_success "所有測試已完成"
    print_info "查看報告: ${REPORT_FILE}"
}

# 執行主程式
main

