"""
认证服务 - 用户 VIP 状态和激活码管理
"""

import supabase
from datetime import datetime, timedelta
from typing import Optional, Dict

from ..config import config
from ..core.logger import logger

# ==================== 认证服务 ====================

class AuthService:
    """认证和授权业务逻辑"""
    
    async def check_user_admin_status(self, user_id: Optional[str]) -> bool:
        """
        检查用户是否是管理员
        
        Args:
            user_id: Supabase 用户 ID
        
        Returns:
            True 如果是管理员，False 如果不是
        """
        if not user_id:
            return False
        
        try:
            supabase_client = supabase.create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
            result = supabase_client.table("profiles").select("is_admin").eq("id", user_id).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0].get("is_admin", False) == True
            return False
            
        except Exception as e:
            logger.warning(f"⚠️  检查管理员状态失败: {e}")
            return False
    
    async def check_user_vip_status(self, user_id: Optional[str]) -> bool:
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
            supabase_client = supabase.create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
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
    
    async def redeem_activation_code(self, code: str, user_id: str) -> Dict:
        """
        兑换激活码升级到 VIP
        
        Args:
            code: 激活码
            user_id: 用户 ID
        
        Returns:
            兑换结果
        """
        try:
            if not code or not user_id:
                return {
                    "status": "error",
                    "message": "激活码和用户ID不能为空"
                }
            
            logger.info(f"🔑 兑换激活码: code={code}, user_id={user_id}")
            
            # 初始化 Supabase 客户端
            supabase_client = supabase.create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
            
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
                    pass
            
            # 获取 VIP 时长（天数）
            vip_days = code_record.get("vip_days", 30)
            
            # 计算 VIP 过期时间
            vip_until = datetime.utcnow() + timedelta(days=vip_days)
            
            # 更新用户的 vip_until 字段
            try:
                profiles_result = supabase_client.table("profiles").update({
                    "vip_until": vip_until.isoformat()
                }).eq("id", user_id).execute()
                
                if profiles_result.data:
                    logger.info(f"✅ 用户 VIP 状态已更新: {user_id}")
                else:
                    logger.warning(f"⚠️ 直接更新失败，尝试 upsert: {user_id}")
                    
                    # 使用 upsert
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
