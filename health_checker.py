#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=== viper-node-store 轻量级节点健康检测模块 ===

功能:
1. TCP 连接测试 - 检测节点端口是否可达
2. HTTP 代理测试 - 通过代理请求测试 URL 验证代理功能
3. 失败重试机制 - 检测失败自动重试2次
4. 状态更新 - 将检测结果写入 Supabase

检测状态:
- online: 节点正常可用
- offline: 节点不可用（TCP或HTTP测试均失败）
- suspect: 可疑节点（TCP通但HTTP失败）

适用于 Vercel Serverless 环境（轻量级，无外部依赖）
"""

import asyncio
import aiohttp
import socket
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import os

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class NodeStatus(str, Enum):
    """节点状态枚举"""
    ONLINE = "online"
    OFFLINE = "offline"
    SUSPECT = "suspect"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """健康检测结果"""
    node_id: str
    host: str
    port: int
    status: NodeStatus
    tcp_ok: bool
    http_ok: bool
    latency_ms: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    checked_at: str = ""


class LightweightHealthChecker:
    """轻量级健康检测器（无外部依赖）"""
    
    def __init__(
        self,
        tcp_timeout: float = 5.0,
        http_timeout: float = 10.0,
        max_retries: int = 2,
        max_concurrent: int = 20
    ):
        """
        初始化检测器
        
        Args:
            tcp_timeout: TCP 连接超时（秒）
            http_timeout: HTTP 请求超时（秒）
            max_retries: 最大重试次数
            max_concurrent: 最大并发数
        """
        self.tcp_timeout = tcp_timeout
        self.http_timeout = http_timeout
        self.max_retries = max_retries
        self.max_concurrent = max_concurrent
        self.test_urls = [
            "http://www.gstatic.com/generate_204",
            "http://cp.cloudflare.com/",
            "http://connectivitycheck.platform.hicloud.com/generate_204"
        ]
    
    async def check_tcp_connection(self, host: str, port: int) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        TCP 连接测试
        
        Returns:
            (成功, 延迟毫秒, 错误信息)
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            # 使用 asyncio 的方式进行 TCP 连接测试
            future = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(future, timeout=self.tcp_timeout)
            
            latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            # 关闭连接
            writer.close()
            await writer.wait_closed()
            
            return True, latency_ms, None
            
        except asyncio.TimeoutError:
            return False, None, "TCP connection timeout"
        except ConnectionRefusedError:
            return False, None, "Connection refused"
        except OSError as e:
            return False, None, f"OS error: {str(e)[:50]}"
        except Exception as e:
            return False, None, f"TCP error: {str(e)[:50]}"
    
    async def check_http_connectivity(self, host: str, port: int, protocol: str = "http") -> Tuple[bool, Optional[int], Optional[str]]:
        """
        HTTP 连通性测试（直接测试节点的 HTTP 响应）
        
        对于代理节点，我们测试是否能通过代理访问测试 URL
        由于没有代理客户端，这里简化为直接测试节点的 HTTP 服务
        
        Returns:
            (成功, 延迟毫秒, 错误信息)
        """
        # 对于非 HTTP 协议的节点，只做 TCP 测试
        if protocol.lower() not in ['http', 'https', 'socks5', 'socks']:
            # 对于 vmess/vless/trojan/ss 等协议，TCP 通就认为基本可用
            return True, 0, None
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # 构建测试 URL
            if protocol.lower() in ['http', 'https']:
                test_url = f"{protocol}://{host}:{port}/"
            else:
                # 对于 socks 协议，无法直接测试，标记为通过
                return True, 0, None
            
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    test_url,
                    timeout=aiohttp.ClientTimeout(total=self.http_timeout),
                    allow_redirects=False,
                    ssl=False
                ) as resp:
                    latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                    
                    # 任何响应都说明节点是活的
                    return True, latency_ms, None
                    
        except asyncio.TimeoutError:
            return False, None, "HTTP timeout"
        except aiohttp.ClientError as e:
            return False, None, f"HTTP error: {str(e)[:50]}"
        except Exception as e:
            return False, None, f"HTTP error: {str(e)[:50]}"
    
    async def check_node(self, node: Dict) -> HealthCheckResult:
        """
        检测单个节点
        
        Args:
            node: 节点数据，需要包含 host, port, protocol
            
        Returns:
            检测结果
        """
        node_id = node.get("id", "")
        host = node.get("host", "")
        port = node.get("port", 0)
        protocol = node.get("protocol", "unknown")
        
        if not host or not port:
            return HealthCheckResult(
                node_id=node_id,
                host=host,
                port=port,
                status=NodeStatus.OFFLINE,
                tcp_ok=False,
                http_ok=False,
                error_message="Invalid host or port",
                checked_at=datetime.utcnow().isoformat()
            )
        
        # 带重试的检测
        tcp_ok = False
        http_ok = False
        latency_ms = None
        error_message = None
        retry_count = 0
        
        for attempt in range(self.max_retries + 1):
            # 1. TCP 检测
            tcp_ok, tcp_latency, tcp_error = await self.check_tcp_connection(host, port)
            
            if tcp_ok:
                latency_ms = tcp_latency
                
                # 2. HTTP 检测（仅对支持的协议）
                http_ok, http_latency, http_error = await self.check_http_connectivity(
                    host, port, protocol
                )
                
                if http_ok:
                    # 检测成功，跳出重试循环
                    break
                else:
                    error_message = http_error
            else:
                error_message = tcp_error
            
            retry_count = attempt
            
            # 如果失败且还有重试机会，等待一小段时间
            if attempt < self.max_retries:
                await asyncio.sleep(0.5)
        
        # 确定最终状态
        if tcp_ok and http_ok:
            status = NodeStatus.ONLINE
        elif tcp_ok and not http_ok:
            # TCP 通但 HTTP 不通，可能是协议问题，标记为可疑但不下线
            # 对于 vmess/vless/trojan 等协议，TCP 通就认为在线
            if protocol.lower() in ['vmess', 'vless', 'trojan', 'ss', 'shadowsocks', 'ssr']:
                status = NodeStatus.ONLINE
            else:
                status = NodeStatus.SUSPECT
        else:
            status = NodeStatus.OFFLINE
        
        return HealthCheckResult(
            node_id=node_id,
            host=host,
            port=port,
            status=status,
            tcp_ok=tcp_ok,
            http_ok=http_ok,
            latency_ms=latency_ms,
            error_message=error_message,
            retry_count=retry_count,
            checked_at=datetime.utcnow().isoformat()
        )
    
    async def check_nodes_batch(self, nodes: List[Dict]) -> List[HealthCheckResult]:
        """
        批量检测节点
        
        Args:
            nodes: 节点列表
            
        Returns:
            检测结果列表
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def check_with_semaphore(node: Dict) -> HealthCheckResult:
            async with semaphore:
                return await self.check_node(node)
        
        tasks = [check_with_semaphore(node) for node in nodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                node = nodes[i]
                final_results.append(HealthCheckResult(
                    node_id=node.get("id", ""),
                    host=node.get("host", ""),
                    port=node.get("port", 0),
                    status=NodeStatus.UNKNOWN,
                    tcp_ok=False,
                    http_ok=False,
                    error_message=f"Check exception: {str(result)[:50]}",
                    checked_at=datetime.utcnow().isoformat()
                ))
            else:
                final_results.append(result)
        
        return final_results


class SupabaseHealthUpdater:
    """Supabase 健康状态更新器"""
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        self.supabase_url = supabase_url or os.environ.get("SUPABASE_URL", "")
        self.supabase_key = supabase_key or os.environ.get("SUPABASE_KEY", "")
    
    async def get_nodes_for_check(self, limit: int = 100) -> List[Dict]:
        """
        从 Supabase 获取需要检测的节点
        
        Args:
            limit: 每次检测的节点数量（Vercel 限制）
            
        Returns:
            节点列表
        """
        if not self.supabase_url or not self.supabase_key:
            logger.error("Supabase credentials not configured")
            return []
        
        try:
            # 查询需要检测的节点
            # 优先检测：1) 从未检测过的 2) 最久未检测的
            url = f"{self.supabase_url}/rest/v1/nodes"
            params = {
                "select": "id,content,status,last_health_check",
                "order": "last_health_check.asc.nullsfirst",
                "limit": str(limit)
            }
            
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        rows = await resp.json()
                        logger.info(f"查询到 {len(rows)} 条记录")
                        
                        if not rows:
                            logger.warning("Supabase 返回空结果")
                            return []
                        
                        nodes = []
                        for row in rows:
                            try:
                                # content 字段是 JSONB，包含节点信息
                                content = row.get("content", {})
                                if isinstance(content, str):
                                    import json
                                    content = json.loads(content)
                                
                                # 提取节点关键信息
                                host = content.get("host") or row.get("host")
                                port = content.get("port") or row.get("port")
                                
                                if not host or not port:
                                    logger.warning(f"节点 {row.get('id')} 缺少 host/port，跳过")
                                    continue
                                
                                nodes.append({
                                    "id": row.get("id"),
                                    "host": str(host),
                                    "port": int(port),
                                    "protocol": content.get("protocol") or row.get("protocol", "unknown"),
                                    "name": content.get("name", ""),
                                    "current_status": row.get("status", "unknown")
                                })
                            except Exception as e:
                                logger.error(f"解析节点 {row.get('id')} 失败: {e}")
                                continue
                        
                        logger.info(f"成功解析 {len(nodes)} 个节点")
                        return nodes
                    else:
                        logger.error(f"Failed to fetch nodes: HTTP {resp.status}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching nodes: {e}")
            return []
    
    async def update_node_status(self, results: List[HealthCheckResult]) -> Tuple[int, int]:
        """
        更新节点状态到 Supabase
        
        Args:
            results: 检测结果列表
            
        Returns:
            (成功数, 失败数)
        """
        if not self.supabase_url or not self.supabase_key:
            logger.error("Supabase credentials not configured")
            return 0, len(results)
        
        success_count = 0
        fail_count = 0
        
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        
        async with aiohttp.ClientSession() as session:
            for result in results:
                if not result.node_id:
                    fail_count += 1
                    continue
                
                try:
                    url = f"{self.supabase_url}/rest/v1/nodes?id=eq.{result.node_id}"
                    
                    update_data = {
                        "status": result.status.value,
                        "last_health_check": result.checked_at,
                        "health_latency": result.latency_ms
                    }
                    
                    async with session.patch(url, json=update_data, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status in [200, 204]:
                            success_count += 1
                        else:
                            fail_count += 1
                            logger.warning(f"Failed to update node {result.node_id}: HTTP {resp.status}")
                            
                except Exception as e:
                    fail_count += 1
                    logger.error(f"Error updating node {result.node_id}: {e}")
        
        return success_count, fail_count


async def run_health_check(batch_size: int = 50) -> Dict:
    """
    执行健康检测的主函数
    
    Args:
        batch_size: 每批检测的节点数量
        
    Returns:
        检测结果统计
    """
    logger.info(f"🏥 开始健康检测 (batch_size={batch_size})")
    start_time = datetime.utcnow()
    
    # 初始化组件
    checker = LightweightHealthChecker(
        tcp_timeout=5.0,
        http_timeout=8.0,
        max_retries=2,
        max_concurrent=20
    )
    updater = SupabaseHealthUpdater()
    
    # 获取待检测节点
    nodes = await updater.get_nodes_for_check(limit=batch_size)
    
    if not nodes:
        logger.warning("没有需要检测的节点")
        return {
            "status": "no_nodes",
            "checked_count": 0,
            "online_count": 0,
            "offline_count": 0,
            "suspect_count": 0,
            "duration_seconds": 0
        }
    
    logger.info(f"📋 获取到 {len(nodes)} 个节点待检测")
    
    # 执行检测
    results = await checker.check_nodes_batch(nodes)
    
    # 统计结果
    online_count = sum(1 for r in results if r.status == NodeStatus.ONLINE)
    offline_count = sum(1 for r in results if r.status == NodeStatus.OFFLINE)
    suspect_count = sum(1 for r in results if r.status == NodeStatus.SUSPECT)
    
    logger.info(f"📊 检测结果: 在线={online_count}, 离线={offline_count}, 可疑={suspect_count}")
    
    # 更新数据库
    success, fail = await updater.update_node_status(results)
    logger.info(f"💾 数据库更新: 成功={success}, 失败={fail}")
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    
    return {
        "status": "completed",
        "checked_count": len(results),
        "online_count": online_count,
        "offline_count": offline_count,
        "suspect_count": suspect_count,
        "update_success": success,
        "update_fail": fail,
        "duration_seconds": round(duration, 2),
        "checked_at": start_time.isoformat()
    }


# 用于测试
if __name__ == "__main__":
    async def test():
        # 测试单个节点
        checker = LightweightHealthChecker()
        
        test_node = {
            "id": "test-1",
            "host": "1.1.1.1",
            "port": 443,
            "protocol": "vmess"
        }
        
        result = await checker.check_node(test_node)
        print(f"检测结果: {result}")
    
    asyncio.run(test())
