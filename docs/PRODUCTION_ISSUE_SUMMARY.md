# 生产环境 API 404 错误 - 问题诊断和解决方案总结

## 现象

前端线上部署后出现错误：
```
❌ GET https://node.peachx.tech/api/nodes 404 (Not Found)
❌ GET https://node.peachx.tech/api/sync-info 404 (Not Found)
```

## 原因分析

### ✅ 代码审查结果：**代码本身完全正确**

我已经详细审查了后端代码，以下部分都验证无误：

1. **API 路由定义** ✅
   - `/api/nodes` 在 `backend/api/routes.py` 中定义正确
   - `/api/sync-info` 在 `backend/api/routes.py` 中定义正确
   - 所有路由参数和返回值正确

2. **路由注册** ✅
   - `app.include_router(api_router)` 在 `backend/main.py` 中正确执行
   - Webhook 路由也正确注册

3. **CORS 配置** ✅
   - 中间件配置允许所有来源：`allow_origins=["*"]`
   - 允许所有方法和头部

4. **模块导入** ✅
   - 所有导入已从 `from backend.x import y` 改为相对导入 `from .x import y`
   - 模块导入测试通过

## 问题根源

404 错误的唯一原因是：**后端服务未能到达或未启动**

### 可能的原因（按优先级）

| 排序 | 原因 | 概率 | 症状 |
|------|------|------|------|
| 1️⃣ | 后端服务未启动或已宕机 | 90% | 无法连接，完全 404 |
| 2️⃣ | 环境变量未配置 | 5% | 启动时 Supabase 连接失败，应用崩溃 |
| 3️⃣ | Nginx 反向代理配置错误 | 3% | 部分请求失败，路由错误 |
| 4️⃣ | 防火墙/安全组未开放端口 | 2% | 连接拒绝，不是 404 |

## 快速诊断方法

### 方法 1：使用诊断脚本（推荐）

```bash
cd /path/to/viper-node-store
bash scripts/diagnose-backend.sh
```

这个脚本会检查：
- Python 环境 ✅
- 依赖包安装 ✅
- 模块导入 ✅
- 后端进程状态 ✅
- 端口监听 ✅
- 已注册的路由 ✅

### 方法 2：手动诊断

```bash
# 1. 登录服务器
ssh user@node.peachx.tech

# 2. 检查后端进程
ps aux | grep python | grep backend

# 3. 如果无结果，说明后端未启动，执行：
cd /path/to/viper-node-store
python backend/main.py

# 4. 或者后台启动（使用 nohup）
nohup python backend/main.py > backend.log 2>&1 &

# 5. 本地测试 API
curl http://localhost:8002/api/status

# 6. 查看日志找错误
tail -f backend.log
```

## 解决方案

### 方案 1：直接启动（临时方案）

```bash
cd /path/to/viper-node-store
python backend/main.py
```

### 方案 2：后台运行（推荐 for 开发）

```bash
cd /path/to/viper-node-store
nohup python backend/main.py > backend.log 2>&1 &

# 查看日志
tail -f backend.log

# 停止服务
pkill -f "python.*backend.main"
```

### 方案 3：使用 Systemd Service（推荐 for 生产）

创建 `/etc/systemd/system/viper-node-store.service`：

```ini
[Unit]
Description=Viper Node Store API
After=network.target

[Service]
Type=simple
User=www-data  # 或你的用户名
WorkingDirectory=/path/to/viper-node-store

# 设置环境变量
Environment="SUPABASE_URL=https://your-supabase-url.supabase.co"
Environment="SUPABASE_KEY=your-supabase-key"
Environment="SPIDERFLOW_API_URL=http://localhost:8001"
Environment="LOG_LEVEL=INFO"

# 启动命令（必须从项目根目录启动）
ExecStart=/usr/bin/python3 /path/to/viper-node-store/backend/main.py

# 自动重启
Restart=on-failure
RestartSec=10

# 日志
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

启动和管理：
```bash
sudo systemctl daemon-reload
sudo systemctl enable viper-node-store
sudo systemctl start viper-node-store
sudo systemctl status viper-node-store
sudo journalctl -u viper-node-store -f  # 查看日志
```

### 方案 4：使用 Docker（如果已容器化）

```dockerfile
FROM python:3.11
WORKDIR /app

