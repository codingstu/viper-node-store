#!/usr/bin/env python3
"""
SHADOW NEXUS - 节点更新与严格测试系统
=====================================
功能:
1. TCP 端口连通性测试
2. 多次测试取平均延迟
3. 丢包率检测 (连接成功率)
4. 异步并发测试提高效率
5. 严格过滤不可用节点
6. 按延迟和速度综合排序
"""

import asyncio
import aiohttp
import socket
import time
import os
import json
import statistics
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor

# =================== 配置区域 ===================
# 测试配置
TEST_ROUNDS = 3          # 每个节点测试轮数
TCP_TIMEOUT = 5          # TCP 连接超时秒数
MAX_LATENCY_MS = 3000    # 最大可接受延迟 (毫秒)
MIN_SUCCESS_RATE = 0.6   # 最低成功率 (60%)
MAX_CONCURRENT = 50      # 最大并发测试数

# 从环境变量获取配置
API_URL = os.environ.get("SHADOW_VIPER_API", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# =================== 核心测试函数 ===================

def tcp_ping(host: str, port: int, timeout: float = TCP_TIMEOUT) -> Tuple[bool, float]:
    """
    TCP 端口连通性测试
    返回: (是否成功, 延迟毫秒)
    """
    try:
        start = time.perf_counter()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        # 尝试连接
        result = sock.connect_ex((host, int(port)))
        
        end = time.perf_counter()
        latency_ms = (end - start) * 1000
        
        sock.close()
        
        if result == 0:
            return (True, round(latency_ms, 2))
        else:
            return (False, -1)
            
    except socket.gaierror:
        # DNS 解析失败
        return (False, -1)
    except socket.timeout:
        # 连接超时
        return (False, -1)
    except Exception as e:
        return (False, -1)


async def test_node_async(node: Dict, executor: ThreadPoolExecutor) -> Optional[Dict]:
    """
    异步测试单个节点
    进行多轮 TCP 连通性测试，计算平均延迟和成功率
    """
    host = node.get("host", "")
    port = node.get("port", 0)
    
    if not host or not port:
        return None
    
    loop = asyncio.get_event_loop()
    results = []
    
    # 多轮测试
    for _ in range(TEST_ROUNDS):
        try:
            # 在线程池中执行 TCP ping (避免阻塞事件循环)
            success, latency = await loop.run_in_executor(
                executor, tcp_ping, host, port, TCP_TIMEOUT
            )
            results.append((success, latency))
        except Exception:
            results.append((False, -1))
        
        # 轮次间小延迟，避免被识别为攻击
        await asyncio.sleep(0.1)
    
    # 统计结果
    success_count = sum(1 for r in results if r[0])
    success_rate = success_count / len(results)
    
    # 过滤: 成功率太低
    if success_rate < MIN_SUCCESS_RATE:
        print(f"  ❌ {host}:{port} - 成功率过低 ({success_rate*100:.0f}%)")
        return None
    
    # 计算有效延迟
    valid_latencies = [r[1] for r in results if r[0] and r[1] > 0]
    
    if not valid_latencies:
        print(f"  ❌ {host}:{port} - 无有效延迟数据")
        return None
    
    avg_latency = statistics.mean(valid_latencies)
    min_latency = min(valid_latencies)
    max_latency = max(valid_latencies)
    
    # 计算延迟抖动 (稳定性指标)
    jitter = max_latency - min_latency if len(valid_latencies) > 1 else 0
    
    # 过滤: 延迟过高
    if avg_latency > MAX_LATENCY_MS:
        print(f"  ⚠️  {host}:{port} - 延迟过高 ({avg_latency:.0f}ms)")
        return None
    
    # 根据延迟计算质量分数 (用于排序)
    # 分数 = 100 - (延迟贡献 + 抖动贡献 + 成功率贡献)
    latency_score = min(avg_latency / 30, 50)  # 延迟越低越好, 最高扣50分
    jitter_score = min(jitter / 100, 20)        # 抖动越小越好, 最高扣20分  
    rate_score = (1 - success_rate) * 30        # 成功率越高越好, 最高扣30分
    quality_score = max(0, 100 - latency_score - jitter_score - rate_score)
    
    # 根据质量分数估算"速度" (MB/s) - 用于前端显示
    # 这是一个基于延迟的估算值，实际速度需要下载测试
    if avg_latency < 100:
        estimated_speed = round(10 + quality_score / 10, 2)
    elif avg_latency < 300:
        estimated_speed = round(5 + quality_score / 20, 2)
    elif avg_latency < 800:
        estimated_speed = round(2 + quality_score / 30, 2)
    else:
        estimated_speed = round(0.5 + quality_score / 50, 2)
    
    # 构建测试结果
    tested_node = node.copy()
    tested_node["speed"] = estimated_speed
    tested_node["latency_ms"] = round(avg_latency, 2)
    tested_node["jitter_ms"] = round(jitter, 2)
    tested_node["success_rate"] = round(success_rate * 100, 1)
    tested_node["quality_score"] = round(quality_score, 1)
    tested_node["tested_at"] = datetime.now().isoformat()
    
    status_icon = "🟢" if avg_latency < 300 else "🟡" if avg_latency < 800 else "🟠"
    print(f"  {status_icon} {host}:{port} - {avg_latency:.0f}ms, 成功率{success_rate*100:.0f}%, 评分{quality_score:.0f}")
    
    return tested_node


async def test_all_nodes(nodes: List[Dict]) -> List[Dict]:
    """
    并发测试所有节点
    """
    print(f"\n🧪 开始严格测试 {len(nodes)} 个节点...")
    print(f"   配置: {TEST_ROUNDS}轮测试, 超时{TCP_TIMEOUT}s, 最大延迟{MAX_LATENCY_MS}ms")
    print("-" * 60)
    
    # 创建线程池用于 TCP 测试
    executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT)
    
    # 使用信号量控制并发数
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    async def limited_test(node):
        async with semaphore:
            return await test_node_async(node, executor)
    
    # 并发测试所有节点
    tasks = [limited_test(node) for node in nodes]
    results = await asyncio.gather(*tasks)
    
    executor.shutdown(wait=False)
    
    # 过滤掉 None (测试失败的节点)
    valid_nodes = [n for n in results if n is not None]
    
    # 按质量分数排序 (高分在前)
    valid_nodes.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
    
    print("-" * 60)
    print(f"✅ 测试完成: {len(valid_nodes)}/{len(nodes)} 个节点通过")
    
    return valid_nodes


