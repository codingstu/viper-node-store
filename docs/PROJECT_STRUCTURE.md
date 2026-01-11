# Viper Node Store - 项目结构与功能说明

## 📋 项目概述

**Viper Node Store** 是一个全自动、零成本的代理节点质量检测系统，采用**前后端分离架构**，具有组件化、模块化的设计。

- **前端**: Vue 3 + Vite + Tailwind CSS（位于 `frontend/` 目录）
- **后端**: FastAPI + Supabase（位于 `backend/` 目录）
- **启动方式**:
  - 前端：`cd frontend && npm run dev`
  - 后端：`python backend/main.py`

---

## 🏗️ 目录结构

```
viper-node-store/
├── backend/                    # 后端服务（模块化）
│   ├── main.py                # 主应用入口
│   ├── config.py              # 配置管理
│   │
│   ├── core/                  # 核心模块
│   │   ├── __init__.py
│   │   ├── logger.py          # 日志配置
│   │   └── database.py        # Supabase 客户端
│   │
│   ├── api/                   # API 路由层
│   │   ├── __init__.py
│   │   ├── models.py          # Pydantic 数据模型
│   │   └── routes.py          # 所有 API 端点
│   │
│   ├── services/              # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── node_service.py    # 节点管理业务
│   │   ├── auth_service.py    # 认证和授权
│   │   ├── health_checker.py  # 健康检测
│   │   └── data_sync.py       # 数据同步
│   │
│   └── webhooks/              # Webhook 处理
│       ├── __init__.py
│       └── receiver.py        # Webhook 接收和处理
│
├── frontend/                  # 前端应用
│   ├── src/
│   │   ├── App.vue            # 主应用组件
│   │   ├── main.js            # 入口文件
│   │   ├── style.css          # 全局样式
│   │   │
│   │   ├── components/        # Vue 组件库
│   │   │   ├── NodeCard.vue
│   │   │   ├── AuthModal.vue
│   │   │   ├── HealthCheckModal.vue
│   │   │   └── ...
│   │   │
│   │   ├── services/          # API 调用层
│   │   │   └── api.js         # Axios 实例和 API 方法
│   │   │
│   │   └── stores/            # Pinia 状态管理
│   │       ├── nodeStore.js   # 节点数据状态
│   │       └── authStore.js   # 认证状态
│   │
│   ├── package.json
│   ├── vite.config.js
│   └── public/
│
├── docs/                      # 文档（集中管理）
│   ├── PROJECT_STRUCTURE.md   # 本文件：项目结构和功能
│   ├── CHANGELOG.md           # 更新日志和修复记录
│   └── README.md              # 快速开始指南
│
├── public/                    # 公开资源
│   └── nodes.json             # 节点数据（不提交）
│
├── scripts/                   # 启动脚本
│   ├── start-backend.sh
│   ├── start-frontend.sh
│   └── start-all-unified.sh
│
├── cloudflare_worker.js       # Cloudflare Worker 代理脚本
├── requirements.txt           # Python 依赖
├── vercel.json                # Vercel 部署配置
│
└── README.md                  # 旧项目说明（已分离到 docs/）

```

---

## 🚀 核心功能

### 1️⃣ **节点管理系统** (`backend/services/node_service.py`)

#### 获取节点列表
```python
GET /api/nodes?limit=20&show_free=true&show_china=true
```

**功能**:
- 从 Supabase 数据库获取节点
- 支持分页、搜索、排序
- 区分 VIP 和免费用户限额
  - VIP 用户：最多 500 个节点
  - 免费用户：最多 20 个节点

#### 同步信息查询
```python
GET /api/sync-info
```

**返回**:
- 最后更新时间
- 距现在分钟数
- 节点总数
- 活跃节点数

---

### 2️⃣ **健康检测** (`backend/services/health_checker.py`)

#### 手动触发检测
```python
POST /api/health-check?batch_size=50
```

**检测项目**:
- TCP 连接测试
- HTTP 连通性测试
- 失败重试机制
- 并发控制（最多 20 个并发）

**检测状态**:
- `online`: 节点正常可用
- `offline`: 节点不可用
- `suspect`: TCP 通但 HTTP 不通

---

### 3️⃣ **用户认证** (`backend/services/auth_service.py`)

#### VIP 状态检查
```python
async def check_user_vip_status(user_id: str) -> bool
```

#### 激活码兑换
```python
POST /api/auth/redeem-code
{
  "code": "VIPX-XXXX-XXXX",
  "user_id": "user-uuid"
}
```

**功能**:
- 激活码验证
- VIP 期限计算
- 状态更新到 Supabase

---

### 4️⃣ **测速功能**

#### 精确测速 (下载速度)
```python
POST /api/nodes/precision-test
{
  "proxy_url": "...",
  "test_file_size": 50  // MB
}
```

#### 延迟测试
```python
POST /api/nodes/latency-test
{
  "proxy_url": "..."
}
```

---

### 5️⃣ **Webhook 支持** (`backend/webhooks/receiver.py`)

接收来自 SpiderFlow 的节点数据推送：
```python
POST /webhooks/nodes
```

**功能**:
- 数据去重
- 自动同步到 Supabase
- 后台异步处理

---

## 🔧 技术栈

### 后端
| 组件 | 技术 | 用途 |
|------|------|------|
| 框架 | FastAPI | Web 框架 |
| 数据库 | Supabase | 云数据库 |
| 异步 | asyncio | 异步 I/O |
| 调度 | APScheduler | 定时任务 |
| HTTP | aiohttp | 异步请求 |

