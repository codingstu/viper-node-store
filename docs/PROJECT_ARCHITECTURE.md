# 项目架构文档 - Phase 2

**版本**: 2.0  
**日期**: 2026-01-01  
**类型**: 系统架构设计

---

## 📐 系统架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                     用户前端 (Web)                          │
│            SpiderFlow Frontend @ localhost:5173              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  NodeHunter 组件                                         ││
│  │  ├─ 快速测速: 前端HEAD → 计算延迟 → 推算速度           ││
│  │  ├─ 精确测速: 用户选择 → 后端/CF Worker → 真实速度    ││
│  │  └─ 节点查询: 调用API获取实时节点数据                  ││
│  └─────────────────────────────────────────────────────────┘│
└────────┬──────────────────────────────────────────────────┬──┘
         │                                                  │
         │ HTTP/HTTPS                              HTTP/HTTPS
         │                                                  │
    ┌────▼──────────────────┐                ┌──────────────▼────┐
    │  SpiderFlow Backend   │                │ viper-node-store  │
    │  @ localhost:8001     │                │ @ localhost:8002  │
    │ ┌──────────────────┐  │   Webhook      │ ┌──────────────┐  │
    │ │ node_hunter.py   │  │◄──推送─────►   │ │ webhook_     │  │
    │ │ webhook_push.py  │  │ (签名验证)    │ │ receiver.py  │  │
    │ │                  │  │                │ │              │  │
    │ │ 检测逻辑:        │  │  轮询获取      │ │ 数据存储:    │  │
    │ │ ├─ Clash检测     │  │◄──────────────┤─┤ ├─ JSON DB   │  │
    │ │ ├─ V2Ray检测     │  │ (5分钟周期)  │ │ │ ├─ 同步状态 │  │
    │ │ ├─ 速度测试      │  │                │ │ │ └─ 推送历史 │  │
    │ │ └─ 可用性检测    │  │  导出请求     │ │ └─ API提供  │  │
    │ └──────────────────┘  │───────────────►│ ├─ GET /nodes │  │
    │                       │                │ ├─ GET /stats │  │
    │ API端点:              │                │ └─ POST /test │  │
    │ ├─ POST /batch-test   │                │                  │
    │ ├─ POST /nodes/test   │   viper数据   │ 数据同步层:      │
    │ └─ POST /nodes/cache  │ ←─ 查询/导出─►│ ├─ Webhook接收 │  │
    └────┬──────────────────┘                │ ├─ 轮询同步    │  │
         │                                   │ └─ 签名验证    │  │
         │                                   └────────────────┘  │
         │                                            │           │
         │                 ┌───────────────────────────┴─────┐   │
         │                 │                                 │   │
    ┌────▼────────┐   ┌────▼─────────┐            ┌──────────▼─┐ │
    │   Supabase  │   │ CF Worker    │            │   导出     │ │
    │  (数据备份) │   │ (边缘计算)   │            │  (仓库)    │ │
    └─────────────┘   └──────────────┘            └────────────┘ │
```

---

## 🔄 数据流架构

### Phase 1 (现有结构)

```
SpiderFlow检测
    ↓
节点验证 (Clash/V2Ray)
    ↓
存储到Supabase + 本地JSON
    ↓
用户查询 ← 前端显示
```

**问题**:
- ❌ SpiderFlow单点依赖
- ❌ 数据不同步
- ❌ viper-node-store静态存储
- ❌ 用户无法控制测速

### Phase 2 (改进架构)

```
SpiderFlow检测
    ├─ 存储到Supabase
    ├─ 推送Webhook (Webhook方案) ──────┐
    │                                  │
    ↓                                  │
监听与轮询                            │
 ├─ 定时轮询 (轮询方案)              │
 │  (5分钟周期)                      │
 │   ↓ (有变更时)                    │
 └─ 更新本地DB ◄───────────────────┘
      ↓
   viper-node-store
      ├─ 节点查询 ← 前端
      ├─ 统计分析 ← 用户分析
      ├─ 精确测速 ← 用户发起
      └─ 数据导出 ← 应用集成
