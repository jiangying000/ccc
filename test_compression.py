#!/usr/bin/env python3
"""测试CCC的压缩功能"""

from pathlib import Path
from ccc.extractor import ClaudeContextExtractor

def test_compression():
    """测试会话压缩的实际效果"""
    
    # 初始化提取器
    extractor = ClaudeContextExtractor(max_tokens=100000)
    
    # 测试前3个会话
    sessions_dir = Path.home() / '.claude' / 'projects' / '-home-jy-gitr-felo-mygpt'
    sessions = sorted(sessions_dir.glob('*.jsonl'), key=lambda x: x.stat().st_mtime, reverse=True)[:3]
    
    for i, session_path in enumerate(sessions, 1):
        print(f"\n{'='*60}")
        print(f"会话 {i}: {session_path.name}")
        print(f"{'='*60}")
        
        # 解析会话
        result = extractor.parse_session(session_path)
        if isinstance(result, tuple):
            messages = result[0]
        else:
            messages = result
        
        # 原始大小
        original_tokens = 0
        for msg in messages:
            content = extractor._get_message_content(msg)
            if content:
                original_tokens += extractor.count_tokens(content)
        
        print(f"原始大小: {original_tokens:,} tokens")
        
        if original_tokens > 100000:
            # 执行压缩
            compressed_messages, stats = extractor.extract_key_messages(list(messages))
            
            # 计算压缩后大小
            compressed_tokens = 0
            for msg in compressed_messages:
                content = extractor._get_message_content(msg)
                if content:
                    compressed_tokens += extractor.count_tokens(content)
            
            print(f"压缩后大小: {compressed_tokens:,} tokens")
            print(f"压缩比: {compressed_tokens/original_tokens*100:.1f}%")
            print(f"统计信息: {stats}")
            
            # 分析前后部分
            front_tokens = 0
            back_tokens = 0
            for j, msg in enumerate(compressed_messages):
                content = extractor._get_message_content(msg)
                if content:
                    tokens = extractor.count_tokens(content)
                    if j < len(compressed_messages) // 2:
                        front_tokens += tokens
                    else:
                        back_tokens += tokens
            
            print(f"前半部分: {front_tokens:,} tokens")
            print(f"后半部分: {back_tokens:,} tokens")
            
            # 检查是否有被截断的消息
            truncated_count = 0
            for msg in compressed_messages:
                content = extractor._get_message_content(msg)
                if content and ('[...内容已截断...]' in content or '[...前面内容已省略...]' in content):
                    truncated_count += 1
            print(f"被截断的消息数: {truncated_count}")
        else:
            print("会话小于100k，不需要压缩")

if __name__ == '__main__':
    test_compression()