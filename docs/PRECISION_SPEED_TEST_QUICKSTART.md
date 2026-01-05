# 精确测速快速开始指南

## 什么是精确测速?

精确测速是 viper-node-store 的一项新功能，允许用户通过 **真实文件下载** 来测量代理的实际性能。

与快速测速（HEAD 请求）不同，精确测速会：
- 📥 真实下载数据
- 🚀 测量实际下载速度
- 📊 消耗对应流量
- ⏱️ 花费更多时间但结果更准确

## 快速开始

### 1️⃣ 启动后端服务

```bash
cd /Users/ikun/study/Learning/viper-node-store
python app_fastapi.py
```

确保看到日志输出类似:
```
INFO:     Uvicorn running on http://0.0.0.0:8002
```

### 2️⃣ 打开前端页面

在浏览器中访问:
```
http://localhost:8002
```

### 3️⃣ 找到要测试的节点

- 在节点列表中浏览可用节点
- 每个节点卡片显示: 国家、协议、速度、延迟

### 4️⃣ 点击精确测速按钮

- 找到节点卡片右侧的 **⚡** 按钮
- 按钮位置: 在 COPY 和 QR 按钮之间
- 点击打开精确测速模态框

### 5️⃣ 选择测试文件大小

弹窗中有 4 个选项:

| 按钮 | 文件大小 | 流量消耗 | 估计耗时 |
|------|--------|---------|---------|
| 10 MB | 10 MB | 10 MB | 1-3s |
| 25 MB | 25 MB | 25 MB | 2-8s |
| 50 MB | 50 MB | 50 MB | 5-20s |
| 100 MB | 100 MB | 100 MB | 10-60s |

**建议**:
- 快速测试: 选择 **10 MB** 或 **25 MB**
- 标准测试: 选择 **50 MB**
- 完整测试: 选择 **100 MB**

### 6️⃣ 等待测试完成

- 模态框显示进度条
- 进度条从 0% 增长到 100%
- 测试中保持页面不离开

### 7️⃣ 查看测试结果

测试完成后显示:

```
✅ 精确测速完成: 45.67 MB/s

下载速度    45.67 MB/s
用时        1.23s
流量消耗    50.0MB
```

关键指标解读:
- **下载速度**: MB/s (越高越好)
- **用时**: 总耗时秒数
- **流量消耗**: 实际消耗的数据量

## 工作流示例

### 场景 1: 快速测试新节点

```
1. 打开 http://localhost:8002
2. 找到新节点（例如 Singapore 节点）
3. 点击 ⚡ 按钮
4. 选择 10 MB（快速测试）
5. 等待 1-2 秒
6. 查看结果
```

### 场景 2: 对比多个节点

```
1. 测试节点 A，记下速度
2. 返回列表
3. 测试节点 B，记下速度
4. 对比结果，选择更快的节点
```

### 场景 3: 详细评估节点性能

```
1. 选择要深度评估的节点
2. 点击 ⚡ 按钮
3. 选择 50 MB 进行标准测试
4. 记录测试结果
5. 可选: 再测试一次以获得更准确的数据
```

## 常见问题

### Q: 为什么测速需要这么长时间?

**A**: 取决于代理的实际速度:
- 速度越快，时间越短
- 速度越慢，时间越长
- 最多等待 300 秒后超时

**加快测速的方法**:
- 选择较小的文件大小 (10MB 而不是 100MB)
- 选择已知速度较快的节点

### Q: 测速会消耗流量吗?

**A**: 是的。精确测速会消耗对应的流量:
- 10 MB 测试 → 消耗 10 MB 流量
- 100 MB 测试 → 消耗 100 MB 流量

**节省流量的方法**:
- 选择较小的文件大小
- 不要重复测试同一节点

### Q: 为什么测速失败?

**常见原因**:

1. **代理已失效**: 该代理无法连接
   - 解决: 选择其他节点
   
2. **网络不稳定**: 下载中途断网
   - 解决: 检查网络连接
   
3. **后端服务未运行**: 后端 API 不可用
   - 解决: 运行 `python app_fastapi.py`
   
4. **超时**: 测试超过 300 秒
   - 解决: 选择更小的文件大小

### Q: 结果不准确怎么办?

**A**: 测速结果受多种因素影响:
- 网络波动
- 后端服务器负载
- 代理真实性能
- 测试文件源的速度

**改进准确性**:
- 多测几次，取平均值
- 避免在网络繁忙时测试
- 选择较大的文件大小

### Q: 能否中断正在进行的测速?

**A**: 当前版本不支持中断测速。

**替代方案**:
- 等待测速完成
- 关闭浏览器标签页重新开始
- 等待 300 秒自动超时

### Q: 后端服务如何处理代理?

**A**: 后端使用以下方式处理代理:

