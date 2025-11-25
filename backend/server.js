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

// Fuzzy search endpoint
app.get('/search', async (req, res) => {
  const query = req.query.q;
  
  if (!query || query.trim().length === 0) {
    return res.json([]);
  }
  
  try {
    // Combined fuzzy search query using UNION ALL
    // This implements three types of fuzzy matching:
    // 1. Prefix autocomplete (highest priority)
    // 2. Contains keyword (medium priority)
    // 3. Similarity-based fuzzy match (flexible matching)
    
    const sql = `
      WITH search_results AS (
        -- 1. Prefix autocomplete: exact prefix match
        SELECT 
          id,
          title, 
          description,
          similarity(title, $1) + 0.5 AS sim,
          'prefix' AS match_type
        FROM worlds
        WHERE title ILIKE $1 || '%'
        
        UNION ALL
        
        -- 2. Contains keyword: substring match
        SELECT 
          id,
          title, 
          description,
          similarity(title, $1) + 0.3 AS sim,
          'contains' AS match_type
        FROM worlds
        WHERE title ILIKE '%' || $1 || '%'
          AND NOT (title ILIKE $1 || '%')  -- Exclude prefix matches
        
        UNION ALL
        
        -- 3. Fuzzy similarity: trigram-based matching
        SELECT 
          id,
          title, 
          description,
          similarity(title, $1) AS sim,
          'fuzzy' AS match_type
        FROM worlds
        WHERE title % $1  -- Trigram similarity operator
          AND NOT (title ILIKE '%' || $1 || '%')  -- Exclude exact substring matches
      )
      SELECT DISTINCT ON (id)
        id,
        title,
        description,
        sim,
        match_type
      FROM search_results
      ORDER BY id, sim DESC
      LIMIT 20
    `;
    
    const result = await pool.query(sql, [query]);
    
    // Format results
    const formattedResults = result.rows.map(row => ({
      title: row.title,
      description: row.description || '',
      similarity: parseFloat(row.sim.toFixed(3)),
      matchType: row.match_type
    }));
    
    // Sort by similarity descending
    formattedResults.sort((a, b) => b.similarity - a.similarity);
    
    res.json(formattedResults);
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
