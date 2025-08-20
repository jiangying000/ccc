#!/bin/bash
# 对比测试：Shell vs Python调用claude

echo "========================================"
echo "测试1: 纯Shell调用"
echo "========================================"
echo "执行: claude --verbose --dangerously-skip-permissions"
echo "----------------------------------------"
timeout 2 claude --verbose --dangerously-skip-permissions
echo ""
echo "如果有token，说明Shell环境正常"
echo ""

echo "========================================"
echo "测试2: Python os.system调用"
echo "========================================"
python3 -c "
import os
print('执行: os.system(\"claude --verbose --dangerously-skip-permissions\")')
print('-' * 40)
os.system('timeout 2 claude --verbose --dangerously-skip-permissions')
"
echo ""
echo "如果没有token，说明Python环境有问题"
echo ""

echo "========================================"
echo "测试3: Python with flush调用"
echo "========================================"
python3 -c "
import os
import sys
sys.stdout.flush()
sys.stderr.flush()
print('执行: 刷新后os.system')
print('-' * 40)
os.system('timeout 2 claude --verbose --dangerously-skip-permissions')
"
echo ""
echo "如果有token，说明flush解决了问题"