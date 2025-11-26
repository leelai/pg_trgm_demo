const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = 3000;

// PostgreSQL connection pool
// Use environment variables for Docker, fallback to localhost for local dev
const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'testdb',
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'password',
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// 設定 pg_trgm 相似度閾值（會話級別）
// 這確保每個連線都使用相同的模糊搜尋閾值
pool.on('connect', (client) => {
  client.query('SET pg_trgm.similarity_threshold = 0.3');
  client.query('SET pg_trgm.word_similarity_threshold = 0.6');
});

// Middleware
app.use(cors());
app.use(express.json());

// Serve static frontend files
app.use(express.static(path.join(__dirname, '../frontend')));

// Health check endpoint
app.get('/health', async (req, res) => {
  try {
    const result = await pool.query('SELECT COUNT(*) FROM worlds');
    res.json({
      status: 'ok',
      database: 'connected',
      records: parseInt(result.rows[0].count)
    });
  } catch (error) {
    res.status(500).json({
      status: 'error',
      message: error.message
    });
  }
});

// Admin API: Get data statistics
app.get('/admin/data/stats', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM get_data_stats()');
    const stats = result.rows[0];
    
    res.json({
      success: true,
      data: {
        totalRecords: parseInt(stats.total_records),
        tableSize: stats.table_size,
        indexSize: stats.index_size,
        totalSize: stats.total_size
      }
    });
  } catch (error) {
    console.error('Stats error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get statistics',
      message: error.message
    });
  }
});

// Admin API: Generate test data
app.post('/admin/data/generate', async (req, res) => {
  const count = parseInt(req.body.count) || 10000;
  
  // Validate count
  if (count < 1 || count > 1000000) {
    return res.status(400).json({
      success: false,
      error: 'Invalid count. Must be between 1 and 1,000,000'
    });
  }
  
  try {
    console.log(`Generating ${count} test records...`);
    const result = await pool.query('SELECT * FROM generate_test_data($1)', [count]);
    const data = result.rows[0];
    
    console.log(`Generated ${data.inserted_count} records in ${data.execution_time_ms}ms`);
    
    res.json({
      success: true,
      data: {
        insertedCount: parseInt(data.inserted_count),
        executionTimeMs: parseFloat(parseFloat(data.execution_time_ms).toFixed(2))
      }
    });
  } catch (error) {
    console.error('Generate error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to generate data',
      message: error.message
    });
  }
});

// Admin API: Clear all data
app.delete('/admin/data/clear', async (req, res) => {
  try {
    console.log('Clearing all data...');
    const result = await pool.query('SELECT * FROM clear_all_data()');
    const data = result.rows[0];
    
    console.log(`Deleted ${data.deleted_count} records in ${data.execution_time_ms}ms`);
    
    // 執行 VACUUM ANALYZE (必須在函數外執行)
    console.log('Running VACUUM ANALYZE...');
    const vacuumStart = Date.now();
    await pool.query('VACUUM ANALYZE worlds');
    const vacuumTime = Date.now() - vacuumStart;
    console.log(`VACUUM completed in ${vacuumTime}ms`);
    
    res.json({
      success: true,
      data: {
        deletedCount: parseInt(data.deleted_count),
        executionTimeMs: parseFloat(parseFloat(data.execution_time_ms).toFixed(2)),
        vacuumTimeMs: vacuumTime
      }
    });
  } catch (error) {
    console.error('Clear error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to clear data',
      message: error.message
    });
  }
});

// Admin API: Rebuild indexes
app.post('/admin/data/rebuild-indexes', async (req, res) => {
  try {
    console.log('Rebuilding indexes...');
    const result = await pool.query('SELECT * FROM rebuild_indexes()');
    const data = result.rows[0];
    
    console.log(`Indexes rebuilt in ${data.execution_time_ms}ms`);
    
    res.json({
      success: true,
      data: {
        status: data.status,
        executionTimeMs: parseFloat(parseFloat(data.execution_time_ms).toFixed(2))
      }
    });
  } catch (error) {
    console.error('Rebuild indexes error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to rebuild indexes',
      message: error.message
    });
  }
});

// Fuzzy search endpoint
app.get('/search', async (req, res) => {
  const query = req.query.q;
  
  if (!query || query.trim().length === 0) {
    return res.json([]);
  }
  
  try {
    // Record start time
    const startTime = Date.now();
    
    // Combined fuzzy search query using UNION ALL
    // This implements four types of fuzzy matching with fault tolerance:
    // 1. Exact prefix match (highest priority) - e.g., "harri" finds "Harrison"
    // 2. Trigram similarity match (%) - e.g., "harri" finds "Harry" (fault tolerant!)
    // 3. Word similarity match (<<%>) - e.g., "harri" finds "Harold Potter"
    // 4. Contains match (fallback) - e.g., "harri" finds "Harriett"
    
    const sql = `
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
        -- 這會找到相似但不完全相同的字串，例如 "harri" 可以找到 "Harry"
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
        -- 適合搜尋詞出現在較長字串中的情況
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
      `;
    
    const result = await pool.query(sql, [query]);
    
    // Calculate query execution time
    const queryTimeMs = Date.now() - startTime;
    
    // Format results
    const formattedResults = result.rows.map(row => ({
      title: row.title,
      description: row.description || '',
      similarity: parseFloat(row.sim.toFixed(3)),
      matchType: row.match_type
    }));
    
    // Sort by similarity descending
    formattedResults.sort((a, b) => b.similarity - a.similarity);
    
    // Return results with query time
    res.json({
      results: formattedResults,
      meta: {
        queryTimeMs: queryTimeMs,
        resultCount: formattedResults.length,
        query: query
      }
    });
  } catch (error) {
    console.error('Search error:', error);
    res.status(500).json({
      error: 'Search failed',
      message: error.message
    });
  }
});

// Root endpoint - serve frontend
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/index.html'));
});

// Start server
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
  console.log(`Search endpoint: http://localhost:${PORT}/search?q=your_query`);
  console.log(`Health check: http://localhost:${PORT}/health`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM signal received: closing HTTP server');
  pool.end(() => {
    console.log('Database pool closed');
  });
});
