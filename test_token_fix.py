#!/usr/bin/env python3
"""
测试Token计算修复的准确性
"""

import os
from ccc.extractor import ClaudeContextExtractor
from pathlib import Path

def test_token_calculation():
    """测试token计算的准确性"""
    
    print("测试修复后的Token计算")
    print("="*80)
    
    # 创建提取器
    extractor = ClaudeContextExtractor(verbose=True)
    
    # 测试的会话文件
    test_sessions = [
        {
            'path': '/home/jy/.claude/projects/-home-jy-gitr-felo-mygpt/0390399b-11e1-4039-a349-9d337a44128f.jsonl',
            'expected': 138000,
            'name': '会话1'
        },
        {
            'path': '/home/jy/.claude/projects/-home-jy-gitr-felo-mygpt/fc7d84bf-30ff-48b0-b3ee-5059cc95163a.jsonl',
            'expected': 175000,
            'name': '会话2'
        },
        {
            'path': '/home/jy/.claude/projects/-home-jy-gitr-felo-mygpt/5b35f399-ea06-4a9f-94e0-e5db6bc1e374.jsonl',
            'expected': 139000,
            'name': '会话3'
        }
    ]
    
    results = []
    
    for session in test_sessions:
        if not os.path.exists(session['path']):
            print(f"⚠️  {session['name']}文件不存在，跳过")
            continue
            
        print(f"\n测试{session['name']}:")
        print(f"  文件: {os.path.basename(session['path'])}")
        
        # 获取会话信息（包含token计算）
        info = extractor.get_session_info(Path(session['path']))
        
        calculated = info.get('tokens', 0)
        expected = session['expected']
        
        # 计算误差
        diff = calculated - expected
        error_rate = (diff / expected * 100) if expected > 0 else 0
        
        print(f"  计算值: {calculated:,} tokens")
        print(f"  期望值: {expected:,} tokens")
        print(f"  差异: {diff:+,} ({error_rate:+.1f}%)")
        
        results.append({
            'name': session['name'],
            'calculated': calculated,
            'expected': expected,
            'error': error_rate
        })
    
    # 总结
    print("\n" + "="*80)
    print("测试总结:")
    
    if results:
        avg_error = sum(abs(r['error']) for r in results) / len(results)
        print(f"  平均绝对误差: {avg_error:.1f}%")
        
        if avg_error < 10:
            print("  ✅ 修复成功！误差在可接受范围内")
        elif avg_error < 20:
            print("  ⚠️  误差较大，但可以使用")
        else:
            print("  ❌ 误差过大，需要进一步优化")
    else:
        print("  ⚠️  没有可测试的会话文件")
    
    return results

if __name__ == "__main__":
    test_token_calculation()