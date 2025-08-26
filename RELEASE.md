# 发布指南

## 准备发布

### 1. 运行测试
```bash
python3 -m venv test_env
source test_env/bin/activate
pip install -e .[dev]
pytest tests/ -v
```

### 2. 更新版本号
编辑 `pyproject.toml` 中的版本号：
```toml
version = "3.9.1"  # 根据变更类型选择合适的版本号
```

### 3. 提交代码
```bash
git add .
git commit -m "Release v3.9.1"
git push
```

### 4. 创建 GitHub Release
```bash
git tag v3.9.1
git push origin v3.9.1
```

在 GitHub 上创建 Release，这将自动触发发布到 PyPI。

## 手动发布到 PyPI

如果需要手动发布：

### 1. 构建包
```bash
pip install build
python -m build
```

### 2. 检查包
```bash
pip install twine
twine check dist/*
```

### 3. 发布到 Test PyPI（可选）
```bash
twine upload --repository testpypi dist/*
```

### 4. 发布到 PyPI
```bash
twine upload dist/*
```

## 发布后验证

```bash
# 等待几分钟让 PyPI 更新
pip install --upgrade ccc
ccc --version
```

## CI/CD 自动化

项目已配置 GitHub Actions：
- **CI**：每次推送和 PR 都会运行测试
- **发布**：创建 GitHub Release 时自动发布到 PyPI

需要在 GitHub 仓库设置中配置以下 Secrets：
- `PYPI_API_TOKEN`：PyPI 的 API token
- `TEST_PYPI_API_TOKEN`：Test PyPI 的 API token（可选）