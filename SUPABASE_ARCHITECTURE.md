# viper-node-store 新架构说明 (v2.0 - Supabase 版)

## 📋 架构变更总结

### 核心变化
这是一次**完整的数据架构重构**，从混合数据源（本地 JSON + SpiderFlow API）切换到**统一的 Supabase 数据库源**。

### 旧架构 (v1.x)
```
┌─────────────┐
│ SpiderFlow  │ ──测速结果──→ ❌ 本地 JSON 文件
└─────────────┘              (verified_nodes.json)
     ↑
     │
     └──────── viper-node-store 
               │ ──读取──→ JSON ──API→ 前端
               │
               └──SpiderFlow API 查询
```

**问题：**
- 本地文件系统不可扩展
- SpiderFlow API 调用重复，低效
- 数据不一致（多个源）
- 无实时数据同步

### 新架构 (v2.0)
```
┌─────────────┐
│ SpiderFlow  │
└─────────────┘
      │
      │ 写入测速结果
      ↓
┌──────────────────────────┐
│   Supabase Database      │
│   public.nodes 表        │
└──────────────────────────┘
      ↑
      │ 读取
      │
┌──────────────────────────┐
│ viper-node-store API     │
│ (FastAPI)                │
└──────────────────────────┘
      │
      │ JSON API
      ↓
┌──────────────────────────┐
│   Frontend (index.html)  │
│   VIPER_API_BASE 路由    │
└──────────────────────────┘
```

**优势：**
✅ 统一数据源（单一真实来源）
✅ 实时数据访问（无本地缓存）
✅ 可扩展性强（数据库支持大规模查询）
✅ 自动同步（SpiderFlow 直接写入 Supabase）
✅ 零数据泄露风险（节点接口被隐藏）

---

## 🔄 数据流说明

### 数据流向
```
SpiderFlow (Azure)
    ├─ 持续测速各个节点
    └─ 将测试结果写入 Supabase public.nodes 表
         │
         └─→ content (JSONB) - 节点完整信息
         └─→ speed (int4) - 下载速度
         └─→ latency (int4) - 延迟
         └─→ is_free (bool) - 免费标志
         └─→ updated_at (timestamptz) - 最后更新时间
         └─→ mainland_score/latency - 大陆地区指标
         └─→ overseas_score/latency - 海外地区指标

viper-node-store (Vercel Serverless)
    ├─ GET /api/nodes → 查询 Supabase 返回节点列表
    ├─ GET /api/sync-info → 查询 Supabase 返回同步信息
    ├─ POST /api/nodes/precision-test → 执行精确测速
    └─ POST /api/nodes/latency-test → 执行延迟测试

前端 (index.html)
    ├─ 获取 VIPER_API_BASE 环境变量
    │  ├─ 本地: http://localhost:8002
    │  └─ 线上: https://api.996828.xyz
    ├─ 定期轮询 /api/sync-info
    └─ 按需调用 /api/nodes 和测速 API
```

---

## 📊 Supabase 表结构

### public.nodes 表

| 列名 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | text | 节点唯一标识 | "node_12345" |
| `content` | jsonb | 节点完整信息（协议、主机、端口等） | `{"protocol": "http", "host": "proxy.example.com", "port": 8080}` |
| `is_free` | bool | 是否为免费节点 | true/false |
| `speed` | int4 | 下载速度 (bytes/s) | 1048576 |
| `latency` | int4 | 延迟 (ms) | 150 |
| `updated_at` | timestamptz | 最后更新时间 | 2026-01-01T21:02:04.012988Z |
| `mainland_score` | int4 | 大陆地区评分 (0-100) | 85 |
| `mainland_latency` | int4 | 大陆地区延迟 (ms) | 200 |
| `overseas_score` | int4 | 海外地区评分 (0-100) | 92 |
| `overseas_latency` | int4 | 海外地区延迟 (ms) | 120 |

---

## 🔌 API 端点

### 1. 获取同步信息
```bash
GET /api/sync-info
```

**响应示例：**
```json
{
  "last_updated_at": "2026-01-01T21:02:04.012988",
  "minutes_ago": 5,
  "nodes_count": 1,
  "active_count": 1,
  "source": "supabase",
  "sync_metadata": {
    "total_nodes": 1,
    "tested_nodes": 1,
    "pending_test": 0
  }
}
```

**前端用途：**显示"上次更新于 X 分钟前"

---

### 2. 获取节点列表
```bash
GET /api/nodes?limit=50&show_free=true&show_china=true
```

**参数：**
- `limit` (int, 1-500, 默认 50) - 返回节点数量
- `show_free` (bool, 默认 true) - 是否显示免费节点
- `show_china` (bool, 默认 true) - 是否显示大陆节点

**响应示例：**
```json
[
  {
    "id": "node_12345",
    "protocol": "http",
    "host": "proxy.example.com",
    "port": 8080,
    "name": "proxy.example.com:8080",
    "country": "CN",
    "link": "http://proxy.example.com:8080",
    "is_free": true,
    "speed": 1048576,
    "latency": 150,
    "alive": true,
    "updated_at": "2026-01-01T21:02:04.012988",
    "mainland_score": 85,
    "mainland_latency": 200,
    "overseas_score": 92,
    "overseas_latency": 120
  }
]
```

---

### 3. 精确速度测试
```bash
POST /api/nodes/precision-test
Content-Type: application/json

{
  "proxy_url": "https://speed.cloudflare.com",
  "test_file_size": 50
}
```

