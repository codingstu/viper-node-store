#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
viper-node-store 后端启动脚本（项目根目录版本）
支持从项目根目录直接运行后端服务
"""

import sys
import os

# 确保项目根目录在 Python 路径中
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

if __name__ == "__main__":
    # 启动后端（使用模块导入方式）
    from backend.main import app, config, logger
    import uvicorn
    
    logger.info("=" * 60)
    logger.info("启动 viper-node-store 后端服务")
    logger.info(f"监听地址: {config.HOST}:{config.PORT}")
    logger.info("=" * 60)
    
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD,
        log_level=config.LOG_LEVEL.lower()
    )
