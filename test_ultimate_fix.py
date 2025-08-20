#!/usr/bin/env python3
"""
测试终极修复：纯input是否保留token显示
"""

import os

print("="*60)
print("测试终极修复：避免termios")
print("="*60)

print("\n使用纯input（终极修复方案）：")
choice = input("👉 请输入选择并按回车: ").strip().lower()[:1]

print(f"\n您选择了: '{choice}'")
print("\n现在调用claude（右下角应该有token）：")
print("-"*60)

os.system('claude --verbose --dangerously-skip-permissions')

print("\n" + "="*60)
print("✅ 如果有token显示，说明终极修复成功！")
print("这证明了termios是问题根源")