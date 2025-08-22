#!/usr/bin/env python3
"""
工具调用净化器 - 将工具调用转换为安全的文本表示
避免JSON格式污染上下文，防止大模型模仿输出
"""

def sanitize_tool_call(tool_name: str, tool_input: dict) -> str:
    """
    将工具调用转换为自然语言描述
    避免JSON格式，防止上下文污染
    
    Args:
        tool_name: 工具名称
        tool_input: 工具参数字典
        
    Returns:
        自然语言描述的工具调用
    """
    
    # 不同工具的简化表示方案
    if tool_name == 'Write':
        file_path = tool_input.get('file_path', 'unknown')
        # 只显示文件名，不显示内容（内容通常很长）
        return f"[Created file: {file_path}]"
    
    elif tool_name == 'Edit':
        file_path = tool_input.get('file_path', 'unknown')
        # 不显示具体的修改内容，只显示动作
        return f"[Edited file: {file_path}]"
    
    elif tool_name == 'MultiEdit':
        file_path = tool_input.get('file_path', 'unknown')
        edits = tool_input.get('edits', [])
        return f"[Made {len(edits)} edits to: {file_path}]"
    
    elif tool_name == 'Read':
        file_path = tool_input.get('file_path', 'unknown')
        offset = tool_input.get('offset')
        limit = tool_input.get('limit')
        if offset or limit:
            return f"[Read file: {file_path} (lines {offset}-{offset+limit if offset and limit else 'partial'})]"
        return f"[Read file: {file_path}]"
    
    elif tool_name == 'Bash':
        command = tool_input.get('command', 'unknown')
        # 简化命令，避免显示完整命令（可能包含复杂参数）
        if len(command) > 50:
            command = command[:47] + "..."
        return f"[Executed: {command}]"
    
    elif tool_name == 'Grep':
        pattern = tool_input.get('pattern', 'unknown')
        path = tool_input.get('path', '.')
        return f"[Searched for '{pattern}' in {path}]"
    
    elif tool_name == 'Glob':
        pattern = tool_input.get('pattern', 'unknown')
        return f"[Found files matching: {pattern}]"
    
    elif tool_name == 'LS':
        path = tool_input.get('path', '.')
        return f"[Listed directory: {path}]"
    
    elif tool_name == 'WebSearch':
        query = tool_input.get('query', 'unknown')
        return f"[Web search: {query}]"
    
    elif tool_name == 'WebFetch':
        url = tool_input.get('url', 'unknown')
        return f"[Fetched URL: {url}]"
    
    elif tool_name == 'TodoWrite':
        todos = tool_input.get('todos', [])
        return f"[Updated todo list: {len(todos)} items]"
    
    elif tool_name == 'Task':
        description = tool_input.get('description', 'unknown task')
        return f"[Launched agent: {description}]"
    
    elif tool_name == 'NotebookEdit':
        notebook_path = tool_input.get('notebook_path', 'unknown')
        return f"[Edited notebook: {notebook_path}]"
    
    elif tool_name == 'ExitPlanMode':
        return "[Exited plan mode]"
    
    elif tool_name == 'BashOutput':
        bash_id = tool_input.get('bash_id', 'unknown')
        return f"[Checked bash output: {bash_id}]"
    
    elif tool_name == 'KillBash':
        shell_id = tool_input.get('shell_id', 'unknown')
        return f"[Killed bash process: {shell_id}]"
    
    else:
        # 通用处理：只显示工具名，不显示参数
        # 避免任何可能被误解为JSON的格式
        return f"[Used tool: {tool_name}]"


def sanitize_tool_result(result_content: str, max_length: int = 100) -> str:
    """
    简化工具结果，避免过长内容
    
    Args:
        result_content: 工具结果内容
        max_length: 最大长度
        
    Returns:
        简化的结果描述
    """
    if not result_content:
        return "[Tool completed]"
    
    # 移除多余的空白
    result_content = result_content.strip()
    
    # 检测一些特殊情况
    if "error" in result_content.lower():
        return "[Tool error occurred]"
    elif "success" in result_content.lower():
        return "[Tool succeeded]"
    elif len(result_content) > max_length:
        return f"[Tool output: {len(result_content)} chars]"
    else:
        # 短结果可以保留
        return f"[Result: {result_content}]"


if __name__ == "__main__":
    # 测试示例
    test_cases = [
        ("Write", {"file_path": "/path/to/file.py", "content": "long content..."}),
        ("Edit", {"file_path": "/path/to/file.py", "old_string": "old", "new_string": "new"}),
        ("Bash", {"command": "git status --short"}),
        ("Grep", {"pattern": "def.*function", "path": "/src"}),
        ("TodoWrite", {"todos": [{"content": "task1"}, {"content": "task2"}]}),
    ]
    
    print("工具调用净化测试：")
    print("=" * 60)
    
    for tool_name, tool_input in test_cases:
        sanitized = sanitize_tool_call(tool_name, tool_input)
        print(f"{tool_name}: {sanitized}")
    
    print("\n" + "=" * 60)
    print("✅ 所有工具调用都已转换为安全的文本表示")
    print("没有JSON格式，不会污染上下文")