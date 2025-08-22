#!/usr/bin/env python3
"""测试大会话的压缩效果"""

import json
from pathlib import Path
from ccdrc.extractor import ClaudeContextExtractor

def test_big_session():
    """测试3.7MB大会话的压缩"""
    
    # 初始化提取器
    extractor = ClaudeContextExtractor(max_tokens=100000)
    
    # 测试最大的会话（3.7MB）
    session_path = Path('/home/jy/.claude/projects/-home-jy-gitr-felo-mygpt/9a22684d-522e-451e-99a3-6c1b215a1ccc.jsonl')
    
    print(f"测试会话: {session_path.name}")
    print(f"文件大小: {session_path.stat().st_size / 1024 / 1024:.1f} MB")
    print("="*60)
    
    # 解析会话
    result = extractor.parse_session(session_path)
    if isinstance(result, tuple):
        messages = result[0]
    else:
        messages = result
    
    print(f"消息数量: {len(messages)}")
    
    # 计算原始大小（使用_get_message_content）
    original_tokens = 0
    tool_count = 0
    
    for msg in messages:
        content = extractor._get_message_content(msg)
        if content:
            tokens = extractor.count_tokens(content)
            original_tokens += tokens
            
            # 统计工具调用
            if '[Tool:' in content or '[Read file:' in content or '[Created file:' in content:
                tool_count += 1
    
    print(f"原始Token数: {original_tokens:,}")
    print(f"包含工具调用的消息: {tool_count}")
    
    if original_tokens > 100000:
        print("\n执行压缩...")
        print("-"*60)
        
        # 执行压缩
        compressed_messages, stats = extractor.extract_key_messages(messages)
        
        # 计算压缩后大小
        compressed_tokens = 0
        compressed_tool_count = 0
        
        for msg in compressed_messages:
            content = extractor._get_message_content(msg)
            if content:
                tokens = extractor.count_tokens(content)
                compressed_tokens += tokens
                
                if '[Tool:' in content or '[Read file:' in content:
                    compressed_tool_count += 1
        
        print(f"压缩后消息数: {len(compressed_messages)}")
        print(f"压缩后Token数: {compressed_tokens:,}")
        print(f"压缩后工具调用: {compressed_tool_count}")
        print(f"压缩比: {compressed_tokens/original_tokens*100:.1f}%")
        
        # 分析前后分配
        front_count = 0
        back_count = 0
        middle_gap = False
        
        for i, msg in enumerate(compressed_messages):
            content = extractor._get_message_content(msg)
            if content:
                tokens = extractor.count_tokens(content)
                
                # 检查是否有截断标记
                if '[...内容已截断...]' in content:
                    print(f"消息 {i}: 前部截断, {tokens} tokens")
                    front_count += tokens
                elif '[...前面内容已省略...]' in content:
                    print(f"消息 {i}: 后部截断, {tokens} tokens")
                    back_count += tokens
                    middle_gap = True
                elif not middle_gap:
                    front_count += tokens
                else:
                    back_count += tokens
        
        print(f"\n前部tokens: {front_count:,}")
        print(f"后部tokens: {back_count:,}")
        print(f"总计: {front_count + back_count:,}")
        
        # 与预期对比
        print(f"\n预期: 前25k + 后75k = 100k")
        print(f"实际: 前{front_count/1000:.1f}k + 后{back_count/1000:.1f}k = {(front_count+back_count)/1000:.1f}k")
        print(f"差异: {(front_count+back_count)/1000 - 100:.1f}k")

if __name__ == '__main__':
    test_big_session()