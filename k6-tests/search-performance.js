import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// 自訂指標
const errorRate = new Rate('errors');
const searchDuration = new Trend('search_duration');

// 測試配置
export const options = {
  // 預設場景: Load Test
  stages: [
    { duration: '30s', target: 10 },  // Ramp up to 10 users
    { duration: '1m', target: 10 },   // Stay at 10 users
    { duration: '30s', target: 0 },   // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'], // 95% 請求 < 500ms, 99% < 1s
    errors: ['rate<0.1'],  // 錯誤率 < 10%
    http_req_failed: ['rate<0.1'],
  },
};

// 測試場景配置 (可透過環境變數切換)
export function getScenario() {
  const scenario = __ENV.SCENARIO || 'load';
  
  const scenarios = {
    smoke: {
      stages: [
        { duration: '30s', target: 1 },
      ],
      description: 'Smoke test: 1 user for 30 seconds',
    },
    load: {
      stages: [
        { duration: '30s', target: 10 },
        { duration: '2m', target: 10 },
        { duration: '30s', target: 0 },
      ],
      description: 'Load test: 10 users for 2 minutes',
    },
    stress: {
      stages: [
        { duration: '1m', target: 20 },
        { duration: '2m', target: 50 },
        { duration: '1m', target: 0 },
      ],
      description: 'Stress test: up to 50 users',
    },
    spike: {
      stages: [
        { duration: '10s', target: 100 },
        { duration: '30s', target: 100 },
        { duration: '10s', target: 0 },
      ],
      description: 'Spike test: sudden 100 users',
    },
  };
  
  return scenarios[scenario] || scenarios.load;
}

// 測試用的搜尋關鍵字
const searchQueries = [
  'a1b2c3',      // 短查詢
  'abc123def',   // 中等查詢
  'test',        // 常見詞
  'xyz',         // 短詞
  'random',      // 一般詞
  '12345',       // 數字
  'abcdefgh',    // 較長查詢
  'md5',         // 技術詞
  'data',        // 常用詞
  'search',      // 功能詞
];

// 基礎 URL (可透過環境變數設定)
// 使用 [::1] 強制 IPv6,避免 IPv4 連到錯誤的服務
const BASE_URL = __ENV.BASE_URL || 'http://[::1]:3000';

export function setup() {
  console.log(`🚀 Starting k6 performance test`);
  console.log(`📍 Target: ${BASE_URL}`);
  console.log(`📊 Scenario: ${__ENV.SCENARIO || 'load'}`);
  
  // 檢查服務是否可用 (帶重試機制)
  let healthCheck;
  let attempts = 0;
  const maxAttempts = 5;
  
  while (attempts < maxAttempts) {
    attempts++;
    console.log(`🔍 Checking service health (attempt ${attempts}/${maxAttempts})...`);
    
    healthCheck = http.get(`${BASE_URL}/health`, {
      timeout: '10s',
    });
    
    if (healthCheck.status === 200) {
      break;
    }
    
    console.log(`⚠️  Service not ready (status: ${healthCheck.status}), waiting 3 seconds...`);
    sleep(3);
  }
  
  if (healthCheck.status !== 200) {
    console.error(`❌ Service is not available after ${maxAttempts} attempts`);
    console.error(`   Status: ${healthCheck.status}`);
    console.error(`   Body: ${healthCheck.body}`);
    throw new Error(`Service is not available (status: ${healthCheck.status})`);
  }
  
  const healthData = JSON.parse(healthCheck.body);
  console.log(`✅ Service is healthy`);
  console.log(`📦 Current records: ${healthData.records}`);
  
  return {
    baseUrl: BASE_URL,
    recordCount: healthData.records,
  };
}

export default function(data) {
  // 隨機選擇一個搜尋關鍵字
  const query = searchQueries[Math.floor(Math.random() * searchQueries.length)];
  
  // 執行搜尋請求
  const response = http.get(`${data.baseUrl}/search?q=${query}`, {
    tags: { name: 'search' },
  });
  
  // 檢查回應
  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
    'response time < 1000ms': (r) => r.timings.duration < 1000,
    'has results or meta': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.results !== undefined || body.meta !== undefined;
      } catch (e) {
        return false;
      }
    },
  });
  
  // 記錄錯誤率
  errorRate.add(!success);
  
  // 記錄搜尋時間
  if (response.status === 200) {
    try {
      const body = JSON.parse(response.body);
      if (body.meta && body.meta.queryTimeMs) {
        searchDuration.add(body.meta.queryTimeMs);
      }
    } catch (e) {
      // Ignore parse errors
    }
  }
  
  // 模擬使用者思考時間 (0.5-2秒)
  sleep(Math.random() * 1.5 + 0.5);
}

export function teardown(data) {
  console.log(`\n✅ Test completed`);
  console.log(`📦 Tested with ${data.recordCount} records`);
}

// ============================================================================
// 使用說明
// ============================================================================
// 
// 基本用法:
// k6 run k6-tests/search-performance.js
// 
// 指定場景:
// k6 run -e SCENARIO=smoke k6-tests/search-performance.js
// k6 run -e SCENARIO=load k6-tests/search-performance.js
// k6 run -e SCENARIO=stress k6-tests/search-performance.js
// k6 run -e SCENARIO=spike k6-tests/search-performance.js
// 
// 指定目標 URL:
// k6 run -e BASE_URL=http://localhost:3000 k6-tests/search-performance.js
// 
// 輸出結果到檔案:
// k6 run k6-tests/search-performance.js --out json=results.json
// 
// 輸出到 InfluxDB (需先安裝):
// k6 run k6-tests/search-performance.js --out influxdb=http://localhost:8086/k6
// 
// ============================================================================

