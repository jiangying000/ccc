# GitHub 仓库设置指南

## 配置 PyPI 发布

### 1. 获取 PyPI API Token

1. 登录 [PyPI](https://pypi.org/)
2. 进入账户设置 -> API tokens
3. 创建新 token，范围选择 "Entire account" 或特定项目
4. 复制 token（只显示一次）

### 2. 配置 GitHub Secrets

1. 进入仓库设置：Settings -> Secrets and variables -> Actions
2. 点击 "New repository secret"
3. 添加以下 secrets：
   - Name: `PYPI_API_TOKEN`
   - Value: 粘贴从 PyPI 获取的 token

### 3. （可选）配置 Test PyPI

1. 登录 [Test PyPI](https://test.pypi.org/)
2. 同样获取 API token
3. 在 GitHub 添加 secret：
   - Name: `TEST_PYPI_API_TOKEN`
   - Value: Test PyPI token

## 启用 GitHub Actions

Actions 已经在 `.github/workflows/` 中配置好：
- `ci.yml`：自动测试
- `publish.yml`：自动发布

推送代码后会自动启用。

## 创建首次发布

1. 更新版本号（pyproject.toml）
2. 提交并推送代码
3. 创建 Release：
   ```bash
   git tag v3.9.0
   git push origin v3.9.0
   ```
4. 在 GitHub 上创建 Release，Actions 会自动发布到 PyPI

## 状态徽章

README 中已添加状态徽章，会自动显示 CI 状态和 PyPI 版本。