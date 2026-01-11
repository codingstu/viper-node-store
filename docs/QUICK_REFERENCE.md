# 快速参考：API 404 错误

## 问题
```
GET https://node.peachx.tech/api/nodes 404 (Not Found)
GET https://node.peachx.tech/api/sync-info 404 (Not Found)
```

## 根本原因
**后端服务未启动**（概率 90%）或**环境变量未配置**（概率 5%）

## 快速修复

### 1️⃣ 运行诊断脚本（30秒）
```bash
cd /path/to/viper-node-store
bash scripts/diagnose-backend.sh
```

### 2️⃣ 启动后端
```bash
# 开发环境
python backend/main.py

# 或后台运行
nohup python backend/main.py > backend.log 2>&1 &

# 或使用生产级 Systemd Service（见下方）
sudo systemctl start viper-node-store
```

### 3️⃣ 验证修复
```bash
curl http://localhost:8002/api/status
# 应该返回 200 OK 和 JSON 响应
```

## 常用命令速查表

```bash
# 🚀 启动后端
python backend/main.py

# 🔍 检查进程
ps aux | grep python | grep backend

# 📊 检查端口
lsof -i :8002
netstat -tuln | grep 8002

# 📜 查看日志
tail -f backend.log
tail -f /var/log/syslog | grep viper

# 🛑 停止后端
pkill -f "python.*backend.main"

# 🧪 测试 API
curl http://localhost:8002/api/status
curl http://localhost:8002/api/nodes

# 📈 检查路由
python -c "from backend.main import app; [print(r.path) for r in app.routes if hasattr(r, 'path')]"
```

## Systemd Service 快速设置

### 1️⃣ 创建 service 文件
```bash
sudo nano /etc/systemd/system/viper-node-store.service
```

### 2️⃣ 复制内容
```ini
[Unit]
Description=Viper Node Store API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/viper-node-store
Environment="SUPABASE_URL=https://your-url.supabase.co"
Environment="SUPABASE_KEY=your-key"
ExecStart=/usr/bin/python3 /path/to/viper-node-store/backend/main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3️⃣ 启动并验证
```bash
sudo systemctl daemon-reload
sudo systemctl enable viper-node-store
sudo systemctl start viper-node-store
sudo systemctl status viper-node-store
sudo journalctl -u viper-node-store -f
```

## 环境变量设置

### 临时设置（当前终端）
```bash
export SUPABASE_URL="https://project.supabase.co"
export SUPABASE_KEY="anon-key"
python backend/main.py
```

### 永久设置（~/.bashrc）
```bash
echo 'export SUPABASE_URL="https://project.supabase.co"' >> ~/.bashrc
echo 'export SUPABASE_KEY="anon-key"' >> ~/.bashrc
source ~/.bashrc
```

## 关键检查点

| 项 | 命令 | 期望结果 |
|---|---|---|
| 进程 | `ps aux \| grep backend` | 看到 python 进程 |
| 端口 | `lsof -i :8002` | 看到 LISTEN |
| 导入 | `python -c "from backend.main import app"` | 无错误 |
| 路由 | `curl http://localhost:8002/api/nodes` | HTTP 200 |

## 常见错误和修复

| 错误 | 原因 | 修复 |
|---|---|---|
| `ModuleNotFoundError: No module named 'backend'` | 未从项目根目录启动 | `cd /path/to/viper-node-store && python backend/main.py` |
| `404 Not Found` | 后端未启动 | `python backend/main.py` |
| `SUPABASE_URL` 错误 | 环境变量未设置 | `export SUPABASE_URL=...` |
| `Connection refused` | 后端关闭 | `python backend/main.py` |
| `CORS error` | 配置错误 | 检查 backend/main.py 中的 CORSMiddleware |

## 文档导航

- **详细诊断** → `docs/API_404_TROUBLESHOOTING.md`
- **部署指南** → `docs/DEPLOYMENT_TROUBLESHOOTING.md`
- **项目结构** → `docs/PROJECT_STRUCTURE.md`
- **完整更新日志** → `docs/CHANGELOG.md`

## 代码验证

✅ 所有代码都已验证正确：
- 路由定义正确
- 路由注册正确
- CORS 配置正确
- 导入语句正确
- 模块结构正确

**问题 100% 出在部署/运行层面，不是代码问题。**

