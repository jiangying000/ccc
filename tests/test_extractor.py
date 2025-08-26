#!/usr/bin/env python3
"""
Tests for the extractor module
"""
import os
import json
import tempfile
import pytest
from pathlib import Path
from ccc.extractor import ClaudeContextExtractor

class TestClaudeContextExtractor:
    
    @pytest.fixture
    def sample_claude_file(self):
        """Create a sample Claude conversation file for testing"""
        content = {
            "id": "test_id",
            "name": "Test Conversation",
            "model": "claude-3-opus",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "settings": {},
            "chat_messages": [
                {
                    "uuid": "msg1",
                    "sender": "human",
                    "text": "Hello, Claude!",
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00",
                    "files": []
                },
                {
                    "uuid": "msg2",
                    "sender": "assistant",
                    "text": "Hello! How can I help you today?",
                    "created_at": "2024-01-01T00:00:01",
                    "updated_at": "2024-01-01T00:00:01",
                    "files": []
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(content, f)
            return f.name
    
    def test_initialization(self):
        """Test extractor initialization"""
        extractor = ClaudeContextExtractor()
        assert extractor is not None
        assert extractor.base_dirs is not None
    
    def test_find_claude_dirs(self):
        """Test finding Claude directories"""
        extractor = ClaudeContextExtractor()
        dirs = extractor.find_claude_dirs()
        assert isinstance(dirs, list)
    
    def test_parse_claude_file(self, sample_claude_file):
        """Test parsing a Claude conversation file"""
        extractor = ClaudeContextExtractor()
        try:
            info = extractor.get_session_info(sample_claude_file)
            assert info["title"] == "Test Conversation"
            assert info["message_count"] == 2
            assert len(info["messages"]) == 2
        finally:
            os.unlink(sample_claude_file)
    
    def test_compress_message(self):
        """Test message compression"""
        extractor = ClaudeContextExtractor()
        long_message = "This is a very long message " * 100
        compressed = extractor.compress_message(long_message, 100)
        assert len(compressed) <= 100
    
    def test_format_for_import(self, sample_claude_file):
        """Test formatting conversation for import"""
        extractor = ClaudeContextExtractor()
        try:
            info = extractor.get_session_info(sample_claude_file)
            formatted = extractor.format_for_import(info, max_chars=10000)
            assert "human" in formatted
            assert "assistant" in formatted
            assert "Hello, Claude!" in formatted
        finally:
            os.unlink(sample_claude_file)