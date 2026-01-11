"""
数据库连接和管理模块
"""

import aiohttp
from typing import List, Dict, Optional
from ..config import config
from .logger import logger

# ==================== Supabase 客户端 ====================

class SupabaseClient:
    """Supabase 异步客户端"""
    
    def __init__(self, url: str, key: str):
        """
        初始化 Supabase 客户端
        
        Args:
            url: Supabase URL
            key: Supabase API Key
        """
        self.url = url
        self.key = key
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
    
    async def query(
        self,
        table: str,
        select: str = "*",
        order: Optional[str] = None,
        limit: Optional[int] = None,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        查询数据
        
        Args:
            table: 表名
            select: 选择的列
            order: 排序条件
            limit: 限制行数
            filters: 过滤条件字典
        
        Returns:
            查询结果列表
        """
        try:
            # 构造 URL
            url = f"{self.url}/rest/v1/{table}?select={select}"
            
            # 添加排序条件
            if order:
                url += f"&order={order}"
            
            # 添加限制
            if limit:
                url += f"&limit={limit}"
            
            # 添加过滤条件
            if filters:
                for key, value in filters.items():
                    url += f"&{key}={value}"
            
            # 发起请求
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        logger.error(f"❌ Supabase 查询失败: {resp.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"❌ Supabase 查询异常: {e}")
            return []
    
    async def update(
        self,
        table: str,
        data: Dict,
        filters: Dict
    ) -> bool:
        """
        更新数据
        
        Args:
            table: 表名
            data: 更新数据字典
            filters: 过滤条件字典
        
        Returns:
            是否成功
        """
        try:
            # 构造 URL
            url = f"{self.url}/rest/v1/{table}"
            
            # 添加过滤条件
            for key, value in filters.items():
                url += f"?{key}=eq.{value}"
                break  # 仅支持第一个条件
            
            # 发起请求
            async with aiohttp.ClientSession() as session:
                async with session.patch(
                    url,
                    json=data,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    return resp.status in [200, 204]
                    
        except Exception as e:
            logger.error(f"❌ Supabase 更新异常: {e}")
            return False


# ==================== 全局客户端实例 ====================

db_client = SupabaseClient(config.SUPABASE_URL, config.SUPABASE_KEY)
