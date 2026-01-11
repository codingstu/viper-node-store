#!/bin/bash

# Viper Node Store 后端诊断脚本
# 用途：快速诊断后端是否正常运行

set -e

echo "================================"
echo "Viper Node Store 后端诊断工具"
echo "================================"
echo

# 1. 检查是否在项目根目录
echo "📁 检查目录..."
if [ ! -f "backend/main.py" ]; then
    echo "❌ 错误：未找到 backend/main.py"
    echo "   请确保在项目根目录运行此脚本"
    exit 1
fi
echo "✅ 目录正确"
echo

# 2. 检查 Python
echo "🐍 检查 Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 Python 3"
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python $PYTHON_VERSION"
echo

# 3. 检查依赖
echo "📦 检查依赖..."
python3 -c "import fastapi; print('✅ fastapi')" 2>/dev/null || echo "❌ fastapi 未安装"
python3 -c "import uvicorn; print('✅ uvicorn')" 2>/dev/null || echo "❌ uvicorn 未安装"
python3 -c "import aiohttp; print('✅ aiohttp')" 2>/dev/null || echo "❌ aiohttp 未安装"
python3 -c "import pydantic; print('✅ pydantic')" 2>/dev/null || echo "❌ pydantic 未安装"
python3 -c "import apscheduler; print('✅ apscheduler')" 2>/dev/null || echo "❌ apscheduler 未安装"
echo

# 4. 测试导入
echo "🔗 测试模块导入..."
python3 -c "
import sys
try:
    from backend.config import config
    print('✅ backend.config')
except Exception as e:
    print(f'❌ backend.config: {e}')
    sys.exit(1)

try:
    from backend.core.logger import setup_logger
    print('✅ backend.core.logger')
except Exception as e:
    print(f'❌ backend.core.logger: {e}')
    sys.exit(1)

try:
    from backend.api.routes import router
    print('✅ backend.api.routes')
except Exception as e:
    print(f'❌ backend.api.routes: {e}')
    sys.exit(1)

try:
    from backend.main import app
    print('✅ backend.main')
except Exception as e:
    print(f'❌ backend.main: {e}')
    sys.exit(1)
" || exit 1
echo

# 5. 检查环境变量
echo "🌍 检查环境变量..."
if [ -z "$SUPABASE_URL" ]; then
    echo "⚠️  SUPABASE_URL 未设置（使用默认值）"
else
    echo "✅ SUPABASE_URL 已设置"
fi

if [ -z "$SUPABASE_KEY" ]; then
    echo "⚠️  SUPABASE_KEY 未设置（使用默认值）"
else
    echo "✅ SUPABASE_KEY 已设置"
fi
echo

# 6. 检查后端进程
echo "⚙️  检查后端进程..."
if pgrep -f "python.*backend.main" > /dev/null; then
    echo "✅ 后端进程正在运行"
    pgrep -f "python.*backend.main" -l | head -1
else
    echo "❌ 后端进程未运行"
fi
echo

# 7. 检查端口
echo "🔌 检查端口监听..."
if command -v lsof &> /dev/null; then
    if lsof -i :8002 > /dev/null 2>&1; then
        echo "✅ 端口 8002 正在监听"
        lsof -i :8002 | grep LISTEN
    else
        echo "❌ 端口 8002 未监听"
    fi
elif command -v netstat &> /dev/null; then
    if netstat -tuln | grep 8002 > /dev/null 2>&1; then
        echo "✅ 端口 8002 正在监听"
    else
        echo "❌ 端口 8002 未监听"
    fi
else
    echo "⚠️  无法检查端口（lsof 和 netstat 都不可用）"
fi
echo

# 8. 列出已注册的路由
echo "📋 已注册的路由..."
python3 -c "
from backend.main import app
routes = []
for route in app.routes:
    if hasattr(route, 'path'):
        methods = list(route.methods) if hasattr(route, 'methods') else []
        routes.append((route.path, methods))

# 只显示 /api 开头的路由
api_routes = [(p, m) for p, m in routes if p.startswith('/api')]
if api_routes:
    for path, methods in sorted(api_routes):
        print(f'  ✅ {path} {methods}')
else:
    print('  ❌ 未找到 /api 路由')
"
echo

# 9. 总结
echo "================================"
echo "诊断完成！"
echo "================================"
echo

echo "🔗 快速测试命令："
echo "  # 启动后端"
echo "  python backend/main.py"
echo
echo "  # 测试 API（在另一个终端）"
echo "  curl http://localhost:8002/api/status"
echo "  curl http://localhost:8002/api/nodes"
echo

echo "📖 更多帮助："
echo "  • docs/API_404_TROUBLESHOOTING.md - API 404 错误诊断"
echo "  • docs/DEPLOYMENT_TROUBLESHOOTING.md - 部署问题排查"
echo "  • docs/PROJECT_STRUCTURE.md - 项目架构"
