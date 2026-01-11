#!/bin/bash

# Viper Node Store 后端启动脚本 (FastAPI)
# 启动新的模块化后端结构（backend/main.py）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

echo "🚀 启动 Viper Node Store FastAPI 后端服务..."
echo "📍 工作目录: $ROOT_DIR"
echo "📌 服务地址: http://localhost:8002"
echo "📦 运行文件: backend/main.py (模块化架构)"

# 检查依赖
if [ ! -f "requirements.txt" ]; then
    echo "❌ 未找到 requirements.txt"
    exit 1
fi

# 检查后端文件夹是否存在
if [ ! -d "backend" ]; then
    echo "❌ 未找到 backend 文件夹，请确保项目结构正确"
    exit 1
fi

# 检查是否已有进程运行（旧版本）
if ps aux | grep -E "python.*app_fastapi.py" | grep -v grep > /dev/null; then
    echo "⚠️  检测到旧版本后端服务在运行，先清理..."
    pkill -9 -f "python.*app_fastapi.py" 2>/dev/null
    sleep 2
    echo "✅ 旧进程已清理"
fi

# 检查是否已有新版本进程运行
if ps aux | grep -E "python.*backend/main.py" | grep -v grep > /dev/null; then
    echo "⚠️  检测到后端服务已在运行，先清理..."
    pkill -9 -f "python.*backend/main.py" 2>/dev/null
    sleep 2
    echo "✅ 旧进程已清理"
fi

# 启动后端 - 使用新的模块化结构
echo "✅ 启动 FastAPI 服务..."
python3 backend/main.py

sleep 3

# 验证启动是否成功
if curl -s http://localhost:8002/api/status > /dev/null 2>&1; then
    echo "✅ 后端服务已启动！"
    echo "📍 API 地址: http://localhost:8002/api/nodes"
    echo ""
    echo "可用 API 端点："
    echo "  - GET  /api/nodes              获取节点列表"
    echo "  - GET  /api/sync-info          获取同步信息"
    echo "  - POST /api/health-check       手动触发健康检测"
    echo ""
else
    echo "⚠️  等待服务完全启动..."
    sleep 2
    if curl -s http://localhost:8002/api/status > /dev/null 2>&1; then
        echo "✅ 后端服务已启动！"
        echo "📍 API 地址: http://localhost:8002/api/nodes"
    else
        echo "❌ 后端服务启动失败，请检查输出"
        exit 1
    fi
fi
