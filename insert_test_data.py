#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动插入测试数据到 Supabase
"""

import requests
import json

SUPABASE_URL = "https://hnlkwtkxbqiakeyienok.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhubGt3dGt4YnFpYWtleWllbm9rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY5MDQwNTksImV4cCI6MjA4MjQ4MDA1OX0.Xg9vQdUfBdUW-IJaomEIRGsX6tB_k2grhrF4dm_aNME"

headers = {
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "apikey": SUPABASE_KEY
}

# 测试数据
test_nodes = [
    {
        "id": "1.2.3.4:1234",
        "content": {
            "id": "test1",
            "name": "测试节点1",
            "host": "1.2.3.4",
            "port": 1234,
            "country": "CN",
            "mainland_score": 80,
            "mainland_latency": 50,
            "overseas_score": 75,
            "overseas_latency": 60,
            "alive": True
        },
        "is_free": True,
        "mainland_score": 80,
        "mainland_latency": 50,
        "overseas_score": 75,
        "overseas_latency": 60,
        "speed": 80,
        "latency": 50,
        "updated_at": "2024-01-01T00:00:00"
    },
    {
        "id": "5.6.7.8:5678",
        "content": {
            "id": "test2",
            "name": "测试节点2",
            "host": "5.6.7.8",
            "port": 5678,
            "country": "US",
            "mainland_score": 90,
            "mainland_latency": 40,
            "overseas_score": 85,
            "overseas_latency": 55,
            "alive": True
        },
        "is_free": False,
        "mainland_score": 90,
        "mainland_latency": 40,
        "overseas_score": 85,
        "overseas_latency": 55,
        "speed": 90,
        "latency": 40,
        "updated_at": "2024-01-01T00:00:00"
    }
]

url = f"{SUPABASE_URL}/rest/v1/nodes"

for node in test_nodes:
    response = requests.post(url, headers=headers, data=json.dumps(node))
    print(f"插入 {node['id']}: {response.status_code}")
    if response.status_code != 201:
        print(f"错误: {response.text}")