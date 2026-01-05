# 部署修复总结 - 2026年1月2日

## 概述
今日对 viper-node-store 和 SpiderFlow 部署进行了全面的优化和修复，解决了前端硬编码地址、路由配置、构建配置等多个关键问题。

---

## 1. 前端硬编码 localhost 地址修复

### 问题描述
部署到 Vercel 后，前端代码中的硬编码 localhost 地址导致"Failed to fetch"错误。浏览器无法从 Vercel 部署的域名访问 localhost。

### 受影响的文件

#### 1.1 viper-node-store/frontend/src/components/ManualRefreshButton.vue
**问题：** 第 49 行硬编码 localhost
```javascript
// ❌ 原代码
const response = await fetch('http://localhost:8002/api/nodes?limit=500')
```

**修复：** 改为相对路径
```javascript
// ✅ 修复后
const response = await fetch('/api/nodes?limit=500')
```

**影响范围：** 手动刷新按钮功能，用户点击按钮时会调用此接口

---

#### 1.2 viper-node-store/frontend/src/stores/authStore.js
**问题：** 第 252 行硬编码 localhost 和变量名错误
```javascript
// ❌ 原代码
const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002'
const response = await fetch(`${apiUrl}/api/auth/redeem-code`, {
```

**修复：** 改为环境变量，修复变量名和路径
```javascript
// ✅ 修复后
const apiUrl = import.meta.env.VITE_API_BASE || '/api'
const response = await fetch(`${apiUrl}/auth/redeem-code`, {
```

**说明：**
- 变量名改为 `VITE_API_BASE`（与 .env.production 对应）
- 路径从 `/api/api/auth/redeem-code` 改为 `/api/auth/redeem-code`（避免双重 /api）

**影响范围：** 激活码兑换功能

---

#### 1.3 SpiderFlow/frontend/src/components/SyncButton.vue
**问题：** 第 45 行硬编码 localhost:8001
```javascript
// ❌ 原代码
const response = await fetch('http://localhost:8001/api/sync', {
```

**修复：** 改为相对路径
```javascript
// ✅ 修复后
const response = await fetch('/api/sync', {
```

**影响范围：** SpiderFlow 同步按钮功能

---

### 修复原理
- 使用**相对路径** `/api/*` 代替硬编码 localhost
- Vercel 的 `vercel.json` 路由规则会将 `/api/*` 转发到后端
- 本地开发时，Vite proxy 也会转发 `/api/*` 到 localhost:8002

---

## 2. Vercel 部署配置优化

### 2.1 vercel.json 路由配置
**文件：** viper-node-store/vercel.json

**优化内容：**
```json
{
  "builds": [
    {
      "src": "app_fastapi.py",
      "use": "@vercel/python",
      "config": { "maxLambdaSize": "50mb" }
    },
    {
      "src": "frontend/package.json",
      "use": "@vercel/node",
      "config": { "zeroConfig": true }
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "app_fastapi.py"
    },
    {
      "src": "/(.*)",
      "dest": "frontend/dist/$1"
    }
  ]
}
```

**关键修复：**
- ✅ `builds` 使用正确的 `app_fastapi.py`（不是旧的 `/api/index.py`）
- ✅ 添加前端构建配置
- ✅ 路由规则：`/api/*` → FastAPI 后端，`/*` → Vue 前端

---

### 2.2 前端 package.json buildCommand
**添加内容：**
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist"
}
```

**目的：** 确保 Vercel 正确编译 Vue 前端

---

## 3. 前端环境变量配置

### 3.1 创建 .env.production
**文件：** viper-node-store/frontend/.env.production
```
VITE_API_BASE=/api
```

**作用：** 生产环境下所有 API 调用使用相对路径 `/api`

---

### 3.2 保留 .env.development（本地开发）
通过 Vite 的 proxy 配置转发到 localhost:8002

**文件：** viper-node-store/frontend/vite.config.js
```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8002',
      changeOrigin: true,
      rewrite: (path) => path
    }
  }
}
```

---

## 4. Cloudflare Tunnel 配置修复

### 问题
Cloudflare Tunnel 指向错误的端口（8000 而非 8001）

### 修复
**文件：** `/etc/cloudflared/config.yml`
```yaml
tunnel: <tunnel-id>
credentials-file: /etc/cloudflared/<uuid>.json

ingress:
  - hostname: api.996828.xyz
    service: http://localhost:8001    # ✅ 改为 8001
  - service: http_status
```

### 影响
- SpiderFlow API 现在可通过 `https://api.996828.xyz` 访问
- 后续可从 Azure 本地通过 Cloudflare 访问 SpiderFlow

---

## 5. Supabase 同步配置

### 环境变量（已配置 ✅）
**文件：** SpiderFlow/backend/.env
```
SUPABASE_URL=https://hnlkwtkxbqiakeyienok.supabase.co
SUPABASE_KEY=eyJhbGc...（anon key）
```

### 数据流
```
SpiderFlow (测速) 
    ↓
Supabase (数据库存储)
    ↓
viper-node-store (读取 Supabase)
    ↓
Vercel 前端 (展示数据)
```

**注意：** 同步依赖 Supabase 连接正常，可通过以下命令检查：
```bash
python3 -c "from app.modules.node_hunter.supabase_helper import check_supabase_connection; import asyncio; asyncio.run(check_supabase_connection())"
```

