# 🔥 生产部署配置指南

## 问题诊断
线上 `api.996828.xyz` 返回 404 错误，因为：
1. ✅ **前端正确配置**：已在 `index.html` 中配置 `VIPER_API_BASE` 环境变量
2. ❌ **后端未部署**：viper-node-store FastAPI 后端没有部署到线上

## 解决方案

### 方案 A：部署 FastAPI 后端到线上（推荐）

#### 选项 A1：使用 Vercel 的 Serverless Functions
这是最简单的方式，可以直接在 Vercel 上部署 Python 后端。

1. **创建 `/api/` 目录结构**：
   ```
   viper-node-store/
   ├── api/
   │   ├── sync-info.py
   │   ├── nodes/
   │   │   ├── precision-test.py
   │   │   └── latency-test.py
   │   └── ...
   └── ...
   ```

2. **安装 Vercel CLI**：
   ```bash
   npm i -g vercel
   ```

3. **部署**：
   ```bash
   vercel deploy --prod
   ```

#### 选项 A2：部署到独立平台（Render / Railway / Fly.io）
1. 选择平台（推荐 Render 或 Railway，因为免费额度足够）
2. 连接 GitHub 仓库
3. 设置环境变量：
   - `SPIDERFLOW_API_URL=http://localhost:8001` （如果需要）
4. 获取部署 URL，例如 `https://viper-api.onrender.com`
5. **更新 Vercel 环境变量**：
   - 在 Vercel Dashboard 设置 `VIPER_API_BASE=https://viper-api.onrender.com`
   - 或在 `vercel.json` 的 `rewrites` 中指向该 URL

#### 选项 A3：在你的 VPS 或云服务器上部署
1. SSH 连接到服务器
2. 克隆仓库
3. 安装依赖：`pip3 install -r requirements.txt`
4. 启动：`python3 app_fastapi.py`
5. 使用 Nginx 反向代理指向 8002 端口
6. 配置 SSL/TLS（使用 Let's Encrypt）

### 方案 B：使用 vercel.json 转发（临时方案，不推荐）

如果你已有后端部署在某个地方，编辑 `vercel.json`：
```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://your-backend-url/api/:path*"
    }
  ]
}
```

## 本地开发

### 启动后端服务
```bash
# 进入项目目录
cd viper-node-store

# 启动 FastAPI 后端（8002 端口）
bash scripts/start-backend.sh

# 或直接运行
python3 app_fastapi.py
```

### 启动前端
```bash
# 打开 index.html 在本地服务器
# 方式 1：Python 简单服务器
python3 -m http.server 8000

# 方式 2：使用 Live Server 插件（VS Code）
# 右键 index.html -> Open with Live Server
```

### 验证本地连接
```bash
# 测试 /api/sync-info
curl http://localhost:8002/api/sync-info

# 测试精确测速
curl -X POST http://localhost:8002/api/nodes/precision-test \
  -H "Content-Type: application/json" \
  -d '{"proxy_url":"test","test_file_size":10}'
```

## 环境变量配置

### 本地开发
- `VIPER_API_BASE`：自动检测为 `http://localhost:8002`
- `SPIDERFLOW_API_URL`：默认 `http://localhost:8001`（需要 SpiderFlow 后端运行）

### 线上部署（Vercel）
在 Vercel Dashboard 设置以下环境变量：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `VIPER_API_BASE` | `https://你的后端URL` | API 基础 URL |
| `SPIDERFLOW_API_URL` | `https://spiderflow后端URL` | SpiderFlow 后端地址 |

## 故障排除

### 症状：GET /api/sync-info 404
**原因**：后端未部署或路由不存在
**解决**：
1. 检查后端是否启动：`curl http://localhost:8002/api/sync-info`
2. 如果是线上，检查 Vercel 环境变量和转发规则

### 症状：POST /api/nodes/precision-test 404
**原因**：同上
**解决**：重启后端，检查路由是否注册

### 症状：GET /api/system/stats 连接被拒绝
**原因**：
1. 后端未启动
2. 前端使用了硬编码的 `localhost:8002` 地址（已修复）

**解决**：
1. 启动后端
2. 确保前端使用 `VIPER_API_BASE` 变量

## 部署检查清单

- [ ] 前端部署到 Vercel
- [ ] 后端部署到 Render/Railway/自建服务器
- [ ] Vercel 环境变量已设置 `VIPER_API_BASE`
- [ ] `vercel.json` 中的 rewrites 指向正确的后端 URL
- [ ] 测试 `/api/sync-info` 端点返回 200
- [ ] 测试 `/api/nodes/precision-test` 端点返回 200
- [ ] SpiderFlow 后端正常运行（如果需要）
- [ ] 检查浏览器控制台没有 CORS 错误

## 下一步建议

1. **立即**：启动本地后端验证功能
2. **短期**：部署后端到线上（Render 最简单）
3. **长期**：考虑 Serverless Functions（更经济）

---

**修改日期**：2026-01-01
**维护人**：AI Assistant
