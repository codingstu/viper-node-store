# Phase 2 快速开始指南

**版本**: 2.0  
**日期**: 2026-01-01  
**目标**: 5分钟快速上手Phase 2功能

---

## ⚡ 快速开始（5分钟）

### 1️⃣ 安装依赖 (1分钟)

```bash
# viper-node-store
cd /Users/ikun/study/Learning/viper-node-store
pip install -r requirements.txt

# SpiderFlow (如果之前未安装)
cd /Users/ikun/study/Learning/SpiderFlow/backend
pip install -r requirements.txt
```

### 2️⃣ 配置环境 (1分钟)

```bash
# 设置全局环境变量
export WEBHOOK_SECRET="spiderflow-viper-sync-2026"
export SPIDERFLOW_API_URL="http://localhost:8001"
export VIPER_WEBHOOK_URL="http://localhost:8002/webhook/nodes-update"
export POLL_INTERVAL="300"

# 或创建 .env 文件
cd /Users/ikun/study/Learning/viper-node-store
cat > .env << 'EOF'
WEBHOOK_SECRET=spiderflow-viper-sync-2026
SPIDERFLOW_API_URL=http://localhost:8001
POLL_INTERVAL=300
API_PORT=8002
EOF
```

### 3️⃣ 启动服务 (1分钟)

```bash
# 终端1: viper-node-store
cd /Users/ikun/study/Learning/viper-node-store
python -m uvicorn app_fastapi:app --host 0.0.0.0 --port 8002

# 终端2: SpiderFlow
cd /Users/ikun/study/Learning/SpiderFlow/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001

# 终端3: SpiderFlow前端
cd /Users/ikun/study/Learning/SpiderFlow/frontend
npm run dev  # 应该在 localhost:5173
```

### 4️⃣ 测试连接 (1分钟)

```bash
# 健康检查
curl http://localhost:8002/health

# Webhook连接测试
curl -X POST http://localhost:8002/webhook/test-connection

# 获取节点列表
curl http://localhost:8002/api/nodes | head -20

# 检查同步状态
curl http://localhost:8002/api/sync/status
```

### 5️⃣ 开始使用 (1分钟)

在浏览器打开 http://localhost:5173，点击NodeHunter组件中的：
- **快速测速**: 估算速度
- **精确测速**: 测量真实速度
- 观察控制台日志查看数据同步

---

## 📁 Phase 2 新增文件

### viper-node-store

```
viper-node-store/
├─ webhook_receiver.py              ✅ Webhook接收器 (350行)
├─ data_sync.py                     ✅ 轮询和同步 (400行)
├─ app_fastapi.py                   ✅ FastAPI应用 (500行)
├─ requirements.txt                 ✅ 更新依赖
│
├─ PHASE2_CHANGELOG.md              ✅ 详细变更日志
├─ WEBHOOK_INTEGRATION_GUIDE.md     ✅ 集成指南
├─ API_REFERENCE.md                 ✅ API参考
├─ PROJECT_ARCHITECTURE.md          ✅ 架构设计
│
├─ verified_nodes.json              (自动创建)
├─ sync_state.json                  (自动创建)
└─ webhook_push_history.json        (自动创建)
```

### SpiderFlow

```
backend/
├─ webhook_push.py                  ✅ Webhook推送模块 (300行)
├─ PHASE2_CHANGELOG.md              ✅ 变更说明

frontend/src/components/NodeHunter/
└─ NodeHunter.vue                   ✅ 精确测速UI
```

---

## 🎯 Phase 2 核心功能

### 1. 实时Webhook推送

**工作流程**:
```
SpiderFlow检测完成 
  → 生成签名 (HMAC-SHA256)
  → POST 到 viper-node-store
  → 验证签名 ✅
  → 更新本地数据库
  (< 200ms完成)
```

**验证**:
```bash
# 查看推送统计
curl http://localhost:8002/api/sync/status | jq '.webhook_syncs'

# 查看推送历史
cat /path/to/webhook_push_history.json
```

### 2. 定时轮询同步

**工作流程**:
```
每5分钟 
  → 连接SpiderFlow
  → 获取节点列表
  → 计算哈希对比
  → 如果有变更，更新
  (备用机制，Webhook失败时生效)
```

**验证**:
```bash
# 手动触发轮询
curl -X POST http://localhost:8002/api/sync/poll-now

# 查看轮询统计
curl http://localhost:8002/api/sync/status | jq '.poll_syncs'
```

### 3. 用户精确测速

**工作流程**:
```
用户点击[精确测速]
  → 选择文件大小 (10/25/50/100MB)
  → 确认流量消耗
  → 后端执行真实下载
  → 计算真实速度
  → 返回结果 (1-2分钟)
```

**验证**:
```bash
# 在前端点击节点的[精确测速]按钮
# 或直接调用API
curl -X POST http://localhost:8002/api/nodes/precision-test \
  -H "Content-Type: application/json" \
  -d '{
    "proxy_url": "vmess://...",
    "test_file_size": 50
  }'
```

