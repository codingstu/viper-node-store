"""
API 数据模型定义
"""

from pydantic import BaseModel
from typing import Optional

# ==================== 请求模型 ====================

class PrecisionTestRequest(BaseModel):
    """精确测速请求模型"""
    proxy_url: str
    test_file_size: int = 50


class LatencyTestRequest(BaseModel):
    """延迟测试请求模型"""
    proxy_url: str


class HealthCheckRequest(BaseModel):
    """健康检测请求模型"""
    batch_size: int = 50


class RedeemCodeRequest(BaseModel):
    """激活码兑换请求"""
    code: str
    user_id: str


# ==================== 响应模型 ====================

class NodeData(BaseModel):
    """节点数据模型"""
    id: str
    protocol: str
    host: str
    port: int
    name: str
    country: str
    link: str
    is_free: bool
    speed: int
    latency: int
    updated_at: Optional[str]
    mainland_score: int
    mainland_latency: int
    overseas_score: int
    overseas_latency: int
    status: str
    last_health_check: Optional[str]
    health_latency: Optional[int]
    alive: bool


class SyncInfo(BaseModel):
    """同步信息模型"""
    last_updated_at: str
    minutes_ago: int
    nodes_count: int
    active_count: int
    source: str
