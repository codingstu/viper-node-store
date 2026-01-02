# 🔥 VIP 激活码 - 现在就做（3 步，10 分钟）

## ✅ 当前状态
- 前端 ✅ 已重启
- 后端 ✅ 已重启  
- API 端点 ✅ 已实现
- 还缺什么？ → **数据库表**

## 🚀 Step 1: 创建数据库表（5 分钟）

### 打开 Supabase SQL Editor

1. 访问 https://app.supabase.com
2. 选择你的项目（viper-node-store）
3. 点击左侧菜单 → **SQL Editor**
4. 点击 **New Query** 或 **Create New**

### 复制并执行这段 SQL

复制下面的代码，粘贴到 SQL Editor 中，然后点 **Run**：

```sql
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

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_activation_codes_code ON activation_codes(code);
CREATE INDEX IF NOT EXISTS idx_activation_codes_used ON activation_codes(used);

-- 启用 RLS
ALTER TABLE activation_codes ENABLE ROW LEVEL SECURITY;

-- 创建策略
CREATE POLICY "Allow public to query activation codes" 
  ON activation_codes FOR SELECT TO public USING (NOT used);

-- 插入测试激活码
INSERT INTO activation_codes (code, vip_days, notes, created_by) VALUES
  ('VIP7-2024-TEST-001', 7, '7天 VIP', 'system'),
  ('VIP30-2024-TEST-001', 30, '30天 VIP', 'system'),
  ('VIP90-2024-TEST-001', 90, '90天 VIP', 'system'),
  ('VIP365-2024-TEST-001', 365, '1年 VIP', 'system')
ON CONFLICT (code) DO NOTHING;
```

### 点击 Run ⚙️

等待看到：✅ **Success**

## 🔍 Step 2: 验证表已创建（1 分钟）

在同一 SQL Editor 中，执行这条查询：

```sql
SELECT code, vip_days FROM activation_codes;
```

应该看到 4 个激活码：
```
VIP7-2024-TEST-001     | 7
VIP30-2024-TEST-001    | 30
VIP90-2024-TEST-001    | 90
VIP365-2024-TEST-001   | 365
```

## 🧪 Step 3: 测试兑换（3 分钟）

1. **刷新浏览器**
   - 打开 http://localhost:5174
   - 按 Cmd+R (Mac) 或 Ctrl+R (Windows)

2. **登录账户**
   - 点击 🔐 登录
   - 创建测试账户或使用已有账户

3. **进入激活码页面**
   - 点击 👤 账户 按钮
   - 选择 **激活码** 标签页

4. **输入测试激活码**
   - 输入：`VIP30-2024-TEST-001`
   - 点击 **兑换激活码**

5. **验证成功**
   - ✅ 看到成功提示
   - ✅ 账户徽章变为 ⭐ VIP
   - ✅ 下拉面板自动关闭

6. **刷新页面确认**
   - 按 Cmd+R 刷新
   - 确认仍显示为 VIP（状态已保存）
   - 确认节点列表显示全部节点

## 🎉 完成！

所有 3 步完成后，VIP 激活码系统已全面工作！

## 📍 文件位置

如果你想查看完整的 SQL 脚本，可以打开：
- `/Users/ikun/study/Learning/viper-node-store/ACTIVATION_CODES_SETUP.sql`

## 🆘 遇到问题？

### 问题：SQL 执行失败
- 确保复制了完整的 SQL
- 检查 Supabase 控制台右侧是否有错误提示
- 尝试逐个执行 SQL 块

### 问题：还是看到 404 错误
- 刷新浏览器：Cmd+R 或 Ctrl+R
- 打开浏览器开发者工具 (F12)
- 清除缓存：Network → 勾选 "Disable cache"

### 问题：激活码不被识别
- 检查大小写（应为全大写）
- 确认 activation_codes 表已创建
- 在 Supabase SQL Editor 中验证激活码是否存在

---

**预计总耗时：10 分钟**

**现在就开始吧！** 🚀
