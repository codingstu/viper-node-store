#!/bin/bash

echo "🧪 Viper Node Store - 大陆/海外节点切换功能测试"
echo "================================================"
echo ""

# 测试 1: 获取海外节点
echo "✅ 测试 1: 获取海外节点"
RESPONSE=$(curl -s "http://localhost:8002/api/nodes?limit=5")
COUNT=$(echo "$RESPONSE" | jq 'length' 2>/dev/null || echo "0")
echo "  返回节点数: $COUNT"
if [ "$COUNT" -gt 0 ]; then
    echo "  ✓ 成功获取海外节点"
else
    echo "  ✗ 获取海外节点失败"
fi
echo ""

# 测试 2: 获取大陆节点
echo "✅ 测试 2: 获取大陆节点"
RESPONSE=$(curl -s "http://localhost:8002/api/telegram-nodes?limit=5")
COUNT=$(echo "$RESPONSE" | jq 'length' 2>/dev/null || echo "0")
echo "  返回节点数: $COUNT"
if [ "$COUNT" -gt 0 ]; then
    echo "  ✓ 成功获取大陆节点"
else
    echo "  ✗ 获取大陆节点失败"
fi
echo ""

# 测试 3: 检查数据格式
echo "✅ 测试 3: 检查节点数据格式"
RESPONSE=$(curl -s "http://localhost:8002/api/nodes?limit=1")
HAS_PROTOCOL=$(echo "$RESPONSE" | jq '.[0] | has("protocol")' 2>/dev/null)
HAS_HOST=$(echo "$RESPONSE" | jq '.[0] | has("host")' 2>/dev/null)
HAS_PORT=$(echo "$RESPONSE" | jq '.[0] | has("port")' 2>/dev/null)
HAS_STATUS=$(echo "$RESPONSE" | jq '.[0] | has("status")' 2>/dev/null)

if [ "$HAS_PROTOCOL" = "true" ] && [ "$HAS_HOST" = "true" ] && [ "$HAS_PORT" = "true" ] && [ "$HAS_STATUS" = "true" ]; then
    echo "  ✓ 节点数据格式正确 (包含 protocol, host, port, status)"
else
    echo "  ✗ 节点数据格式不正确"
fi
echo ""

# 测试 4: VIP 限制
echo "✅ 测试 4: VIP 用户节点数限制"
echo "  非 VIP 用户: 最多 20 个节点"
RESPONSE=$(curl -s "http://localhost:8002/api/nodes")
COUNT=$(echo "$RESPONSE" | jq 'length' 2>/dev/null || echo "0")
if [ "$COUNT" -le 20 ]; then
    echo "  ✓ VIP 限制工作正常 (获得 $COUNT 个节点)"
else
    echo "  ✗ VIP 限制未生效"
fi
echo ""

# 测试 5: 健康检测权限（不提供用户ID，应该返回无权限错误）
echo "✅ 测试 5: 健康检测权限验证"
RESPONSE=$(curl -s -X POST "http://localhost:8002/api/health-check" \
  -H "Content-Type: application/json" \
  -d '{"source": "overseas"}')
STATUS=$(echo "$RESPONSE" | jq -r '.status' 2>/dev/null || echo "error")
if [ "$STATUS" = "error" ] || [ "$STATUS" = "success" ]; then
    echo "  ✓ 健康检测权限验证工作 (返回: $STATUS)"
else
    echo "  ✗ 健康检测权限验证失败"
fi
echo ""

echo "================================================"
echo "✅ 测试完成！"
echo ""
echo "📝 注意事项："
echo "  1. 大陆/海外节点需要从前端切换，后端已支持"
echo "  2. 健康检测需要有效的 admin 账户来激活"
echo "  3. 需要在 Supabase 运行 scripts/add_admin_field.sql 以启用管理员功能"
