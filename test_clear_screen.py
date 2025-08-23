#!/usr/bin/env python3
"""测试清屏功能"""
import time
import sys

print("测试清屏功能")
print("="*60)
print("这段文字将在3秒后被清除...")
print("如果清屏成功，你将看不到这些文字")
print("="*60)

# 等待3秒
for i in range(3, 0, -1):
    print(f"倒计时: {i}秒", end='\r')
    time.sleep(1)

# 执行清屏（和CCDRC相同的方式）
print("\033[2J\033[H", end='', file=sys.stderr)

# 显示新内容
print("✅ 清屏成功！")
print("如果你看到这行而看不到之前的文字，说明清屏工作正常。")
print()
print("ANSI清屏序列说明：")
print("  \\033[2J - 清除整个屏幕")
print("  \\033[H  - 光标移到左上角(Home)")