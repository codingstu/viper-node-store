#!/bin/bash

# Viper Node Store 停止脚本

echo "🛑 停止 Viper Node Store 服务..."

# 停止后端
echo "停止后端服务..."
pkill -9 -f "python.*app.py" 2>/dev/null

# 停止前端
echo "停止前端服务..."
pkill -9 -f "python.*http.server" 2>/dev/null

sleep 1
echo "✅ 所有服务已停止"
