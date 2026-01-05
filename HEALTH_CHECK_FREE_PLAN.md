# 健康检测 - 免费方案

## 问题
Vercel Cron Jobs 仅在 **Pro 及以上付费计划** 支持，Hobby 免费计划不可用。

## 解决方案

### 方案一：手动触发（推荐用于测试）
点击前端页面顶部的 **「🏥 健康检测」** 按钮，手动触发一次全局检测。

**优点：**
- ✅ 完全免费
- ✅ 无需额外配置
- ✅ 随时可用

**缺点：**
- ❌ 需要手动触发
- ❌ 无法定时自动检测

---

### 方案二：使用免费 Cron 服务（推荐用于生产环境）

#### 使用 cron-job.org（完全免费）

1. **访问网站**
   - 打开 https://cron-job.org
   - 注册免费账户

2. **创建新的 Cron Job**
   - 点击 "Create Cronjob"
   - 填写以下配置：

   ```
   Title: Node Health Check
   
   URL: https://your-domain.vercel.app/api/health-check
   
   Method: POST
   
   Schedule: Every 30 minutes
   (或任意你想要的频率)
   
   Authentication: None
   ```

3. **请求体（Body）**
   ```json
   {
     "check_all": true,
     "batch_size": 50
   }
   ```

4. **设置频率**
   - Free 计划：最少间隔 **5 分钟**
   - 推荐：**30 分钟一次**（同原计划）

5. **保存并激活**
   - 点击 "Create Cronjob"
   - 状态显示为 "OK" 表示配置成功

#### 验证工作状态
访问 `/api/health-check/stats` 检查最后的检测时间：
```
https://your-domain.vercel.app/api/health-check/stats
```

---

### 方案三：其他免费服务

| 服务 | 最小间隔 | 免费额度 | 优点 |
|------|---------|--------|------|
| **cron-job.org** | 5分钟 | 无限 | ⭐ 完全免费，无需账户登录 |
| **EasyCron** | 1分钟 | 50次/月 | 更频繁的检测，但需要验证域名 |
| **IFTTT** | 15分钟 | 无限 | 可与其他服务集成 |

---

## 当前配置状态

### ✅ 已完成
- [x] 后端 API `/api/health-check` 支持手动触发
- [x] 前端「🏥 健康检测」按钮实现
- [x] 数据库字段已准备（status, last_health_check, health_latency）
- [x] 移除了 Vercel Cron 配置（免费计划不支持）

### 🔧 下一步
1. **选择方案**
   - 仅测试开发：使用方案一（手动按钮）
   - 生产环境：使用方案二（cron-job.org）

2. **配置 Supabase SQL 迁移**
   ```sql
   -- 在 Supabase SQL Editor 中执行 HEALTH_CHECK_MIGRATION.sql
   ```

3. **部署到 Vercel**
   ```bash
   git push origin dev
   # Vercel 会自动部署
   ```

---

## API 文档

### POST /api/health-check
**手动触发健康检测**

**请求体：**
```json
{
  "check_all": true,
  "batch_size": 50
}
```

**响应：**
```json
{
  "status": "success",
  "data": {
    "total": 100,
    "online": 85,
    "offline": 10,
    "suspect": 5,
    "problem_nodes": [...]
  },
  "timestamp": "2026-01-04T10:30:00"
}
```

### GET /api/health-check/stats
**获取统计信息**

**响应：**
```json
{
  "total": 100,
  "online": 85,
  "offline": 10,
  "suspect": 5
}
```

---

## 成本对比

| 方案 | 成本 | 维护 | 自动化 |
|------|------|------|--------|
| 手动按钮 | 🟢 ¥0 | 🟢 无 | 🔴 无 |
| cron-job.org | 🟢 ¥0 | 🟢 简单 | 🟢 完全 |
| Vercel Pro | 🔴 ¥20/月 | 🟢 内置 | 🟢 完全 |

**推荐：** 使用 cron-job.org（完全免费 + 完全自动化）

---

## 故障排查

### Cron Job 无法触发？
1. 检查 cron-job.org 控制面板的 "Execution logs"
2. 确保 URL 正确：`https://your-domain.vercel.app/api/health-check`
3. 确保请求方法为 POST
4. 检查 Vercel 日志：`vercel logs <project-name>`

### 检测失败？
- 检查 health_checker.py 是否部署
- 查看 Vercel 部署日志中的错误信息
- 确认 Supabase 连接正常

---

## 相关文件
- `app_fastapi.py` - 后端 API 实现
- `health_checker.py` - 健康检测逻辑
- `frontend/src/components/HealthCheckModal.vue` - 前端 UI
- `HEALTH_CHECK_MIGRATION.sql` - 数据库迁移脚本