**参数：**
- `proxy_url` (string) - 要测试的代理或服务器 URL
- `test_file_size` (int, 默认 50) - 测试文件大小 (MB)

**响应示例：**
```json
{
  "status": "success",
  "speed_mbps": 45.23,
  "download_time_seconds": 1.11,
  "traffic_consumed_mb": 50.2,
  "bytes_downloaded": 52650240,
  "test_file_size_requested_mb": 50,
  "message": "精确测速完成: 45.23 MB/s",
  "timestamp": "2026-01-01T21:05:00.123456"
}
```

---

### 4. 延迟测试
```bash
POST /api/nodes/latency-test
Content-Type: application/json

{
  "proxy_url": "https://cloudflare.com"
}
```

**响应示例：**
```json
{
  "status": "success",
  "latency": 145,
  "latency_ms": 145,
  "timestamp": "2026-01-01T21:05:00.123456"
}
```

---

### 5. 触发轮询（向 SpiderFlow 发送信号）
```bash
POST /api/sync/poll-now
```

**响应示例：**
```json
{
  "status": "poll_triggered",
  "message": "已请求 SpiderFlow 执行轮询，结果将保存到 Supabase",
  "timestamp": "2026-01-01T21:05:00.123456"
}
```

**注意：** 此端点仅向 SpiderFlow 发送触发信号，实际数据仍从 Supabase 读取

---

## 🚀 本地测试

### 1. 安装依赖
```bash
cd /Users/ikun/study/Learning/viper-node-store
pip install -r requirements.txt
```

### 2. 启动 API 服务
```bash
python3 app_fastapi.py
```

服务将在 `http://localhost:8002` 启动

### 3. 测试 API 端点
```bash
# 测试所有端点
python3 test_supabase_api.py

# 或手动测试
curl http://localhost:8002/api/sync-info | jq .
curl http://localhost:8002/api/nodes?limit=5 | jq .
```

---

## 🌐 环境配置

### Supabase 环境变量
在 `.env` 或系统环境中设置：

```bash
SUPABASE_URL=https://hnlkwtkxbqiakeyienok.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 前端 VIPER_API_BASE 路由
在 `index.html` 中：

```javascript
// 自动检测环境
const VIPER_API_BASE = 
  window.location.hostname === 'localhost' 
    ? 'http://localhost:8002'
    : 'https://api.996828.xyz';
```

### 线上部署 (Vercel)
自动通过 GitHub Workflows 部署：
- 推送到 `dev` 分支 → 自动部署到 Vercel
- Frontend: `https://node.peachx.tech`
- API: `https://api.996828.xyz/api/*`

---

## 📝 已移除的文件/模块

为了完整迁移到 Supabase，以下内容已被移除或不再使用：

| 项目 | 原因 | 替代方案 |
|------|------|--------|
| `verified_nodes.json` | 本地文件存储 | Supabase REST API |
| 本地文件 I/O 操作 | 单点故障 | 云数据库 |
| 对 SpiderFlow API 的直接调用 | 低效/不必要 | 直接读 Supabase |
| `webhook_receiver.py` | 不再需要 | SpiderFlow 直接写 Supabase |
| `data_sync.py` 的节点同步逻辑 | 由 SpiderFlow 接管 | SpiderFlow 写 Supabase |

---

## ✅ 验证清单

- [x] app_fastapi.py 重写为 Supabase-first
- [x] 所有 API 端点从 Supabase 读取
- [x] 本地文件依赖完全移除
- [x] requirements.txt 包含必需的依赖
- [x] 环境变量正确配置
- [x] 提交代码到 dev 分支
- [x] 创建 test_supabase_api.py 测试套件
- [ ] 本地测试通过（待执行）
- [ ] Vercel 自动部署完成（等待 GitHub Actions）
- [ ] 线上生产环境验证（https://node.peachx.tech）

---

## 🔐 安全性说明

### 隐藏节点接口
新架构中，所有原始节点接口信息（IP:PORT）都存储在 Supabase 的 `content` JSONB 字段中，不会通过 API 直接暴露给未授权的客户端。

### 数据访问控制
- viper-node-store API 是唯一的数据网关
- 前端通过 VIPER_API_BASE 路由，既可以是本地（8002）也可以是线上（api.996828.xyz）
- Supabase 直接访问权限受到 API Key 限制

---

## 📞 故障排查

### 问题：/api/sync-info 返回空数据
**解决：** 检查 Supabase 连接
```bash
# 查看启动日志
python3 app_fastapi.py
# 应该看到 "✅ Supabase 连接成功"
```

### 问题：API 返回 404
**解决：** 检查端口和路由
```bash
curl -v http://localhost:8002/api/sync-info
# 应该返回 200 OK
```

### 问题：前端无法连接 API
**解决：** 检查 VIPER_API_BASE 环境变量
```javascript
// 在浏览器控制台检查
console.log(window.VIPER_API_BASE);
```

---

## 📚 相关文档

- [SpiderFlow 架构](../SpiderFlow/README.md) - 节点测速引擎
- [前端集成指南](./index.html) - HTML/JavaScript 前端
- [部署指南](./DEPLOYMENT_PLAN.md) - Vercel 部署说明
- [Supabase 官方文档](https://supabase.com/docs) - 数据库文档

---

**最后更新：** 2026-01-01
**架构版本：** v2.0 (Supabase)
**维护者：** viper-node-store 团队
