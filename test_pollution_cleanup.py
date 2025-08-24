#!/usr/bin/env python3
"""
测试：验证历史污染清理功能
确保只清理工具调用JSON，保留正常JSON
"""

from ccc.extractor import ClaudeContextExtractor

def test_pollution_cleanup():
    """测试污染清理功能"""
    
    # 创建包含各种JSON的测试消息
    test_messages = [
        {
            'message': {
                'content': [
                    {
                        'type': 'text',
                        'text': '''这是一个混合内容的消息：
                        
1. 工具调用（需要清理）：
[Tool: Write] {"file_path": "/test.py", "content": "print('hello')"}
[Tool: Bash] {"command": "git status"}

2. 正常的JSON示例（应该保留）：
```json
{
  "name": "John",
  "age": 30,
  "city": "New York"
}
```

3. API返回（应该保留）：
服务器返回: {"status": "success", "data": {"id": 123}}

4. 更多工具调用（需要清理）：
[Tool: Edit] {"file_path": "main.py", "old_string": "foo", "new_string": "bar"}
[Tool: Grep] {"pattern": "def.*"}
'''
                    }
                ]
            }
        },
        {
            'message': {
                'content': [
                    {
                        'type': 'text', 
                        'text': '普通消息，包含代码示例：\n```python\ndata = {"key": "value"}\n```'
                    }
                ]
            }
        }
    ]
    
    # 使用提取器清理
    extractor = ClaudeContextExtractor(verbose=True)
    cleaned = extractor._clean_tool_call_pollution(test_messages)
    
    print("清理结果检查：")
    print("=" * 60)
    
    # 检查第一条消息
    cleaned_text = cleaned[0]['message']['content'][0]['text']
    
    # 验证工具调用JSON被清理
    tool_json_found = False
    if '"file_path":' in cleaned_text and '[Tool:' in cleaned_text:
        print("❌ 工具调用JSON未被清理！")
        tool_json_found = True
    else:
        print("✅ 工具调用JSON已清理")
    
    # 验证正常JSON被保留
    normal_json_preserved = True
    if '"name": "John"' not in cleaned_text:
        print("❌ 正常JSON示例被误删！")
        normal_json_preserved = False
    else:
        print("✅ 正常JSON示例已保留")
    
    if '"status": "success"' not in cleaned_text:
        print("❌ API返回JSON被误删！")
        normal_json_preserved = False
    else:
        print("✅ API返回JSON已保留")
    
    # 检查第二条消息
    cleaned_text2 = cleaned[1]['message']['content'][0]['text']
    if '{"key": "value"}' not in cleaned_text2:
        print("❌ 代码示例中的JSON被误删！")
        normal_json_preserved = False
    else:
        print("✅ 代码示例中的JSON已保留")
    
    print("\n" + "=" * 60)
    print("清理后的第一条消息内容：")
    print("-" * 60)
    print(cleaned_text[:500] + "..." if len(cleaned_text) > 500 else cleaned_text)
    
    return not tool_json_found and normal_json_preserved


def test_specific_patterns():
    """测试特定的清理模式"""
    
    patterns = [
        # (原始文本, 期望结果, 描述)
        ('[Tool: Write] {"file_path": "/test.py", "content": "code"}', '[Created file]', 'Write工具'),
        ('[Tool: Edit] {"file_path": "a.py", "old_string": "a", "new_string": "b"}', '[Edited file]', 'Edit工具'),
        ('[Tool: Bash] {"command": "ls -la"}', '[Executed command]', 'Bash工具'),
        ('正常的JSON: {"data": "value"}', '正常的JSON: {"data": "value"}', '普通JSON'),
        ('API返回 {"status": 200}', 'API返回 {"status": 200}', 'API JSON'),
    ]
    
    extractor = ClaudeContextExtractor()
    
    print("\n特定模式测试：")
    print("=" * 60)
    
    all_passed = True
    for original, expected, description in patterns:
        # 创建测试消息
        msg = {'message': {'content': [{'type': 'text', 'text': original}]}}
        cleaned = extractor._clean_tool_call_pollution([msg])
        result = cleaned[0]['message']['content'][0]['text']
        
        if result == expected:
            print(f"✅ {description}: 正确")
        else:
            print(f"❌ {description}: 错误")
            print(f"   原始: {original}")
            print(f"   期望: {expected}")
            print(f"   实际: {result}")
            all_passed = False
    
    return all_passed


if __name__ == "__main__":
    print("=" * 70)
    print("测试：历史污染清理（保留正常JSON）")
    print("=" * 70)
    
    # 运行测试
    test1 = test_pollution_cleanup()
    test2 = test_specific_patterns()
    
    print("\n" + "=" * 70)
    if test1 and test2:
        print("🎉 所有测试通过！")
        print("✅ 工具调用JSON被清理")
        print("✅ 正常JSON数据被保留")
        print("✅ 压缩时会自动修复历史污染")
    else:
        print("⚠️ 部分测试失败，需要调整清理逻辑")