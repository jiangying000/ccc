# 发布到PyPI

## 准备工作

1. 注册PyPI账号: https://pypi.org/account/register/
2. 注册TestPyPI账号（可选）: https://test.pypi.org/account/register/
3. 创建API Token: https://pypi.org/manage/account/token/

## 构建包

```bash
# 使用uv构建
uv build

# 或使用传统方式
python3 -m pip install --user build
python3 -m build
```

## 发布到TestPyPI（推荐先测试）

```bash
# 安装twine
pip install --user twine

# 上传到TestPyPI
python3 -m twine upload --repository testpypi dist/*

# 测试安装
pip install --index-url https://test.pypi.org/simple/ ccc
```

## 发布到PyPI

```bash
# 上传到PyPI
python3 -m twine upload dist/*

# 或使用uv
uv publish
```

## 配置API Token（推荐）

创建 `~/.pypirc` 文件：

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = <your-pypi-token>

[testpypi]
username = __token__
password = <your-testpypi-token>
```

## 发布后安装

用户可以通过以下方式安装：

```bash
# pipx（推荐）
pipx install ccc

# pip
pip install ccc

# uvx
uvx ccc

# uv tool
uv tool install ccc
```

## 版本更新

1. 更新 `pyproject.toml` 中的版本号
2. 更新 `ccc/__init__.py` 中的 `__version__`
3. 创建Git标签：
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
4. 重新构建和发布

## GitHub Actions自动发布

创建 `.github/workflows/publish.yml`：

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install uv
      run: curl -LsSf https://astral.sh/uv/install.sh | sh
    
    - name: Build package
      run: uv build
    
    - name: Publish to PyPI
      env:
        UV_PUBLISH_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
      run: uv publish
```

在GitHub仓库设置中添加 `PYPI_API_TOKEN` secret。