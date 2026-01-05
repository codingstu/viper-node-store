# 快速参考：API 路由和数据流

## 🚀 快速启动（3个终端）

### 终端 1：SpiderFlow 后端
```bash
cd SpiderFlow/backend
python main.py
# 监听 http://localhost:8001
```

### 终端 2：viper-node-store 后端
```bash
cd viper-node-store
python app_fastapi.py
# 监听 http://localhost:8002
```

### 终端 3：立即同步数据到 Supabase（首次初始化）
```bash
cd SpiderFlow/backend
python trigger_supabase_sync.py
```

### 然后访问前端
```
http://localhost:8002/index.html
```

---

## 📍 API 端点映射表

### 前端请求的 API

| 功能 | 使用的基础 URL | 完整端点 | 来自后端 |
|------|-------------|---------|--------|
| **节点列表** | VIPER_API_BASE | `/api/nodes` | viper-node-store |
| **同步信息** | VIPER_API_BASE | `/api/sync-info` | viper-node-store |
| **精准测速** | VIPER_API_BASE | `/api/nodes/precision-test` | viper-node-store |
| **延迟测试** | VIPER_API_BASE | `/api/nodes/latency-test` | viper-node-store |
| **NET I/O** | SPIDERFLOW_API_BASE | `/api/system/stats` | SpiderFlow |
| **访客数** | SPIDERFLOW_API_BASE | `/api/visitors/stats` | SpiderFlow |
| **节点进度** | SPIDERFLOW_API_BASE | `/nodes/stats` | SpiderFlow |

---

## 🔑 关键代码片段

### 前端定义 API 基础 URL（index.html）
```javascript
const VIPER_API_BASE = window.location.hostname === 'localhost' 
    ? 'http://localhost:8002'
    : 'https://api.996828.xyz';

const SPIDERFLOW_API_BASE = window.location.hostname === 'localhost' 
    ? 'http://localhost:8001'
    : 'https://spiderflow.996828.xyz';
```

### 前端调用系统监控（index.html 中的 updateMonitorStats）
```javascript
// ✅ 正确：使用 SPIDERFLOW_API_BASE
const sysRes = await fetch(`${SPIDERFLOW_API_BASE}/api/system/stats`);
const visitRes = await fetch(`${SPIDERFLOW_API_BASE}/api/visitors/stats`);

// ❌ 错误：使用 VIPER_API_BASE（会 404）
const sysRes = await fetch(`${VIPER_API_BASE}/api/system/stats`);
```

### SpiderFlow 定时同步到 Supabase（每10分钟）
```python
scheduler.add_job(
    self._sync_to_supabase_task,
    'interval',
    minutes=10,
    id='supabase_sync'
)
```

### viper-node-store 定时从 Supabase 拉取（每12分钟）
```python
scheduler.add_job(
    periodic_pull_from_supabase,
    'interval',
    minutes=12,
    id='supabase_pull'
)
```

---

## ✅ 检查清单

运行以下命令验证所有组件都正确运行：

```bash
# 1. 检查 SpiderFlow 是否运行
curl -s http://localhost:8001/api/system/stats | jq '.network'
# 应该显示网络统计数据

# 2. 检查 viper-node-store 是否运行
curl -s http://localhost:8002/api/status | jq .
# 应该显示 status: running

# 3. 检查节点数据是否存在
curl -s http://localhost:8002/api/sync-info | jq .
# 应该显示 nodes_count > 0

# 4. 获取节点列表
curl -s http://localhost:8002/api/nodes?limit=3 | jq '.[0]'
# 应该显示节点信息

# 5. 检查 Supabase 连接
curl -s 'https://hnlkwtkxbqiakeyienok.supabase.co/rest/v1/nodes?select=count()' \
  -H 'apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' | jq .
# 应该显示节点总数
```

---

## 🐛 常见问题

### Q: 为什么节点列表是空的？
A: 运行 `python trigger_supabase_sync.py` 初始化数据库

### Q: NET I/O 显示 `--`？
A: 检查是否使用了 `SPIDERFLOW_API_BASE`（不是 `VIPER_API_BASE`）

### Q: 精准测速返回 404？
A: 确保使用 `VIPER_API_BASE`，viper-node-store 监听 8002 端口

### Q: 多久数据更新一次？
A: SpiderFlow 每 10 分钟同步一次到 Supabase，viper-node-store 每 12 分钟拉取一次

---

## 📊 三层架构

```
┌─────────────────────┐
│   前端界面          │ (index.html)
│  - 节点列表         │
│  - 系统监控         │
│  - 测速功能         │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌──────────────┐ ┌────────────────┐
│   Viper      │ │  SpiderFlow    │
│  (8002)      │ │    (8001)      │
│ 节点数据API  │ │ 系统监控API    │
└──────────┬───┘ └────────┬───────┘
           │              │
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │  Supabase    │
           │  数据库      │
           └──────────────┘
```

---

**文档更新于：2026-01-01**
**架构版本：v2.0 完整版**
