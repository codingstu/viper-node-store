#!/bin/bash

# Viper Node Store 一键启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🎯 Viper Node Store 一键启动"
echo "================================"
echo ""

# 启动后端
echo "1️⃣  启动后端服务 (Python Proxy Server)..."
bash start-backend.sh

if [ $? -ne 0 ]; then
    echo "❌ 后端启动失败！"
    exit 1
fi

echo ""
echo "2️⃣  启动前端服务 (HTTP Server)..."
bash start-frontend.sh

if [ $? -ne 0 ]; then
    echo "⚠️  前端启动可能有问题"
fi

echo ""
echo "================================"
echo "✅ 两项服务已启动！"
echo "================================"
echo ""
echo "📍 前端页面: http://localhost:5173/index.html"
echo "📍 后端 API: http://localhost:8080/api/nodes"
echo ""
echo "停止服务: bash stop-all.sh"
echo ""
