# 精确速度测试实现文档

## 概述

本文档详细说明 viper-node-store 中精确速度测试功能的完整实现，包括后端 API、前端 UI 和用户工作流。

## 架构设计

### 核心原理

**精确测速** vs **快速测速**:
- **快速测速**: 通过 HEAD 请求检测代理响应速度 (前端执行，无流量消耗)
- **精确测速**: 通过真实文件下载测量代理性能 (后端执行，消耗对应流量)

### 部署拓扑

```
┌─────────────────────────────┐
│   viper-node-store 前端      │
│   (index.html - HTML5 UI)    │
│  • 节点卡片展示              │
│  • 精确测速按钮 (⚡)          │
│  • 文件大小选择 (10/25/50/100MB) │
│  • 进度条 + 结果显示          │
└─────────┬───────────────────┘
          │ HTTP POST
          │ /api/nodes/precision-test
          │
┌─────────▼───────────────────┐
│   viper-node-store 后端      │
│   (app_fastapi.py)           │
│  • 接收测速请求              │
│  • 下载测试文件              │
│  • 计算下载速度              │
│  • 返回测试结果              │
└─────────────────────────────┘
```

## 后端实现

### API 端点

**路径**: `POST /api/nodes/precision-test`

**请求参数**:
```json
{
  "proxy_url": "vmess://...",      // 代理链接
  "test_file_size": 50              // 测试文件大小 (MB)
}
```

**响应示例**:

成功响应 (HTTP 200):
```json
{
  "status": "success",
  "speed_mbps": 45.67,
  "download_time_seconds": 1.23,
  "traffic_consumed_mb": 50.0,
  "bytes_downloaded": 52428800,
  "test_file_size_requested_mb": 50,
  "message": "精确测速完成: 45.67 MB/s",
  "timestamp": "2024-01-15T10:30:00"
}
```

错误响应 (HTTP 200):
```json
{
  "status": "timeout",
  "speed_mbps": 0,
  "message": "测速超时 (> 300秒)",
  "timestamp": "2024-01-15T10:30:00"
}
```

### 实现细节 (app_fastapi.py)

**关键功能**:

1. **文件下载测试**
   - 使用 Cloudflare 的测试文件服务: `https://speed.cloudflare.com/__down?bytes=XXX`
   - 支持多个文件大小: 10MB, 25MB, 50MB, 100MB
   - 异步下载，避免阻塞主线程

2. **速度计算**
   ```python
   speed_mbps = (bytes_downloaded / (1024 * 1024)) / download_time
   ```

3. **超时处理**
   - 最大超时时间: 300 秒
   - 超时返回错误状态，但包含已下载数据

4. **错误恢复**
   - 部分下载成功: 返回 `partial_success` 状态和部分速度数据
   - 完全失败: 返回 `error` 状态和错误消息

### 代码位置

文件: `/Users/ikun/study/Learning/viper-node-store/app_fastapi.py`
函数: `precision_speed_test()` (第 369-470 行)

## 前端实现

### UI 组件

#### 1. 节点卡片上的精确测速按钮

位置: `index.html` 第 992 行
```html
<button onclick="openPrecisionTestModal('${node.link}', '${cnName}')" 
        class="col-span-1 py-1.5 rounded-lg text-xs ... bg-purple-500/20 ...">
    ⚡
</button>
```

样式:
- 紫色主题 (purple-500/20 → purple-500/30)
- 按钮文本: "⚡" (闪电符号)
- 悬停效果: 背景加深，边框变亮

#### 2. 精确测速模态框

位置: `index.html` 第 413-472 行

结构:
- **标题**: "⚡ 精确测速"
- **文件大小选择**: 4 个按钮 (10/25/50/100MB)
- **进度显示**: 进度条 + 百分比
- **结果显示**: 表格展示速度、用时、流量消耗

样式特点:
- Glass-card 效果 (毛玻璃背景)
- 紫色主题 (border-purple-500/20)
- Z-index: 108 (在节点卡片上方但在底层弹窗下方)
- 最大宽度: 28rem (432px)

#### 3. JavaScript 函数

**主要函数**:

1. **openPrecisionTestModal(link, nodeName)**
   - 打开模态框
   - 存储当前节点信息到 `currentTestNode`
   - 重置 UI 状态

2. **closePrecisionTestModal()**
   - 关闭模态框
   - 清理状态

3. **startPrecisionTest(fileSizeMs)**
   - 发起 API 请求到后端
   - 更新进度条
   - 处理响应结果
   - 调用 `showPrecisionTestResult()`

4. **showPrecisionTestResult(result)**
   - 显示测试结果
   - 解析响应数据
   - 更新 UI 显示速度、用时、流量

### 代码位置

文件: `/Users/ikun/study/Learning/viper-node-store/index.html`

- **模态框 HTML**: 第 413-472 行
- **按钮代码**: 第 992-995 行
- **JavaScript 函数**: 第 1193-1250 行

## 用户工作流

### 使用步骤

1. **打开 viper-node-store 前端**
   ```
   http://localhost:8002
   ```

2. **找到要测试的节点**
   - 在节点列表中找到目标节点

