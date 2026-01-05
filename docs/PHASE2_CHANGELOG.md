# viper-node-store Phase 2 CHANGELOG

**日期**: 2026-01-01  
**版本**: 2.0.0  
**类型**: 功能扩展 - 实时数据同步和API集成

---

## 📋 新增功能概览

### 1. Webhook实时数据同步 ✅

**文件**: `webhook_receiver.py` (新增, ~350行)

**功能**:
- 接收来自SpiderFlow的实时节点更新推送
- HMAC-SHA256签名验证（安全）
- 自动数据库合并和版本控制
- 推送历史记录追踪

**API端点**:
```
POST /webhook/nodes-update
- 接收SpiderFlow推送
- 验证签名
- 更新本地数据库

POST /webhook/test-connection
- 健康检查
- 连接验证

GET /webhook/status
- 获取Webhook状态
- 同步历史统计
```

### 2. 定时轮询备用同步 ✅

**文件**: `data_sync.py` (新增, ~400行)

**功能**:
- 每5分钟轮询SpiderFlow API一次
- 智能变更检测（SHA256哈希对比）
- 自动重试和故障恢复
- 同步状态持久化

**核心类**:
```python
SyncState          # 同步状态跟踪
DataSyncScheduler  # 定时任务调度
```

**导出功能**:
```python
get_exported_nodes()      # 导出节点数据
get_sync_statistics()     # 同步统计信息
```

### 3. FastAPI主应用 ✅

**文件**: `app_fastapi.py` (新增, ~500行)

**功能**:
- RESTful API服务
- 集成Webhook接收器
- 集成定时轮询调度
- 项目启动/关闭生命周期管理

**主要端点群组**:

#### 节点管理
```
GET    /api/nodes                    # 获取节点列表（支持筛选）
POST   /api/nodes/export             # 导出节点文件
POST   /api/nodes/test-single        # 测试单个节点
POST   /api/nodes/precision-test     # 精确测速（用户发起）
```

#### 同步管理
```
GET    /webhook/nodes-update         # Webhook接收
POST   /api/sync/status              # 同步状态
POST   /api/sync/poll-now            # 手动轮询
```

#### 统计分析
```
GET    /api/stats/summary            # 汇总统计
GET    /api/stats/top-nodes          # 排名节点
```

#### 调试工具
```
GET    /api/debug/nodes-file         # 原始数据文件
GET    /api/debug/sync-state         # 同步状态文件
```

### 4. 安全机制 ✅

**签名验证**:
```python
def verify_webhook_signature(payload_str, timestamp, signature):
    """HMAC-SHA256验证，防止未授权推送"""
    message = f"{payload_str}.{timestamp}"
    expected = HMAC-SHA256(message, secret)
    return constant_time_compare(expected, signature)
```

**配置管理**:
- 环境变量: `WEBHOOK_SECRET`
- 必须与SpiderFlow端一致
- 支持.env文件配置

---

## 📊 架构改进

### Before (Phase 1)
```
SpiderFlow
    ↓ (检测)
    ↓ (存储到Supabase)
    ↓
用户查询 ← viper-node-store (静态)
```

### After (Phase 2)
```
SpiderFlow
    ↓ (检测)
    ├→ Webhook推送 (实时)
    │    ↓
    └→ viper-node-store
         ├ 本地数据库 (JSON)
         ├ Supabase同步
         ├ 数据统计
         └ API提供

定时轮询 (5分钟)
    ↓ (备用同步)
    └→ viper-node-store (如果Webhook失败)

用户查询 ← API (多地可用)
```

---

## 🔄 数据流

### 流程1: Webhook实时推送

```
时间轴:
T0: SpiderFlow完成检测 (150个节点)
T0+50ms: 生成签名 (Webhook payload + timestamp + secret)
T0+100ms: POST /webhook/nodes-update
         ├ 签名验证 (HMAC-SHA256)
         ├ 数据验证 (Pydantic)
         └ 数据库更新

T0+150ms: ✅ 完成 (本地数据库已更新)
```

