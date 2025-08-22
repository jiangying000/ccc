#!/usr/bin/env python3
"""
调试token计算问题
"""

import json
import sys
sys.path.insert(0, '/home/jy/gitr/jiangying000/ccdrc')
from ccdrc.extractor import ClaudeContextExtractor

def debug_session(session_path):
    """详细调试一个会话的token计算"""
    
    print(f"\n调试会话: {session_path.name}")
    print("-" * 60)
    
    messages = []
    with open(session_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    messages.append(json.loads(line))
                except:
                    pass
    
    # 统计不同类型的消息
    msg_types = {}
    total_json_chars = 0
    text_content_chars = 0
    
    for msg in messages:
        msg_type = msg.get('type', 'unknown')
        msg_types[msg_type] = msg_types.get(msg_type, 0) + 1
        
        # JSON大小
        msg_json = json.dumps(msg, ensure_ascii=False, separators=(',', ':'))
        total_json_chars += len(msg_json)
        
        # 文本内容
        if 'message' in msg and isinstance(msg['message'], dict):
            content = msg['message'].get('content', [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        text = item.get('text', '')
                        text_content_chars += len(text)
    
    print(f"文件大小: {session_path.stat().st_size / 1024:.1f} KB")
    print(f"消息数: {len(messages)}")
    print(f"消息类型分布: {msg_types}")
    print(f"\n字符统计:")
    print(f"  总JSON字符: {total_json_chars:,}")
    print(f"  文本内容字符: {text_content_chars:,}")
    print(f"  结构字符: {total_json_chars - text_content_chars:,}")
    
    # 我的计算公式
    text_tokens = text_content_chars / 3.5
    structure_chars = total_json_chars - text_content_chars
    structure_tokens = structure_chars / 2.5
    raw_total = text_tokens + structure_tokens
    adjusted_total = raw_total * 1.09
    
    print(f"\nToken计算:")
    print(f"  文本tokens: {int(text_tokens):,}")
    print(f"  结构tokens: {int(structure_tokens):,}")
    print(f"  调整前: {int(raw_total):,}")
    print(f"  调整后(×1.09): {int(adjusted_total):,}")
    
    # 检查是否有异常大的消息
    max_msg_size = 0
    for msg in messages:
        msg_json = json.dumps(msg, ensure_ascii=False, separators=(',', ':'))
        if len(msg_json) > max_msg_size:
            max_msg_size = len(msg_json)
    
    print(f"\n最大单条消息: {max_msg_size:,} 字符")
    
    # 看看平均每条消息的大小
    avg_msg_size = total_json_chars / len(messages) if messages else 0
    print(f"平均每条消息: {int(avg_msg_size):,} 字符")
    
    return adjusted_total

# 测试前3个会话
extractor = ClaudeContextExtractor()
sessions = extractor.find_claude_sessions()

print("="*60)
print("调试Token计算问题")
print("="*60)

for i in range(min(3, len(sessions))):
    calculated = debug_session(sessions[i])
    
    # 用CCDRC获取
    info = extractor.get_session_info(sessions[i])
    print(f"\nCCDRC新算法计算: {info['tokens']:,}")
    print(f"我的调试计算: {int(calculated):,}")
    
    if i == 2:
        print(f"实际值: 139,000")
    
    print("="*60)