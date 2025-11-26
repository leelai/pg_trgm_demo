#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試容錯搜尋功能
"""

import psycopg2
import requests
import json
from typing import List, Dict

# 資料庫連線設定
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'testdb',
    'user': 'postgres',
    'password': 'password'
}

# API 端點
API_URL = 'http://localhost:3000/search'

def insert_test_data():
    """插入測試資料"""
    print("🔧 插入測試資料...")
    
    test_data = [
        ('Harry', 'A young wizard'),
        ('Harold', 'An old king'),
        ('Harriett', 'A brave woman'),
        ('Harrison', 'A famous actor'),
        ('Harris', 'A common surname'),
        ('Garry', 'Very similar to Harry'),
        ('Larry', 'Similar ending to Harry'),
        ('Barry', 'Another similar name'),
        ('Henry', 'Somewhat similar'),
        ('Harvey', 'Similar beginning'),
    ]
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # 先刪除舊的測試資料
    cur.execute("DELETE FROM worlds WHERE title IN ('Harry', 'Harold', 'Harriett', 'Harrison', 'Harris', 'Garry', 'Larry', 'Barry', 'Henry', 'Harvey')")
    
    # 插入新的測試資料
    for title, description in test_data:
        cur.execute("INSERT INTO worlds (title, description) VALUES (%s, %s)", (title, description))
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✓ 成功插入 {len(test_data)} 筆測試資料")

def test_search(query: str) -> List[Dict]:
    """測試搜尋功能"""
    print(f"\n🔍 搜尋: '{query}'")
    
    response = requests.get(API_URL, params={'q': query})
    
    if response.status_code != 200:
        print(f"❌ 錯誤: {response.status_code}")
        return []
    
    data = response.json()
    
    if isinstance(data, dict):
        results = data.get('results', [])
        meta = data.get('meta', {})
        print(f"   查詢時間: {meta.get('queryTimeMs', 0)}ms")
        print(f"   結果數量: {meta.get('resultCount', 0)}")
    else:
        results = data
    
    print("\n   結果:")
    if not results:
        print("   (無結果)")
    else:
        for i, result in enumerate(results, 1):
            title = result.get('title', '')
            similarity = result.get('similarity', 0)
            match_type = result.get('matchType', 'unknown')
            print(f"   {i}. {title:20s} (相似度: {similarity:.3f}, 類型: {match_type})")
    
    return results

def check_tolerance():
    """檢查容錯功能"""
    print("\n" + "="*60)
    print("容錯測試結果")
    print("="*60)
    
    # 測試 1: 搜尋 "harri" 應該找到 Harry, Harold, Harriett, Harrison, Harris
    print("\n【測試 1】搜尋 'harri' (少了一個字母)")
    results = test_search('harri')
    found_names = [r.get('title', '') for r in results]
    
    expected = ['Harry', 'Harold', 'Harriett', 'Harrison', 'Harris']
    found = []
    not_found = []
    
    for name in expected:
        if name in found_names:
            found.append(name)
        else:
            not_found.append(name)
    
    print(f"\n   ✓ 找到: {', '.join(found) if found else '(無)'}")
    print(f"   ✗ 未找到: {', '.join(not_found) if not_found else '(無)'}")
    
    # 測試 2: 搜尋 "hary" (拼錯)
    print("\n【測試 2】搜尋 'hary' (拼錯，少了一個 r)")
    results = test_search('hary')
    found_names = [r.get('title', '') for r in results]
    print(f"   應該找到 'Harry': {'✓' if 'Harry' in found_names else '✗'}")
    
    # 測試 3: 搜尋 "hari" (拼錯)
    print("\n【測試 3】搜尋 'hari' (拼錯，少了一個 r)")
    results = test_search('hari')
    found_names = [r.get('title', '') for r in results]
    print(f"   應該找到 'Harry': {'✓' if 'Harry' in found_names else '✗'}")
    
    # 測試 4: 搜尋 "harrry" (拼錯，多了一個 r)
    print("\n【測試 4】搜尋 'harrry' (拼錯，多了一個 r)")
    results = test_search('harrry')
    found_names = [r.get('title', '') for r in results]
    print(f"   應該找到 'Harry': {'✓' if 'Harry' in found_names else '✗'}")
    
    print("\n" + "="*60)

def main():
    print("="*60)
    print("PostgreSQL Trigram 容錯搜尋測試")
    print("="*60)
    
    try:
        # 插入測試資料
        insert_test_data()
        
        # 等待一下讓資料完全寫入
        import time
        time.sleep(1)
        
        # 執行容錯測試
        check_tolerance()
        
        print("\n✅ 測試完成！")
        
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

