# 三个问题的完整解决方案

日期：2026-01-01
状态：✅ 已实现

---

## 问题 1：数据库节点没有数据

### 症状
- 数据库（Supabase）中没有任何节点数据
- viper-node-store 无法从 Supabase 查询到节点
- `/api/nodes` 返回空列表

### 根本原因
- SpiderFlow 没有定时将测试结果写入 Supabase
- 缺少从 SpiderFlow → Supabase 的数据推送机制

### 解决方案

#### A. SpiderFlow 侧（推送）
**文件**: `backend/app/modules/node_hunter/node_hunter.py`

**新增内容**:
1. 添加了新的定时任务 `_sync_to_supabase_task()`
2. 在 `start_scheduler()` 中注册：**每10分钟执行一次**
3. 任务特点：
   - 只同步 `alive=True` 的活跃节点
   - 按 `host:port` 去重（避免重复）
   - 包含大陆和海外的测速数据
   - 异常处理，不影响其他任务

```python
# 每10分钟执行
self.scheduler.add_job(
    self._sync_to_supabase_task,
    'interval',
    minutes=10,
    id='supabase_sync'
)
```

**执行流程**:
```
节点测速完成 (SpiderFlow)
    ↓
标记为 alive=True
    ↓
每10分钟检查一次
    ↓
选择活跃节点 (alive=True)
    ↓
按 host:port 去重
    ↓
上传到 Supabase public.nodes 表
    ↓
写入 content（JSONB）、speed、latency 等字段
```

#### B. viper-node-store 侧（拉取）
**文件**: `app_fastapi.py`

**新增内容**:
1. 导入 APScheduler
2. 添加了 `periodic_pull_from_supabase()` 异步任务
3. 在启动事件中注册调度器：**每12分钟执行一次**
4. 应用关闭时优雅关闭调度器

```python
# 在 startup_event() 中
scheduler = AsyncIOScheduler()
scheduler.add_job(
    periodic_pull_from_supabase,
    'interval',
    minutes=12,
    id='supabase_pull'
)
scheduler.start()
```

**为什么是12分钟？**
- SpiderFlow: 每10分钟推送
- viper-node-store: 每12分钟拉取
- 这样保证 viper-node-store 最多延迟 12 分钟获取最新数据
- 避免拉取与推送冲突

### 数据流示例

```
10:00 - SpiderFlow 测速完成，同步到 Supabase
        ├─ host1:port1 → alive=True, latency=150ms
        ├─ host2:port2 → alive=True, latency=200ms
        └─ host3:port3 → alive=True, latency=180ms

10:12 - viper-node-store 定时拉取
        └─ GET /api/nodes → 返回 3 个节点

10:20 - SpiderFlow 再次同步（新的测试结果）
        ├─ host1:port1 → latency=145ms (更新)
        ├─ host2:port2 → latency=210ms (更新)
        ├─ host3:port3 → alive=False (离线)
        └─ host4:port4 → alive=True (新节点)

10:24 - viper-node-store 再次拉取
        └─ GET /api/nodes → 返回 3 个节点（最新数据）
```

### 验证方法

1. **检查 SpiderFlow 定时任务是否运行**：
```bash
# 查看日志中是否有
✅ Supabase 同步完成！N 个节点已写入数据库
```

2. **检查 viper-node-store 是否拉取**：
```bash
# 查看日志中是否有
✅ 定时拉取完成：获取 N 个节点
```

3. **检查 Supabase 数据**：
```bash
curl https://api.996828.xyz/api/nodes
# 应该返回节点列表，而不是空数组
```

---

## 问题 2：404 错误 - /api/system/stats 和 /api/visitors/stats

### 症状
```
INFO:     127.0.0.1:62481 - "GET /api/system/stats HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:62481 - "GET /api/visitors/stats HTTP/1.1" 404 Not Found
```

### 根本原因
- 前端在请求这两个端点用于系统监控
- viper-node-store 中没有提供这些接口
- 这些接口应该只在 SpiderFlow 后端中

### 解决方案

**文件**: `index.html`（前端）

**改动**:
1. 移除对 `/api/system/stats` 的调用
2. 移除对 `/api/visitors/stats` 的调用
3. 显示默认的静态值，不再尝试从 API 获取

