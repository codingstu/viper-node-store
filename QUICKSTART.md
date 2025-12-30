# 🚀 快速启动指南

## ⚡ 3 分钟快速开始

### 前置条件
- ✅ GitHub 账号 (已有)
- ✅ Cloudflare 账号 (需要)
- ✅ 项目已配置好 Aliyun FC (已有)
- ✅ Supabase 数据库已就绪 (已有)

---

## 📋 第 1 步: 部署 Cloudflare Worker (2 分钟)

### 1.1 访问 Cloudflare Dashboard
```
https://dash.cloudflare.com
```

### 1.2 进入 Workers 页面
- 左侧菜单 → "Workers and Pages"
- 点击 "Create application"
- 选择 "Create a Worker"

### 1.3 创建 Worker
- **名称:** `mainland-node-overseas-probe`
- 点击 "Deploy"

### 1.4 部署代码
1. 点击 "Edit code"
2. 清空默认代码
3. 复制粘贴以下代码:

```javascript
export default {
  async fetch(request, env, ctx) {
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    try {
      const data = await request.json();
      const nodes = data.nodes || [];

      if (!nodes.length) {
        return new Response(JSON.stringify({ error: 'No nodes provided' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      const results = [];

      const promises = nodes.map(async (node) => {
        const { id, host, port } = node;
        const start = Date.now();

        try {
          const response = await fetch(`http://${host}:${port || 80}/`, {
            method: 'HEAD',
            timeout: 2500,
            cf: {
              cacheTtl: 0,
              mirage: false,
              minify: { javascript: false, css: false, html: false }
            }
          }).catch(() => null);

          const latency = Date.now() - start;
          const success = response && (response.status === 200 || response.status === 405);

          return {
            id,
            host,
            port,
            latency: success ? latency : -1,
            success: !!success,
            region: 'Global'
          };
        } catch (e) {
          return {
            id,
            host,
            port,
            latency: -1,
            success: false,
            error: e.message
          };
        }
      });

      const allResults = await Promise.all(promises);
      
      return new Response(JSON.stringify(allResults), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });

    } catch (e) {
      return new Response(
        JSON.stringify({ error: e.message, type: 'ParseError' }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      );
    }
  }
};
```

4. 点击 "Save and Deploy"

### 1.5 获取 Worker URL ⭐

部署完成后，会显示 Worker URL，格式如:
```
https://mainland-node-overseas-probe.your-account.workers.dev
```

**复制这个 URL** ← 下一步需要用到

---

## 📋 第 2 步: 添加 GitHub Secret (1 分钟)

### 2.1 进入仓库设置
1. 打开你的 GitHub 仓库
2. Settings → Secrets and variables → Actions

### 2.2 创建新 Secret
1. 点击 "New repository secret"
2. **名称:** `CLOUDFLARE_WORKER_URL`
3. **值:** 粘贴第 1.5 步的 Worker URL
4. 点击 "Add secret"

---

## 📋 第 3 步: 测试系统 (验证)

### 3.1 手动运行工作流
1. 进入 GitHub 仓库
2. 点击 "Actions" 标签页
3. 选择 "Update & Test Nodes"
4. 点击 "Run workflow" → "Run workflow"

### 3.2 等待完成
- 监测日志，看是否出现:
```
🚀 [2B/3] 启动国外测速 (Cloudflare Workers)...
   📤 发送批次 1 (X 个节点)...
   ✅ 1.2.3.4 | 延迟: 45ms (国外真实)
✅ 国外测速完成: X / Y 个节点在国外可用
```

### 3.3 检查 Supabase
1. 访问 https://app.supabase.com
2. 选择你的项目 → Tables → nodes
3. 看是否有新数据 (updated_at 是最近的时间)

### 3.4 刷新前端
1. 打开网站首页
2. 点击右上角刷新按钮
3. 应该看到更新后的节点数据

---

## ✅ 验证清单

- [ ] Cloudflare Worker 已部署并返回正确响应
- [ ] GitHub Secret `CLOUDFLARE_WORKER_URL` 已添加
- [ ] GitHub Actions 工作流成功运行
- [ ] Supabase 中有最新的节点数据
- [ ] 前端页面显示新节点数据

**全部勾选？恭喜！系统已就位！** 🎉

---

## 📊 系统现状

```
┌─────────────────────────────────┐
│   GitHub Actions (每 4 小时)    │
│   自动运行更新和测速            │
└─────────────┬───────────────────┘
              │
    ┌─────────┴──────────┐
    │                    │
    ▼                    ▼
⚙️ Aliyun FC      🌍 Cloudflare
(大陆测速)         (国外测速)
    │                    │
    └─────────┬──────────┘
              │
              ▼
    💾 Supabase (存储)
              │
              ▼
    🌐 前端网页 (显示)
```

---

## 🔄 自动化流程

系统现在会**每 4 小时自动**:

1. 📡 从 API 获取节点列表
2. 🏷️ 按国家分类:
   - 🇨🇳 CN → Aliyun FC 大陆测速
   - 🌍 其他 → Cloudflare 国外测速
3. 📊 计算速度评分
4. 💾 保存到 Supabase
5. 🌐 前端自动更新

---

## 🆘 如果出现问题

### Worker 部署失败？
→ 检查 Cloudflare Dashboard 的错误信息
→ 确认代码没有语法错误

### GitHub Actions 报错？
→ 检查 Secrets 是否正确设置
→ 查看完整错误日志

### 数据没有更新？
→ 清除浏览器缓存 (Ctrl+Shift+Delete)
→ 点击页面刷新按钮
→ 检查 Supabase 是否有新数据

### 更多帮助?
→ 查看 [CLOUDFLARE_SETUP.md](./CLOUDFLARE_SETUP.md) 详细指南
→ 查看 [ARCHITECTURE.md](./ARCHITECTURE.md) 系统架构
→ 查看 [UPGRADE_SUMMARY.md](./UPGRADE_SUMMARY.md) 完整更改

---

## 💡 小贴士

- 🔔 **定期检查:** 每周检查一次测速数据质量
- 📊 **监控趋势:** 观察节点延迟的变化趋势
- 🔄 **手动刷新:** 如果需要立即更新，点击页面刷新按钮
- 🐛 **报告问题:** 发现节点问题，可临时从列表中删除

---

## 🎯 下一步

系统已完全配置好，可以开始:

1. ✅ 定期监控测速数据
2. ✅ 根据结果优化节点选择
3. ✅ 定期备份 Supabase 数据
4. ✅ 考虑扩展到更多地区测速

---

**现在就开始吧！** 🚀

有问题？查看详细文档:
- [Cloudflare 部署指南](./CLOUDFLARE_SETUP.md)
- [系统架构说明](./ARCHITECTURE.md)
- [完整更改总结](./UPGRADE_SUMMARY.md)
