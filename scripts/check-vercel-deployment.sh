#!/bin/bash
# Vercel 部署前检查脚本

echo "🔍 Vercel 部署前检查"
echo "===================="

# 检查必要文件
echo "📁 检查文件结构..."
files=("api/index.py" "vercel.json" "requirements.txt" "frontend/package.json")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file 存在"
    else
        echo "❌ $file 不存在"
    fi
done

echo ""
echo "🐍 检查 Python 环境..."
python3 --version
pip --version

echo ""
echo "📦 检查依赖..."
pip install -r requirements.txt --dry-run 2>/dev/null && echo "✅ requirements.txt 有效" || echo "❌ requirements.txt 有问题"

echo ""
echo "🌐 检查前端..."
cd frontend
npm --version
if npm run build --dry-run 2>/dev/null; then
    echo "✅ 前端构建配置正确"
else
    echo "❌ 前端构建配置有问题"
fi
cd ..

echo ""
echo "⚙️  检查环境变量..."
echo "请确保在 Vercel Dashboard 中设置："
echo "  - SUPABASE_URL"
echo "  - SUPABASE_KEY"

echo ""
echo "🚀 部署就绪！推送代码到 GitHub 即可自动部署。"