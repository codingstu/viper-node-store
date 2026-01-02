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
import re
from urllib.parse import urlparse
from datetime import datetime
from typing import List, Dict
from email.utils import formatdate

# =================== 配置区域 ===================

# 环境变量 (必须在 GitHub Secrets 中设置)
API_URL = os.environ.get("SHADOW_VIPER_API", "")  # 你的后端 API 地址
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")  # Supabase URL
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")  # Supabase Key

# 大陆测速：阿里云函数计算
ALIYUN_FC_URL = os.environ.get("ALIYUN_FC_URL", "")

# 回国节点测速：Cloudflare Workers
CLOUDFLARE_WORKER_URL = os.environ.get("CLOUDFLARE_WORKER_URL", "")

# 调试：检查环境变量是否正确设置
print(f"🔧 [DEBUG] ALIYUN_FC_URL: {ALIYUN_FC_URL[:50] if ALIYUN_FC_URL else 'NOT SET'}...")
print(f"🔧 [DEBUG] CLOUDFLARE_WORKER_URL: {CLOUDFLARE_WORKER_URL[:50] if CLOUDFLARE_WORKER_URL else 'NOT SET'}...")


# =================== 核心逻辑 ===================

def extract_host_port(link: str) -> tuple:
    """
    从代理链接中提取 host 和 port
    支持: vless://, vmess://, trojan://, ss:// 等
    """
    try:
        # 首先尝试标准 URL 解析
        parsed = urlparse(link)
        host = parsed.hostname
        port = parsed.port
        
        if host and port:
            return host, port
        
        # 备选：从 netloc 手动解析（处理非标准格式）
        netloc = parsed.netloc
        if '@' in netloc:
            netloc = netloc.split('@')[1]
        
        if ':' in netloc:
            parts = netloc.rsplit(':', 1)
            try:
                return parts[0], int(parts[1])
            except:
                pass
        
        # 如果是 VMess，尝试从 base64 解析
        if link.startswith('vmess://'):
            try:
                import base64
                encoded = link.replace('vmess://', '')
                decoded = base64.b64decode(encoded).decode('utf-8')
                vmess_json = json.loads(decoded)
                host = vmess_json.get('add')
                port = vmess_json.get('port')
                if host and port:
                    return host, int(port)
            except:
                pass
        
        return None, None
    except Exception as e:
        return None, None

async def fetch_nodes_from_api(region: str = 'mainland') -> List[Dict]:
    """
    步骤1: 获取节点 (从 SpiderFlow 后端的 API)
    region: 'mainland' (大陆) 或 'overseas' (海外)
    """
    # 优先尝试从本地 JSON 文件读取
    try:
        with open('public/nodes.json', 'r', encoding='utf-8') as f:
            local_nodes = json.load(f)
            if isinstance(local_nodes, list) and len(local_nodes) > 0:
                print(f"✅ [1/3] 从本地文件加载节点 (地区: {region})")
                print(f"   📦 加载成功: {len(local_nodes)} 个节点")
                return local_nodes
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"⚠️ 本地文件读取失败: {e}")
    
    # 本地文件不存在或为空，尝试从 API 获取
    if not API_URL:
        print("❌ 错误: SHADOW_VIPER_API 环境变量未设置")
        return []

    print(f"🚀 [1/3] 从远程 API 获取节点: {API_URL} (地区: {region})")

    headers = {
        "User-Agent": "ShadowNexus/Probe",
        "Accept": "application/json"
    }

    # 增加超时时间
    timeout = aiohttp.ClientTimeout(total=180, connect=60, sock_read=120)
    
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
                return []


