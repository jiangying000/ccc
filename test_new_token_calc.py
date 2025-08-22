#!/usr/bin/env python3
"""
测试新的token计算准确性
"""

import sys
sys.path.insert(0, '/home/jy/gitr/jiangying000/ccdrc')
from ccdrc.extractor import ClaudeContextExtractor

def test_new_calculation():
    """测试新的token计算"""
    
    extractor = ClaudeContextExtractor()
    sessions = extractor.find_claude_sessions()
    
    if len(sessions) < 3:
        print("没有足够的会话进行测试")
        return
    
    print("="*60)
    print("测试新的Token计算")
    print("="*60)
    
    # 测试前3个会话
    for i in range(min(3, len(sessions))):
        session = sessions[i]
        info = extractor.get_session_info(session)
        
        print(f"\n[{i+1}] 会话: {session.name[:8]}...")
        print(f"    文件大小: {info['size']/1024:.1f} KB")
        print(f"    消息数: {info['message_count']}")
        print(f"    新计算tokens: {info['tokens']:,}")
        
        # 如果是第3个会话（用户提到的）
        if i == 2:
            print(f"    您提到的实际: 139,000")
            error = abs(139000 - info['tokens'])
            error_pct = error * 100 / 139000
            print(f"    误差: {error:,} ({error_pct:.1f}%)")
            
            if error_pct < 10:
                print("    ✅ 误差在10%以内，计算准确！")
            elif error_pct < 20:
                print("    ⚠️  误差在20%以内，基本准确")
            else:
                print("    ❌ 误差超过20%，需要进一步优化")
    
    print("\n" + "="*60)
    print("结论")
    print("="*60)
    print("新的计算方法考虑了：")
    print("1. 完整的JSONL结构（不只是文本内容）")
    print("2. 元数据开销（parentUuid, sessionId等）")
    print("3. JSON序列化的字符开销")
    print("4. Claude特定的tokenizer差异（调整系数1.09）")

if __name__ == "__main__":
    test_new_calculation()