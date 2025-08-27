# CCC - Claude Context Resume Tool

[![CI](https://github.com/jiangying000/ccc/actions/workflows/ci.yml/badge.svg)](https://github.com/jiangying000/ccc/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/ccc.svg)](https://badge.fury.io/py/ccc)
[![Python Support](https://img.shields.io/pypi/pyversions/ccc.svg)](https://pypi.org/project/ccc/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

智能提取和恢复Claude Code对话上下文的工具，优化token使用，支持超长对话的高效续接。

## ⚡ 快速安装（推荐：uv）

优先使用 uv（更快、更稳、隔离好）。从 PyPI 安装稳定版：

```bash
# 安装（推荐）
uv tool install ccc

# 升级
uv tool upgrade ccc

# 卸载
uv tool uninstall ccc
```

从 GitHub 指定版本（建议固定到 tag）安装：

```bash
# 将 vX.Y.Z 替换为发布的版本标签
uv tool install 'git+https://github.com/jiangying000/ccc.git@vX.Y.Z'
```

无需安装的临时运行（CI/一次性使用）：

```bash
# 从 PyPI 直接运行
uvx ccc --stats

# 从 GitHub 指定版本临时运行
uvx --from 'git+https://github.com/jiangying000/ccc.git@vX.Y.Z' ccc --stats
```

## ✨ 特性

- 🚀 **智能交互**: 无参数时自动进入会话选择界面
- 📊 **丰富信息**: 显示大小、消息数、tokens、内容预览
- ✅ **双重确认**: 选择后预览，发送前确认
- 🎯 **智能压缩**: 自动识别并保留关键信息
- ⚡ **超快安装**: 使用uv包管理器，比pip快10-100倍
- 🔒 **环境隔离**: 不污染全局Python环境
- 📊 **精确计算**: 使用tiktoken精确计算token数量
- 🗜️ **高效压缩**: 通常可达到50-70%的压缩率

## 📦 安装

推荐顺序：

1) uv（工具安装） → 最快、最稳、隔离好（上面“快速安装”）
2) pipx（替代方案） → 也能隔离 CLI 工具
3) pip（虚拟环境内） → 通用且可控
4) 源码/脚本运行 → 本地开发或离线环境

### 方法1: uv 工具安装（推荐）

```bash
# 稳定版（PyPI）
uv tool install ccc

# 或固定 GitHub 版本（建议 pin 到 tag）
uv tool install 'git+https://github.com/jiangying000/ccc.git@vX.Y.Z'
```

升级/卸载：

```bash
uv tool upgrade ccc
uv tool uninstall ccc
```

### 方法2: PyPI 安装（pip/pipx）

```bash
# pip（建议在虚拟环境内）
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install ccc

# pipx（隔离安装 CLI）
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install ccc
```

### 方法3: 从源码安装（pipx/pip）

使用pipx安装到隔离环境（不污染全局Python）：

```bash
# 安装pipx（如果未安装）
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# 从GitHub安装最新版
pipx install git+https://github.com/jiangying000/ccc.git

# 或从本地安装
git clone https://github.com/jiangying000/ccc.git
pipx install ./ccc
```

### 方法4: uvx（无需安装，最快）

使用uvx即时运行（无需安装）：

```bash
# 直接运行
uvx --from git+https://github.com/jiangying000/ccc.git ccc

# 或创建别名
alias ccc='uvx --from git+https://github.com/jiangying000/ccc.git ccc'
```

### 方法5: pip 安装（虚拟环境内）

```bash
# 在虚拟环境中安装（推荐）
python3 -m venv venv
source venv/bin/activate
pip install git+https://github.com/jiangying000/ccc.git

# 或使用--user（不推荐）
pip install --user git+https://github.com/jiangying000/ccc.git
```

### 方法6: 本地脚本安装（离线/保守）

```bash
git clone https://github.com/jiangying000/ccc.git
cd ccc
bash install.sh
```

### 依赖要求

- Python 3.8+
- Claude CLI（用于发送到Claude）

## 🚀 使用方法

### 基本用法

```bash
# 默认：进入交互式选择界面
ccc

# 直接选择特定会话（带确认预览）
ccc 0   # 最新会话
ccc 1   # 第2新会话
ccc 2   # 第3新会话
```

