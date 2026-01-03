#!/usr/bin/env python3
"""
健康检测模块本地测试脚本

用法：
    python test_health_checker.py
"""

import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from health_checker import LightweightHealthChecker, NodeStatus


async def test_tcp_check():
    """测试 TCP 连接检测"""
    print("\n🧪 测试 1: TCP 连接检测")
    print("-" * 40)
    
    checker = LightweightHealthChecker(tcp_timeout=5.0)
    
    # 测试一些公共服务器
    test_cases = [
        ("1.1.1.1", 443, "Cloudflare DNS (应该成功)"),
        ("8.8.8.8", 53, "Google DNS (应该成功)"),
        ("192.0.2.1", 80, "TEST-NET (应该失败)"),
    ]
    
    for host, port, desc in test_cases:
        ok, latency, error = await checker.check_tcp_connection(host, port)
        status = "✅" if ok else "❌"
        latency_str = f"{latency}ms" if latency else "N/A"
        error_str = f"({error})" if error else ""
        print(f"  {status} {host}:{port} - {desc}")
        print(f"     延迟: {latency_str} {error_str}")


async def test_node_check():
    """测试完整节点检测"""
    print("\n🧪 测试 2: 完整节点检测")
    print("-" * 40)
    
    checker = LightweightHealthChecker(
        tcp_timeout=5.0,
        http_timeout=8.0,
        max_retries=1  # 测试时只重试1次
    )
    
    # 模拟一些节点
    test_nodes = [
        {
            "id": "test-1",
            "host": "1.1.1.1",
            "port": 443,
            "protocol": "vmess",
            "name": "Cloudflare DNS"
        },
        {
            "id": "test-2",
            "host": "invalid.example.com",
            "port": 12345,
            "protocol": "trojan",
            "name": "Invalid Node"
        }
    ]
    
    for node in test_nodes:
        result = await checker.check_node(node)
        status_icon = {
            NodeStatus.ONLINE: "🟢",
            NodeStatus.OFFLINE: "🔴",
            NodeStatus.SUSPECT: "🟡",
            NodeStatus.UNKNOWN: "⚪"
        }.get(result.status, "❓")
        
        print(f"  {status_icon} {node['name']} ({node['host']}:{node['port']})")
        print(f"     状态: {result.status.value}")
        print(f"     TCP: {'✅' if result.tcp_ok else '❌'}")
        print(f"     HTTP: {'✅' if result.http_ok else '❌'}")
        print(f"     延迟: {result.latency_ms}ms" if result.latency_ms else "     延迟: N/A")
        print(f"     重试: {result.retry_count}")
        if result.error_message:
            print(f"     错误: {result.error_message}")


async def test_batch_check():
    """测试批量检测"""
    print("\n🧪 测试 3: 批量节点检测")
    print("-" * 40)
    
    checker = LightweightHealthChecker(
        tcp_timeout=3.0,
        http_timeout=5.0,
        max_retries=1,
        max_concurrent=5
    )
    
    # 创建一批测试节点
    test_nodes = [
        {"id": f"batch-{i}", "host": f"192.0.2.{i}", "port": 443, "protocol": "vmess", "name": f"Test Node {i}"}
        for i in range(1, 6)
    ]
    
    # 添加一些真实的服务器
    test_nodes.extend([
        {"id": "batch-real-1", "host": "1.1.1.1", "port": 443, "protocol": "vmess", "name": "Cloudflare"},
        {"id": "batch-real-2", "host": "8.8.8.8", "port": 53, "protocol": "vmess", "name": "Google DNS"},
    ])
    
    print(f"  检测 {len(test_nodes)} 个节点...")
    
    results = await checker.check_nodes_batch(test_nodes)
    
    # 统计
    online = sum(1 for r in results if r.status == NodeStatus.ONLINE)
    offline = sum(1 for r in results if r.status == NodeStatus.OFFLINE)
    suspect = sum(1 for r in results if r.status == NodeStatus.SUSPECT)
    
    print(f"\n  📊 检测结果统计:")
    print(f"     🟢 在线: {online}")
    print(f"     🔴 离线: {offline}")
    print(f"     🟡 可疑: {suspect}")


async def main():
    print("=" * 50)
    print("🏥 viper-node-store 健康检测模块测试")
    print("=" * 50)
    
    try:
        await test_tcp_check()
        await test_node_check()
        await test_batch_check()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试完成!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
