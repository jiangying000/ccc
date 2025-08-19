#!/usr/bin/env python3
"""Test token calculation fix - excluding tool content"""

import json
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, '/home/jy/gitr/jiangying000/ccdrc')

from ccdrc.extractor import ClaudeContextExtractor

def create_test_session():
    """Create a test session with tool usage"""
    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": "Read the file test.py"}]
        },
        {
            "role": "assistant", 
            "content": [
                {"type": "text", "text": "I'll read the test.py file for you."},
                {"type": "tool_use", "name": "read_file", "input": {"path": "test.py"}},
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "content": "def test():\n" + "    # " + "x" * 10000 + "\n    pass"}
            ]
        },
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "The file contains a test function."}]
        }
    ]
    
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        for msg in messages:
            f.write(json.dumps(msg) + '\n')
        return Path(f.name)

def main():
    # Create test session
    test_file = create_test_session()
    
    try:
        extractor = ClaudeContextExtractor()
        
        # Get session info (should use new token calculation)
        info = extractor.get_session_info(test_file)
        
        print(f"Token count (excluding tool content): {info['tokens']}")
        print(f"Message count: {info['message_count']}")
        
        # Manually calculate expected tokens (rough estimate)
        text_only = [
            "Read the file test.py",  # ~5 tokens
            "I'll read the test.py file for you.",  # ~10 tokens
            "The file contains a test function."  # ~7 tokens
        ]
        expected_tokens = sum(len(t.split()) * 1.3 for t in text_only)  # Rough estimate
        
        print(f"\nExpected tokens (text only): ~{int(expected_tokens)}")
        print(f"Actual tokens calculated: {info['tokens']}")
        
        if info['tokens'] > expected_tokens * 10:
            print("\n❌ ERROR: Token count seems to include tool content!")
            print("   This would explain why some sessions show inflated token counts.")
        else:
            print("\n✅ Token count looks reasonable (tool content excluded)")
            
    finally:
        test_file.unlink()

if __name__ == "__main__":
    main()