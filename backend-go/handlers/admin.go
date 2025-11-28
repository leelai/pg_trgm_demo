package handlers

import (
	"backend-go/config"
	"backend-go/models"
	"log"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

// GetDataStats 取得資料統計
func GetDataStats(c *gin.Context) {
	var result struct {
		TotalRecords int64  `gorm:"column:total_records"`
		TableSize    string `gorm:"column:table_size"`
		IndexSize    string `gorm:"column:index_size"`
		TotalSize    string `gorm:"column:total_size"`
	}

	sql := "SELECT * FROM get_data_stats()"
	if err := config.DB.Raw(sql).Scan(&result).Error; err != nil {
		log.Printf("Stats error: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"success": false,
			"error":   "Failed to get statistics",
			"message": err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data": models.DataStats{
			TotalRecords: result.TotalRecords,
			TableSize:    result.TableSize,
			IndexSize:    result.IndexSize,
			TotalSize:    result.TotalSize,
		},
	})
}

// GenerateTestData 產生測試資料
func GenerateTestData(c *gin.Context) {
	var req struct {
		Count int `json:"count"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		req.Count = 10000
	}

	// 驗證 count
	if req.Count < 1 || req.Count > 1000000 {
		c.JSON(http.StatusBadRequest, gin.H{
			"success": false,
			"error":   "Invalid count. Must be between 1 and 1,000,000",
		})
		return
	}

	log.Printf("Generating %d test records...", req.Count)

	var result struct {
		InsertedCount   int     `gorm:"column:inserted_count"`
		ExecutionTimeMs float64 `gorm:"column:execution_time_ms"`
	}

	sql := "SELECT * FROM generate_test_data($1)"
	if err := config.DB.Raw(sql, req.Count).Scan(&result).Error; err != nil {
		log.Printf("Generate error: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"success": false,
			"error":   "Failed to generate data",
			"message": err.Error(),
		})
		return
	}

	log.Printf("Generated %d records in %.2fms", result.InsertedCount, result.ExecutionTimeMs)

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data": models.GenerateDataResult{
			InsertedCount:   result.InsertedCount,
			ExecutionTimeMs: roundFloat(result.ExecutionTimeMs, 2),
		},
	})
}

// ClearAllData 清空所有資料
func ClearAllData(c *gin.Context) {
	log.Println("Clearing all data...")

	var result struct {
		DeletedCount    int     `gorm:"column:deleted_count"`
		ExecutionTimeMs float64 `gorm:"column:execution_time_ms"`
	}

	sql := "SELECT * FROM clear_all_data()"
	if err := config.DB.Raw(sql).Scan(&result).Error; err != nil {
		log.Printf("Clear error: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"success": false,
			"error":   "Failed to clear data",
			"message": err.Error(),
		})
		return
	}

	log.Printf("Deleted %d records in %.2fms", result.DeletedCount, result.ExecutionTimeMs)

	// 執行 VACUUM ANALYZE
	log.Println("Running VACUUM ANALYZE...")
	vacuumStart := time.Now()
	if err := config.DB.Exec("VACUUM ANALYZE worlds").Error; err != nil {
		log.Printf("VACUUM error: %v", err)
	}
	vacuumTime := time.Since(vacuumStart).Milliseconds()
	log.Printf("VACUUM completed in %dms", vacuumTime)

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data": models.ClearDataResult{
			DeletedCount:    result.DeletedCount,
			ExecutionTimeMs: roundFloat(result.ExecutionTimeMs, 2),
			VacuumTimeMs:    vacuumTime,
		},
	})
}

// RebuildIndexes 重建索引
func RebuildIndexes(c *gin.Context) {
	log.Println("Rebuilding indexes...")

	var result struct {
		Status          string  `gorm:"column:status"`
		ExecutionTimeMs float64 `gorm:"column:execution_time_ms"`
	}

	sql := "SELECT * FROM rebuild_indexes()"
	if err := config.DB.Raw(sql).Scan(&result).Error; err != nil {
		log.Printf("Rebuild indexes error: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"success": false,
			"error":   "Failed to rebuild indexes",
			"message": err.Error(),
		})
		return
	}

	log.Printf("Indexes rebuilt in %.2fms", result.ExecutionTimeMs)

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data": models.RebuildIndexesResult{
			Status:          result.Status,
			ExecutionTimeMs: roundFloat(result.ExecutionTimeMs, 2),
		},
	})
}

// ServeStatic 提供靜態檔案（前端）
func ServeStatic(c *gin.Context) {
	c.File("../frontend/index.html")
}
