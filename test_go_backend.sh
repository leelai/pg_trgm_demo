#!/bin/bash

# Go Backend 測試腳本

echo "======================================"
echo "Go Backend API 測試"
echo "======================================"
echo ""

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 測試函數
test_endpoint() {
    local name=$1
    local url=$2
    local method=${3:-GET}
    local data=$4
    
    echo -e "${YELLOW}測試: $name${NC}"
    echo "URL: $url"
    echo "Method: $method"
    
    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X $method "$url")
    else
        response=$(curl -s -w "\n%{http_code}" -X $method "$url" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 201 ]; then
        echo -e "${GREEN}✓ 成功 (HTTP $http_code)${NC}"
        echo "回應: $body" | head -c 200
        echo "..."
    else
        echo -e "${RED}✗ 失敗 (HTTP $http_code)${NC}"
        echo "回應: $body"
    fi
    echo ""
    echo "--------------------------------------"
    echo ""
}

# 等待服務啟動
echo "等待 Go backend 啟動..."
sleep 2

# 1. 健康檢查
test_endpoint "健康檢查" "http://localhost:3001/health"

# 2. 搜尋測試
test_endpoint "搜尋測試 - harry" "http://localhost:3001/search?q=harry"

# 3. 搜尋測試 - 空查詢
test_endpoint "搜尋測試 - 空查詢" "http://localhost:3001/search?q="

# 4. 資料統計
test_endpoint "資料統計" "http://localhost:3001/admin/data/stats"

echo "======================================"
echo "測試完成！"
echo "======================================"
echo ""
echo "如果所有測試都通過，Go backend 已經正常運行。"
echo ""
echo "前端測試："
echo "1. 開啟瀏覽器訪問 http://localhost:3000 或 http://localhost:3001"
echo "2. 使用頁面上方的 Toggle 按鈕切換 Node.js 和 Go backend"
echo "3. 測試搜尋功能"
echo ""

