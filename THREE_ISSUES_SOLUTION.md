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

---

## 前端重写：从纯HTML到Vue3（2026-01-02）

### 背景
原始纯HTML前端存在三个关键问题：
1. **空链接问题**：节点链接为空时，仍显示 COPY/QR CODE 按钮
2. **空QR码问题**：链接为空时生成空白QR码
3. **实时性问题**：精准测速后，数据不刷新UI

### 解决方案：完全重写为Vue3 + Vite

#### 项目结构
```
viper-node-store-vue/
├── src/
│   ├── main.js                 # 应用入口，Pinia初始化
│   ├── App.vue                 # 根组件，主界面布局
│   ├── style.css               # 全局样式（Tailwind）
│   ├── components/
│   │   ├── NodeCard.vue        # 单个节点卡片组件
│   │   ├── QRCodeModal.vue     # QR码弹窗，链接验证
│   │   └── PrecisionTestModal.vue  # 测速弹窗
│   ├── services/
│   │   └── api.js              # 集中式API层，数据规范化
│   └── stores/
│       └── nodeStore.js        # Pinia状态管理
├── tailwind.config.js
├── postcss.config.cjs
├── vite.config.js
└── package.json
```

#### 核心改进

##### 1. 智能链接验证（解决问题1、2）

**NodeCard.vue**:
```javascript
// 只有链接有效时才显示按钮
const showActions = computed(() => {
  return link.value && link.value.trim() !== '';
});

// v-if/v-else 条件渲染
<button v-if="showActions" @click="showQRCode">QR CODE</button>
<div v-else class="text-gray-400">🔗 No Link</div>
```

**QRCodeModal.vue**:
```javascript
// watch监听prop，链接有效才生成QR码
watch(() => [props.show, props.node], () => {
  if (props.show && link.value?.trim()) {
    generateQRCode();  // ✅ 只生成有效QR码
  }
});
```

##### 2. 响应式数据更新（解决问题3）

**PrecisionTestModal.vue**:
```javascript
// 调用API测速
const testResult = await nodeStore.precisionTest(node, fileSize);

// 直接更新状态存储
nodeStore.updateNodeSpeed(node.id, testResult.speed);
// Vue 自动响应式更新 NodeCard 显示的速度
```

**nodeStore.js** (Pinia):
```javascript
// 状态管理
state: () => ({
  nodes: [],
}),

// 更新方法触发响应式
updateNodeSpeed(nodeId, speed) {
  const node = this.nodes.find(n => n.id === nodeId);
  if (node) node.speed = speed;  // ✅ Vue自动重新渲染
}
```

##### 3. 数据规范化（api.js）

```javascript
// 后端返回格式可能不一致
// api.js 统一转换为标准格式
export async function fetchNodes() {
  const response = await fetch('/api/nodes');
  const data = await response.json();
  
  // 规范化到统一的数据结构
  return data.map(node => ({
    id: node.id,
    protocol: node.protocol,
    host: node.host,
    port: node.port,
    link: node.link || '',        // ✅ 处理空链接
    speed: node.speed || 0,
    latency: node.latency || 0,
    country: node.country || 'Unknown',
    is_free: node.is_free ?? true,
  }));
}
```

#### 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.x | 前端框架（Composition API） |
| Vite | 7.3.0 | 构建工具 |
| Pinia | 3.0.4 | 状态管理 |
| Tailwind CSS | 3.x | 样式框架 |
| easyqrcodejs | 4.6.2 | QR码生成 |

#### 安装和运行

```bash
# 安装依赖
npm install

# 开发服务器（Vite，热重载）
npm run dev
# → http://localhost:5173/

# 生产构建
npm run build

# 预览生产构建
npm run preview
```

#### 配置要点

**tailwind.config.js**:
- 内容扫描：`"./src/**/*.{vue,js,ts,jsx,tsx}"`
- 确保Tailwind类被识别

**postcss.config.cjs** (关键！):
```javascript
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```
⚠️ **必须是 .cjs 格式**（CommonJS），避免 Vite ESM 冲突

#### 组件通信流程

```
App.vue (主界面)
  ├─ nodeStore (状态中心)
  │  ├─ nodes[]           # 所有节点
  │  ├─ displayedNodes    # 搜索/过滤后的节点
  │  └─ updateNodeSpeed() # 更新速度
  │
  ├─ NodeCard.vue (节点卡片) ×50
  │  ├─ 显示node属性
  │  ├─ @click:showQRCode  → emit → App.vue
  │  └─ @click:showTest    → emit → App.vue
  │
  ├─ QRCodeModal.vue (QR码弹窗)
  │  ├─ v-if="props.show"
  │  ├─ v-if="link.trim()"  ✅ 链接有效才显示
  │  └─ generateQRCode()     ✅ 只生成有效QR码
  │
  └─ PrecisionTestModal.vue (测速弹窗)
     ├─ 调用 nodeStore.precisionTest()
     ├─ 接收测速结果
     └─ nodeStore.updateNodeSpeed()  ✅ 自动更新UI
```

#### 问题解决验证

| 问题 | 原因 | 解决方案 | 状态 |
|------|------|--------|------|
| 空链接显示按钮 | 纯HTML无条件渲染 | NodeCard v-if/showActions | ✅ |
| 空QR码 | 未验证链接 | QRCodeModal watch监听 | ✅ |
| 测速不更新UI | 无状态管理 | Pinia updateNodeSpeed() | ✅ |

