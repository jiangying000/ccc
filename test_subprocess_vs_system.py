#!/usr/bin/env python3
"""
对比测试：subprocess.run vs os.system对token显示的影响
"""

import subprocess
import os
import sys

print("="*60)
print("subprocess.run vs os.system 对比测试")
print("="*60)

# 先用input确保终端正常
choice = input("\n请按回车开始测试: ")

print("\n测试1: 使用subprocess.run（CCDRC原来的方式）")
print("-"*40)
try:
    result = subprocess.run(
        ['claude', '--verbose', '--dangerously-skip-permissions'],
        text=False,
        timeout=2
    )
except subprocess.TimeoutExpired:
    print("（超时退出）")
except Exception as e:
    print(f"错误: {e}")

print("\n" + "="*60)
print("测试1结果：如果没有token，说明subprocess破坏了终端")
print("="*60)

input("\n按回车继续测试2...")

print("\n测试2: 使用os.system（修复后的方式）")
print("-"*40)
os.system('timeout 2 claude --verbose --dangerously-skip-permissions')

print("\n" + "="*60)
print("测试2结果：如果有token，说明os.system保持了终端状态")
print("="*60)

print("\n结论：")
print("subprocess.run() 创建新的进程环境，破坏终端状态传递")
print("os.system() 在当前shell中执行，保持终端状态完整")