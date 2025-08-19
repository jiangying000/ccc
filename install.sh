#!/bin/bash
# CCDRC - Claude Context Resume Tool
# 使用uv的快速安装脚本（不污染全局环境）

set -e

echo "🚀 安装 CCDRC (Claude Context Resume Tool)..."
echo "════════════════════════════════════════════"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装，请先安装Python3"
    exit 1
fi

# 安装uv（如果未安装）
if ! command -v uv &> /dev/null; then
    echo "⚡ 安装uv (超快包管理器)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    
    # 添加到shell配置
    for RC in ~/.bashrc ~/.zshrc; do
        if [ -f "$RC" ]; then
            grep -q '.cargo/bin' "$RC" || echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> "$RC"
        fi
    done
else
    echo "✅ uv已安装: $(uv --version)"
fi

# 创建安装目录（用户级，不污染系统）
INSTALL_DIR="$HOME/.local/share/ccdrc"
BIN_DIR="$HOME/.local/bin"

echo "📁 创建安装目录..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# 复制主程序
echo "📝 安装主程序..."
cp claude-smart-extract.py "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/claude-smart-extract.py"

# 创建pyproject.toml（用于uv依赖管理）
cat > "$INSTALL_DIR/pyproject.toml" << 'EOF'
[project]
name = "ccdrc"
version = "1.0.0"
description = "Claude Context Resume Tool - Smart context extraction"
dependencies = [
    "tiktoken>=0.5.0",
]

[tool.uv]
managed = true
dev-dependencies = []
EOF

# 创建ccdrc命令（使用uv run确保隔离环境）
cat > "$BIN_DIR/ccdrc" << 'EOF'
#!/bin/bash
# CCDRC - Claude Context Resume with Smart Compression
# 所有依赖通过uv管理，不污染全局环境

SCRIPT_DIR="$HOME/.local/share/ccdrc"
SCRIPT_PATH="$SCRIPT_DIR/claude-smart-extract.py"

# 确保uv在PATH中
export PATH="$HOME/.cargo/bin:$PATH"

# 默认参数
SESSION_INDEX=${1:-0}

# 检查Claude CLI
if ! command -v claude &> /dev/null; then
    echo "⚠️  Claude CLI未安装"
    echo "请访问: https://claude.ai/code"
    exit 1
fi

echo "════════════════════════════════════════════"
echo "🚀 CCDRC - Smart Context Resume"
echo "════════════════════════════════════════════"

# 使用uv run在隔离环境中运行（自动管理tiktoken依赖）
cd "$SCRIPT_DIR"
uv run python3 "$SCRIPT_PATH" --index "$SESSION_INDEX" --output /dev/stdout | claude --dangerously-skip-permissions
EOF

# 创建独立提取工具
cat > "$BIN_DIR/ccdrc-extract" << 'EOF'
#!/bin/bash
# 独立提取工具（不发送到Claude）

SCRIPT_DIR="$HOME/.local/share/ccdrc"
SCRIPT_PATH="$SCRIPT_DIR/claude-smart-extract.py"

export PATH="$HOME/.cargo/bin:$PATH"

cd "$SCRIPT_DIR"
uv run python3 "$SCRIPT_PATH" "$@"
EOF

# 创建交互式工具
cat > "$BIN_DIR/ccdrc-interactive" << 'EOF'
#!/bin/bash
# 交互式选择会话

SCRIPT_DIR="$HOME/.local/share/ccdrc"
SCRIPT_PATH="$SCRIPT_DIR/claude-smart-extract.py"

export PATH="$HOME/.cargo/bin:$PATH"

cd "$SCRIPT_DIR"
uv run python3 "$SCRIPT_PATH" --interactive --send
EOF

# 设置执行权限
chmod +x "$BIN_DIR/ccdrc"
chmod +x "$BIN_DIR/ccdrc-extract"
chmod +x "$BIN_DIR/ccdrc-interactive"

# 初始化uv环境（预安装依赖）
echo "⚡ 初始化隔离环境..."
cd "$INSTALL_DIR"
uv sync --no-dev 2>/dev/null || echo "将在首次运行时自动安装依赖"

# 验证安装
echo ""
echo "🧪 验证安装..."

# 测试tiktoken
if cd "$INSTALL_DIR" && uv run python3 -c "import tiktoken; print('✅ tiktoken可用')" 2>/dev/null; then
    echo "✅ 依赖已准备就绪"
else
    echo "⚠️  依赖将在首次运行时自动安装（约1秒）"
fi

# 更新PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "⚠️  请运行以下命令添加到PATH:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "  或添加到shell配置文件:"
    echo "    echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
fi

echo ""
echo "✅ 安装完成！"
echo ""
echo "📋 命令说明："
echo "  ccdrc              # 恢复最新会话"
echo "  ccdrc 1            # 恢复第2新会话"
echo "  ccdrc-extract      # 提取但不发送"
echo "  ccdrc-interactive  # 交互式选择"
echo ""
echo "🎯 特性："
echo "  • 🔒 完全隔离环境（不污染全局）"
echo "  • ⚡ uv超快依赖管理"
echo "  • 📊 智能上下文压缩"
echo "  • 🎯 精确token计算"
echo ""
echo "📦 安装位置："
echo "  程序: $INSTALL_DIR"
echo "  命令: $BIN_DIR"