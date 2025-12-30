#!/usr/bin/env python3
"""
SHADOW NEXUS - 节点更新系统 (阿里云大陆测速版)
=====================================
架构: GitHub Action (调度) -> Aliyun FC Function (大陆探针) -> Target Nodes
优势: 100% 还原大陆用户真实延迟与连通性
"""

import asyncio
import aiohttp
import os
import json
import time
from datetime import datetime
from typing import List, Dict
from email.utils import formatdate

# =================== 配置区域 ===================

# 环境变量 (必须在 GitHub Secrets 中设置)
API_URL = os.environ.get("SHADOW_VIPER_API", "")  # 你的后端 API 地址
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")  # Supabase URL
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")  # Supabase Key

# 阿里云函数计算配置
# 格式如: https://mainland-probe.xxx.cn-hangzhou.fc.aliyuncs.com
ALIYUN_FC_URL = os.environ.get("ALIYUN_FC_URL", "")
# 必须与阿里云 main.py 里的密码一致
ALIYUN_SECRET = os.environ.get("ALIYUN_SECRET", "viper-aliyun-2025")

# 调试：检查环境变量是否正确设置
print(f"🔧 [DEBUG] ALIYUN_FC_URL: {ALIYUN_FC_URL[:50] if ALIYUN_FC_URL else 'NOT SET'}...")
print(f"🔧 [DEBUG] ALIYUN_SECRET: {'SET' if ALIYUN_SECRET else 'NOT SET'} (value: {ALIYUN_SECRET[:10] if ALIYUN_SECRET else 'empty'}...)")


# =================== 核心逻辑 ===================

async def fetch_nodes_from_api() -> List[Dict]:
    """
    步骤1: 获取原始节点 (带重试机制)
    """
    if not API_URL:
        print("❌ 错误: SHADOW_VIPER_API 环境变量未设置")
        return []

    print(f"🚀 [1/3] 从 API 获取节点: {API_URL}")

    headers = {
        "User-Agent": "ShadowNexus/Aliyun-Probe",
        "Accept": "application/json"
    }

    # 增加超时时间以应对 GitHub Actions 网络环境
    # 总超时 120 秒，连接 30 秒，读取 60 秒
    timeout = aiohttp.ClientTimeout(total=120, connect=30, sock_read=60)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(API_URL, headers=headers) as resp:
                    print(f"   📡 API 响应状态: {resp.status}")
                    if resp.status == 200:
                        nodes = await resp.json()
                        print(f"   📦 获取成功: {len(nodes)} 个原始节点")
                        return nodes
                    else:
                        text = await resp.text()
                        print(f"   ❌ 获取失败: {text[:100]}")
                        return []
        except Exception as e:
            print(f"   ❌ 网络异常 (尝试 {attempt + 1}/{max_retries}): {type(e).__name__}")
            if attempt < max_retries - 1:
                print(f"   ⏳ 等待 5 秒后重试...")
                await asyncio.sleep(5)
            else:
                print(f"   🔍 调试信息: API_URL={API_URL[:60]}...")
                print(f"   💡 建议: 检查 API 服务器是否在线，或增加超时时间")
                return []


