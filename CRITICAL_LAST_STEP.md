# ⚠️ 激活码系统 - 关键的最后一步

## 📌 当前状态

- ✅ 后端 API 端点已实现 (`/api/auth/redeem-code`)
- ✅ 前端已更新为调用后端 API
- ✅ 后端和前端都已重启
- ⏳ **还需要**：在 Supabase 中创建 `activation_codes` 表

## 🔴 缺失的环节

`activation_codes` 表还不存在于 Supabase 数据库中。

当用户尝试兑换激活码时，后端会尝试查询这个表，但会收到 "table not found" 的错误。

## ✅ 必须执行的最后一步（5分钟）

### 方法 1: 在 Supabase 仪表板中执行 SQL（推荐）

1. 打开 https://app.supabase.com
2. 选择您的项目
3. 点击左侧 **SQL Editor**
4. 点击 **New Query**
5. 复制以下 SQL 代码

**完整 SQL 脚本**（复制全部）：

```sql
-- ===== Supabase SQL: 创建激活码系统 =====
-- 在 Supabase 仪表板的 SQL 编辑器中执行此脚本

-- 创建激活码表
CREATE TABLE IF NOT EXISTS activation_codes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    code VARCHAR(30) UNIQUE NOT NULL,
    vip_days INT DEFAULT 30,
    used BOOLEAN DEFAULT FALSE,
    used_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '90 days'),
    used_at TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    created_by VARCHAR(255)
);

-- 创建索引以提高查询效率
CREATE INDEX IF NOT EXISTS idx_activation_codes_code ON activation_codes(code);
CREATE INDEX IF NOT EXISTS idx_activation_codes_used ON activation_codes(used);
CREATE INDEX IF NOT EXISTS idx_activation_codes_expires_at ON activation_codes(expires_at);

-- 向 activation_codes 表启用 RLS
ALTER TABLE activation_codes ENABLE ROW LEVEL SECURITY;

-- 创建 RLS 策略
CREATE POLICY "Allow public to query activation codes" 
  ON activation_codes FOR SELECT 
  TO public 
  USING (NOT used);

-- ===== 插入测试激活码 =====
INSERT INTO activation_codes (code, vip_days, notes, created_by) VALUES
  ('VIP7-2024-TEST-001', 7, '7天 VIP 测试码', 'system'),
  ('VIP30-2024-TEST-001', 30, '30天 VIP 测试码', 'system'),
  ('VIP90-2024-TEST-001', 90, '90天 VIP 测试码', 'system'),
  ('VIP365-2024-TEST-001', 365, '1年 VIP 测试码', 'system')
ON CONFLICT (code) DO NOTHING;
```

6. 点击 **Run** 按钮执行
7. 应该看到 "Success" 提示

### 验证表已创建

在同一 SQL Editor 中执行：

```sql
SELECT code, vip_days, used, created_at 
FROM activation_codes 
ORDER BY created_at DESC;
```

应该看到 4 个测试激活码

## ✨ 执行后的效果

执行完 SQL 脚本后：

1. ✅ `activation_codes` 表已创建
2. ✅ 4 个测试激活码已插入
3. ✅ 索引已创建（提高查询性能）
4. ✅ RLS 策略已配置（安全访问）
5. ✅ 后端 API 现在能够：
   - 查询激活码是否存在
   - 检查激活码是否已使用
   - 验证激活码未过期
   - 更新用户 VIP 状态
   - 标记激活码为已使用

## 🎯 完整流程确认

```
用户打开 http://localhost:5174
  ↓
点击 🔐 登录 → 登录成功
  ↓
点击 👤 账户 → 激活码 标签页
  ↓
输入激活码: VIP30-2024-TEST-001
  ↓
点击 "兑换激活码"
  ↓
前端发送: POST /api/auth/redeem-code
  ↓
后端流程:
  1. 查询 activation_codes 表 ← 需要表存在！
  2. 验证激活码有效
  3. 更新 profiles.vip_until
  4. 标记激活码为已使用
  5. 返回成功
  ↓
前端刷新 VIP 状态
  ↓
✅ 显示成功，账户变为 ⭐ VIP
```

## 📋 3 个必要条件

| 条件 | 状态 | 说明 |
|------|------|------|
| 后端 API 实现 | ✅ 完成 | `/api/auth/redeem-code` 已实现 |
| 前端代码更新 | ✅ 完成 | authStore.redeemCode() 已改用 API |
| 数据库表创建 | ⏳ 需要 | SQL 脚本还未在 Supabase 执行 |

## ⚠️ 警告

**如果不执行 SQL 脚本**，用户兑换时会看到错误：
```
{
  "status": "error",
  "message": "更新 VIP 状态失败: relation \"activation_codes\" does not exist"
}
```

## 🚀 现在就做！

1. 打开 https://app.supabase.com
2. 进入 SQL Editor
3. 复制上面的 SQL 脚本
4. 点击 Run
5. 等待 "Success" 提示
6. 回到浏览器，测试激活码兑换！

---

**预计耗时**：3-5 分钟

**不需要重启任何服务** - 只需要创建表

**创建完成后立即可用** - 前端和后端都已准备好！
