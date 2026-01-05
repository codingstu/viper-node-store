# Vue3 登录/VIP 系统完整实现

## 📋 实现概要

完成了 Viper Node Store 的完整登录和 VIP 限制系统。用户现在可以：
- ✅ 使用注册账户登录
- ✅ 通过"极速注册"快速接入（自动生成账户信息）
- ✅ 使用激活码成为 VIP 用户
- ✅ 非 VIP 用户最多查看 20 个节点
- ✅ VIP 用户可查看全部节点

---

## 🔧 实现细节

### 1️⃣ authStore.js - 认证状态管理
**位置**: `frontend/src/stores/authStore.js`
**关键功能**:
- `init()` - 应用启动时初始化，检查 VIP 状态
- `login(email, password)` - 邮箱密码登录
- `register(email, password, username)` - 新用户注册
- `quickStart()` - 极速注册（自动生成VIPER-XXXX-YYYY账户）
- `redeemCode(code)` - 兑换激活码成为VIP
- `logout()` - 登出
- `checkVipStatus()` - 检查VIP状态（从profiles表vip_until字段）

**核心逻辑**:
```javascript
// 检查 VIP 状态
const { data: profile } = await supabaseClient
  .from('profiles')
  .select('vip_until')
  .eq('id', user.id)
  .maybeSingle()

if (profile?.vip_until) {
  isVip.value = new Date(profile.vip_until) > new Date()
}
```

**极速注册示例**:
- 用户名: `VIPER-ABCD-1234`
- 密码: `Viper#a1b2c3d4!`
- 邮箱: `agent.abcd.1234@shadow-network.com`

### 2️⃣ nodeStore.js - 节点数据存储（修改）
**位置**: `frontend/src/stores/nodeStore.js`
**关键修改**:
1. 导入 `useAuthStore`
2. 修改 `init()` - 开始时调用 `authStore.checkVipStatus()`
3. 修改 `displayedNodes` 计算属性 - 非VIP用户显示20个节点限制

**VIP 限制逻辑**:
```javascript
// 在 displayedNodes 计算属性中
const authStore = useAuthStore()
if (!authStore.isVip) {
  result = result.slice(0, 20)  // 非VIP最多20个节点
}
```

### 3️⃣ AuthModal.vue - 登录/注册UI组件
**位置**: `frontend/src/components/AuthModal.vue`
**功能**:
- 三个标签页: 登录、注册、激活码（已登录时显示）
- 登录表单：邮箱 + 密码
- 注册表单：邮箱 + 用户名 + 密码 + 极速注册按钮
- 极速注册后显示身份卡（可复制账户信息）
- 激活码输入（需已登录）
- 用户登出选项

**极速注册流程**:
1. 用户点击"极速注册"
2. 自动生成VIPER账户和密码
3. 显示身份卡弹窗，用户可复制信息
4. 自动登录
5. 3秒后关闭模态框

### 4️⃣ App.vue - 主应用界面（修改）
**位置**: `frontend/src/App.vue`
**关键修改**:
1. 导入 `useAuthStore` 和 `AuthModal`
2. 顶部导航栏添加:
   - VIP 徽章（仅已登录用户显示）
   - 登录/账户按钮
3. `onMounted()` 中先调用 `authStore.init()` 再调用 `nodeStore.init()`

**UI 布局**:
```
┌─ 顶部导航栏
│  ├─ Logo: 🐍 Viper Node Store
│  ├─ [中间] 用户名 | ⭐ VIP/📌 普通
│  ├─ 同步状态 (✓/⟳/✗)
│  ├─ 🔄 刷新按钮
│  └─ 🔐 登录 / 👤 账户
├─ 统计信息 (总数/健康/速度/更新时间)
├─ 搜索和过滤
└─ 节点网格
```

---

## 📊 用户权限对照表

| 功能 | 游客 | 普通用户 | VIP用户 |
|------|------|--------|--------|
| 查看节点 | ✓ (前20个) | ✓ (前20个) | ✓ (全部) |
| 测速 | ✓ | ✓ | ✓ |
| 生成二维码 | ✓ | ✓ | ✓ |
| 查看用户名 | - | ✓ | ✓ |
| 输入激活码 | - | ✓ | ✓ |
| VIP 徽章 | - | - | ✓ |

---

## 🔄 初始化流程

