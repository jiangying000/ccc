#!/bin/bash
# 重新安装修复后的CCDRC

echo "🔧 重新安装修复后的CCDRC..."
echo "================================"

cd /home/jy/gitr/jiangying000/ccdrc

# 卸载旧版本
echo "📦 卸载旧版本..."
pip uninstall -y ccdrc 2>/dev/null || true

# 重新安装（开发模式）
echo "📦 安装修复版本..."
pip install -e .

echo ""
echo "✅ 安装完成！"
echo ""
echo "测试步骤："
echo "1. 运行: ccdrc"
echo "2. 选择一个会话"
echo "3. 按R恢复会话"
echo "4. 观察右下角是否有token显示"
echo ""
echo "如果仍无token，可尝试："
echo "  python3 /home/jy/gitr/jiangying000/ccdrc/fix_terminal_state.py"
echo "  选择不同的修复方案测试"