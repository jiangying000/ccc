#!/usr/bin/env python3
"""
逆向工程Claude的token计算
基于JSONL文件的真实结构
"""

import json
from ccc.extractor import ClaudeContextExtractor

def analyze_jsonl_structure(jsonl_path):
    """分析JSONL文件的真实结构和token占用"""
    
    messages = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    messages.append(json.loads(line))
                except Exception:
                    pass
    
    print("="*60)
    print("JSONL结构分析")
    print("="*60)
    
    # 分析不同部分的大小
    total_chars = 0
    text_content_chars = 0
    metadata_chars = 0
    structure_chars = 0
    
    for msg in messages:
        # 完整消息的JSON大小
        msg_json = json.dumps(msg, ensure_ascii=False, separators=(',', ':'))
        total_chars += len(msg_json)
        
        # 提取纯文本内容
        text = ""
        if 'message' in msg and isinstance(msg['message'], dict):
            content = msg['message'].get('content', [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        text += item.get('text', '')
            elif isinstance(content, str):
                text = content
        
        text_content_chars += len(text)
        
        # 元数据部分（不包括message内容）
        metadata = {
            'parentUuid': msg.get('parentUuid'),
            'isSidechain': msg.get('isSidechain'),
            'userType': msg.get('userType'),
            'cwd': msg.get('cwd'),
            'sessionId': msg.get('sessionId'),
            'version': msg.get('version'),
            'gitBranch': msg.get('gitBranch'),
            'type': msg.get('type'),
            'uuid': msg.get('uuid'),
            'timestamp': msg.get('timestamp'),
        }
        metadata_json = json.dumps(metadata, ensure_ascii=False, separators=(',', ':'))
        metadata_chars += len(metadata_json)
    
    # 结构开销 = 总大小 - 纯文本
    structure_chars = total_chars - text_content_chars
    
    print(f"\n📁 文件: {jsonl_path.name}")
    print(f"   消息数: {len(messages)}")
    print(f"   文件大小: {jsonl_path.stat().st_size / 1024:.1f} KB")
    
    print("\n📊 字符统计:")
    print(f"   总JSON字符: {total_chars:,}")
    print(f"   纯文本内容: {text_content_chars:,} ({text_content_chars*100//total_chars}%)")
    print(f"   元数据: {metadata_chars:,} ({metadata_chars*100//total_chars}%)")
    print(f"   JSON结构: {structure_chars:,} ({structure_chars*100//total_chars}%)")
    
    # Token估算（基于Claude的tokenizer特点）
    # Claude对JSON的处理：
    # 1. 英文文本：约3.5字符/token
    # 2. JSON键值对：约2.5字符/token（因为有很多短键）
    # 3. UUID等：约2字符/token（密集字符）
    
    text_tokens = text_content_chars / 3.5
    structure_tokens = structure_chars / 2.5
    total_tokens_estimate = text_tokens + structure_tokens
    
    print("\n🎯 Token估算:")
    print(f"   文本tokens: {int(text_tokens):,}")
    print(f"   结构tokens: {int(structure_tokens):,}")
    print(f"   总计: {int(total_tokens_estimate):,}")
    
    # 基于文件大小的经验公式
    # 您提到的实际：1.8MB ≈ 139k tokens
    # 比例：1KB ≈ 77 tokens
    file_size_kb = jsonl_path.stat().st_size / 1024
    empirical_tokens = int(file_size_kb * 77)
    
    print("\n📐 经验公式:")
    print(f"   基于文件大小(1KB≈77tokens): {empirical_tokens:,}")
    
    return {
        'messages': len(messages),
        'total_chars': total_chars,
        'text_chars': text_content_chars,
        'structure_chars': structure_chars,
        'estimated_tokens': int(total_tokens_estimate),
        'empirical_tokens': empirical_tokens
    }

def compare_with_ccc():
    """对比CCC的计算和实际"""
    
    extractor = ClaudeContextExtractor()
    sessions = extractor.find_claude_sessions()
    
    if len(sessions) < 3:
        print("没有足够的会话")
        return
    
    # 分析第3个会话（您提到的）
    session_path = sessions[2]
    
    # CCC的计算
    info = extractor.get_session_info(session_path)
    ccc_tokens = info['tokens']
    
    # 我们的分析
    analysis = analyze_jsonl_structure(session_path)
    
    print("\n" + "="*60)
    print("对比分析")
    print("="*60)
    
    print(f"\nCCC显示: {ccc_tokens:,} tokens")
    print(f"结构分析估算: {analysis['estimated_tokens']:,} tokens")
    print(f"经验公式: {analysis['empirical_tokens']:,} tokens")
    print("您提到的实际: 139,000 tokens")
    
    print("\n误差分析:")
    print(f"CCC误差: {abs(139000 - ccc_tokens):,} ({abs(139000 - ccc_tokens)*100//139000}%)")
    print(f"结构分析误差: {abs(139000 - analysis['estimated_tokens']):,} ({abs(139000 - analysis['estimated_tokens'])*100//139000}%)")
    print(f"经验公式误差: {abs(139000 - analysis['empirical_tokens']):,} ({abs(139000 - analysis['empirical_tokens'])*100//139000}%)")
    
    print("\n💡 结论:")
    print("CCC只计算了message.content.text部分，")
    print("忽略了JSONL的所有元数据和结构开销。")
    print("实际上Claude需要处理完整的JSONL，包括：")
    print("- parentUuid, sessionId, timestamp等元数据")
    print("- message的role和content数组结构")
    print("- type字段和其他控制信息")

if __name__ == "__main__":
    compare_with_ccc()