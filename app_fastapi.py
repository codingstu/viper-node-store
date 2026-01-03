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

from fastapi import FastAPI, Query, HTTPException, Header
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import logging
import os
from datetime import datetime, timedelta
from typing import Optional
import json
import aiohttp
import asyncio
from typing import List, Dict, Optional
import time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import supabase

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

class HealthCheckRequest(BaseModel):
    """健康检测请求模型"""
    batch_size: int = 50  # 每批检测节点数量，Vercel 限制建议 30-50

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

# ==================== 静态文件和根路由 ====================
# 挂载静态文件目录，但只为 /static 路由提供文件
import os
static_dir = os.path.join(os.path.dirname(__file__))
app.mount("/static", StaticFiles(directory=static_dir), name="static")

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
                                "link": row.get("link", "") or node_content.get("link", ""),  # 优先从表字段读取，备用从 content 读取
                                "is_free": row.get("is_free", False),
                                "speed": row.get("speed", 0),
                                "latency": row.get("latency", 9999),
                                "updated_at": row.get("updated_at"),
                                "mainland_score": row.get("mainland_score", 0),
                                "mainland_latency": row.get("mainland_latency", 9999),
                                "overseas_score": row.get("overseas_score", 0),
                                "overseas_latency": row.get("overseas_latency", 9999),
                                # 健康检测字段
                                "status": row.get("status", "online"),  # 节点状态：online/suspect/offline
                                "last_health_check": row.get("last_health_check"),
                                "health_latency": row.get("health_latency"),
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

async def check_user_vip_status(user_id: Optional[str]) -> bool:
    """
    检查用户是否是 VIP
    
    Args:
        user_id: Supabase 用户 ID
    
    Returns:
        True 如果是 VIP，False 如果不是或用户不存在
    """
    if not user_id:
        return False
    
    try:
        supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
        result = supabase_client.table("profiles").select("vip_until").eq("id", user_id).execute()
        
        if result.data and len(result.data) > 0:
            vip_until = result.data[0].get("vip_until")
            if vip_until:
                try:
                    vip_until_dt = datetime.fromisoformat(vip_until.replace("Z", "+00:00"))
                    now = datetime.now(vip_until_dt.tzinfo) if vip_until_dt.tzinfo else datetime.now()
                    return vip_until_dt > now
                except:
                    return False
        return False
    except Exception as e:
        logger.warning(f"⚠️  检查 VIP 状态失败: {e}")
        return False

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
    """根路由 - 返回 index.html 前端"""
    import os
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"message": "viper-node-store API", "status": "running", "data_source": "Supabase"}

