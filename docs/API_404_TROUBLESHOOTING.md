# 线上 API 404 错误 - 原因分析和修复方案

## 问题症状
- 前端请求 `GET https://node.peachx.tech/api/nodes` 返回 404
- 前端请求 `GET https://node.peachx.tech/api/sync-info` 返回 404

## 最可能的原因（按优先级）

### 1️⃣ **最可能：后端服务未启动或已宕机**

**症状**：
- API 完全无响应或返回 404
- 日志中看不到任何来自后端的记录

**解决方案**：

#### 检查进程
```bash
# 查看是否有后端进程在运行
ps aux | grep -i python | grep -i backend
ps aux | grep -i uvicorn

# 如果无结果，说明后端已宕机，需要重启
```

#### 启动后端
```bash
# 方式 1：开发模式（单进程）
cd /path/to/viper-node-store
python backend/main.py

# 方式 2：生产模式（多进程）
cd /path/to/viper-node-store
uvicorn backend.main:app --host 0.0.0.0 --port 8002 --workers 4 --log-level info

# 方式 3：使用启动脚本
bash scripts/start-backend.sh

# 方式 4：后台运行
nohup python backend/main.py > backend.log 2>&1 &
```

#### 验证启动成功
```bash
# 检查端口是否监听
lsof -i :8002
netstat -tuln | grep 8002

# 应该看到类似输出：
# tcp        0      0 0.0.0.0:8002            0.0.0.0:*               LISTEN
```

---

### 2️⃣ **可能：环境变量未配置**

**症状**：
- 后端启动但 Supabase 连接失败
- 日志显示：`⚠️  Supabase 连接失败`

**解决方案**：

在部署环境中设置环境变量：

```bash
# 如果使用 systemd service
sudo nano /etc/systemd/system/viper-node-store.service

# 添加以下内容：
[Service]
Environment="SUPABASE_URL=https://your-supabase-url.supabase.co"
Environment="SUPABASE_KEY=your-supabase-anon-key"
Environment="SPIDERFLOW_API_URL=http://your-spiderflow-server:8001"
Environment="LOG_LEVEL=INFO"

# 如果使用 Docker
docker run -e SUPABASE_URL=... -e SUPABASE_KEY=... ...

# 如果使用 shell 脚本启动
export SUPABASE_URL="https://..."
export SUPABASE_KEY="..."
python backend/main.py
```

---

### 3️⃣ **可能：导入路径错误（Python 模块问题）**

**症状**：
- 后端启动时出现 `ModuleNotFoundError` 或 `ImportError`
- 应用启动失败

**解决方案**：

确保从**项目根目录**启动：

```bash
# ✅ 正确
cd /path/to/viper-node-store
python backend/main.py

# ❌ 错误
cd /path/to/viper-node-store/backend
python main.py  # 这样会导致导入失败！
```

测试导入：
```bash
cd /path/to/viper-node-store
python -c "from backend.main import app; print('✅ Import successful')"
```

---

### 4️⃣ **可能：CORS 或反向代理配置问题**

**症状**：
- 浏览器显示 CORS 错误
- 或者前端无法连接到后端

**解决方案**：

#### 检查 CORS 配置

`backend/main.py` 中的 CORS 配置：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

这个配置已经很宽松了，应该没问题。

#### 检查反向代理配置

如果你使用 Nginx：

```nginx
# /etc/nginx/conf.d/viper-node-store.conf

server {
    listen 80;
    server_name node.peachx.tech;

    location / {
        # 反向代理到后端
        proxy_pass http://localhost:8002;
        proxy_http_version 1.1;
        
        # 重要：转发必要的 headers
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 关键：不要重写路径
        proxy_redirect off;
    }
}
```

重启 Nginx：
```bash
sudo nginx -t  # 测试配置
sudo systemctl restart nginx
```

---

## 完整的诊断步骤

### 步骤 1：验证后端运行状态

