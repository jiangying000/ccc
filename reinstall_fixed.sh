#!/bin/bash
# 重新安装CCC

echo "🔧 重新安装CCC..."
echo "================================"

cd "$(dirname "$0")"

# 卸载旧版本
echo "📦 卸载旧版本..."
pip uninstall -y ccc 2>/dev/null || true

# 重新安装（开发模式）
echo "📦 安装开发版本..."
pip install -e .

echo ""
echo "✅ 安装完成！"
echo ""
echo "测试步骤："
echo "1. 运行: ccc"
echo "2. 选择一个会话"
echo "3. 按R恢复会话"
echo "4. 观察右下角是否有token显示"
echo ""
echo "如果仍无token，可尝试："
echo "  python3 ./fix_terminal_state.py"
echo "  选择不同的修复方案测试"