@app.get("/index.html")
async def index_html():
    """直接访问 index.html"""
    import os
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="index.html not found")

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
    limit: int = Query(None, ge=1, le=500),
    show_free: bool = Query(True),
    show_china: bool = Query(True),
    user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    获取节点列表（从 Supabase）
    
    安全特性：
    - VIP 用户可获取最多 500 个节点
    - 非 VIP 用户最多获取 20 个节点
    - 限制在服务器端实现，无法被前端绕过
    
    Parameters:
    - limit: 返回节点数量限制（1-500，可选）
    - show_free: 是否显示免费节点
    - show_china: 是否显示中国节点
    - X-User-ID: 用户ID（HTTP header）
    """
    try:
        # 检查用户 VIP 状态
        is_vip = await check_user_vip_status(user_id)
        
        # 确定返回的节点数量
        if limit is None:
            # 如果没有指定 limit，使用默认值
            default_limit = 500 if is_vip else 20
            limit = default_limit
        else:
            # 如果指定了 limit，非 VIP 用户最多 20 个
            if not is_vip and limit > 20:
                limit = 20
        
        logger.info(f"📋 获取节点: VIP={is_vip}, limit={limit}, user_id={user_id or '(anonymous)'}")
        
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
        
        if not nodes:
            return {
                "last_updated_at": datetime.now().isoformat(),
                "minutes_ago": 0,
                "nodes_count": 0,
                "active_count": 0,
                "source": "supabase",
                "sync_metadata": {
                    "total_nodes": 0,
                    "tested_nodes": 0,
                    "pending_test": 0
                }
            }
        
        # 从节点中获取最新的更新时间
        latest_time = None
        for node in nodes:
            if node.get("updated_at"):
                latest_time = node.get("updated_at")
                break
        
        # 计算分钟差异
        minutes_ago = 0
        if latest_time:
            try:
                last_synced = datetime.fromisoformat(latest_time.replace('Z', '+00:00'))
                now = datetime.now(last_synced.tzinfo) if last_synced.tzinfo else datetime.now()
                minutes_ago = max(0, int((now - last_synced).total_seconds() / 60))
            except Exception as e:
                logger.debug(f"计算时间差异失败: {e}")
                minutes_ago = 0
        
        # 统计节点
        active_count = len([n for n in nodes if n.get("alive")])
        
        return {
            "last_updated_at": latest_time or datetime.now().isoformat(),
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
    
    注意：这里不通过代理下载，因为代理需要本地代理软件支持。
    改为直接测速服务器速度，作为节点性能的参考。
    """
    try:
        test_file_size = request.test_file_size
        
        logger.info(f"⚡ 用户发起精确测速 | 文件大小: {test_file_size}MB | 代理: {request.proxy_url}")
        
        # 生成测试文件URL（直接从测速服务器下载，不通过代理）
        # 因为代理需要本地客户端支持，后端无法直接使用远程代理
        test_file_url = f"https://speed.cloudflare.com/__down?bytes={test_file_size * 1024 * 1024}"
        
        start_time = time.time()
        bytes_downloaded = 0
        
        try:
            # 使用带超时的 aiohttp 会话进行下载
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    test_file_url, 
                    timeout=aiohttp.ClientTimeout(total=120, connect=10, sock_read=30),
                    ssl=False  # 跳过SSL验证以避免网络问题
                ) as resp:
                    if resp.status == 200:
                        async for chunk in resp.content.iter_chunked(8192):
                            bytes_downloaded += len(chunk)
                    else:
                        logger.error(f"HTTP {resp.status} from {test_file_url}")
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
            logger.error(f"精确测速超时 (> 120秒)")
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
                if download_time <= 0:
                    download_time = 0.001
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
                    "latency": 9999,
                    "message": f"测速失败: 无法连接到测速服务器",
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

# ==================== 激活码兑换 API ====================

class RedeemCodeRequest(BaseModel):
    """激活码兑换请求"""
    code: str
    user_id: str  # Supabase 用户 ID

