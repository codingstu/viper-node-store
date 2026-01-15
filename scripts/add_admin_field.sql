-- 为 profiles 表添加管理员字段
-- 运行此脚本前请确保已连接到正确的 Supabase 数据库

-- 1. 添加 is_admin 字段（如果不存在）
ALTER TABLE public.profiles 
ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;

-- 2. 创建索引以优化查询
CREATE INDEX IF NOT EXISTS idx_profiles_is_admin ON public.profiles (is_admin);

-- 3. 设置指定用户为管理员（替换 YOUR_USER_ID 为实际的用户 ID）
-- UPDATE public.profiles 
-- SET is_admin = TRUE 
-- WHERE id = 'YOUR_USER_ID';

-- 4. 或者通过邮箱设置管理员（需要先查询用户 ID）
-- 假设你想让 admin@example.com 成为管理员：
-- 
-- UPDATE public.profiles 
-- SET is_admin = TRUE 
-- WHERE id = (
--   SELECT id FROM auth.users WHERE email = 'admin@example.com'
-- );

-- 5. 查看当前管理员列表
-- SELECT p.id, u.email, p.is_admin, p.vip_until
-- FROM public.profiles p
-- JOIN auth.users u ON p.id = u.id
-- WHERE p.is_admin = TRUE;

COMMENT ON COLUMN public.profiles.is_admin IS '是否为管理员，管理员可执行健康检测等高级操作';