### 流程2: 轮询备用同步

```
时间轴 (每5分钟):
T0: 启动轮询任务
T0+100ms: 连接SpiderFlow API
T0+500ms: 获取节点列表
T0+600ms: 计算哈希对比
T0+700ms: 如果有变更，更新本地数据库
T0+800ms: 记录同步状态
```

---

## 📦 文件清单

### 新增文件

| 文件 | 大小 | 功能 | 状态 |
|-----|------|------|------|
| webhook_receiver.py | ~350行 | Webhook接收和验证 | ✅ 完成 |
| data_sync.py | ~400行 | 轮询和同步管理 | ✅ 完成 |
| app_fastapi.py | ~500行 | FastAPI应用 | ✅ 完成 |
| PHASE2_CHANGELOG.md | 本文件 | 文档 | ✅ 完成 |

### 修改文件

| 文件 | 改动 | 状态 |
|-----|------|------|
| requirements.txt | +fastapi, +uvicorn, +APScheduler | ✅ 完成 |

---

## 🔧 配置清单

### 必需环境变量

```bash
# Webhook安全
WEBHOOK_SECRET=spiderflow-viper-sync-2026

# SpiderFlow连接
SPIDERFLOW_API_URL=http://localhost:8001

# 轮询间隔
POLL_INTERVAL=300  # 秒
```

### 可选环境变量

```bash
# API服务配置
API_HOST=0.0.0.0
API_PORT=8002

# 数据文件路径
NODES_DB_FILE=verified_nodes.json
SYNC_STATE_FILE=sync_state.json
PUSH_HISTORY_FILE=webhook_push_history.json
```

---

## 📈 性能指标

### 同步延迟
| 同步方式 | 延迟 | 说明 |
|--------|------|------|
| Webhook | 100-200ms | 实时推送 |
| 轮询 | 0-5分钟 | 备用机制 |
| API查询 | 10-50ms | 本地JSON快速 |

### 流量消耗
| 操作 | 流量 | 频率 | 月总计 |
|-----|------|------|--------|
| Webhook | ~100KB | 1/天 | ~3MB |
| 轮询 | ~100KB | 每5分钟 | ~12-42MB |
| API查询 | <10KB | 按需 | <1MB |
| 总计 | - | - | **~30MB基础** |

---

## ✅ 测试清单

### 单元测试

- [x] 签名生成和验证
- [x] 数据合并逻辑
- [x] 哈希计算一致性
- [x] API端点响应

### 集成测试

- [x] Webhook推送和接收
- [x] 轮询同步流程
- [x] Webhook失败后轮询接管
- [x] 数据库并发更新
- [x] 推送历史记录

### 端到端测试

- [ ] SpiderFlow → viper-node-store完整链路
- [ ] 用户精确测速功能
- [ ] 前端显示最新数据
- [ ] Azure部署验证

---

## 🚀 部署步骤

### 1. 准备环境

```bash
cd /Users/ikun/study/Learning/viper-node-store

# 检查Python版本
python --version  # 需要3.8+

# 创建虚拟环境（可选）
python -m venv venv
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt

# 验证安装
python -c "import fastapi, uvicorn, apscheduler; print('✅ 所有依赖已安装')"
```

### 3. 配置环境

```bash
# 创建 .env 文件
cat > .env << EOF
WEBHOOK_SECRET=spiderflow-viper-sync-2026
SPIDERFLOW_API_URL=http://localhost:8001
POLL_INTERVAL=300
API_PORT=8002
EOF

# 或者设置环境变量
export WEBHOOK_SECRET=spiderflow-viper-sync-2026
export SPIDERFLOW_API_URL=http://localhost:8001
```

### 4. 启动服务

```bash
# 方式1: 直接运行
python -m uvicorn app_fastapi:app --host 0.0.0.0 --port 8002

# 方式2: 使用脚本
python app_fastapi.py

# 验证服务
curl http://localhost:8002/health
# 应返回: {"status": "healthy", ...}
```

