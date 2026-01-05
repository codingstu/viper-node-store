#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Supabase-based API endpoints
验证所有 API 端点是否从 Supabase 正确读取数据
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8002"

def test_status():
    """Test /api/status endpoint"""
    print("\n" + "="*60)
    print("测试 /api/status")
    print("="*60)
    try:
        resp = requests.get(f"{BASE_URL}/api/status", timeout=5)
        data = resp.json()
        print(f"✅ 状态码: {resp.status_code}")
        print(f"✅ 数据来源: {data.get('data_source')}")
        print(f"✅ 版本: {data.get('version')}")
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_sync_info():
    """Test /api/sync-info endpoint"""
    print("\n" + "="*60)
    print("测试 /api/sync-info")
    print("="*60)
    try:
        resp = requests.get(f"{BASE_URL}/api/sync-info", timeout=5)
        data = resp.json()
        print(f"✅ 状态码: {resp.status_code}")
        print(f"✅ 最后更新: {data.get('last_updated_at')}")
        print(f"✅ 分钟前: {data.get('minutes_ago')} 分钟前")
        print(f"✅ 节点总数: {data.get('nodes_count')}")
        print(f"✅ 活跃节点: {data.get('active_count')}")
        print(f"✅ 数据来源: {data.get('source')}")
        
        # Check data is from Supabase
        if data.get('source') == 'supabase':
            print("✅ 数据源验证成功 - 来自 Supabase")
        else:
            print(f"❌ 数据源错误 - 预期 'supabase'，获得 '{data.get('source')}'")
        
        return resp.status_code == 200 and data.get('source') == 'supabase'
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_nodes():
    """Test /api/nodes endpoint"""
    print("\n" + "="*60)
    print("测试 /api/nodes")
    print("="*60)
    try:
        resp = requests.get(f"{BASE_URL}/api/nodes?limit=5", timeout=5)
        data = resp.json()
        print(f"✅ 状态码: {resp.status_code}")
        print(f"✅ 返回节点数: {len(data)}")
        
        if len(data) > 0:
            node = data[0]
            print(f"\n第一个节点信息:")
            print(f"  - ID: {node.get('id')}")
            print(f"  - 协议: {node.get('protocol')}")
            print(f"  - 主机: {node.get('host')}")
            print(f"  - 端口: {node.get('port')}")
            print(f"  - 速度: {node.get('speed')} bytes/s")
            print(f"  - 延迟: {node.get('latency')} ms")
            print(f"  - 状态: {'活跃' if node.get('alive') else '离线'}")
            print(f"  - 最后更新: {node.get('updated_at')}")
        
        return resp.status_code == 200 and len(data) > 0
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_precision_test():
    """Test /api/nodes/precision-test endpoint"""
    print("\n" + "="*60)
    print("测试 /api/nodes/precision-test (精确测速)")
    print("="*60)
    print("⚠️  注意: 此测试将下载 50MB 数据，可能耗时较长")
    
    try:
        # 使用 Cloudflare 速度测试，较小的文件 (10MB)
        payload = {
            "proxy_url": "https://speed.cloudflare.com",
            "test_file_size": 10
        }
        
        print(f"📤 发送请求: {json.dumps(payload)}")
        start_time = time.time()
        
        resp = requests.post(f"{BASE_URL}/api/nodes/precision-test", 
                           json=payload, timeout=30)
        
        elapsed = time.time() - start_time
        data = resp.json()
        
        print(f"✅ 状态码: {resp.status_code}")
        print(f"✅ 耗时: {elapsed:.1f} 秒")
        print(f"✅ 测速状态: {data.get('status')}")
        print(f"✅ 下载速度: {data.get('speed_mbps')} MB/s")
        print(f"✅ 下载时间: {data.get('download_time_seconds')} 秒")
        print(f"✅ 消耗流量: {data.get('traffic_consumed_mb')} MB")
        
        return resp.status_code == 200
    except requests.Timeout:
        print(f"⏱️  测试超时 (>30秒)")
        return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_latency_test():
    """Test /api/nodes/latency-test endpoint"""
    print("\n" + "="*60)
    print("测试 /api/nodes/latency-test (延迟测试)")
    print("="*60)
    
    try:
        payload = {
            "proxy_url": "https://cloudflare.com"
        }
        
        print(f"📤 发送请求: {json.dumps(payload)}")
        
        resp = requests.post(f"{BASE_URL}/api/nodes/latency-test", 
                           json=payload, timeout=10)
        
        data = resp.json()
        
        print(f"✅ 状态码: {resp.status_code}")
        print(f"✅ 延迟状态: {data.get('status')}")
        print(f"✅ 延迟: {data.get('latency')} ms")
        
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_poll_trigger():
    """Test /api/sync/poll-now endpoint"""
    print("\n" + "="*60)
    print("测试 /api/sync/poll-now (触发轮询)")
    print("="*60)
    
    try:
        resp = requests.post(f"{BASE_URL}/api/sync/poll-now", timeout=5)
        data = resp.json()
        
        print(f"✅ 状态码: {resp.status_code}")
        print(f"✅ 状态: {data.get('status')}")
        print(f"✅ 消息: {data.get('message')}")
        
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def main():
    print("\n" + "🧪 " * 30)
    print("viper-node-store Supabase API 测试套件")
    print("🧪 " * 30)
    
    results = {
        "status": test_status(),
        "sync_info": test_sync_info(),
        "nodes": test_nodes(),
        "poll_trigger": test_poll_trigger(),
        "latency_test": test_latency_test(),
        # 注意：不自动测试 precision_test，因为需要下载数据
    }
    
    print("\n" + "="*60)
    print("测试结果摘要")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name.upper()}: {status}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\n总体: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有关键测试都通过了！")
        print("\nℹ️  可选: 运行以下命令测试精确下载速度:")
        print(f"   curl -X POST {BASE_URL}/api/nodes/precision-test -H 'Content-Type: application/json' -d '{{\"proxy_url\": \"https://speed.cloudflare.com\", \"test_file_size\": 10}}'")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查日志")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
