#!/usr/bin/env python3
"""
Interactive UI with pagination for CCDRC
"""

import sys
import os
import time
from typing import List, Dict, Optional
from pathlib import Path

try:
    import termios
    import tty
    TERMIOS_AVAILABLE = True
except ImportError:
    TERMIOS_AVAILABLE = False

class InteractiveSessionSelector:
    """交互式会话选择器，支持分页"""
    
    def __init__(self, sessions: List[Dict], page_size: int = 3, extractor=None):
        self.sessions = sessions
        self.page_size = page_size  # 每页显示3条
        self.current_page = 0
        self.total_pages = (len(sessions) + page_size - 1) // page_size
        self.extractor = extractor  # 用于延迟加载
        
    def display_page(self):
        """显示当前页"""
        # 清屏并移动光标到左上角
        print("\033[2J\033[H", end='', file=sys.stderr)
        
        # 标题
        print("🚀 CCDRC - Claude Code会话压缩和恢复工具", file=sys.stderr)
        print(f"📄 第 {self.current_page + 1}/{self.total_pages} 页", file=sys.stderr)
        print("─" * 60, file=sys.stderr)
        
        # 计算当前页的会话范围
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.sessions))
        
        # 加载当前页的会话（如果需要）
        for i in range(start_idx, end_idx):
            session = self.sessions[i]
            
            # 如果还没有加载完整信息，现在加载
            if session.get('needs_full_load') and self.extractor:
                try:
                    full_info = self.extractor.get_session_info(session['path'])
                    full_info['path'] = session['path']
                    self.sessions[i] = full_info
                except:
                    pass  # 加载失败就用原来的基本信息
        
        # 显示当前页的会话
        for i in range(start_idx, end_idx):
            session = self.sessions[i]
            local_idx = i - start_idx  # 本页内的索引 (0-2)
            
            # 使用1-3的索引，更符合日常习惯
            display_idx = local_idx + 1  # 显示为1-3而非0-2
            print(f"\n[{display_idx}] ", end='', file=sys.stderr)
            self._display_session(session)
        
        # 显示帮助信息（增加空白）
        print("\n" + "─" * 60, file=sys.stderr)
        help_items = []
        help_items.append("1-3:选择会话")
        if self.current_page < self.total_pages - 1:
            help_items.append("n:下一页")
        if self.current_page > 0:
            help_items.append("b:上一页")
        help_items.append("j<数字>:跳页(如j20)")
        help_items.append("q:退出")
        
        print(" | ".join(help_items) + " 👆直接按键", file=sys.stderr)
        
    def _display_session(self, session: Dict):
        """显示单个会话信息（最美观版）"""
        from datetime import datetime
        
        # 时间信息（精确到秒，iOS Termius 兼容）
        mtime = datetime.fromtimestamp(session['mtime'])
        now = datetime.now()
        total_seconds = int((now - mtime).total_seconds())
        if total_seconds < 0:
            total_seconds = 0

        if total_seconds < 60:
            time_str = f"{total_seconds}秒前"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            time_str = f"{minutes}分{seconds}秒前"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            time_str = f"{hours}小时{minutes}分前" if minutes > 0 else f"{hours}小时前"
        else:
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            time_str = f"{days}天{hours}小时前" if hours > 0 else f"{days}天前"
        
        # iOS Termius兼容：使用全角括号避免半角"("被遮挡；emoji 后两个空格更稳
        print(f"⏰  {mtime.strftime('%m-%d %H:%M')}  （{time_str}）", file=sys.stderr)
        
        # 第二行：核心数据（emoji后双空格，不用ANSI）
        tokens = session['tokens']
        if tokens >= 1000000:
            tokens_str = f"≈{tokens/1000000:.1f}M"
        elif tokens >= 1000:
            tokens_str = f"≈{tokens/1000:.1f}k"
        else:
            tokens_str = f"≈{tokens}"
            
        # 统计信息（emoji后双空格，避免iOS Termius首位数字遮挡）
        size = session['size']
        if size < 1024 * 1024:
            size_str = f"{size//1024}KB"
        else:
            size_str = f"{size/1024/1024:.1f}MB"
            
        # 使用中文顿号替代pipe，iOS Termius对pipe渲染有问题
        # Use an ideographic space (U+3000) after the emoji to avoid iOS Termius overlap with first digit
        print(f"  📊　{session['message_count']}条消息、{tokens_str} tokens(估)、{size_str}", file=sys.stderr)
        
        # 主题或分类（去除缩进，iOS Termius对缩进+emoji渲染有问题）
        if session.get('summaries'):
            summary = session['summaries'][0]
            if len(summary) > 70:
                summary = summary[:67] + "..."
            print(f"📌 {summary}", file=sys.stderr)
        elif session.get('topics'):
            topics_str = ' / '.join(session['topics'][:2])
            print(f"📚 {topics_str}", file=sys.stderr)
        
        # 获取对话内容
        meaningful_msgs = session.get('meaningful_messages', [])
        last_msgs = session.get('last_messages', [])
        
        # 显示关键对话
        if meaningful_msgs or last_msgs:
            print("💬 对话片段:", file=sys.stderr)
            displayed = 0
            
            # 显示有代表性的对话
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
            
            # 如果有最近的不同对话
            if last_msgs and last_msgs != meaningful_msgs and displayed < 3:
                print("🔚 最近:", file=sys.stderr)
                for msg in last_msgs[:1]:
                    if '[Tool' not in msg and '[Thinking]' not in msg:
                        if msg.startswith('👤'):
                            content = msg[2:].strip()[:50]
                            print(f"   👤 {content}...", file=sys.stderr)
                        elif msg.startswith('🤖'):
                            content = msg[2:].strip()[:50]
                            print(f"   🤖 {content}...", file=sys.stderr)
        
        print("", file=sys.stderr)  # 会话之间增加空行
    
    def get_single_char(self):
        """获取单个字符输入（无需回车）"""
        import termios, tty
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            # 设置为raw模式，立即读取单个字符
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
            
            # 处理特殊键
            if ch == '\x03':  # Ctrl+C
                raise KeyboardInterrupt
            
            return ch.lower() if ch else ''
        finally:
            # 恢复终端设置
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            
            # 清除当前行并重新显示提示（避免字符残留）
            sys.stderr.write('\r\033[K')
            sys.stderr.flush()
    
    def run(self) -> Optional[Dict]:
        """运行交互式选择器，返回选中的会话"""
        while True:
            self.display_page()
            
            # 获取用户输入
            ch = self.get_single_char()
            
            # ESC或q退出
            if ch in ['\x1b', 'q', 'Q']:
                print("\n👋 已退出", file=sys.stderr)
                return None
            
            # Ctrl+C退出（检查ch非空）
            if ch and ord(ch) == 3:
                print("\n👋 已退出", file=sys.stderr)
                return None
            
            # 数字选择（接受1-3的输入，映射到0-2的索引）
            if ch.isdigit():
                display_idx = int(ch)
                if 1 <= display_idx <= self.page_size:  # 接受1-3
                    idx = display_idx - 1  # 转换为0-2的索引
                    actual_idx = self.current_page * self.page_size + idx
                    if actual_idx < len(self.sessions):
                        return self.sessions[actual_idx]
            
            # n - 下一页
            if ch in ['n', 'N'] and self.current_page < self.total_pages - 1:
                self.current_page += 1
            
            # b - 上一页 (back)
            if ch in ['b', 'B'] and self.current_page > 0:
                self.current_page -= 1
            
            # g - 跳转到指定页面 (旧方式，保留兼容)
            if ch in ['g', 'G']:
                # 显示输入提示
                print("\n📋 输入页码 (1-{}):".format(self.total_pages), end=' ', file=sys.stderr)
                sys.stderr.flush()
                
                try:
                    # 读取多位数字输入
                    page_input = ""
                    while True:
                        if TERMIOS_AVAILABLE:
                            # 使用raw模式读取
                            fd = sys.stdin.fileno()
                            old_settings = termios.tcgetattr(fd)
                            try:
                                tty.setraw(sys.stdin.fileno())
                                input_ch = sys.stdin.read(1)
                            finally:
                                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                            
                            # 回车结束输入
                            if ord(input_ch) == 13:  # Enter
                                break
                            # ESC取消
                            elif ord(input_ch) == 27:  # ESC
                                page_input = ""
                                break
                            # 退格删除
                            elif ord(input_ch) == 127 or ord(input_ch) == 8:  # Backspace
                                if page_input:
                                    page_input = page_input[:-1]
                                    # 清除显示的字符
                                    sys.stderr.write('\b \b')
                                    sys.stderr.flush()
                            # 数字输入
                            elif input_ch.isdigit():
                                page_input += input_ch
                                sys.stderr.write(input_ch)
                                sys.stderr.flush()
                        else:
                            # 回退到普通input
                            page_input = input()
                            break
                    
                    if page_input:
                        page_num = int(page_input)
                        # 页码从1开始，转换为0索引
                        if 1 <= page_num <= self.total_pages:
                            self.current_page = page_num - 1
                        else:
                            print(f"\n⚠  页码超出范围 (1-{self.total_pages})", file=sys.stderr)
                            time.sleep(1)
                except (ValueError, KeyboardInterrupt):
                    pass  # 取消输入
            
            # j - 开始页码跳转输入 (v2.0新功能: j20跳到第20页)
            if ch in ['j', 'J']:
                # 读取后续数字
                page_input = ""
                print("\n➜ j", end='', file=sys.stderr)
                sys.stderr.flush()
                
                while True:
                    if TERMIOS_AVAILABLE:
                        fd = sys.stdin.fileno()
                        old_settings = termios.tcgetattr(fd)
                        try:
                            tty.setraw(sys.stdin.fileno())
                            next_ch = sys.stdin.read(1)
                        finally:
                            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                        
                        # 数字继续输入
                        if next_ch.isdigit():
                            page_input += next_ch
                            sys.stderr.write(next_ch)
                            sys.stderr.flush()
                        # 回车或空格结束输入
                        elif ord(next_ch) in [13, 32]:  # Enter or Space
                            break
                        # ESC取消
                        elif ord(next_ch) == 27:  # ESC
                            page_input = ""
                            break
                        # 退格删除
                        elif ord(next_ch) in [127, 8]:  # Backspace
                            if page_input:
                                page_input = page_input[:-1]
                                sys.stderr.write('\b \b')
                                sys.stderr.flush()
                        # 非数字字符结束输入
                        else:
                            break
                    else:
                        # 非终端环境
                        page_input = input("输入页码: ").strip()
                        break
                
                # 处理输入的页码
                if page_input:
                    try:
                        page_num = int(page_input)
                        if 1 <= page_num <= self.total_pages:
                            self.current_page = page_num - 1
                        else:
                            print(f"\n⚠  页码超出范围 (1-{self.total_pages})", file=sys.stderr)
                            time.sleep(1)
                    except ValueError:
                        pass  # 忽略无效输入
            
            # 移除搜索功能