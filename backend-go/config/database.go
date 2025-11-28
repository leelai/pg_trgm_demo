package config

import (
	"fmt"
	"log"
	"os"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

var DB *gorm.DB

// InitDB 初始化資料庫連線
func InitDB() error {
	host := getEnv("DB_HOST", "localhost")
	port := getEnv("DB_PORT", "5432")
	dbname := getEnv("DB_NAME", "testdb")
	user := getEnv("DB_USER", "postgres")
	password := getEnv("DB_PASSWORD", "password")

	dsn := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		host, port, user, password, dbname)

	var err error
	DB, err = gorm.Open(postgres.Open(dsn), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Info),
	})

	if err != nil {
		return fmt.Errorf("failed to connect to database: %w", err)
	}

	// 取得底層的 *sql.DB 以設定連線池
	sqlDB, err := DB.DB()
	if err != nil {
		return fmt.Errorf("failed to get database instance: %w", err)
	}

	// 設定連線池參數
	sqlDB.SetMaxOpenConns(20)
	sqlDB.SetMaxIdleConns(10)

	// 設定 pg_trgm 閾值（會話級別）
	if err := DB.Exec("SET pg_trgm.similarity_threshold = 0.3").Error; err != nil {
		log.Printf("Warning: failed to set similarity_threshold: %v", err)
	}
	if err := DB.Exec("SET pg_trgm.word_similarity_threshold = 0.6").Error; err != nil {
		log.Printf("Warning: failed to set word_similarity_threshold: %v", err)
	}

	log.Println("Database connected successfully")
	return nil
}

// getEnv 取得環境變數，如果不存在則返回預設值
func getEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}

