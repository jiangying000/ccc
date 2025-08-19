#!/bin/bash
# 测试各种安装方式

set -e

echo "🧪 测试CCDRC安装方式"
echo "════════════════════════════════════════"

# 测试目录
TEST_DIR="/tmp/ccdrc-test-$$"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo ""
echo "1️⃣ 测试uvx（无需安装）"
echo "─────────────────────────"
if command -v uvx &> /dev/null; then
    uvx --from /home/jy/gitr/jiangying000/ccdrc ccdrc-extract --help | head -3
    echo "✅ uvx测试通过"
else
    echo "⚠️  uvx未安装"
fi

echo ""
echo "2️⃣ 测试pipx安装"
echo "─────────────────────────"
if command -v pipx &> /dev/null; then
    pipx uninstall ccdrc 2>/dev/null || true
    pipx install /home/jy/gitr/jiangying000/ccdrc
    ~/.local/bin/ccdrc-extract --help | head -3
    echo "✅ pipx测试通过"
    pipx uninstall ccdrc
else
    echo "⚠️  pipx未安装"
fi

echo ""
echo "3️⃣ 测试uv tool安装"
echo "─────────────────────────"
if command -v uv &> /dev/null; then
    uv tool uninstall ccdrc 2>/dev/null || true
    uv tool install /home/jy/gitr/jiangying000/ccdrc
    ~/.local/bin/ccdrc-extract --help | head -3
    echo "✅ uv tool测试通过"
    uv tool uninstall ccdrc
else
    echo "⚠️  uv未安装"
fi

echo ""
echo "4️⃣ 测试wheel文件安装"
echo "─────────────────────────"
cd /home/jy/gitr/jiangying000/ccdrc
uv build --quiet
if [ -f dist/ccdrc-1.0.0-py3-none-any.whl ]; then
    echo "✅ Wheel文件构建成功: dist/ccdrc-1.0.0-py3-none-any.whl"
    echo "   大小: $(ls -lh dist/ccdrc-1.0.0-py3-none-any.whl | awk '{print $5}')"
else
    echo "❌ Wheel构建失败"
fi

echo ""
echo "5️⃣ 测试源码包安装"
echo "─────────────────────────"
if [ -f dist/ccdrc-1.0.0.tar.gz ]; then
    echo "✅ 源码包构建成功: dist/ccdrc-1.0.0.tar.gz"
    echo "   大小: $(ls -lh dist/ccdrc-1.0.0.tar.gz | awk '{print $5}')"
else
    echo "❌ 源码包构建失败"
fi

# 清理
rm -rf "$TEST_DIR"

echo ""
echo "════════════════════════════════════════"
echo "📊 测试总结"
echo ""
echo "项目已准备好通过以下方式分发："
echo ""
echo "  • GitHub: git+https://github.com/jiangying000/ccdrc.git"
echo "  • PyPI: ccdrc (需要先发布)"
echo "  • 本地: /home/jy/gitr/jiangying000/ccdrc"
echo ""
echo "支持的安装工具："
echo "  • pipx install ccdrc"
echo "  • uv tool install ccdrc"
echo "  • uvx ccdrc"
echo "  • pip install ccdrc"
echo ""
echo "✅ 所有测试完成！"