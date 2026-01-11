# Viper Node Store - 代理节点测速系统

![Status](https://img.shields.io/badge/Status-Active-green)
![License](https://img.shields.io/badge/License-MIT-blue)
![Architecture](https://img.shields.io/badge/Architecture-Modular-blue)
![Backend](https://img.shields.io/badge/Backend-FastAPI-blue)
![Frontend](https://img.shields.io/badge/Frontend-Vue3-green)

**一个全自动、零成本的代理节点质量检测系统。** 采用**前后端分离、模块化架构**，易于维护和扩展。

---

## 🎯 快速导航

### 📚 完整文档
- **[项目结构与功能说明](docs/PROJECT_STRUCTURE.md)** - 了解项目架构、技术栈、API 端点
- **[更新日志与修复记录](docs/CHANGELOG.md)** - 查看所有优化和修复
- **[快速参考](docs/QUICK_REFERENCE.md)** - 常用命令和快速诊断
- **[Vercel 部署配置](docs/VERCEL_DEPLOYMENT.md)** - Serverless 部署指南

### 🆘 遇到问题？
- **[API 404 错误](docs/API_404_TROUBLESHOOTING.md)** - 后端 API 无响应？看这里
- **[部署问题排查](docs/DEPLOYMENT_TROUBLESHOOTING.md)** - 部署时出错？详细诊断指南
- **[生产问题总结](docs/PRODUCTION_ISSUE_SUMMARY.md)** - 线上问题和解决方案

### 🚀 快速启动

#### 启动后端
```bash
# 方式 1：直接运行
python backend/main.py

# 方式 2：使用启动脚本
bash scripts/start-backend.sh
```
后端地址: `http://localhost:8002`

#### 启动前端
```bash
cd frontend
npm run dev
```
前端地址: `http://localhost:5173`

---

## ✨ 主要特性

### 🌐 节点管理
- 从 Supabase 实时获取节点数据
- 支持分页、搜索、排序
- VIP 和免费用户限额管理

### 🏥 健康检测
- TCP 连接测试
- HTTP 连通性测试
- 并发健康检测（最多 20 个并发）
- 自动重试机制

### ⚡ 测速功能
- 精确下载速度测试
- 延迟测试
- 性能评分

### 🔐 用户认证
- VIP 状态检查
- 激活码兑换
- 安全的服务端验证

### 💾 数据管理
- Supabase 云数据库
- 定时数据同步
- Webhook 支持

---

## 🏗️ 项目结构

```
viper-node-store/
├── backend/                    # 后端（FastAPI）
│   ├── main.py                # 主应用入口
│   ├── config.py              # 配置管理
│   ├── core/                  # 核心模块（日志、数据库）
│   ├── api/                   # API 路由和模型
│   ├── services/              # 业务逻辑
│   └── webhooks/              # Webhook 处理
│
├── frontend/                  # 前端（Vue 3）
│   ├── src/
│   │   ├── App.vue
│   │   ├── components/        # UI 组件
│   │   ├── services/          # API 调用
│   │   └── stores/            # 状态管理
│   └── package.json
│
├── docs/                      # 文档
│   ├── PROJECT_STRUCTURE.md   # 项目说明
│   └── CHANGELOG.md           # 更新日志
│
├── scripts/                   # 启动脚本
└── requirements.txt           # Python 依赖
```

---

## 🔧 技术栈

| 组件 | 技术 |
|------|------|
| **后端框架** | FastAPI |
| **前端框架** | Vue 3 + Vite |
| **样式** | Tailwind CSS |
| **状态管理** | Pinia |
| **数据库** | Supabase |
| **异步框架** | asyncio |
| **HTTP 客户端** | aiohttp |

---

## 🚀 快速开始

### 前置条件
- Python 3.11+
- Node.js 18+
- Supabase 账户
- Cloudflare 账户（可选）

### 本地开发

**1. 克隆和安装**
```bash
git clone <repository>
cd viper-node-store

# 安装后端依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend
npm install
cd ..
```

**2. 配置环境变量**
```bash
# 创建 .env 文件（参考 .env.example）
export SUPABASE_URL="https://..."
export SUPABASE_KEY="eyJhbGc..."
```

**3. 启动服务**
```bash
# 终端 1: 启动后端
python backend/main.py

# 终端 2: 启动前端
cd frontend
npm run dev
```

**4. 访问应用**
- 前端: http://localhost:5173
- 后端 API: http://localhost:8002/api/nodes

---

## 📖 API 文档

### 主要端点

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/nodes` | 获取节点列表 |
| `GET` | `/api/sync-info` | 获取同步信息 |
| `POST` | `/api/health-check` | 触发健康检测 |
| `POST` | `/api/nodes/precision-test` | 精确测速 |
| `POST` | `/api/nodes/latency-test` | 延迟测试 |
| `POST` | `/api/auth/redeem-code` | 兑换激活码 |

**详见 [项目结构文档](docs/PROJECT_STRUCTURE.md#-api-文档)**

---

## ⚙️ 配置

所有配置在 `backend/config.py` 中管理：

```python
# Supabase 配置
SUPABASE_URL = "..."
SUPABASE_KEY = "..."

# 服务器
HOST = "0.0.0.0"
PORT = 8002

# 限制
DEFAULT_NODE_LIMIT = 20      # 免费用户
VIP_NODE_LIMIT = 500         # VIP 用户
```

支持环境变量覆盖。

---

## 📊 数据库

### Supabase 表结构

**nodes** 表包含：
- 节点信息（host、port、protocol）
- 测速结果（速度、延迟、评分）
- 健康状态（online/offline/suspect）
- 时间戳

**activation_codes** 表包含：
- 激活码
- VIP 期限
- 使用情况

**详见 [项目结构文档](docs/PROJECT_STRUCTURE.md#-supabase-数据库结构)**

---

## 🧪 测试

```bash
# 测试后端
curl http://localhost:8002/api/status

# 获取节点
curl http://localhost:8002/api/nodes?limit=10

# 获取同步信息
curl http://localhost:8002/api/sync-info
```

---

## 📈 定时任务

系统自动运行：
- **每 12 分钟**: Supabase 数据拉取（更新缓存）

手动触发：
```bash
curl -X POST http://localhost:8002/api/sync/poll-now
```

---

## 🔄 更新日志

查看 [CHANGELOG.md](docs/CHANGELOG.md) 了解：
- ✅ 2026-01-11 - 项目重构与解耦（模块化架构）
- ✅ 2026-01-06 - 前端同步状态修复
- ✅ 2026-01-06 - Cloudflare Worker 修复

---

## 💡 开发指南

### 添加新 API
1. 在 `backend/api/models.py` 定义数据模型
2. 在 `backend/services/` 实现业务逻辑
3. 在 `backend/api/routes.py` 注册路由

### 添加新功能
1. 创建新服务类 (`backend/services/your_service.py`)
2. 在 `backend/api/routes.py` 中调用
3. 更新 [CHANGELOG.md](docs/CHANGELOG.md)

### 修改配置
1. 编辑 `backend/config.py`
2. 更新 `.env.example`
3. 记录变更

---

## 🐛 故障排除

### 后端无法启动
- 检查 Python 版本：`python --version`
- 检查依赖：`pip install -r requirements.txt`
- 检查环境变量：`echo $SUPABASE_URL`

### 前端无法连接后端
- 确保后端运行在 `http://localhost:8002`
- 检查 CORS 配置
- 查看浏览器控制台错误

### API 返回错误
- 查看后端日志输出
- 检查 Supabase 连接
- 验证 API 端点正确性

**更多信息见 [CHANGELOG.md](docs/CHANGELOG.md)**

---

## 📄 许可证

MIT License - 详见 LICENSE 文件

---

## 📞 支持

- 查看 [项目结构文档](docs/PROJECT_STRUCTURE.md)
- 检查 [更新日志](docs/CHANGELOG.md)
- 查看日志输出诊断问题

---

## 🎉 致谢

感谢所有贡献者和使用者的支持！

---

**最后更新**: 2026-01-11 | **版本**: 2.0.0


**第 2 步: 添加 GitHub Secret**
```
Settings → Secrets and variables → Actions
添加: CLOUDFLARE_WORKER_URL = <你的Worker URL>
```

**第 3 步: 测试**
```
Actions → Update & Test Nodes → Run workflow
```

👉 [详细指南](./QUICKSTART.md)

---

## 📁 项目结构

```
viper-node-store/
├── update_nodes.py              # 主测速脚本
├── aliyun_fc_main.py            # Aliyun FC 大陆测速函数
├── cloudflare_worker.js         # Cloudflare 国外测速函数
├── index.html                   # 前端网页
├── public/
│   └── nodes.json              # 本地节点缓存
├── .github/workflows/
│   └── update-nodes.yml         # GitHub Actions 工作流
├── QUICKSTART.md                # 快速启动指南 ← START HERE
├── CLOUDFLARE_SETUP.md          # Cloudflare 部署详指南
├── ARCHITECTURE.md              # 完整系统架构说明
└── UPGRADE_SUMMARY.md           # 最新更改总结
```

---

## 🔧 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| **大陆测速** | Aliyun FC Python 3.11 | Web Function 模式 |
| **国外测速** | Cloudflare Workers | JavaScript Service Worker |
| **主脚本** | Python 3.11 | aiohttp + supabase 库 |
| **前端** | HTML5 + Tailwind CSS | 无框架，纯 JavaScript |
| **数据库** | Supabase | PostgreSQL 后端 |
| **自动化** | GitHub Actions | Cron 触发 (0 */4 * * *) |

---

## 📈 性能指标

| 指标 | 数值 |
|------|------|
| 节点容量 | 200+ |
| 测速成功率 | >85% |
| 执行时间 | ~5 分钟 |
| 前端加载 | <2 秒 |
| 无单点故障 | ✅ 是 (Aliyun + CF 独立) |

---

## 💡 工作流程

### 1. 节点获取
```
API 导出 → 本地 JSON (备份) → 200+ 个原始节点
```

### 2. 智能分类
```
遍历每个节点的 country 字段:
  - CN        → 大陆测速队列
  - HK/TW/MO  → 国外测速队列 (回国节点)
  - 其他/无   → 国外测速队列
```

### 3. 并发测速
```
大陆 (Aliyun):    批大小 15, TCP 握手测试, 延迟 < 400ms
国外 (Cloudflare): 批大小 15, HTTP HEAD 请求, 延迟 < 500ms
```

### 4. 质量评分
```
根据延迟计算 1-50 分评分:
  大陆: 50分(极速<50ms) → 1分(差>350ms)
  国外: 50分(极速<100ms) → 1分(差>400ms)
```

### 5. 数据保存
```
去重 (host:port ID) → 批量写入 (50 条/批) → Supabase
```

### 6. 前端显示
```
禁用缓存 → 获取最新数据 → 分类显示 (免费/VIP) → 用户查看
```

---

## 🔐 安全性

### 密钥保护
- ✅ 所有密钥存储在 GitHub Secrets
- ✅ 不在代码中硬编码任何凭证
- ✅ Cloudflare Worker URL 作为密钥保管

### 数据安全
- ✅ public/nodes.json 在 .gitignore 中 (不提交节点信息)
- ✅ Supabase 使用 anon key (只读权限)
- ✅ 前端使用 HTTPS 通信

### 频率限制
- ✅ Aliyun 批处理 (15 个/批, 0.5s 间隔)
- ✅ Cloudflare 并发测试 (充分利用)

---

## 📊 监控和日志

### GitHub Actions 日志
```
Actions 标签页 → Update & Test Nodes → 运行记录 → 完整日志
```

### Supabase 数据
```
项目 → SQL 编辑器 → SELECT * FROM nodes ORDER BY updated_at DESC
```

### 前端控制台
```
F12 → Console → 检查 fetch 请求和 JSON 数据
```

---

## 🆘 故障排查

### 常见问题

**Q: 为什么页面显示旧数据？**
```
A: 刷新浏览器缓存
   - 按 Ctrl+Shift+Delete
   - 点击页面刷新按钮
   - 系统已添加时间戳参数防止缓存
```

**Q: Worker 返回 error？**
```
A: 检查以下:
   1. Cloudflare Dashboard 的 Worker 日志
   2. 节点是否真的在线
   3. JSON 格式是否正确
```

**Q: GitHub Actions 没有执行？**
```
A: 检查:
   1. 所有 Secrets 是否正确设置
   2. 工作流文件是否有语法错误
   3. main 分支是否是默认分支
```

👉 [完整故障排查指南](./CLOUDFLARE_SETUP.md#常见问题)

---

## 🎯 使用场景

### 场景 1: 自动更新节点质量
```
系统每 4 小时自动:
- 从 API 获取最新节点
- 大陆和国外分别测速
- 将结果保存到数据库
```

### 场景 2: 用户选择最佳节点
```
用户访问网站:
- 看到通过测速的节点
- 按速度评分排序
- 选择最合适的节点
```

### 场景 3: 监控节点健康
```
定期检查:
- 哪些节点失败率高
- 延迟趋势如何变化
- 是否需要移除坏节点
```

---

## 📈 成本分析

| 服务 | 免费额度 | 预计使用 | 成本 |
|------|---------|---------|------|
| Aliyun FC | 100 万次/月 | ~10 万次/月 | $0 |
| Cloudflare Workers | 10 万次/天 | ~2000 次/天 | $0 |
| GitHub Actions | 2000 分钟/月 | ~300 分钟/月 | $0 |
| Supabase | 500MB | ~50MB | $0 |
| **总计** | - | - | **$0** |

---

## 🚀 进阶功能 (规划中)

- [ ] 添加大陆多地区测速 (北京/深圳/上海)
- [ ] WebSocket 实时监控
- [ ] 用户自定义评分标准
- [ ] 历史数据和趋势分析
- [ ] 支持更多国外测速点 (AWS/GCP/Azure)
- [ ] 节点备份和恢复

---

## 📚 文档导航

| 文档 | 说明 |
|------|------|
| [QUICKSTART.md](./QUICKSTART.md) | **👈 从这里开始** 3 分钟快速部署 |
| [CLOUDFLARE_SETUP.md](./CLOUDFLARE_SETUP.md) | Cloudflare Worker 详细部署指南 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 系统架构、数据流、性能分析 |
| [UPGRADE_SUMMARY.md](./UPGRADE_SUMMARY.md) | 最新更改和改进总结 |

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 报告 Bug
```
GitHub Issues → 描述问题 → 附加日志
```

### 建议功能
```
GitHub Issues → Feature Request → 详细说明需求
```

---

## 📄 许可证

MIT License - 自由使用和修改

---

## 🙋 常见问题

### Q: 支持多少个节点？
A: 理论上无限制。系统设计支持 200+ 节点，测速时间控制在 5 分钟内。

### Q: 测速有多准确？
A: 非常准确。大陆测速来自真实 Aliyun 机房，国外测速来自 Cloudflare 全球节点。

### Q: 能否自定义测速评分？
A: 可以。修改 Python 脚本中的 `calculate_score()` 函数。

### Q: 大陆多地区怎么测？
A: 需要在多个地区部署 Aliyun FC，然后轮流调用。计划中的功能。

---

## 📞 技术支持

- 🐛 **Bug 报告:** GitHub Issues
- 💡 **建议反馈:** GitHub Discussions
- 📧 **邮件联系:** (添加你的邮箱)

---

## 🎉 快开始吧！

👉 [点击这里开始 3 分钟快速启动](./QUICKSTART.md)

---

**Made with ❤️ by SHADOW NEXUS Team**

Last Updated: 2025-01-XX | Status: ✅ Fully Operational