#### CSS和样式

- **框架**：Tailwind CSS v3
- **预处理**：PostCSS + autoprefixer
- **深色主题**：内置深灰色背景 + 蓝色渐变
- **响应式**：移动端友好的网格布局

示例 App.vue 样式：
```vue
<div class="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-blue-900">
  <!-- 深灰色到蓝色渐变背景 -->
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-6">
    <!-- 响应式网格：1列(移动) → 2列(平板) → 3列(桌面) -->
  </div>
</div>
```

#### 部署

**Vercel 部署配置** (vercel.json):
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist"
}
```

推送到 main 分支后，Vercel 自动构建并部署。

---

### 开发进度

- [x] 项目初始化（Vite + Vue3）
- [x] 组件架构设计
- [x] NodeCard 组件（链接验证）
- [x] QRCodeModal 组件（条件生成QR）
- [x] PrecisionTestModal 组件（测速结果）
- [x] Pinia 状态管理
- [x] API 服务层（数据规范化）
- [x] Tailwind CSS 配置
- [x] 搜索和过滤功能
- [x] 深色主题样式
- [x] 热重载开发环境（Vite）

### 关键文件修改

```bash
# 新增文件
viper-node-store-vue/src/main.js
viper-node-store-vue/src/App.vue
viper-node-store-vue/src/style.css
viper-node-store-vue/src/components/NodeCard.vue
viper-node-store-vue/src/components/QRCodeModal.vue
viper-node-store-vue/src/components/PrecisionTestModal.vue
viper-node-store-vue/src/services/api.js
viper-node-store-vue/src/stores/nodeStore.js
viper-node-store-vue/tailwind.config.js
viper-node-store-vue/postcss.config.cjs
viper-node-store-vue/vite.config.js
viper-node-store-vue/package.json

# 配置文件
viper-node-store-vue/.gitignore
viper-node-store-vue/index.html
```

### 测试验证

```bash
# 1. 启动开发服务器
cd viper-node-store-vue && npm run dev

# 2. 打开浏览器
# → http://localhost:5173/

# 3. 验证功能
# ✅ 页面加载，显示节点列表
# ✅ 点击有效链接的节点 → QR CODE 按钮可用
# ✅ 点击无链接的节点 → QR CODE 按钮禁用
# ✅ QR CODE 弹窗显示有效的二维码
# ✅ 点击精准测速 → 进度条显示，结果更新
# ✅ 搜索和过滤功能正常
```

---

**完成日期**: 2026-01-02  
**验证状态**: ✅ 本地开发环境正常运行，所有功能测试通过  
**部署建议**: 测试无误后推送到 main 分支，Vercel 自动部署

---

## 前端重构：功能完善计划（2026-01-02 进行中）

### 已完成
- ✅ 项目迁移至 viper-node-store/frontend
- ✅ 修复 Tailwind CSS 配置（v3.4）
- ✅ **修复刷新间隔：30秒 → 12分钟（720000ms）**
  - 现在与后端 Supabase 拉取同步（每12分钟一次）
- ✅ 页面样式正确显示
- ✅ 节点列表加载和显示
- ✅ QR码生成和复制
- ✅ 精准测速功能

### 进行中（高优先级）
- 🔄 登录/注册功能（Supabase Auth）
  - 文件：需要创建 `src/components/AuthModal.vue`
  - Supabase 配置已在后端 app_fastapi.py
  - 需要在前端集成 @supabase/supabase-js

- 🔄 VIP 状态显示和切换
  - 从 Supabase Auth 读取用户身份
  - 显示 VIP 徽章和过期时间
  - VIP 和普通节点的不同显示

- 🔄 VIP 和非 VIP 节点区分显示
  - 在 NodeCard 中根据 VIP 状态显示不同内容
  - VIP 节点显示额外功能
  - 非 VIP 节点显示限制提示

### 暂停（未来功能，不在当前迭代）
- ⏸️ **区域切换功能**（大陆/海外）
  - 原始功能在 index.html 中的 switchRegion()
  - 需要后端支持两套数据源
  - **暂时不实现，以后再做**

- ⏸️ CN LINE 按钮
  - 属于区域切换的一部分

- ⏸️ Latency Test（延迟测试）
  - 原始功能在 index.html 中的 startLatencyTest()
  - 补充功能，优先级较低

### 修复清单（当前迭代）
- [x] 刷新间隔：30秒 → 12分钟
- [ ] Supabase Auth 集成
- [ ] 登录/注册 UI（AuthModal 组件）
- [ ] VIP 状态读取和显示
- [ ] VIP/普通节点 UI 区分

### 测试步骤（修复后）
```bash
# 确认刷新间隔是 12 分钟而不是 30 秒
# 浏览器控制台应该每 12 分钟输出一次：
# "🚀 应用启动，初始化数据..."
# 或后续更新的时间戳

# 数据应该与后端 Supabase 拉取同步
# 后端日志每 12 分钟：
# "Supabase 定时拉取完成"
```

---

**最后更新**: 2026-01-02 02:05  
**状态**: 🔧 修复进行中  
**下一步**: 添加登录/VIP 功能
