package handlers

import (
	"backend-go/config"
	"backend-go/models"
	"net/http"

	"github.com/gin-gonic/gin"
)

// HealthCheck 健康檢查端點
func HealthCheck(c *gin.Context) {
	var count int64
	if err := config.DB.Model(&models.World{}).Count(&count).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  "error",
			"message": err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":   "ok",
		"database": "connected",
		"records":  count,
	})
}

