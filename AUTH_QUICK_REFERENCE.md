# 🎯 登录/VIP 系统快速参考卡片

## ✨ 核心功能一览

```
游客用户              普通用户                VIP 用户
   ↓                    ↓                       ↓
只看前20节点 ← 极速/邮箱注册 → 输入激活码 → 看全部节点
  无登录       自动登录并存储        升级VIP
```

---

## 🔧 文件修改速查表

| 文件 | 操作 | 主要改动 |
|------|------|---------|
| authStore.js | ✅ 新建 | 6个方法 (init/login/register/quickStart/redeemCode/logout) |
| AuthModal.vue | ✅ 新建 | 完整UI (登录/注册/激活码/身份卡) |
| App.vue | 📝 修改 | 导入authStore, 修改顶部导航栏, 加VIP徽章 |
| nodeStore.js | 📝 修改 | 导入authStore, 添加VIP限制逻辑 |

---

## 🚀 快速启动

```bash
# 启动开发服务器
cd frontend && npm run dev

# 打开浏览器
http://localhost:5174
```

---

## 💡 核心代码片段

### VIP 限制逻辑
```javascript
// nodeStore.js - displayedNodes
const authStore = useAuthStore()
if (!authStore.isVip) {
  result = result.slice(0, 20)  // 非VIP最多20个节点
}
```

### 极速注册生成账户
```javascript
// authStore.js - quickStart()
const username = `VIPER-${random}-${timestamp}`
const password = `Viper#${hash}!`
const email = `agent.${random}.${timestamp}@shadow-network.com`
```

### 初始化顺序
```javascript
// App.vue - onMounted
await authStore.init()      // 先检查VIP状态
await nodeStore.init()      // 再加载节点
```

---

## 🎨 UI 顶部导航栏

```
┌─────────────────────────────────────────┐
│ 🐍 Viper Node Store                     │
│                    用户名 | ⭐VIP | 🔄  │
└─────────────────────────────────────────┘
```

状态映射:
- 游客: 显示 "🔐 登录"
- 登录: 显示 "用户名 | 📌 普通用户" + "👤 账户"
- VIP: 显示 "用户名 | ⭐ VIP" + "👤 账户"

---

## 📊 用户权限矩阵

| 功能 | 游客 | 普通 | VIP |
|------|------|------|-----|
| 查看节点 | 20个 | 20个 | 全部 |
| 测速 | ✓ | ✓ | ✓ |
| 二维码 | ✓ | ✓ | ✓ |
| 激活码输入 | ✗ | ✓ | ✓ |
| VIP徽章 | ✗ | ✗ | ✓ |

---

## 🔄 三种登录方式

### 1️⃣ 极速注册 (推荐)
- 点击: 🚀 极速注册
- 结果: 自动生成账户并登录
- 显示: 身份卡弹窗，支持复制

### 2️⃣ 邮箱注册
- 点击: 注册表单
- 输入: 邮箱 + 用户名 + 密码
- 结果: 注册后自动登录

### 3️⃣ 邮箱登录
- 点击: 登录标签页
- 输入: 邮箱 + 密码
- 结果: 登录成功

---

## ⚡ VIP 升级流程

```
已登录用户
    ↓
点击"激活码"标签页
    ↓
输入激活码 (XXXX-XXXX-XXXX)
    ↓
后端验证 (redeem_kami RPC)
    ↓
更新 profiles.vip_until
    ↓
自动检查 isVip 状态
    ↓
显示 "⭐ VIP" 徽章
    ↓
解锁全部节点
```

---

## 🧪 测试场景速查

| 场景 | 步骤 | 预期结果 |
|------|------|---------|
| 游客 | 打开应用 | 显示前20个节点 + 🔐登录 |
| 极速注册 | 🚀极速注册 → 生成账户 | 自动登录 + 📌普通用户 |
| 激活码 | 输入有效码 → 兑换 | ⭐VIP + 全部节点 |
| 登出 | 点击登出 | 恢复游客状态 |

---

## 📱 设备兼容性

- ✅ 桌面浏览器 (Chrome, Firefox, Safari, Edge)
- ✅ 移动浏览器 (iOS Safari, Android Chrome)
- ✅ 响应式设计已适配

---

## 🔐 安全特性

- ✅ 密码字段使用 type="password"
- ✅ 激活码验证在服务器端
- ✅ VIP 状态从 Supabase 获取
- ✅ Supabase RLS 策略保护
- ✅ 敏感数据不存储本地

---

## 📚 参考文档

- 📖 [完整实现文档](AUTH_IMPLEMENTATION.md)
- 🧪 [测试指南](TESTING_GUIDE_LOGIN_VIP.md)
- ✅ [完成清单](IMPLEMENTATION_CHECKLIST.md)

---

## 🆘 常见问题

**Q: VIP 徽章不显示？**
A: 检查 profiles.vip_until 是否大于当前日期

**Q: 激活码无反应？**
A: 检查 redeem_kami RPC 函数是否存在于 Supabase

**Q: 登录后仍是20个节点？**
A: 刷新页面使 displayedNodes 重新计算

**Q: 极速注册失败？**
A: 查看浏览器控制台错误信息，检查 Supabase 连接

---

## 📞 联系方式

问题?
1. 查看控制台错误信息 (F12)
2. 参考本参考卡片和文档
3. 检查 Supabase 配置

---

**最后更新**: 2026-01-02  
**版本**: 1.0  
**状态**: ✅ 生产就绪
