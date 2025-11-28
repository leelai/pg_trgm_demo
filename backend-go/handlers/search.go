package handlers

import (
	"backend-go/config"
	"backend-go/models"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

// Search 模糊搜尋端點
func Search(c *gin.Context) {
	query := c.Query("q")

	if query == "" {
		c.JSON(http.StatusOK, gin.H{
			"results": []models.SearchResult{},
			"meta": gin.H{
				"queryTimeMs": 0,
				"resultCount": 0,
				"query":       "",
			},
		})
		return
	}

	startTime := time.Now()

	// 複雜的 SQL 查詢，實作四種模糊匹配
	sql := `
		WITH search_results AS (
			-- 1. Exact prefix match (最高優先級，精確匹配)
			SELECT 
				id,
				title,
				description,
				similarity(title, $1) + 0.5 AS sim,
				'exact_prefix' AS match_type
			FROM worlds
			WHERE title ILIKE $1 || '%'

			UNION ALL

			-- 2. Trigram similarity match (容錯匹配，使用 % 操作符)
			SELECT 
				id,
				title,
				description,
				similarity(title, $1) + 0.3 AS sim,
				'similarity' AS match_type
			FROM worlds
			WHERE title % $1
				AND NOT (title ILIKE $1 || '%')

			UNION ALL

			-- 3. Word similarity match (部分相似匹配，使用 <<% 操作符)
			SELECT 
				id,
				title,
				description,
				word_similarity($1, title) + 0.2 AS sim,
				'word_similarity' AS match_type
			FROM worlds
			WHERE $1 <<% title
				AND NOT (title ILIKE $1 || '%')
				AND NOT (title % $1)

			UNION ALL

			-- 4. Contains match (包含匹配，優先級較低)
			SELECT 
				id,
				title,
				description,
				similarity(title, $1) + 0.1 AS sim,
				'contains' AS match_type
			FROM worlds
			WHERE title ILIKE '%' || $1 || '%'
				AND NOT (title ILIKE $1 || '%')
				AND NOT (title % $1)
				AND NOT ($1 <<% title)
		)
		SELECT DISTINCT ON (id)
			id, title, description, sim, match_type
		FROM search_results
		WHERE sim > 0.2
		ORDER BY id, sim DESC
		LIMIT 20;
	`

	var rawResults []struct {
		ID          int
		Title       string
		Description string
		Sim         float64
		MatchType   string `gorm:"column:match_type"`
	}

	if err := config.DB.Raw(sql, query).Scan(&rawResults).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error":   "Search failed",
			"message": err.Error(),
		})
		return
	}

	// 轉換為回應格式
	results := make([]models.SearchResult, 0, len(rawResults))
	for _, r := range rawResults {
		results = append(results, models.SearchResult{
			Title:       r.Title,
			Description: r.Description,
			Similarity:  roundFloat(r.Sim, 3),
			MatchType:   r.MatchType,
		})
	}

	// 按相似度排序（已經在 SQL 中處理，但這裡再確保一次）
	// 由於 SQL 已經排序，這裡可以省略

	queryTimeMs := time.Since(startTime).Milliseconds()

	c.JSON(http.StatusOK, gin.H{
		"results": results,
		"meta": gin.H{
			"queryTimeMs": queryTimeMs,
			"resultCount": len(results),
			"query":       query,
		},
	})
}

// roundFloat 四捨五入到指定小數位數
func roundFloat(val float64, precision int) float64 {
	ratio := 1.0
	for i := 0; i < precision; i++ {
		ratio *= 10
	}
	return float64(int(val*ratio+0.5)) / ratio
}

