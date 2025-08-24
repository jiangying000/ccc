#!/bin/bash

echo "测试当前的ccc行为..."

# 测试交互模式
echo "运行: ccc"
echo "应该：显示选择界面 -> 选择后直接发送（不需要确认）"
echo ""

# 模拟用户输入选择0
echo "0" | ccc 2>&1 | head -20

echo ""
echo "检查是否有确认提示..."