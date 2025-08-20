# CCDRC最佳安装实践指南（2025年版）

## 背景：为什么需要新的安装方法

从Ubuntu 23.04开始，系统实施了PEP 668保护机制，禁止pip直接修改系统Python环境。
这是为了防止pip安装的包与apt管理的系统包冲突，导致系统工具崩溃。

## 三种推荐的安装方案

### 方案1：使用pipx（最推荐）✨

**优势：**
- 自动创建隔离环境
- 全局可用的命令行工具
- 不会污染系统Python
- 符合PEP 668规范

**安装步骤：**
```bash
# 1. 安装pipx
sudo apt update
sudo apt install pipx
pipx ensurepath

# 2. 重启终端或执行
source ~/.bashrc

# 3. 安装CCDRC
pipx install git+https://github.com/jiangying000/ccdrc.git

# 4. 升级
pipx upgrade ccdrc

# 5. 卸载
pipx uninstall ccdrc
```

### 方案2：使用虚拟环境（传统但可靠）

**优势：**
- 完全隔离的Python环境
- 可精确控制依赖版本
- 适合开发和调试

**安装步骤：**
```bash
# 1. 创建虚拟环境
cd /home/jy/gitr/jiangying000/ccdrc
python3 -m venv .venv

# 2. 激活虚拟环境
source .venv/bin/activate

# 3. 升级pip
pip install --upgrade pip

# 4. 安装CCDRC（开发模式）
pip install -e .

# 5. 创建全局命令链接
sudo ln -sf /home/jy/gitr/jiangying000/ccdrc/.venv/bin/ccdrc /usr/local/bin/ccdrc

# 6. 退出虚拟环境
deactivate
```

### 方案3：使用uv工具（最新最快）🚀

**优势：**
- 比pip快10-100倍
- 自动管理虚拟环境
- 2025年最新工具

**安装步骤：**
```bash
# 1. 安装uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# 2. 安装CCDRC作为工具
uv tool install git+https://github.com/jiangying000/ccdrc.git

# 3. 或从本地安装
cd /home/jy/gitr/jiangying000/ccdrc
uv tool install .

# 4. 升级
uv tool upgrade ccdrc
```

## 不推荐的方案 ⚠️

### 使用--break-system-packages（当前使用的）

```bash
pip install --break-system-packages -e .
```

**问题：**
- 可能破坏系统Python包
- 不符合PEP 668规范
- 可能导致系统工具故障
- 仅应在Docker或测试环境中使用

## 对比表

| 方案 | 安全性 | 速度 | 易用性 | 适用场景 |
|-----|-------|------|--------|---------|
| pipx | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | CLI工具安装 |
| venv | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 开发调试 |
| uv | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 现代化工具链 |
| --break | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 临时测试 |

## 建议选择

1. **普通用户**：使用pipx，最简单安全
2. **开发者**：使用venv，方便调试修改
3. **追求性能**：使用uv，速度最快
4. **Docker环境**：可以使用--break-system-packages

## 故障排除

### 问题：找不到ccdrc命令
```bash
# pipx用户
pipx ensurepath
source ~/.bashrc

# venv用户
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 问题：权限错误
```bash
# 使用用户目录而非系统目录
pipx install --user ccdrc
```

### 问题：依赖冲突
```bash
# 完全重装
pipx uninstall ccdrc
pipx install --force ccdrc
```

## 总结

PEP 668推动Python生态向更好的方向发展。虽然初期可能不便，但长期来看：
- 系统更稳定
- 依赖更清晰
- 环境更隔离

选择合适的安装方案，拥抱Python包管理的未来！