#!/bin/bash
# 测试CCDRC v1.2.0新功能

echo "🧪 测试CCDRC v1.2.0"
echo "════════════════════════════════════════"

# 测试交互模式（输入q退出）
echo ""
echo "1️⃣ 测试默认交互模式（输入q退出）："
echo "q" | ccdrc-extract --interactive 2>&1 | head -20

echo ""
echo "2️⃣ 测试直接索引模式："
ccdrc-extract --index 0 --stats 2>&1 | head -10

echo ""
echo "════════════════════════════════════════"
echo "✅ 测试完成"
echo ""
echo "主要改进："
echo "  • 默认交互选择（更直观）"
echo "  • 显示文件大小（KB/MB）"
echo "  • 显示消息数量"
echo "  • 显示token估算"
echo "  • 第一条消息预览"