```

**优势**:
- ✅ 实时同步 (Webhook < 200ms)
- ✅ 可靠性高 (轮询兜底)
- ✅ 流量优化 (仅变更推送)
- ✅ 用户控制 (精确测速)
- ✅ 可扩展性 (轻松支持多源)

---

## 🏗️ 分层架构

### 1. 表现层 (Frontend)

**技术栈**: Vue 3 + Naive UI + Tailwind CSS

**文件**: `SpiderFlow/frontend/src/components/NodeHunter/NodeHunter.vue`

**功能**:
```
快速测速 (估算)
├─ 前端HEAD请求
├─ 计算真实延迟 (200-500ms)
└─ 推算速度 (基于延迟→速度映射)

精确测速 (真实)
├─ 用户选择文件大小 (10/25/50/100MB)
├─ 确认流量消耗提示
└─ 后端处理真实下载
```

**核心组件**:
- NodeHunter.vue: 主要界面
- 快速测速按钮: 调用testSingleNode()
- 精确测速按钮: 弹出precision-test modal

---

### 2. 业务逻辑层 (Logic)

**SpiderFlow端** (检测和推送):

```python
# 文件: SpiderFlow/backend/app/modules/node_hunter/node_hunter.py
# 核心职责:
1. 节点检测 (Clash/V2Ray验证)
2. 速度测试 (原有逻辑)
3. Webhook推送 (新增)

# 文件: SpiderFlow/backend/webhook_push.py
# 核心职责:
1. 签名生成 (HMAC-SHA256)
2. 数据推送 (异步HTTP POST)
3. 重试机制 (最多3次)
4. 历史记录 (推送日志)
```

**viper-node-store端** (同步和存储):

```python
# 文件: viper-node-store/webhook_receiver.py
# 核心职责:
1. Webhook接收
2. 签名验证
3. 数据合并
4. 异步同步

# 文件: viper-node-store/data_sync.py
# 核心职责:
1. 定时轮询
2. 变更检测 (哈希对比)
3. 数据同步
4. 状态管理

# 文件: viper-node-store/app_fastapi.py
# 核心职责:
1. API服务 (FastAPI)
2. 生命周期管理
3. 端点暴露
4. 集成调度
```

---

### 3. 数据持久化层 (Data)

**本地存储**:

```
viper-node-store/
├─ verified_nodes.json
│  ├─ nodes: [...]
│  ├─ last_updated: timestamp
│  └─ sync_metadata: {}
│
├─ sync_state.json
│  ├─ last_webhook_time
│  ├─ last_poll_time
│  ├─ webhook_received_count
│  └─ poll_received_count
│
└─ webhook_push_history.json
   └─ [{ timestamp, status, nodes_count }, ...]
```

**远程存储**:

```
Supabase (备份)
├─ nodes表
├─ sync_logs表
└─ test_history表

Cloudflare Workers (计算)
├─ 真实速度测试
├─ 代理延迟测量
└─ 全球边缘节点
```

---

## 🔐 安全架构

### 认证和授权

**Webhook签名机制**:

```python
# 生成 (SpiderFlow端)
payload_str = json.dumps({...}, sort_keys=True)
message = f"{payload_str}.{timestamp}"
signature = HMAC-SHA256(message, WEBHOOK_SECRET)

# 验证 (viper-node-store端)
def verify_webhook_signature(payload_str, timestamp, signature):
    expected = HMAC-SHA256(f"{payload_str}.{timestamp}", WEBHOOK_SECRET)
    return constant_time_compare(expected, signature)
```

**配置**: 共享密钥 `WEBHOOK_SECRET=spiderflow-viper-sync-2026`

---

### 网络隔离

```
开发环境:
localhost:8001 (SpiderFlow)
localhost:8002 (viper-node-store)
└─ 本地内网通信，无需TLS

