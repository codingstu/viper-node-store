# 节点健康检测功能 - 完整实现文档

## 📋 目录
1. [功能概述](#功能概述)
2. [架构设计](#架构设计)
3. [实现细节](#实现细节)
4. [修复历程](#修复历程)
5. [使用指南](#使用指南)
6. [故障排查](#故障排查)
7. [维护建议](#维护建议)

---

## 功能概述

### 需求背景
用户报告问题：
- "节点没网了但是还在数据库中"
- "需要定时加上健康检测"
- "页面上临时加一个按钮用来检测所有节点"
- "不能用的节点多检测两遍"
- "给节点打上标记离线或者offline"

### 最终方案
实现轻量级节点健康检测系统：
- ✅ **轻量级 TCP + HTTP 检测**（而非 Clash + Xray）
- ✅ **失败重试机制**（检测失败自动重试 2 次）
- ✅ **数据库状态标记**（online/suspect/offline）
- ✅ **前端自动刷新**（检测完成后自动更新节点卡片）
- ✅ **免费部署方案**（Vercel Hobby + Supabase）

---

## 架构设计

### 系统组件

```
┌─────────────────────────────────────────────────────────────┐
│                     前端 (Vue.js)                            │
├─────────────────────────────────────────────────────────────┤
│ App.vue                    ← 添加「🏥 健康检测」按钮          │
│ HealthCheckModal.vue       ← 新建检测进度弹窗                │
│ NodeCard.vue              ← 显示离线/可疑状态徽章             │
│ api.js                    ← healthCheckApi.checkAll()        │
│ nodeStore.js              ← 节点状态管理                     │
└─────────────────────────────────────────────────────────────┘
                              ↓ API /api/health-check (POST)
┌─────────────────────────────────────────────────────────────┐
│                  后端 (FastAPI)                              │
├─────────────────────────────────────────────────────────────┤
│ app_fastapi.py                                              │
│ ├─ trigger_health_check()     ← 接收前端请求                │
│ ├─ get_supabase_nodes()       ← 获取节点列表                │
│ └─ updater.update_node_status() ← 更新数据库                │
│                                                             │
│ health_checker.py                                           │
│ ├─ LightweightHealthChecker   ← 执行 TCP/HTTP 检测          │
│ ├─ SupabaseHealthUpdater      ← 更新 Supabase              │
│ └─ run_health_check()         ← 主检测函数                 │
└─────────────────────────────────────────────────────────────┘
                              ↓ 更新
┌─────────────────────────────────────────────────────────────┐
│                  Supabase 数据库                             │
├─────────────────────────────────────────────────────────────┤
│ nodes 表新增字段：                                           │
│ ├─ status (VARCHAR 20)            ← online/suspect/offline   │
│ ├─ last_health_check (TIMESTAMP)  ← 最后检测时间            │
│ └─ health_latency (INTEGER)       ← 检测延迟 (ms)          │
└─────────────────────────────────────────────────────────────┘
```

### 检测流程

```
用户点击「🏥 健康检测」
         ↓
HealthCheckModal 显示
         ↓
POST /api/health-check
         ↓
app_fastapi.py:
  1. 调用 get_supabase_nodes(limit=100) 获取前 100 个节点
  2. 初始化 LightweightHealthChecker
  3. 批量调用 check_node() 执行 TCP/HTTP 检测
  4. 统计结果 (online/suspect/offline)
  5. 调用 updater.update_node_status() 更新数据库
         ↓
前端自动调用 nodeStore.refreshNodes()
         ↓
重新拉取 /api/nodes（包含新的 status 字段）
         ↓
NodeCard 显示 offline/suspect 徽章
```

---

## 实现细节

### 1. 数据库字段（Supabase）

**迁移脚本**: `HEALTH_CHECK_MIGRATION.sql`

```sql
ALTER TABLE public.nodes 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'unknown';

ALTER TABLE public.nodes 
ADD COLUMN IF NOT EXISTS last_health_check TIMESTAMP WITH TIME ZONE;

ALTER TABLE public.nodes 
ADD COLUMN IF NOT EXISTS health_latency INTEGER;

CREATE INDEX IF NOT EXISTS idx_nodes_status ON public.nodes(status);
CREATE INDEX IF NOT EXISTS idx_nodes_last_health_check ON public.nodes(last_health_check NULLS FIRST);
```

**状态值**:
- `online` - 节点正常，TCP 通 + HTTP 通
- `suspect` - 可疑节点，TCP 通但 HTTP 超时（多用于代理协议）
- `offline` - 节点离线，TCP 连接失败
- `unknown` - 未检测过（默认值）

### 2. 后端实现

#### app_fastapi.py

**新增 API 端点**:

```python
@app.post("/api/health-check")
async def trigger_health_check(request: HealthCheckRequest = None):
    """
    手动触发健康检测
    
    逻辑流程：
    1. 获取 batch_size（默认 100）个节点
    2. 初始化 LightweightHealthChecker
    3. 执行批量 TCP/HTTP 检测
    4. 更新 Supabase 数据库
    5. 返回统计结果
    
    返回格式：
    {
        "status": "success",
        "data": {
            "status": "completed",
            "total": 100,
            "online": 85,
            "suspect": 5,
            "offline": 10,
            "problem_nodes": [...]
        }
    }
    """
```

**修改 get_supabase_nodes()**:

新增返回字段以支持前端显示状态：
```python
node = {
    ...
    "status": row.get("status", "online"),           # ← 新增
    "last_health_check": row.get("last_health_check"), # ← 新增
    "health_latency": row.get("health_latency"),       # ← 新增
    ...
}
```

#### health_checker.py

**LightweightHealthChecker 类**:

```python
class LightweightHealthChecker:
    """轻量级健康检测器"""
    
    async def check_tcp_connection(host: str, port: int)
        → (bool, Optional[int], Optional[str])
    # 使用 asyncio.open_connection() 测试 TCP 连接
    # 返回 (是否成功, 延迟ms, 错误信息)
    
    async def check_http_connectivity(host: str, port: int, protocol: str)
        → (bool, Optional[int], Optional[str])
    # 对 HTTP/HTTPS/SOCKS 协议进行测试
    # 代理协议（vmess/vless/trojan/ss）跳过 HTTP 测试
    
    async def check_node(node: Dict) → HealthCheckResult
    # 单个节点检测，包含 2 次重试机制
    
    async def check_nodes_batch(nodes: List[Dict]) → List[HealthCheckResult]
    # 批量检测，最多 20 个并发
```

**SupabaseHealthUpdater 类**:

```python
class SupabaseHealthUpdater:
    """Supabase 数据库更新器"""
    
    async def update_node_status(results: List[HealthCheckResult])
        → Tuple[int, int]
    # 使用 PATCH /rest/v1/nodes?id=eq.{node_id}
    # 批量更新 status, last_health_check, health_latency
    # 返回 (成功数, 失败数)
```

### 3. 前端实现

#### HealthCheckModal.vue

**新建组件** - 健康检测弹窗

关键功能：
- 显示检测进度（已检测 / 总数）
- 实时统计（在线 / 离线 / 可疑）
- 显示问题节点列表
- 自动刷新节点列表

```vue
<!-- 初始状态 -->
开始检测按钮

<!-- 检测中 -->
显示进度条 (0-100%)
显示实时统计数字

<!-- 完成 -->
显示最终结果
列出所有离线/可疑节点
重新检测 / 关闭按钮
```

#### NodeCard.vue

**修改内容**:

1. **添加状态徽章** - 在节点名称旁显示离线/可疑标识
```vue
<span v-if="node.status === 'offline'" class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-500/30 text-rose-300 border border-rose-500/50">
  离线
</span>
<span v-else-if="node.status === 'suspect'" class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/30 text-amber-300 border border-amber-500/50">
  可疑
</span>
```

2. **动态样式** - 根据状态改变卡片颜色
```javascript
const nodeStatusClass = computed(() => {
  const status = props.node.status
  if (status === 'offline') {
    return 'from-rose-500/10 to-rose-500/5 border-rose-500/30 opacity-60'  // 红色 + 半透明
  }
  if (status === 'suspect') {
    return 'from-amber-500/10 to-amber-500/5 border-amber-500/30'  // 黄色
  }
  return 'from-white/10 to-white/5 border-white/20'  // 默认
})
```

#### api.js

**新增 healthCheckApi**:

```javascript
export const healthCheckApi = {
  async checkAll() {
    // POST /api/health-check
    // 返回检测结果和问题节点列表
  },
  
  async getStats() {
    // GET /api/health-check/stats
    // 获取全局统计信息
  }
}
```

**修改 nodeApi.fetchNodes()**:

确保返回 status 字段并添加调试日志：
```javascript
nodes = nodes.map(node => ({
  ...
  status: node.status || 'online',
  last_health_check: node.last_health_check || null,
  health_latency: node.health_latency || null
}))

console.log('📦 获取节点数据，示例节点:', nodes.length > 0 ? nodes[0] : 'empty')
```

#### nodeStore.js

**新增计算属性**:

```javascript
// 离线节点统计
const offlineNodeCount = computed(() => {
  return displayedNodes.value.filter(n => n.status === 'offline').length
})

// 可疑节点统计
const suspectNodeCount = computed(() => {
  return displayedNodes.value.filter(n => n.status === 'suspect').length
})

// 修改健康节点统计逻辑
const healthyNodeCount = computed(() => {
  return displayedNodes.value.filter(n => n.speed >= 5 && n.status !== 'offline').length
})
```

#### App.vue

**修改内容**:

1. 导入 HealthCheckModal 组件
2. 添加健康检测按钮
3. 绑定弹窗状态
4. 添加完成回调处理

```vue
<!-- 顶部导航栏 -->
<button
  @click="showHealthCheckModal = true"
  class="px-4 py-1.5 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 text-sm font-bold rounded-lg border border-emerald-500/50 transition"
  title="检测所有节点的健康状态"
>
  🏥 健康检测
</button>

<!-- 弹窗组件 -->
<HealthCheckModal
  :show="showHealthCheckModal"
  @close="showHealthCheckModal = false"
  @complete="handleHealthCheckComplete"
/>
```

---

## 修复历程

### 问题 1: Vercel Cron Jobs 收费

**现象**: 部署失败，提示 Cron Jobs 仅在 Pro 计划可用

**原始方案**: 在 vercel.json 中配置 Cron Job，每 30 分钟自动触发

**修复方案**: 
- ❌ 移除 vercel.json 中的 crons 配置
- ✅ 改为前端按钮手动触发
- ✅ 提供免费定时方案（cron-job.org）

**相关文件**: 
- `vercel.json` - 移除 crons 配置
- `HEALTH_CHECK_FREE_PLAN.md` - 免费方案文档

---

### 问题 2: 前端框架错误

**现象**: 修改了旧的 HTML 文件，Vue 前端无法使用

**原始方案**: 修改 index.html

**修复方案**:
- ❌ 删除对 index.html 的修改
- ✅ 创建 HealthCheckModal.vue 组件
- ✅ 修改 NodeCard.vue、App.vue 等 Vue 文件

**相关提交**: `5ea489a` - 移除 App.vue 中重复声明的 showTestModal 变量

---

### 问题 3: 节点查询返回空结果

**现象**: 健康检测完成但显示 "no_nodes"

**根本原因**: health_checker.py 中的 get_nodes_direct() 使用了错误的环境变量

**修复方案**:
1. ✅ 添加详细的环境变量检查日志
2. ✅ 改用 app_fastapi.py 中的 get_supabase_nodes()（已验证可用）
3. ✅ 在 trigger_health_check() 中直接调用 get_supabase_nodes()

**相关提交**: `7a45ff6` - 直接使用 app_fastapi 的 get_supabase_nodes

---

### 问题 4: status 字段不显示

**现象**: 检测完成，数据库已更新，但节点卡片上没有 offline/suspect 徽章

**根本原因**: `/api/nodes` 返回的数据中没有 status 字段

**修复方案**:
- ✅ 在 get_supabase_nodes() 中添加 status 字段
- ✅ 添加 last_health_check 和 health_latency 字段
- ✅ 确保 NodeCard.vue 能读取到 status 值

**相关提交**: `badf3b5` - 确保 /api/nodes 返回 status 字段

---

### 问题 5: 完成后节点不刷新

**现象**: 检测完成但页面上仍显示旧状态

**修复方案**:
- ✅ 在 HealthCheckModal 完成后自动调用 nodeStore.refreshNodes()
- ✅ 统一 API 返回数据格式
- ✅ 添加刷新状态提示

**相关提交**: `78a4936` - 完善自动刷新机制

---

## 使用指南

### 普通用户

#### 1. 手动检测节点

1. 打开网站，找到顶部导航栏的「🏥 健康检测」按钮
2. 点击按钮，弹窗显示进度
3. 等待检测完成（进度条到 100%）
4. 查看离线节点列表
5. 页面自动刷新，显示 offline/suspect 徽章

#### 2. 定期自动检测（推荐）

使用免费服务 [cron-job.org](https://cron-job.org)：

1. 注册账户
2. 创建新 Cron Job：
   - URL: `https://你的域名.vercel.app/api/health-check`
   - 方法: POST
   - 频率: 每 30 分钟
3. 保存即可

### 开发者

#### 1. 本地测试

```bash
# 后端测试
python test_health_checker.py

# 前端测试
cd frontend && npm run dev
# 访问 http://localhost:5174
# 点击「🏥 健康检测」按钮
```

#### 2. 调试技巧

**查看前端接收的节点数据**:
```javascript
// 在浏览器 Console 中
console.log(nodeStore.allNodesBackup[0])  // 查看第一个节点的完整数据
```

**查看后端日志**:
```bash
# Vercel 部署日志
vercel logs <project-name>

# 本地日志
# 查看 FastAPI 输出中的 🏥 健康检测日志
```

**手动调用 API**:
```bash
curl -X POST https://你的域名.vercel.app/api/health-check \
  -H "Content-Type: application/json" \
  -d '{"check_all": true}'
```

---

## 故障排查

### Q1: 点击「🏥 健康检测」后没有反应

**检查清单**:
1. 打开浏览器 DevTools (F12)
2. 查看 Network 标签，看 POST /api/health-check 是否发出
3. 查看 Response，看是否有错误信息

**常见原因**:
- ❌ Supabase 连接失败 → 检查 SUPABASE_URL 和 SUPABASE_KEY
- ❌ 节点列表为空 → 检查数据库中是否有节点
- ❌ 超时 → 节点过多，增加超时时间

---

### Q2: 检测完成但没有看到 offline 徽章

**检查清单**:
1. 打开 Browser DevTools Console
2. 搜索 `📦 获取节点数据` 日志
3. 展开第一个节点，检查是否有 `status` 字段
4. 如果没有，说明后端返回的数据不对

**常见原因**:
- ❌ 后端没有返回 status 字段 → 检查 app_fastapi.py 的 get_supabase_nodes()
- ❌ Supabase 中节点的 status 列为 NULL → 手动检测或等待自动更新
- ❌ 浏览器缓存 → 按 Ctrl+Shift+Delete 清除缓存

---

### Q3: 健康检测速度很慢

**原因**: 默认检测 100 个节点，TCP 超时 5 秒，HTTP 超时 8 秒

**优化方案**:
```python
# 在 app_fastapi.py 中修改
batch_size = request.batch_size if request else 50  # 改成 50

# 或在 health_checker.py 中修改超时时间
checker = LightweightHealthChecker(
    tcp_timeout=3.0,  # 改成 3 秒
    http_timeout=5.0,  # 改成 5 秒
    max_concurrent=30  # 改成 30 并发
)
```

---

### Q4: 某些节点一直是 offline

**检查清单**:
1. 该节点是否真的离线？尝试手动连接测试
2. 该节点的 protocol 是什么？
3. 检查 Vercel 的网络是否能访问该节点

**已知问题**:
- 一些服务器对 TCP 连接有限制，可能误判为离线
- 某些代理协议需要特殊处理，可在 health_checker.py 中优化

---

## 维护建议

### 1. 定期监控

每周检查一次：
```sql
-- 查看离线节点统计
SELECT status, COUNT(*) as count 
FROM nodes 
GROUP BY status;

-- 查看最久未检测的节点
SELECT id, name, last_health_check 
FROM nodes 
WHERE last_health_check IS NULL 
LIMIT 10;
```

### 2. 优化检测参数

如果发现误判率高，调整：

```python
# health_checker.py
LightweightHealthChecker(
    tcp_timeout=5.0,      # TCP 连接超时
    http_timeout=8.0,     # HTTP 请求超时
    max_retries=2,        # 重试次数
    max_concurrent=20     # 并发数
)
```

### 3. 升级建议

**短期** (1-3 个月):
- 监控误判率，调整超时参数
- 收集用户反馈，改进检测逻辑
- 考虑支持更多代理协议

**中期** (3-6 个月):
- 如果用户增长，考虑迁移到 Vercel Pro（支持 Cron Jobs）
- 实现更复杂的检测逻辑（Clash 集成）
- 添加检测历史记录和趋势分析

**长期** (6 个月+):
- 与 SpiderFlow 深度集成
- 实现全局节点监控中心
- 支持自定义检测策略

### 4. 故障恢复

如果检测功能异常：

```bash
# 1. 检查 Supabase 连接
curl https://your-supabase-url/rest/v1/nodes?select=count \
  -H "apikey: your-key"

# 2. 手动触发一次检测
curl -X POST https://your-domain.vercel.app/api/health-check

# 3. 查看 Vercel 日志
vercel logs <project-name> --follow

# 4. 重置所有节点状态为 unknown
UPDATE nodes SET status = 'unknown', last_health_check = NULL;
```

---

## 相关文件清单

### 后端
- `app_fastapi.py` - FastAPI 主应用，health-check 接口
- `health_checker.py` - 检测逻辑和 Supabase 更新
- `HEALTH_CHECK_MIGRATION.sql` - 数据库迁移脚本
- `test_health_checker.py` - 单元测试

### 前端
- `frontend/src/components/HealthCheckModal.vue` - 检测弹窗
- `frontend/src/components/NodeCard.vue` - 节点卡片（显示徽章）
- `frontend/src/components/App.vue` - 主应用（检测按钮）
- `frontend/src/services/api.js` - healthCheckApi
- `frontend/src/stores/nodeStore.js` - 节点状态管理

### 文档
- `HEALTH_CHECK_FREE_PLAN.md` - 免费部署方案
- `HEALTH_CHECK_IMPLEMENTATION.md` - 本文档

### 配置
- `vercel.json` - Vercel 部署配置（已移除 crons）

---

## 已知限制

1. **TCP/HTTP 轻量级检测** - 不如 Clash/Xray 精准，但足够识别离线节点
2. **并发限制** - 最多 20 个并发（Vercel 限制），检测 100 个节点需约 10-15 秒
3. **误判风险** - 某些服务器可能对 TCP 连接有限制或延迟高，导致误判
4. **协议限制** - 某些特殊代理协议可能需要特殊处理
5. **无历史记录** - 当前仅保存最后一次检测结果，不保存历史

---

## 总结

该功能已完整实现并修复了所有已知问题：

✅ 后端检测逻辑完整
✅ 前端界面友好
✅ 自动状态刷新
✅ 免费部署方案
✅ 完整文档和故障排查

预期后续改进方向：
- 支持更多代理协议
- 集成 Clash/Xray 进行深度检测
- 添加检测历史和趋势分析
- 实现自适应检测参数

---

**最后更新**: 2026-01-04
**当前版本**: 1.0.0
**维护者**: viper-node-store 团队
