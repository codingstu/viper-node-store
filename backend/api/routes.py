"""
API 路由模块 - 节点、同步、测速等端点
"""

from fastapi import APIRouter, Query, HTTPException, Header
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import aiohttp
import time
import asyncio

from ..config import config
from ..core.logger import logger
from .models import (
    PrecisionTestRequest, 
    LatencyTestRequest,
    HealthCheckRequest,
    RedeemCodeRequest
)
from ..services.node_service import NodeService
from ..services.auth_service import AuthService

# ==================== 路由组 ====================

router = APIRouter(prefix="/api")

# ==================== 依赖注入 ====================

node_service = NodeService()
auth_service = AuthService()

# ==================== 健康检查 ====================

@router.get("/status")
async def status():
    """API 状态检查"""
    return {
        "status": "running",
        "version": config.API_VERSION,
        "data_source": "Supabase",
        "timestamp": datetime.now().isoformat()
    }

# ==================== 节点 API ====================

@router.get("/nodes")
async def get_nodes(
    limit: int = Query(None, ge=1, le=config.MAX_NODE_LIMIT),
    show_free: bool = Query(True),
    show_china: bool = Query(True),
    user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    获取节点列表（从 Supabase）- 海外用户节点
    
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
        is_vip = await auth_service.check_user_vip_status(user_id)
        
        # 确定返回的节点数量
        if limit is None:
            limit = config.VIP_NODE_LIMIT if is_vip else config.DEFAULT_NODE_LIMIT
        else:
            if not is_vip and limit > config.DEFAULT_NODE_LIMIT:
                limit = config.DEFAULT_NODE_LIMIT
        
        logger.info(f"📋 获取海外节点: VIP={is_vip}, limit={limit}, user_id={user_id or '(anonymous)'}")
        
        nodes = await node_service.get_nodes(
            limit=limit,
            show_free=show_free,
            show_china=show_china
        )
        return nodes
        
    except Exception as e:
        logger.error(f"❌ 获取节点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/telegram-nodes")
async def get_telegram_nodes(
    limit: int = Query(None, ge=1, le=config.MAX_NODE_LIMIT),
    show_free: bool = Query(True),
    user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    获取 Telegram 节点列表（从 Supabase telegram_nodes 表）- 大陆用户节点
    
    安全特性：
    - VIP 用户可获取最多 500 个节点
    - 非 VIP 用户最多获取 20 个节点
    - 限制在服务器端实现，无法被前端绕过
    
    Parameters:
    - limit: 返回节点数量限制（1-500，可选）
    - show_free: 是否显示免费节点
    - X-User-ID: 用户ID（HTTP header）
    """
    try:
        # 检查用户 VIP 状态
        is_vip = await auth_service.check_user_vip_status(user_id)
        
        # 确定返回的节点数量
        if limit is None:
            limit = config.VIP_NODE_LIMIT if is_vip else config.DEFAULT_NODE_LIMIT
        else:
            if not is_vip and limit > config.DEFAULT_NODE_LIMIT:
                limit = config.DEFAULT_NODE_LIMIT
        
        logger.info(f"📋 获取大陆节点: VIP={is_vip}, limit={limit}, user_id={user_id or '(anonymous)'}")
        
        nodes = await node_service.get_telegram_nodes(
            limit=limit,
            show_free=show_free
        )
        return nodes
        
    except Exception as e:
        logger.error(f"❌ 获取 telegram 节点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 同步信息 API ====================

@router.get("/sync-info")
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
        sync_info = await node_service.get_sync_info()
        return sync_info
        
    except Exception as e:
        logger.error(f"❌ 获取同步信息失败: {e}")
        return {
            "last_updated_at": datetime.now().isoformat(),
            "minutes_ago": 0,
            "nodes_count": 0,
            "active_count": 0,
            "source": "error",
            "error": str(e)
        }

# ==================== 手动触发轮询 ====================

@router.post("/sync/poll-now")
async def trigger_manual_poll():
    """
    手动触发轮询（向 SpiderFlow 发送请求）
    注：实际数据仍从 Supabase 读取
    """
    try:
        # 向 SpiderFlow 触发轮询
        async with aiohttp.ClientSession() as session:
            trigger_url = f"{config.SPIDERFLOW_API_URL}/api/sync/poll-now"
            try:
                async with session.post(
                    trigger_url,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
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

@router.post("/nodes/precision-test")
async def precision_speed_test(request: PrecisionTestRequest):
    """
    用户发起的精确测速 - 真实下载测试
    
    注意：这里不通过代理下载，因为代理需要本地代理软件支持。
    改为直接测速服务器速度，作为节点性能的参考。
    """
    try:
        test_file_size = request.test_file_size
        
        logger.info(f"⚡ 用户发起精确测速 | 文件大小: {test_file_size}MB | 代理: {request.proxy_url}")
        
        # 生成测试文件URL
        test_file_url = f"https://speed.cloudflare.com/__down?bytes={test_file_size * 1024 * 1024}"
        
        start_time = time.time()
        bytes_downloaded = 0
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    test_file_url,
                    timeout=aiohttp.ClientTimeout(total=120, connect=10, sock_read=30),
                    ssl=False
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

# ==================== 延迟测试 API ====================

@router.post("/nodes/latency-test")
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
                async with session.head(
                    proxy_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    allow_redirects=False
                ) as resp:
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

@router.post("/auth/redeem-code")
async def redeem_code(request: RedeemCodeRequest):
    """
    兑换激活码升级到 VIP
    
    激活码格式：VIPX-XXXX-XXXX（示例）
    激活码有效期：根据激活码配置决定
    """
    try:
        result = await auth_service.redeem_activation_code(
            request.code.strip().upper(),
            request.user_id
        )
        return result
        
    except Exception as e:
        logger.error(f"❌ 激活码兑换异常: {e}")
        return {
            "status": "error",
            "message": f"兑换失败: {str(e)}"
        }

# ==================== 健康检测 API ====================

@router.post("/health-check")
async def trigger_health_check(
    request: HealthCheckRequest = None,
    user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    手动触发节点健康检测（仅限管理员）
    
    由前端「🏥 健康检测」按钮调用
    每次检测一批节点，更新其在线状态到数据库
    
    Parameters:
    - X-User-ID: 用户ID（HTTP header，必须是管理员）
    """
    try:
        # 验证管理员权限
        is_admin = await auth_service.check_user_admin_status(user_id)
        if not is_admin:
            logger.warning(f"⚠️ 非管理员尝试执行健康检测: user_id={user_id}")
            return {
                "status": "error",
                "message": "无权限：仅管理员可执行健康检测",
                "timestamp": datetime.now().isoformat()
            }
        
        batch_size = request.batch_size if request else 100
        source = request.source if request and hasattr(request, 'source') else "overseas"
        logger.info(f"🏥 收到健康检测请求 (batch_size={batch_size}, source={source}, admin={user_id})")
        
        # 根据 source 获取对应的节点
        if source == "china":
            nodes = await node_service.get_telegram_nodes(limit=batch_size)
        else:
            nodes = await node_service.get_nodes(limit=batch_size)
        
        logger.info(f"✅ 获取到 {len(nodes)} 个节点")
        
        if not nodes:
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
        
        # 执行健康检测（异步）
        result = await node_service.health_check_nodes(nodes)
        
        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 健康检测失败: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/health-check/stats")
async def get_health_stats():
    """
    获取健康检测统计数据
    
    返回各状态节点的数量统计
    """
    try:
        stats = await node_service.get_health_check_stats()
        
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 获取健康统计失败: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ==================== SpiderFlow 代理 ====================

@router.get("/proxy/nodes")
async def proxy_nodes(
    limit: int = Query(500, ge=1, le=500),
    show_socks_http: bool = Query(False),
    show_china_nodes: bool = Query(False)
):
    """代理 SpiderFlow 的 /api/nodes 请求"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{config.SPIDERFLOW_API_URL}/api/nodes"
            params = {
                "limit": limit,
                "show_socks_http": show_socks_http,
                "show_china_nodes": show_china_nodes
            }
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                return await resp.json()
                
    except Exception as e:
        logger.error(f"❌ 代理 SpiderFlow 节点数据失败: {e}")
        raise HTTPException(status_code=502, detail=f"SpiderFlow 服务不可用: {str(e)}")

@router.get("/proxy/system/stats")
async def proxy_system_stats():
    """代理 SpiderFlow 的 /api/system/stats 请求"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{config.SPIDERFLOW_API_URL}/api/system/stats",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                return await resp.json()
                
    except Exception as e:
        logger.error(f"❌ 代理 SpiderFlow 系统统计失败: {e}")
        raise HTTPException(status_code=502, detail=f"SpiderFlow 服务不可用: {str(e)}")

@router.get("/proxy/nodes/stats")
async def proxy_nodes_stats():
    """代理 SpiderFlow 的 /nodes/stats 请求"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{config.SPIDERFLOW_API_URL}/nodes/stats",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                return await resp.json()
                
    except Exception as e:
        logger.error(f"❌ 代理 SpiderFlow 节点统计失败: {e}")
        raise HTTPException(status_code=502, detail=f"SpiderFlow 服务不可用: {str(e)}")
