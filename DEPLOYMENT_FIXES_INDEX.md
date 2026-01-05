# 部署优化与修复索引 - 2026年1月

## 快速导航

### 📋 详细文档
- **[viper-node-store 部署修复](viper-node-store/DEPLOYMENT_FIXES_2026-01-02.md)** - 完整的前端硬编码修复和 Vercel 配置说明
- **[SpiderFlow 部署修复](SpiderFlow/DEPLOYMENT_FIXES_2026-01-02.md)** - SyncButton 硬编码修复和路由配置说明

---

## 📊 修复概览

### 问题统计
| 类别 | 数量 | 状态 |
|------|------|------|
| 硬编码 localhost 地址 | 3 处 | ✅ 全部修复 |
| 环境变量配置错误 | 1 处 | ✅ 修复 |
| 路由配置问题 | 多项 | ✅ 全部修复 |
| Cloudflare Tunnel 配置 | 1 处 | ✅ 修复 |

---

## 🔧 修复详情

### 1. 硬编码 localhost 移除

#### viper-node-store 前端
```
❌ ManualRefreshButton.vue:49
   fetch('http://localhost:8002/api/nodes?limit=500')
   
✅ 修复为
   fetch('/api/nodes?limit=500')

❌ authStore.js:252
   const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002'
   fetch(`${apiUrl}/api/auth/redeem-code`, ...)
   
✅ 修复为
   const apiUrl = import.meta.env.VITE_API_BASE || '/api'
   fetch(`${apiUrl}/auth/redeem-code`, ...)
```

#### SpiderFlow 前端
```
❌ SyncButton.vue:45
   fetch('http://localhost:8001/api/sync', {...})
   
✅ 修复为
   fetch('/api/sync', {...})
```

---

### 2. 环境变量配置

**创建文件：** `viper-node-store/frontend/.env.production`
```
VITE_API_BASE=/api
```

**检查文件：** `SpiderFlow/backend/.env`
```bash
✅ SUPABASE_URL 已配置
✅ SUPABASE_KEY 已配置
```

---

### 3. Vercel 部署配置

**文件：** `viper-node-store/vercel.json`
```
✅ builds 配置正确（app_fastapi.py）
✅ routes 规则正确（/api/* → FastAPI，/* → Vue）
✅ 前端 buildCommand 已添加
```

**文件：** `viper-node-store/frontend/vite.config.js`
```
✅ dev proxy 配置正确
```

---

### 4. Cloudflare Tunnel 修复

**文件：** `/etc/cloudflared/config.yml`
```
❌ service: http://localhost:8000
✅ service: http://localhost:8001
```

---

## 📈 数据架构

```
┌──────────────────────────────────────────────────┐
│           Vercel 部署（生产环境）                 │
├──────────────────────────────────────────────────┤
│                                                  │
│  viper-node-store 前端          SpiderFlow 前端  │
│  https://viper-...vercel.app    https://spider..│
│                                                  │
│  ✅ 相对路径 /api/*    ←→    ✅ 相对路径 /api/*  │
│                                                  │
└──────────────────────────────────────────────────┘
              ↓                        ↓
    ┌─────────────────────────────────────┐
    │   Vercel 路由层 (vercel.json)       │
    │   /api/* → FastAPI 后端             │
    │   /* → 前端 dist/                   │
    └─────────────────────────────────────┘
              ↓                        ↓
┌──────────────────────────────────────────────────┐
│         后端服务（Vercel Functions）             │
│    viper-node-store    SpiderFlow                │
│    app_fastapi.py      node_hunter.py            │
└──────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────┐
│          Supabase 数据库                         │
│     (SpiderFlow 写入 / viper-node-store 读取)    │
└──────────────────────────────────────────────────┘
```

---

## ✅ 验证检查列表

### 代码层面
- [x] 所有硬编码 localhost 已移除
- [x] 环境变量已配置
- [x] 路由配置已更新
- [x] 代码已 commit 并 push

### 部署准备
- [ ] 清除 Vercel 缓存
- [ ] 等待 Vercel 自动部署完成
- [ ] 测试生产环境 API 端点
- [ ] 验证前后端通信

### 生产验证
- [ ] 前端可正常访问
- [ ] API 请求成功（Network tab 显示 /api/...）
- [ ] Supabase 数据更新
- [ ] 同步功能正常工作

---

## 🚀 快速部署指南

### 1. 本地测试
```bash
# 启动 viper-node-store 后端
cd /Users/ikun/study/Learning/viper-node-store
python app_fastapi.py

# 启动 viper-node-store 前端（新终端）
cd frontend && npm run dev

# 启动 SpiderFlow 后端（新终端）
cd /Users/ikun/study/Learning/SpiderFlow/backend
python -m app.main
```

### 2. 推送到 GitHub
```bash
cd /Users/ikun/study/Learning/viper-node-store
git push origin dev

cd /Users/ikun/study/Learning/SpiderFlow
git push origin dev
```

### 3. Vercel 自动部署
- GitHub push 触发自动部署
- 等待 2-5 分钟完成
- 访问 Vercel 仪表板查看部署状态

### 4. 验证生产环境
```bash
# 测试 API
curl https://viper-node-store-git-dev-*.vercel.app/api/status

# 打开浏览器
https://viper-node-store-git-dev-*.vercel.app
```

---

## 🐛 常见问题

### "Failed to fetch" 错误
**原因：** 硬编码 localhost 或 Vercel 缓存未清除
**解决：** 
1. 确认代码已推送
2. 清除 Vercel 缓存：Vercel 仪表板 → Settings → Git → Clear Cache
3. 等待重新部署

### Supabase 同步失败
**原因：** 环境变量未配置或连接失败
**解决：**
```bash
# 检查环境变量
grep SUPABASE /Users/ikun/study/Learning/SpiderFlow/backend/.env

# 测试连接
python3 -c "from app.modules.node_hunter.supabase_helper import check_supabase_connection; import asyncio; asyncio.run(check_supabase_connection())"
```

### 本地开发 /api 404
**原因：** vite.config.js proxy 配置不正确
**解决：**
```bash
# 检查配置
cat frontend/vite.config.js | grep -A 5 proxy

# 重启开发服务器
npm run dev
```

---

## 📚 相关文件

### viper-node-store
| 文件 | 状态 | 用途 |
|------|------|------|
| `frontend/src/components/ManualRefreshButton.vue` | ✅ 修复 | 手动刷新功能 |
| `frontend/src/stores/authStore.js` | ✅ 修复 | 激活码兑换 |
| `frontend/.env.production` | ✅ 创建 | 生产环境变量 |
| `frontend/vite.config.js` | ✅ 配置 | 本地开发 proxy |
| `vercel.json` | ✅ 配置 | Vercel 路由 |
| `DEPLOYMENT_FIXES_2026-01-02.md` | ✅ 创建 | 详细修复文档 |

### SpiderFlow
| 文件 | 状态 | 用途 |
|------|------|------|
| `frontend/src/components/SyncButton.vue` | ✅ 修复 | 同步功能 |
| `frontend/vite.config.js` | ✅ 配置 | 本地开发 proxy |
| `backend/.env` | ✅ 配置 | Supabase 凭证 |
| `DEPLOYMENT_FIXES_2026-01-02.md` | ✅ 创建 | 详细修复文档 |

---

## 📞 支持信息

如有问题，请参考：
1. **详细文档：** 查看上面的文档链接
2. **日志文件：** 检查应用启动时的错误信息
3. **GitHub Commits：** 查看具体的代码修改

---

**最后更新：** 2026-01-02  
**维护人：** ikun  
**状态：** ✅ 完成