```bash
# 登录到部署服务器
ssh user@node.peachx.tech

# 检查进程
ps aux | grep python

# 如果没有后端进程，马上启动：
cd /path/to/viper-node-store
python backend/main.py &
```

### 步骤 2：测试本地 API

```bash
# 从服务器本地测试
curl http://localhost:8002/api/status

# 预期返回：
# {
#   "status": "running",
#   "version": "2.0.0",
#   "data_source": "Supabase",
#   "timestamp": "..."
# }
```

### 步骤 3：查看后端日志

```bash
# 查看完整的启动日志
python backend/main.py

# 或查看日志文件
tail -f backend.log
tail -f /var/log/viper-node-store.log

# 关键日志行：
# ✅ "Supabase 连接成功" → Supabase 配置正确
# ✅ "定时任务调度器已启动" → APScheduler 正常
# ❌ "Supabase 连接失败" → 检查环境变量
```

### 步骤 4：测试远程 API

```bash
# 从本地计算机测试
curl https://node.peachx.tech/api/status

# 预期返回同样的 JSON
```

### 步骤 5：检查网络连接

```bash
# 测试防火墙/安全组是否开放了 8002 端口
telnet node.peachx.tech 8002

# 或使用 nc
nc -zv node.peachx.tech 8002

# 预期输出：
# Connection to node.peachx.tech 8002 port [tcp/*] succeeded!
```

---

## 快速修复清单

- [ ] 1. 登录服务器：`ssh user@node.peachx.tech`
- [ ] 2. 检查后端进程：`ps aux | grep python`
- [ ] 3. 如果没有进程，启动后端：`python backend/main.py`
- [ ] 4. 查看启动日志，找错误信息
- [ ] 5. 本地测试 API：`curl http://localhost:8002/api/status`
- [ ] 6. 验证环境变量：`echo $SUPABASE_URL`
- [ ] 7. 检查 Nginx 配置（如果使用）：`sudo nginx -t`
- [ ] 8. 远程测试 API：`curl https://node.peachx.tech/api/status`

---

## 代码检查清单

✅ **已验证以下内容都正确：**

1. ✅ 路由定义在 `backend/api/routes.py` 中
   - `/api/nodes` ✅
   - `/api/sync-info` ✅
   - `/api/status` ✅

2. ✅ 路由已在 `backend/main.py` 中注册
   - `app.include_router(api_router)` ✅
   - `app.include_router(webhook_router)` ✅

3. ✅ CORS 中间件已配置允许所有来源
   - `allow_origins=["*"]` ✅

4. ✅ 相对导入已修复
   - 所有 `from backend.x import y` 已改为 `from .x import y` ✅

5. ✅ 启动脚本已更新
   - `scripts/start-backend.sh` 指向 `backend/main.py` ✅

**因此，代码本身没有问题，问题一定在部署环境或启动命令。**

---

## 推荐的生产部署方案

### 使用 Systemd Service

创建 `/etc/systemd/system/viper-node-store.service`：

```ini
[Unit]
Description=Viper Node Store API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/viper-node-store

Environment="SUPABASE_URL=https://your-supabase-url.supabase.co"
Environment="SUPABASE_KEY=your-supabase-key"
Environment="SPIDERFLOW_API_URL=http://localhost:8001"
Environment="LOG_LEVEL=INFO"

ExecStart=/usr/bin/python3 backend/main.py

Restart=on-failure
RestartSec=10

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
sudo systemctl logs -f viper-node-store  # 查看日志
```

---

## 联系支持

如果问题仍未解决，请收集以下信息：

1. 完整的后端启动日志（包含所有"✅"和"❌"的行）
2. `curl http://localhost:8002/api/status` 的输出
3. `ps aux | grep python` 的输出
4. 服务器操作系统和 Python 版本
5. 部署方式（直接运行、Systemd、Docker 等）
6. 前端浏览器 DevTools 的完整错误信息

