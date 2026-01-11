"""
后端配置管理
"""

import os
from typing import Optional

# ==================== 环境配置 ====================

class Config:
    """配置管理类"""
    
    # Supabase 配置
    SUPABASE_URL: str = os.environ.get(
        "SUPABASE_URL", 
        "https://hnlkwtkxbqiakeyienok.supabase.co"
    )
    SUPABASE_KEY: str = os.environ.get(
        "SUPABASE_KEY", 
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhubGt3dGt4YnFpYWtleWllbm9rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY5MDQwNTksImV4cCI6MjA4MjQ4MDA1OX0.Xg9vQdUfBdUW-IJaomEIRGsX6tB_k2grhrF4dm_aNME"
    )
    
    # FastAPI 配置
    API_TITLE: str = "viper-node-store API"
    API_DESCRIPTION: str = "节点数据管理和展示平台（数据来源: Supabase）"
    API_VERSION: str = "2.0.0"
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8002
    DEBUG: bool = False
    RELOAD: bool = False
    
    # SpiderFlow 后端配置
    SPIDERFLOW_API_URL: str = os.environ.get(
        "SPIDERFLOW_API_URL",
        "http://localhost:8001"
    )
    
    # 节点查询限制
    DEFAULT_NODE_LIMIT: int = 20
    MAX_NODE_LIMIT: int = 500
    VIP_NODE_LIMIT: int = 500
    
    # 定时任务配置
    SUPABASE_PULL_INTERVAL_MINUTES: int = 12
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "[%(asctime)s] %(levelname)s - %(message)s"
    LOG_DATE_FORMAT: str = "%H:%M:%S"


# ==================== 配置实例 ====================

config = Config()
