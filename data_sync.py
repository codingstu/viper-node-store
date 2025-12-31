#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=== 数据同步模块 ===
实现Webhook + 轮询的混合数据同步策略

架构：
- 主要机制：Webhook推送（实时，由SpiderFlow发起）
- 备用机制：定时轮询（每5分钟检查一次SpiderFlow的最新节点）
- 策略：Webhook优先 + 轮询兜底
- 流量估算：~30MB/月（可接受范围）
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import os
from pathlib import Path
import hashlib
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import socket

logger = logging.getLogger(__name__)

# ==================== 配置 ====================

# SpiderFlow后端URL
SPIDERFLOW_API_URL = os.environ.get("SPIDERFLOW_API_URL", "http://localhost:8001")

# 轮询间隔（秒）
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "300"))  # 默认5分钟

# 本地节点数据库路径
NODES_DB_FILE = "verified_nodes.json"
SYNC_STATE_FILE = "sync_state.json"

# 并发配置
MAX_CONCURRENT_SYNCS = 3
REQUEST_TIMEOUT = 10  # 秒

# ==================== 同步状态跟踪 ====================

class SyncState:
    """跟踪同步状态和上次更新的信息"""
    
    def __init__(self):
        self.state_file = SYNC_STATE_FILE
        self.load()
    
    def load(self):
        """从文件加载同步状态"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.last_webhook_time = state.get("last_webhook_time")
                    self.last_poll_time = state.get("last_poll_time")
                    self.last_sync_hash = state.get("last_sync_hash")
                    self.webhook_received_count = state.get("webhook_received_count", 0)
                    self.poll_received_count = state.get("poll_received_count", 0)
                    logger.info(f"📋 已加载同步状态 | Webhook: {self.webhook_received_count} | 轮询: {self.poll_received_count}")
            except Exception as e:
                logger.error(f"加载同步状态失败: {e}")
                self._init_defaults()
        else:
            self._init_defaults()
    
    def _init_defaults(self):
        """初始化默认值"""
        self.last_webhook_time = None
        self.last_poll_time = None
        self.last_sync_hash = None
        self.webhook_received_count = 0
        self.poll_received_count = 0
    
    def save(self):
        """保存同步状态到文件"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump({
                    "last_webhook_time": self.last_webhook_time,
                    "last_poll_time": self.last_poll_time,
                    "last_sync_hash": self.last_sync_hash,
                    "webhook_received_count": self.webhook_received_count,
                    "poll_received_count": self.poll_received_count,
                    "saved_at": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"保存同步状态失败: {e}")
    
    def record_webhook(self, data_hash: str):
        """记录Webhook接收"""
        self.last_webhook_time = datetime.now().isoformat()
        self.last_sync_hash = data_hash
        self.webhook_received_count += 1
        self.save()
    
    def record_poll(self, data_hash: str):
        """记录轮询接收"""
        self.last_poll_time = datetime.now().isoformat()
        self.last_sync_hash = data_hash
        self.poll_received_count += 1
        self.save()

# ==================== 哈希和变更检测 ====================

def calculate_nodes_hash(nodes: List[Dict]) -> str:
    """
    计算节点数据的哈希值，用于检测变更
    
    哈希基于：
    - 节点URL列表
    - 每个节点的关键信息（国家、延迟、速度等）
    """
    if not nodes:
        return hashlib.sha256(b"").hexdigest()
    
    # 按URL排序，确保一致性
    sorted_nodes = sorted(nodes, key=lambda x: x.get("url", ""))
    
    # 提取关键字段进行哈希
    key_data = []
    for node in sorted_nodes:
        key_str = f"{node.get('url')}|{node.get('country')}|{node.get('latency')}|{node.get('speed')}"
        key_data.append(key_str)
    
    combined = "\n".join(key_data)
    return hashlib.sha256(combined.encode()).hexdigest()

# ==================== 节点去重与合并 ====================

def get_node_unique_key(node: Dict) -> str:
    """
    获取节点的唯一标识key
    规则：protocol + host + port（最精确的组合）
    """
    protocol = node.get("protocol", "unknown").lower()
    host = node.get("host", "").lower()
    port = node.get("port", 0)
    return f"{protocol}://{host}:{port}"

