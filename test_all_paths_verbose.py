#!/usr/bin/env python3
"""
测试CCDRC所有执行路径都有--verbose参数
"""

import re

# 读取源文件
with open('/home/jy/gitr/jiangying000/ccdrc/ccdrc/extractor.py', 'r') as f:
    content = f.read()

# 查找所有claude调用
claude_calls = re.findall(r'(os\.system\([^)]*claude[^)]*\))', content)

print("="*60)
print("检查CCDRC中所有claude调用是否包含--verbose")
print("="*60)

missing_verbose = []
has_verbose = []

for call in claude_calls:
    if '--verbose' in call:
        has_verbose.append(call)
    else:
        missing_verbose.append(call)

print(f"\n✅ 包含--verbose的调用: {len(has_verbose)}")
for call in has_verbose:
    # 提取命令部分
    cmd = re.search(r'claude[^"\']*', call)
    if cmd:
        print(f"   - {cmd.group()}")

if missing_verbose:
    print(f"\n❌ 缺少--verbose的调用: {len(missing_verbose)}")
    for call in missing_verbose:
        print(f"   - {call}")
else:
    print("\n✅ 所有调用都包含--verbose参数！")

# 检查具体的执行路径
print("\n" + "="*60)
print("执行路径分析：")
print("="*60)

paths = {
    "恢复路径(r)": "claude --resume.*--verbose",
    "压缩路径(c)": "cat.*claude.*--verbose",
}

for path_name, pattern in paths.items():
    if re.search(pattern, content):
        print(f"✅ {path_name}: 包含--verbose")
    else:
        print(f"❌ {path_name}: 缺少--verbose")