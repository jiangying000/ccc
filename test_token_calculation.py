#!/usr/bin/env python3
"""
测试token计算准确性
对比CCDRC计算 vs Claude实际使用
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, '/home/jy/gitr/jiangying000/ccdrc')
from ccdrc.extractor import ClaudeContextExtractor

def analyze_session_tokens(session_path):
    """分析会话的token计算"""
    
    extractor = ClaudeContextExtractor(verbose=True)
    
    # 1. CCDRC的计算方式
    info = extractor.get_session_info(session_path)
    ccdrc_tokens = info['tokens']
    
    # 2. 分析实际内容
    messages = extractor.parse_session(session_path)
    
    # 计算不同部分的大小
    total_file_size = session_path.stat().st_size
    message_count = len(messages)
    
    # 纯文本内容
    text_only_tokens = 0
    json_structure_chars = 0
    
    for msg in messages:
        # 纯文本
        content = extractor._get_message_content(msg)
        if content:
            text_only_tokens += extractor.count_tokens(content)
        
        # JSON结构（整个消息的JSON表示）
        json_str = json.dumps(msg, ensure_ascii=False, separators=(',', ':'))
        json_structure_chars += len(json_str)
    
    # 估算JSON结构的tokens（JSON通常1字符≈0.5 token）
    json_tokens_estimate = json_structure_chars // 2
    
    # 3. 更准确的估算
    # Claude实际会处理完整的JSONL，包括所有字段
    accurate_estimate = json_tokens_estimate  # 完整JSON的tokens
    
    print("="*60)
    print("Token计算分析")
    print("="*60)
    
    print(f"\n📁 会话文件: {session_path.name}")
    print(f"   文件大小: {total_file_size/1024:.1f} KB")
    print(f"   消息数量: {message_count}")
    
    print(f"\n🔢 CCDRC当前计算:")
    print(f"   显示tokens: {ccdrc_tokens:,}")
    print(f"   = 文本内容: {text_only_tokens:,}")
    print(f"   + 系统开销: 20,000 (硬编码)")
    
    print(f"\n📊 实际内容分析:")
    print(f"   纯文本tokens: {text_only_tokens:,}")
    print(f"   JSON字符数: {json_structure_chars:,}")
    print(f"   JSON tokens (估算): {json_tokens_estimate:,}")
    
    print(f"\n🎯 更准确的估算:")
    print(f"   总tokens: {accurate_estimate:,}")
    
    print(f"\n⚠️  偏差分析:")
    print(f"   CCDRC显示: {ccdrc_tokens:,}")
    print(f"   实际可能: {accurate_estimate:,}")
    print(f"   差异: {accurate_estimate - ccdrc_tokens:,} tokens")
    print(f"   偏差率: {(accurate_estimate - ccdrc_tokens) / accurate_estimate * 100:.1f}%")
    
    return {
        'ccdrc': ccdrc_tokens,
        'text_only': text_only_tokens,
        'json_estimate': json_tokens_estimate,
        'accurate': accurate_estimate
    }

if __name__ == "__main__":
    # 测试最近的会话
    extractor = ClaudeContextExtractor()
    sessions = extractor.find_claude_sessions()
    
    if sessions and len(sessions) >= 3:
        # 测试第3个会话（用户提到的）
        session_path = sessions[2]
        result = analyze_session_tokens(session_path)
        
        print("\n" + "="*60)
        print("💡 结论：")
        print("="*60)
        print("CCDRC目前只计算纯文本内容的tokens，")
        print("忽略了JSON结构的巨大开销。")
        print("实际上Claude需要解析完整的JSONL文件，")
        print("包括所有的type、role、timestamp等字段。")
        
        if result['accurate'] > 100000:
            print(f"\n建议：这个会话实际约{result['accurate']//1000}k tokens，")
            print("已接近或超过Claude的上下文限制。")
    else:
        print("未找到足够的会话进行测试")