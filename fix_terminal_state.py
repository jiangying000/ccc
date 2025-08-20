#!/usr/bin/env python3
"""
修复CCDRC的终端状态问题
两种解决方案
"""

import os
import sys

print("="*60)
print("修复方案测试")
print("="*60)

# 方案1: 在调用claude前显式重置终端
def fix_method_1():
    print("\n方案1: 显式重置终端状态")
    
    # 先做CCDRC的操作
    import termios
    import tty
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    print(f"\n按下了: {repr(ch)}")
    
    # ★ 关键修复：确保终端完全恢复
    os.system('stty sane')  # 重置终端到正常状态
    
    print("调用claude（应该有token）：")
    os.system('claude --verbose --dangerously-skip-permissions')

# 方案2: 使用更安全的单字符输入
def fix_method_2():
    print("\n方案2: 使用termios.TCSANOW而非TCSADRAIN")
    
    import termios
    import tty
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(sys.stdin.fileno())  # 使用setcbreak而非setraw
        ch = sys.stdin.read(1)
    finally:
        # 立即恢复，不等待输出完成
        termios.tcsetattr(fd, termios.TCSANOW, old_settings)
        # 强制刷新
        sys.stdout.flush()
        sys.stderr.flush()
    
    print(f"\n按下了: {repr(ch)}")
    print("调用claude（应该有token）：")
    os.system('claude --verbose --dangerously-skip-permissions')

# 方案3: 不使用raw mode
def fix_method_3():
    print("\n方案3: 完全避免raw mode，使用普通input")
    ch = input("请输入选择: ").strip()
    if ch:
        ch = ch[0]
    
    print(f"\n您选择了: {ch}")
    print("调用claude（肯定有token）：")
    os.system('claude --verbose --dangerously-skip-permissions')

print("\n选择测试方案:")
print("1. stty sane 修复")
print("2. setcbreak + TCSANOW")
print("3. 普通input (最安全)")

choice = input("请选择 (1/2/3): ").strip()

if choice == '1':
    fix_method_1()
elif choice == '2':
    fix_method_2()
elif choice == '3':
    fix_method_3()
else:
    print("无效选择")