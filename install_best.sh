#!/bin/bash
# CCC最佳实践安装脚本
# 自动选择最合适的安装方法

set -e

echo "🚀 CCC智能安装脚本"
echo "================================"
echo ""

# 检测系统类型
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="Mac"
else
    OS="Unknown"
fi

# 检测是否在Docker中
if [ -f /.dockerenv ]; then
    IN_DOCKER=true
else
    IN_DOCKER=false
fi

# 检测是否有PEP 668保护
HAS_PEP668=false
if [ -f /usr/lib/python3*/EXTERNALLY-MANAGED ]; then
    HAS_PEP668=true
fi

echo "📊 系统检测："
echo "  - 操作系统: $OS"
echo "  - Docker环境: $IN_DOCKER"  
echo "  - PEP 668保护: $HAS_PEP668"
echo ""

# 检测可用工具
HAS_PIPX=false
HAS_UV=false

if command -v pipx &> /dev/null; then
    HAS_PIPX=true
    echo "✅ 检测到 pipx"
fi

if command -v uv &> /dev/null; then
    HAS_UV=true
    echo "✅ 检测到 uv"
fi

echo ""
echo "🎯 推荐安装方案："
echo ""

# 推荐方案
if [ "$IN_DOCKER" = true ]; then
    echo "Docker环境 → 使用 pip --break-system-packages"
    METHOD="docker"
elif [ "$HAS_UV" = true ]; then
    echo "检测到uv → 使用 uv tool（最快）"
    METHOD="uv"
elif [ "$HAS_PIPX" = true ]; then
    echo "检测到pipx → 使用 pipx（最安全）"
    METHOD="pipx"
elif [ "$HAS_PEP668" = true ]; then
    echo "PEP 668环境 → 使用虚拟环境"
    METHOD="venv"
else
    echo "标准环境 → 使用pip直接安装"
    METHOD="pip"
fi

echo ""
echo "可选方案："
echo "  1) pipx安装（推荐）"
echo "  2) 虚拟环境安装"
echo "  3) uv工具安装"
echo "  4) pip强制安装（不推荐）"
echo "  5) 使用推荐方案（$METHOD）"
echo ""

read -p "请选择安装方案 (1-5，默认5): " choice
choice=${choice:-5}

# 安装函数
install_with_pipx() {
    echo "📦 使用pipx安装..."
    
    # 安装pipx（如果需要）
    if ! command -v pipx &> /dev/null; then
        echo "正在安装pipx..."
        if [[ "$OS" == "Linux" ]]; then
            sudo apt update
            sudo apt install -y pipx
        elif [[ "$OS" == "Mac" ]]; then
            brew install pipx
        fi
        pipx ensurepath
        export PATH="$HOME/.local/bin:$PATH"
    fi
    
    # 安装CCC（当前仓库）
    pipx install -e "$(pwd)"
    echo "✅ 安装完成！"
    echo "运行: ccc"
}

install_with_venv() {
    echo "📦 使用虚拟环境安装..."
    
    # 进入当前仓库
    cd "$(pwd)"
    
    # 创建虚拟环境
    python3 -m venv .venv
    source .venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装
    pip install -e .
    
    # 创建命令链接
    mkdir -p ~/.local/bin
    ln -sf "$(pwd)/.venv/bin/ccc" ~/.local/bin/ccc
    
    deactivate
    
    echo "✅ 安装完成！"
    echo "运行: ccc"
    echo "提示: 添加 ~/.local/bin 到PATH"
}

install_with_uv() {
    echo "📦 使用uv安装..."
    
    # 安装uv（如果需要）
    if ! command -v uv &> /dev/null; then
        echo "正在安装uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source ~/.bashrc
    fi
    
    # 安装CCC（当前仓库）
    uv tool install .
    
    echo "✅ 安装完成！"
    echo "运行: ccc"
}

install_with_pip_force() {
    echo "⚠️  使用pip强制安装（不推荐）..."
    
    pip install -e . --break-system-packages
    
    echo "✅ 安装完成！"
    echo "运行: ccc"
    echo "⚠️  警告：这可能影响系统稳定性"
}

# 执行安装
case $choice in
    1)
        install_with_pipx
        ;;
    2)
        install_with_venv
        ;;
    3)
        install_with_uv
        ;;
    4)
        install_with_pip_force
        ;;
    5)
        case $METHOD in
            "pipx")
                install_with_pipx
                ;;
            "venv")
                install_with_venv
                ;;
            "uv")
                install_with_uv
                ;;
            "docker"|"pip")
                install_with_pip_force
                ;;
        esac
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac

echo ""
echo "🎉 安装脚本执行完成！"
echo ""
echo "下一步："
echo "1. 如果命令找不到，执行: source ~/.bashrc 或 source ~/.zshrc"
echo "2. 测试: ccc --stats"
echo "3. 查看文档: cat INSTALLATION_BEST_PRACTICES.md"