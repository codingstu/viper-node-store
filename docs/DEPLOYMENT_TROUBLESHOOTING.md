# Viper Node Store - 部署故障排查指南

## 常见问题：API 返回 404

### 症状
- 前端显示：`GET https://node.peachx.tech/api/nodes 404 (Not Found)`
- 前端显示：`GET https://node.peachx.tech/api/sync-info 404 (Not Found)`

### 排查步骤

#### 1. 确认后端服务是否运行

```bash
# 检查后端进程
ps aux | grep python | grep backend

# 检查端口是否监听
lsof -i :8002  # 或你部署的端口
netstat -tuln | grep 8002
```

**预期输出**: 看到 `uvicorn` 或 `python` 进程监听在 8002 端口

---

#### 2. 测试本地 API 连接

```bash
# 测试后端 API 是否响应
curl http://localhost:8002/api/status

# 预期响应
{
  "status": "running",
  "version": "2.0.0",
  "data_source": "Supabase",
  "timestamp": "2026-01-11T..."
}
```

---

#### 3. 检查环境变量配置

**在生产环境中，必须设置以下环境变量**：

```bash
# Supabase 配置（必需）
export SUPABASE_URL="https://your-supabase-url.supabase.co"
export SUPABASE_KEY="your-supabase-anon-key"

# 可选配置
export SPIDERFLOW_API_URL="http://your-spiderflow-server:8001"
export LOG_LEVEL="INFO"
```

**检查环境变量是否已设置**：
```bash
echo $SUPABASE_URL
echo $SUPABASE_KEY
```

---

#### 4. 检查 Python 导入问题

```bash
# 从项目根目录运行（重要！）
cd /path/to/viper-node-store

# 测试模块导入
python -c "from backend.config import config; print('✅ Config 导入成功')"
python -c "from backend.api.routes import router; print('✅ Routes 导入成功')"
python -c "import backend.main; print('✅ Main 导入成功')"
```

**常见导入错误**：
- `ModuleNotFoundError: No module named 'backend'` → 未从项目根目录运行
- `ImportError: cannot import name 'X'` → 检查 `__init__.py` 文件是否存在

---

#### 5. 检查后端日志

```bash
# 查看最近的日志
tail -f /var/log/viper-node-store.log  # 或你的日志文件路径

# 或在启动时直接查看输出
python backend/main.py
```

**关键日志项**：
- ✅ `✅ Supabase 连接成功` → Supabase 配置正确
- ❌ `⚠️  Supabase 连接失败` → 检查 SUPABASE_URL 和 SUPABASE_KEY
- ✅ `✅ 定时任务调度器已启动` → APScheduler 正常工作

---

#### 6. 检查 Supabase 连接

```bash
# 测试 Supabase 连接
python -c "
import asyncio
from backend.core.database import db_client

async def test():
    try:
        result = await db_client.query(
            'SELECT COUNT(*) as count FROM nodes'
        )
        print(f'✅ Supabase 连接成功, 节点数: {result}')
    except Exception as e:
        print(f'❌ Supabase 连接失败: {e}')

asyncio.run(test())
"
```

---

#### 7. 检查路由注册

在 `backend/main.py` 的启动后输出 FastAPI 路由：

```bash
python -c "
from backend.main import app
print('已注册的路由:')
for route in app.routes:
    print(f'  - {route.path} {route.methods if hasattr(route, \"methods\") else \"(static)\"}')"
```

**预期输出应包含**：
- `/api/nodes`
- `/api/sync-info`
- `/api/status`
- `/api/health-check`
等等

---

#### 8. 使用 curl 测试 API（跨域问题）

```bash
# 从另一个主机测试
curl -H "Origin: https://your-frontend-domain.com" \
     -H "Access-Control-Request-Method: GET" \
     -v http://backend-server:8002/api/nodes

# 应该返回 200 OK 和 CORS 头
# 头部应包含: Access-Control-Allow-Origin: *
```

---

### 常见原因和解决方案

| 问题 | 原因 | 解决方案 |
|------|------|--------|
| **404 Not Found** | 后端没启动或路由未注册 | 检查进程、查看日志、确保从项目根目录启动 |
| **500 Internal Server** | Supabase 连接失败或代码错误 | 检查环境变量、查看详细错误日志 |
| **CORS 错误** | 跨域请求被拦截 | 确认 CORS 中间件已配置（已在 main.py 中配置） |
| **超时 (504)** | Supabase 响应慢或网络问题 | 检查网络连接、Supabase 服务状态 |

---

### 完整的启动命令（推荐）

```bash
# 方式 1：直接运行（开发）
cd /path/to/viper-node-store
python backend/main.py

# 方式 2：使用 uvicorn（生产）
cd /path/to/viper-node-store
uvicorn backend.main:app --host 0.0.0.0 --port 8002 --workers 4

# 方式 3：使用启动脚本
cd /path/to/viper-node-store
bash scripts/start-backend.sh

# 方式 4：在后台运行（Linux/Mac）
cd /path/to/viper-node-store
nohup python backend/main.py > backend.log 2>&1 &
```

---

### 部署检查清单

- [ ] 后端服务已启动且端口正确监听
- [ ] `SUPABASE_URL` 和 `SUPABASE_KEY` 环境变量已设置
- [ ] Supabase 连接测试成功 (`✅ Supabase 连接成功`)
- [ ] 路由已正确注册 (`/api/nodes`, `/api/sync-info` 等)
- [ ] 后端日志中无严重错误
- [ ] CORS 配置允许前端域名
- [ ] 防火墙/安全组允许后端端口访问
- [ ] 前端 API 请求地址正确指向后端服务器

---

### 进阶调试

#### 启用详细日志

```bash
# 在启动时设置日志级别
LOG_LEVEL=DEBUG python backend/main.py
```

#### 添加临时调试端点

在 `backend/api/routes.py` 中添加：

```python
@router.get("/api/debug/routes")
async def debug_routes():
    """调试：列出所有注册的路由"""
    routes = []
    from backend.main import app
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append({
                'path': route.path,
                'methods': list(route.methods) if hasattr(route, 'methods') else [],
                'name': route.name
            })
    return {"routes": routes}
```

然后访问：`http://backend-server:8002/api/debug/routes`

---

### 联系支持

如果以上步骤都不能解决问题，请收集以下信息：

1. 后端启动日志（完整输出）
2. `curl http://localhost:8002/api/status` 的输出
3. 错误截图（包括浏览器 DevTools）
4. 系统信息（OS、Python 版本、部署方式）