async def test_nodes_via_aliyun(nodes: List[Dict]) -> List[Dict]:
    """
    步骤2: 发送给阿里云进行大陆测速
    如果失败，将使用本地测速作为降级方案
    """
    if not ALIYUN_FC_URL:
        print("❌ 错误: ALIYUN_FC_URL 未设置，无法测速")
        return []

    print(f"\n🚀 [2/3] 启动大陆测速 (阿里云杭州/上海/北京)...")

    valid_nodes = []
    # 阿里云函数限制超时，建议分批处理，每批 15 个
    batch_size = 15
    total_success = 0
    total_failed = 0

    async with aiohttp.ClientSession() as session:
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]

            # 构造 Payload（包含密钥和节点列表）
            payload_nodes = []
            for n in batch:
                # 提取 host 和 port
                host = n.get('host')
                port = n.get('port')
                
                # 如果没有 host/port，尝试从 link 字段解析
                if not host or not port:
                    link = n.get('link', '')
                    host, port = extract_host_port(link)
                
                # 跳过无法解析的节点
                if not host or not port:
                    print(f"⚠️ 无法解析节点: {n.get('name', 'unknown')}")
                    continue
                
                # 确保 id 存在
                n_id = n.get("id") or n.get("name") or f"{host}:{port}"
                payload_nodes.append({
                    "id": n_id,
                    "host": host,
                    "port": int(port)
                })
            
            if not payload_nodes:
                print(f"⚠️ 批次 {i // batch_size + 1} 没有有效节点")
                continue

            # 完整的请求体：只包含 nodes（移除认证）
            request_payload = {
                "nodes": payload_nodes
            }

            try:
                print(f"   📤 发送批次 {i // batch_size + 1} ({len(payload_nodes)} 个节点)...")

                # 构造请求头
                request_headers = {
                    "Content-Type": "application/json",
                    "Date": formatdate(timeval=None, localtime=False, usegmt=True)
                }

                async with session.post(
                        ALIYUN_FC_URL,
                        json=request_payload,
                        headers=request_headers,
                        timeout=20  # 给阿里云足够的运行时间
                ) as resp:
                    if resp.status == 200:
                        results = await resp.json()
                        total_success += len([r for r in results if r.get('success')])
                        total_failed += len([r for r in results if not r.get('success')])

                        for res in results:
                            if not res['success']:
                                continue

                            # 找到对应的原始节点
                            # 使用 ID 或 host:port 匹配
                            orig = next((x for x in batch if
                                         (x.get("id") == res['id'] or x.get("name") == res['id'] or f"{x.get('host', '')}:{x.get('port', '')}" == res['id'])), None)

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
                                print(f"     ✅ {orig.get('host', 'N/A')} | 延迟: {latency}ms (大陆真实)")
                    else:
                        error_text = await resp.text()
                        print(f"     ⚠️ 阿里云返回错误 {resp.status}: {error_text[:200]}")
                        
                        # 如果是认证错误，打印详细信息用于诊断
                        if resp.status == 401 or resp.status == 400:
                            try:
                                error_json = json.loads(error_text)
                                print(f"     📋 详细错误: {json.dumps(error_json, ensure_ascii=False)}")
                            except:
                                pass

            except Exception as e:
                print(f"     ❌ 批次请求异常: {type(e).__name__}: {str(e)}")

            # 避免触发频率限制
            await asyncio.sleep(0.5)

    # 按质量排序
    valid_nodes.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
    print(f"✅ 测速完成: {len(valid_nodes)} / {len(nodes)} 个节点在大陆可用 (成功: {total_success}, 失败: {total_failed})")
    return valid_nodes


async def test_nodes_via_cloudflare(nodes: List[Dict]) -> List[Dict]:
    """
    步骤2B: 发送给 Cloudflare Workers 进行国外测速 (回国节点)
    """
    if not CLOUDFLARE_WORKER_URL:
        print("⚠️ 警告: CLOUDFLARE_WORKER_URL 未设置，跳过国外测速")
        return []

    print(f"\n🚀 [2B/3] 启动国外测速 (Cloudflare Workers)...")

    valid_nodes = []
    batch_size = 15
    total_success = 0
    total_failed = 0

    async with aiohttp.ClientSession() as session:
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]

            # 构造 Payload
            payload_nodes = []
            for n in batch:
                host = n.get('host')
                port = n.get('port')
                
                if not host or not port:
                    link = n.get('link', '')
                    host, port = extract_host_port(link)
                
                if not host or not port:
                    continue
                
                n_id = n.get("id") or n.get("name") or f"{host}:{port}"
                payload_nodes.append({
                    "id": n_id,
                    "host": host,
                    "port": int(port)
                })
            
            if not payload_nodes:
                continue

            request_payload = {
                "nodes": payload_nodes
            }

            try:
                print(f"   📤 发送批次 {i // batch_size + 1} ({len(payload_nodes)} 个节点)...")

                request_headers = {
                    "Content-Type": "application/json",
                    "Date": formatdate(timeval=None, localtime=False, usegmt=True)
                }

                async with session.post(
                        CLOUDFLARE_WORKER_URL,
                        json=request_payload,
                        headers=request_headers,
                        timeout=20
                ) as resp:
                    if resp.status == 200:
                        results = await resp.json()
                        total_success += len([r for r in results if r.get('success')])
                        total_failed += len([r for r in results if not r.get('success')])

                        for res in results:
                            if not res['success']:
                                continue

                            orig = next((x for x in batch if
                                         (x.get("id") == res['id'] or x.get("name") == res['id'] or f"{x.get('host', '')}:{x.get('port', '')}" == res['id'])), None)

                            if orig:
                                latency = res['latency']

                                # === 国外优化的评分逻辑 ===
                                # 国外测速延迟会更高，标准放更宽
                                speed_score = 0
                                quality_score = 0

                                if latency < 100:  # 极速 (距离近/专线)
                                    speed_score = 50
                                    quality_score = 95
                                elif latency < 150:  # 优秀
                                    speed_score = 30
                                    quality_score = 85
                                elif latency < 250:  # 正常
                                    speed_score = 10
                                    quality_score = 70
                                elif latency < 400:  # 一般
                                    speed_score = 3
                                    quality_score = 50
                                else:  # 较差
                                    speed_score = 1
                                    quality_score = 30

                                orig['latency_ms'] = latency
                                orig['speed'] = speed_score
                                orig['quality_score'] = quality_score
                                orig['success_rate'] = 100
                                orig['updated_at'] = datetime.now().isoformat()
                                orig['test_via'] = 'cloudflare'  # 标记测试来源

                                valid_nodes.append(orig)
                                print(f"     ✅ {orig.get('host', 'N/A')} | 延迟: {latency}ms (国外真实)")
                    else:
                        error_text = await resp.text()
                        print(f"     ⚠️ Cloudflare 返回错误 {resp.status}: {error_text[:200]}")

            except Exception as e:
                print(f"     ❌ 批次请求异常: {type(e).__name__}: {str(e)}")

            await asyncio.sleep(0.5)

    valid_nodes.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
    print(f"✅ 国外测速完成: {len(valid_nodes)} / {len(nodes)} 个节点在国外可用 (成功: {total_success}, 失败: {total_failed})")
    return valid_nodes