async def test_nodes_via_aliyun(nodes: List[Dict]) -> List[Dict]:
    """
    步骤2: 发送给阿里云进行大陆测速
    """
    if not ALIYUN_FC_URL:
        print("❌ 错误: ALIYUN_FC_URL 未设置，无法测速")
        return []

    print(f"\n🚀 [2/3] 启动大陆测速 (阿里云杭州/上海/北京)...")

    valid_nodes = []
    # 阿里云函数限制超时，建议分批处理，每批 15 个
    batch_size = 15

    async with aiohttp.ClientSession() as session:
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]

            # 构造 Payload
            payload = []
            for n in batch:
                # 确保 id 存在
                n_id = n.get("id") or f"{n['host']}:{n['port']}"
                payload.append({
                    "id": n_id,
                    "host": n['host'],
                    "port": int(n['port'])
                })

            try:
                print(f"   📤 发送批次 {i // batch_size + 1} ({len(batch)} 个节点)...")

                # 构造请求头（阿里云要求包含 Date 头）
                request_headers = {
                    "x-secret": ALIYUN_SECRET,
                    "Content-Type": "application/json",
                    "Date": formatdate(timeval=None, localtime=False, usegmt=True)
                }

                async with session.post(
                        ALIYUN_FC_URL,
                        json=payload,
                        headers=request_headers,
                        timeout=20  # 给阿里云足够的运行时间
                ) as resp:
                    if resp.status == 200:
                        results = await resp.json()

                        for res in results:
                            if not res['success']:
                                continue

                            # 找到对应的原始节点
                            # 使用 ID 或 host:port 匹配
                            orig = next((x for x in batch if
                                         (x.get("id") == res['id'] or f"{x['host']}:{x['port']}" == res['id'])), None)

                            if orig:
                                latency = res['latency']

                                # === 大陆优化的评分逻辑 ===
                                # 大陆连境外，延迟通常较高，评分标准需放宽
                                speed_score = 0
                                quality_score = 0

                                if latency < 50:  # 极速 (CN2/专线)
                                    speed_score = 50
                                    quality_score = 95
                                elif latency < 100:  # 优秀 (亚太直连)
                                    speed_score = 30
                                    quality_score = 85
                                elif latency < 200:  # 正常 (美西直连)
                                    speed_score = 10
                                    quality_score = 70
                                elif latency < 350:  # 一般 (普通线路)
                                    speed_score = 3
                                    quality_score = 50
                                else:  # 较差 (绕路)
                                    speed_score = 1
                                    quality_score = 30

                                # 更新节点数据
                                orig['latency_ms'] = latency
                                orig['speed'] = speed_score
                                orig['quality_score'] = quality_score
                                orig['success_rate'] = 100
                                orig['updated_at'] = datetime.now().isoformat()

                                valid_nodes.append(orig)
                                print(f"     ✅ {orig['host']} | 延迟: {latency}ms (大陆真实)")
                    else:
                        print(f"     ⚠️ 阿里云返回错误 {resp.status}: {await resp.text()}")

            except Exception as e:
                print(f"     ❌ 批次请求异常: {e}")

            # 避免触发频率限制
            await asyncio.sleep(0.5)

    # 按质量排序
    valid_nodes.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
    print(f"✅ 测速完成: {len(valid_nodes)} / {len(nodes)} 个节点在大陆可用")
    return valid_nodes


def save_to_supabase(nodes: List[Dict]):
    """
    步骤3: 保存结果 (含整数修复)
    """
    if not SUPABASE_URL:
        return

    print(f"\n🚀 [3/3] 保存至数据库...")
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        data = []
        for i, node in enumerate(nodes):
            # 构造唯一ID
            node_id = f"{node['host']}:{node['port']}"

            data.append({
                "id": node_id,
                "content": node,
                "is_free": i < 15,  # 前15个免费
                # 🟢 修复: 强制转整数，解决 "20.0" 报错
                "speed": int(float(node.get("speed", 0))),
                "latency": int(node.get("latency_ms", 9999)),
                "updated_at": datetime.now().isoformat()
            })

        # 分批写入
        batch_size = 50
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            supabase.table("nodes").upsert(batch).execute()

        print(f"💾 成功保存 {len(data)} 条数据")

    except Exception as e:
        print(f"❌ 数据库保存失败: {e}")


async def main():
    # 1. 获取
    raw_nodes = await fetch_nodes_from_api()
    if not raw_nodes: return

    # 2. 测速
    valid_nodes = await test_nodes_via_aliyun(raw_nodes)

    # 3. 保存
    if valid_nodes:
        save_to_supabase(valid_nodes)


if __name__ == "__main__":
    asyncio.run(main())