#!/bin/bash
# CCC - Claude Context Companion
# 简单安装指引脚本（推荐使用 pipx / pip / uvx 安装 ccc 命令）

set -e

echo "🚀 安装 CCC (Claude Context Companion)..."
echo "════════════════════════════════════════════"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装，请先安装Python3"
    exit 1
fi

echo ""
echo "推荐安装方式："
echo "─────────────────────────"
echo "1) pipx（推荐）:   pipx install ."
echo "2) pip:           pip install -e .  或  pip install ."
echo "3) uvx（免安装）: uvx --from . ccc --stats"
echo ""
echo "或直接遵循 README.md 的安装指南。"
echo ""
echo "执行检测："
echo "─────────────────────────"
if command -v ccc &> /dev/null; then
    echo "✅ 已检测到 ccc 命令，可直接运行: ccc"
else
    echo "ℹ️  未检测到 ccc 命令，请使用上面任一方式安装。"
fi
echo ""
echo "完成。"