---

## 6. Git 提交记录

### viper-node-store
```bash
commit b2d6e61
Author: ...
Date: 2026-01-02

fix: remove all hardcoded localhost addresses in frontend components

- ManualRefreshButton.vue: changed fetch('http://localhost:8002/api/nodes?limit=500') to relative path '/api/nodes?limit=500'
- authStore.js: changed fetch with hardcoded localhost to use environment variable VITE_API_BASE with fallback to '/api'
- authStore.js: fixed double /api in URL path (/api/api/auth/redeem-code -> /api/auth/redeem-code)
```

### SpiderFlow
```bash
commit 1d209ec
Author: ...
Date: 2026-01-02

fix: remove hardcoded localhost in SyncButton component

- SyncButton.vue: changed fetch('http://localhost:8001/api/sync') to relative path '/api/sync'
- This allows the deployed frontend to communicate with its backend via proper routing
```

---

## 7. 验证清单

### ✅ 已完成的检查
- [x] 所有前端文件中硬编码 localhost 已移除
- [x] 环境变量正确配置（SUPABASE_URL, SUPABASE_KEY）
- [x] Cloudflare Tunnel 指向正确端口（8001）
- [x] vercel.json 路由配置正确
- [x] 前端构建命令正确
- [x] 代码已提交到 git

### ⚠️ 待验证的事项
- [ ] 清除 Vercel 构建缓存并重新部署
- [ ] 测试生产环境 `/api/nodes` 接口
- [ ] 测试 Vercel 前端与后端通信
- [ ] 测试激活码兑换功能
- [ ] 检查 SpiderFlow 同步是否成功

---

## 8. 部署步骤

### 8.1 本地测试
```bash
# viper-node-store 后端
cd /Users/ikun/study/Learning/viper-node-store
python app_fastapi.py

# viper-node-store 前端（新终端）
cd frontend
npm run dev  # 访问 http://localhost:5174

# SpiderFlow 后端（新终端）
cd /Users/ikun/study/Learning/SpiderFlow/backend
python -m app.main
```

### 8.2 Vercel 部署
```bash
cd /Users/ikun/study/Learning/viper-node-store
git push origin dev  # 触发自动部署

# 如果需要手动清除缓存：
# 访问 Vercel 仪表板 → 项目 → Settings → Git → Clear Cache
```

### 8.3 验证生产 URL
```bash
# 测试 API 端点
curl https://viper-node-store-git-dev-codingstus-projects.vercel.app/api/status
curl https://viper-node-store-git-dev-codingstus-projects.vercel.app/api/nodes?limit=5

# 打开浏览器访问前端
https://viper-node-store-git-dev-codingstus-projects.vercel.app
```

---

## 9. 常见问题排查

### Q: 前端显示"Failed to fetch"
**原因可能：**
- [ ] Vercel 部署未更新代码（清除缓存重新部署）
- [ ] 后端未启动或不可达
- [ ] CORS 配置问题

**解决方案：**
```bash
# 1. 清除 Vercel 缓存
# 访问 Vercel 仪表板 → Settings → Git → Clear Cache

# 2. 重新部署
git push origin dev

# 3. 检查后端
curl https://viper-node-store-git-dev-codingstus-projects.vercel.app/api/status
```

---

### Q: Supabase 同步失败
**原因可能：**
- [ ] 环境变量未配置
- [ ] Supabase 连接超时
- [ ] nodes 表不存在或权限问题

**解决方案：**
```bash
# 1. 检查环境变量
grep SUPABASE /Users/ikun/study/Learning/SpiderFlow/backend/.env

# 2. 测试连接
cd /Users/ikun/study/Learning/SpiderFlow/backend
python3 -c "from app.modules.node_hunter.supabase_helper import check_supabase_connection; import asyncio; print(asyncio.run(check_supabase_connection()))"
```

---

## 10. 相关文件速查表

| 文件 | 修改内容 | 优先级 |
|------|--------|-------|
| `frontend/src/components/ManualRefreshButton.vue` | 移除硬编码 localhost | 🔴 高 |
| `frontend/src/stores/authStore.js` | 改用环境变量，修复路径 | 🔴 高 |
| `frontend/src/components/SyncButton.vue` (SpiderFlow) | 移除硬编码 localhost | 🔴 高 |
| `vercel.json` | 路由配置、build 配置 | 🔴 高 |
| `frontend/.env.production` | 设置 VITE_API_BASE=/api | 🔴 高 |
| `frontend/vite.config.js` | 本地 proxy 配置 | 🟡 中 |
| `/etc/cloudflared/config.yml` | Tunnel 端口 8001 | 🟡 中 |
| `SpiderFlow/backend/.env` | Supabase 凭证 | 🟡 中 |

---

## 11. 下一步优化方向

- [ ] 添加更详细的错误日志（便于排查问题）
- [ ] 实现环境变量验证（启动时检查必要的环境变量）
- [ ] 添加 API 健康检查端点
- [ ] 考虑添加 API 速率限制
- [ ] 性能监控和告警

---

**文档更新时间：** 2026-01-02  
**维护人：** ikun  
**状态：** ✅ 完成