def deduplicate_nodes(nodes: List[Dict]) -> List[Dict]:
    """
    对节点列表进行去重，保留最新数据
    
    规则：
    1. 按 protocol+host+port 识别唯一节点
    2. 重复节点时，新数据覆盖旧数据
    3. 保留 first_seen_at（首次发现时间）
    4. 更新 last_updated_at（最后更新时间）
    
    返回：去重后的节点列表
    """
    if not nodes:
        return []
    
    deduped = {}
    now = datetime.now().isoformat()
    
    for node in nodes:
        key = get_node_unique_key(node)
        
        if key not in deduped:
            # 新节点：添加时间戳字段
            node["first_seen_at"] = node.get("first_seen_at", now)
            node["last_updated_at"] = now
            deduped[key] = node
            logger.debug(f"✨ 新节点: {key}")
        else:
            # 重复节点：保留first_seen_at，更新其他字段
            old_node = deduped[key]
            first_seen = old_node.get("first_seen_at", now)
            
            # 合并新旧数据（新数据优先）
            merged = {**old_node, **node}
            merged["first_seen_at"] = first_seen  # 保留首次发现时间
            merged["last_updated_at"] = now
            
            deduped[key] = merged
            logger.debug(f"🔄 更新节点: {key}")
    
    result = list(deduped.values())
    logger.info(f"📊 去重结果: {len(nodes)} → {len(result)} 个节点")
    return result

def merge_with_local_nodes(remote_nodes: List[Dict]) -> List[Dict]:
    """
    将远程节点与本地节点进行合并
    
    规则：
    1. 远程节点优先（覆盖本地旧数据）
    2. 保留本地节点中不在远程的节点（标记为stale）
    3. 保留原始的 first_seen_at
    """
    local_data = load_local_nodes()
    local_nodes = local_data.get("nodes", [])
    
    # 建立本地节点的key映射
    local_map = {get_node_unique_key(n): n for n in local_nodes}
    
    # 建立远程节点的key映射（带新数据）
    remote_map = {}
    now = datetime.now().isoformat()
    
    for node in remote_nodes:
        key = get_node_unique_key(node)
        
        # 保留本地的first_seen_at
        if key in local_map:
            node["first_seen_at"] = local_map[key].get("first_seen_at", now)
        else:
            node["first_seen_at"] = now
        
        node["last_updated_at"] = now
        remote_map[key] = node
    
    # 合并：远程节点 + 本地但已过期的节点（标记为stale）
    merged_map = {**local_map, **remote_map}
    
    # 标记只在本地存在的节点为 stale
    for key, node in merged_map.items():
        if key not in remote_map:
            node["is_stale"] = True
            logger.debug(f"⚠️ 标记过期节点: {key}")
    
    result = list(merged_map.values())
    logger.info(f"🔀 合并结果: 本地{len(local_nodes)} + 远程{len(remote_nodes)} = {len(result)}个节点")
    return result


# ==================== TTL 和生命周期管理 ====================

def calculate_node_age(node: Dict) -> int:
    """
    计算节点年龄（天数）
    
    基于first_seen_at时间戳
    返回值：
    - 0: 今天新增
    - 1: 1天前
    - 3: 3天前（需要验证）
    """
    try:
        first_seen = node.get("first_seen_at")
        if not first_seen:
            return 0
        
        # 解析ISO格式时间戳
        created_time = datetime.fromisoformat(first_seen.replace('Z', '+00:00'))
        now = datetime.now(created_time.tzinfo) if created_time.tzinfo else datetime.now()
        
        age = (now - created_time).days
        return max(0, age)
    except Exception as e:
        logger.debug(f"⚠️  计算节点年龄失败: {e}")
        return 0