生产环境:
- 通过VPN或内网连接
- 使用HTTPS + 自签证书
- 考虑API网关 (API Gateway)
```

---

## ⚙️ 集成流程

### 流程1: 检测完成推送

```
事件: 检测完成
┌──────────────────────────────────────────┐
│ SpiderFlow                               │
│ 1. 执行节点检测                          │
│ 2. 保存到本地JSON                        │
│ 3. 上传到Supabase                        │
│ 4. 调用 push_nodes_to_viper()           │
└────────────┬─────────────────────────────┘
             │ POST /webhook/nodes-update
             │ Content: JSON + 签名
             ▼
┌──────────────────────────────────────────┐
│ viper-node-store                         │
│ 1. 接收Webhook请求                       │
│ 2. 验证签名 (HMAC-SHA256)                │
│ 3. 解析JSON数据                          │
│ 4. 合并到本地数据库                      │
│ 5. 记录同步状态                          │
│ 6. 返回200 OK                            │
└──────────────────────────────────────────┘
             │
             ▼
        同步完成 (< 200ms)
```

---

### 流程2: 轮询备用同步

```
定时任务 (每5分钟)
┌──────────────────────────────────────┐
│ viper-node-store DataSyncScheduler   │
│ 1. 连接SpiderFlow API                │
│ 2. GET /nodes/export?format=json     │
│ 3. 接收节点列表                      │
│ 4. 计算本地数据的哈希                │
│ 5. 比对哈希值                        │
└────────────┬──────────────────────────┘
             │
             ├─ 哈希相同 → 无变更 (跳过)
             │
             └─ 哈希不同 → 有变更 ↓
              ┌──────────────────────────────┐
              │ 更新本地数据库               │
              │ 记录同步状态                 │
              │ 异步同步到Supabase          │
              └──────────────────────────────┘
```

---

### 流程3: 用户精确测速

```
用户操作: 点击[精确测速]按钮
┌──────────────────────────────────────────┐
│ NodeHunter.vue (前端)                    │
│ 1. 打开精确测速Modal                     │
│ 2. 用户选择文件大小 (10/50/100MB)        │
│ 3. 显示流量消耗提示                      │
│ 4. 用户点击[确认]                        │
└────────────┬─────────────────────────────┘
             │ POST /api/nodes/precision-test
             │ { proxy_url, test_file_size }
             ▼
┌──────────────────────────────────────────┐
│ viper-node-store                         │
│ 1. 接收精确测速请求                      │
│ 2. 验证代理URL有效性                     │
│ 3. 启动后台测速任务                      │
│ 4. 返回 { status: initiated }            │
└────────────┬─────────────────────────────┘
             │
             ▼
   后台任务: 真实下载测试
   ├─ 通过代理下载test_file_size MB文件
   ├─ 记录下载时间
   ├─ 计算速度 = 文件大小 / 时间
   ├─ 更新节点数据 (node.speed_precise)
   └─ 触发前端轮询更新
```

---

## 📦 模块依赖关系

### viper-node-store模块依赖

```
app_fastapi.py (主应用)
  ├─ imports: webhook_router (from webhook_receiver)
  ├─ imports: DataSyncScheduler, poll_spiderflow_nodes (from data_sync)
  │
  ├─ on_startup():
  │  └─ 启动 sync_scheduler.start()
  │
  └─ API端点
     ├─ GET /api/nodes
     ├─ POST /webhook/nodes-update (webhook_router)
     ├─ GET /api/sync/status
     └─ POST /api/nodes/precision-test

webhook_receiver.py (独立模块)
  ├─ verify_webhook_signature()
  ├─ load_nodes_from_file()
  ├─ merge_node_data()
  └─ webhook_router

