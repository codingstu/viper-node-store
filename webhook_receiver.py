#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=== Webhook接收器 ===
用于从SpiderFlow接收实时的节点数据更新

架构：
- 监听POST /webhook/nodes-update（来自SpiderFlow推送）
- 验证签名和数据完整性
- 立即更新本地节点数据库
- 异步同步到各个存储端点
"""

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import hashlib
import hmac
import logging
import asyncio
import aiohttp
from datetime import datetime
import os

logger = logging.getLogger(__name__)

webhook_router = APIRouter(prefix="/webhook", tags=["webhook"])

# ==================== 配置 ====================
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "spiderflow-viper-sync-2026")
NODES_DB_FILE = "verified_nodes.json"

# ==================== 数据模型 ====================

class NodeData(BaseModel):
    """单个节点数据"""
    url: str
    name: str
    country: str
    latency: float
    speed: float  # MB/s
    availability: float  # 0-100%
    last_checked: str  # ISO格式时间戳
    protocol: str  # vmess, vless, ss, etc.
    
class WebhookPayload(BaseModel):
    """Webhook推送的数据格式"""
    event_type: str  # "nodes_updated", "batch_test_complete", etc.
    timestamp: str
    nodes: List[NodeData]
    total_count: int
    verified_count: int
    
class WebhookSignature(BaseModel):
    """Webhook签名验证"""
    timestamp: str
    signature: str  # HMAC-SHA256(payload + timestamp, secret)

# ==================== 签名验证 ====================

def verify_webhook_signature(payload_str: str, timestamp: str, signature: str) -> bool:
    """
    验证Webhook签名
    
    签名算法：
    1. 构造: {payload_json_string}.{timestamp}
    2. 使用HMAC-SHA256进行签名
    3. 与传入的签名比对
    """
    message = f"{payload_str}.{timestamp}"
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # 使用constant-time比较防止时序攻击
    return hmac.compare_digest(expected_signature, signature)

# ==================== 本地存储操作 ====================

def load_nodes_from_file() -> Dict[str, Any]:
    """从JSON文件加载节点数据"""
    if os.path.exists(NODES_DB_FILE):
        try:
            with open(NODES_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载节点文件失败: {e}")
            return {"nodes": [], "last_updated": None}
    return {"nodes": [], "last_updated": None}

def save_nodes_to_file(data: Dict[str, Any]) -> bool:
    """保存节点数据到JSON文件"""
    try:
        data["last_updated"] = datetime.now().isoformat()
        with open(NODES_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ 已保存{len(data.get('nodes', []))}个节点到本地数据库")
        return True
    except Exception as e:
        logger.error(f"保存节点文件失败: {e}")
        return False

def merge_node_data(existing: Dict[str, Any], new_nodes: List[NodeData]) -> Dict[str, Any]:
    """
    合并新节点数据到现有数据库
    
    策略：
    - 按URL作为唯一标识符
    - 新节点覆盖旧数据
    - 保留历史统计信息
    """
    existing_nodes = {node['url']: node for node in existing.get('nodes', [])}
    
    for node in new_nodes:
        node_dict = node.dict()
        existing_nodes[node.url] = {
            **existing_nodes.get(node.url, {}),  # 保留旧字段
            **node_dict,  # 新字段覆盖
            "updated_at": datetime.now().isoformat()
        }
    
    return {
        "nodes": list(existing_nodes.values()),
        "sync_history": existing.get("sync_history", []) + [{
            "timestamp": datetime.now().isoformat(),
            "updated_count": len(new_nodes),
            "total_count": len(existing_nodes)
        }]
    }

# ==================== 异步后台任务 ====================

async def sync_to_supabase(nodes: List[NodeData], background_tasks: BackgroundTasks):
    """后台任务：同步到Supabase"""
    try:
        # TODO: 实现Supabase同步逻辑
        logger.info(f"📤 同步{len(nodes)}个节点到Supabase...")
        # await upload_to_supabase(nodes)
    except Exception as e:
        logger.error(f"Supabase同步失败: {e}")

async def sync_to_ipfs(nodes: List[NodeData]):
    """后台任务：同步到IPFS（可选）"""
    try:
        # TODO: 实现IPFS同步逻辑
        logger.info(f"📤 同步{len(nodes)}个节点到IPFS...")
        pass
    except Exception as e:
        logger.error(f"IPFS同步失败: {e}")

# ==================== Webhook端点 ====================

@webhook_router.post("/nodes-update")
async def receive_nodes_update(request: Request, background_tasks: BackgroundTasks):
    """
    接收来自SpiderFlow的节点更新推送
    
    请求体格式：
    {
        "event_type": "nodes_updated",
        "timestamp": "2026-01-01T12:00:00Z",
        "signature": "abc123...",
        "nodes": [
            {
                "url": "vmess://...",
                "name": "节点名",
                "country": "SG",
                "latency": 123.45,
                "speed": 45.67,
                ...
            }
        ],
        "total_count": 150,
        "verified_count": 145
    }
    """
    try:
        body = await request.json()
        
        # 提取签名信息
        timestamp = body.get("timestamp")
        signature = body.get("signature")
        
        if not timestamp or not signature:
            raise HTTPException(status_code=400, detail="缺少签名信息")
        
        # 生成payload（不包含签名字段）
        payload = {k: v for k, v in body.items() if k not in ["signature"]}
        payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        
        # 验证签名
        if not verify_webhook_signature(payload_str, timestamp, signature):
            logger.warning(f"❌ Webhook签名验证失败")
            raise HTTPException(status_code=401, detail="签名验证失败")
        
        # 解析数据
        event_type = body.get("event_type", "nodes_updated")
        nodes_data = [NodeData(**node) for node in body.get("nodes", [])]
        total_count = body.get("total_count", 0)
        verified_count = body.get("verified_count", 0)
        
        logger.info(f"✅ 收到Webhook推送 | 事件: {event_type} | 节点数: {len(nodes_data)}")
        
        # 1. 立即更新本地数据库
        existing = load_nodes_from_file()
        updated = merge_node_data(existing, nodes_data)
        save_nodes_to_file(updated)
        
        # 2. 触发异步同步任务
        background_tasks.add_task(sync_to_supabase, nodes_data, background_tasks)
        # background_tasks.add_task(sync_to_ipfs, nodes_data)
        
        return {
            "status": "success",
            "message": f"已接收{len(nodes_data)}个节点",
            "local_total": len(updated.get("nodes", [])),
            "timestamp": datetime.now().isoformat()
        }
        
    except ValueError as e:
        logger.error(f"JSON解析失败: {e}")
        raise HTTPException(status_code=400, detail="无效的JSON格式")
    except Exception as e:
        logger.error(f"Webhook处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@webhook_router.post("/test-connection")
async def test_webhook_connection():
    """用于测试Webhook连接的健康检查端点"""
    return {
        "status": "connected",
        "receiver": "viper-node-store",
        "webhook_version": "1.0",
        "timestamp": datetime.now().isoformat()
    }

# ==================== 调试端点 ====================

@webhook_router.get("/status")
async def get_webhook_status():
    """获取Webhook接收器状态"""
    db = load_nodes_from_file()
    return {
        "status": "active",
        "nodes_count": len(db.get("nodes", [])),
        "last_updated": db.get("last_updated"),
        "sync_history_count": len(db.get("sync_history", []))
    }

@webhook_router.post("/generate-signature")
async def generate_test_signature(payload_str: str, timestamp: str):
    """
    用于测试的签名生成器（仅用于开发）
    
    使用方式：
    1. 生成要发送的payload
    2. 调用此端点获取签名
    3. 使用signature进行webhook推送测试
    """
    signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        f"{payload_str}.{timestamp}".encode(),
        hashlib.sha256
    ).hexdigest()
    
    return {
        "signature": signature,
        "payload_sample": payload_str[:100] + "..."
    }
