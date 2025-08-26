#!/usr/bin/env python3
"""
Tests for the interactive UI module
"""
import pytest
from unittest.mock import MagicMock, patch
from ccc.interactive_ui import InteractiveSessionSelector, _Style, _c

class TestInteractiveUI:
    
    @pytest.fixture
    def sample_sessions(self):
        """Create sample session data for testing"""
        return [
            {
                "path": "/path/to/session1.json",
                "title": "Test Session 1",
                "timestamp": "08-25 10:00",
                "message_count": 10,
                "compressed_size": 1024,
                "tags": ["test", "python"],
                "messages": [
                    {"sender": "human", "text": "Hello"},
                    {"sender": "assistant", "text": "Hi there!"}
                ]
            },
            {
                "path": "/path/to/session2.json",
                "title": "Test Session 2",
                "timestamp": "08-25 11:00",
                "message_count": 20,
                "compressed_size": 2048,
                "tags": ["coding"],
                "messages": [
                    {"sender": "human", "text": "Help me code"},
                    {"sender": "assistant", "text": "Sure!"}
                ]
            }
        ]
    
    def test_initialization(self, sample_sessions):
        """Test selector initialization"""
        selector = InteractiveSessionSelector(sample_sessions, page_size=3)
        assert selector.sessions == sample_sessions
        assert selector.page_size == 3
        assert selector.current_page == 0
        assert selector.total_pages == 1
    
    def test_pagination(self):
        """Test pagination with multiple sessions"""
        sessions = [{"title": f"Session {i}", "path": f"/path/{i}"} for i in range(10)]
        selector = InteractiveSessionSelector(sessions, page_size=3)
        assert selector.total_pages == 4
        assert selector.get_page_sessions(0) == sessions[0:3]
        assert selector.get_page_sessions(1) == sessions[3:6]
        assert selector.get_page_sessions(3) == sessions[9:10]
    
    def test_format_message_preview(self, sample_sessions):
        """Test message preview formatting"""
        selector = InteractiveSessionSelector(sample_sessions)
        preview = selector.format_message_preview(sample_sessions[0])
        assert "Hello" in preview
        assert "Hi there!" in preview
    
    @patch('ccc.interactive_ui.InteractiveSessionSelector.get_single_char')
    @patch('ccc.interactive_ui.InteractiveSessionSelector.display_page')
    def test_quit_command(self, mock_display, mock_get_char, sample_sessions):
        """Test quit command"""
        selector = InteractiveSessionSelector(sample_sessions)
        mock_get_char.return_value = 'q'
        
        result = selector.run()
        assert result is None
        mock_display.assert_called()
    
    @patch('ccc.interactive_ui.InteractiveSessionSelector.get_single_char')
    @patch('ccc.interactive_ui.InteractiveSessionSelector.display_page')
    def test_select_session(self, mock_display, mock_get_char, sample_sessions):
        """Test selecting a session"""
        selector = InteractiveSessionSelector(sample_sessions)
        mock_get_char.return_value = '1'
        
        result = selector.run()
        assert result == sample_sessions[0]
        mock_display.assert_called()
    
    def test_color_functions(self):
        """Test color formatting functions"""
        text = "Test"
        colored = _c(text, _Style.GREEN)
        assert _Style.GREEN in colored
        assert text in colored
        assert _Style.RESET in colored