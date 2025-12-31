# SHADOW NEXUS - 双地区智能节点测速系统

![Status](https://img.shields.io/badge/Status-Active-green)
![License](https://img.shields.io/badge/License-MIT-blue)
![Cost](https://img.shields.io/badge/Cost-Free-brightgreen)
![Python](https://img.shields.io/badge/Python-3.11-blue)

**一个全自动、零成本的代理节点质量检测系统，分别在大陆和国外进行真实测速，确保最佳的用户体验。**

---

## ✨ 主要特性

### 🌍 双地区测速
- **🇨🇳 大陆测速:** Aliyun Function Compute (杭州/上海)
- **🌐 国外测速:** Cloudflare Workers (全球节点)
- **🎯 精准分类:** 按国家自动分配测速方式

### ⚡ 自动化运行
- GitHub Actions 每 4 小时运行一次
- 支持手动触发
- 完整的日志和错误处理

### 💾 数据管理
- Supabase 云数据库存储
- **自动去重** (protocol+host:port 作为唯一标准)
- **TTL管理** (3天后自动验证，7天离线自动删除)
- **活力检查** (每天凌晨2:00验证所有3天+的节点)
- VIP 用户和免费用户区分

### 🌐 智能前端
- 实时显示最新测速结果
- 禁用缓存确保数据最新
- 支持节点搜索和筛选
- 二维码快速复制

### 💰 完全免费
- Aliyun FC: 100 万次/月免费额度
- Cloudflare Workers: 10 万次/天免费额度
- GitHub Actions: 充足免费额度
- Supabase: 免费 500MB 存储

---

## 📊 系统架构

```
┌─────────────────────────────────────────────────────────┐
│              GitHub Actions (每 4 小时)                  │
└──────────────────────┬──────────────────────────────────┘
                       │
                ┌──────▼──────┐
                │ 获取原始节点 │
                └──────┬───────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
    🇨🇳 CN         🌍 HK/TW      🌍 其他
   大陆节点         回国节点       国外节点
         │             │             │
         └─────────────┼─────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
         ▼                           ▼
    ⚙️ Aliyun FC          🌍 Cloudflare Workers
    (大陆测速)              (国外测速)
         │                           │
         └─────────────┬─────────────┘
                       │
                ┌──────▼──────┐
                │ 合并结果    │
                └──────┬───────┘
                       │
                ┌──────▼──────────┐
                │ Supabase 数据库  │
                └──────┬───────────┘
                       │
                ┌──────▼──────────┐
                │ 前端网页        │
                └─────────────────┘
```

---

## 🚀 快速开始

### 前置条件
- GitHub 仓库已配置
- Aliyun FC 已部署
- Supabase 项目已创建
- Cloudflare 账号

### 3 分钟快速启动

**第 1 步: 部署 Cloudflare Worker**
```bash
1. 访问 https://dash.cloudflare.com
2. Workers and Pages → Create a Worker
3. 复制粘贴 cloudflare_worker.js 内容
4. 保存 Worker URL
```

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
| [NODE_LIFECYCLE.md](./NODE_LIFECYCLE.md) | **🔄 节点管理系统** - 去重、TTL、验证、清理 |
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
