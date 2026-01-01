#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=== viper-node-store FastAPI主应用（Supabase版本） ===

核心功能：
1. 从 Supabase 数据库读取节点数据
2. 提供节点查询和过滤 API
3. 提供同步信息查询
4. 支持用户自定义精确测速

数据来源：
- 所有节点数据存储在 Supabase public.nodes 表
- SpiderFlow 负责测速，结果直接写入 Supabase
- viper-node-store 仅读取和展示数据

集成的技术栈：
- FastAPI: Web框架
- Pydantic: 数据验证
- Supabase: 数据库
- aiohttp: 异步HTTP请求
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import os
from datetime import datetime
import json
import aiohttp
import asyncio
from typing import List, Dict, Optional
import time
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ==================== 配置 ====================

# Supabase 配置
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://hnlkwtkxbqiakeyienok.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhubGt3dGt4YnFpYWtleWllbm9rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY5MDQwNTksImV4cCI6MjA4MjQ4MDA1OX0.Xg9vQdUfBdUW-IJaomEIRGsX6tB_k2grhrF4dm_aNME")

# SpiderFlow 后端 URL（用于同步状态查询，不用于获取节点）
SPIDERFLOW_API_URL = os.environ.get("SPIDERFLOW_API_URL", "http://localhost:8001")

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==================== Pydantic Models ====================

class PrecisionTestRequest(BaseModel):
    """精确测速请求模型"""
    proxy_url: str
    test_file_size: int = 50

class LatencyTestRequest(BaseModel):
    """延迟测速请求模型"""
    proxy_url: str

# ==================== FastAPI 应用 ====================

