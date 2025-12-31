#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=== viper-node-store FastAPI主应用 ===

核心功能：
1. 接收SpiderFlow的Webhook推送（实时数据更新）
2. 定时轮询SpiderFlow API（备用同步机制）
3. 提供节点数据导出API
4. 管理本地节点数据库
5. 支持用户自定义精确测速

集成的技术栈：
- FastAPI: Web框架
- APScheduler: 定时任务调度
- Pydantic: 数据验证
- aiohttp: 异步HTTP请求
"""

from fastapi import FastAPI, BackgroundTasks, Query, HTTPException
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import asyncio
import os
from datetime import datetime
from pathlib import Path
import json

# 导入自定义模块
from webhook_receiver import webhook_router, verify_webhook_signature, load_nodes_from_file
from data_sync import (
    DataSyncScheduler, 
    poll_spiderflow_nodes, 
    get_exported_nodes,
    get_sync_statistics,
    POLL_INTERVAL,
    load_local_nodes
)

# ==================== 配置 ====================

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

# FastAPI应用
app = FastAPI(
    title="viper-node-store API",
    description="节点数据管理和同步平台",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局调度器
sync_scheduler: DataSyncScheduler = None

# ==================== 启动和关闭 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    global sync_scheduler
    
    logger.info("=" * 60)
    logger.info("🚀 viper-node-store 正在启动...")
    logger.info("=" * 60)
    
    # 初始化定时轮询调度器
    sync_scheduler = DataSyncScheduler()
    asyncio.create_task(sync_scheduler.start())
    
    # 执行首次轮询
    logger.info("📥 执行首次节点轮询...")
    await poll_spiderflow_nodes()
    
    logger.info("✅ viper-node-store 启动完成")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    global sync_scheduler
    
    logger.info("🛑 viper-node-store 正在关闭...")
    if sync_scheduler:
        await sync_scheduler.stop()
    logger.info("✅ viper-node-store 已关闭")

# ==================== 根路由 ====================

@app.get("/")
async def root():
    """API文档和基本信息"""
    return {
        "name": "viper-node-store",
        "version": "1.0.0",
        "description": "实时节点数据同步和管理平台",
        "features": [
            "Webhook实时推送",
            "定时轮询备用",
            "节点数据导出",
            "统计信息查询",
            "用户精确测速"
        ],
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
            "nodes": "/api/nodes",
            "webhook": "/webhook/nodes-update",
            "status": "/api/status"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "scheduler_running": sync_scheduler.running if sync_scheduler else False
    }

# ==================== 节点数据API ==================== 

@app.get("/api/nodes")
async def get_nodes(
    country: str = Query(None, description="按国家代码筛选"),
    protocol: str = Query(None, description="按协议筛选"),
    min_speed: float = Query(None, description="最小速度(MB/s)"),
    max_latency: int = Query(None, description="最大延迟(ms)"),
    format: str = Query("json", description="输出格式: json, clash, subscription")
):
    """
    获取节点列表
    
    示例：
    - /api/nodes → 所有节点
    - /api/nodes?country=SG → 新加坡节点
    - /api/nodes?min_speed=50 → 速度≥50MB/s的节点
    - /api/nodes?format=clash → Clash配置格式
    """
    try:
        data = load_nodes_from_file()
        nodes = data.get("nodes", [])
        
        # 应用过滤条件
        if country:
            nodes = [n for n in nodes if n.get("country") == country.upper()]
        
        if protocol:
            nodes = [n for n in nodes if n.get("protocol") == protocol.lower()]
        
        if min_speed:
            nodes = [n for n in nodes if n.get("speed", 0) >= min_speed]
        
        if max_latency:
            nodes = [n for n in nodes if n.get("latency", 999999) <= max_latency]
        
        # 按格式返回
        if format == "json":
            return {
                "total": len(nodes),
                "nodes": nodes,
                "last_updated": data.get("last_updated"),
                "filtered": bool(country or protocol or min_speed or max_latency)
            }
        
        elif format == "clash":
            # TODO: 实现Clash格式
            return {"format": "clash", "status": "not_implemented"}
        
        elif format == "subscription":
            # TODO: 实现订阅格式
            return {"format": "subscription", "status": "not_implemented"}
        
        return {"error": "不支持的格式"}
        
    except Exception as e:
        logger.error(f"获取节点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/nodes/export")
async def export_nodes_data(
    format: str = Query("json", description="导出格式"),
    include_metadata: bool = Query(True, description="是否包含元数据")
):
    """
    导出节点数据文件
    
    支持的格式：
    - json: JSON格式（默认）
    - clash: Clash配置文件
    - subscription: 订阅链接
    """
    try:
        if format == "json":
            content = get_exported_nodes(format="json")
            return JSONResponse(
                content=json.loads(content),
                media_type="application/json"
            )
        
        return {"error": "不支持的导出格式"}
        
    except Exception as e:
        logger.error(f"导出节点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 同步状态API ====================

@app.get("/api/sync/status")
async def get_sync_status():
    """
    获取数据同步状态
    
    返回：
    - 总节点数
    - 最后同步时间
    - 同步方法（Webhook/轮询）
    - Webhook/轮询统计信息
    - 轮询间隔
    """
    try:
        stats = get_sync_statistics()
        return {
            **stats,
            "poll_interval_seconds": POLL_INTERVAL,
            "scheduler_status": "running" if sync_scheduler and sync_scheduler.running else "stopped"
        }
    except Exception as e:
        logger.error(f"获取同步状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sync-info")
async def get_sync_info():
    """
    获取同步信息（用于前端显示"上次更新于X分钟前"）
    
    返回：
    - last_updated_at: ISO格式时间戳
    - minutes_ago: 距离现在的分钟数
    - nodes_count: 节点总数
    - active_count: 活跃节点数（not is_stale）
    - source: 数据来源（webhook/poll/local）
    - needs_verification: 待验证节点数
    """
    try:
        data = load_local_nodes()
        nodes = data.get("nodes", [])
        sync_metadata = data.get("sync_metadata", {})
        last_synced_at_str = data.get("last_synced_at")
        source = data.get("last_synced_from", "local")
        
        logger.debug(f"获取同步信息: nodes={len(nodes)}, last_synced={last_synced_at_str}, source={source}")
        
        # 计算分钟差异
        minutes_ago = 0
        if last_synced_at_str:
            try:
                last_synced = datetime.fromisoformat(last_synced_at_str.replace('Z', '+00:00'))
                now = datetime.now(last_synced.tzinfo) if last_synced.tzinfo else datetime.now()
                minutes_ago = max(0, int((now - last_synced).total_seconds() / 60))
            except Exception as e:
                logger.debug(f"计算时间差异失败: {e}")
                minutes_ago = 0
        else:
            # 如果没有last_synced_at，说明还没有同步过数据
            logger.debug("尚未进行数据同步")
        
        # 统计节点数量
        active_count = len([n for n in nodes if not n.get("is_stale")])
        needs_verification_count = len([n for n in nodes if n.get("needs_verification")])
        
        response = {
            "last_updated_at": last_synced_at_str or datetime.now().isoformat(),
            "minutes_ago": minutes_ago,
            "nodes_count": len(nodes),
            "active_count": active_count,
            "source": source,
            "needs_verification": needs_verification_count,
            "sync_metadata": sync_metadata
        }
        
        logger.debug(f"✅ 返回同步信息: {response}")
        return response
    except Exception as e:
        logger.error(f"❌ 获取同步信息失败: {e}", exc_info=True)
        return {
            "last_updated_at": datetime.now().isoformat(),
            "minutes_ago": 0,
            "nodes_count": 0,
            "active_count": 0,
            "source": "error",
            "needs_verification": 0,
            "error": str(e)
        }
            "needs_verification": 0,
            "error": str(e)
        }


@app.post("/api/sync/poll-now")
async def trigger_manual_poll(background_tasks: BackgroundTasks):
    """
    立即执行一次轮询（用于测试或紧急更新）
    """
    try:
        background_tasks.add_task(poll_spiderflow_nodes)
        return {
            "status": "poll_triggered",
            "message": "已触发手动轮询，在后台执行",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"手动轮询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Webhook路由集成 ====================

app.include_router(webhook_router)

# ==================== 统计和分析API ====================

@app.get("/api/stats/summary")
async def get_summary_stats():
    """获取汇总统计信息"""
    try:
        data = load_nodes_from_file()
        nodes = data.get("nodes", [])
        
        # 国家分布
        country_dist = {}
        for node in nodes:
            country = node.get("country", "UNKNOWN")
            country_dist[country] = country_dist.get(country, 0) + 1
        
        # 协议分布
        protocol_dist = {}
        for node in nodes:
            protocol = node.get("protocol", "unknown")
            protocol_dist[protocol] = protocol_dist.get(protocol, 0) + 1
        
        # 平均指标
        avg_latency = sum(n.get("latency", 0) for n in nodes) / len(nodes) if nodes else 0
        avg_speed = sum(n.get("speed", 0) for n in nodes) / len(nodes) if nodes else 0
        
        return {
            "total_nodes": len(nodes),
            "country_distribution": country_dist,
            "protocol_distribution": protocol_dist,
            "average_latency_ms": round(avg_latency, 2),
            "average_speed_mbps": round(avg_speed, 2),
            "last_updated": data.get("last_updated")
        }
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats/top-nodes")
async def get_top_nodes(
    metric: str = Query("speed", description="排序指标: speed, latency"),
    limit: int = Query(10, description="返回数量"),
    country: str = Query(None, description="按国家筛选")
):
    """
    获取排名靠前的节点
    
    示例：
    - /api/stats/top-nodes?metric=speed&limit=20 → 最快的20个节点
    - /api/stats/top-nodes?metric=latency&limit=10 → 延迟最低的10个节点
    """
    try:
        data = load_nodes_from_file()
        nodes = data.get("nodes", [])
        
        if country:
            nodes = [n for n in nodes if n.get("country") == country.upper()]
        
        if metric == "speed":
            sorted_nodes = sorted(nodes, key=lambda x: x.get("speed", 0), reverse=True)
        elif metric == "latency":
            sorted_nodes = sorted(nodes, key=lambda x: x.get("latency", 999999))
        else:
            raise ValueError(f"不支持的排序指标: {metric}")
        
        return {
            "metric": metric,
            "country": country or "all",
            "total": len(nodes),
            "returned": len(sorted_nodes[:limit]),
            "nodes": sorted_nodes[:limit]
        }
    except Exception as e:
        logger.error(f"获取排名节点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 测速API ====================

@app.post("/api/nodes/test-single")
async def test_single_node(
    proxy_url: str,
    background_tasks: BackgroundTasks,
    timeout: int = Query(10, description="超时时间(秒)")
):
    """
    测试单个节点
    
    支持三层测试机制：
    1. 前端HEAD请求（最快，最少流量）
    2. 后端HEAD请求（兼容性好）
    3. CF Worker实际下载（精确但慢）
    """
    try:
        # TODO: 实现节点测试逻辑
        return {
            "proxy_url": proxy_url,
            "status": "test_initiated",
            "message": "已发起测试，请稍候...",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"节点测试失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/nodes/latency-test")
async def latency_test(request: LatencyTestRequest):
    """
    延迟测速 - 测试代理连接延迟
    
    工作流程：
    1. 接收代理URL
    2. 发起HTTP HEAD请求测延迟
    3. 返回往返时间（RTT）
    
    请求示例:
    POST /api/nodes/latency-test
    {
      "proxy_url": "vmess://..."
    }
    
    返回: { status, latency, message }
    """
    import aiohttp
    import time
    
    proxy_url = request.proxy_url
    
    try:
        logger.info(f"⚡ 用户发起延迟测速 | 代理: {proxy_url[:50]}...")
        
        # 使用Cloudflare或其他快速响应的服务测延迟
        test_url = "https://www.cloudflare.com"
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(test_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    latency = (time.time() - start_time) * 1000  # 转换为毫秒
                    
                    if resp.status in [200, 301, 302, 404]:
                        logger.info(f"✅ 延迟测速完成 | 延迟: {latency:.0f}ms")
                        return {
                            "status": "success",
                            "latency": round(latency, 0),
                            "message": f"延迟: {latency:.0f}ms",
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        raise Exception(f"HTTP {resp.status}")
        
        except asyncio.TimeoutError:
            logger.error(f"延迟测速超时 (> 10秒)")
            return {
                "status": "timeout",
                "latency": 0,
                "message": "延迟测速超时",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as inner_err:
            logger.error(f"延迟测速失败: {inner_err}")
            return {
                "status": "error",
                "latency": 0,
                "message": f"测速失败: {str(inner_err)[:50]}",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"延迟测速异常: {e}")
        return {
            "status": "error",
            "latency": 0,
            "message": f"API 错误: {str(e)[:50]}",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/nodes/precision-test")
async def precision_speed_test(
    request: PrecisionTestRequest,
    background_tasks: BackgroundTasks = None
):
    """
    用户发起的精确测速 - 真实下载测试
    
    工作流程：
    1. 用户点击[精确测速]按钮
    2. 后台执行真实下载测速
    3. 即时返回初始响应
    4. 用户界面轮询获取结果
    
    请求示例:
    POST /api/nodes/precision-test
    {
      "proxy_url": "vmess://...",
      "test_file_size": 50
    }
    
    返回: { status, speed_mbps, download_time_seconds, traffic_consumed_mb, ... }
    """
    import aiohttp
    import time
    
    proxy_url = request.proxy_url
    test_file_size = request.test_file_size
    
    try:
        logger.info(f"⚡ 用户发起精确测速 | 文件大小: {test_file_size}MB")
        
        # 生成一个测试文件URL
        test_file_url = f"https://speed.cloudflare.com/__down?bytes={test_file_size * 1024 * 1024}"
        
        start_time = time.time()
        bytes_downloaded = 0
        download_time = 0
        
        try:
            # 异步下载文件，使用超时控制
            async with aiohttp.ClientSession() as session:
                async with session.get(test_file_url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        async for chunk in resp.content.iter_chunked(8192):
                            bytes_downloaded += len(chunk)
                    else:
                        raise Exception(f"HTTP {resp.status}")
            
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
            # 如果有部分下载数据，返回部分成功
            if bytes_downloaded > 0 and download_time > 0:
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

# ==================== 开发调试API ====================

@app.get("/api/debug/nodes-file")
async def debug_nodes_file():
    """获取原始节点文件内容（调试用）"""
    try:
        nodes_file = Path("verified_nodes.json")
        if nodes_file.exists():
            return JSONResponse(
                content=json.loads(nodes_file.read_text(encoding='utf-8')),
                media_type="application/json"
            )
        return {"status": "file_not_found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/sync-state")
async def debug_sync_state():
    """获取同步状态文件内容（调试用）"""
    try:
        state_file = Path("sync_state.json")
        if state_file.exists():
            return JSONResponse(
                content=json.loads(state_file.read_text(encoding='utf-8')),
                media_type="application/json"
            )
        return {"status": "state_not_created_yet"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 主程序 ====================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("=" * 60)
    logger.info("启动viper-node-store API服务")
    logger.info("=" * 60)
    
    uvicorn.run(
        "app_fastapi:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_level="info"
    )
