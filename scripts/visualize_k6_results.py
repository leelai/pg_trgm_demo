#!/usr/bin/env python3
"""
k6 測試結果視覺化工具
解析多個 k6 JSON 結果檔案,產生效能比較圖表
"""

import json
import glob
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 非互動式後端

def parse_k6_json(filename):
    """解析 k6 JSON 輸出檔案"""
    metrics = defaultdict(list)
    data_volume = None
    
    # 從檔名提取資料量
    match = re.search(r'k6_(\d+)_', filename)
    if match:
        data_volume = int(match.group(1))
    
    # 解析 JSONL 格式 (每行一個 JSON 物件)
    with open(filename, 'r') as f:
        for line in f:
            try:
                obj = json.loads(line.strip())
                if obj.get('type') == 'Point' and 'data' in obj:
                    metric_name = obj.get('metric')
                    data = obj['data']
                    
                    # 只收集搜尋相關的 metrics (排除 setup)
                    tags = data.get('tags', {})
                    if tags.get('group') == '' and 'scenario' in tags:
                        value = data.get('value')
                        if value is not None:
                            metrics[metric_name].append(value)
            except json.JSONDecodeError:
                continue
    
    # 計算統計值
    stats = {}
    for metric_name, values in metrics.items():
        if values:
            values = [v for v in values if isinstance(v, (int, float))]
            if values:
                sorted_values = sorted(values)
                stats[metric_name] = {
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'p50': sorted_values[len(sorted_values) // 2],
                    'p95': sorted_values[int(len(sorted_values) * 0.95)] if len(sorted_values) > 1 else sorted_values[0],
                    'p99': sorted_values[int(len(sorted_values) * 0.99)] if len(sorted_values) > 1 else sorted_values[0],
                    'count': len(values)
                }
    
    return data_volume, stats

def create_visualization():
    """產生視覺化圖表"""
    # 找出所有 k6 結果檔案
    json_files = sorted(glob.glob('test-results/k6_*.json'))
    
    if not json_files:
        print("❌ 找不到 k6 測試結果檔案")
        print("   請先執行: ./scripts/run-performance-tests.sh")
        return
    
    print(f"📊 找到 {len(json_files)} 個測試結果檔案")
    
    # 解析所有檔案
    results = {}
    for json_file in json_files:
        print(f"  📄 解析 {json_file}...", end=' ')
        data_volume, stats = parse_k6_json(json_file)
        if data_volume and stats:
            results[data_volume] = stats
            print(f"✓ ({data_volume:,} 筆資料)")
        else:
            print("✗ (無法解析)")
    
    if not results:
        print("❌ 無法解析測試結果")
        return
    
    # 排序資料量
    volumes = sorted(results.keys())
    print(f"\n✅ 成功解析 {len(volumes)} 個測試結果")
    
    # 建立圖表
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('pg_trgm 搜尋效能測試 - 資料量影響分析', fontsize=16, fontweight='bold')
    
    # 1. 回應時間比較 (p50, p95, p99)
    ax1 = axes[0, 0]
    p50_values = [results[v].get('http_req_duration', {}).get('p50', 0) for v in volumes]
    p95_values = [results[v].get('http_req_duration', {}).get('p95', 0) for v in volumes]
    p99_values = [results[v].get('http_req_duration', {}).get('p99', 0) for v in volumes]
    
    ax1.plot(volumes, p50_values, 'o-', label='p50 (中位數)', linewidth=2, markersize=8, color='#4CAF50')
    ax1.plot(volumes, p95_values, 's-', label='p95', linewidth=2, markersize=8, color='#FF9800')
    ax1.plot(volumes, p99_values, '^-', label='p99', linewidth=2, markersize=8, color='#F44336')
    ax1.set_xlabel('資料量 (筆)', fontsize=12)
    ax1.set_ylabel('回應時間 (ms)', fontsize=12)
    ax1.set_title('HTTP 回應時間分佈', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    if len(volumes) > 3:
        ax1.set_xscale('log')
    
    # 2. 平均回應時間
    ax2 = axes[0, 1]
    avg_values = [results[v].get('http_req_duration', {}).get('avg', 0) for v in volumes]
    colors = ['#667eea' if v < 100 else '#FF9800' if v < 500 else '#F44336' for v in avg_values]
    bars = ax2.bar(range(len(volumes)), avg_values, color=colors, alpha=0.7)
    ax2.set_xticks(range(len(volumes)))
    ax2.set_xticklabels([f'{v:,}' for v in volumes], rotation=45, ha='right')
    ax2.set_xlabel('資料量 (筆)', fontsize=12)
    ax2.set_ylabel('平均回應時間 (ms)', fontsize=12)
    ax2.set_title('平均回應時間', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # 在柱狀圖上顯示數值
    for i, v in enumerate(avg_values):
        ax2.text(i, v, f'{v:.1f}ms', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # 3. 搜尋查詢時間 (search_duration)
    ax3 = axes[1, 0]
    search_avg = [results[v].get('search_duration', {}).get('avg', 0) for v in volumes]
    search_p95 = [results[v].get('search_duration', {}).get('p95', 0) for v in volumes]
    
    x_pos = range(len(volumes))
    width = 0.35
    ax3.bar([x - width/2 for x in x_pos], search_avg, width, label='平均', alpha=0.7, color='#2196F3')
    ax3.bar([x + width/2 for x in x_pos], search_p95, width, label='p95', alpha=0.7, color='#FF5722')
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels([f'{v:,}' for v in volumes], rotation=45, ha='right')
    ax3.set_xlabel('資料量 (筆)', fontsize=12)
    ax3.set_ylabel('查詢時間 (ms)', fontsize=12)
    ax3.set_title('資料庫查詢時間 (來自 API meta)', fontsize=14, fontweight='bold')
    ax3.legend(fontsize=10)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 4. 請求總數和迭代次數
    ax4 = axes[1, 1]
    iterations = [results[v].get('iterations', {}).get('count', 0) for v in volumes]
    http_reqs = [results[v].get('http_reqs', {}).get('count', 0) for v in volumes]
    
    x_pos = range(len(volumes))
    width = 0.35
    ax4.bar([x - width/2 for x in x_pos], iterations, width, label='Iterations', alpha=0.7, color='#9C27B0')
    ax4.bar([x + width/2 for x in x_pos], http_reqs, width, label='HTTP Requests', alpha=0.7, color='#00BCD4')
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels([f'{v:,}' for v in volumes], rotation=45, ha='right')
    ax4.set_xlabel('資料量 (筆)', fontsize=12)
    ax4.set_ylabel('數量', fontsize=12)
    ax4.set_title('測試執行統計', fontsize=14, fontweight='bold')
    ax4.legend(fontsize=10)
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    # 儲存圖表
    output_file = 'test-results/performance_comparison.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✅ 圖表已儲存至: {output_file}")
    
    # 產生 HTML 報告
    create_html_report(results, volumes, output_file)
    
    # 顯示摘要
    print("\n📊 測試結果摘要:")
    print("=" * 80)
    print(f"{'資料量':<15} {'平均回應':<15} {'p95':<15} {'p99':<15} {'請求數':<15}")
    print("-" * 80)
    for volume in volumes:
        stats = results[volume]
        http_duration = stats.get('http_req_duration', {})
        iterations = stats.get('iterations', {})
        print(f"{volume:>10,} 筆  {http_duration.get('avg', 0):>10.2f}ms  "
              f"{http_duration.get('p95', 0):>10.2f}ms  "
              f"{http_duration.get('p99', 0):>10.2f}ms  "
              f"{iterations.get('count', 0):>10,}")
    print("=" * 80)

def create_html_report(results, volumes, chart_file):
    """產生 HTML 報告"""
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>pg_trgm 效能測試報告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            color: #333;
            padding: 40px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .header p {{
            font-size: 1.2em;
            color: #666;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .summary-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }}
        .summary-card h3 {{
            font-size: 0.9em;
            color: #667eea;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .summary-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }}
        .summary-card .subtitle {{
            font-size: 0.9em;
            color: #999;
        }}
        .chart-container {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .chart-container h2 {{
            margin-bottom: 20px;
            color: #333;
            font-size: 1.8em;
        }}
        .chart-container img {{
            width: 100%;
            height: auto;
            border-radius: 10px;
        }}
        .table-container {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            overflow-x: auto;
        }}
        .table-container h2 {{
            margin-bottom: 20px;
            color: #333;
            font-size: 1.8em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .metric-value {{
            font-weight: 600;
            color: #667eea;
            font-size: 1.1em;
        }}
        .good {{
            color: #4CAF50;
        }}
        .warning {{
            color: #FF9800;
        }}
        .bad {{
            color: #F44336;
        }}
        .footer {{
            text-align: center;
            color: white;
            margin-top: 30px;
            padding: 20px;
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 pg_trgm 效能測試報告</h1>
            <p>資料量對搜尋效能的影響分析</p>
        </div>
        
        <div class="summary">
"""
    
    # 計算總結統計
    if volumes:
        first_volume = volumes[0]
        last_volume = volumes[-1]
        first_avg = results[first_volume].get('http_req_duration', {}).get('avg', 0)
        last_avg = results[last_volume].get('http_req_duration', {}).get('avg', 0)
        growth_rate = ((last_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0
        
        # 找出最佳和最差效能
        best_volume = min(volumes, key=lambda v: results[v].get('http_req_duration', {}).get('avg', float('inf')))
        worst_volume = max(volumes, key=lambda v: results[v].get('http_req_duration', {}).get('avg', 0))
        
        html += f"""
            <div class="summary-card">
                <h3>測試資料量範圍</h3>
                <div class="value">{len(volumes)}</div>
                <div class="subtitle">{first_volume:,} - {last_volume:,} 筆</div>
            </div>
            <div class="summary-card">
                <h3>效能變化率</h3>
                <div class="value {'good' if growth_rate < 50 else 'warning' if growth_rate < 100 else 'bad'}">{growth_rate:+.1f}%</div>
                <div class="subtitle">平均回應時間變化</div>
            </div>
            <div class="summary-card">
                <h3>最佳效能</h3>
                <div class="value good">{first_avg:.1f}ms</div>
                <div class="subtitle">{best_volume:,} 筆資料</div>
            </div>
            <div class="summary-card">
                <h3>最大負載</h3>
                <div class="value {'warning' if last_avg < 500 else 'bad'}">{last_avg:.1f}ms</div>
                <div class="subtitle">{worst_volume:,} 筆資料</div>
            </div>
        </div>
"""
    
    html += f"""
        <div class="chart-container">
            <h2>📈 效能比較圖表</h2>
            <img src="performance_comparison.png" alt="效能比較圖表">
        </div>
        
        <div class="table-container">
            <h2>📋 詳細數據</h2>
            <table>
                <thead>
                    <tr>
                        <th>資料量</th>
                        <th>平均回應時間</th>
                        <th>p50 (中位數)</th>
                        <th>p95</th>
                        <th>p99</th>
                        <th>平均查詢時間</th>
                        <th>總請求數</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for volume in volumes:
        stats = results[volume]
        http_duration = stats.get('http_req_duration', {})
        search_duration = stats.get('search_duration', {})
        iterations = stats.get('iterations', {})
        
        avg_val = http_duration.get('avg', 0)
        avg_class = 'good' if avg_val < 100 else 'warning' if avg_val < 500 else 'bad'
        
        html += f"""
                    <tr>
                        <td><strong>{volume:,} 筆</strong></td>
                        <td><span class="metric-value {avg_class}">{avg_val:.2f}ms</span></td>
                        <td>{http_duration.get('p50', 0):.2f}ms</td>
                        <td>{http_duration.get('p95', 0):.2f}ms</td>
                        <td>{http_duration.get('p99', 0):.2f}ms</td>
                        <td>{search_duration.get('avg', 0):.2f}ms</td>
                        <td>{iterations.get('count', 0):,}</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>🚀 Generated by pg_trgm Performance Test Suite</p>
            <p>使用 k6 負載測試工具 | PostgreSQL pg_trgm 模糊搜尋</p>
        </div>
    </div>
</body>
</html>
"""
    
    output_file = 'test-results/performance_report.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML 報告已儲存至: {output_file}")
    print(f"   在瀏覽器開啟: file://{output_file}")

if __name__ == '__main__':
    print("=" * 80)
    print("pg_trgm 效能測試結果視覺化工具")
    print("=" * 80)
    create_visualization()
    print("\n" + "=" * 80)
    print("✨ 視覺化完成!")
    print("=" * 80)