data_sync.py (独立模块)
  ├─ SyncState
  ├─ DataSyncScheduler
  ├─ poll_spiderflow_nodes()
  ├─ calculate_nodes_hash()
  └─ get_sync_statistics()
```

### SpiderFlow模块依赖

```
app/modules/node_hunter/node_hunter.py
  ├─ imports: webhook_push
  │
  ├─ @router.post("/batch-test")
  │  └─ background_tasks.add_task(push_nodes_to_viper, ...)
  │
  └─ 原有逻辑不变

webhook_push.py (新增模块)
  ├─ generate_webhook_signature()
  ├─ push_nodes_to_viper() (异步推送)
  ├─ PushHistory (推送历史)
  ├─ get_push_statistics()
  ├─ test_webhook_connection()
  └─ test_webhook_push()
```

---

## 📊 性能指标

### 延迟指标

| 操作 | 延迟 | 说明 |
|-----|------|------|
| Webhook推送 | 100-200ms | 实时推送 |
| 签名验证 | 1-5ms | 本地计算 |
| 数据合并 | 5-20ms | 内存操作 |
| API查询 | 10-50ms | 本地JSON快速 |
| 轮询周期 | 300s (5分钟) | 定时任务 |
| 用户精确测速 | 30-120s | 取决于文件大小和网络 |

---

### 流量指标

| 操作 | 流量 | 频率 | 月总计 |
|-----|------|------|--------|
| Webhook推送 | ~100KB | 1-10/天 | ~3-30MB |
| 定时轮询 | ~100KB | 289次 | ~30MB |
| API查询 | <10KB | 按需 | <1MB |
| 精确测速 | 按选择 | 用户控制 | 按需 |
| **基础总计** | - | - | **~30-60MB** |

**Azure额度**: 100-200GB/月  
**使用率**: 0.03-0.06% ✅ 完全可接受

---

### 资源占用

| 资源 | 使用 | 说明 |
|-----|------|------|
| 内存 | ~50-100MB | Python进程 |
| 存储 | ~1-5MB | JSON数据库 |
| CPU | <5% | 轮询和API |
| 网络 | ~30MB/月 | 基础操作 |

---

## 🔌 可扩展性设计

### 支持多数据源

```python
# 未来支持多个SpiderFlow实例推送
WEBHOOK_SOURCES = [
    "http://spiderflow1:8001",
    "http://spiderflow2:8001",
    "http://spiderflow3:8001"
]

# 轮询所有源
async def poll_all_spiderflow_sources():
    for source_url in WEBHOOK_SOURCES:
        await poll_spiderflow_nodes(source_url)
```

---

### 支持多个消费者

```python
# 导出到多个平台
async def sync_to_multiple_targets(nodes):
    tasks = [
        sync_to_supabase(nodes),      # 数据库
        sync_to_ipfs(nodes),           # 分布式存储
        sync_to_github(nodes),         # 代码仓库
        sync_to_telegram(nodes),       # 通知推送
    ]
    await asyncio.gather(*tasks)
```

---

### 支持扩展协议

```python
# 不仅支持Webhook，还可扩展其他协议
class SyncStrategy:
    async def sync_webhook()        # HMAC签名 (当前)
    async def sync_grpc()           # gRPC (未来)
    async def sync_kafka()          # 消息队列 (未来)
    async def sync_database()       # 数据库变更日志 (未来)
```

---

## 📈 未来演进

### Phase 3 计划

```
1. 前端优化
   ├─ 增强精确测速UI
   ├─ 实时推送更新 (WebSocket)
   └─ 分析图表显示

2. 后端优化
   ├─ 支持多源同步
   ├─ 分布式存储 (IPFS)
   └─ 缓存优化

3. 可观测性
   ├─ 完整日志系统
   ├─ 性能指标导出
   └─ Prometheus集成
```

---

**版本**: 2.0  
**更新日期**: 2026-01-01  
**下一版本**: 2.1 (优化和性能改进)
