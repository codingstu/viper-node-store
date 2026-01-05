-- =====================================================
-- Supabase 健康检测字段迁移脚本
-- 
-- 在 Supabase SQL Editor 中执行此脚本
-- 为 nodes 表添加健康检测所需的字段
-- =====================================================

-- 1. 添加 status 字段（节点状态：online/offline/suspect/unknown）
ALTER TABLE public.nodes 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'unknown';

-- 2. 添加 last_health_check 字段（最后健康检测时间）
ALTER TABLE public.nodes 
ADD COLUMN IF NOT EXISTS last_health_check TIMESTAMP WITH TIME ZONE;

-- 3. 添加 health_latency 字段（健康检测时的延迟）
ALTER TABLE public.nodes 
ADD COLUMN IF NOT EXISTS health_latency INTEGER;

-- 4. 创建索引以加速按状态查询
CREATE INDEX IF NOT EXISTS idx_nodes_status ON public.nodes(status);

-- 5. 创建索引以加速按检测时间排序（优先检测最久未检测的节点）
CREATE INDEX IF NOT EXISTS idx_nodes_last_health_check ON public.nodes(last_health_check NULLS FIRST);

-- 6. 添加注释
COMMENT ON COLUMN public.nodes.status IS '节点健康状态: online=在线, offline=离线, suspect=可疑, unknown=未检测';
COMMENT ON COLUMN public.nodes.last_health_check IS '最后一次健康检测的时间';
COMMENT ON COLUMN public.nodes.health_latency IS '健康检测时的TCP连接延迟（毫秒）';

-- =====================================================
-- 验证字段是否添加成功
-- =====================================================
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'nodes' 
AND column_name IN ('status', 'last_health_check', 'health_latency');
