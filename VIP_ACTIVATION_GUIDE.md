# VIP 激活码系统设置指南

## 问题描述

用户兑换激活码后，VIP 状态没有更新，无法看到所有节点。这是因为：

1. **缺少激活码数据库表** - Supabase 中没有 `activation_codes` 表
2. **后端 API 不完整** - 虽然已添加了 `/api/auth/redeem-code` 端点，但需要先创建表
3. **前端状态刷新** - 已修复，会自动调用 `checkVipStatus()` 更新用户状态

## 解决方案

### 第 1 步：在 Supabase 中创建激活码表

1. 打开 [Supabase 仪表板](https://app.supabase.com)
2. 选择您的项目
3. 进入 **SQL Editor**
4. 复制并执行 [ACTIVATION_CODES_SETUP.sql](./ACTIVATION_CODES_SETUP.sql) 中的 SQL 代码

**执行的 SQL 内容**：
- 创建 `activation_codes` 表
- 添加索引以提高查询效率
- 启用行级安全 (RLS)
- 插入 4 个测试激活码

### 第 2 步：验证表已创建

执行以下 SQL 查询，确认表和数据已创建：

```sql
SELECT code, vip_days, used, expires_at, notes 
FROM activation_codes 
ORDER BY created_at DESC;
```

应该看到 4 个测试激活码：
- `VIP7-2024-TEST-001` (7 天)
- `VIP30-2024-TEST-001` (30 天)
- `VIP90-2024-TEST-001` (90 天)
- `VIP365-2024-TEST-001` (1 年)

### 第 3 步：重启后端服务

如果后端已在运行，重启以加载新的激活码 API 端点：

```bash
pkill -f "app_fastapi.py"
cd /Users/ikun/study/Learning/viper-node-store
python app_fastapi.py
```

### 第 4 步：测试激活码兑换

1. 打开 http://localhost:5173 (或你的 viper-node-store 地址)
2. 点击 **🔐 登录** 按钮
3. 使用测试账户登录（或创建新账户）
4. 点击 **👤 账户** → **激活码** 选项卡
5. 输入测试激活码 `VIP7-2024-TEST-001`
6. 点击 **兑换激活码**

**预期结果**：
- ✅ 显示成功提示："恭喜！您已升级为 VIP 用户"
- ✅ 下拉面板自动关闭
- ✅ 导航栏的账户徽章变为 **⭐ VIP**
- ✅ 节点网格显示所有节点（不再限制 20 个）

## 工作原理

### 前端流程

```
用户输入激活码
    ↓
点击 "兑换激活码" 按钮
    ↓
AuthDropdown → authStore.redeemCode(code)
    ↓
调用 POST /api/auth/redeem-code
    ↓
后端验证并更新 VIP 状态
    ↓
authStore.checkVipStatus() 刷新本地状态
    ↓
authStore.isVip 变为 true
    ↓
NodeStore.displayedNodes 自动显示所有节点
```

### 后端 API

**端点**: `POST /api/auth/redeem-code`

**请求**:
```json
{
  "code": "VIP30-2024-TEST-001",
  "user_id": "user-uuid-here"
}
```

**响应（成功）**:
```json
{
  "status": "success",
  "message": "恭喜！您已升级为 VIP 用户，有效期至 2026-02-01",
  "vip_until": "2026-02-01T12:00:00"
}
```

**响应（失败）**:
```json
{
  "status": "error",
  "message": "激活码不存在或已过期"
}
```

## 激活码数据库字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `code` | VARCHAR(30) | 激活码（唯一） |
| `vip_days` | INT | 升级天数（默认 30） |
| `used` | BOOLEAN | 是否已被兑换 |
| `used_by` | UUID | 兑换者的用户 ID |
| `created_at` | TIMESTAMP | 创建时间 |
| `expires_at` | TIMESTAMP | 激活码过期时间 |
| `used_at` | TIMESTAMP | 兑换时间 |
| `notes` | TEXT | 备注（如 "7天 VIP 测试码"） |

## 常见问题排查

### 问题：兑换失败，显示 "激活码不存在"

**可能原因**：
1. activation_codes 表未创建 → 执行 ACTIVATION_CODES_SETUP.sql
2. 激活码拼写错误 → 检查激活码大小写
3. 激活码已过期 → 创建新的激活码

### 问题：兑换成功但 VIP 状态未更新

**可能原因**：
1. Supabase profiles 表没有 `vip_until` 字段 → 需要添加该字段
2. 前端没有刷新页面 → 自动 checkVipStatus() 应该会更新，如果没有，手动刷新

**添加 vip_until 字段的 SQL**:
```sql
ALTER TABLE profiles 
ADD COLUMN vip_until TIMESTAMP WITH TIME ZONE DEFAULT NULL;
```

### 问题：兑换显示成功，但节点列表仍只显示 20 个

**可能原因**：
1. 前端没有刷新 → 手动刷新页面 (Cmd+R)
2. AuthStore 的 `isVip` 状态没有更新 → 检查浏览器控制台是否有错误

**调试步骤**：
```javascript
// 在浏览器控制台执行
import { useAuthStore } from '/src/stores/authStore'
const auth = useAuthStore()
console.log('当前 VIP 状态:', auth.isVip)
console.log('VIP 过期时间:', auth.vipDate)
```

## 生产环境激活码管理

### 生成真实激活码

1. 在 Supabase SQL Editor 中执行：

```sql
INSERT INTO activation_codes (code, vip_days, notes) VALUES
  ('YOUR-CODE-1', 30, '1个月 VIP'),
  ('YOUR-CODE-2', 365, '1年 VIP')
RETURNING code, vip_days, expires_at;
```

2. 或通过 Python 脚本：

```bash
python init_activation_codes.py
```

### 监控激活码使用

```sql
-- 查看已使用的激活码
SELECT code, used_by, used_at, vip_days 
FROM activation_codes 
WHERE used = TRUE 
ORDER BY used_at DESC;

-- 查看即将过期的未使用激活码
SELECT code, vip_days, expires_at 
FROM activation_codes 
WHERE used = FALSE AND expires_at < NOW() + INTERVAL '7 days'
ORDER BY expires_at ASC;
```

## 文件清单

- ✅ **app_fastapi.py** - 已添加 `/api/auth/redeem-code` 端点
- ✅ **authStore.js** - 已更新 `redeemCode()` 调用后端 API
- ✅ **AuthDropdown.vue** - 已更新兑换成功后的处理
- ✅ **ACTIVATION_CODES_SETUP.sql** - Supabase SQL 初始化脚本
- ✅ **init_activation_codes.py** - Python 初始化脚本

## 下一步

1. ✅ 在 Supabase 中执行 SQL 脚本创建表
2. ✅ 重启后端服务
3. ✅ 测试激活码兑换功能
4. ✅ 验证 VIP 用户可以看到所有节点

---

如有问题，请检查：
- 浏览器控制台错误信息
- 后端日志 (看 app_fastapi.py 输出)
- Supabase 日志 (SQL Editor 中查看表数据)
