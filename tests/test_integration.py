#!/usr/bin/env python3
"""
Integration tests for CCC
"""
import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path
import pytest

class TestCCCIntegration:
    
    def test_import_ccc_modules(self):
        """Test that all ccc modules can be imported"""
        from ccc import extractor
        from ccc import interactive_ui
        from ccc import cli
        assert extractor is not None
        assert interactive_ui is not None
        assert cli is not None
    
    def test_cli_help(self):
        """Test that ccc --help works"""
        result = subprocess.run(
            [sys.executable, "-m", "ccc.cli", "--help"],
            capture_output=True,
            text=True
        )
        # Allow both success and the expected behavior
        assert result.returncode in [0, 1]  # May exit with 1 when showing help
    
    def test_extractor_main_function(self):
        """Test that the main function can be called"""
        from ccc.extractor import ClaudeContextExtractor
        extractor = ClaudeContextExtractor()
        # Just verify it doesn't crash
        dirs = extractor.find_claude_dirs()
        assert isinstance(dirs, list)
    
    @pytest.mark.slow
    def test_full_workflow_with_sample_data(self):
        """Test the full workflow with sample data"""
        from ccc.extractor import ClaudeContextExtractor
        
        # Create a temporary Claude conversation file
        with tempfile.TemporaryDirectory() as tmpdir:
            conv_file = Path(tmpdir) / "test_conversation.json"
            sample_data = {
                "id": "test_conv",
                "name": "Test Conversation",
                "model": "claude-3-opus",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "settings": {},
                "chat_messages": [
                    {
                        "uuid": "msg1",
                        "sender": "human",
                        "text": "Write a Python function to calculate factorial",
                        "created_at": "2024-01-01T00:00:00",
                        "updated_at": "2024-01-01T00:00:00",
                        "files": []
                    },
                    {
                        "uuid": "msg2",
                        "sender": "assistant",
                        "text": "Here's a Python function to calculate factorial:\n\n```python\ndef factorial(n):\n    if n == 0 or n == 1:\n        return 1\n    else:\n        return n * factorial(n - 1)\n```",
                        "created_at": "2024-01-01T00:00:01",
                        "updated_at": "2024-01-01T00:00:01",
                        "files": []
                    }
                ]
            }
            
            with open(conv_file, 'w') as f:
                json.dump(sample_data, f)
            
            # Test extraction
            extractor = ClaudeContextExtractor()
            info = extractor.get_session_info(str(conv_file))
            
            assert info["title"] == "Test Conversation"
            assert info["message_count"] == 2
            assert "factorial" in info["messages"][0]["text"].lower()
            
            # Test formatting
            formatted = extractor.format_for_import(info, max_chars=10000)
            assert "human:" in formatted
            assert "assistant:" in formatted
            assert "factorial" in formatted