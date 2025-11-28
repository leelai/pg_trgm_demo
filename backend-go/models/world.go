package models

import (
	"time"
)

// World 資料模型
type World struct {
	ID          int       `gorm:"primaryKey;autoIncrement" json:"id"`
	Title       string    `gorm:"type:text;not null" json:"title"`
	Description string    `gorm:"type:text" json:"description"`
	CreatedAt   time.Time `gorm:"autoCreateTime" json:"created_at"`
}

// TableName 指定表名
func (World) TableName() string {
	return "worlds"
}

// SearchResult 搜尋結果結構
type SearchResult struct {
	ID          int     `json:"-"`
	Title       string  `json:"title"`
	Description string  `json:"description"`
	Similarity  float64 `json:"similarity"`
	MatchType   string  `json:"matchType"`
}

// DataStats 資料統計結構
type DataStats struct {
	TotalRecords int64  `json:"totalRecords"`
	TableSize    string `json:"tableSize"`
	IndexSize    string `json:"indexSize"`
	TotalSize    string `json:"totalSize"`
}

// GenerateDataResult 產生資料結果
type GenerateDataResult struct {
	InsertedCount   int     `json:"insertedCount"`
	ExecutionTimeMs float64 `json:"executionTimeMs"`
}

// ClearDataResult 清空資料結果
type ClearDataResult struct {
	DeletedCount    int     `json:"deletedCount"`
	ExecutionTimeMs float64 `json:"executionTimeMs"`
	VacuumTimeMs    int64   `json:"vacuumTimeMs"`
}

// RebuildIndexesResult 重建索引結果
type RebuildIndexesResult struct {
	Status          string  `json:"status"`
	ExecutionTimeMs float64 `json:"executionTimeMs"`
}

