#!/bin/bash

# ============================================================================
# 效能測試系統設定腳本
# 用於初始化 SQL 函數和重啟服務
# ============================================================================

set -e

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}效能測試系統設定${NC}"
echo -e "${BLUE}========================================${NC}"

# 步驟 1: 建立 SQL 函數
echo -e "${YELLOW}→ 建立 SQL 函數...${NC}"
docker exec -i pg_trgm_demo psql -U postgres -d testdb < scripts/generate_test_data.sql
echo -e "${GREEN}✓ SQL 函數已建立${NC}"

# 步驟 2: 重啟後端服務
echo -e "${YELLOW}→ 重啟後端服務...${NC}"
docker compose restart backend
echo -e "${GREEN}✓ 後端服務已重啟${NC}"

# 步驟 3: 等待服務啟動
echo -e "${YELLOW}→ 等待服務啟動...${NC}"
sleep 8

# 步驟 4: 驗證
echo -e "${YELLOW}→ 驗證服務...${NC}"

# 檢查健康狀態
HEALTH=$(curl -s http://localhost:3000/health)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 後端服務正常${NC}"
    echo "  $HEALTH"
else
    echo -e "${RED}✗ 後端服務異常${NC}"
    exit 1
fi

# 檢查管理 API
STATS=$(curl -s http://localhost:3000/admin/data/stats)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 管理 API 正常${NC}"
    echo "  $STATS"
else
    echo -e "${RED}✗ 管理 API 異常${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ 設定完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "現在可以使用以下方式測試:"
echo "  1. 前端: http://localhost:3000"
echo "  2. 自動化測試: ./scripts/run-performance-tests.sh"
echo "  3. 手動 API: curl -X POST http://localhost:3000/admin/data/generate -H 'Content-Type: application/json' -d '{\"count\": 10000}'"

