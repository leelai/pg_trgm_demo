package main

import (
	"backend-go/config"
	"backend-go/handlers"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

func main() {
	// 初始化資料庫
	if err := config.InitDB(); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}

	// 建立 Gin 路由
	r := gin.Default()

	// 設定 CORS
	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"*"},
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
	}))

	// 提供靜態檔案
	r.Static("/static", "../frontend")

	// 健康檢查端點
	r.GET("/health", handlers.HealthCheck)

	// 搜尋端點
	r.GET("/search", handlers.Search)

	// 管理端點
	admin := r.Group("/admin")
	{
		data := admin.Group("/data")
		{
			data.GET("/stats", handlers.GetDataStats)
			data.POST("/generate", handlers.GenerateTestData)
			data.DELETE("/clear", handlers.ClearAllData)
			data.POST("/rebuild-indexes", handlers.RebuildIndexes)
		}
	}

	// 根路徑 - 提供前端
	r.GET("/", handlers.ServeStatic)

	// 優雅關閉
	go func() {
		sigint := make(chan os.Signal, 1)
		signal.Notify(sigint, os.Interrupt, syscall.SIGTERM)
		<-sigint

		log.Println("Shutting down server...")
		
		// 關閉資料庫連線
		sqlDB, err := config.DB.DB()
		if err == nil {
			sqlDB.Close()
			log.Println("Database connection closed")
		}
		
		os.Exit(0)
	}()

	// 啟動伺服器
	port := getEnv("PORT", "3001")
	log.Printf("Server running on http://localhost:%s", port)
	log.Printf("Search endpoint: http://localhost:%s/search?q=your_query", port)
	log.Printf("Health check: http://localhost:%s/health", port)

	if err := r.Run(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}

func getEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}

