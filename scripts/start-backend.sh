#!/bin/bash

# Viper Node Store 后端启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 启动 Viper Node Store 后端服务..."
echo "📍 工作目录: $SCRIPT_DIR"

# 检查依赖
if [ ! -f "requirements.txt" ]; then
    echo "❌ 未找到 requirements.txt"
    exit 1
fi

# 检查是否已有进程运行
if ps aux | grep -E "python.*app.py" | grep -v grep > /dev/null; then
    echo "⚠️  检测到已有后端服务在运行，先清理旧进程..."
    pkill -9 -f "python.*app.py" 2>/dev/null
    sleep 2
    echo "✅ 旧进程已清理"
fi

# 启动后端
nohup python3 app.py > backend.log 2>&1 &

# 保存进程ID
echo $! > backend.pid

sleep 3

# 验证启动是否成功
if curl -s http://localhost:8080/api/nodes > /dev/null 2>&1; then
    echo "✅ 后端服务已启动！"
    echo "📍 API 地址: http://localhost:8080/api/nodes"
    echo ""
    echo "查看日志: tail -f backend.log"
else
    echo "⚠️  等待服务完全启动，检查日志..."
    sleep 2
    if curl -s http://localhost:8080/api/nodes > /dev/null 2>&1; then
        echo "✅ 后端服务已启动！"
        echo "📍 API 地址: http://localhost:8080/api/nodes"
    else
        echo "⚠️  服务可能启动中，查看日志:"
        tail -20 backend.log
    fi
fi
