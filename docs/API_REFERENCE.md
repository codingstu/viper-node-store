# API 参考文档 - Phase 2 更新

**版本**: 2.0  
**更新日期**: 2026-01-01  
**API文档级别**: v2

---

## 目录

1. [viper-node-store API](#viper-node-store-api)
2. [SpiderFlow Webhook API](#spiderflow-webhook-api)
3. [集成端点](#集成端点)
4. [错误处理](#错误处理)
5. [示例代码](#示例代码)

---

## viper-node-store API

### 基础信息

**基URL**: `http://localhost:8002`

**认证**: 暂无（内网环境）

**返回格式**: JSON

---

### 节点查询接口

#### GET /api/nodes

获取节点列表，支持多种过滤条件。

**请求参数**:

| 参数 | 类型 | 说明 | 示例 |
|-----|------|------|------|
| country | string | 国家代码筛选 | SG, JP, US |
| protocol | string | 协议筛选 | vmess, vless, ss |
| min_speed | float | 最小速度 (MB/s) | 50 |
| max_latency | int | 最大延迟 (ms) | 500 |
| format | string | 输出格式 | json, clash |

**请求示例**:

```bash
# 获取所有节点
curl http://localhost:8002/api/nodes

# 新加坡节点
curl "http://localhost:8002/api/nodes?country=SG"

# 速度≥50MB/s的节点
curl "http://localhost:8002/api/nodes?min_speed=50&max_latency=500"
```

**响应示例** (200 OK):

```json
{
  "total": 145,
  "nodes": [
    {
      "url": "vmess://abc123@sg-proxy.example.com:443",
      "name": "SG-Fast-1",
      "country": "SG",
      "latency": 123.45,
      "speed": 89.50,
      "availability": 98.5,
      "last_checked": "2026-01-01T12:00:00",
      "protocol": "vmess"
    },
    ...
  ],
  "last_updated": "2026-01-01T12:05:00",
  "filtered": false
}
```

---

#### POST /api/nodes/export

导出节点数据文件。

**请求参数**:

| 参数 | 类型 | 说明 |
|-----|------|------|
| format | string | 导出格式: json, clash, subscription |
| include_metadata | boolean | 是否包含元数据 |

**请求示例**:

```bash
curl -X POST http://localhost:8002/api/nodes/export \
  -H "Content-Type: application/json" \
  -d '{
    "format": "json",
    "include_metadata": true
  }'
```

**响应示例** (200 OK):

```json
{
  "total": 145,
  "nodes": [...],
  "exported_at": "2026-01-01T12:05:00",
  "format": "json"
}
```

---

#### POST /api/nodes/test-single

测试单个节点。

**请求体**:

```json
{
  "proxy_url": "vmess://user@host:port",
  "timeout": 10
}
```

**响应示例** (200 OK):

```json
{
  "proxy_url": "vmess://...",
  "status": "test_initiated",
  "message": "已发起测试，请稍候...",
  "timestamp": "2026-01-01T12:05:00"
}
```

---

#### POST /api/nodes/precision-test

用户发起的精确测速。

**请求体**:

```json
{
  "proxy_url": "vmess://user@host:port",
  "test_file_size": 50
}
```

**参数说明**:
- `proxy_url`: 完整的代理链接
- `test_file_size`: 测试文件大小 (MB)，如 10, 25, 50, 100

**工作流程**:
1. 用户在前端选择测试文件大小
2. 前端发送 POST 请求到本端点
3. 后端通过代理下载真实测试文件
4. 后端计算下载速度和流量消耗
5. 返回测速结果

**成功响应示例** (200 OK):

```json
{
  "status": "success",
  "speed_mbps": 45.67,
  "download_time_seconds": 1.23,
  "traffic_consumed_mb": 50.0,
  "bytes_downloaded": 52428800,
  "test_file_size_requested_mb": 50,
  "message": "精确测速完成: 45.67 MB/s",
  "timestamp": "2026-01-01T12:05:00"
}
```

**超时响应示例** (200 OK):

```json
{
  "status": "timeout",
  "speed_mbps": 0,
  "message": "测速超时 (> 300秒)",
  "timestamp": "2026-01-01T12:05:00"
}
```

**前端调用示例** (JavaScript):

```javascript
// 开始精确测速
async function startPrecisionTest(proxyUrl, fileSizeMb) {
  try {
    const response = await fetch('http://localhost:8002/api/nodes/precision-test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        proxy_url: proxyUrl,
        test_file_size: fileSizeMb
      })
    });

    const result = await response.json();
    
    if (result.status === 'success') {
      console.log(`测速完成: ${result.speed_mbps} MB/s`);
    } else if (result.status === 'timeout') {
      console.warn('测速超时');
    }
    
    return result;
  } catch (error) {
    console.error('请求失败:', error);
  }
}
```

---

### Webhook接收接口

#### POST /webhook/nodes-update

接收来自SpiderFlow的节点更新推送。

**请求头**:

```
Content-Type: application/json
```

**请求体**:

```json
{
  "event_type": "nodes_updated",
  "timestamp": "2026-01-01T12:00:00Z",
  "nodes": [
    {
      "url": "vmess://...",
      "name": "节点名",
      "country": "SG",
      "latency": 123.45,
      "speed": 45.67,
      "availability": 95.5,
      "last_checked": "2026-01-01T12:00:00",
      "protocol": "vmess"
    }
  ],
  "total_count": 150,
  "verified_count": 145,
  "signature": "abc123..."
}
```

**签名生成方法**:

```python
import hashlib
import hmac
import json

payload = {...}  # 上面的JSON对象
timestamp = "2026-01-01T12:00:00Z"
secret = "spiderflow-viper-sync-2026"

payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
message = f"{payload_str}.{timestamp}"
signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
```

**响应示例** (200 OK):

```json
{
  "status": "success",
  "message": "已接收145个节点",
  "local_total": 290,
  "timestamp": "2026-01-01T12:05:00"
}
```

**错误响应示例** (401 Unauthorized):

```json
{
  "detail": "签名验证失败"
}
```

---

#### POST /webhook/test-connection

测试Webhook连接。

**响应示例** (200 OK):

```json
{
  "status": "connected",
  "receiver": "viper-node-store",
  "webhook_version": "1.0",
  "timestamp": "2026-01-01T12:05:00"
}
```

---

### 同步管理接口

#### GET /api/sync/status

获取数据同步状态。

**响应示例** (200 OK):

```json
{
  "total_nodes": 145,
  "last_synced_at": "2026-01-01T12:05:00",
  "sync_method": "webhook",
  "webhook_syncs": 5,
  "poll_syncs": 2,
  "total_syncs": 7,
  "last_webhook_time": "2026-01-01T12:05:00",
  "last_poll_time": "2026-01-01T12:00:00",
  "data_hash": "abc123...",
  "poll_interval_seconds": 300,
  "scheduler_status": "running"
}
```

---

#### POST /api/sync/poll-now

立即执行一次轮询。

**响应示例** (200 OK):

```json
{
  "status": "poll_triggered",
  "message": "已触发手动轮询，在后台执行",
  "timestamp": "2026-01-01T12:05:00"
}
```

---

### 统计分析接口

#### GET /api/stats/summary

获取汇总统计信息。

**响应示例** (200 OK):

```json
{
  "total_nodes": 145,
  "country_distribution": {
    "SG": 25,
    "JP": 20,
    "US": 30,
    "HK": 15,
    "CN": 55
  },
  "protocol_distribution": {
    "vmess": 60,
    "vless": 50,
    "ss": 30,
    "trojan": 5
  },
  "average_latency_ms": 234.56,
  "average_speed_mbps": 45.23,
  "last_updated": "2026-01-01T12:05:00"
}
```

---

#### GET /api/stats/top-nodes

获取排名靠前的节点。

**请求参数**:

| 参数 | 类型 | 说明 | 默认值 |
|-----|------|------|--------|
| metric | string | 排序指标: speed 或 latency | speed |
| limit | int | 返回数量 | 10 |
| country | string | 按国家筛选 | 无 |

**请求示例**:

```bash
# 最快的20个节点
curl "http://localhost:8002/api/stats/top-nodes?metric=speed&limit=20"

# 延迟最低的10个新加坡节点
curl "http://localhost:8002/api/stats/top-nodes?metric=latency&limit=10&country=SG"
```

**响应示例** (200 OK):

```json
{
  "metric": "speed",
  "country": "all",
  "total": 145,
  "returned": 10,
  "nodes": [
    {
      "url": "vmess://...",
      "name": "SG-Fast-1",
      "country": "SG",
      "latency": 45.23,
      "speed": 250.67,
      "availability": 99.2,
      "protocol": "vmess"
    },
    ...
  ]
}
```

---

## SpiderFlow Webhook API

### Webhook推送接口

#### 后端模块

**文件**: `backend/webhook_push.py`

**核心函数**:

```python
async def push_nodes_to_viper(
    nodes: List[Dict[str, Any]],
    event_type: str = "nodes_updated",
    total_count: int = 0,
    verified_count: int = 0
) -> bool
```

**参数说明**:
- `nodes`: 节点列表
- `event_type`: 事件类型 (nodes_updated, batch_test_complete, 等)
- `total_count`: 总节点数
- `verified_count`: 验证通过的节点数

**返回值**: True 成功，False 失败

**使用示例**:

```python
from webhook_push import push_nodes_to_viper

# 在检测完成后调用
background_tasks.add_task(
    push_nodes_to_viper,
    nodes=verified_nodes,
    event_type="batch_test_complete",
    total_count=150,
    verified_count=145
)
```

---

#### 测试函数

```python
async def test_webhook_connection() -> bool
```

测试与viper-node-store的连接。

**使用示例**:

```python
from webhook_push import test_webhook_connection

connected = await test_webhook_connection()
if connected:
    print("✅ Webhook连接正常")
else:
    print("❌ Webhook连接失败")
```

---

#### 推送历史和统计

```python
def get_push_statistics() -> Dict[str, Any]
def get_push_history(limit: int = 50) -> List[Dict[str, Any]]
```

**使用示例**:

```python
from webhook_push import get_push_statistics, get_push_history

# 获取统计
stats = get_push_statistics()
print(f"成功率: {stats['success_rate']}")
print(f"总推送: {stats['total_pushes']}")

# 获取历史
history = get_push_history(limit=10)
for item in history:
    print(f"{item['timestamp']} - {item['status']}")
```

---

## 集成端点

### SpiderFlow → viper-node-store

**流程**:

```
1. SpiderFlow完成检测
   ↓
2. 调用 push_nodes_to_viper()
   ↓
3. 生成签名 (HMAC-SHA256)
   ↓
4. POST /webhook/nodes-update 到 viper-node-store
   ↓
5. viper-node-store验证签名
   ↓
6. 更新本地数据库
```

**环境变量配置**:

```bash
# SpiderFlow端
export WEBHOOK_SECRET="spiderflow-viper-sync-2026"
export VIPER_WEBHOOK_URL="http://localhost:8002/webhook/nodes-update"

# viper-node-store端
export WEBHOOK_SECRET="spiderflow-viper-sync-2026"
export SPIDERFLOW_API_URL="http://localhost:8001"
export POLL_INTERVAL="300"
```

---

## 错误处理

### 常见HTTP状态码

| 状态码 | 说明 | 处理方法 |
|--------|------|---------|
| 200 | 成功 | 继续处理 |
| 400 | 请求格式错误 | 检查请求体格式 |
| 401 | 签名验证失败 | 检查WEBHOOK_SECRET配置 |
| 404 | 端点不存在 | 检查API路径 |
| 500 | 服务器错误 | 查看服务日志 |
| 503 | 服务不可用 | 检查服务是否运行 |

---

### 错误响应示例

**签名验证失败** (401):

```json
{
  "detail": "签名验证失败"
}
```

**请求格式错误** (400):

```json
{
  "detail": "无效的JSON格式"
}
```

**服务器错误** (500):

```json
{
  "detail": "处理请求时发生错误"
}
```

---

## 示例代码

### Python - 推送节点数据

```python
import asyncio
from webhook_push import push_nodes_to_viper

async def main():
    nodes = [
        {
            "url": "vmess://abc@proxy1.com:443",
            "name": "SG-1",
            "country": "SG",
            "latency": 123.45,
            "speed": 45.67,
            "availability": 95.5,
            "last_checked": "2026-01-01T12:00:00",
            "protocol": "vmess"
        }
    ]
    
    success = await push_nodes_to_viper(
        nodes=nodes,
        event_type="nodes_updated",
        total_count=100,
        verified_count=1
    )
    
    if success:
        print("✅ 推送成功")
    else:
        print("❌ 推送失败")

asyncio.run(main())
```

---

### Bash - 获取节点列表

```bash
#!/bin/bash

# 获取所有节点
curl -s http://localhost:8002/api/nodes | jq '.total'

# 获取新加坡节点
curl -s "http://localhost:8002/api/nodes?country=SG" | jq '.nodes | length'

# 获取同步状态
curl -s http://localhost:8002/api/sync/status | jq '.total_syncs'
```

---

### JavaScript/Node.js - 查询API

```javascript
// 获取节点列表
async function getNodes() {
  const response = await fetch('http://localhost:8002/api/nodes');
  const data = await response.json();
  console.log(`总节点数: ${data.total}`);
  console.log(`新加坡节点: ${data.nodes.filter(n => n.country === 'SG').length}`);
}

// 获取统计信息
async function getStats() {
  const response = await fetch('http://localhost:8002/api/stats/summary');
  const stats = await response.json();
  console.log(`平均延迟: ${stats.average_latency_ms}ms`);
  console.log(`平均速度: ${stats.average_speed_mbps}MB/s`);
}

// 获取排名节点
async function getTopNodes() {
  const response = await fetch('http://localhost:8002/api/stats/top-nodes?metric=speed&limit=5');
  const data = await response.json();
  data.nodes.forEach(node => {
    console.log(`${node.name}: ${node.speed.toFixed(1)}MB/s`);
  });
}

getNodes();
getStats();
getTopNodes();
```

---

### cURL - 精确测速

```bash
#!/bin/bash

# 启动精确测速
curl -X POST http://localhost:8002/api/nodes/precision-test \
  -H "Content-Type: application/json" \
  -d '{
    "proxy_url": "vmess://user@host:port",
    "test_file_size": 50
  }' | jq '.'

# 检查同步状态
curl http://localhost:8002/api/sync/status | jq '.last_synced_at'

# 手动触发轮询
curl -X POST http://localhost:8002/api/sync/poll-now | jq '.status'
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|-----|------|------|
| 2.0 | 2026-01-01 | Phase 2: Webhook集成, 数据同步, 精确测速 |
| 1.0 | 2025-12-01 | 初始版本: 基础API |

---

**最后更新**: 2026-01-01  
**维护者**: 系统开发团队  
**下一版本**: 3.0 (前端集成和优化)
