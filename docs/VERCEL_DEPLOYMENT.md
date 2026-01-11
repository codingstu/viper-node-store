# Vercel 部署配置指南

## 概述

本项目已适配 Vercel serverless 部署。后端使用 FastAPI，前端使用 Vue.js。

## 当前配置

### vercel.json
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    },
    {
      "src": "frontend/package.json",
      "use": "@vercel/static-build",
      "config": {
        "buildCommand": "npm run build",
        "outputDirectory": "dist"
      }
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "/api/index.py"
    },
    {
      "src": "/(.*)",
      "dest": "/frontend/$1"
    }
  ]
}
```

### api/index.py
```python
from backend.main import app
# Vercel serverless function 入口
```

## 环境变量设置

在 Vercel Dashboard 中设置以下环境变量：

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
```

## 部署步骤

1. **推送代码到 GitHub**
   ```bash
   git add .
   git commit -m "feat: Update Vercel configuration for modular backend"
   git push origin main
   ```

2. **连接 Vercel 项目**
   - 在 Vercel Dashboard 中导入 GitHub 仓库
   - 自动检测配置并部署

3. **验证部署**
   - 前端: https://your-domain.vercel.app
   - API: https://your-domain.vercel.app/api/status

## 注意事项

### Serverless 限制
- 每次请求都是独立的冷启动
- 执行时间限制为 10 秒（Hobby 计划）
- 定时任务（APScheduler）在 serverless 环境中不会运行
- 需要通过外部服务（如 Vercel Cron）实现定时任务

### 性能优化
- 启用 Vercel 的缓存功能
- 考虑使用 Redis 或其他缓存服务
- 监控冷启动时间

### 故障排除
- 检查 Vercel 构建日志
- 验证环境变量设置
- 测试 API 端点响应

## 相关文档
- [Vercel Python 运行时](https://vercel.com/docs/concepts/functions/serverless-functions/runtimes/python)
- [FastAPI 部署到 Vercel](https://fastapi.tiangolo.com/deployment/)