# 大陆/海外节点切换功能 - 部署指南

## 📋 功能概述

本版本实现了节点列表的大陆/海外切换功能，具有以下特点：

- **默认显示大陆节点**：从 `telegram_nodes` 表获取
- **一键切换海外节点**：通过顶部 Tab 切换到 `nodes` 表
- **管理员权限控制**：健康检测仅限管理员使用
- **数据源隔离**：每个数据源有独立的 VIP 限制（各 20 个节点）
- **智能刷新**：刷新按钮仅刷新当前选择的数据源

## 🔧 部署步骤

### 1. 数据库配置

在 Supabase 运行以下 SQL 脚本添加管理员字段：

```bash
# 自动运行脚本
cat scripts/add_admin_field.sql | psql -h <supabase-host> -U <user> -d <database>

# 或在 Supabase 控制面板手动运行
```

**SQL 脚本内容**：
```sql
ALTER TABLE public.profiles 
ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_profiles_is_admin ON public.profiles (is_admin);
```

### 2. 设置管理员用户

在 Supabase SQL 编辑器中运行：

```sql
-- 通过用户 ID 设置管理员
UPDATE public.profiles 
SET is_admin = TRUE 
WHERE id = 'your-user-id-here';

-- 或通过邮箱查询并设置
UPDATE public.profiles 
SET is_admin = TRUE 
WHERE id = (
  SELECT id FROM auth.users WHERE email = 'admin@example.com'
);

-- 查看所有管理员
SELECT p.id, u.email, p.is_admin
FROM public.profiles p
JOIN auth.users u ON p.id = u.id
WHERE p.is_admin = TRUE;
```

### 3. 后端启动方式

**方式 1：使用新的启动脚本（推荐）**
```bash
cd /path/to/viper-node-store
python run_backend.py
```

**方式 2：使用 python -m**
```bash
cd /path/to/viper-node-store
python -m backend.main
```

**方式 3：使用启动脚本**
```bash
bash scripts/start-backend.sh
```

### 4. 前端配置

前端会自动从后端加载节点列表，默认显示大陆节点。用户可以通过顶部的 Tab 切换：

- **🇨🇳 大陆节点**：从 `/api/telegram-nodes` 获取
- **🌍 海外节点**：从 `/api/nodes` 获取

## 🧪 测试功能

运行测试脚本验证所有功能：

```bash
bash test_features.sh
```

### 测试内容包括：
1. ✅ 获取海外节点 API
2. ✅ 获取大陆节点 API
3. ✅ 节点数据格式验证
4. ✅ VIP 用户限制验证
5. ✅ 健康检测权限验证

## 📱 前端 UI 布局

### PC 端（≥768px）
```
┌─────────────────────────────────────────────────────┐
│ 🌟 萤火云 │ [🇨🇳大陆] [🌍海外] │ [🏥健] [🔄刷] [👤]│  ← 顶部导航栏
├─────────────────────────────────────────────────────┤
│ 总节点 212 │ 健康 181 │ 平均 13.16 MB/s │ 更新 18:26│
├─────────────────────────────────────────────────────┤
│  🔍 搜索框                                           │
│  [协议过滤] [国家过滤]                              │
├─────────────────────────────────────────────────────┤
│ [节点卡片 1] [节点卡片 2] [节点卡片 3]             │
│ [节点卡片 4] [节点卡片 5] [节点卡片 6]             │
└─────────────────────────────────────────────────────┘
```

### 移动端（<768px）
```
┌──────────────────────────────┐
│ 🌟 萤火云 │ [🏥] [🔄] [👤] │ ← 顶部导航栏（折叠）
├──────────────────────────────┤
│ [🇨🇳大陆] [🌍海外]         │ ← Tab 切换
├──────────────────────────────┤
│ 总节点 212 │ 健康 181 ...  │
├──────────────────────────────┤
│  🔍 搜索框                   │
│  [协议过滤]                  │
│  [国家过滤]                  │
├──────────────────────────────┤
│ [节点卡片 1]                 │
│ [节点卡片 2]                 │
└──────────────────────────────┘
```

## 🔐 权限控制

### 健康检测权限

健康检测按钮仅在以下条件下显示：
- 用户已登录
- 用户的 `profiles.is_admin = TRUE`

**权限验证流程**：
1. 前端检查 `authStore.isAdmin` 显示/隐藏按钮
2. 后端验证请求头中的 `X-User-ID` 及其管理员状态
3. 非管理员请求返回 403 Unauthorized

## 📊 API 端点

### 获取海外节点
```http
GET /api/nodes?limit=20
Headers: X-User-ID: <user-id> (可选)
```

### 获取大陆节点
```http
GET /api/telegram-nodes?limit=20
Headers: X-User-ID: <user-id> (可选)
```

### 执行健康检测（仅管理员）
```http
POST /api/health-check
Headers: X-User-ID: <admin-user-id>, Content-Type: application/json
Body: {
  "batch_size": 100,
  "source": "overseas" | "china"
}
```

## 🐛 故障排除

### 问题 1：后端启动失败 - ImportError

**症状**：`attempted relative import with no known parent package`

**解决方案**：
```bash
# ✓ 使用 python -m 启动
python -m backend.main

# 或使用新的启动脚本
python run_backend.py
```

### 问题 2：获取大陆节点返回空列表

**症状**：`/api/telegram-nodes` 返回 `[]`

**排查步骤**：
1. 确认 Supabase 中 `telegram_nodes` 表存在
2. 检查后端日志中的错误信息
3. 验证 Supabase API 密钥配置正确

### 问题 3：健康检测权限验证失败

**症状**：非管理员点击健康检测按钮返回 403 错误

**解决方案**：
1. 确认用户的 `profiles.is_admin = TRUE`
2. 检查请求中 `X-User-ID` 是否正确
3. 刷新页面重新加载用户权限信息

## 📝 配置文件

### backend/config.py（环境变量）
```python
HOST = "0.0.0.0"  # 监听地址
PORT = 8002        # 监听端口
RELOAD = True      # 开发模式热重载
LOG_LEVEL = "INFO" # 日志级别
```

### 启动环境变量
```bash
export SUPABASE_URL="https://xxx.supabase.co"
export SUPABASE_KEY="your-api-key"
python run_backend.py
```

## 📚 技术实现细节

### 后端实现
- **Auth Service**：`check_user_admin_status()` 方法验证管理员权限
- **Node Service**：新增 `get_telegram_nodes()` 方法获取大陆节点
- **Routes**：新增 `/api/telegram-nodes` 端点，修改健康检测权限控制

### 前端实现
- **Auth Store**：添加 `isAdmin` 状态，同时检查 VIP 和管理员身份
- **Node Store**：添加 `dataSource` 状态实现数据源切换，`switchDataSource()` 方法
- **App.vue**：添加 Tab 切换按钮和条件渲染

## 🚀 性能考虑

- **并发限制**：健康检测最多并发 20 个节点
- **超时设置**：TCP 5 秒，HTTP 8 秒超时
- **重试机制**：不可用节点重试 2 次
- **缓存策略**：节点列表使用 12 分钟更新周期

## 📞 支持

如遇到问题，请检查：
1. 后端日志输出（寻找 WARNING 和 ERROR）
2. 前端浏览器控制台（F12 -> Console）
3. Supabase 数据库状态和 API 密钥
4. 网络连接和防火墙设置
