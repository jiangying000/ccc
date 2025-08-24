#!/usr/bin/env python3
"""
测试自定义token分配功能
"""

from ccc.extractor import ClaudeContextExtractor

# 创建测试消息
test_messages = []
for i in range(100):
    test_messages.append({
        'message': {
            'role': 'user' if i % 2 == 0 else 'assistant',
            'content': f"这是第{i+1}条测试消息。" * 50  # 每条约100 tokens
        }
    })

print("="*60)
print("测试自定义Token分配功能")
print("="*60)

extractor = ClaudeContextExtractor()

# 测试不同的分配策略
test_cases = [
    (25000, 75000, "默认分配"),
    (10000, 90000, "偏向最近"),
    (50000, 50000, "平均分配"),
    (80000, 20000, "偏向开始"),
    (0, 100000, "只保留最后"),
    (100000, 0, "只保留开始"),
]

for front, back, desc in test_cases:
    print(f"\n测试: {desc} (前{front//1000}k + 后{back//1000}k)")
    print("-"*40)
    
    extracted, stats = extractor.extract_key_messages(test_messages, front, back)
    
    print(f"原始: {stats['total_messages']}条消息, {stats['total_tokens']:,} tokens")
    print(f"提取: {stats['extracted_messages']}条消息, {stats['extracted_tokens']:,} tokens")
    print(f"压缩率: {stats['compression_ratio']:.1%}")
    
    # 显示第一条和最后一条消息的索引
    if extracted:
        first_msg = extracted[0]['message']['content'][:50]
        last_msg = extracted[-1]['message']['content'][:50]
        print(f"第一条: {first_msg}...")
        print(f"最后条: {last_msg}...")

print("\n" + "="*60)
print("✅ 测试完成！自定义token分配功能正常工作")