# viper-node-store 账户系统故障排除指南

## 问题描述
点击 👤 **账户** 按钮时出现网络连接错误 (net:ERR_CONNECTION_REFUSED)

## 根本原因

viper-node-store 的账户系统**直接调用 Supabase Auth API**，而不是通过本地 FastAPI 后端。这意味着：

```
前端 (Vue) → Supabase Auth API (云端)
                  ↓
              Supabase 数据库
```

**不是**：
```
前端 → FastAPI 8002 → Supabase  ❌
```

因此，`app_fastapi.py` 的运行状态与账户系统**无关**。

## 可能的失败原因

### 1. **Supabase API 密钥过期** ⚠️
- viper-node-store 中的 ANON_KEY 可能已经失效
- 需要从 Supabase 项目面板更新密钥
- 检查：浏览器 Console → 查看是否有 "密钥无效" 或 "401 Unauthorized" 错误

### 2. **网络连接问题**
- 你的 ISP 可能阻止了对 `hnlkwtkxbqiakeyienok.supabase.co` 的访问
- VPN/代理可能干扰了连接
- Supabase 服务暂时中断

### 3. **浏览器隐私设置**
- 某些浏览器扩展可能阻止了跨域请求
- 浏览器的 Cookie/存储空间设置可能有限制

### 4. **初始化延迟**
- 认证系统初始化太快，在 Supabase 响应前就超时了
- 解决：页面加载后等待 5 秒再尝试

## 快速修复方案

### 方案 A：浏览器层面（最快）
```
1. 打开 https://viper-node-store 页面
2. 按 Cmd+Shift+R (macOS) 或 Ctrl+Shift+F5 (Windows) 清除缓存
3. 等待 5 秒让所有初始化完成
4. 点击 👤 账户 按钮
```

### 方案 B：检查网络问题
```javascript
// 在浏览器 Console 中粘贴以下代码：

const testSupabase = async () => {
  try {
    const response = await fetch('https://hnlkwtkxbqiakeyienok.supabase.co/rest/v1/', {
      headers: {
        'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhubGt3dGt4YnFpYWtleWllbm9rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY5MDQwNTksImV4cCI6MjA4MjQ4MDA1OX0.Xg9vQdUfBdUW-IJaomEIRGsX6tB_k2grhrF4dm_aNME'
      }
    })
    console.log('✅ Supabase 连接正常:', response.status)
  } catch(e) {
    console.error('❌ Supabase 连接失败:', e.message)
  }
}

testSupabase()
```

### 方案 C：更新 ANON_KEY（如果密钥过期）
1. 进入 Supabase 项目面板
2. 到 Settings → API → Project API keys
3. 复制新的 `anon` key
4. 更新文件：`frontend/src/stores/authStore.js` 第 9 行
5. 重新刷新页面

## 最近的改进

### ✅ 已添加的功能
- 自动重试机制：初始化失败时自动重试 3 次
- 更友好的错误提示：区分不同类型的错误
- 网络诊断：Console 中显示详细的连接状态

### 📝 日志输出
打开浏览器 Console (F12) 查看诊断信息：
```
🔄 检查 VIP 状态... (尝试 1/3)
✅ 认证系统初始化成功

或

⚠️ 初始化失败，2秒后重试: ...
❌ 认证系统初始化失败（3次重试均失败）
```

## 如果问题仍未解决

### 调试步骤
1. 打开浏览器 DevTools (F12)
2. 切换到 Console 标签
3. 查找以下关键字：
   - `❌ Supabase` - 连接失败
   - `PGRST` - 权限/密钥问题
   - `network` - 网络错误
   - `timeout` - 连接超时

4. 记下完整的错误信息，查看是否与以下情况匹配：
   - **"密钥无效"** → 需要更新 ANON_KEY
   - **"连接拒绝"** → 网络/防火墙问题
   - **"超时"** → Supabase 服务不可用
   - **"CORS 错误"** → 跨域问题（罕见）

### 联系管理员
如果按照上述步骤仍无法解决，请提供以下信息：
- 浏览器 Console 中的完整错误信息
- 你的网络环境（是否使用 VPN/代理）
- `testSupabase()` 的执行结果

## 关键文件

修改过的文件：
- `frontend/src/stores/authStore.js` - 添加重试逻辑和错误处理
- `frontend/src/components/AuthModal.vue` - 添加诊断提示

这些修改会在下次页面刷新时生效。

---

## 账户系统架构图

```
┌─────────────────────────────────────────────────────┐
│           viper-node-store 前端                      │
│                                                     │
│  [👤 账户] ← AuthModal.vue                          │
│      ↓                                              │
│  authStore.js (Pinia)                              │
│      ↓                                              │
│  Supabase 客户端库                                  │
└─────────────────────────────────────────────────────┘
              ↓↓↓ HTTPS 直连 ↓↓↓
┌─────────────────────────────────────────────────────┐
│  Supabase Auth + Supabase 数据库                     │
│  hnlkwtkxbqiakeyienok.supabase.co                   │
│                                                     │
│  📊 auth.users (账户认证)                            │
│  📋 profiles (用户信息 + VIP 状态)                  │
└─────────────────────────────────────────────────────┘

❌ app_fastapi.py ← 与账户系统无关！
```