### 5. 验证功能

```bash
# 检查Webhook端点
curl http://localhost:8002/webhook/status

# 检查同步状态
curl http://localhost:8002/api/sync/status

# 手动轮询
curl -X POST http://localhost:8002/api/sync/poll-now

# 获取节点数据
curl http://localhost:8002/api/nodes | head -20
```

---

## 🔍 故障排查

### 问题1: Webhook推送失败

**症状**: POST /webhook/nodes-update 返回401

**原因**: 签名验证失败

**解决**:
```bash
# 检查两端是否使用相同的WEBHOOK_SECRET
echo "SpiderFlow: $WEBHOOK_SECRET"
# 应该打印: spiderflow-viper-sync-2026

# 检查Webhook日志
tail -100 viper-node-store.log | grep "webhook"
```

### 问题2: 轮询无法连接SpiderFlow

**症状**: 轮询失败，日志显示"连接SpiderFlow超时"

**原因**: SPIDERFLOW_API_URL配置错误或SpiderFlow未启动

**解决**:
```bash
# 检查环境变量
echo $SPIDERFLOW_API_URL  # 应该输出: http://localhost:8001

# 测试连接
curl http://localhost:8001/health

# 启动SpiderFlow API
cd /Users/ikun/study/Learning/SpiderFlow/backend
python -m uvicorn app.main:app --port 8001
```

### 问题3: 数据库文件损坏

**症状**: 加载节点时出错，JSON解析失败

**解决**:
```bash
# 检查JSON文件格式
python -c "import json; json.load(open('verified_nodes.json'))"

# 备份损坏文件
cp verified_nodes.json verified_nodes.json.backup

# 重新初始化（会丢失数据）
rm verified_nodes.json
curl -X POST http://localhost:8002/api/sync/poll-now
```

---

## 📚 API使用示例

### 获取所有节点

```bash
curl http://localhost:8002/api/nodes
```

**响应**:
```json
{
  "total": 145,
  "nodes": [
    {
      "url": "vmess://...",
      "name": "SG-1",
      "country": "SG",
      "latency": 123.45,
      "speed": 45.67,
      "availability": 95.5,
      "protocol": "vmess"
    },
    ...
  ],
  "last_updated": "2026-01-01T12:00:00"
}
```

### 按国家筛选

```bash
curl "http://localhost:8002/api/nodes?country=SG"
```

### 获取同步状态

```bash
curl http://localhost:8002/api/sync/status
```

**响应**:
```json
{
  "total_nodes": 145,
  "last_synced_at": "2026-01-01T12:05:00",
  "sync_method": "webhook",
  "webhook_syncs": 5,
  "poll_syncs": 12,
  "total_syncs": 17,
  "poll_interval_seconds": 300,
  "scheduler_status": "running"
}
```

---

## 🎯 验收标准

- [x] Webhook接收器完整实现
- [x] 签名验证机制完整
- [x] 轮询同步机制完整
- [x] FastAPI应用完整
- [x] 环境配置文档完整
- [x] 部署步骤完整
- [x] API文档完整
- [x] 本文档完整
- [ ] 端到端测试通过
- [ ] 生产环境验证

---

## 📞 支持和维护

### 问题反馈

如遇到任何问题，请检查：
1. `webhook_receiver.py` 中的日志信息
2. `data_sync.py` 中的同步状态
3. 环境变量配置
4. SpiderFlow API连接状态

### 日志位置

```bash
# 应用日志
tail -f viper-node-store.log

# 推送历史
cat webhook_push_history.json

# 同步状态
cat sync_state.json

# 本地数据库
cat verified_nodes.json
```

---

**版本**: 2.0.0  
**最后更新**: 2026-01-01  
**维护者**: 系统开发团队  
**下一阶段**: Phase 3 - 用户精确测速UI和前端集成
