#!/usr/bin/env python3
"""
测试：验证工具调用不会产生JSON污染
"""

import json
import sys
import os
sys.path.insert(0, '/home/jy/gitr/jiangying000/ccdrc')

from ccdrc.extractor import ClaudeContextExtractor

def test_tool_call_extraction():
    """测试工具调用的提取是否避免了JSON"""
    
    # 创建测试消息，包含工具调用
    test_message = {
        'message': {
            'content': [
                {
                    'type': 'text',
                    'text': '我要创建一个文件'
                },
                {
                    'type': 'tool_use',
                    'name': 'Write',
                    'input': {
                        'file_path': '/test/file.py',
                        'content': 'def hello():\n    print("Hello World")'
                    }
                },
                {
                    'type': 'tool_result',
                    'content': 'File created successfully'
                }
            ]
        }
    }
    
    # 使用提取器
    extractor = ClaudeContextExtractor()
    content = extractor._get_message_content(test_message)
    
    print("提取的内容：")
    print("=" * 60)
    print(content)
    print("=" * 60)
    
    # 检查是否包含JSON
    has_json = False
    json_indicators = ['{', '}', '"file_path":', '"content":', 'def hello()']
    
    for indicator in json_indicators:
        if indicator in content:
            print(f"❌ 发现JSON污染: {indicator}")
            has_json = True
    
    if not has_json:
        print("✅ 没有JSON污染！工具调用已安全净化")
    else:
        print("\n⚠️ 警告：仍然存在JSON格式，可能污染上下文")
    
    return not has_json


def test_multiple_tools():
    """测试多个工具调用"""
    
    test_message = {
        'message': {
            'content': [
                {'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'git status'}},
                {'type': 'tool_use', 'name': 'Grep', 'input': {'pattern': 'def.*', 'path': '/src'}},
                {'type': 'tool_use', 'name': 'TodoWrite', 'input': {'todos': [
                    {'content': 'task1', 'status': 'pending'},
                    {'content': 'task2', 'status': 'in_progress'}
                ]}},
            ]
        }
    }
    
    extractor = ClaudeContextExtractor()
    content = extractor._get_message_content(test_message)
    
    print("\n多工具调用测试：")
    print("=" * 60)
    print(content)
    print("=" * 60)
    
    # 验证格式
    lines = content.strip().split('\n')
    for line in lines:
        if line.startswith('[') and line.endswith(']'):
            print(f"✅ 安全格式: {line}")
        else:
            print(f"⚠️ 检查格式: {line}")
    
    # 确保没有JSON
    if '{' not in content and '"' not in content:
        print("\n✅ 所有工具调用都已净化，无JSON污染")
        return True
    else:
        print("\n❌ 检测到潜在的JSON格式")
        return False


def test_context_summary():
    """测试完整的上下文摘要生成"""
    
    messages = [
        {
            'message': {
                'role': 'user',
                'content': [{'type': 'text', 'text': '帮我创建一个Python脚本'}]
            }
        },
        {
            'message': {
                'role': 'assistant',
                'content': [
                    {'type': 'text', 'text': '好的，我来创建一个Python脚本'},
                    {'type': 'tool_use', 'name': 'Write', 'input': {
                        'file_path': 'script.py',
                        'content': 'print("Hello")'
                    }}
                ]
            }
        },
        {
            'message': {
                'content': [
                    {'type': 'tool_result', 'content': 'File created'}
                ]
            }
        }
    ]
    
    extractor = ClaudeContextExtractor()
    summary = extractor.create_context_summary(messages, {
        'extracted_messages': len(messages),
        'compression_ratio': 0.5,
        'extracted_tokens': 100
    })
    
    print("\n生成的上下文摘要：")
    print("=" * 60)
    print(summary)
    print("=" * 60)
    
    # 检查JSON污染
    if '"file_path"' in summary or '"content"' in summary:
        print("\n❌ 摘要中包含JSON，会污染上下文！")
        return False
    else:
        print("\n✅ 摘要安全，没有JSON污染")
        return True


if __name__ == "__main__":
    print("=" * 70)
    print("测试：工具调用净化（防止JSON污染）")
    print("=" * 70)
    
    results = []
    
    # 运行测试
    results.append(("基础工具调用", test_tool_call_extraction()))
    results.append(("多工具调用", test_multiple_tools()))
    results.append(("完整摘要生成", test_context_summary()))
    
    # 总结
    print("\n" + "=" * 70)
    print("测试结果总结：")
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n🎉 所有测试通过！工具调用不会产生JSON污染")
        print("大模型可以正常工作，不会被误导输出工具调用文本")
    else:
        print("\n⚠️ 部分测试失败，需要进一步修复")