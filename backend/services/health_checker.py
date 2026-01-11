"""
健康检测模块 - 复制自 health_checker.py
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
        """初始化检测器"""
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
        """TCP 连接测试"""
        try:
            start_time = asyncio.get_event_loop().time()
            future = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(future, timeout=self.tcp_timeout)
            latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
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
        """HTTP 连通性测试"""
        if protocol.lower() not in ['http', 'https', 'socks5', 'socks']:
            return True, 0, None
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            if protocol.lower() in ['http', 'https']:
                test_url = f"{protocol}://{host}:{port}/"
            else:
                return True, 0, None
            
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    test_url,
                    timeout=aiohttp.ClientTimeout(total=self.http_timeout),
                    allow_redirects=False,
                    ssl=False
                ) as resp:
                    latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                    return True, latency_ms, None
        except asyncio.TimeoutError:
            return False, None, "HTTP timeout"
        except aiohttp.ClientError as e:
            return False, None, f"HTTP error: {str(e)[:50]}"
        except Exception as e:
            return False, None, f"HTTP error: {str(e)[:50]}"
    
    async def check_node(self, node: Dict) -> HealthCheckResult:
        """检测单个节点"""
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
        
        tcp_ok = False
        http_ok = False
        latency_ms = None
        error_message = None
        retry_count = 0
        
        for attempt in range(self.max_retries + 1):
            tcp_ok, tcp_latency, tcp_error = await self.check_tcp_connection(host, port)
            
            if tcp_ok:
                latency_ms = tcp_latency
                http_ok, http_latency, http_error = await self.check_http_connectivity(
                    host, port, protocol
                )
                
                if http_ok:
                    break
                else:
                    error_message = http_error
            else:
                error_message = tcp_error
            
            retry_count = attempt
            
            if attempt < self.max_retries:
                await asyncio.sleep(0.5)
        
        if tcp_ok and http_ok:
            status = NodeStatus.ONLINE
        elif tcp_ok and not http_ok:
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
        """批量检测节点"""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def check_with_semaphore(node: Dict) -> HealthCheckResult:
            async with semaphore:
                return await self.check_node(node)
        
        tasks = [check_with_semaphore(node) for node in nodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
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
    
    async def update_node_status(self, results: List[HealthCheckResult]) -> Tuple[int, int]:
        """更新节点状态到 Supabase"""
        if not self.supabase_url or not self.supabase_key:
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
                            
                except Exception as e:
                    fail_count += 1
        
        return success_count, fail_count
