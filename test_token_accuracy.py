#!/usr/bin/env python3
"""
测试Token计算准确性修复
"""

from ccc.extractor import ClaudeContextExtractor

print("="*60)
print("Token计算准确性测试")
print("="*60)

# 创建测试消息（模拟实际场景）
test_messages = []
for i in range(200):
    test_messages.append({
        'message': {
            'role': 'user' if i % 2 == 0 else 'assistant',
            'content': f"这是第{i+1}条消息。" + "测试内容" * 100  # 每条约200 tokens
        }
    })

extractor = ClaudeContextExtractor()

print(f"\n总消息数: {len(test_messages)}")
total_tokens = sum(extractor.count_tokens(msg['message']['content']) 
                  for msg in test_messages)
print(f"总tokens: {total_tokens:,}")

# 测试不同的分配
test_cases = [
    (25, 75, "默认"),
    (50, 50, "平均"),
    (30, 70, "自定义"),
]

for front_k, back_k, desc in test_cases:
    print(f"\n{'='*40}")
    print(f"测试: {desc} (前{front_k}k + 后{back_k}k)")
    print("-"*40)
    
    extracted, stats = extractor.extract_key_messages(
        test_messages, 
        front_k * 1000, 
        back_k * 1000
    )
    
    print(f"原始: {stats['total_tokens']:,} tokens")
    print(f"提取内容: {stats['extracted_tokens']:,} tokens")
    print(f"预估实际: ~{stats['actual_tokens']:,} tokens")
    
    # 计算比例
    overhead = stats['actual_tokens'] / stats['extracted_tokens'] if stats['extracted_tokens'] > 0 else 0
    print(f"格式化开销: {overhead:.2f}x")
    
    # 安全检查
    if stats['actual_tokens'] > 180000:
        print("⚠️  警告: 接近200k限制!")
    elif stats['actual_tokens'] > 150000:
        print("⚠  注意: tokens较多")
    else:
        print("✅ 安全范围内")

print("\n" + "="*60)
print("修复说明:")
print("- 现在考虑了~40%的格式化开销")
print("- 实际提取的内容会减少以确保不超限")
print("- 显示预估的实际tokens供参考")