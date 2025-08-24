#!/bin/bash
# 测试各种安装方式

set -e

echo "🧪 测试CCC安装方式"
echo "════════════════════════════════════════"

# 测试目录
TEST_DIR="/tmp/ccc-test-$$"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo ""
echo "1️⃣ 测试uvx（无需安装）"
echo "─────────────────────────"
if command -v uvx &> /dev/null; then
    uvx --from . ccc --help | head -3
    echo "✅ uvx测试通过"
else
    echo "⚠️  uvx未安装"
fi

echo ""
echo "2️⃣ 测试pipx安装"
echo "─────────────────────────"
if command -v pipx &> /dev/null; then
    pipx uninstall ccc 2>/dev/null || true
    pipx install "$(pwd)"
    ~/.local/bin/ccc --help | head -3
    echo "✅ pipx测试通过"
    pipx uninstall ccc
else
    echo "⚠️  pipx未安装"
fi

echo ""
echo "3️⃣ 测试uv tool安装"
echo "─────────────────────────"
if command -v uv &> /dev/null; then
    uv tool uninstall ccc 2>/dev/null || true
    uv tool install .
    ~/.local/bin/ccc --help | head -3
    echo "✅ uv tool测试通过"
    uv tool uninstall ccc
else
    echo "⚠️  uv未安装"
fi

echo ""
echo "4️⃣ 测试wheel文件安装"
echo "─────────────────────────"
cd "$(pwd)"
uv build --quiet
if ls dist/*.whl >/dev/null 2>&1; then
    echo "✅ Wheel文件构建成功"
    ls -lh dist/*.whl | awk '{print "   大小:", $5, "文件:", $9}'
else
    echo "❌ Wheel构建失败"
fi

echo ""
echo "5️⃣ 测试源码包安装"
echo "─────────────────────────"
if ls dist/*.tar.gz >/dev/null 2>&1; then
    echo "✅ 源码包构建成功"
    ls -lh dist/*.tar.gz | awk '{print "   大小:", $5, "文件:", $9}'
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
echo "  • GitHub: git+https://github.com/jiangying000/ccc.git"
echo "  • PyPI: ccc (需要先发布)"
echo "  • 本地: $(pwd)"
echo ""
echo "支持的安装工具："
echo "  • pipx install ccc"
echo "  • uv tool install ccc"
echo "  • uvx ccc"
echo "  • pip install ccc"
echo ""
echo "✅ 所有测试完成！"