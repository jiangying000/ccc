#!/usr/bin/env python3
"""
最终测试：验证CCC的verbose是否真正生效
"""

import subprocess
import sys

print("=" * 60)
print("测试CCC的verbose传递")
print("=" * 60)

# 测试方式1：不传env（v3.12.0的方式）
print("\n方式1：不传env参数")
print("-" * 40)

session_id = "0c057059-e246-4447-8e3e-8694ab6b68d3"  # 使用一个实际的session
cmd = ['claude', '--resume', session_id, '--verbose', '--dangerously-skip-permissions']

print(f"执行: {' '.join(cmd)}")
print("期望: 看到Welcome to Claude和API URL等信息\n")

try:
    result = subprocess.run(
        cmd,
        input=b"test message",
        text=False,
        timeout=5
    )
    print(f"\n返回码: {result.returncode}")
except subprocess.TimeoutExpired:
    print("\n(超时，但这是正常的)")
except Exception as e:
    print(f"\n错误: {e}")

print("\n" + "=" * 60)
print("如果看到了详细信息，说明v3.12.0修复成功！")