def mark_nodes_for_verification(nodes: List[Dict], ttl_days: int = 3) -> List[Dict]:
    """
    标记需要验证的节点
    
    规则：
    - age_days >= ttl_days 的节点标记为 needs_verification=True
    - 从未验证过或验证失败的节点也标记为需要验证
    - 返回修改后的节点列表
    """
    for node in nodes:
        # 计算节点年龄
        age_days = calculate_node_age(node)
        node["age_days"] = age_days
        
        # 判断是否需要验证
        needs_verification = (
            age_days >= ttl_days or  # 超过TTL
            not node.get("last_verified_at")  # 从未验证
        )
        
        node["needs_verification"] = needs_verification
        
        if needs_verification:
            logger.debug(f"🔍 标记待验证节点 {get_node_unique_key(node)} | 年龄{age_days}天")
    
    return nodes


def apply_node_lifecycle(nodes: List[Dict], ttl_days: int = 3, max_offline_days: int = 7) -> List[Dict]:
    """
    应用完整节点生命周期管理
    
    流程：
    1. 计算节点年龄
    2. 标记需要验证的节点
    3. 标记长期离线的节点为删除候选
    
    参数：
    - ttl_days: 节点TTL（天），超过则需要验证
    - max_offline_days: 最大离线天数，超过则删除
    
    返回：
    - 处理后的节点列表
    """
    processed_nodes = []
    
    for node in nodes:
        # 1. 计算年龄
        age_days = calculate_node_age(node)
        node["age_days"] = age_days
        
        # 2. 检查离线状态和离线时长
        offline_status = node.get("offline_status", False)
        verification_failed_at = node.get("verification_failed_at")
        
        if offline_status and verification_failed_at:
            try:
                failed_time = datetime.fromisoformat(verification_failed_at.replace('Z', '+00:00'))
                now = datetime.now(failed_time.tzinfo) if failed_time.tzinfo else datetime.now()
                offline_days = (now - failed_time).days
                
                # 离线超过max_offline_days则标记删除
                if offline_days > max_offline_days:
                    node["should_delete"] = True
                    logger.info(f"🗑️  标记删除长期离线节点 {get_node_unique_key(node)} | 离线{offline_days}天")
                    continue  # 不加入返回列表
            except Exception as e:
                logger.debug(f"⚠️  检查离线时长失败: {e}")
        
        # 3. 标记需要验证的节点
        needs_verification = (
            age_days >= ttl_days or
            not node.get("last_verified_at") or
            offline_status
        )
        node["needs_verification"] = needs_verification
        
        processed_nodes.append(node)
    
    return processed_nodes


# ==================== 节点活力验证 ====================

async def verify_node_connectivity(node: Dict, timeout: int = 5) -> bool:
    """
    验证节点连通性
    
    实现方式：
    - 通过HTTP HEAD请求验证代理是否可达
    - 测试地址：https://www.cloudflare.com/（轻量级）
    - 支持HTTP代理协议
    
    参数：
    - node: 节点信息字典
    - timeout: 超时时间（秒）
    
    返回：
    - True: 节点可达
    - False: 节点不可达
    """
    try:
        proxy_url = node.get("proxy_url") or f"{node.get('protocol', 'http')}://{node.get('host')}:{node.get('port')}"
        
        # 设置代理协议
        proxy_protocol = node.get('protocol', 'http').lower()
        if proxy_protocol not in ['http', 'https', 'socks5']:
            return False
        
        # 构建代理URL (HTTP通用格式)
        auth_str = ""
        if node.get('username') and node.get('password'):
            auth_str = f"{node.get('username')}:{node.get('password')}@"
        
        proxy_connect_url = f"{proxy_protocol}://{auth_str}{node.get('host')}:{node.get('port')}"
        
        # 使用aiohttp验证连通性
        async with aiohttp.ClientSession() as session:
            async with session.head(
                'https://www.cloudflare.com/',
                proxy=proxy_connect_url if proxy_protocol != 'socks5' else None,
                timeout=aiohttp.ClientTimeout(total=timeout),
                ssl=False
            ) as resp:
                return resp.status < 500  # 只要不是5xx错误就认为可达
                
    except asyncio.TimeoutError:
        logger.debug(f"⏱️  节点验证超时: {get_node_unique_key(node)}")
        return False
    except Exception as e:
        logger.debug(f"❌ 节点验证失败 {get_node_unique_key(node)}: {e}")
        return False