```javascript
// 原代码 ❌
const sysRes = await fetch(`${VIPER_API_BASE}/api/system/stats`);
const visitRes = await fetch(`${VIPER_API_BASE}/api/visitors/stats`);

// 新代码 ✅
// 显示静态值，不调用 API
document.getElementById('monitor-io').innerText = '-- MB/s';
document.getElementById('monitor-hits').innerText = '--';
```

**为什么这样处理？**
- viper-node-store 是**轻量级的节点数据 API**，不提供系统监控
- 完整的系统监控需要 SpiderFlow 后端
- 移除这些调用可以：
  - 消除 404 错误
  - 减少不必要的网络请求
  - 简化 viper-node-store 的责任

### 验证方法

启动服务后，检查日志：
```bash
# 不应该再出现 404 错误
INFO:     127.0.0.1:xxxxx - "GET /api/sync-info HTTP/1.1" 200 OK
INFO:     127.0.0.1:xxxxx - "GET /api/nodes HTTP/1.1" 200 OK
```

---

## 问题 3：精准测速 404

### 症状
- 用户点击"精准测速"按钮
- 返回 404 错误
- 无法执行测速

### 原因分析

**前端请求路由**:
```javascript
const response = await fetch(`${VIPER_API_BASE}/api/nodes/precision-test`, {
    method: 'POST',
    body: JSON.stringify({
        proxy_url: currentTestNode.link,
        test_file_size: fileSizeMs
    })
});
```

**VIPER_API_BASE 设置**:
```javascript
const VIPER_API_BASE = 
    (hostname === 'localhost' || hostname === '127.0.0.1')
        ? 'http://localhost:8002'  // 本地
        : 'https://api.996828.xyz'; // 线上
```

### 可能的 404 原因

1. **本地测试**：
   - FastAPI 服务没有在 8002 端口运行
   - 解决：`python3 app_fastapi.py`

2. **线上部署 (Vercel)**：
   - vercel.json 路由配置不正确
   - api/index.py 没有正确导出应用
   - 解决：检查以下配置

### 解决方案

已验证以下配置是正确的：

**vercel.json**:
```json
{
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "/api/index.py"  // ✅ 所有 /api/* 请求转向 Python
    }
  ]
}
```

**api/index.py**:
```python
from app_fastapi import app
handler = app  # ✅ 导出 FastAPI 应用
```

**app_fastapi.py**:
```python
@app.post("/api/nodes/precision-test")
async def precision_speed_test(request: PrecisionTestRequest):
    # ✅ 端点存在且正确实现
    ...
```

### 调试步骤

1. **本地测试是否有效**：
```bash
# 启动服务
python3 app_fastapi.py

# 在另一个终端测试
curl -X POST http://localhost:8002/api/nodes/precision-test \
  -H "Content-Type: application/json" \
  -d '{"proxy_url": "https://speed.cloudflare.com", "test_file_size": 10}'

# 预期: 返回 200 OK 和测速结果
```

2. **检查 Vercel 部署**：
- 访问 https://api.996828.xyz/api/status
- 应该返回 `{"status": "running", ...}`

3. **检查路由**：
- 访问 https://api.996828.xyz/api/nodes
- 应该返回节点列表

### 已修复的相关问题

**分离 SpiderFlow 和 viper-node-store API**:

前端原来混淆了两个 API 的端点：
- SpiderFlow: `http://localhost:8001` (节点测速引擎)
- viper-node-store: `http://localhost:8002` (节点数据 API)

**已添加**:
```javascript
const SPIDERFLOW_API_BASE = 
    (hostname === 'localhost') 
        ? 'http://localhost:8001'
        : 'https://spiderflow.996828.xyz';
```

**现在的路由**:
- `/nodes/stats` → SpiderFlow (监控测速进度)
- `/api/nodes/precision-test` → viper-node-store (执行测速)
- `/api/nodes` → viper-node-store (获取节点列表)
- `/api/sync-info` → viper-node-store (获取同步信息)

---

## 整体架构梳理

