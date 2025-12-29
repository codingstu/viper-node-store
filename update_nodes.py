#!/usr/bin/env python3
"""
SHADOW NEXUS - 节点更新与严格测试系统 (优化版)
=====================================
优化点:
1. 延迟计算改用中位数 (Median) 抗干扰
2. 修复速度计算公式，防止出现 2000MB/s 等离谱数值
3. 强制覆盖原始数据的 speed 字段
4. 增强 Socket 资源回收
"""

import asyncio
import aiohttp
import socket
import time
import os
import json
import statistics
import math
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor

# =================== 配置区域 ===================
# 测试配置
TEST_ROUNDS = 4  # 增加一轮测试，取中位数更准
TCP_TIMEOUT = 3  # 缩短超时时间，提高效率
MAX_LATENCY_MS = 2000  # 稍微收紧最大延迟要求
MIN_SUCCESS_RATE = 0.75  # 提高成功率门槛 (75%)
MAX_CONCURRENT = 50  # 并发数保持不变

# 速度显示上限 (MB/s)，防止虚标
MAX_DISPLAY_SPEED = 50.0

# 环境变量
API_URL = os.environ.get("SHADOW_VIPER_API", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# 新增配置
CF_WORKER_URL = os.environ.get("CF_WORKER_URL", "https://patient-bonus-f141.sdemon9963.workers.dev")
CF_SECRET = os.environ.get("CF_SECRET", "viper-speed-2025") # 与 Worker 里的密码一致

# =================== 核心测试函数 ===================

def tcp_ping(host: str, port: int, timeout: float = TCP_TIMEOUT) -> Tuple[bool, float]:
    """
    TCP 端口连通性测试 (优化版)
    """
    sock = None
    try:
        start = time.perf_counter()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        # 尝试连接
        result = sock.connect_ex((host, int(port)))

        end = time.perf_counter()
        latency_ms = (end - start) * 1000

        if result == 0:
            return (True, latency_ms)
        else:
            return (False, -1)

    except Exception:
        return (False, -1)
    finally:
        # 确保 socket 关闭
        if sock:
            try:
                sock.close()
            except:
                pass


async def test_node_async(node: Dict, executor: ThreadPoolExecutor) -> Optional[Dict]:
    """
    异步测试单个节点
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
            success, latency = await loop.run_in_executor(
                executor, tcp_ping, host, port, TCP_TIMEOUT
            )
            results.append((success, latency))
        except Exception:
            results.append((False, -1))

        # 微小间隔
        await asyncio.sleep(0.05)

    # 统计数据
    success_count = sum(1 for r in results if r[0])
    success_rate = success_count / len(results)

    # 1. 严格过滤: 成功率
    if success_rate < MIN_SUCCESS_RATE:
        return None

    # 提取有效延迟
    valid_latencies = [r[1] for r in results if r[0] and r[1] > 0]
    if not valid_latencies:
        return None

    # 2. 算法优化: 使用中位数 (Median) 而不是平均值，剔除网络抖动的极端值
    median_latency = statistics.median(valid_latencies)

    # 3. 严格过滤: 延迟过高
    if median_latency > MAX_LATENCY_MS:
        return None

    # 4. 计算稳定性 (Jitter)
    jitter = max(valid_latencies) - min(valid_latencies)

    # 5. 速度估算公式 (重构)
    # 逻辑: 延迟越低 -> 基础带宽越高。 Jitter越低 -> 越接近满速。
    # 基础分: 1000 / (延迟 + 10) -> 比如 50ms 延迟 = 16分
    base_score = 1000 / (median_latency + 10)

    # 乘数修正: 成功率100%且抖动小，系数为 1.5，否则衰减
    stability_factor = 1.0
    if success_rate == 1.0 and jitter < 50:
        stability_factor = 1.5
    elif jitter > 200:
        stability_factor = 0.6

    estimated_speed = base_score * stability_factor * 2.5  # 系数调整以匹配常见 MB/s

    # 6. 强制钳位 (Clamping)
    # 修复 "2000m/s" 问题：无论算的多少，都不能超过设定的物理上限
    final_speed = min(estimated_speed, MAX_DISPLAY_SPEED)
    # 至少给 0.5 MB/s
    final_speed = max(final_speed, 0.5)

    # 计算质量评分 (0-100)
    # 延迟分(60%) + 稳定性(40%)
    score_latency = max(0, 60 - (median_latency / 10))
    score_stability = 40 * success_rate * (1 - min(jitter, 500) / 1000)
    quality_score = score_latency + score_stability

    # 构建结果 (强制覆盖 speed)
    tested_node = node.copy()
    tested_node["speed"] = round(final_speed, 1)  # 强制保留1位小数
    tested_node["latency_ms"] = int(median_latency)  # 取整
    tested_node["success_rate"] = round(success_rate * 100, 0)
    tested_node["quality_score"] = int(quality_score)
    tested_node["updated_at"] = datetime.now().isoformat()

    # 简单的控制台进度条
    # status_icon = "🟢" if median_latency < 200 else "🟡"
    # print(f"  {status_icon} {host} | {int(median_latency)}ms | {final_speed}MB/s")

    return tested_node


async def test_all_nodes(nodes: List[Dict]) -> List[Dict]:
    """
    并发测试所有节点
    """
    print(f"\n🧪 启动严格测试 (GitHub Action Mode)...")
    print(f"   目标: {len(nodes)} 节点 | 并发: {MAX_CONCURRENT} | 策略: Median Latency")

    executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def limited_test(node):
        async with semaphore:
            return await test_node_async(node, executor)

    tasks = [limited_test(node) for node in nodes]
    results = await asyncio.gather(*tasks)

    executor.shutdown(wait=False)

    # 过滤无效节点
    valid_nodes = [n for n in results if n is not None]

    # 排序: 质量优先
    valid_nodes.sort(key=lambda x: x.get("quality_score", 0), reverse=True)

    print(f"✅ 测试完成: 存活 {len(valid_nodes)} / {len(nodes)}")
    return valid_nodes


async def fetch_nodes_from_api() -> List[Dict]:
    """
    API 获取节点 (保持原逻辑，增加超时鲁棒性)
    """
    if not API_URL:
        # 本地开发没配置环境变量时的假数据逻辑，防止报错
        print("⚠️ 未配置 API_URL，跳过获取")
        return []

    headers = {"User-Agent": "ShadowNexus-Tester/2.0"}
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(API_URL, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            print(f"❌ API 获取失败: {e}")
    return []


def save_to_supabase(nodes: List[Dict]):
    """
    保存到 Supabase (保持原逻辑)
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return

    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        data_to_upsert = []
        for i, node in enumerate(nodes):
            # 重新构建 ID，确保唯一性
            node_id = f"{node['host']}:{node['port']}"

            # 强制覆盖字段，确保原来的脏数据(如speed=2000)被清洗
            clean_data = {
                "id": node_id,
                "content": node,  # content 里的 speed 已经被 test_node_async 修改了
                "is_free": i < 15,
                "speed": int(float(node.get("speed", 0))), # 🟢 修复点：强制转换为整数
                "latency": int(node.get("latency_ms", 9999)),
                "updated_at": datetime.now().isoformat()
            }
            data_to_upsert.append(clean_data)

        # 分批写入 (避免包体过大)
        batch_size = 50
        for i in range(0, len(data_to_upsert), batch_size):
            batch = data_to_upsert[i:i + batch_size]
            supabase.table("nodes").upsert(batch).execute()

        print(f"💾 数据库同步完成: {len(data_to_upsert)} 条")

    except Exception as e:
        print(f"❌ 数据库保存失败: {e}")


def save_public_json(nodes: List[Dict]):
    # 简单的文件保存逻辑，保持不变但增强安全性
    os.makedirs("public", exist_ok=True)
    # 只取核心字段，减小体积
    mini_nodes = []
    for n in nodes[:10]:  # 只公开前10个
        mini_nodes.append({
            "name": n.get("name"),
            "type": n.get("protocol"),
            "country": n.get("country"),
            "link": n.get("link")
        })
    with open("public/nodes.json", "w") as f:
        json.dump(mini_nodes, f)


async def test_nodes_via_cloudflare(nodes: List[Dict]) -> List[Dict]:
    """
    代理测速: 将节点列表分批发送给 Cloudflare Worker 进行测试
    """
    print(f"\n🌍 启动云端边缘测速 (Cloudflare Workers)...")

    valid_nodes = []
    batch_size = 10  # CF Worker 每次处理的数量不宜过多，防止超时

    async with aiohttp.ClientSession() as session:
        # 分批处理
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]

            # 构造发送给 Worker 的数据 Payload
            payload = []
            for n in batch:
                payload.append({
                    "id": f"{n['host']}:{n['port']}",  # 用于回溯识别
                    "host": n['host'],
                    "port": int(n['port'])
                })

            try:
                print(f"   📤 发送批次 {i // batch_size + 1} ({len(batch)} 个节点)...")
                start_time = time.time()

                async with session.post(
                        CF_WORKER_URL,
                        json=payload,
                        headers={"x-secret": CF_SECRET},
                        timeout=10  # 给 Worker 足够的运行时间
                ) as resp:
                    if resp.status == 200:
                        results = await resp.json()

                        # 解析结果并回填
                        for res in results:
                            # 找到原始节点对象
                            original_node = next((n for n in batch if f"{n['host']}:{n['port']}" == res['id']), None)
                            if original_node and res['success']:
                                # 修正: CF 测出来的延迟通常比较低，且比较稳定
                                latency = res['latency']

                                # 重新计算质量分 (逻辑与之前类似，但基于 CF 数据)
                                # 假设 CF 到国内节点的平均延迟是 X，这里拿到的数据会比 GitHub 直连更真实
                                original_node['latency_ms'] = latency
                                original_node['success_rate'] = 1.0  # CF 能连上通常算 100%

                                # 简单的速度估算
                                if latency < 100:
                                    original_node['speed'] = 20.0
                                elif latency < 200:
                                    original_node['speed'] = 10.0
                                else:
                                    original_node['speed'] = 5.0

                                # 计算分数
                                original_node['quality_score'] = max(0, 100 - (latency / 5))
                                original_node['updated_at'] = datetime.now().isoformat()

                                valid_nodes.append(original_node)
                                print(f"     ✅ {original_node['host']} | Latency: {latency}ms (CF Edge)")
                    else:
                        print(f"     ❌ Worker 返回错误: {resp.status}")

            except Exception as e:
                print(f"     ⚠️ 批次请求失败: {e}")

            # 稍微休息一下，防止触发 CF 的速率限制
            await asyncio.sleep(1)

    print(f"✅ 云端测试完成: {len(valid_nodes)} / {len(nodes)} 个节点存活")

    # 排序
    valid_nodes.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
    return valid_nodes




async def main():
    start = time.time()

    raw_nodes = await fetch_nodes_from_api()
    if not raw_nodes:
        return

    # 🔥 替换: 不再调用 test_all_nodes (本地/GitHub测速)
    # 而是调用新的云端测速
    valid_nodes = await test_nodes_via_cloudflare(raw_nodes)

    if valid_nodes:
        save_to_supabase(valid_nodes)
        save_public_json(valid_nodes)

    print(f"⏱️ 总耗时: {time.time() - start:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())