```
应用启动 (App.vue onMounted)
    ↓
authStore.init()
    ↓
检查已登录用户的VIP状态 (从profiles.vip_until)
    ↓
nodeStore.init()
    ↓
根据isVip状态加载节点 (displayedNodes自动应用限制)
    ↓
显示UI (根据authStore状态渲染)
    ↓
每12分钟自动刷新一次节点和同步状态
```

---

## 🧪 测试场景

### 场景1: 游客用户
1. 打开应用
2. 查看前20个节点（非VIP限制已应用）
3. 点击"🔐 登录"按钮

### 场景2: 极速注册
1. 点击"🔐 登录" → "注册"标签页
2. 点击"🚀 极速注册"
3. 系统生成账户信息，显示身份卡
4. 自动登录，3秒后关闭模态框
5. 仍然只能看20个节点（非VIP）
6. 顶部显示"📌 普通用户"徽章

### 场景3: 激活码升级
1. 已登录普通用户
2. 点击"👤 账户" → "激活码"标签页
3. 输入激活码，点击"兑换激活码"
4. 后端 RPC 函数 `redeem_kami()` 处理
5. VIP 升级成功，profiles.vip_until 字段更新
6. 立即看到"⭐ VIP"徽章
7. 可查看全部节点（20个限制自动取消）

### 场景4: 邮箱注册
1. 点击"🔐 登录" → "注册"标签页
2. 输入邮箱、用户名、密码
3. 点击"注册"
4. 创建新账户，自动登录
5. 同样限制20个节点

---

## 📝 Supabase 配置检查清单

- ✅ Auth 用户表 (Auth.users)
- ✅ 公开资料表 (public.profiles)
  - 字段: id (uuid), username (text), vip_until (timestamp)
  - RLS 启用
- ✅ RPC 函数 (redeem_kami)
  - 参数: code_input (text)
  - 返回: 成功/失败消息
- ✅ Supabase URL 配置
- ✅ Anon Key 配置（已在authStore.js中）

---

## 🚀 未来功能（已规划）

1. 区域选择功能（在 Region 菜单中）
2. 记住登录状态（从 localStorage 恢复）
3. 忘记密码功能
4. VIP 续费提醒
5. 用户头像和个人中心

---

## 📚 文件清单

### 新增文件
- `frontend/src/components/AuthModal.vue` - 登录/注册/激活码UI
- `frontend/src/stores/authStore.js` - 认证状态管理

### 修改文件
- `frontend/src/App.vue` - 集成AuthModal，修改顶部导航栏
- `frontend/src/stores/nodeStore.js` - 添加VIP限制逻辑，集成authStore

### 依赖
- `@supabase/supabase-js` - 已安装

---

## ✅ 完成状态

```
✅ authStore.js 创建 (6个方法完整)
✅ nodeStore.js 修改 (VIP限制已应用)
✅ AuthModal.vue 创建 (完整UI)
✅ App.vue 修改 (集成auth,显示VIP徽章)
✅ Supabase集成 (URL + Key配置)
✅ 应用启动成功 (无编译错误)
✅ 开发服务器运行 (Vite 7.3.0)
```

---

## 🎯 核心约束条件已满足

1. **非VIP用户只看20个节点** ✅
   - 在 `nodeStore.js` displayedNodes 中实现
   - 自动应用，无需额外操作

2. **注册登录功能** ✅
   - Supabase Auth 处理
   - 邮箱密码或极速注册两种方式

3. **激活码升级VIP** ✅
   - 调用 `authStore.redeemCode()`
   - 后端 RPC 函数处理 `redeem_kami(code_input)`

4. **极速注册** ✅
   - 自动生成 VIPER-XXXX-YYYY 账户
   - 生成密码：Viper#XXXXXXXX!
   - 生成邮箱：agent.XXXX.YYYY@shadow-network.com

5. **刷新间隔12分钟** ✅
   - App.vue 设置 720000ms (12 * 60 * 1000)

---

## 📞 故障排查

**问题1: VIP徽章不显示**
- 检查: authStore.isVip 是否为 true
- 解决: 确保 profiles 表中有 vip_until 数据

**问题2: 登录无反应**
- 检查: Supabase URL 和 API Key 是否正确
- 检查: 浏览器控制台错误信息
- 解决: 查看authStore.error 输出

**问题3: 激活码不生效**
- 检查: redeem_kami RPC 函数是否存在
- 检查: 激活码格式是否正确
- 解决: 验证后端 RPC 函数返回结果

---

**最后更新**: 2026-01-02
**实现状态**: ✅ 完成并测试就绪