### 前端
| 组件 | 技术 | 用途 |
|------|------|------|
| 框架 | Vue 3 | 前端框架 |
| 构建 | Vite | 构建工具 |
| 样式 | Tailwind CSS | 样式框架 |
| 状态 | Pinia | 状态管理 |
| 请求 | Axios | HTTP 客户端 |

---

## 🔄 数据流向

```
┌─────────────┐
│  SpiderFlow  │  (外部测速系统)
└──────┬──────┘
       │ Webhook 推送
       ▼
┌──────────────────┐
│ Webhook Receiver │  (接收推送)
└──────┬───────────┘
       │ 数据验证、去重
       ▼
┌──────────────────┐
│  Supabase DB     │  (数据存储)
└──────┬───────────┘
       │ 查询
       ▼
┌──────────────────┐
│ Backend API      │  (FastAPI 服务)
└──────┬───────────┘
       │ RESTful API
       ▼
┌──────────────────┐
│ Frontend Vue App │  (用户界面)
└──────────────────┘
```

---

## 📊 Supabase 数据库结构

### nodes 表
| 列 | 类型 | 说明 |
|-----|-----|------|
| id | UUID | 主键 |
| link | Text | 节点分享链接 |
| content | JSONB | 节点详细信息 |
| is_free | Boolean | 是否免费 |
| speed | Integer | 速度测试结果 |
| latency | Integer | 延迟 (ms) |
| mainland_score | Integer | 大陆测速评分 |
| mainland_latency | Integer | 大陆延迟 (ms) |
| overseas_score | Integer | 国外测速评分 |
| overseas_latency | Integer | 国外延迟 (ms) |
| status | Text | 健康状态 (online/offline/suspect) |
| last_health_check | Timestamp | 最后检测时间 |
| health_latency | Integer | 检测延迟 |
| updated_at | Timestamp | 更新时间 |
| created_at | Timestamp | 创建时间 |

### activation_codes 表
| 列 | 类型 | 说明 |
|-----|-----|------|
| id | UUID | 主键 |
| code | Text | 激活码（唯一） |
| vip_days | Integer | VIP 天数 |
| used | Boolean | 是否已使用 |
| used_by | UUID | 使用者 ID |
| used_at | Timestamp | 使用时间 |
| created_at | Timestamp | 创建时间 |
| expires_at | Timestamp | 过期时间 |

---

## ⚙️ 配置管理

所有配置集中在 `backend/config.py`：

```python
class Config:
    # Supabase 配置
    SUPABASE_URL = "..."
    SUPABASE_KEY = "..."
    
    # 服务器配置
    HOST = "0.0.0.0"
    PORT = 8002
    
    # 节点限制
    DEFAULT_NODE_LIMIT = 20  # 免费用户
    VIP_NODE_LIMIT = 500     # VIP 用户
    
    # 定时任务
    SUPABASE_PULL_INTERVAL_MINUTES = 12
```

### 环境变量
```bash
SUPABASE_URL=https://...
SUPABASE_KEY=eyJhbGc...
SPIDERFLOW_API_URL=http://localhost:8001
WEBHOOK_SECRET=your-secret-key
```

---

## 🔐 API 安全特性

### 1. CORS 配置
- 允许所有来源（可按需限制）
- 支持跨域请求

### 2. VIP 限制
- 在服务器端检查用户 VIP 状态
- 防止前端绕过限制

### 3. Webhook 签名验证
- HMAC-SHA256 验证
- 防止伪造请求

### 4. 错误处理
- 统一错误返回格式
- 详细的日志记录
- 无敏感信息泄露

---

## 🚀 启动与部署

### 本地开发

**启动后端**:
```bash
python backend/main.py
# 或
python -m backend.main
```

**启动前端**:
```bash
cd frontend
npm run dev
```

### 部署

**Vercel (前端)**:
```bash
cd frontend
npm install
npm run build
# Vercel 自动部署
```

**云服务器 (后端)**:
```bash
pip install -r requirements.txt
python backend/main.py
```

**Docker**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "backend/main.py"]
```

---

## 📈 定时任务

系统自动运行以下定时任务：

| 任务 | 间隔 | 功能 |
|-----|------|------|
| Supabase 定时拉取 | 12 分钟 | 更新内存缓存 |

可通过 API 手动触发：
```python
POST /api/sync/poll-now
```

---

## 🧪 测试

### API 测试
```bash
# 健康检查
curl http://localhost:8002/api/status

# 获取节点
curl http://localhost:8002/api/nodes?limit=10

# 获取同步信息
curl http://localhost:8002/api/sync-info
```

### 前端测试
访问 `http://localhost:5173`

---

## 🔄 版本信息

- **API 版本**: 2.0.0
- **数据来源**: Supabase
- **最后更新**: 2026-01-11

---

## 📚 相关文档

- [更新日志](CHANGELOG.md) - 所有修复和改进记录
- [快速开始](README.md) - 3 分钟快速启动
- 原始项目说明已整合至本文档

---

## 💡 开发建议

1. **添加新功能**: 在 `backend/services/` 创建新业务类
2. **添加新 API**: 在 `backend/api/routes.py` 中注册路由
3. **修改配置**: 编辑 `backend/config.py`
4. **前端开发**: 在 `frontend/src/` 中添加组件
5. **数据模型**: 在 `backend/api/models.py` 中定义

---

## 📞 支持

如有问题，请：
1. 检查 `CHANGELOG.md` 中的已知问题
2. 查看日志输出
3. 验证环境变量配置
