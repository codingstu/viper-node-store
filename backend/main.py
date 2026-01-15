#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=== viper-node-store 后端主应用 ===

核心功能：
1. 从 Supabase 数据库读取节点数据
2. 提供节点查询和过滤 API
3. 提供同步信息查询
4. 支持用户自定义精确测速
5. 健康检测

数据来源：
- 所有节点数据存储在 Supabase public.nodes 表
- SpiderFlow 负责测速，结果直接写入 Supabase
- viper-node-store 仅读取和展示数据

架构：
- backend/config.py - 配置管理
- backend/core/ - 核心模块（日志、数据库）
- backend/api/ - API 路由
- backend/services/ - 业务逻辑
- backend/webhooks/ - Webhook 处理
"""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
import os
from datetime import datetime

# 导入配置和日志
from .config import config
from .core.logger import logger, setup_logger

# 导入路由
from .api.routes import router as api_router
from .webhooks.receiver import router as webhook_router

# 导入服务
from .services.node_service import NodeService

# ==================== 应用初始化 ====================

# 初始化日志
setup_logger()

app = FastAPI(
    title=config.API_TITLE,
    description=config.API_DESCRIPTION,
    version=config.API_VERSION
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
static_dir = os.path.dirname(os.path.dirname(__file__))
try:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
except Exception as e:
    logger.warning(f"⚠️  无法挂载静态文件: {e}")

# ==================== 路由注册 ====================

app.include_router(api_router)
app.include_router(webhook_router)

# ==================== 根路由 ====================

@app.get("/")
async def root():
    """根路由 - 返回 index.html 前端"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {
        "message": "viper-node-store API",
        "status": "running",
        "data_source": "Supabase",
        "version": config.API_VERSION
    }

@app.get("/index.html")
async def index_html():
    """直接访问 index.html"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path, media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="index.html not found")

# ==================== 定时任务 ====================

# 全局调度器实例
scheduler = None

async def periodic_pull_from_supabase():
    """
    定时拉取任务：每 12 分钟从 Supabase 拉取一次最新的节点数据
    这可以确保内存缓存保持最新
    """
    try:
        logger.info("📥 开始定时拉取 Supabase 节点数据...")
        node_service = NodeService()
        nodes = await node_service.get_nodes(limit=10000)
        logger.info(f"✅ 定时拉取完成：获取 {len(nodes)} 个节点")
    except Exception as e:
        logger.warning(f"⚠️  定时拉取失败: {e}")

# ==================== 应用生命周期 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    global scheduler
    
    logger.info("=" * 60)
    logger.info("🚀 viper-node-store 后端正在启动...")
    logger.info("📊 数据来源: Supabase public.nodes 表")
    logger.info("=" * 60)
    
    # 验证 Supabase 连接
    try:
        node_service = NodeService()
        nodes = await node_service.get_nodes(limit=1)
        logger.info("✅ Supabase 连接成功")
    except Exception as e:
        logger.warning(f"⚠️  Supabase 连接失败: {e}")
    
    # 启动定时任务调度器
    try:
        scheduler = AsyncIOScheduler()
        
        # 添加定时任务：每 12 分钟拉取一次 Supabase 数据
        scheduler.add_job(
            periodic_pull_from_supabase,
            'interval',
            minutes=config.SUPABASE_PULL_INTERVAL_MINUTES,
            id='supabase_pull',
            name='Supabase 定时拉取'
        )
        
        scheduler.start()
        logger.info(f"✅ 定时任务调度器已启动（每 {config.SUPABASE_PULL_INTERVAL_MINUTES} 分钟拉取一次 Supabase 数据）")
    except Exception as e:
        logger.warning(f"⚠️  启动定时任务调度器失败: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    global scheduler
    
    logger.info("🛑 viper-node-store 后端正在关闭...")
    
    # 关闭调度器
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("✅ 定时任务调度器已关闭")

# ==================== 主程序 ====================

if __name__ == "__main__":
    import uvicorn
    import sys
    
    logger.info("=" * 60)
    logger.info("启动 viper-node-store 后端服务")
    logger.info(f"监听地址: {config.HOST}:{config.PORT}")
    logger.info("=" * 60)
    
    # 支持两种启动方式：
    # 1. python -m backend.main
    # 2. python backend/main.py (需要在项目根目录)
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD,
        log_level=config.LOG_LEVEL.lower()
    )