def mark_node_offline(node: Dict) -> Dict:
    """
    标记节点为离线状态
    
    更新字段：
    - offline_status: 标记为True
    - verification_failed_at: 记录失败时间
    - last_verified_at: 更新为当前时间
    """
    node["offline_status"] = True
    node["verification_failed_at"] = datetime.now().isoformat()
    node["last_verified_at"] = datetime.now().isoformat()
    return node


async def verify_nodes_batch(nodes_to_verify: List[Dict]) -> List[Dict]:
    """
    批量验证节点
    
    流程：
    1. 遍历待验证节点列表
    2. 逐个执行连通性测试
    3. 失败的节点标记为离线
    4. 更新last_verified_at时间戳
    
    返回：
    - 包含验证结果的节点列表
    """
    verified = []
    failed_count = 0
    
    for node in nodes_to_verify:
        node_key = get_node_unique_key(node)
        is_reachable = await verify_node_connectivity(node)
        
        if is_reachable:
            node["offline_status"] = False
            node["last_verified_at"] = datetime.now().isoformat()
            logger.info(f"✅ 节点验证通过: {node_key}")
        else:
            mark_node_offline(node)
            failed_count += 1
            logger.warning(f"❌ 节点验证失败: {node_key}")
        
        verified.append(node)
        # 每个验证间隔100ms，避免过于激进
        await asyncio.sleep(0.1)
    
    logger.info(f"🔍 批量验证完成 | 总计{len(verified)}个 | 失败{failed_count}个")
    return verified


async def scheduled_node_verification():
    """
    定时任务：验证3天以上的节点
    
    执行频率：每天凌晨2:00
    规则：
    1. 加载本地节点数据
    2. 筛选age_days >= 3且needs_verification=True的节点
    3. 批量验证这些节点
    4. 删除长期离线的节点
    5. 保存更新结果
    """
    logger.info("🔄 开始定时节点验证任务 (每天2:00执行)")
    
    try:
        data = load_local_nodes()
        nodes = data.get("nodes", [])
        
        if not nodes:
            logger.info("📊 无节点数据，跳过验证")
            return
        
        # 1. 筛选需要验证的节点 (age_days >= 3)
        nodes_to_verify = [
            n for n in nodes 
            if n.get("needs_verification") and n.get("age_days", 0) >= 3
        ]
        
        if not nodes_to_verify:
            logger.info("✅ 无需验证的节点")
            return
        
        logger.info(f"🔍 准备验证{len(nodes_to_verify)}个节点...")
        
        # 2. 批量验证
        verified_nodes = await verify_nodes_batch(nodes_to_verify)
        
        # 3. 更新节点映射
        verified_map = {get_node_unique_key(n): n for n in verified_nodes}
        for i, node in enumerate(nodes):
            key = get_node_unique_key(node)
            if key in verified_map:
                nodes[i] = verified_map[key]
        
        # 4. 应用生命周期管理（删除长期离线的）
        final_nodes = apply_node_lifecycle(nodes, ttl_days=3, max_offline_days=7)
        
        # 5. 保存更新结果
        data["nodes"] = final_nodes
        data["last_verified_at"] = datetime.now().isoformat()
        save_local_nodes(data)
        
        # 6. 记录统计
        offline_count = len([n for n in final_nodes if n.get("offline_status")])
        logger.info(f"✅ 节点验证任务完成 | 总计{len(final_nodes)}个 | 离线{offline_count}个")
        
    except Exception as e:
        logger.error(f"❌ 节点验证任务异常: {e}")


# ==================== 网络请求 ====================

async def fetch_nodes_from_spiderflow() -> Optional[Dict[str, Any]]:
    """
    从SpiderFlow API获取最新的节点列表
    
    端点：GET /nodes/export?format=json
    返回：{ "nodes": [...], "last_updated": "...", "total_count": ... }
    """
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{SPIDERFLOW_API_URL}/nodes/export?format=json"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"✅ 从SpiderFlow获取{len(data.get('nodes', []))}个节点")
                    return data
                else:
                    logger.error(f"SpiderFlow返回错误状态: {resp.status}")
                    return None
    except asyncio.TimeoutError:
        logger.error(f"❌ 连接SpiderFlow超时")
        return None
    except Exception as e:
        logger.error(f"❌ 从SpiderFlow获取数据失败: {e}")
        return None