3. **点击精确测速按钮**
   - 点击节点卡片右侧的 "⚡" 按钮
   - 打开"精确测速"模态框

4. **选择文件大小**
   - 10 MB: 快速测试，消耗 10MB 流量
   - 25 MB: 中等测试，消耗 25MB 流量
   - 50 MB: 标准测试，消耗 50MB 流量
   - 100 MB: 完整测试，消耗 100MB 流量

5. **等待测试完成**
   - 显示进度条
   - 进度实时更新
   - 测试可能需要 30 秒至 5 分钟 (取决于代理速度)

6. **查看测试结果**
   - **下载速度**: 用 MB/s 表示
   - **用时**: 总下载耗时
   - **流量消耗**: 实际消耗的数据量

### 示例场景

```
用户点击 [⚡] 按钮
    ↓
模态框弹出: "选择测试文件大小"
    ↓
用户选择: "50 MB"
    ↓
前端发送 POST 请求
    ↓
后端开始下载 50MB 文件
    ↓
进度条显示: 0% → 50% → 100%
    ↓
后端返回结果:
   {
     "speed_mbps": 45.67,
     "download_time_seconds": 1.23,
     "traffic_consumed_mb": 50.0,
     ...
   }
    ↓
前端显示结果:
   ✅ 精确测速完成: 45.67 MB/s
   下载速度: 45.67 MB/s
   用时: 1.23s
   流量消耗: 50.0MB
```

## 集成要点

### 跨域配置

后端 FastAPI 应用已配置 CORS 中间件:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

这允许前端从任何源调用 API。

### 本地开发

**启动后端**:
```bash
cd /Users/ikun/study/Learning/viper-node-store
python app_fastapi.py
# 后端运行在 http://localhost:8002
```

**前端访问**:
```
http://localhost:8002
```

前端页面直接在后端提供 (static file serving)。

### 错误处理

前端处理的错误场景:

1. **网络连接失败**
   ```javascript
   catch (error) {
     console.error('精确测速失败:', error);
     showPrecisionTestResult({
       status: 'error',
       speed_mbps: 0,
       message: `测速失败: ${error.message}`
     });
   }
   ```

2. **超时 (> 300秒)**
   - 后端返回 `timeout` 状态
   - 前端显示: "❌ 测速失败 - 测速超时 (> 300秒)"

3. **代理无效**
   - 后端返回 `error` 状态
   - 前端显示具体错误消息

## 测试清单

- [x] 后端 API 实现完成
- [x] 前端模态框 UI 完成
- [x] 精确测速按钮添加到节点卡片
- [x] JavaScript 函数实现完成
- [x] 错误处理和超时处理
- [x] CORS 中间件配置
- [ ] 端到端测试 (待验证)
- [ ] 性能优化 (并发控制)
- [ ] 日志记录完善

## 性能注意事项

### 限制

1. **单个测试超时**: 300 秒
2. **最大并发**: 单后端服务可支持多个并发测速，但受系统资源限制
3. **带宽消耗**: 与测试文件大小成正比

### 优化建议

1. **请求队列**: 实现后端任务队列，避免过多并发
2. **缓存结果**: 缓存最近的测速结果，减少重复测试
3. **CDN 加速**: 使用更靠近用户的 CDN 服务提高下载速度

## 常见问题

### Q: 精确测速需要多长时间?

A: 取决于代理速度和网络环境:
- 快速代理 (50+ MB/s): 1-2 秒
- 中速代理 (10-50 MB/s): 2-10 秒
- 慢速代理 (< 10 MB/s): 10-300 秒

### Q: 测速会消耗大量流量吗?

A: 会的。精确测速会消耗对应文件大小的流量:
- 10 MB 测试 = 10 MB 流量
- 100 MB 测试 = 100 MB 流量

建议在流量充足的情况下使用。

### Q: 能否取消正在进行的测速?

A: 当前实现不支持中断。建议等待超时或重新加载页面。

### Q: 测速结果不准确怎么办?

A: 影响测速准确性的因素:
- 网络波动
- 后端服务器负载
- 代理的真实速度
- 测试文件源的速度

建议多次测试取平均值。

## 部署检查清单

在生产环境部署前，确保:

- [x] 后端 FastAPI 应用正确配置
- [x] CORS 中间件启用
- [x] 前端 HTML/JS 正确加载
- [x] 测速 API 端点响应正常
- [ ] 防火墙允许出站连接 (用于下载测试文件)
- [ ] 有足够的带宽用于测速
- [ ] 日志记录配置完善

## 版本历史

| 版本 | 日期 | 更改 |
|------|------|------|
| 1.0  | 2024-01-15 | 初始实现：后端 API + 前端 UI |

## 相关文件

- 后端实现: `/Users/ikun/study/Learning/viper-node-store/app_fastapi.py`
- 前端实现: `/Users/ikun/study/Learning/viper-node-store/index.html`
- API 文档: `/Users/ikun/study/Learning/viper-node-store/API_REFERENCE.md`

## 作者

GitHub Copilot

## 许可证

与 viper-node-store 项目保持一致

---

**最后更新**: 2024-01-15
**实现状态**: ✅ 完成