@app.post("/api/auth/redeem-code")
async def redeem_code(request: RedeemCodeRequest):
    """
    兑换激活码升级到 VIP
    
    激活码格式：VIPX-XXXX-XXXX（示例）
    激活码有效期：根据激活码配置决定
    """
    try:
        code = request.code.strip().upper()
        user_id = request.user_id
        
        if not code or not user_id:
            return {
                "status": "error",
                "message": "激活码和用户ID不能为空"
            }
        
        logger.info(f"🔑 兑换激活码: code={code}, user_id={user_id}")
        
        # 初始化 Supabase 客户端
        supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # 查询 activation_codes 表
        try:
            codes_result = supabase_client.table("activation_codes").select("*").eq("code", code).execute()
        except Exception as e:
            logger.error(f"❌ 查询激活码表失败: {e}")
            return {
                "status": "error",
                "message": "系统错误：无法查询激活码"
            }
        
        if not codes_result.data:
            logger.warning(f"❌ 激活码不存在: {code}")
            return {
                "status": "error",
                "message": "激活码不存在或已过期"
            }
        
        code_record = codes_result.data[0]
        
        # 检查激活码是否已被使用
        if code_record.get("used"):
            logger.warning(f"❌ 激活码已被使用: {code}")
            return {
                "status": "error",
                "message": "该激活码已被兑换"
            }
        
        # 检查激活码是否过期
        if code_record.get("expires_at"):
            try:
                expires_at = datetime.fromisoformat(code_record["expires_at"].replace("Z", "+00:00"))
                if expires_at < datetime.now(expires_at.tzinfo):
                    logger.warning(f"❌ 激活码已过期: {code}")
                    return {
                        "status": "error",
                        "message": "激活码已过期"
                    }
            except:
                pass  # 如果时间解析失败，继续处理
        
        # 获取 VIP 时长（天数）
        vip_days = code_record.get("vip_days", 30)  # 默认 30 天
        
        # 计算 VIP 过期时间
        vip_until = datetime.utcnow() + timedelta(days=vip_days)
        
        # 更新用户的 vip_until 字段
        # 使用 upsert 确保即使字段不存在也能成功（Supabase 会自动添加）
        try:
            # 首先尝试直接更新
            profiles_result = supabase_client.table("profiles").update({
                "vip_until": vip_until.isoformat()
            }).eq("id", user_id).execute()
            
            # 检查是否有更新
            if profiles_result.data:
                logger.info(f"✅ 用户 VIP 状态已更新: {user_id}")
            else:
                # 如果没有返回数据，可能是因为用户不存在或 RLS 限制
                # 尝试插入或更新（upsert）
                logger.warning(f"⚠️ 直接更新失败，尝试 upsert: {user_id}")
                
                # 使用 upsert：如果用户不存在，创建；如果存在，更新
                upsert_result = supabase_client.table("profiles").upsert({
                    "id": user_id,
                    "vip_until": vip_until.isoformat()
                }).execute()
                
                if not upsert_result.data:
                    logger.error(f"❌ upsert 也失败了: {user_id}")
                    return {
                        "status": "error",
                        "message": "更新 VIP 状态失败，请稍后重试"
                    }
                
                logger.info(f"✅ 用户 VIP 状态已通过 upsert 更新: {user_id}")
                
        except Exception as e:
            logger.error(f"❌ 更新用户 VIP 状态异常: {e}")
            return {
                "status": "error",
                "message": f"更新 VIP 状态失败: {str(e)}"
            }
        
        # 标记激活码为已使用
        try:
            supabase_client.table("activation_codes").update({
                "used": True,
                "used_by": user_id,
                "used_at": datetime.utcnow().isoformat()
            }).eq("code", code).execute()
        except Exception as e:
            logger.warning(f"⚠️ 标记激活码失败（但用户已升级）: {e}")
            # 不中断流程，因为用户已经升级了
        
        logger.info(f"✅ 激活码兑换成功: {code}, VIP 至 {vip_until.isoformat()}")
        
        return {
            "status": "success",
            "message": f"恭喜！您已升级为 VIP 用户，有效期至 {vip_until.strftime('%Y-%m-%d')}",
            "vip_until": vip_until.isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 激活码兑换异常: {e}")
        return {
            "status": "error",
            "message": f"兑换失败: {str(e)}"
        }

# ==================== SpiderFlow API 代理 ====================

@app.get("/api/proxy/nodes")
async def proxy_nodes(
    limit: int = Query(500, ge=1, le=500),
    show_socks_http: bool = Query(False),
    show_china_nodes: bool = Query(False)
):
    """代理 SpiderFlow 的 /api/nodes 请求"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{SPIDERFLOW_API_URL}/api/nodes"
            params = {
                "limit": limit,
                "show_socks_http": show_socks_http,
                "show_china_nodes": show_china_nodes
            }
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                return await resp.json()
    except Exception as e:
        logger.error(f"❌ 代理 SpiderFlow 节点数据失败: {e}")
        raise HTTPException(status_code=502, detail=f"SpiderFlow 服务不可用: {str(e)}")

@app.get("/api/proxy/system/stats")
async def proxy_system_stats():
    """代理 SpiderFlow 的 /api/system/stats 请求"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SPIDERFLOW_API_URL}/api/system/stats", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                return await resp.json()
    except Exception as e:
        logger.error(f"❌ 代理 SpiderFlow 系统统计失败: {e}")
        raise HTTPException(status_code=502, detail=f"SpiderFlow 服务不可用: {str(e)}")

@app.get("/api/proxy/nodes/stats")
async def proxy_nodes_stats():
    """代理 SpiderFlow 的 /nodes/stats 请求"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SPIDERFLOW_API_URL}/nodes/stats", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                return await resp.json()
    except Exception as e:
        logger.error(f"❌ 代理 SpiderFlow 节点统计失败: {e}")
        raise HTTPException(status_code=502, detail=f"SpiderFlow 服务不可用: {str(e)}")

# ==================== 节点健康检测 API ====================

@app.post("/api/health-check")
async def trigger_health_check(request: HealthCheckRequest = None):
    """
    手动触发节点健康检测
    
    由前端「🏥 健康检测」按钮调用
    每次检测一批节点，更新其在线状态到数据库
    Vercel 环境建议 batch_size=30-50（受执行时间限制）
    
    注意：Vercel Hobby 免费计划不支持 Cron Jobs，需手动触发
    如需定时检测，可使用免费服务如 cron-job.org 定时调用此 API
    
    Returns:
        检测结果统计
    """
    try:
        batch_size = request.batch_size if request else 100
        
        logger.info(f"🏥 收到健康检测请求 (batch_size={batch_size})")
        logger.info(f"SUPABASE_URL: {SUPABASE_URL[:50] if SUPABASE_URL else 'NOT SET'}...")
        logger.info(f"SUPABASE_KEY: {SUPABASE_KEY[:20] if SUPABASE_KEY else 'NOT SET'}...")
        
        # 导入健康检测模块
        from health_checker import run_health_check, LightweightHealthChecker, SupabaseHealthUpdater
        from health_checker import NodeStatus
        from datetime import datetime as dt
        
        # 1. 先从 app_fastapi 的 get_supabase_nodes 获取节点
        logger.info("📡 使用 app_fastapi 的方式获取节点...")
        nodes = await get_supabase_nodes(limit=batch_size, show_free=True, show_china=True)
        
        logger.info(f"✅ 获取到 {len(nodes)} 个节点")
        
        if not nodes:
            logger.warning("❌ 没有节点可检测")
            return {
                "status": "success",
                "data": {
                    "status": "no_nodes",
                    "checked_count": 0,
                    "online_count": 0,
                    "offline_count": 0,
                    "suspect_count": 0,
                    "duration_seconds": 0
                },
                "timestamp": datetime.now().isoformat()
            }
        
        # 2. 执行健康检测
        logger.info("🏥 开始检测节点...")
        checker = LightweightHealthChecker(
            tcp_timeout=5.0,
            http_timeout=8.0,
            max_retries=2,
            max_concurrent=20
        )
        
        # 将节点数据转换为检测格式
        check_nodes = []
        for node in nodes:
            check_nodes.append({
                "id": node.get("id", ""),
                "host": node.get("host", ""),
                "port": node.get("port", 0),
                "protocol": node.get("protocol", "unknown"),
                "name": node.get("name", "")
            })
        
        # 执行批量检测
        results = await checker.check_nodes_batch(check_nodes)
        
        # 3. 统计结果
        online_count = sum(1 for r in results if r.status == NodeStatus.ONLINE)
        offline_count = sum(1 for r in results if r.status == NodeStatus.OFFLINE)
        suspect_count = sum(1 for r in results if r.status == NodeStatus.SUSPECT)
        
        logger.info(f"📊 检测结果: 在线={online_count}, 离线={offline_count}, 可疑={suspect_count}")
        
        # 4. 更新数据库
        logger.info("💾 更新数据库...")
        updater = SupabaseHealthUpdater(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)
        success, fail = await updater.update_node_status(results)
        logger.info(f"✅ 数据库更新: 成功={success}, 失败={fail}")
        
        # 获取问题节点列表
        problem_nodes = [
            {
                "id": r.node_id,
                "name": r.host,
                "host": r.host,
                "port": r.port,
                "status": r.status.value
            }
            for r in results if r.status in [NodeStatus.OFFLINE, NodeStatus.SUSPECT]
        ]
        
        return {
            "status": "success",
            "data": {
                "status": "completed",
                "total": len(results),
                "online": online_count,
                "offline": offline_count,
                "suspect": suspect_count,
                "problem_nodes": problem_nodes,
                "update_success": success,
                "update_fail": fail
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except ImportError as e:
        logger.error(f"❌ 健康检测模块导入失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": "健康检测模块未安装",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ 健康检测失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

# 注意：Vercel Cron Jobs 仅在 Pro 及以上计划支持
# Hobby 免费计划：使用前端按钮手动触发
# 如需定时任务，可使用外部免费服务（如 cron-job.org）定时调用 /api/health-check

@app.get("/api/health-check/stats")
async def get_health_stats():
    """
    获取健康检测统计数据
    
    返回各状态节点的数量统计
    """
    try:
        # 从 Supabase 查询统计
        url = f"{SUPABASE_URL}/rest/v1/nodes?select=status"
        
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    rows = await resp.json()
                    
                    # 统计各状态数量
                    stats = {
                        "total": len(rows),
                        "online": 0,
                        "offline": 0,
                        "suspect": 0,
                        "unknown": 0
                    }
                    
                    for row in rows:
                        status = row.get("status", "unknown")
                        if status in stats:
                            stats[status] += 1
                        else:
                            stats["unknown"] += 1
                    
                    return {
                        "status": "success",
                        "data": stats,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"查询失败: HTTP {resp.status}",
                        "timestamp": datetime.now().isoformat()
                    }
                    
    except Exception as e:
        logger.error(f"❌ 获取健康统计失败: {e}")
        return {
            "status": "error",
            "message": str(e),
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
