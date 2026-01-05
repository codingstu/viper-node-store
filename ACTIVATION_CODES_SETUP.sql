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

-- 向 profiles 表添加 RLS 策略（如果尚未添加）
ALTER TABLE activation_codes ENABLE ROW LEVEL SECURITY;

-- 创建 RLS 策略
-- 允许匿名用户查询激活码（用于验证）
CREATE POLICY "Allow public to query activation codes" 
  ON activation_codes FOR SELECT 
  TO public 
  USING (NOT used);

-- 只允许认证用户更新自己的 VIP 状态
CREATE POLICY "Allow users to read own profile" 
  ON profiles FOR SELECT 
  TO authenticated 
  USING (auth.uid() = id);

-- ===== 插入测试激活码 =====
INSERT INTO activation_codes (code, vip_days, notes, created_by) VALUES
  ('VIP7-2024-TEST-001', 7, '7天 VIP 测试码', 'system'),
  ('VIP30-2024-TEST-001', 30, '30天 VIP 测试码', 'system'),
  ('VIP90-2024-TEST-001', 90, '90天 VIP 测试码', 'system'),
  ('VIP365-2024-TEST-001', 365, '1年 VIP 测试码', 'system')
ON CONFLICT (code) DO NOTHING;

-- ===== 查询现有激活码 =====
SELECT 
  code,
  vip_days,
  used,
  created_at,
  expires_at,
  notes
FROM activation_codes
ORDER BY created_at DESC;