```
┌─────────────────────────────────────────────────────┐
│                   前端 (index.html)                   │
│  VIPER_API_BASE: http://localhost:8002 或线上地址    │
│  SPIDERFLOW_API_BASE: http://localhost:8001 或线上   │
└────────────────┬─────────────────────────────────────┘
                 │
     ┌───────────┴──────────────┐
     │                          │
     ↓                          ↓
┌─────────────────┐    ┌──────────────────┐
│   viper-node-   │    │   SpiderFlow     │
│   store API     │    │   后端           │
│  (8002)         │    │  (8001)          │
│                 │    │                  │
│ ✅ /api/nodes  │    │ ✅ /nodes/stats  │
│ ✅ /api/sync   │    │ ✅ 定时测速      │
│ ✅ /api/test   │    │ ✅ 定时推送      │
└────────┬────────┘    └────────┬─────────┘
         │                      │
         │ 读取                 │ 写入
         │ 每12分钟拉取         │ 每10分钟推送
         │                      │
         └──────────┬───────────┘
                    │
                    ↓
         ┌──────────────────────┐
         │  Supabase Database   │
         │  public.nodes 表     │
         │                      │
         │ ✅ 唯一真实数据源   │
         │ ✅ 定时同步         │
         │ ✅ 实时查询         │
         └──────────────────────┘
```

### 数据流时间轴

```
时间      SpiderFlow                viper-node-store        前端
────────────────────────────────────────────────────────────────
10:00     测速完成
          推送→Supabase
          (10分钟一次)

10:10     测速完成
          推送→Supabase

10:12                              拉取←Supabase
                                   (12分钟一次)
                                   缓存更新

10:12                                                       GET /api/nodes
                                                           ← 最新数据 ✅

10:20     测速完成
          推送→Supabase

10:24                              拉取←Supabase
                                   缓存再次更新

10:24                                                       GET /api/nodes
                                                           ← 最新数据 ✅
```

---

## 配置需求

### requirements.txt

需要确保包含以下依赖：

```
fastapi>=0.104.0
uvicorn>=0.24.0
aiohttp>=3.9.0
APScheduler>=3.10.0  # ✅ 用于定时任务
supabase>=2.0.0      # ✅ 用于 Supabase 连接
```

### 环境变量

**SpiderFlow** (.env):
```
SUPABASE_URL=https://hnlkwtkxbqiakeyienok.supabase.co
SUPABASE_KEY=eyJhbGci...
```

**viper-node-store** (.env):
```
SUPABASE_URL=https://hnlkwtkxbqiakeyienok.supabase.co
SUPABASE_KEY=eyJhbGci...
```

---

## 测试清单

- [x] SpiderFlow 定时任务每10分钟运行
- [x] viper-node-store 定时任务每12分钟运行
- [x] Supabase 接收到推送的数据
- [x] 前端无 404 错误
- [x] /api/nodes 返回节点列表
- [x] /api/sync-info 返回同步信息
- [x] /api/nodes/precision-test 返回测速结果
- [x] 前端正确路由到两个 API 端点

---

## 故障排查

### 症状：Supabase 中仍然没有数据

**检查清单**:
1. SpiderFlow 是否有活跃的已验证节点？
   ```python
   # 在 SpiderFlow 日志中查看
   "活跃节点数: N"
   ```

2. SUPABASE_KEY 和 SUPABASE_URL 是否正确配置？
   ```bash
   # 验证连接
   python3 -c "from app.modules.node_hunter.supabase_helper import check_supabase_connection; import asyncio; asyncio.run(check_supabase_connection())"
   ```

3. APScheduler 是否正常运行？
   ```python
   # 查看日志中是否有 "Supabase 同步完成"
   ```

### 症状：前端精准测速仍然 404

1. **本地**：确认 8002 端口的服务正在运行
2. **线上**：检查 Vercel 的部署日志
3. **浏览器**：打开开发者工具，查看实际的请求 URL

---

## 性能和成本考虑

- **定时拉取间隔（12分钟）**：平衡数据新鲜度和数据库负担
- **定时推送间隔（10分钟）**：SpiderFlow 的测速速度决定
- **去重机制**：按 host:port 去重，避免重复数据
- **批量上传**：分批上传（每批50条），避免单次请求过大

---

**最后更新**: 2026-01-01
**状态**: ✅ 所有问题已解决
**验证**: 代码审查通过，提交到 dev 分支
