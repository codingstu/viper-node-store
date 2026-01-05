# 🚀 节点管理系统 - 快速启动指南

## 📦 依赖检查

```bash
# 检查requirements.txt中是否包含必要的包
grep -E "APScheduler|aiohttp|fastapi" requirements.txt
```

**预期输出**:
```
APScheduler>=3.10.0
aiohttp>=3.9.0
fastapi>=0.104.0
```

✅ 所有依赖已在requirements.txt中

---

## 🔧 部署步骤

### 步骤1: 安装依赖
```bash
pip install -r requirements.txt
```

### 步骤2: 启动后端
```bash
# 启动FastAPI应用
python app_fastapi.py

# 或使用uvicorn
uvicorn app_fastapi:app --reload --host 0.0.0.0 --port 8002
```

**预期输出**:
```
✅ 启动数据同步调度器 | 轮询间隔: 300秒
✅ 节点验证定时器已启动 (每天2:00执行)
INFO:     Uvicorn running on http://0.0.0.0:8002
```

### 步骤3: 验证前端
```bash
# 打开浏览器访问
http://localhost:8002
```

**预期显示**:
- ✅ 同步状态横幅 (数据同步: 刚刚)
- ✅ 活跃节点数量
- ✅ 手动刷新按钮

---

## 🧪 功能测试

### 测试1: 去重功能
```bash
# 推送两个相同的节点
curl -X POST http://localhost:8002/webhook/nodes \
  -H "Content-Type: application/json" \
  -d '{
    "nodes": [
      {"protocol":"http", "host":"127.0.0.1", "port":8080},
      {"protocol":"http", "host":"127.0.0.1", "port":8080}
    ]
  }'
```

**预期结果**: 数据库中只保留1个节点

### 测试2: TTL管理
```bash
# 手动触发轮询
curl -X POST http://localhost:8002/api/sync/poll-now
```

**预期结果**: 日志显示去重和TTL管理信息

### 测试3: 同步信息API
```bash
curl http://localhost:8002/api/sync-info
```

**预期返回**:
```json
{
  "last_updated_at": "2024-01-15T14:45:23",
  "minutes_ago": 5,
  "nodes_count": 150,
  "active_count": 145,
  "source": "webhook",
  "needs_verification": 12
}
```

### 测试4: 前端实时刷新
```bash
# 打开浏览器开发者工具 (F12)
# 观察Network标签
# 验证每30秒调用 /api/sync-info
```

**预期行为**:
- ✅ 每30秒刷新一次
- ✅ 时间戳更新准确
- ✅ 显示 "X分钟前" 格式

---

## 📊 监控日志

### 关键日志信息

启动时:
```
🚀 启动数据同步调度器 | 轮询间隔: 300秒
✅ 节点验证定时器已启动 (每天2:00执行)
```

去重时:
```
✅ 去重完成 | 发现3个重复节点
📥 从SpiderFlow获取150个节点
🔀 合并结果 | 本地100 + 远程150 = 245个节点
```

验证时 (每天2:00):
```
🔄 开始定时节点验证任务 (每天2:00执行)
🔍 准备验证12个节点...
✅ 节点验证通过: http://127.0.0.1:8080
❌ 节点验证失败: http://proxy.example.com:8080
✅ 节点验证任务完成 | 总计245个 | 离线3个
```

---

## 🔍 故障排查

### 问题1: 定时验证未执行

**症状**: 日志无 "开始定时节点验证任务" 信息

**解决**:
1. 检查系统时间是否正确
2. 查看APScheduler是否启动:
   ```python
   # 在代码中检查
   scheduler.running  # 应该为True
   ```
3. 检查时区设置: `Asia/Shanghai`

### 问题2: 去重不工作

**症状**: 相同IP:端口出现多条

**解决**:
1. 检查节点protocol字段是否存在
2. 验证host格式: 应该全小写，无空格
3. 检查port是数字而非字符串

### 问题3: 前端未显示同步时间

**症状**: 同步状态显示 "加载失败"

**解决**:
1. 检查浏览器控制台错误
2. 验证 `/api/sync-info` 端点是否可访问
3. 检查CORS设置

---

## 📈 性能优化

### 调整验证间隔
```python
# data_sync.py 中修改
await asyncio.sleep(0.1)  # 改为 0.05 以加快速度
```

### 调整前端刷新频率
```javascript
// index.html 中修改
setTimeout(fetchSyncInfo, 30000);  // 改为 10000 (10秒)
```

### 调整TTL参数
```python
# 修改TTL天数
apply_node_lifecycle(nodes, ttl_days=2)  # 从3天改为2天

# 修改最大离线天数
apply_node_lifecycle(nodes, max_offline_days=5)  # 从7天改为5天
```

---

## 📚 完整文档

- **NODE_LIFECYCLE.md** - 完整的系统说明 (1500+行)
- **NODE_MANAGEMENT_CHANGELOG.md** - 实现细节 (600+行)
- **PROJECT_COMPLETION_REPORT.md** - 项目报告
- **README.md** - 项目总览

---

## ✅ 部署清单

- [ ] 后端代码无语法错误 (✅ 已验证)
- [ ] 前端代码无语法错误 (✅ 已验证)
- [ ] requirements.txt包含APScheduler (✅ 已验证)
- [ ] FastAPI应用启动成功
- [ ] APScheduler定时任务已启动
- [ ] 前端可正常加载
- [ ] /api/sync-info 端点可访问
- [ ] 去重功能正常工作
- [ ] TTL管理正常工作
- [ ] 定时验证任务正常执行

---

## 🎯 验证成功标志

✅ **当你看到以下信息时，说明部署成功**:

1. **后端日志**:
   ```
   🚀 启动数据同步调度器 | 轮询间隔: 300秒
   ✅ 节点验证定时器已启动 (每天2:00执行)
   ```

2. **前端显示**:
   ```
   ✅ 同步状态 | 数据同步: 刚刚 | 150个活跃节点 | 🔄刷新
   ```

3. **API测试**:
   ```bash
   curl http://localhost:8002/api/sync-info
   # 返回有效的JSON数据
   ```

4. **日志验证** (首次轮询):
   ```
   📥 从SpiderFlow获取X个节点
   ✅ 去重完成 | 发现Y个重复节点
   🔀 合并结果 | 总计Z个节点
   ✅ 轮询完成 | 活跃W个
   ```

---

## 📞 需要帮助?

- 📖 查看 [NODE_LIFECYCLE.md](./NODE_LIFECYCLE.md) 了解系统设计
- 🐛 查看"故障排查"章节解决问题
- 💬 查看"示例场景"了解工作流程

---

**🎉 部署完成，享受自动化的节点管理！**

*最后更新: 2024-01-15*  
*viper-node-store v1.0*