def save_to_supabase(nodes: List[Dict]):
    """
    步骤3: 保存结果 (含整数修复和去重)
    """
    if not SUPABASE_URL:
        return

    print(f"\n🚀 [3/3] 保存至数据库...")
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        data = []
        seen_ids = set()  # 用于去重
        
        for i, node in enumerate(nodes):
            # 构造唯一ID
            node_id = f"{node.get('host', 'unknown')}:{node.get('port', 'unknown')}"
            
            # 跳过重复的ID
            if node_id in seen_ids:
                print(f"⚠️ 跳过重复节点: {node_id}")
                continue
            
            seen_ids.add(node_id)

            data.append({
                "id": node_id,
                "content": node,
                "link": node.get("link", ""),  # 添加 link 字段直接到表中
                "is_free": i < 15,  # 前15个免费
                # 🟢 修复: 强制转整数，解决 "20.0" 报错
                "speed": int(float(node.get("speed", 0))),
                "latency": int(node.get("latency_ms", 9999)),
                "updated_at": datetime.now().isoformat()
            })

        if not data:
            print("⚠️ 没有数据需要保存")
            return

        # 分批写入
        batch_size = 50
        total_saved = 0
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            try:
                supabase.table("nodes").upsert(batch).execute()
                total_saved += len(batch)
                print(f"  📝 批次 {i // batch_size + 1}: 保存 {len(batch)} 条")
            except Exception as batch_error:
                print(f"  ⚠️ 批次 {i // batch_size + 1} 保存失败: {batch_error}")

        print(f"💾 成功保存 {total_saved} 条数据")

    except Exception as e:
        print(f"❌ 数据库保存失败: {type(e).__name__}: {e}")


async def main():
    # 1. 获取原始节点
    raw_nodes = await fetch_nodes_from_api()
    if not raw_nodes:
        print("❌ 无法获取节点")
        return

    print(f"\n📊 节点分类统计:")
    print(f"   总节点数: {len(raw_nodes)}")
    
    # 2A. 分类处理节点
    # 优先级: 
    # - 如果 country 字段存在，使用它
    # - 如果没有，尝试从其他字段推断
    
    cn_nodes = []
    overseas_nodes = []
    
    for node in raw_nodes:
        country = node.get('country', '').upper()
        
        # 大陆节点
        if country == 'CN':
            cn_nodes.append(node)
        # 香港/台湾/澳门 -> 归类为国外（需要国外测速）
        elif country in ['HK', 'TW', 'MO']:
            overseas_nodes.append(node)
        # 其他国外节点
        elif country and country != 'CN':
            overseas_nodes.append(node)
        # 没有国家标签，默认归为国外
        else:
            overseas_nodes.append(node)
    
    print(f"   🇨🇳 大陆节点: {len(cn_nodes)}")
    print(f"   🌍 国外节点: {len(overseas_nodes)}")
    
    all_valid_nodes = []
    
    # 2B. 大陆节点：使用阿里云测速
    if cn_nodes:
        aliyun_results = await test_nodes_via_aliyun(cn_nodes)
        all_valid_nodes.extend(aliyun_results)
    
    # 2C. 国外节点：使用 Cloudflare Workers 测速
    if overseas_nodes:
        cf_results = await test_nodes_via_cloudflare(overseas_nodes)
        all_valid_nodes.extend(cf_results)
    
    # 3. 保存所有结果
    if all_valid_nodes:
        print(f"\n📦 共有 {len(all_valid_nodes)} 个节点通过测速，即将保存...")
        save_to_supabase(all_valid_nodes)
    else:
        print("⚠️ 没有节点通过测速")


if __name__ == "__main__":
    asyncio.run(main())