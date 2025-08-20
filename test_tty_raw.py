#!/usr/bin/env python3
"""
测试：tty.setraw() 是否影响了token显示
"""

import os
import sys
import termios
import tty

print("="*60)
print("测试 tty.setraw() 对token的影响")
print("="*60)

print("\n模拟CCDRC的get_single_char()：")
print("按任意键继续...")

# 模拟CCDRC的get_single_char()
fd = sys.stdin.fileno()
old_settings = termios.tcgetattr(fd)
try:
    tty.setraw(sys.stdin.fileno())
    ch = sys.stdin.read(1)
finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

print(f"\n您按下了: {repr(ch)}")
print("\n现在调用claude（观察右下角是否有token）：")
print("-"*60)

# 和CCDRC一样用os.system
os.system('claude --verbose --dangerously-skip-permissions')

print("\n" + "="*60)
print("如果没有token，说明tty.setraw()破坏了终端状态")