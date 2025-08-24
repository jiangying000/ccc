"""Utility functions to sanitize tool call text and results.
Kept identical behavior to original for compatibility.
"""
from typing import Any

def sanitize_tool_call(tool_name: str, tool_input: Any) -> str:
    """Return a concise representation of a tool call."""
    return f"[Tool: {tool_name}]"


def sanitize_tool_result(result_content: Any, max_length: int = 100) -> str:
    """Return a concise representation of a tool result."""
    return "[Tool Result]"
