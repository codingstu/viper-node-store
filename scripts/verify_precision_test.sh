#!/bin/bash
# 精确测速 API 验证脚本

echo "======================================"
echo "精确测速 API 快速验证"
echo "======================================"
echo ""

# 检查后端是否运行
echo "📋 检查后端服务..."
if curl -s -m 2 http://localhost:8002/api/nodes >/dev/null 2>&1; then
    echo "✅ 后端服务已运行"
else
    echo "❌ 后端服务未运行"
    echo ""
    echo "启动后端:"
    echo "  cd /Users/ikun/study/Learning/viper-node-store"
    echo "  python app_fastapi.py"
    exit 1
fi

echo ""
echo "📊 测试精确测速 API..."
echo ""

# 发送测试请求
RESPONSE=$(curl -s -X POST http://localhost:8002/api/nodes/precision-test \
  -H "Content-Type: application/json" \
  -d '{"proxy_url": "test://example.com", "test_file_size": 10}' 2>&1)

echo "响应结果:"
echo "$RESPONSE" | python -m json.tool 2>/dev/null || echo "$RESPONSE"

echo ""
echo "======================================"

# 检查响应状态
if echo "$RESPONSE" | grep -q '"status"'; then
    echo "✅ API 响应正常"
    if echo "$RESPONSE" | grep -q '"error"' || echo "$RESPONSE" | grep -q '"timeout"'; then
        echo "⚠️  返回错误状态（这可能是网络问题）"
    else
        echo "✅ 测速逻辑执行"
    fi
else
    echo "❌ API 响应异常"
fi

echo "======================================"
echo ""
echo "📝 验证步骤:"
echo "1. 打开 http://localhost:8002 在浏览器"
echo "2. 找到一个节点"
echo "3. 点击 ⚡ 按钮启动精确测速"
echo "4. 应该看到进度条和结果"
echo ""
