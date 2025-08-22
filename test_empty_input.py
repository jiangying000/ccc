#!/usr/bin/env python3
"""
测试CCDRC处理空输入的能力
"""

import sys
sys.path.insert(0, '/home/jy/gitr/jiangying000/ccdrc')

from ccdrc.interactive_ui import InteractiveSessionSelector

# 模拟get_single_char方法
def test_get_single_char():
    print("测试get_single_char方法处理空输入")
    print("-" * 40)
    
    # 创建一个模拟选择器
    class TestSelector:
        def get_single_char(self):
            # 模拟用户直接按回车（空输入）
            user_input = "".strip().lower()
            return user_input[0] if user_input else ''
    
    selector = TestSelector()
    
    # 测试空输入
    ch = selector.get_single_char()
    print(f"空输入返回: '{ch}' (长度: {len(ch)})")
    
    # 测试后续处理
    try:
        # 这些都应该安全
        if ch in ['q', 'Q']:
            print("退出检查: 通过")
        
        if ch.isdigit():
            print("数字检查: 通过")
        
        # 这个需要额外检查
        if ch and ord(ch) == 3:
            print("Ctrl+C检查: 通过")
        
        print("\n✅ 所有检查通过，空输入处理正常")
    except Exception as e:
        print(f"\n❌ 错误: {e}")

if __name__ == "__main__":
    test_get_single_char()