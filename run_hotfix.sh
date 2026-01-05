#!/bin/bash
# 🚀 Viper Node Store - 快速修复执行脚本
# 用于完成两个严重问题的修复

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         🚀 Viper Node Store 快速修复执行指南 v1.0            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# 检查当前工作目录
if [ ! -f "update_nodes.py" ]; then
    echo "❌ 错误: 请在 viper-node-store 目录中运行此脚本"
    echo "   cd /Users/ikun/study/Learning/viper-node-store"
    exit 1
fi

echo "✅ 工作目录确认: $(pwd)"
echo ""

# ============= 第1步: Supabase 数据库修改 =============
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ 步骤 1: 在 Supabase 中添加 link 字段                             │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""
echo "请手动执行以下步骤:"
echo ""
echo "1. 打开 https://supabase.com/dashboard"
echo "2. 进入 SQL Editor"
echo "3. 复制粘贴以下 SQL 命令:"
echo ""
echo "========== 开始复制 =========="
cat << 'SQLEOF'
ALTER TABLE nodes 
ADD COLUMN IF NOT EXISTS link TEXT DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_nodes_link ON nodes(link);
SQLEOF
echo "========== 结束复制 =========="
echo ""
echo "4. 点击 Run 执行"
echo ""
read -p "按 Enter 继续... (完成 Supabase SQL 后)"
echo ""

# ============= 第2步: 数据同步 =============
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ 步骤 2: 同步节点数据到 Supabase                                 │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""
echo "选择同步方式:"
echo ""
echo "  选项 A (推荐): 启动 SpiderFlow 后端 + 运行同步脚本"
echo "  选项 B: 使用迁移脚本 (SpiderFlow 不可用时)"
echo ""
echo "如果选择 A，需要在两个终端中执行:"
echo ""
echo "------- 终端 1 -------"
echo "cd /Users/ikun/study/Learning/SpiderFlow/backend"
echo "python main.py"
echo ""
echo "------- 终端 2 -------"
echo "cd /Users/ikun/study/Learning/viper-node-store"
echo "python update_nodes.py"
echo ""
echo "如果选择 B，执行:"
echo "python3 fix_link_field.py"
echo ""
read -p "选择 (A/B): " CHOICE

case $CHOICE in
  [Aa]*)
    echo "你选择了选项 A (手动启动 SpiderFlow)"
    echo "请确保 SpiderFlow 和 update_nodes.py 都已运行"
    ;;
  [Bb]*)
    echo "你选择了选项 B (使用迁移脚本)"
    echo "运行: python3 fix_link_field.py"
    python3 fix_link_field.py
    ;;
  *)
    echo "❌ 无效选择"
    exit 1
    ;;
esac

echo ""
read -p "按 Enter 继续... (完成数据同步后)"
echo ""

# ============= 第3步: 浏览器刷新 =============
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ 步骤 3: 刷新浏览器                                              │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""
echo "请在浏览器中打开: http://localhost:5174"
echo "然后强制刷新: Cmd+Shift+R (Mac) 或 Ctrl+Shift+R (Windows)"
echo ""
read -p "按 Enter 继续... (完成浏览器刷新后)"
echo ""

# ============= 第4步: 功能验证 =============
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ 步骤 4: 验证修复 ✅                                             │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""
echo "🔵 测试清单:"
echo ""
echo "□ 登录功能"
echo "  □ 点击 [注册] 按钮"
echo "  □ 输入邮箱和密码"
echo "  □ 验证邮箱后登录"
echo "  □ 登录后 [👤 账户] 按钮可以点击"
echo ""
echo "□ 节点功能"
echo "  □ 找到任意一个节点卡片"
echo "  □ [📋 COPY] 按钮已启用 (之前是灰色禁用)"
echo "  □ [📱 QR CODE] 按钮已启用"
echo "  □ 点击 COPY 能复制链接"
echo "  □ 点击 QR CODE 能生成二维码"
echo ""
echo "□ VIP 功能"
echo "  □ 点击 [👤 账户] → [VIP 激活]"
echo "  □ 输入激活码 (如有测试码)"
echo "  □ VIP 徽章显示正确"
echo ""
echo "□ 导出功能"
echo "  □ 点击 [⬇️ 导出] 能下载节点配置"
echo ""

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "✅ 修复完成!"
echo ""
echo "如果所有测试都通过,说明问题已解决。"
echo "如果仍有问题,请检查:"
echo "  1. Supabase SQL 是否执行成功"
echo "  2. 数据同步是否完成"
echo "  3. 浏览器控制台 (F12) 是否有错误信息"
echo ""
echo "详细文档: HOTFIX_GUIDE.md 或 QUICK_FIX_CHECKLIST.md"
echo "════════════════════════════════════════════════════════════════════"
