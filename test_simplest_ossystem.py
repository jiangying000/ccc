#!/usr/bin/env python3
"""
最简单的测试：纯os.system调用claude
"""

import os

print("最简单测试：os.system调用claude")
print("="*60)

# 直接用os.system
print("执行: os.system('claude --verbose --dangerously-skip-permissions')")
print("-"*60)

exit_code = os.system('claude --verbose --dangerously-skip-permissions')

print("\n" + "="*60)
print(f"退出码: {exit_code >> 8}")
print("如果有token显示，说明os.system本身没问题")
print("如果没有token，说明问题更深层")