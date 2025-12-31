#!/bin/bash

# Viper Node Store 前端启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 启动 Viper Node Store 前端服务..."
echo "📍 工作目录: $SCRIPT_DIR"

# 检查是否存在 Python HTTP 服务器运行
if ps aux | grep -E "python.*http.server|SimpleHTTPServer" | grep -v grep > /dev/null; then
    echo "⚠️  检测到已有前端服务在运行，先清理旧进程..."
    pkill -9 -f "python.*http.server\|SimpleHTTPServer" 2>/dev/null
    sleep 2
    echo "✅ 旧进程已清理"
fi

# 启动简单 HTTP 服务器（用于提供静态文件）
echo "⏳ 启动 HTTP 服务器..."
nohup python3 -m http.server 5174 --directory "$SCRIPT_DIR" > frontend.log 2>&1 &

# 保存进程ID
echo $! > frontend.pid

sleep 2

# 验证启动是否成功
if curl -s http://localhost:5174/index.html > /dev/null 2>&1; then
    echo "✅ 前端服务已启动！"
    echo "📍 前端页面: http://localhost:5174/index.html"
    echo ""
    echo "查看日志: tail -f frontend.log"
else
    echo "⚠️  服务启动中，查看日志:"
    tail -10 frontend.log
fi
