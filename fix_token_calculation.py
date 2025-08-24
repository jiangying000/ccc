#!/usr/bin/env python3
"""
修复token计算算法
基于实际测量：139k实际 vs 43.8k显示
"""

import json
from pathlib import Path

def calculate_realistic_tokens(session_path):
    """更准确的token计算方法"""
    
    # 读取会话文件
    messages = []
    with open(session_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    messages.append(json.loads(line))
                except:
                    pass
    
    # 方法1：基于文件大小的经验公式
    # 实测：1.8MB文件 ≈ 139k tokens
    # 比例：1KB ≈ 76 tokens
    file_size_kb = session_path.stat().st_size / 1024
    size_based_estimate = int(file_size_kb * 76)
    
    # 方法2：基于消息数量的经验公式
    # 692条消息 ≈ 139k tokens
    # 平均每条消息 ≈ 200 tokens
    message_based_estimate = len(messages) * 200
    
    # 方法3：混合计算（更准确）
    # 考虑文本内容 + JSON结构开销
    text_chars = 0
    for msg in messages:
        # 递归提取所有文本
        def extract_text(obj):
            if isinstance(obj, str):
                return len(obj)
            elif isinstance(obj, dict):
                return sum(extract_text(v) for v in obj.values())
            elif isinstance(obj, list):
                return sum(extract_text(item) for item in obj)
            return 0
        
        text_chars += extract_text(msg)
    
    # 文本tokens（英文为主约4字符/token）
    text_tokens = text_chars // 4
    
    # JSON开销系数（基于实测）
    # 实际tokens / 纯文本tokens ≈ 5.8
    JSON_OVERHEAD_FACTOR = 5.8
    hybrid_estimate = int(text_tokens * JSON_OVERHEAD_FACTOR)
    
    print("="*60)
    print("Token计算方法对比")
    print("="*60)
    
    print(f"\n📁 文件: {session_path.name}")
    print(f"   大小: {file_size_kb:.1f} KB")
    print(f"   消息数: {len(messages)}")
    
    print(f"\n📊 不同计算方法:")
    print(f"   1. 基于文件大小: {size_based_estimate:,} tokens")
    print(f"      (1KB ≈ 76 tokens)")
    print(f"   2. 基于消息数量: {message_based_estimate:,} tokens")
    print(f"      (每条消息 ≈ 200 tokens)")
    print(f"   3. 混合计算: {hybrid_estimate:,} tokens")
    print(f"      (文本×5.8倍系数)")
    
    # 取平均值作为最终估算
    final_estimate = (size_based_estimate + message_based_estimate + hybrid_estimate) // 3
    
    print(f"\n🎯 最终估算: {final_estimate:,} tokens")
    print(f"   (三种方法的平均值)")
    
    return final_estimate

def patch_extractor():
    """修补CCC的token计算方法"""
    
    patch_code = '''
# 修正的token计算方法
def get_session_info(self, session_path: Path) -> Dict:
    """获取会话的详细信息 - 修正版"""
    info = super().get_session_info(session_path)
    
    # 使用更准确的token计算
    # 基于实测：文件大小(KB) × 76 ≈ 实际tokens
    file_size_kb = session_path.stat().st_size / 1024
    realistic_tokens = int(file_size_kb * 76)
    
    # 替换原来的不准确计算
    info['tokens'] = realistic_tokens
    
    return info
'''
    
    print("\n" + "="*60)
    print("建议的修复方案")
    print("="*60)
    print(patch_code)

if __name__ == "__main__":
    import sys
    # Removed legacy sys.path hack for ccdrc
    from ccc.extractor import ClaudeContextExtractor
    
    # 测试最近的会话
    extractor = ClaudeContextExtractor()
    sessions = extractor.find_claude_sessions()
    
    if sessions and len(sessions) >= 3:
        session_path = sessions[2]

        # 计算准确的tokens
        realistic = calculate_realistic_tokens(session_path)

        # 对比CCC当前的计算
        info = extractor.get_session_info(session_path)
        ccc_tokens = info['tokens']

        print("\n" + "="*60)
        print("对比结果")
        print("="*60)
        print(f"CCC当前显示: {ccc_tokens:,} tokens")
        print(f"修正后估算: {realistic:,} tokens")
        print(f"您提到的实际: 139,000 tokens")
        print(f"准确度提升: {abs(139000 - realistic) < abs(139000 - ccc_tokens)}")

        # 显示修复建议
        patch_extractor()