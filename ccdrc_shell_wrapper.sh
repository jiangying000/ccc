#!/bin/bash
# CCC Shell包装器 - 绕过Python环境问题（已弃用）

echo "CCC Shell Wrapper - 保证token显示（建议直接使用 ccc 命令）"
echo "===================================="

# 获取会话ID（这里用示例，实际需要从Python获取）
SESSION_ID="0c057059-e246-4447-8e3e-8694ab6b68d3"

echo "选择操作："
echo "1. 恢复会话"
echo "2. 压缩发送"
read -p "请选择: " choice

if [ "$choice" = "1" ]; then
    echo "正在恢复会话..."
    claude --resume "$SESSION_ID" --verbose --dangerously-skip-permissions
elif [ "$choice" = "2" ]; then
    echo "正在压缩并发送..."
    # 这里调用Python做压缩，然后pipe给claude
    python3 -c "
# from ccc.extractor import ClaudeContextExtractor  # rebranded
# ... 压缩逻辑
    " | claude --verbose --dangerously-skip-permissions
fi