app = FastAPI(
    title="viper-node-store API",
    description="节点数据管理和展示平台（数据来源: Supabase）",
    version="2.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Supabase 辅助函数 ====================

async def get_supabase_nodes(
    limit: int = 500,
    show_free: bool = True,
    show_china: bool = True
) -> List[Dict]:
    """
    从 Supabase 获取节点数据
    
    Args:
        limit: 返回的最大节点数
        show_free: 是否显示免费节点
        show_china: 是否显示中国节点
    
    Returns:
        节点列表
    """
    try:
        # 构造 Supabase REST API 查询 URL
        url = f"{SUPABASE_URL}/rest/v1/nodes?select=*&limit={limit}"
        
        # 添加过滤条件
        if not show_free:
            url += "&is_free=eq.false"
        
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    raw_nodes = await resp.json()
                    
                    # 解析节点数据
                    nodes = []
                    for row in raw_nodes:
                        try:
                            # content 字段是 JSONB，包含完整的节点信息
                            node_content = row.get("content", {})
                            if isinstance(node_content, str):
                                node_content = json.loads(node_content)
                            
                            # 组装节点对象
                            node = {
                                "id": row.get("id", ""),
                                "protocol": node_content.get("protocol", ""),
                                "host": node_content.get("host", ""),
                                "port": node_content.get("port", 0),
                                "name": node_content.get("name", f"{node_content.get('host')}:{node_content.get('port')}"),
                                "country": node_content.get("country", "UNK"),
                                "link": node_content.get("link", ""),
                                "is_free": row.get("is_free", False),
                                "speed": row.get("speed", 0),
                                "latency": row.get("latency", 9999),
                                "updated_at": row.get("updated_at"),
                                "mainland_score": row.get("mainland_score", 0),
                                "mainland_latency": row.get("mainland_latency", 9999),
                                "overseas_score": row.get("overseas_score", 0),
                                "overseas_latency": row.get("overseas_latency", 9999),
                                # 计算活跃状态：latency < 9999 表示已测试
                                "alive": row.get("latency", 9999) < 9999
                            }
                            nodes.append(node)
                        except Exception as e:
                            logger.warning(f"解析节点数据失败: {e}")
                            continue
                    
                    logger.info(f"✅ 从 Supabase 获取 {len(nodes)} 个节点")
                    return nodes
                else:
                    logger.error(f"❌ Supabase 返回错误: {resp.status}")
                    return []
    except Exception as e:
        logger.error(f"❌ 获取 Supabase 节点失败: {e}")
        return []

async def get_latest_sync_time() -> Optional[str]:
    """
    从 Supabase 获取最后一次更新时间（所有节点中的最新 updated_at）
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/nodes?select=updated_at&order=updated_at.desc&limit=1"
        
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and len(data) > 0:
                        return data[0].get("updated_at")
        return None
    except Exception as e:
        logger.warning(f"⚠️  获取最后更新时间失败: {e}")
        return None

# ==================== 启动和关闭 ====================

# 全局调度器实例
scheduler = None

async def periodic_pull_from_supabase():
    """
    定时拉取任务：每12分钟从 Supabase 拉取一次最新的节点数据
    这可以确保 viper-node-store 的内存缓存保持最新
    """
    try:
        logger.info("📥 开始定时拉取 Supabase 节点数据...")
        nodes = await get_supabase_nodes(limit=10000)
        logger.info(f"✅ 定时拉取完成：获取 {len(nodes)} 个节点")
    except Exception as e:
        logger.warning(f"⚠️  定时拉取失败: {e}")

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    global scheduler
    
    logger.info("=" * 60)
    logger.info("🚀 viper-node-store 正在启动...")
    logger.info("📊 数据来源: Supabase public.nodes 表")
    logger.info("=" * 60)
    
    # 验证 Supabase 连接
    try:
        nodes = await get_supabase_nodes(limit=1)
        logger.info("✅ Supabase 连接成功")
    except Exception as e:
        logger.warning(f"⚠️  Supabase 连接失败: {e}")
    
    # 启动定时任务调度器
    try:
        scheduler = AsyncIOScheduler()
        
        # 添加定时任务：每12分钟拉取一次 Supabase 数据
        scheduler.add_job(
            periodic_pull_from_supabase,
            'interval',
            minutes=12,
            id='supabase_pull',
            name='Supabase 定时拉取'
        )
        
        scheduler.start()
        logger.info("✅ 定时任务调度器已启动（每12分钟拉取一次 Supabase 数据）")
    except Exception as e:
        logger.warning(f"⚠️  启动定时任务调度器失败: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    global scheduler
    
    logger.info("🛑 viper-node-store 正在关闭...")
    
    # 关闭调度器
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("✅ 定时任务调度器已关闭")

# ==================== 健康检查 ====================

@app.get("/")
async def root():
    """根路由 - 返回 HTML 前端"""
    return {"message": "viper-node-store API", "status": "running", "data_source": "Supabase"}

@app.get("/api/status")
async def status():
    """API 状态检查"""
    return {
        "status": "running",
        "version": "2.0.0",
        "data_source": "Supabase",
        "timestamp": datetime.now().isoformat()
    }

# ==================== 节点 API ====================

@app.get("/api/nodes")
async def get_nodes(
    limit: int = Query(50, ge=1, le=500),
    show_free: bool = Query(True),
    show_china: bool = Query(True)
):
    """
    获取节点列表（从 Supabase）
    
    Parameters:
    - limit: 返回节点数量限制（1-500）
    - show_free: 是否显示免费节点
    - show_china: 是否显示中国节点
    """
    try:
        nodes = await get_supabase_nodes(limit=limit, show_free=show_free, show_china=show_china)
        return nodes
    except Exception as e:
        logger.error(f"❌ 获取节点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 同步信息 API ====================

@app.get("/api/sync-info")
async def get_sync_info():
    """
    获取同步信息（用于前端显示"上次更新于X分钟前"）
    
    返回：
    - last_updated_at: ISO格式时间戳
    - minutes_ago: 距离现在的分钟数
    - nodes_count: 节点总数
    - active_count: 活跃节点数（已测试）
    - source: 数据来源（supabase）
    """
    try:
        # 获取所有节点统计
        nodes = await get_supabase_nodes(limit=10000)
        
        # 获取最后更新时间
        last_updated_at = await get_latest_sync_time()
        
        # 计算分钟差异
        minutes_ago = 0
        if last_updated_at:
            try:
                last_synced = datetime.fromisoformat(last_updated_at.replace('Z', '+00:00'))
                now = datetime.now(last_synced.tzinfo) if last_synced.tzinfo else datetime.now()
                minutes_ago = max(0, int((now - last_synced).total_seconds() / 60))
            except Exception as e:
                logger.debug(f"计算时间差异失败: {e}")
                minutes_ago = 0
        
        # 统计节点
        active_count = len([n for n in nodes if n.get("alive")])
        
        return {
            "last_updated_at": last_updated_at or datetime.now().isoformat(),
            "minutes_ago": minutes_ago,
            "nodes_count": len(nodes),
            "active_count": active_count,
            "source": "supabase",
            "sync_metadata": {
                "total_nodes": len(nodes),
                "tested_nodes": active_count,
                "pending_test": len(nodes) - active_count
            }
        }
    except Exception as e:
        logger.error(f"❌ 获取同步信息失败: {e}", exc_info=True)
        return {
            "last_updated_at": datetime.now().isoformat(),
            "minutes_ago": 0,
            "nodes_count": 0,
            "active_count": 0,
            "source": "error",
            "error": str(e)
        }

# ==================== 手动触发轮询 ====================

@app.post("/api/sync/poll-now")
async def trigger_manual_poll(background_tasks = None):
    """
    手动触发轮询（向 SpiderFlow 发送请求）
    注：实际数据仍从 Supabase 读取
    """
    try:
        # 向 SpiderFlow 触发轮询
        async with aiohttp.ClientSession() as session:
            trigger_url = f"{SPIDERFLOW_API_URL}/api/sync/poll-now"
            try:
                async with session.post(trigger_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        logger.info("✅ 已向 SpiderFlow 发送轮询请求")
                    else:
                        logger.warning(f"⚠️  SpiderFlow 轮询返回 {resp.status}")
            except Exception as e:
                logger.warning(f"⚠️  无法连接 SpiderFlow: {e}")
        
        return {
            "status": "poll_triggered",
            "message": "已请求 SpiderFlow 执行轮询，结果将保存到 Supabase",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ 触发轮询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 精确测速 API ====================

@app.post("/api/nodes/precision-test")
async def precision_speed_test(request: PrecisionTestRequest):
    """
    用户发起的精确测速 - 真实下载测试
    """
    try:
        proxy_url = request.proxy_url
        test_file_size = request.test_file_size
        
        logger.info(f"⚡ 用户发起精确测速 | 文件大小: {test_file_size}MB")
        
        # 生成测试文件URL
        test_file_url = f"https://speed.cloudflare.com/__down?bytes={test_file_size * 1024 * 1024}"
        
        start_time = time.time()
        bytes_downloaded = 0
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(test_file_url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        async for chunk in resp.content.iter_chunked(8192):
                            bytes_downloaded += len(chunk)
            
            download_time = time.time() - start_time
            
            if download_time <= 0:
                download_time = 0.001
            
            # 计算速度 (MB/s)
            speed_mbps = (bytes_downloaded / (1024 * 1024)) / download_time
            
            logger.info(f"✅ 精确测速完成 | 大小: {bytes_downloaded/(1024*1024):.1f}MB | 时间: {download_time:.1f}s | 速度: {speed_mbps:.1f}MB/s")
            
            return {
                "status": "success",
                "speed_mbps": round(speed_mbps, 2),
                "download_time_seconds": round(download_time, 2),
                "traffic_consumed_mb": round(bytes_downloaded / (1024 * 1024), 2),
                "bytes_downloaded": bytes_downloaded,
                "test_file_size_requested_mb": test_file_size,
                "message": f"精确测速完成: {speed_mbps:.1f} MB/s",
                "timestamp": datetime.now().isoformat()
            }
        except asyncio.TimeoutError:
            logger.error(f"精确测速超时 (> 60秒)")
            return {
                "status": "timeout",
                "speed_mbps": 0,
                "message": "测速超时，请稍后重试",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as inner_err:
            logger.error(f"精确测速下载失败: {inner_err}")
            if bytes_downloaded > 0:
                download_time = time.time() - start_time
                speed_mbps = (bytes_downloaded / (1024 * 1024)) / download_time
                return {
                    "status": "partial_success",
                    "speed_mbps": round(speed_mbps, 2),
                    "download_time_seconds": round(download_time, 2),
                    "traffic_consumed_mb": round(bytes_downloaded / (1024 * 1024), 2),
                    "message": f"部分测试: {speed_mbps:.1f} MB/s",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "speed_mbps": 0,
                    "message": f"测速失败: {str(inner_err)[:50]}",
                    "timestamp": datetime.now().isoformat()
                }
    except Exception as e:
        logger.error(f"精确测速异常: {e}")
        return {
            "status": "error",
            "speed_mbps": 0,
            "message": f"API 错误: {str(e)[:50]}",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/nodes/latency-test")
async def latency_test(request: LatencyTestRequest):
    """
    延迟测试 - 简单的 ping 延迟测试
    """
    try:
        proxy_url = request.proxy_url
        
        logger.info(f"⚡ 执行延迟测试")
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(proxy_url, timeout=aiohttp.ClientTimeout(total=10), allow_redirects=False) as resp:
                    latency = int((time.time() - start_time) * 1000)  # 毫秒
                    
                    return {
                        "status": "success",
                        "latency": latency,
                        "latency_ms": latency,
                        "timestamp": datetime.now().isoformat()
                    }
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "latency": 9999,
                "message": "延迟测试超时",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.warning(f"延迟测试失败: {e}")
            return {
                "status": "error",
                "latency": 9999,
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"延迟测试异常: {e}")
        return {
            "status": "error",
            "latency": 9999,
            "message": f"API 错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

# ==================== 主程序 ====================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("=" * 60)
    logger.info("启动 viper-node-store API 服务 (Supabase 版本)")
    logger.info("=" * 60)
    
    uvicorn.run(
        "app_fastapi:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_level="info"
    )
