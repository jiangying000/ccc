#!/usr/bin/env python3
"""
完全模拟CCDRC的执行环境
"""

import os
import sys
from pathlib import Path

# 模拟CCDRC的导入
sys.path.insert(0, '/home/jy/gitr/jiangying000/ccdrc')

print("="*60)
print("完全模拟CCDRC环境测试")
print("="*60)

# 模拟用户选择会话
print("🚀 CCDRC - Claude Code会话压缩和恢复工具", file=sys.stderr)
print("📄 第 1/80 页", file=sys.stderr)
print("─" * 60, file=sys.stderr)

# 模拟input（CCDRC现在用的普通input）
choice = input("\n👉 ").strip().lower()[:1]
print(f"您选择了: {choice}", file=sys.stderr)

# 模拟选择r恢复
if choice == 'r':
    session_id = "0c057059-e246-4447-8e3e-8694ab6b68d3"  # 示例ID
    print(f"\n🚀 正在使用 --resume 恢复会话...", file=sys.stderr)
    print(f"⚡ 已启用 --dangerously-skip-permissions 跳过权限检查", file=sys.stderr)
    
    # 完全模拟CCDRC的调用方式
    cmd = f'claude --resume {session_id} --dangerously-skip-permissions'
    print(f"\n执行命令: {cmd}", file=sys.stderr)
    print("-"*60, file=sys.stderr)
    
    exit_code = os.system(cmd)
    print(f"\n退出码: {exit_code >> 8}", file=sys.stderr)
else:
    print("测试其他选项...")
    cmd = 'claude --verbose --dangerously-skip-permissions'
    os.system(cmd)

print("\n" + "="*60)
print("如果没有token，说明问题在整体环境配置")