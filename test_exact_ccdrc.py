#!/usr/bin/env python3
"""
精确模拟CCDRC压缩模式
"""

import os
import sys
import tempfile

print("精确模拟CCDRC压缩模式")
print("="*60)

# 创建测试内容（模拟压缩后的summary）
test_content = """# 测试对话上下文

这是一个测试内容，模拟CCDRC压缩后的输出。

## 用户
Hello Claude

## Assistant
Hello! How can I help you today?

## 用户
Test message
"""

print("\n1. 检查环境：")
print(f"   stdin.isatty(): {sys.stdin.isatty()}")
print(f"   stdout.isatty(): {sys.stdout.isatty()}")
print(f"   stderr.isatty(): {sys.stderr.isatty()}")

print("\n2. 模拟CCDRC压缩模式：")

# 保存到临时文件（和CCDRC一样）
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
    f.write(test_content)
    temp_file = f.name

print(f"   临时文件: {temp_file}")

try:
    # 完全模拟CCDRC的命令
    cmd_str = "claude --dangerously-skip-permissions --verbose"
    cmd_with_input = f"cat {temp_file} | {cmd_str}"
    
    print(f"   执行命令: {cmd_with_input}")
    print("   [观察右下角是否有token显示]\n")
    print("-" * 60)
    
    # 和CCDRC完全一样的调用方式
    result_code = os.system(cmd_with_input)
    
    print("\n" + "-" * 60)
    print(f"   返回码: {result_code >> 8}")
    
finally:
    # 清理临时文件
    try:
        os.unlink(temp_file)
    except:
        pass

print("\n" + "="*60)
print("如果这里没有token，说明问题在管道输入方式")
print("如果这里有token但CCDRC没有，说明还有其他环境差异")