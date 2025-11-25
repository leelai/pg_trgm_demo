#!/bin/bash
# PostgreSQL 資料庫匯入腳本
# 用途：從備份檔案還原 testdb 資料庫

set -e  # 遇到錯誤立即停止

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 資料庫連線參數
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="testdb"
DB_USER="postgres"
DB_PASSWORD="password"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}PostgreSQL 資料庫匯入工具${NC}"
echo -e "${BLUE}============================================================${NC}"

# 檢查參數
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}使用方式: $0 <備份檔案路徑>${NC}"
    echo ""
    echo -e "${GREEN}可用的備份檔案：${NC}"
    if [ -d "backups" ]; then
        ls -lh backups/*.sql 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
    else
        echo -e "${RED}  找不到 backups 目錄${NC}"
    fi
    echo ""
    echo -e "${GREEN}範例：${NC}"
    echo -e "  $0 backups/testdb_dump_20241125_120000.sql"
    exit 1
fi

DUMP_FILE="$1"

# 檢查檔案是否存在
if [ ! -f "$DUMP_FILE" ]; then
    echo -e "${RED}✗ 找不到備份檔案: $DUMP_FILE${NC}"
    exit 1
fi

FILE_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
echo -e "${GREEN}→ 備份檔案: $DUMP_FILE (${FILE_SIZE})${NC}"

# 檢查 Docker 容器是否運行
echo -e "${GREEN}→ 檢查 Docker 容器...${NC}"
if ! docker ps | grep -q pg_trgm_demo; then
    echo -e "${RED}✗ Docker 容器未運行！${NC}"
    echo -e "${RED}  請先啟動容器：docker compose up -d${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker 容器運行中${NC}"

# 警告訊息
echo -e "${YELLOW}⚠️  警告：此操作將會：${NC}"
echo -e "${YELLOW}  1. 刪除現有的 testdb 資料庫${NC}"
echo -e "${YELLOW}  2. 重新建立 testdb 資料庫${NC}"
echo -e "${YELLOW}  3. 匯入備份資料${NC}"
echo ""
read -p "確定要繼續嗎？(yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${BLUE}已取消操作${NC}"
    exit 0
fi

# 取得現有資料筆數（如果資料庫存在）
EXISTING_COUNT=0
if docker exec pg_trgm_demo psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    EXISTING_COUNT=$(docker exec pg_trgm_demo psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM worlds" 2>/dev/null | xargs || echo "0")
    echo -e "${BLUE}→ 現有資料: ${EXISTING_COUNT} 筆${NC}"
fi

# 終止所有連線到目標資料庫的 session
echo -e "${GREEN}→ 斷開所有連線...${NC}"
docker exec pg_trgm_demo psql -U "$DB_USER" -d "postgres" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" > /dev/null 2>&1

# 刪除現有資料庫
echo -e "${GREEN}→ 刪除現有資料庫...${NC}"
docker exec pg_trgm_demo psql -U "$DB_USER" -d "postgres" -c "DROP DATABASE IF EXISTS $DB_NAME" > /dev/null

# 建立新資料庫
echo -e "${GREEN}→ 建立新資料庫...${NC}"
docker exec pg_trgm_demo psql -U "$DB_USER" -d "postgres" -c "CREATE DATABASE $DB_NAME" > /dev/null

# 匯入資料（使用 Docker 容器內的 psql 避免版本問題）
echo -e "${GREEN}→ 匯入資料中（這可能需要一些時間）...${NC}"
docker exec -i pg_trgm_demo psql -U "$DB_USER" -d "$DB_NAME" < "$DUMP_FILE" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    # 取得匯入後的資料筆數
    NEW_COUNT=$(docker exec pg_trgm_demo psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM worlds" | xargs)
    
    echo -e "${GREEN}✓ 匯入成功！${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${GREEN}匯入結果：${NC}"
    echo -e "  資料庫: ${DB_NAME}"
    echo -e "  資料筆數: ${NEW_COUNT} 筆"
    if [ "$EXISTING_COUNT" != "0" ]; then
        echo -e "  原有筆數: ${EXISTING_COUNT} 筆"
    fi
    echo -e "${BLUE}============================================================${NC}"
else
    echo -e "${RED}✗ 匯入失敗！${NC}"
    exit 1
fi

# 清理密碼環境變數
unset PGPASSWORD