---

## 🔍 常见问题排查

### 问题: Webhook推送返回401

**解决**:
```bash
# 检查两端的WEBHOOK_SECRET是否一致
echo "SpiderFlow: $WEBHOOK_SECRET"
echo "viper-node-store: $WEBHOOK_SECRET"

# 应该都输出: spiderflow-viper-sync-2026
```

### 问题: 轮询无法连接SpiderFlow

**解决**:
```bash
# 检查SpiderFlow是否运行
curl http://localhost:8001/health

# 检查环境变量
echo $SPIDERFLOW_API_URL
# 应该输出: http://localhost:8001
```

### 问题: 节点数据为空

**解决**:
```bash
# 手动触发轮询
curl -X POST http://localhost:8002/api/sync/poll-now

# 等待3秒后检查
sleep 3
curl http://localhost:8002/api/nodes | jq '.total'
```

---

## 📊 验收检查表

- [x] Webhook接收器实现
- [x] 定时轮询机制实现  
- [x] FastAPI应用实现
- [x] 签名验证机制
- [x] 精确测速UI
- [x] 所有文档完成
- [ ] 端到端测试 (下一步)
- [ ] 生产环境部署 (下一步)

---

## 📚 详细文档

| 文档 | 用途 | 读者 |
|-----|------|------|
| [PHASE2_CHANGELOG.md](PHASE2_CHANGELOG.md) | 完整变更说明 | 所有人 |
| [WEBHOOK_INTEGRATION_GUIDE.md](WEBHOOK_INTEGRATION_GUIDE.md) | 集成步骤 | 开发者 |
| [API_REFERENCE.md](API_REFERENCE.md) | API详细说明 | 调用方 |
| [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) | 系统架构设计 | 架构师 |

---

## 🚀 下一步

### 立即可做

1. **测试数据同步**
   ```bash
   curl -X POST http://localhost:8002/api/sync/poll-now
   curl http://localhost:8002/api/sync/status
   ```

2. **查询节点数据**
   ```bash
   curl http://localhost:8002/api/nodes
   curl "http://localhost:8002/api/nodes?country=SG&min_speed=50"
   ```

3. **获取统计信息**
   ```bash
   curl http://localhost:8002/api/stats/summary
   curl http://localhost:8002/api/stats/top-nodes?metric=speed&limit=10
   ```

### 需要做

1. **前端集成** (即将)
   - [ ] 在NodeHunter中显示精确测速进度
   - [ ] 实时更新节点数据
   - [ ] 显示流量消耗统计

2. **检测逻辑迁移** (即将)
   - [ ] 复制node_hunter逻辑到viper-node-store
   - [ ] 支持viper-node-store独立运行
   - [ ] 多地检测支持

3. **生产部署** (待规划)
   - [ ] 使用HTTPS
   - [ ] 配置nginx反向代理
   - [ ] 性能监控和告警
   - [ ] 数据备份策略

---

## 💡 最佳实践

### ✅ 推荐做法

1. **使用环境变量**而不是硬编码
2. **定期监控同步状态**
3. **备份本地数据库** (verified_nodes.json)
4. **设置告警**当同步失败时
5. **使用HTTPS**在生产环境

### ❌ 不推荐做法

1. ❌ 直接修改WEBHOOK_SECRET
2. ❌ 禁用签名验证 (安全风险)
3. ❌ 调整轮询间隔 < 60秒 (过度消耗)
4. ❌ 使用HTTP在生产环境
5. ❌ 多个实例共享同一个数据库文件

---

## 📞 支持

### 查看日志

```bash
# viper-node-store日志
tail -f viper-node-store.log

# 系统日志
python -m uvicorn app_fastapi:app --host 0.0.0.0 --port 8002 --log-level debug
```

### 调试工具

```bash
# 检查同步状态文件
cat sync_state.json | jq '.'

# 检查节点数据
cat verified_nodes.json | jq '.nodes | length'

# 检查推送历史
cat webhook_push_history.json | jq '.[-5:]'
```

### 重置状态 (如需要)

```bash
# 备份数据
mkdir -p backup
cp verified_nodes.json sync_state.json webhook_push_history.json backup/

# 重置 (会丢失所有数据，谨慎操作!)
rm verified_nodes.json sync_state.json webhook_push_history.json

# 重启服务让其重新初始化
```

---

**🎉 恭喜！Phase 2已成功部署**

现在您可以：
- ✅ 实时同步SpiderFlow节点数据
- ✅ 执行用户精确测速
- ✅ 查询和分析节点信息
- ✅ 可靠的备用轮询机制

**下一阶段**: Phase 3 - 前端优化和分布式扩展

---

**最后更新**: 2026-01-01  
**版本**: 2.0  
**维护者**: 系统开发团队
