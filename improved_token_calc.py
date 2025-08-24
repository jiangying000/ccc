#!/usr/bin/env python3
"""
Improved token calculation: prefer cache_read_input_tokens
Based on research: Claude Code likely shows cache_read_input_tokens.
"""

import json
from pathlib import Path
from ccc.extractor import ClaudeContextExtractor

def get_accurate_token_count(session_path):
    """
    获取准确的token计数，匹配Claude Code的显示
    
    策略：
    1. 优先使用最新的cache_read_input_tokens（代表当前上下文窗口）
    2. 如果没有，回退到内容提取计算
    """
    
    # 尝试读取cache_read_input_tokens
    cache_read_latest = None
    has_usage_count = 0
    
    try:
        with open(session_path, 'r') as f:
            for line in f:
                msg = json.loads(line)
                # Find usage in assistant messages
                if msg.get('type') == 'assistant' and 'message' in msg:
                    usage = msg['message'].get('usage')
                    if usage:
                        has_usage_count += 1
                        cache_read = usage.get('cache_read_input_tokens', 0)
                        if cache_read > 0:
                            cache_read_latest = cache_read
    except Exception:
        pass
    
    # 如果找到cache_read，使用它
    if cache_read_latest:
        # 这是Claude Code很可能使用的值
        return {
            'method': 'cache_read',
            'tokens': cache_read_latest,
            'confidence': 'high',
            'note': f'基于cache_read_input_tokens（{has_usage_count}个usage记录）'
        }
    
    # Fallback: use CCC content-based calculation
    extractor = ClaudeContextExtractor()
    info = extractor.get_session_info(Path(session_path))
    
    return {
        'method': 'content_extraction',
        'tokens': info.get('tokens', 0),
        'confidence': 'medium',
        'note': '基于内容提取计算（无cache_read数据）'
    }


def test_accuracy():
    """测试新方法的准确性"""
    sessions_dir = Path.home() / '.claude' / 'projects' / '-home-jy-gitr-felo-mygpt'
    sessions = sorted(sessions_dir.glob('*.jsonl'), key=lambda x: x.stat().st_mtime, reverse=True)[:3]
    
    print("测试改进的Token计算方法")
    print("="*60)
    
    for i, session in enumerate(sessions, 1):
        result = get_accurate_token_count(session)
        
        print(f"\n会话{i}: {session.name[:20]}...")
        print(f"  方法: {result['method']}")
        print(f"  Tokens: {result['tokens']:,} ({result['tokens']/1000:.1f}k)")
        print(f"  置信度: {result['confidence']}")
        print(f"  说明: {result['note']}")
    
    print("\n"+"="*60)
    print("总结：")
    print("1. cache_read_input_tokens是Claude Code最可能显示的值")
    print("2. 它代表'当前上下文窗口大小'，不是累计使用")
    print("3. CCC应优先读取这个值以匹配Claude Code")


if __name__ == '__main__':
    test_accuracy()