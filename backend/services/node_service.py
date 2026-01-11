"""
节点管理服务
"""

import aiohttp
import json
from typing import List, Dict, Optional
from datetime import datetime

from ..config import config
from ..core.logger import logger
from ..core.database import db_client

# ==================== 节点服务 ====================

class NodeService:
    """节点管理业务逻辑"""
    
    async def get_nodes(
        self,
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
            url = f"{config.SUPABASE_URL}/rest/v1/nodes?select=*&limit={limit}"
            
            # 添加过滤条件
            if not show_free:
                url += "&is_free=eq.false"
            
            headers = {
                "apikey": config.SUPABASE_KEY,
                "Authorization": f"Bearer {config.SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
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
                                    "link": row.get("link", "") or node_content.get("link", ""),
                                    "is_free": row.get("is_free", False),
                                    "speed": row.get("speed", 0),
                                    "latency": row.get("latency", 9999),
                                    "updated_at": row.get("updated_at"),
                                    "mainland_score": row.get("mainland_score", 0),
                                    "mainland_latency": row.get("mainland_latency", 9999),
                                    "overseas_score": row.get("overseas_score", 0),
                                    "overseas_latency": row.get("overseas_latency", 9999),
                                    "status": row.get("status", "online"),
                                    "last_health_check": row.get("last_health_check"),
                                    "health_latency": row.get("health_latency"),
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
    
    async def get_sync_info(self) -> Dict:
        """
        获取同步信息
        
        Returns:
            包含同步信息的字典
        """
        try:
            # 获取所有节点统计
            nodes = await self.get_nodes(limit=10000)
            
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
            logger.error(f"❌ 获取同步信息失败: {e}")
            return {
                "last_updated_at": datetime.now().isoformat(),
                "minutes_ago": 0,
                "nodes_count": 0,
                "active_count": 0,
                "source": "error",
                "error": str(e)
            }
    
    async def health_check_nodes(self, nodes: List[Dict]) -> Dict:
        """
        执行节点健康检测
        
        Args:
            nodes: 要检测的节点列表
        
        Returns:
            检测结果统计
        """
        try:
            from .health_checker import LightweightHealthChecker, SupabaseHealthUpdater
            from .health_checker import NodeStatus
            
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
            
            # 统计结果
            online_count = sum(1 for r in results if r.status == NodeStatus.ONLINE)
            offline_count = sum(1 for r in results if r.status == NodeStatus.OFFLINE)
            suspect_count = sum(1 for r in results if r.status == NodeStatus.SUSPECT)
            
            logger.info(f"📊 检测结果: 在线={online_count}, 离线={offline_count}, 可疑={suspect_count}")
            
            # 更新数据库
            logger.info("💾 更新数据库...")
            updater = SupabaseHealthUpdater(
                supabase_url=config.SUPABASE_URL,
                supabase_key=config.SUPABASE_KEY
            )
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
                "status": "completed",
                "total": len(results),
                "online": online_count,
                "offline": offline_count,
                "suspect": suspect_count,
                "problem_nodes": problem_nodes,
                "update_success": success,
                "update_fail": fail
            }
            
        except ImportError as e:
            logger.error(f"❌ 健康检测模块导入失败: {e}")
            return {
                "status": "error",
                "message": "健康检测模块未安装"
            }
        except Exception as e:
            logger.error(f"❌ 健康检测失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def get_health_check_stats(self) -> Dict:
        """
        获取健康检测统计数据
        
        Returns:
            统计信息字典
        """
        try:
            url = f"{config.SUPABASE_URL}/rest/v1/nodes?select=status"
            
            headers = {
                "apikey": config.SUPABASE_KEY,
                "Authorization": f"Bearer {config.SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
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
                        
                        return stats
                    else:
                        logger.error(f"查询失败: HTTP {resp.status}")
                        return {}
                        
        except Exception as e:
            logger.error(f"❌ 获取健康统计失败: {e}")
            return {}
