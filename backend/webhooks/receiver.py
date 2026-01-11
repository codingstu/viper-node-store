"""
Webhook 接收和处理 - 复制自 webhook_receiver.py
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

# ==================== 数据模型 ====================

class NodeData(BaseModel):
    """节点数据模型"""
    protocol: str
    host: str
    port: int
    name: str
    country: str
    mainland_score: Optional[int] = 0
    mainland_latency: Optional[int] = 9999
    overseas_score: Optional[int] = 0
    overseas_latency: Optional[int] = 9999
    link: Optional[str] = ""
    is_free: Optional[bool] = False


class WebhookPayload(BaseModel):
    """Webhook 负载模型"""
    nodes: List[NodeData]
    timestamp: str


class WebhookSignature(BaseModel):
    """Webhook 签名模型"""
    payload_str: str
    timestamp: str
    signature: str


# ==================== 工具函数 ====================

def verify_webhook_signature(payload_str: str, timestamp: str, signature: str) -> bool:
    """
    验证 Webhook 签名
    
    使用 HMAC-SHA256 验证，防止伪造请求
    """
    webhook_secret = os.environ.get("WEBHOOK_SECRET", "")
    
    if not webhook_secret:
        logger.warning("⚠️ WEBHOOK_SECRET 未配置，无法验证签名")
        return False
    
    # 构造待签名的字符串：payload + timestamp
    message = f"{payload_str}{timestamp}".encode()
    
    # 计算签名
    expected_signature = hmac.new(
        webhook_secret.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    
    # 比对签名（使用恒定时间比较防止时间攻击）
    return hmac.compare_digest(signature, expected_signature)


# ==================== Webhook 路由 ====================

router = APIRouter(prefix="/webhooks")


@router.post("/nodes")
async def webhook_nodes(request: Request, background_tasks: BackgroundTasks):
    """
    接收节点数据 Webhook
    
    来自 SpiderFlow 的 Webhook，推送最新节点数据
    """
    try:
        # 读取请求体
        body = await request.body()
        payload_str = body.decode('utf-8')
        
        # 获取签名头
        timestamp = request.headers.get("X-Webhook-Timestamp", "")
        signature = request.headers.get("X-Webhook-Signature", "")
        
        # 验证签名
        if not verify_webhook_signature(payload_str, timestamp, signature):
            logger.warning("❌ Webhook 签名验证失败")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # 解析 JSON
        payload = json.loads(payload_str)
        nodes_data = payload.get("nodes", [])
        
        logger.info(f"✅ 收到 Webhook 推送: {len(nodes_data)} 个节点")
        
        # 异步后台处理
        background_tasks.add_task(process_webhook_nodes, nodes_data)
        
        return {
            "status": "received",
            "message": f"已接收 {len(nodes_data)} 个节点",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Webhook 处理失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


async def process_webhook_nodes(nodes_data: List[Dict]):
    """
    后台处理 Webhook 节点数据
    
    将节点数据同步到 Supabase
    """
    try:
        logger.info(f"🔄 开始处理 {len(nodes_data)} 个节点...")
        
        # TODO: 实现数据同步逻辑
        # - 去重
        # - 数据验证
        # - 更新 Supabase
        
        logger.info(f"✅ 处理完成")
        
    except Exception as e:
        logger.error(f"❌ 处理节点数据失败: {e}")
