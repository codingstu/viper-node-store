## 🚀 VIP 激活码兑换 - 快速设置 Checklist

### 问题症状
- [ ] 用户输入激活码后，兑换显示成功
- [ ] 但刷新页面后，用户仍是普通身份，无法看到全部节点

### 根本原因
- [ ] Supabase 中没有 `activation_codes` 表
- [ ] 后端只有不完整的 RPC，没有真正的激活码 API

### ✅ 解决步骤

#### 1️⃣ 创建数据库表（5分钟）
- [ ] 打开 https://app.supabase.com
- [ ] 选择你的 viper-node-store 项目
- [ ] 点击左侧 **SQL Editor**
- [ ] 新建查询，复制粘贴 `ACTIVATION_CODES_SETUP.sql` 中的 SQL
- [ ] 点击 **Run** 执行
- [ ] 执行完成后，在 **Tables** 中应该能看到 `activation_codes` 表

**验证**：
```sql
-- 在 SQL Editor 中执行，应该看到 4 个测试码
SELECT code, vip_days, used FROM activation_codes;
```

#### 2️⃣ 检查 profiles 表有 vip_until 字段（2分钟）
- [ ] 在 SQL Editor 中执行：
```sql
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'profiles' AND column_name = 'vip_until';
```
- [ ] 如果没有结果，执行：
```sql
ALTER TABLE profiles 
ADD COLUMN vip_until TIMESTAMP WITH TIME ZONE DEFAULT NULL;
```

#### 3️⃣ 代码更新（已完成 ✅）
- [x] `app_fastapi.py` - 已添加 `/api/auth/redeem-code` 端点
- [x] `authStore.js` - 已改为调用后端 API
- [x] `AuthDropdown.vue` - 已改进成功处理

#### 4️⃣ 重启后端（3分钟）
```bash
cd /Users/ikun/study/Learning/viper-node-store

# 停止现有的后端
pkill -f "app_fastapi.py"
sleep 2

# 启动新的后端
python app_fastapi.py &

# 或使用 nohup 后台运行
nohup python app_fastapi.py > backend.log 2>&1 &
```

- [ ] 确认后端启动成功（应该看到 `viper-node-store API 服务启动` 的日志）

#### 5️⃣ 测试激活码兑换（5分钟）

**准备**：
- [ ] 打开浏览器开发者工具（F12 → Console）
- [ ] 打开 http://localhost:5173

**步骤**：
1. [ ] 点击 **🔐 登录** 按钮
2. [ ] 创建测试账户或使用现有账户登录
3. [ ] 登录成功后，点击 **👤 账户** 按钮
4. [ ] 点击 **激活码** 标签页
5. [ ] 输入测试激活码：`VIP30-2024-TEST-001`
6. [ ] 点击 **兑换激活码** 按钮
7. [ ] 检查：
   - [ ] 显示 "✅ 激活成功！您已升级为 VIP 用户"
   - [ ] 下拉面板自动关闭
   - [ ] 导航栏账户按钮变为 **⭐ VIP** 或 **👤 账户**
   - [ ] 页面顶部显示 "⭐ VIP 用户" 徽章

**刷新验证**：
- [ ] 手动刷新页面 (Cmd+R / Ctrl+R)
- [ ] 确认用户仍显示为 **VIP** 状态
- [ ] 节点列表显示所有节点（不限制 20 个）
- [ ] 在浏览器控制台执行并验证：
```javascript
// 打开浏览器 Console，执行：
import { useAuthStore } from '/src/stores/authStore'
const auth = useAuthStore()
console.log('isVip:', auth.isVip)
console.log('vipDate:', auth.vipDate)
```

#### 6️⃣ 验证 VIP 权限生效
- [ ] 未登录或非 VIP 状态：节点列表显示前 20 个
- [ ] 登录并兑换激活码后：节点列表显示全部节点

### 🧪 可用的测试激活码

| 激活码 | 期限 | 状态 |
|--------|------|------|
| `VIP7-2024-TEST-001` | 7 天 | 未使用 |
| `VIP30-2024-TEST-001` | 30 天 | 未使用 |
| `VIP90-2024-TEST-001` | 90 天 | 未使用 |
| `VIP365-2024-TEST-001` | 1 年 | 未使用 |

### 🔧 故障排查

#### 兑换时显示 "激活码不存在"
- [ ] 检查 activation_codes 表是否存在
```sql
SELECT * FROM activation_codes LIMIT 1;
```
- [ ] 如果表不存在，重新执行 ACTIVATION_CODES_SETUP.sql
- [ ] 检查激活码大小写是否正确（应为全大写）

#### 兑换显示成功但 VIP 未更新
- [ ] 检查 profiles 表是否有 vip_until 字段
```sql
DESC profiles;  -- 或 DESCRIBE profiles
```
- [ ] 如果没有，执行字段添加 SQL
- [ ] 手动刷新页面（Cmd+R）
- [ ] 在浏览器 Console 中检查 authStore 状态

#### 后端无法启动
- [ ] 检查依赖是否安装：`pip install -r requirements.txt`
- [ ] 确认 8002 端口未被占用：`lsof -i :8002`
- [ ] 查看启动错误日志

#### API 无法调用
- [ ] 在浏览器 Network 标签页检查 `/api/auth/redeem-code` 请求
- [ ] 查看请求状态码和响应内容
- [ ] 检查后端日志是否有错误信息

### 📊 预期行为变化

| 场景 | 之前 | 现在 |
|------|------|------|
| 未登录 | 看 20 个节点 | 看 20 个节点 |
| 已登录非VIP | 看 20 个节点 | 看 20 个节点 |
| 已登录且兑换激活码 | 看 20 个节点（错误）| 看全部节点 ✅ |
| 刷新页面 | 状态丢失 | 状态保留 ✅ |
| 退出登录 | N/A | VIP 状态清除 ✅ |

### ✨ 完成标志

所有以下条件都达成时，说明设置完成：

- [ ] Supabase 中能查询到 activation_codes 表
- [ ] profiles 表有 vip_until 字段
- [ ] 后端能成功启动 `/api/auth/redeem-code` 端点
- [ ] 用户能输入激活码并点击兑换
- [ ] 兑换显示成功提示
- [ ] 刷新后 VIP 状态保留
- [ ] VIP 用户能看到全部节点

### 📞 问题反馈

如果遇到问题，请提供：
1. 截图（错误信息、节点数量等）
2. 浏览器控制台错误（F12 → Console）
3. 后端日志（运行时的输出）
4. 执行的 SQL 查询结果

---

**预计完成时间**: 15-20 分钟

**关键文件**:
- 📄 ACTIVATION_CODES_SETUP.sql - SQL 初始化脚本
- 📄 VIP_ACTIVATION_GUIDE.md - 详细指南
- 📄 VIP_FIX_SUMMARY.md - 技术总结
- 🐍 app_fastapi.py - 后端 API 实现
- 📱 authStore.js - 前端状态管理
- 🎨 AuthDropdown.vue - 前端 UI 组件
