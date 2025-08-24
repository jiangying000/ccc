#!/usr/bin/env python3
"""
Interactive UI with pagination for CCC

Improved for clarity and ease-of-use:
- ANSI colors when running in a real TTY; plain text otherwise
- Safe clear screen only when TTY
- Cleaner header and keyboard hints
- Jump to page via 'j' -> prompt page number
- Fallback to line input when raw mode unavailable
"""

import sys
from typing import List, Dict, Optional

try:
    import termios  # noqa: F401
    import tty  # noqa: F401
    TERMIOS_AVAILABLE = True
except ImportError:
    TERMIOS_AVAILABLE = False


def _supports_color() -> bool:
    return sys.stderr.isatty()


def _should_clear() -> bool:
    return sys.stderr.isatty()


class _Style:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"


def _c(text: str, *styles: str) -> str:
    if not _supports_color():
        return text
    return "".join(styles) + text + _Style.RESET

class InteractiveSessionSelector:
    """Interactive session selector with pagination"""

    def __init__(self, sessions: List[Dict], page_size: int = 3, extractor=None):
        self.sessions = sessions
        self.page_size = page_size
        self.current_page = 0
        self.total_pages = (len(sessions) + page_size - 1) // page_size
        self.extractor = extractor

    def display_page(self):
        if _should_clear():
            print("\033[2J\033[H", end='', file=sys.stderr)
        print(_c("🚀 CCC - Claude Code 会话压缩与恢复", _Style.BOLD, _Style.CYAN), file=sys.stderr)
        print(_c(f"📄 第 {self.current_page + 1}/{self.total_pages} 页", _Style.DIM), file=sys.stderr)
        print("─" * 60, file=sys.stderr)

        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.sessions))

        for i in range(start_idx, end_idx):
            session = self.sessions[i]
            if session.get('needs_full_load') and self.extractor:
                try:
                    full_info = self.extractor.get_session_info(session['path'])
                    full_info['path'] = session['path']
                    self.sessions[i] = full_info
                except Exception:
                    pass

        for i in range(start_idx, end_idx):
            session = self.sessions[i]
            local_idx = i - start_idx
            display_idx = local_idx + 1
            idx_render = _c(f"[{display_idx}] ", _Style.MAGENTA, _Style.BOLD)
            print(f"\n{idx_render}", end='', file=sys.stderr)
            self._display_session(session)

        print("\n" + "─" * 60, file=sys.stderr)
        help_items = []
        help_items.append(f"1-{end_idx-start_idx}:选择会话")
        if self.current_page < self.total_pages - 1:
            help_items.append("n:下一页")
        if self.current_page > 0:
            help_items.append("b:上一页")
        help_items.append("j:跳页")
        help_items.append("q:退出")
        print(_c(" | ".join(help_items) + "  👆直接按键", _Style.DIM), file=sys.stderr)

    def _display_session(self, session: Dict):
        from datetime import datetime
        mtime = datetime.fromtimestamp(session['mtime'])
        print(_c("⏰  ", _Style.YELLOW) + f"{mtime.strftime('%m-%d %H:%M')}", file=sys.stderr)
        tokens = session['tokens']
        if tokens >= 1000000:
            tokens_str = f"≈{tokens/1000000:.1f}M"
        elif tokens >= 1000:
            tokens_str = f"≈{tokens/1000:.1f}k"
        else:
            tokens_str = f"≈{tokens}"
        size = session['size']
        if size < 1024 * 1024:
            size_str = f"{size//1024}KB"
        else:
            size_str = f"{size/1024/1024:.1f}MB"
        print(f"  📊　{session['message_count']}条消息、{tokens_str} tokens(估)、{size_str}", file=sys.stderr)
        if session.get('summaries'):
            summary = session['summaries'][0]
            if len(summary) > 70:
                summary = summary[:67] + "..."
            print(_c("📌 ", _Style.BLUE) + summary, file=sys.stderr)
        elif session.get('topics'):
            topics_str = ' / '.join(session['topics'][:2])
            print(_c("📚 ", _Style.BLUE) + topics_str, file=sys.stderr)
        meaningful_msgs = session.get('meaningful_messages', [])
        last_msgs = session.get('last_messages', [])
        if meaningful_msgs or last_msgs:
            print(_c("💬 对话片段:", _Style.BOLD), file=sys.stderr)
            displayed = 0
            for msg in meaningful_msgs[:2]:
                if displayed >= 2:
                    break
                if '[Tool' not in msg and '[Thinking]' not in msg:
                    if msg.startswith('👤'):
                        content = msg[2:].strip()[:50]
                        print(f"   👤 {content}...", file=sys.stderr)
                        displayed += 1
                    elif msg.startswith('🤖'):
                        content = msg[2:].strip()[:50]
                        print(f"   🤖 {content}...", file=sys.stderr)
                        displayed += 1
            if last_msgs and last_msgs != meaningful_msgs and displayed < 3:
                print(_c("🔚 最近:", _Style.DIM), file=sys.stderr)
                for msg in last_msgs[:1]:
                    if '[Tool' not in msg and '[Thinking]' not in msg:
                        if msg.startswith('👤'):
                            content = msg[2:].strip()[:50]
                            print(f"   👤 {content}...", file=sys.stderr)
                        elif msg.startswith('🤖'):
                            content = msg[2:].strip()[:50]
                            print(f"   🤖 {content}...", file=sys.stderr)
        print("", file=sys.stderr)

    def get_single_char(self):
        """Read a single char if possible; fallback to line mode.

        Returns a lower-cased first character, or empty string.
        """
        if not TERMIOS_AVAILABLE or not sys.stdin.isatty():
            line = input(_c("\n👉 选择: ", _Style.MAGENTA))
            return (line.strip().lower()[:1] if line else '')
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == '\x03':
                raise KeyboardInterrupt
            return ch.lower() if ch else ''
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            sys.stderr.write('\r\033[K')
            sys.stderr.flush()

    def run(self) -> Optional[Dict]:
        while True:
            self.display_page()
            ch = self.get_single_char()
            if ch in ['\x1b', 'q', 'Q']:
                print("\n👋 已退出", file=sys.stderr)
                return None
            if ch and ord(ch) == 3:
                print("\n👋 已退出", file=sys.stderr)
                return None
            if ch.isdigit():
                display_idx = int(ch)
                if 1 <= display_idx <= self.page_size:
                    idx = display_idx - 1
                    actual_idx = self.current_page * self.page_size + idx
                    if actual_idx < len(self.sessions):
                        return self.sessions[actual_idx]
            if ch in ['j', 'J']:
                try:
                    page_input = input(_c("跳转到第几页: ", _Style.MAGENTA)).strip()
                    if page_input.isdigit():
                        page = int(page_input)
                        if 1 <= page <= self.total_pages:
                            self.current_page = page - 1
                except EOFError:
                    pass
            if ch in ['n', 'N'] and self.current_page < self.total_pages - 1:
                self.current_page += 1
            if ch in ['b', 'B'] and self.current_page > 0:
                self.current_page -= 1