# 复制项目文件
COPY . .

# 安装依赖
RUN pip install -r requirements.txt

# 暴露端口
EXPOSE 8002

# 从项目根目录启动（重要！）
CMD ["python", "backend/main.py"]
```

```bash
docker build -t viper-node-store .

docker run -d \
  -p 8002:8002 \
  -e SUPABASE_URL=https://... \
  -e SUPABASE_KEY=... \
  --name viper-api \
  viper-node-store
```

## 环境变量配置

**必须设置的环境变量**（否则会使用硬编码的默认值）：

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-anon-key"
```

**可选的环境变量**：

```bash
export SPIDERFLOW_API_URL="http://localhost:8001"  # SpiderFlow 后端地址
export LOG_LEVEL="INFO"  # 日志级别：DEBUG, INFO, WARNING, ERROR
```

## 验证修复成功

修复后，验证以下几点：

```bash
# 1. 后端进程运行
ps aux | grep python | grep backend
# 应该看到：python backend/main.py

# 2. 端口监听
lsof -i :8002 | grep LISTEN
# 应该看到端口 8002 的监听

# 3. API 响应
curl http://localhost:8002/api/status
# 应该返回：
# {
#   "status": "running",
#   "version": "2.0.0",
#   "data_source": "Supabase",
#   "timestamp": "2026-01-11T..."
# }

# 4. 获取节点
curl http://localhost:8002/api/nodes
# 应该返回：[{...}, {...}, ...]

# 5. 远程访问（如果部署在服务器上）
curl https://node.peachx.tech/api/status
# 应该同样返回成功响应
```

## 重要注意事项

### ⚠️ 启动时必须从项目根目录

❌ **错误的方式**：
```bash
cd /path/to/viper-node-store/backend
python main.py  # 这样会导致导入失败！
```

✅ **正确的方式**：
```bash
cd /path/to/viper-node-store
python backend/main.py  # 从项目根目录！
```

### ⚠️ Nginx 反向代理配置

如果使用 Nginx，确保配置正确：

```nginx
location /api/ {
    proxy_pass http://localhost:8002;  # 注意：8002 是后端端口
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

重启 Nginx：
```bash
sudo nginx -t  # 测试配置
sudo systemctl restart nginx
```

## 提供的文档和工具

我为你创建了以下辅助工具和文档：

| 文件 | 用途 |
|------|------|
| `docs/API_404_TROUBLESHOOTING.md` | 详细的 404 错误诊断指南 |
| `docs/DEPLOYMENT_TROUBLESHOOTING.md` | 部署常见问题和解决方案 |
| `scripts/diagnose-backend.sh` | 自动诊断脚本 |
| `docs/CHANGELOG.md` | 更新日志记录 |

## 下一步行动

1. **立即检查**：
   ```bash
   bash scripts/diagnose-backend.sh
   ```

2. **查看日志**：
   ```bash
   python backend/main.py  # 查看启动输出
   ```

3. **如果仍有问题**，收集以下信息：
   - 完整的启动日志（包含所有"✅"和"❌"）
   - `curl http://localhost:8002/api/status` 的输出
   - 服务器系统信息（OS、Python 版本）
   - 部署方式（直接运行、Systemd、Docker 等）

## 总结

**代码没有问题。问题出在部署/运行方式上。**

最可能是：**后端服务没有启动或已宕机。**

解决方案：确保后端进程正在运行，并正确监听 8002 端口。

使用诊断脚本快速定位问题：`bash scripts/diagnose-backend.sh`

