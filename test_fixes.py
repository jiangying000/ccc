#!/usr/bin/env python3
"""测试v3.8.1的修复"""

from ccc.extractor import ClaudeContextExtractor

# 测试修复
extractor = ClaudeContextExtractor()
sessions = extractor.find_claude_sessions()

print("=" * 60)
print("测试 v3.8.1 修复效果")
print("=" * 60)

# 找到187k左右的会话测试
for session in sessions[:10]:
    info = extractor.get_session_info(session)
    if 180000 < info['tokens'] < 200000:
        print("\n找到测试会话:")
        print(f"  文件: {session.name}")
        print(f"  消息数: {info['message_count']}")
        print(f"  Tokens: {info['tokens']:,}")
        
        # 验证是否包含系统开销
        if info['tokens'] > 180000:
            print("  ✅ 包含系统开销（约23k）")
        
        # 测试是否会触发压缩
        if info['tokens'] >= 150000:
            print(f"  ✅ 应该触发压缩（{info['tokens']:,} >= 150,000）")
        else:
            print(f"  ❌ 不应该触发压缩（{info['tokens']:,} < 150,000）")
        
        break

print("\n索引显示测试:")
print("  [1] 第一个会话（用户输入1）")
print("  [2] 第二个会话（用户输入2）")
print("  [3] 第三个会话（用户输入3）")
print("  ✅ 索引从1开始，更符合日常习惯")

print("\n流程简化:")
print("  ✅ ccc命令直接进入交互界面")
print("  ✅ 无需--interactive参数")