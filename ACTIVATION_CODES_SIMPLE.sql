-- ===== 简化版：只创建表和插入数据 =====

-- 1. 创建激活码表（最小化版本）
CREATE TABLE IF NOT EXISTS activation_codes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    code VARCHAR(30) UNIQUE NOT NULL,
    vip_days INT DEFAULT 30,
    used BOOLEAN DEFAULT FALSE,
    used_by UUID DEFAULT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '90 days',
    used_at TIMESTAMP DEFAULT NULL,
    notes TEXT DEFAULT NULL
);

-- 2. 创建索引
CREATE INDEX IF NOT EXISTS idx_activation_codes_code ON activation_codes(code);
CREATE INDEX IF NOT EXISTS idx_activation_codes_used ON activation_codes(used);

-- 3. 插入测试激活码
INSERT INTO activation_codes (code, vip_days, notes) VALUES
  ('VIP7-2024-TEST-001', 7, '7天 VIP 测试码'),
  ('VIP30-2024-TEST-001', 30, '30天 VIP 测试码'),
  ('VIP90-2024-TEST-001', 90, '90天 VIP 测试码'),
  ('VIP365-2024-TEST-001', 365, '1年 VIP 测试码')
ON CONFLICT (code) DO NOTHING;

-- 4. 验证：查询激活码数量
SELECT COUNT(*) as 激活码总数 FROM activation_codes;
SELECT code, vip_days, used FROM activation_codes ORDER BY created_at DESC;
