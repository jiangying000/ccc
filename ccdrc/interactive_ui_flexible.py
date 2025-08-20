#!/usr/bin/env python3
"""
Flexible Interactive UI - 支持两种模式
1. SAFE模式（默认）：使用普通input，保证token显示
2. FAST模式：使用termios，单键响应但可能影响token
"""

import sys
import os
from typing import Optional

# 从环境变量读取模式
CCDRC_MODE = os.environ.get('CCDRC_MODE', 'SAFE').upper()

try:
    import termios
    import tty
    TERMIOS_AVAILABLE = True
except ImportError:
    TERMIOS_AVAILABLE = False
    CCDRC_MODE = 'SAFE'  # 强制安全模式

def get_single_char_safe():
    """安全模式：普通input，需要回车"""
    prompt = "\n👉 " if CCDRC_MODE == 'SAFE' else "\n⚡ "
    user_input = input(prompt).strip().lower()
    return user_input[0] if user_input else ''

def get_single_char_fast():
    """快速模式：termios单键，可能影响token"""
    if not TERMIOS_AVAILABLE:
        return get_single_char_safe()
    
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, old_settings)
    return ch

def get_single_char():
    """根据模式选择输入方法"""
    if CCDRC_MODE == 'FAST' and TERMIOS_AVAILABLE:
        print("⚡ 快速模式（单键，可能无token）", file=sys.stderr)
        return get_single_char_fast()
    else:
        print("🛡️ 安全模式（需回车，保证token）", file=sys.stderr)
        return get_single_char_safe()

# 使用示例
if __name__ == "__main__":
    print(f"当前模式: {CCDRC_MODE}")
    print("切换模式:")
    print("  export CCDRC_MODE=SAFE  # 安全模式（默认）")
    print("  export CCDRC_MODE=FAST  # 快速模式")
    print("")
    print("按任意键测试...")
    ch = get_single_char()
    print(f"您输入了: {ch}")
    
    # 测试token显示
    print("\n测试调用claude...")
    os.system('claude --verbose --dangerously-skip-permissions')