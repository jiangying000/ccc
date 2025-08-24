#!/usr/bin/env python3
"""强制测试压缩逻辑，模拟180k场景"""

from ccc.extractor import ClaudeContextExtractor

def test_compression_logic():
    """直接测试extract_key_messages的逻辑"""
    
    extractor = ClaudeContextExtractor(max_tokens=100000)
    
    # 创建模拟消息（180k tokens）
    messages = []
    
    # 创建180条消息，每条1000 tokens
    for i in range(180):
        # 创建约1000 tokens的内容（约4000字符）
        content = f"消息{i}: " + "这是一条测试消息。" * 200
        
        msg = {
            'type': 'human' if i % 2 == 0 else 'assistant',
            'message': {
                'role': 'user' if i % 2 == 0 else 'assistant',
                'content': [{'type': 'text', 'text': content}]
            }
        }
        messages.append(msg)
    
    # 计算原始大小
    original_tokens = 0
    for msg in messages:
        content = extractor._get_message_content(msg)
        if content:
            original_tokens += extractor.count_tokens(content)
    
    print(f"模拟会话：{len(messages)} 条消息")
    print(f"原始Token数: {original_tokens:,}")
    
    # 执行压缩
    print("\n执行压缩...")
    print("-"*60)
    
    compressed_messages, stats = extractor.extract_key_messages(messages)
    
    # 计算压缩后大小
    compressed_tokens = 0
    front_tokens = 0
    back_tokens = 0
    has_gap = False
    
    for i, msg in enumerate(compressed_messages):
        content = extractor._get_message_content(msg)
        if content:
            tokens = extractor.count_tokens(content)
            compressed_tokens += tokens
            
            # 判断前后部分
            if '[...前面内容已省略...]' in content:
                has_gap = True
                back_tokens += tokens
            elif has_gap:
                back_tokens += tokens
            else:
                front_tokens += tokens
    
    print(f"压缩后消息数: {len(compressed_messages)}")
    print(f"压缩后Token数: {compressed_tokens:,}")
    print(f"压缩比: {compressed_tokens/original_tokens*100:.1f}%")
    
    print(f"\n前部: {front_tokens:,} tokens ({front_tokens/1000:.1f}k)")
    print(f"后部: {back_tokens:,} tokens ({back_tokens/1000:.1f}k)")
    print(f"总计: {compressed_tokens:,} tokens ({compressed_tokens/1000:.1f}k)")
    
    print("\n预期: 100k")
    print(f"实际: {compressed_tokens/1000:.1f}k")
    print(f"差异: {compressed_tokens/1000 - 100:.1f}k ({(compressed_tokens/100000 - 1)*100:+.1f}%)")
    
    # 分析为什么会有差异
    print("\n分析差异原因：")
    print("1. Token计算方式: 使用tiktoken的o200k_base")
    print("2. 内容提取: _get_message_content提取了text内容")
    print(f"3. 压缩策略: 前{front_tokens/1000:.1f}k + 后{back_tokens/1000:.1f}k")
    
    # 验证是否精确到25k+75k
    if abs(front_tokens - 25000) > 1000:
        print(f"⚠️ 前部偏差: {front_tokens - 25000:+,} tokens")
    if abs(back_tokens - 75000) > 1000:
        print(f"⚠️ 后部偏差: {back_tokens - 75000:+,} tokens")

if __name__ == '__main__':
    test_compression_logic()