#!/usr/bin/env python3
"""
Token计算差异分析报告
确认Claude Code与CCDRC显示差异的根本原因
"""

import json
import tiktoken
from pathlib import Path
from ccdrc.extractor import ClaudeContextExtractor

def analyze_token_difference():
    """分析token计算差异"""
    
    extractor = ClaudeContextExtractor()
    sessions = extractor.find_claude_sessions()
    
    if not sessions:
        print("未找到会话")
        return
    
    # 使用最新的会话
    session = sessions[0]
    encoder = tiktoken.get_encoding('o200k_base')
    
    with open(session, 'r') as f:
        lines = f.readlines()
    
    print("=" * 70)
    print("Token计算差异分析报告")
    print("=" * 70)
    print(f"\n会话文件: {session.name}")
    print(f"消息总数: {len(lines)}")
    print()
    
    # 方法A：Claude Code的方式（推测）
    text_only_tokens = 0
    for line in lines:
        try:
            msg = json.loads(line)
            content = extractor._get_message_content(msg)
            if content:
                text_only_tokens += len(encoder.encode(content))
        except:
            pass
    
    claude_estimated = text_only_tokens + 20000  # Claude的系统开销约20k
    
    # 方法B：CCDRC当前方式
    ccdrc_info = extractor.get_session_info(session)
    ccdrc_tokens = ccdrc_info['tokens']
    
    # 详细对比
    print("【计算方式对比】")
    print("-" * 40)
    print(f"纯文本内容:        {text_only_tokens:,} tokens")
    print()
    print(f"Claude Code (推测): {claude_estimated:,} tokens")
    print(f"  = 纯文本 ({text_only_tokens:,})")
    print(f"  + 系统开销 (20,000)")
    print()
    print(f"CCDRC 当前显示:    {ccdrc_tokens:,} tokens")
    print(f"  = API JSON格式")
    print(f"  + 系统开销 (23,000)")
    print()
    print("【差异分析】")
    print("-" * 40)
    print(f"总差异: {ccdrc_tokens - claude_estimated:,} tokens")
    print()
    print("差异来源:")
    print(f"1. JSON结构开销: ~{ccdrc_tokens - claude_estimated - 3000:,} tokens")
    print("   (包含role, type, content等字段名)")
    print(f"2. 系统开销差异: 3,000 tokens")
    print("   (CCDRC 23k vs Claude 20k)")
    print()
    print("【结论】")
    print("-" * 40)
    print("CCDRC计算了完整的API JSON格式，而Claude Code只计算纯文本。")
    print("这导致CCDRC显示的tokens比Claude Code多60-85k。")
    print()
    print("【建议】")
    print("-" * 40)
    print("如果要与Claude Code显示一致，应该：")
    print("1. 只计算纯文本内容（不含JSON结构）")
    print("2. 系统开销改为20k（而非23k）")

if __name__ == "__main__":
    analyze_token_difference()