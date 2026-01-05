# Webhook集成指南

**版本**: 1.0  
**日期**: 2026-01-01  
**目标受众**: 开发者、部署工程师

---

## 📖 目录

1. [概述](#概述)
2. [安装和配置](#安装和配置)
3. [集成步骤](#集成步骤)
4. [测试和验证](#测试和验证)
5. [故障排除](#故障排除)
6. [最佳实践](#最佳实践)

---

## 概述

### 什么是Webhook集成？

Webhook是一种实时数据推送机制，允许SpiderFlow在完成节点检测后立即将数据推送到viper-node-store。

```
事件 → 触发 → 推送 → 接收 → 更新
检测完成 → Webhook → POST请求 → 验证签名 → 数据库更新
```

### 为什么需要Webhook？

| 功能 | 必要性 | 优势 |
|-----|--------|------|
| 实时同步 | ✅ 必需 | 数据延迟 < 200ms |
| 低流量 | ✅ 必需 | 仅变更时推送 |
| 可靠性 | ✅ 必需 | 支持失败重试 |
| 安全性 | ✅ 必需 | HMAC-SHA256签名验证 |

---

## 安装和配置

### 前置条件

- Python 3.8+
- FastAPI 0.104+
- uvicorn 0.24+
- APScheduler 3.10+
- aiohttp 3.9+

### 步骤1: 安装viper-node-store

```bash
cd /Users/ikun/study/Learning/viper-node-store

# 安装依赖
pip install -r requirements.txt

# 验证安装
python -c "from webhook_receiver import webhook_router; print('✅ Webhook模块已安装')"
```

### 步骤2: 配置共享密钥

```bash
# 设置环境变量 (两端必须相同)
export WEBHOOK_SECRET="spiderflow-viper-sync-2026"

# 或创建 .env 文件
cat > /Users/ikun/study/Learning/viper-node-store/.env << 'EOF'
WEBHOOK_SECRET=spiderflow-viper-sync-2026
SPIDERFLOW_API_URL=http://localhost:8001
POLL_INTERVAL=300
API_PORT=8002
EOF

# 验证
echo $WEBHOOK_SECRET
# 应输出: spiderflow-viper-sync-2026
```

### 步骤3: 启动viper-node-store服务

```bash
cd /Users/ikun/study/Learning/viper-node-store

# 启动API服务
python -m uvicorn app_fastapi:app --host 0.0.0.0 --port 8002

# 输出应包含:
# ✅ viper-node-store 启动完成
# 🚀 启动数据同步调度器
```

### 步骤4: 在SpiderFlow中集成

```bash
cd /Users/ikun/study/Learning/SpiderFlow/backend

# 确保webhook_push.py已存在
ls webhook_push.py

# 检查SpiderFlow的node_hunter.py
grep -n "push_nodes_to_viper" app/modules/node_hunter/node_hunter.py

# 如果不存在，需要添加导入和调用
```

---

## 集成步骤

### 步骤1: 在SpiderFlow中导入Webhook模块

编辑 `SpiderFlow/backend/app/modules/node_hunter/node_hunter.py`:

```python
# 在文件顶部的导入区添加
from webhook_push import push_nodes_to_viper, test_webhook_connection

# 在logger配置后添加
logger.info("✅ Webhook推送模块已加载")
```

### 步骤2: 在检测完成后调用推送

在node_hunter.py的检测完成位置添加：

```python
# 假设检测完成后有这样的代码:
# verified_nodes = [...]  # 验证通过的节点列表
# total_count = 150
# verified_count = len(verified_nodes)

# 添加Webhook推送 (在background_tasks中)
background_tasks.add_task(
    push_nodes_to_viper,
    nodes=verified_nodes,
    event_type="batch_test_complete",
    total_count=total_count,
    verified_count=verified_count
)
```

**完整示例**:

```python
@router.post("/batch-test")
async def batch_test_nodes(
    nodes_data: List[NodeData],
    background_tasks: BackgroundTasks
):
    """批量测试节点"""
    
    # 执行检测
    verified_nodes = await run_node_tests(nodes_data)
    
    # 1. 保存到本地
    save_to_local_db(verified_nodes)
    
    # 2. 推送到viper-node-store (新增)
    background_tasks.add_task(
        push_nodes_to_viper,
        nodes=verified_nodes,
        event_type="batch_test_complete",
        total_count=len(nodes_data),
        verified_count=len(verified_nodes)
    )
    
    return {"status": "success", "verified": len(verified_nodes)}
```

### 步骤3: 配置SpiderFlow的环境变量

编辑 `SpiderFlow/backend/.env`:

```env
# Webhook推送配置
WEBHOOK_SECRET=spiderflow-viper-sync-2026
VIPER_WEBHOOK_URL=http://localhost:8002/webhook/nodes-update

# 其他配置...
```

### 步骤4: 启动SpiderFlow API

```bash
cd /Users/ikun/study/Learning/SpiderFlow/backend

# 设置环境变量
export WEBHOOK_SECRET="spiderflow-viper-sync-2026"
export VIPER_WEBHOOK_URL="http://localhost:8002/webhook/nodes-update"

# 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

---

## 测试和验证

### 测试1: 连接测试

```bash
# 测试Webhook连接
curl -X POST http://localhost:8002/webhook/test-connection

# 预期输出:
# {
#   "status": "connected",
#   "receiver": "viper-node-store",
#   "webhook_version": "1.0",
#   "timestamp": "2026-01-01T..."
# }
```

### 测试2: 签名生成和验证

```bash
# 使用Python脚本测试签名
python << 'EOF'
from webhook_push import generate_webhook_signature, verify_webhook_signature
import json
import os

# 生成签名
os.environ['WEBHOOK_SECRET'] = 'spiderflow-viper-sync-2026'

payload = {"test": "data", "nodes": []}
timestamp, signature = generate_webhook_signature(payload)

print(f"✅ 生成签名成功")
print(f"   Timestamp: {timestamp}")
print(f"   Signature: {signature[:16]}...")

# 验证签名
payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
is_valid = verify_webhook_signature(payload_str, timestamp, signature)
print(f"✅ 签名验证: {'有效' if is_valid else '无效'}")

EOF
```

### 测试3: 手动推送测试数据

```bash
# 方法1: 使用Python脚本
python << 'EOF'
import asyncio
from webhook_push import test_webhook_push

async def main():
    success = await test_webhook_push()
    print(f"测试推送结果: {'✅ 成功' if success else '❌ 失败'}")

asyncio.run(main())
EOF

# 方法2: 使用curl (需要手动生成签名)
curl -X POST http://localhost:8002/webhook/nodes-update \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "test_push",
    "timestamp": "2026-01-01T12:00:00Z",
    "nodes": [
      {
        "url": "vmess://test@example.com",
        "name": "Test Node",
        "country": "SG",
        "latency": 100,
        "speed": 50,
        "availability": 95,
        "protocol": "vmess"
      }
    ],
    "signature": "your-signature-here"
  }'
```

### 测试4: 检查同步状态

```bash
# 获取当前同步状态
curl http://localhost:8002/api/sync/status

# 预期输出示例:
# {
#   "total_nodes": 145,
#   "last_synced_at": "2026-01-01T12:05:00",
#   "sync_method": "webhook",
#   "webhook_syncs": 5,
#   "poll_syncs": 0,
#   "total_syncs": 5
# }
```

### 测试5: 查看推送历史

```bash
# 获取推送统计
python << 'EOF'
from webhook_push import get_push_statistics, get_push_history

# 显示统计
stats = get_push_statistics()
print("推送统计:")
for key, value in stats.items():
    print(f"  {key}: {value}")

# 显示最近推送
print("\n最近10条推送:")
for item in get_push_history(limit=10):
    print(f"  {item['timestamp']} - {item['status']} ({item['nodes_count']}个节点)")

EOF
```

---

## 故障排除

### 问题1: Webhook推送返回401 Unauthorized

**症状**:
```
❌ Webhook返回错误状态 401 | 签名验证失败
```

**原因**: 签名验证失败，通常是WEBHOOK_SECRET不匹配

**诊断**:
```bash
# 检查SpiderFlow的WEBHOOK_SECRET
echo "SpiderFlow SECRET: $WEBHOOK_SECRET"

# 检查代码中的配置
grep -n "WEBHOOK_SECRET" SpiderFlow/backend/webhook_push.py
grep -n "WEBHOOK_SECRET" viper-node-store/webhook_receiver.py

# 验证两端设置是否一致
if [ "$(echo $WEBHOOK_SECRET)" = "spiderflow-viper-sync-2026" ]; then
    echo "✅ 环境变量设置正确"
else
    echo "❌ 环境变量不匹配"
fi
```

**解决**:
```bash
# 确保两端设置相同的密钥
export WEBHOOK_SECRET="spiderflow-viper-sync-2026"

# 重启两个服务
# SpiderFlow
pkill -f "python.*app.main"
sleep 2
cd SpiderFlow/backend && python -m uvicorn app.main:app --port 8001 &

# viper-node-store
pkill -f "uvicorn app_fastapi"
sleep 2
cd viper-node-store && python -m uvicorn app_fastapi:app --port 8002 &

# 重新测试
python webhook_push.py test_webhook_push()
```

### 问题2: 网络连接超时

**症状**:
```
❌ Webhook连接失败: [Errno -3] Try again
```

**原因**: 网络问题或viper-node-store未启动

**诊断**:
```bash
# 检查viper-node-store是否运行
lsof -i :8002

# 测试连接
curl -v http://localhost:8002/health

# 检查防火墙
sudo lsof -i TCP:8002
```

**解决**:
```bash
# 启动viper-node-store
cd /Users/ikun/study/Learning/viper-node-store
python -m uvicorn app_fastapi:app --host 0.0.0.0 --port 8002

# 等待启动完成
sleep 3

# 再次测试
curl http://localhost:8002/health
```

### 问题3: 轮询无法获取SpiderFlow数据

**症状**:
```
❌ 从SpiderFlow获取数据失败: Connection refused
```

**原因**: SpiderFlow API不可用或SPIDERFLOW_API_URL配置错误

**诊断**:
```bash
# 检查SpiderFlow是否运行
lsof -i :8001

# 检查配置的URL
echo $SPIDERFLOW_API_URL

# 测试连接
curl -v http://localhost:8001/health
```

**解决**:
```bash
# 启动SpiderFlow
cd /Users/ikun/study/Learning/SpiderFlow/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001

# 在viper-node-store中设置正确的URL
export SPIDERFLOW_API_URL="http://localhost:8001"

# 重启viper-node-store
pkill -f "uvicorn app_fastapi"
sleep 2
cd viper-node-store && python -m uvicorn app_fastapi:app --port 8002 &

# 手动触发轮询
curl -X POST http://localhost:8002/api/sync/poll-now
```

### 问题4: JSON数据文件损坏

**症状**:
```
加载节点文件失败: Expecting value: line 1 column 1 (char 0)
```

**原因**: verified_nodes.json文件损坏或为空

**诊断**:
```bash
# 检查文件大小
ls -lh verified_nodes.json

# 检查内容
head -20 verified_nodes.json

# 验证JSON格式
python -c "import json; json.load(open('verified_nodes.json'))"
```

**解决**:
```bash
# 备份损坏文件
cp verified_nodes.json verified_nodes.json.backup

# 删除损坏文件
rm verified_nodes.json

# 触发轮询重建
curl -X POST http://localhost:8002/api/sync/poll-now

# 验证恢复
curl http://localhost:8002/api/nodes | head -10
```

---

## 最佳实践

### 1. 错误处理

```python
# ✅ 推荐做法：在后台任务中执行
background_tasks.add_task(push_nodes_to_viper, nodes)

# ❌ 不推荐：阻塞主线程
await push_nodes_to_viper(nodes)
```

### 2. 监控和日志

```python
# 记录推送历史
from webhook_push import get_push_statistics

stats = get_push_statistics()
logger.info(f"推送统计: {stats['success_rate']}成功率")

# 监控轮询状态
from data_sync import get_sync_statistics

sync_stats = get_sync_statistics()
logger.info(f"同步状态: {sync_stats['total_nodes']}个节点")
```

### 3. 定期备份

```bash
# 定期备份本地数据库
0 2 * * * cp /path/to/verified_nodes.json /path/to/backup/verified_nodes.$(date +\%Y\%m\%d).json

# 定期清理推送历史 (保留最近1000条)
0 3 * * 0 python -c "from webhook_push import PushHistory; h = PushHistory.load()[-1000:]; PushHistory.save(h)"
```

### 4. 性能优化

```python
# 批量推送而不是单个推送
# ✅ 推荐
background_tasks.add_task(push_nodes_to_viper, all_nodes, "batch_test_complete")

# ❌ 不推荐 (多个任务阻塞)
for node in nodes:
    background_tasks.add_task(push_single_node, node)
```

### 5. 安全建议

```bash
# 1. 定期更换WEBHOOK_SECRET
# 每月更换一次，更新两端配置

# 2. 使用HTTPS (生产环境)
VIPER_WEBHOOK_URL=https://yourdomain.com/webhook/nodes-update

# 3. 限制访问
# 只允许特定IP推送
# 在nginx或firewall中配置

# 4. 监控异常
# 记录所有401/403错误
# 设置告警
```

---

## 📞 获取帮助

### 常见问题解答

**Q: Webhook可以从云环境推送到本地吗？**  
A: 不行，需要内网或使用反向代理。可以使用Cloudflare Tunnel或ngrok。

**Q: 推送失败会丢失数据吗？**  
A: 不会，轮询机制会在5分钟内兜底同步。

**Q: 是否可以修改轮询间隔？**  
A: 可以，设置环境变量 `POLL_INTERVAL=600` (单位:秒)。

**Q: 签名可以跳过验证吗？**  
A: 不推荐，但可以注释掉验证代码（仅用于测试）。

### 联系方式

- 问题报告: 创建Issue或检查日志
- 性能优化: 调整POLL_INTERVAL或批量推送策略
- 安全咨询: 更新WEBHOOK_SECRET或使用HTTPS

---

**文档版本**: 1.0  
**最后更新**: 2026-01-01  
**适用版本**: viper-node-store 2.0+, SpiderFlow 5.0+
