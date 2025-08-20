#!/usr/bin/env python3
"""
测试：input()是否影响了token显示
"""

import os
import sys

print("="*60)
print("测试input()对token的影响")
print("="*60)

# 模拟CCDRC的交互
print("\n模拟CCDRC的交互过程：")
print("[1] 选项1")
print("[2] 选项2")
choice = input("请选择 (输入1): ")

print(f"\n您选择了: {choice}")
print("\n现在调用claude（观察右下角是否有token）：")
print("-"*60)

# 和CCDRC一样用os.system
os.system('claude --verbose --dangerously-skip-permissions')

print("\n" + "="*60)
print("如果没有token，说明input()破坏了终端状态")