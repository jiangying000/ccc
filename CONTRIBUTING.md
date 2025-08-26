# 贡献指南

感谢您对 CCC 项目的关注！我们欢迎各种形式的贡献。

## 如何贡献

### 报告问题
1. 在 [Issues](https://github.com/jiangying000/ccc/issues) 中搜索是否已有类似问题
2. 创建新 Issue，详细描述：
   - 问题描述
   - 复现步骤
   - 期望行为
   - 实际行为
   - 系统环境（OS、Python版本等）

### 提交代码

1. Fork 仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 安装开发依赖：
   ```bash
   pip install -e .[dev]
   ```
4. 编写代码并添加测试
5. 运行测试：
   ```bash
   pytest tests/ -v
   ```
6. 运行代码检查：
   ```bash
   ruff check ccc/
   ```
7. 提交代码：`git commit -m "Add your feature"`
8. 推送分支：`git push origin feature/your-feature`
9. 创建 Pull Request

## 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/jiangying000/ccc.git
cd ccc

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装开发依赖
pip install -e .[dev]

# 运行测试
pytest tests/ -v

# 运行代码检查
ruff check ccc/
```

## 代码规范

- 使用 Python 3.8+ 特性
- 遵循 PEP 8 代码风格
- 添加类型提示（Type Hints）
- 编写文档字符串（Docstrings）
- 保持代码简洁清晰
- 添加适当的测试

## 测试

- 为新功能添加测试
- 确保所有测试通过
- 保持测试覆盖率

## 文档

- 更新 README.md（如果需要）
- 添加代码注释
- 更新 CHANGELOG.md

## 许可

通过贡献代码，您同意您的贡献将在 MIT 许可下发布。