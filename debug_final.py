#!/usr/bin/env python3
"""
最终调试 - 找出准确的计算方法
"""

import json
import sys
sys.path.insert(0, '/home/jy/gitr/jiangying000/ccdrc')
from ccdrc.extractor import ClaudeContextExtractor

def debug_sessions():
    """详细调试每个会话"""
    
    extractor = ClaudeContextExtractor()
    if not extractor.encoder:
        print("需要tiktoken")
        return
    
    sessions = extractor.find_claude_sessions()
    
    # 实际值（您提供的）
    actual_values = {
        0: 158000,  # 第1个会话
        2: 139000,  # 第3个会话
    }
    
    for idx in [0, 2]:  # 测试第1和第3个
        if idx >= len(sessions):
            continue
            
        session = sessions[idx]
        messages = extractor.parse_session(session)
        
        print(f"\n{'='*60}")
        print(f"会话 {idx+1}: {session.name[:8]}...")
        print(f"{'='*60}")
        
        # 统计消息类型
        tool_use_count = 0
        tool_result_count = 0
        normal_count = 0
        
        for msg in messages:
            msg_str = str(msg)
            if 'tool_use' in msg_str:
                tool_use_count += 1
            elif 'tool_result' in msg_str:
                tool_result_count += 1
            else:
                normal_count += 1
        
        print(f"消息统计:")
        print(f"  总计: {len(messages)}")
        print(f"  工具调用: {tool_use_count}")
        print(f"  工具结果: {tool_result_count}")
        print(f"  普通消息: {normal_count}")
        
        # 方法1：只计算message.content中的text
        text_only_tokens = 0
        for msg in messages:
            content = extractor._get_message_content(msg)
            if content:
                try:
                    tokens = extractor.encoder.encode(content)
                    text_only_tokens += len(tokens)
                except:
                    pass
        
        # 方法2：计算完整JSON
        full_json_tokens = 0
        for msg in messages:
            try:
                msg_json = json.dumps(msg, ensure_ascii=False, separators=(',', ':'))
                tokens = extractor.encoder.encode(msg_json)
                full_json_tokens += len(tokens)
            except:
                pass
        
        # 方法3：智能方法（当前实现）
        info = extractor.get_session_info(session)
        smart_tokens = info['tokens']
        
        actual = actual_values.get(idx, 0)
        
        print(f"\nToken计算对比:")
        print(f"  纯文本: {text_only_tokens:,} tokens")
        print(f"  完整JSON: {full_json_tokens:,} tokens")
        print(f"  智能方法: {smart_tokens:,} tokens")
        print(f"  实际值: {actual:,} tokens")
        
        # 分析哪个更接近
        text_error = abs(actual - text_only_tokens)
        json_error = abs(actual - full_json_tokens)
        smart_error = abs(actual - smart_tokens)
        
        print(f"\n误差分析:")
        print(f"  纯文本误差: {text_error:,} ({text_error*100//actual}%)")
        print(f"  完整JSON误差: {json_error:,} ({json_error*100//actual}%)")
        print(f"  智能方法误差: {smart_error:,} ({smart_error*100//actual}%)")
        
        # 找出最优系数
        if text_only_tokens > 0:
            text_factor = actual / text_only_tokens
            print(f"\n如果用纯文本×{text_factor:.2f} = {int(text_only_tokens * text_factor):,}")
        
        if full_json_tokens > 0:
            json_factor = actual / full_json_tokens
            print(f"如果用完整JSON×{json_factor:.2f} = {int(full_json_tokens * json_factor):,}")

if __name__ == "__main__":
    debug_sessions()