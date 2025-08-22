#!/usr/bin/env python3
"""
测试动态Token计算（不用固定系数）
"""

from ccdrc.extractor import ClaudeContextExtractor

print("="*60)
print("动态Token计算测试")
print("="*60)

# 创建测试消息
test_messages = []
for i in range(100):
    test_messages.append({
        'message': {
            'role': 'user' if i % 2 == 0 else 'assistant',
            'content': f"这是第{i+1}条测试消息。" + "内容" * 200  # 每条约400 tokens
        }
    })

extractor = ClaudeContextExtractor()

# 测试不同的分配
test_cases = [
    (10, 20, "小规模"),
    (25, 75, "默认"),
    (50, 100, "大规模"),
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
    
    print(f"输入目标: {front_k}k + {back_k}k = {front_k+back_k}k tokens")
    print(f"提取内容: {stats['extracted_tokens']:,} tokens")
    print(f"格式化后: {stats['formatted_tokens']:,} tokens (实际)")
    
    # 计算开销
    if stats['extracted_tokens'] > 0:
        overhead = stats['formatted_tokens'] - stats['extracted_tokens']
        overhead_pct = (overhead / stats['extracted_tokens']) * 100
        print(f"格式化开销: +{overhead:,} tokens ({overhead_pct:.1f}%)")
    
    # 安全检查
    if stats['formatted_tokens'] > 200000:
        print("❌ 超过200k限制!")
    elif stats['formatted_tokens'] > 180000:
        print("⚠️  接近200k限制")
    elif stats['formatted_tokens'] > 150000:
        print("⚠  tokens较多")
    else:
        print("✅ 安全范围")

print("\n" + "="*60)
print("说明:")
print("- 动态计算：基于实际格式化输出")
print("- 每条消息约增加20 tokens（角色标记、换行等）")
print("- 精确显示最终发送给Claude的tokens数")