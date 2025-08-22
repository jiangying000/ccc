#!/usr/bin/env python3
"""
历史污染清理器 - 清理已经被JSON污染的历史消息
用于修复之前版本CCDRC产生的问题
"""

import re
import json
from typing import Dict, Any

def clean_json_pollution(text: str) -> str:
    """
    清理文本中的JSON污染
    
    Args:
        text: 可能包含JSON污染的文本
        
    Returns:
        清理后的文本
    """
    if not text:
        return text
    
    # 检测并清理不同类型的工具调用JSON
    patterns = [
        # [Tool: Name] {json} 格式
        (r'\[Tool:\s*(\w+)\]\s*(\{[^}]*\})', clean_tool_call),
        # [Tool: Name] {"key": "value", ...} 多行JSON
        (r'\[Tool:\s*(\w+)\]\s*(\{[\s\S]*?\n\})', clean_tool_call),
        # 直接的JSON工具调用
        (r'^\s*\{\s*"tool":\s*"(\w+)"[^}]*\}', clean_direct_json),
        # function_calls格式
        (r'<function_calls>[\s\S]*?</function_calls>', '[Tool call executed]'),
        # 遗留的file_path, content等键值对
        (r'"file_path":\s*"[^"]*"', ''),
        (r'"content":\s*"[^"]*"', ''),
        (r'"command":\s*"[^"]*"', ''),
        (r'"pattern":\s*"[^"]*"', ''),
    ]
    
    cleaned = text
    for pattern, replacement in patterns:
        if callable(replacement):
            cleaned = re.sub(pattern, replacement, cleaned)
        else:
            cleaned = re.sub(pattern, replacement, cleaned)
    
    # 清理多余的空行
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    return cleaned.strip()


def clean_tool_call(match) -> str:
    """清理工具调用JSON，转换为简洁描述"""
    tool_name = match.group(1)
    json_str = match.group(2)
    
    # 尝试解析JSON以提取关键信息
    try:
        data = json.loads(json_str)
        
        # 根据工具类型生成简洁描述
        if tool_name == 'Write':
            file_path = data.get('file_path', 'unknown')
            return f"[Created file: {file_path}]"
        elif tool_name == 'Edit':
            file_path = data.get('file_path', 'unknown')
            return f"[Edited file: {file_path}]"
        elif tool_name == 'Read':
            file_path = data.get('file_path', 'unknown')
            return f"[Read file: {file_path}]"
        elif tool_name == 'Bash':
            command = data.get('command', 'unknown')
            if len(command) > 50:
                command = command[:47] + "..."
            return f"[Executed: {command}]"
        elif tool_name == 'Grep':
            pattern = data.get('pattern', 'unknown')
            return f"[Searched for: {pattern}]"
        else:
            return f"[Used tool: {tool_name}]"
    except:
        # JSON解析失败，返回简单描述
        return f"[Used tool: {tool_name}]"


def clean_direct_json(match) -> str:
    """清理直接的JSON工具调用"""
    tool_name = match.group(1)
    return f"[Used tool: {tool_name}]"


def clean_message_content(msg: Dict[str, Any]) -> Dict[str, Any]:
    """
    清理消息中的JSON污染
    
    Args:
        msg: 消息字典
        
    Returns:
        清理后的消息
    """
    if not msg:
        return msg
    
    # 深拷贝避免修改原始数据
    import copy
    cleaned_msg = copy.deepcopy(msg)
    
    def clean_recursive(obj, depth=0):
        """递归清理所有文本内容"""
        if depth > 10:  # 防止无限递归
            return
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in ['text', 'thinking'] and isinstance(value, str):
                    # 清理文本内容
                    obj[key] = clean_json_pollution(value)
                elif key == 'content':
                    if isinstance(value, str):
                        obj[key] = clean_json_pollution(value)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                # 处理content数组中的项
                                if item.get('type') == 'text' and 'text' in item:
                                    item['text'] = clean_json_pollution(item['text'])
                                elif item.get('type') == 'tool_use':
                                    # 将工具使用转换为文本
                                    tool_name = item.get('name', 'unknown')
                                    item['type'] = 'text'
                                    item['text'] = f"[Used tool: {tool_name}]"
                                    # 移除input字段
                                    item.pop('input', None)
                                    item.pop('name', None)
                                elif item.get('type') == 'tool_result':
                                    # 简化工具结果
                                    item['type'] = 'text'
                                    item['text'] = '[Tool completed]'
                                    item.pop('content', None)
                                else:
                                    clean_recursive(item, depth + 1)
                            elif isinstance(item, str):
                                # 字符串内容也要清理
                                value[value.index(item)] = clean_json_pollution(item)
                    else:
                        clean_recursive(value, depth + 1)
                elif isinstance(value, (dict, list)):
                    clean_recursive(value, depth + 1)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, str):
                    obj[i] = clean_json_pollution(item)
                else:
                    clean_recursive(item, depth + 1)
    
    clean_recursive(cleaned_msg)
    return cleaned_msg


def clean_all_messages(messages: list) -> list:
    """
    清理所有消息中的JSON污染
    
    Args:
        messages: 消息列表
        
    Returns:
        清理后的消息列表
    """
    cleaned_messages = []
    
    for msg in messages:
        cleaned = clean_message_content(msg)
        cleaned_messages.append(cleaned)
    
    return cleaned_messages


if __name__ == "__main__":
    # 测试清理器
    test_cases = [
        '[Tool: Write] {"file_path": "/test.py", "content": "print(\'hello\')"}',
        '[Tool: Bash] {"command": "git status --short"}',
        '{"tool": "Edit", "file_path": "main.py"}',
        'Normal text with [Tool: Read] {"file_path": "readme.md"} in middle',
    ]
    
    print("历史污染清理测试：")
    print("=" * 60)
    
    for test in test_cases:
        cleaned = clean_json_pollution(test)
        print(f"原始: {test}")
        print(f"清理: {cleaned}")
        print("-" * 40)
    
    print("\n✅ 清理器可以去除JSON污染，恢复干净的历史")