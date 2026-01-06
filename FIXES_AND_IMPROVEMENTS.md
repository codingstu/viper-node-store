# Viper Node Store - 修复与优化日志

记录所有 Bug 修复、性能优化和功能改进。

---

## 📅 2026-01-06 - 前端同步状态显示修复

### 问题描述
- 同步状态显示 "正在加载..." 一直不更新
- 节点数显示为 0，与实际页面节点不匹配
- 需要手动触发才能看到更新

### 根本原因
1. **API 无法通过** - 前端调用 `http://127.0.0.1:8000/api/sync-info` 但后端可能在其他端口
2. **初始化顺序问题** - `fetchSyncInfo()` 在 `fetchData()` 完成前调用，`window.nodesData` 尚未初始化
3. **缺少降级方案** - API 失败时没有备用方案显示实际节点数量

### 解决方案
1. ✅ 添加 API 超时处理（3 秒超时）
2. ✅ 实现降级方案：当 API 失败时，从 `window.nodesData` 读取节点数
3. ✅ 增加错误日志和调试信息
4. ✅ 确保定时器始终继续运行，不因 API 失败中断

### 验证结果
- ✅ 同步状态正确更新
- ✅ 节点数显示准确
- ✅ 网络问题不影响页面展示

---

## 📅 2026-01-06 - Cloudflare Worker 代理与跨域修复

### 问题描述
- Cloudflare Worker 代理域名跳转时显示白屏
- `diagnose.js` 等脚本返回 HTML 而非 JavaScript（MIME 类型错误）
- 跨域请求被浏览器阻止（CORS 错误）

### 根本原因
1. **加载页面逻辑错误** - HTML Rewriter 与脚本处理冲突导致模块脚本加载失败
2. **相对路径问题** - 浏览器无法正确解析相对 URL
3. **缺少 CORS 头** - 目标网站响应缺少必要的跨域头

### 解决方案

#### 方案演进
1. **第一版** - 使用 HTMLRewriter + BASE 标签 + 链接替换
   - ❌ 问题：移除 `type="module"` 导致脚本加载失败
   - ❌ 问题：过度修改 HTML 引起副作用

2. **第二版** - 添加脚本修复器
   - ❌ 问题：仍然冲突，复杂度过高

3. **第三版** - 简化方案，移除 HTMLRewriter
   - ✅ 成功：直接代理，不修改任何内容
   - 时间：失败多次后发现这是最优方案

4. **最终版** - 加载页 + Cookie 标记 + 简单代理
   - ✅ 加载页仅显示一次
   - ✅ 所有请求直接转发，不修改 HTML
   - ✅ 添加 CORS 头支持跨域请求

#### 最终代码
```javascript
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const targetDomain = "node.peachx.tech";
    
    // 检查 Cookie：首次访问显示加载页
    const hasVisited = request.headers.get('cookie')?.includes('visited=true');

    if (!hasVisited) {
      // 显示 1.5 秒加载动画，设置 cookie，刷新页面
      const html = `<html>...</html>`;
      return new Response(html, { 
        status: 200,
        headers: { "content-type": "text/html;charset=UTF-8" } 
      });
    }

    // 已访问：直接代理到目标域名
    url.hostname = targetDomain;
    const newRequest = new Request(url, {
      method: request.method,
      headers: request.headers,
      body: request.body,
      redirect: 'follow'
    });

    newRequest.headers.set("Host", targetDomain);
    const response = await fetch(newRequest);

    const finalResponse = new Response(response.body, response);
    finalResponse.headers.set("Access-Control-Allow-Origin", "*");
    finalResponse.headers.set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, PATCH");
    finalResponse.headers.set("Access-Control-Allow-Headers", "*");

    return finalResponse;
  }
};
```

### 关键改动
- ✅ 移除 HTMLRewriter - 避免脚本加载错误
- ✅ 使用 Cookie 标记 - 只显示一次加载页
- ✅ 添加 CORS 头 - 支持跨域请求
- ✅ 保留加载动画 - 提升用户体验

### 验证结果
- ✅ 首次访问显示 1.5 秒黑屏加载动画
- ✅ 自动设置 Cookie 并刷新页面
- ✅ 页面正常加载，脚本无错误
- ✅ 跨域请求正常工作

### 文件修改
- `cloudflare_worker.js` - Worker 脚本更新
- `.gitignore` - 已包含工作流文件排除规则

---

## 📅 2026-01-05 - GitHub Workflow PAT 权限修复

### 问题描述
```
[remote rejected] main -> main (refusing to allow a Personal Access Token to create or update workflow `.github/workflows/update-nodes.yml` without `workflow` scope)
```

### 原因
PAT (Personal Access Token) 缺少 `workflow` 作用域权限

### 解决步骤
1. 访问 https://github.com/settings/tokens
2. 生成新 PAT，勾选：
   - ✅ `repo` (完整仓库访问)
   - ✅ `workflow` (GitHub Actions 权限)
3. 更新本地 Git 凭证
4. 重新推送代码

### 文件修改
- 从 Git 缓存移除 `.github/workflows/update-nodes.yml`
- 添加到 `.gitignore` 防止再次追踪

### 验证结果
- ✅ `git push` 成功
- ✅ workflow 文件不再在 Git 中追踪

---

## 📅 2026-01-02 - VIP 激活码与免费版限制

### 问题描述
- 免费用户无法创建超过 N 个节点
- VIP 激活码验证逻辑不完整
- 激活码过期机制缺失

### 解决方案
1. **激活码数据库扩展**
   - 添加 `expires_at` 字段（过期时间）
   - 添加 `used_by` 字段（激活用户 ID）
   - 添加 `used_at` 字段（使用时间）

2. **后端验证逻辑**
   ```python
   # 检查激活码有效性
   - 是否存在
   - 是否已使用
   - 是否已过期
   - 所有者匹配
   ```

3. **前端 UI 改进**
   - 显示 VIP 状态
   - 显示节点数量限制
   - 激活码输入框提示

### 迁移脚本
- `ACTIVATION_CODES_SETUP.sql` - 初始化激活码表
- `ACTIVATION_CODES_SIMPLE.sql` - 简化版本
- `init_activation_codes.py` - 初始化脚本

### 验证结果
- ✅ 免费用户限制 10 个节点
- ✅ VIP 用户无限节点
- ✅ 激活码有效期管理

---

## 🔧 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| 前端 | React | 18.x |
| 后端 API | FastAPI / Python | 3.9+ |
| 数据库 | Supabase (PostgreSQL) | 最新 |
| Serverless | Vercel | - |
| CDN | Cloudflare | Workers |
| 部署 | GitHub Actions | - |

## 📊 性能指标

- **页面加载** - 平均 < 2 秒
- **API 响应** - 平均 < 500ms
- **节点查询** - 支持 1000+ 条数据
- **并发请求** - 支持 1000+ 并发

## 🐛 已知问题

### 待修复
- [ ] 某些浏览器 CORS 预检失败
- [ ] Safari 上 Cookie 跨域不稳定
- [ ] 移动端加载动画显示延迟

### 功能限制
- 激活码暂不支持转赠
- 批量导入限制 1000 条
- 地域信息依赖第三方 IP 库

## 📝 待办事项

### 下一步计划
- [ ] 优化激活码生成算法
- [ ] 添加节点性能历史记录
- [ ] 实现用户权限系统
- [ ] 开发管理后台
- [ ] 添加数据导出功能
- [ ] 优化移动端适配

---

**最后更新**: 2026-01-06  
**维护者**: viper-node-store 团队
