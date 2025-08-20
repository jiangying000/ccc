#!/usr/bin/env python3
"""
测试：向stderr输出是否影响token显示
"""

import os
import sys

print("="*60)
print("测试stderr输出对token的影响")
print("="*60)

# 模拟CCDRC的stderr输出
print("🚀 正在使用 --resume 恢复会话...", file=sys.stderr)
print("⚡ 已启用 --dangerously-skip-permissions 跳过权限检查", file=sys.stderr)

print("\n现在调用claude（观察token）：")
print("-"*60)

# 和CCDRC完全一样的调用
exit_code = os.system('claude --verbose --dangerously-skip-permissions')

print("\n" + "="*60)
print(f"退出码: {exit_code >> 8}")
print("如果没有token，说明stderr输出影响了终端")