1. 解析代理链接
2. 配置下载客户端使用代理
3. 通过代理下载测试文件
4. 计算下载速度

目前使用 Cloudflare 的速度测试文件:
```
https://speed.cloudflare.com/__down?bytes=XXX
```

## API 调用示例

### cURL

```bash
# 发起 50MB 文件的精确测速
curl -X POST http://localhost:8002/api/nodes/precision-test \
  -H "Content-Type: application/json" \
  -d '{
    "proxy_url": "vmess://user@host:port",
    "test_file_size": 50
  }'

# 输出:
# {
#   "status": "success",
#   "speed_mbps": 45.67,
#   "download_time_seconds": 1.23,
#   "traffic_consumed_mb": 50.0,
#   "message": "精确测速完成: 45.67 MB/s",
#   ...
# }
```

### Python

```python
import requests
import json

# 后端 API 地址
API_URL = "http://localhost:8002/api/nodes/precision-test"

# 代理链接
proxy_url = "vmess://..."

# 发起精确测速请求
response = requests.post(API_URL, json={
    "proxy_url": proxy_url,
    "test_file_size": 50
})

# 解析结果
result = response.json()

if result['status'] == 'success':
    print(f"测速完成: {result['speed_mbps']} MB/s")
    print(f"用时: {result['download_time_seconds']}s")
    print(f"流量: {result['traffic_consumed_mb']}MB")
else:
    print(f"测速失败: {result['message']}")
```

### JavaScript

```javascript
// 发起精确测速
async function testSpeed(proxyUrl) {
  try {
    const response = await fetch('http://localhost:8002/api/nodes/precision-test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        proxy_url: proxyUrl,
        test_file_size: 50
      })
    });

    const result = await response.json();
    
    if (result.status === 'success') {
      console.log(`速度: ${result.speed_mbps} MB/s`);
      console.log(`流量: ${result.traffic_consumed_mb} MB`);
    } else {
      console.error('测速失败:', result.message);
    }
    
    return result;
  } catch (error) {
    console.error('请求失败:', error);
  }
}
```

## 技术细节

### 后端实现流程

```
请求接收
  ↓
解析代理链接
  ↓
配置异步下载客户端
  ↓
开始下载测试文件
  ↓ (通过代理)
← 测试文件来自 Cloudflare
  ↓
记录下载时间
  ↓
计算下载速度: bytes / time
  ↓
返回结果 JSON
```

### 前端 UI 流程

```
用户点击 ⚡ 按钮
  ↓
模态框显示选项 (10/25/50/100 MB)
  ↓
用户选择文件大小
  ↓
前端发送 POST 请求
  ↓
显示进度条 (0% → 100%)
  ↓
后端返回结果
  ↓
显示结果卡片
  ↓
用户点击 [关闭] 返回列表
```

## 故障排查

### 问题 1: "测速超时"

**症状**: 等待超过 300 秒后返回超时错误

**解决方案**:
```
1. 选择更小的文件大小 (10MB)
2. 更换节点重试
3. 检查网络连接
4. 检查代理是否有速度限制
```

### 问题 2: "代理连接失败"

**症状**: 立即返回错误

**解决方案**:
```
1. 确认代理链接是否有效
2. 手动复制链接到代理工具测试
3. 尝试其他代理
4. 检查后端是否正确接收请求
```

### 问题 3: 进度条卡住

**症状**: 进度条长时间不动

**解决方案**:
```
1. 不要关闭浏览器，继续等待
2. 检查网络连接
3. 如果超过 5 分钟，刷新页面重试
4. 检查后端是否仍在运行
```

### 问题 4: 后端返回 500 错误

**症状**: 看到 HTTP 500 错误

**解决方案**:
```
1. 检查后端控制台输出
2. 确认 Python 进程仍在运行
3. 重启后端: Ctrl+C, 然后重新运行 python app_fastapi.py
4. 检查 fastapi 和 aiohttp 是否已安装
```

## 更多信息

- 📖 详细文档: [PRECISION_SPEED_TEST_IMPLEMENTATION.md](./PRECISION_SPEED_TEST_IMPLEMENTATION.md)
- 🔧 API 参考: [API_REFERENCE.md](./API_REFERENCE.md)
- 💻 源代码: [app_fastapi.py](./app_fastapi.py) 和 [index.html](./index.html)

## 支持

遇到问题? 检查以下内容:

1. ✅ 后端是否正在运行 (`http://localhost:8002/api/nodes`)
2. ✅ 前端是否能正常加载 (`http://localhost:8002`)
3. ✅ 代理链接是否有效
4. ✅ 网络连接是否正常
5. ✅ 流量是否充足

---

**最后更新**: 2024-01-15  
**版本**: 1.0  
**状态**: ✅ 生产就绪
