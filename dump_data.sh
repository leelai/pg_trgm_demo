#!/bin/bash
# PostgreSQL 資料庫匯出腳本
# 用途：備份 testdb 資料庫的所有資料

set -e  # 遇到錯誤立即停止

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 資料庫連線參數
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="testdb"
DB_USER="postgres"
DB_PASSWORD="password"

# 備份目錄
DUMP_DIR="backups"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}PostgreSQL 資料庫匯出工具${NC}"
echo -e "${BLUE}============================================================${NC}"

# 建立備份目錄
if [ ! -d "$DUMP_DIR" ]; then
    echo -e "${GREEN}→ 建立備份目錄: $DUMP_DIR${NC}"
    mkdir -p "$DUMP_DIR"
fi

# 檢查 Docker 容器是否運行
echo -e "${GREEN}→ 檢查 Docker 容器...${NC}"
if ! docker ps | grep -q pg_trgm_demo; then
    echo -e "${RED}✗ Docker 容器未運行！${NC}"
    echo -e "${RED}  請先啟動容器：docker compose up -d${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker 容器運行中${NC}"

# 取得資料筆數
echo -e "${GREEN}→ 檢查資料庫...${NC}"
RECORD_COUNT=$(docker exec pg_trgm_demo psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM worlds" | xargs)
echo -e "${GREEN}→ 資料表 'worlds' 共有 ${RECORD_COUNT} 筆資料${NC}"

# 匯出檔案名稱（包含時間戳記和資料筆數）
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DUMP_FILE="testdb_dump_${RECORD_COUNT}rows_${TIMESTAMP}.sql"
echo -e "${GREEN}→ 備份檔名: ${DUMP_FILE}${NC}"

# 匯出資料庫（使用 Docker 容器內的 pg_dump 避免版本問題）
echo -e "${GREEN}→ 開始匯出資料庫...${NC}"
docker exec pg_trgm_demo pg_dump -U "$DB_USER" -d "$DB_NAME" \
    --format=plain \
    --no-owner \
    --no-privileges \
    > "$DUMP_DIR/$DUMP_FILE"

if [ $? -eq 0 ]; then
    FILE_SIZE=$(du -h "$DUMP_DIR/$DUMP_FILE" | cut -f1)
    echo -e "${GREEN}✓ 匯出成功！${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${GREEN}備份檔案資訊：${NC}"
    echo -e "  檔案名稱: ${DUMP_FILE}"
    echo -e "  檔案路徑: ${DUMP_DIR}/${DUMP_FILE}"
    echo -e "  檔案大小: ${FILE_SIZE}"
    echo -e "  資料筆數: ${RECORD_COUNT} 筆"
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${GREEN}使用方式：${NC}"
    echo -e "  匯入資料：./restore_data.sh ${DUMP_DIR}/${DUMP_FILE}"
    echo -e "${BLUE}============================================================${NC}"
else
    echo -e "${RED}✗ 匯出失敗！${NC}"
    exit 1
fi

# 清理密碼環境變數
unset PGPASSWORD