# ==================== 本地存储操作 ====================

def load_local_nodes() -> Dict[str, Any]:
    """从本地加载节点数据"""
    if os.path.exists(NODES_DB_FILE):
        try:
            with open(NODES_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载本地节点失败: {e}")
            return {"nodes": []}
    return {"nodes": []}

def save_local_nodes(data: Dict[str, Any]):
    """保存节点数据到本地"""
    try:
        with open(NODES_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 已保存{len(data.get('nodes', []))}个节点到本地")
    except Exception as e:
        logger.error(f"保存本地节点失败: {e}")

# ==================== 核心同步逻辑 ====================

async def poll_spiderflow_nodes() -> Optional[Dict[str, Any]]:
    """
    轮询从SpiderFlow获取节点数据
    
    工作流程：
    1. 连接SpiderFlow API
    2. 获取最新节点列表
    3. 执行去重和合并
    4. 与本地数据对比（哈希检查）
    5. 如果有变更，更新本地数据库
    6. 记录同步状态
    """
    logger.info("🔄 开始轮询SpiderFlow节点...")
    
    # 获取远程节点数据
    remote_data = await fetch_nodes_from_spiderflow()
    if not remote_data:
        logger.warning("⚠️ 轮询失败，使用本地数据")
        return None
    
    remote_nodes = remote_data.get("nodes", [])
    logger.info(f"📥 从SpiderFlow获取{len(remote_nodes)}个节点")
    
    # 1. 远程节点去重
    deduplicated = deduplicate_nodes(remote_nodes)
    
    # 2. 与本地节点合并
    merged_nodes = merge_with_local_nodes(deduplicated)
    
    # 计算哈希值
    merged_hash = calculate_nodes_hash(merged_nodes)
    
    # 加载本地数据获取旧哈希
    local_data = load_local_nodes()
    local_nodes = local_data.get("nodes", [])
    local_hash = calculate_nodes_hash(local_nodes)
    
    # 检查是否有变更
    if merged_hash == local_hash and local_nodes:
        logger.info("📊 节点数据无变更，跳过更新")
        return None
    
    # 更新本地数据
    updated_data = {
        "nodes": merged_nodes,
        "last_synced_from": "spiderflow_poll",
        "last_synced_at": datetime.now().isoformat(),
        "nodes_count": len([n for n in merged_nodes if not n.get("is_stale")]),
        "sync_metadata": {
            "total_count": len(merged_nodes),
            "active_count": len([n for n in merged_nodes if not n.get("is_stale")]),
            "remote_timestamp": remote_data.get("last_updated"),
            "deduplicated": len(remote_nodes) - len(deduplicated)
        }
    }
    
    # 3. 应用TTL和生命周期管理
    lifecycle_nodes = apply_node_lifecycle(updated_data["nodes"])
    needs_verification_count = len([n for n in lifecycle_nodes if n.get("needs_verification")])
    
    updated_data["nodes"] = lifecycle_nodes
    updated_data["sync_metadata"]["needs_verification"] = needs_verification_count
    
    save_local_nodes(updated_data)
    
    # 记录轮询状态
    sync_state = SyncState()
    sync_state.record_poll(merged_hash)
    
    logger.info(f"✅ 轮询完成 | 总计{len(lifecycle_nodes)}个节点 | 活跃{updated_data['nodes_count']}个 | 待验证{needs_verification_count}个")
    return updated_data

async def handle_webhook_sync(webhook_payload: Dict[str, Any]):
    """
    处理Webhook同步（实时，由SpiderFlow发起）
    
    工作流程：
    1. 接收webhook推送的节点
    2. 执行去重和合并
    3. 更新本地数据库
    4. 记录同步状态
    
    优势：
    - 实时推送，无延迟
    - 最小流量开销
    - 响应时间短
    """
    try:
        remote_nodes = webhook_payload.get("nodes", [])
        logger.info(f"⚡ 接收Webhook推送，{len(remote_nodes)}个节点")
        
        # 1. 远程节点去重
        deduplicated = deduplicate_nodes(remote_nodes)
        
        # 2. 与本地节点合并
        merged_nodes = merge_with_local_nodes(deduplicated)
        
        # 计算哈希
        merged_hash = calculate_nodes_hash(merged_nodes)
        
        # 更新本地数据
        data = {
            "nodes": merged_nodes,
            "last_synced_from": "webhook",
            "last_synced_at": datetime.now().isoformat(),
            "nodes_count": len([n for n in merged_nodes if not n.get("is_stale")]),
            "sync_metadata": {
                "total_count": len(merged_nodes),
                "active_count": len([n for n in merged_nodes if not n.get("is_stale")]),
                "deduplicated": len(remote_nodes) - len(deduplicated)
            }
        }
        save_local_nodes(data)
        
        # 记录状态
        sync_state = SyncState()
        sync_state.record_webhook(merged_hash)
        
        logger.info(f"⚡ Webhook同步完成 | 总计{len(merged_nodes)}个节点 | 活跃{data['nodes_count']}个")
        
    except Exception as e:
        logger.error(f"Webhook同步处理失败: {e}")

# ==================== 定时调度器 ====================

class DataSyncScheduler:
    """管理定时轮询任务和节点验证任务"""
    
    def __init__(self):
        self.running = False
        self.poll_task = None
        self.scheduler = None
    
    async def start(self):
        """启动定时轮询"""
        self.running = True
        logger.info(f"🚀 启动数据同步调度器 | 轮询间隔: {POLL_INTERVAL}秒")
        
        # 启动APScheduler进行定时验证
        if not self.scheduler:
            self.scheduler = BackgroundScheduler()
            # 每天凌晨2:00执行节点验证
            self.scheduler.add_job(
                scheduled_node_verification,
                CronTrigger(hour=2, minute=0, timezone='Asia/Shanghai'),
                id='node_verification',
                name='Daily Node Verification',
                replace_existing=True
            )
            self.scheduler.start()
            logger.info("✅ 节点验证定时器已启动 (每天2:00执行)")
        
        while self.running:
            try:
                # 执行轮询
                await poll_spiderflow_nodes()
                
                # 等待下一个轮询周期
                await asyncio.sleep(POLL_INTERVAL)
                
            except Exception as e:
                logger.error(f"轮询循环异常: {e}")
                await asyncio.sleep(10)  # 出错后等待10秒再重试
    
    async def stop(self):
        """停止定时轮询"""
        self.running = False
        if self.poll_task:
            self.poll_task.cancel()
        
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("🛑 节点验证定时器已停止")
        
        logger.info("🛑 已停止数据同步调度器")

# ==================== 快速导出接口 ====================

def get_exported_nodes(format: str = "json") -> str:
    """
    导出本地节点数据
    
    支持的格式：
    - json: JSON格式
    - clash: Clash配置格式
    - subscription: 订阅链接格式
    """
    data = load_local_nodes()
    nodes = data.get("nodes", [])
    
    if format == "json":
        return json.dumps({
            "nodes": nodes,
            "total_count": len(nodes),
            "exported_at": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
    
    elif format == "clash":
        # TODO: 实现Clash格式导出
        return "# Clash配置（待实现）"
    
    elif format == "subscription":
        # TODO: 实现订阅格式导出
        return "# 订阅链接（待实现）"
    
    return ""

# ==================== 统计和监控 ====================

def get_sync_statistics() -> Dict[str, Any]:
    """获取同步统计信息"""
    sync_state = SyncState()
    local_data = load_local_nodes()
    
    return {
        "total_nodes": len(local_data.get("nodes", [])),
        "last_synced_at": local_data.get("last_synced_at"),
        "sync_method": local_data.get("last_synced_from", "unknown"),
        "webhook_syncs": sync_state.webhook_received_count,
        "poll_syncs": sync_state.poll_received_count,
        "total_syncs": sync_state.webhook_received_count + sync_state.poll_received_count,
        "last_webhook_time": sync_state.last_webhook_time,
        "last_poll_time": sync_state.last_poll_time,
        "data_hash": calculate_nodes_hash(local_data.get("nodes", []))
    }
