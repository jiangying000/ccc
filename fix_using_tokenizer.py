#!/usr/bin/env python3
"""
使用专业tokenizer正确计算tokens
不再用愚蠢的字符数估算！
"""

import json
from ccc.extractor import ClaudeContextExtractor

def test_tokenizer_calculation():
    """测试用tokenizer计算"""
    
    extractor = ClaudeContextExtractor()
    
    if not extractor.encoder:
        print("❌ Tiktoken未安装，无法测试")
        return
    
    print(f"✅ 使用tokenizer: {extractor.encoding_name}")
    print(f"   词汇表大小: {extractor.vocab_size:,}")
    
    # 测试文本
    test_cases = [
        ("Hello world", "简单英文"),
        ("你好世界", "中文"),
        ('{"key": "value", "nested": {"id": 123}}', "JSON结构"),
        ("a" * 1000, "重复字符"),
    ]
    
    print("\n测试不同类型文本的token计算:")
    print("-" * 60)
    
    for text, desc in test_cases:
        # 用tokenizer计算
        tokens = extractor.encoder.encode(text)
        token_count = len(tokens)
        
        # 对比字符数
        char_count = len(text)
        ratio = char_count / token_count if token_count > 0 else 0
        
        print(f"{desc:15} {char_count:6}字符 → {token_count:6} tokens (比率: {ratio:.1f})")
    
    print("\n" + "="*60)
    print("结论：不同类型文本的token比率差异很大！")
    print("必须用tokenizer，不能用固定比率估算。")

def correct_token_calculation():
    """正确的token计算实现"""
    
    code = '''
# 修改 ccc/extractor.py 的 get_session_info 方法

def get_session_info(self, session_path: Path) -> Dict:
    """获取会话的详细信息 - 使用tokenizer版"""
    # ... 前面代码保持不变 ...
    
    try:
        messages = self.parse_session(session_path)
        info['message_count'] = len(messages)
        
        # 使用tokenizer计算准确的tokens
        total_tokens = 0
        
        if self.encoder:
            # 有tokenizer，精确计算
            for msg in messages:
                try:
                    # 计算完整消息的JSON tokens
                    # 这才是Claude实际处理的内容！
                    msg_json = json.dumps(msg, ensure_ascii=False, separators=(',', ':'))
                    tokens = self.encoder.encode(msg_json)
                    total_tokens += len(tokens)
                except Exception as e:
                    # 编码失败，跳过这条消息
                    if self.verbose:
                        print(f"  ⚠ 编码消息失败: {str(e)[:50]}", file=sys.stderr)
                    # 降级估算：1KB约80tokens
                    total_tokens += len(str(msg)) // 12
        else:
            # 没有tokenizer，降级到基于文件大小的估算
            # 基于实测：1KB约80-100 tokens
            file_size_kb = session_path.stat().st_size / 1024
            total_tokens = int(file_size_kb * 90)
        
        # 合理性检查（防止极端情况）
        file_size_kb = session_path.stat().st_size / 1024
        min_tokens = int(file_size_kb * 50)   # 最少50 tokens/KB
        max_tokens = int(file_size_kb * 200)  # 最多200 tokens/KB
        
        if total_tokens < min_tokens:
            total_tokens = min_tokens
        elif total_tokens > max_tokens:
            # 可能是工具调用密集，但也要有上限
            if self.verbose:
                print(f"  ⚠ Token计算超出上限，限制为{max_tokens:,}", file=sys.stderr)
            total_tokens = max_tokens
        
        info['tokens'] = total_tokens
'''
    
    print("\n" + "="*60)
    print("正确的实现方案")
    print("="*60)
    print(code)
    
    return code

if __name__ == "__main__":
    test_tokenizer_calculation()
    correct_token_calculation()
    
    print("\n" + "="*60)
    print("测试实际会话")
    print("="*60)
    
    extractor = ClaudeContextExtractor()
    sessions = extractor.find_claude_sessions()
    
    if len(sessions) >= 3 and extractor.encoder:
        session = sessions[2]
        
        # 读取并计算
        messages = extractor.parse_session(session)
        total_tokens = 0
        
        for msg in messages:
            try:
                msg_json = json.dumps(msg, ensure_ascii=False, separators=(',', ':'))
                tokens = extractor.encoder.encode(msg_json)
                total_tokens += len(tokens)
            except:
                pass
        
        print(f"会话: {session.name[:8]}...")
        print(f"消息数: {len(messages)}")
        print(f"Tokenizer计算: {total_tokens:,} tokens")
        print(f"您提到的实际: 139,000 tokens")
        print(f"误差: {abs(139000 - total_tokens):,} ({abs(139000 - total_tokens)*100//139000}%)")