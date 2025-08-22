#!/usr/bin/env python3
"""
分析工具调用的token计算问题
"""

import json
import sys
sys.path.insert(0, '/home/jy/gitr/jiangying000/ccdrc')
from ccdrc.extractor import ClaudeContextExtractor

def analyze_tool_call_session():
    """分析工具调用密集会话"""
    
    extractor = ClaudeContextExtractor()
    if not extractor.encoder:
        print("需要tiktoken")
        return
    
    sessions = extractor.find_claude_sessions()
    session = sessions[0]  # 第一个会话（工具调用密集）
    
    messages = extractor.parse_session(session)
    
    print("="*60)
    print("分析工具调用会话")
    print("="*60)
    
    # 分类统计
    tool_use_msgs = []
    tool_result_msgs = []
    normal_msgs = []
    
    for msg in messages:
        msg_str = str(msg)
        if 'tool_use' in msg_str:
            tool_use_msgs.append(msg)
        elif 'tool_result' in msg_str:
            tool_result_msgs.append(msg)
        else:
            normal_msgs.append(msg)
    
    print(f"总消息数: {len(messages)}")
    print(f"工具调用: {len(tool_use_msgs)}")
    print(f"工具结果: {len(tool_result_msgs)}")
    print(f"普通消息: {len(normal_msgs)}")
    
    # 分别计算tokens
    def calc_tokens(msgs):
        tokens = 0
        for msg in msgs:
            try:
                msg_json = json.dumps(msg, ensure_ascii=False, separators=(',', ':'))
                encoded = extractor.encoder.encode(msg_json)
                tokens += len(encoded)
            except:
                pass
        return tokens
    
    tool_use_tokens = calc_tokens(tool_use_msgs)
    tool_result_tokens = calc_tokens(tool_result_msgs)
    normal_tokens = calc_tokens(normal_msgs)
    total_tokens = tool_use_tokens + tool_result_tokens + normal_tokens
    
    print(f"\nToken分布:")
    print(f"工具调用tokens: {tool_use_tokens:,} ({tool_use_tokens*100//total_tokens if total_tokens else 0}%)")
    print(f"工具结果tokens: {tool_result_tokens:,} ({tool_result_tokens*100//total_tokens if total_tokens else 0}%)")
    print(f"普通消息tokens: {normal_tokens:,} ({normal_tokens*100//total_tokens if total_tokens else 0}%)")
    print(f"总计: {total_tokens:,}")
    
    # 查看工具调用的结构
    if tool_use_msgs:
        sample = tool_use_msgs[0]
        print(f"\n工具调用样例:")
        print(json.dumps(sample, ensure_ascii=False, indent=2)[:500] + "...")
    
    print("\n" + "="*60)
    print("假设：Claude可能对工具调用有优化")
    print("="*60)
    
    # 假设Claude只处理关键字段
    optimized_tokens = 0
    
    for msg in messages:
        if 'tool_use' in str(msg):
            # 工具调用可能只保留tool_name和关键参数
            # 不需要完整的JSON结构
            optimized_tokens += 100  # 假设每个工具调用平均100 tokens
        elif 'tool_result' in str(msg):
            # 工具结果可能被截断或压缩
            optimized_tokens += 50  # 假设每个结果平均50 tokens
        else:
            # 普通消息正常计算
            try:
                msg_json = json.dumps(msg, ensure_ascii=False, separators=(',', ':'))
                encoded = extractor.encoder.encode(msg_json)
                optimized_tokens += len(encoded)
            except:
                pass
    
    print(f"优化后估算: {optimized_tokens:,} tokens")
    print(f"您提到的实际: 158,000 tokens")
    print(f"原计算: {total_tokens:,} tokens")
    print(f"\n可能的原因:")
    print("1. Claude对工具调用有特殊压缩")
    print("2. 不是所有JSON字段都被处理")
    print("3. 重复的结构被优化")

if __name__ == "__main__":
    analyze_tool_call_session()