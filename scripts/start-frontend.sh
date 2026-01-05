#!/bin/bash

# Viper Node Store 前端启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

echo "🚀 启动 Viper Node Store 前端服务..."
echo "📍 前端工作目录: $ROOT_DIR/frontend"

# 清理可能残留的前端服务（http.server / vite / node）
if ps aux | grep -E "python.*http.server|SimpleHTTPServer|vite|npm run dev|node .*vite" | grep -v grep > /dev/null; then
    echo "⚠️  检测到已有前端相关进程，先清理旧进程..."
    pkill -9 -f "python.*http.server\|SimpleHTTPServer\|vite\|npm run dev\|node .*vite" 2>/dev/null || true
    sleep 1
    echo "✅ 旧进程尝试已清理"
fi

# 开发模式：使用 Vite 启动（后台运行）
echo "⏳ 在 frontend 目录启动 Vite 开发服务器 (npm run dev)..."
cd "$ROOT_DIR/frontend" || exit 1
nohup npm run dev > "$ROOT_DIR/frontend/frontend_dev.log" 2>&1 &
echo $! > "$ROOT_DIR/frontend/frontend_dev.pid"

sleep 2

# 验证启动是否成功（检查 vite 是否在监听常用端口）
if lsof -iTCP -sTCP:LISTEN -Pn | egrep ":5173|:5174" > /dev/null 2>&1; then
    echo "✅ 前端服务已启动（Vite）。"
    echo "📍 本地预览请查看 Vite 输出或访问 http://localhost:5173 或工具提示的端口"
    echo "查看日志: tail -f $ROOT_DIR/frontend/frontend_dev.log"
else
    echo "⚠️  前端可能尚未完全启动，查看日志以获取详细信息："
    tail -n 30 "$ROOT_DIR/frontend/frontend_dev.log" || true
fi