### 交互式选择界面

无参数运行`ccc`时，显示：

```text
================================================================================
📋 Claude会话选择器
================================================================================

[ 0] 08-18 14:30 |  125.3KB |  54条 | ~ 25000 tokens
     📝 请帮我分析这个Python代码的性能问题...

[ 1] 08-18 13:15 |   45.2KB |  32条 | ~ 12000 tokens
     📝 我想创建一个React组件来展示数据...

[ 2] 08-18 10:20 |   89.7KB |  78条 | ~ 35000 tokens
     📝 能否帮我设计一个数据库架构...

--------------------------------------------------------------------------------
提示: 输入数字选择会话，或按 Ctrl+C 退出
--------------------------------------------------------------------------------

请选择会话 [0-14]: _
```

键位速览（实际界面底部会动态显示）

- [1~N]：选择当前页第 N 个会话
- [n]：下一页；[Shift+n]/[b]：上一页
- [g]：第一页；[G]：最后一页
- [j]：跳转到指定页
- [s]：设置每页数量（1–20，默认3）
- [h]：显示/隐藏帮助；[q]：退出

### 确认预览

选择会话后，发送前显示：

- 📊 会话统计（消息数、token数、压缩率）
- 📝 开头3条消息预览
- 📝 结尾3条消息预览
- ❓ 确认选项：发送(Y) / 取消(N) / 重选(R)

### 高级用法

```bash
# 交互式选择会话
ccc

# 只提取不发送（用于查看）
ccc --stats
```

## 🔧 工作原理

1. **扫描会话**: 自动扫描 `~/.claude/projects/` 下的所有会话文件
2. **智能提取**: 使用多种策略识别重要消息：
   - 最近的对话（最近10条）
   - 包含代码的消息
   - 包含文件路径的消息
   - 包含错误信息的消息
   - 包含关键指令的消息
3. **Token优化**: 使用tiktoken精确计算，确保不超过限制
4. **格式化输出**: 生成易读的Markdown格式摘要
5. **自动发送**: 通过管道发送到Claude CLI

## 🏗️ 项目结构

```text
ccc/
├── claude-smart-extract.py  # 主程序
├── install.sh              # 安装脚本
├── pyproject.toml          # Python项目配置
├── README.md               # 本文档
└── LICENSE                 # MIT许可证
```

## 📊 压缩策略

工具使用以下优先级策略：

1. **高优先级** (70% token配额):
   - 最近10条消息
   - 包含代码块
   - 包含文件路径
   - 错误信息
   - 重要指令

2. **普通优先级** (30% token配额):
   - 其他历史消息

## 🔒 隐私与安全

- 所有数据处理都在本地进行
- 不会上传或存储你的对话内容
- 仅读取本地Claude会话文件
- 使用用户级安装，不需要sudo权限

### 安全与最佳实践

- 优先安装稳定发布版（PyPI），或固定到 GitHub tag，避免直接跟随主分支。
- 使用 `uv tool install` 或 `pipx install` 进行“工具级隔离安装”，不要用 `sudo pip install` 修改系统Python。
- 在服务器/CI 中使用 `uvx` 或 `uv pip sync`（基于锁文件）确保环境可复现。
- 升级遵循：先本地验证，再在生产环境升级；保留回滚方案（固定上一个版本）。

### Windows/macOS/Linux 提示

- Windows: 建议安装官方 Python，并在“可选功能”里勾选“Add python.exe to PATH”。PowerShell 使用 `py -m venv .venv` 创建 venv。
- macOS: 使用 Homebrew 安装 uv：`brew install uv`；或使用官方安装脚本。
- Linux: 推荐使用官方 uv 安装脚本；谨慎使用系统 Python 环境，尽量在虚拟环境或工具隔离中安装。

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [Anthropic](https://anthropic.com) - Claude和Claude Code
- [Astral](https://astral.sh) - uv包管理器
- [OpenAI](https://openai.com) - tiktoken库

## 📮 联系

- GitHub: [@jiangying000](https://github.com/jiangying000)
- Issues: [GitHub Issues](https://github.com/jiangying000/ccc/issues)

---

Made with ❤️ for the Claude community