async def fetch_nodes_from_api() -> List[Dict]:
    """
    从 API 获取原始节点列表
    """
    if not API_URL:
        raise ValueError("SHADOW_VIPER_API 环境变量未设置")
    
    print(f"🚀 正在从 API 拉取节点...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            if resp.status != 200:
                raise Exception(f"API 请求失败: {resp.status}")
            
            nodes = await resp.json()
            print(f"📦 获取到 {len(nodes)} 个原始节点")
            return nodes


def save_to_supabase(nodes: List[Dict]):
    """
    将测试通过的节点保存到 Supabase
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️  Supabase 配置缺失，跳过数据库保存")
        return
    
    try:
        from supabase import create_client, Client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        data_to_upsert = []
        
        for index, node in enumerate(nodes):
            node_id = f"{node['host']}:{node['port']}"
            
            # 前 15 个高质量节点为免费
            is_free = index < 15
            
            data_to_upsert.append({
                "id": node_id,
                "content": node,
                "is_free": is_free,
                "speed": int(node.get("speed", 0)),
                "latency": int(node.get("latency_ms", 9999)),
                "updated_at": datetime.now().isoformat()
            })
        
        # 批量写入
        if data_to_upsert:
            batch_size = 100
            for i in range(0, len(data_to_upsert), batch_size):
                batch = data_to_upsert[i:i+batch_size]
                supabase.table("nodes").upsert(batch).execute()
            
            print(f"💾 Supabase 更新成功: {len(data_to_upsert)} 条数据")
            
    except ImportError:
        print("⚠️  supabase 模块未安装，跳过数据库保存")
    except Exception as e:
        print(f"❌ Supabase 保存失败: {e}")


def save_public_json(nodes: List[Dict], count: int = 5):
    """
    生成公开的节点 JSON 文件 (仅含少量预览节点)
    """
    os.makedirs("public", exist_ok=True)
    
    # 取前 N 个最优节点作为试用
    safe_nodes = []
    for node in nodes[:count]:
        # 创建简化版本 (隐藏测试细节)
        safe_node = {
            "protocol": node.get("protocol"),
            "host": node.get("host"),
            "port": node.get("port"),
            "country": node.get("country"),
            "speed": node.get("speed"),
            "name": node.get("name"),
            "link": node.get("link")
        }
        safe_nodes.append(safe_node)
    
    with open("public/nodes.json", "w", encoding="utf-8") as f:
        json.dump(safe_nodes, f, indent=2, ensure_ascii=False)
    
    print(f"🛡️  public/nodes.json 已更新 ({len(safe_nodes)} 个试用节点)")


def generate_report(original_count: int, valid_nodes: List[Dict]):
    """
    生成测试报告
    """
    print("\n" + "=" * 60)
    print("📊 节点测试报告")
    print("=" * 60)
    print(f"  原始节点数:   {original_count}")
    print(f"  通过测试数:   {len(valid_nodes)}")
    print(f"  过滤率:       {(1 - len(valid_nodes)/max(original_count,1))*100:.1f}%")
    
    if valid_nodes:
        latencies = [n.get("latency_ms", 0) for n in valid_nodes]
        scores = [n.get("quality_score", 0) for n in valid_nodes]
        
        print(f"\n  📈 延迟统计:")
        print(f"     最低: {min(latencies):.0f}ms")
        print(f"     最高: {max(latencies):.0f}ms")
        print(f"     平均: {statistics.mean(latencies):.0f}ms")
        
        print(f"\n  ⭐ 质量评分:")
        print(f"     最高: {max(scores):.1f}")
        print(f"     平均: {statistics.mean(scores):.1f}")
        
        # 按地区统计
        countries = {}
        for n in valid_nodes:
            c = n.get("country", "UNK")
            countries[c] = countries.get(c, 0) + 1
        
        print(f"\n  🌍 地区分布:")
        for c, count in sorted(countries.items(), key=lambda x: -x[1])[:5]:
            print(f"     {c}: {count} 个")
    
    print("=" * 60 + "\n")


async def main():
    """
    主入口
    """
    print("\n" + "🔥" * 30)
    print("   SHADOW NEXUS - 节点严格测试系统")
    print("🔥" * 30 + "\n")
    
    start_time = time.time()
    
    try:
        # 1. 获取原始节点
        raw_nodes = await fetch_nodes_from_api()
        original_count = len(raw_nodes)
        
        if not raw_nodes:
            print("❌ 无节点数据")
            return
        
        # 2. 严格测试所有节点
        valid_nodes = await test_all_nodes(raw_nodes)
        
        if not valid_nodes:
            print("❌ 所有节点测试失败")
            return
        
        # 3. 保存到 Supabase
        save_to_supabase(valid_nodes)
        
        # 4. 生成公开 JSON
        save_public_json(valid_nodes, count=5)
        
        # 5. 生成报告
        generate_report(original_count, valid_nodes)
        
        elapsed = time.time() - start_time
        print(f"⏱️  总耗时: {elapsed:.1f} 秒")
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
