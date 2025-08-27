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
import os
import shutil
import time
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


def _weekday_cn(dt) -> str:
    """将weekday转换为中文(周一~周日)。"""
    names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    try:
        return names[dt.weekday()]
    except Exception:
        return ""


def _relative_time_text(now, dt) -> str:
    """生成简洁的相对时间文本：刚刚/5分钟前/3小时前/昨天/3天前/2周前。"""
    delta = now - dt
    days = delta.days
    seconds = delta.seconds
    if days <= 0:
        if seconds < 60:
            return "刚刚"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}分钟前"
        hours = minutes // 60
        return f"{hours}小时前"
    if days == 1:
        return "昨天"
    if days < 7:
        return f"{days}天前"
    weeks = days // 7
    return f"{weeks}周前"


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
    """Interactive session selector with pagination

    realtime: when True, recompute session info on each page display
              without caching results back to self.sessions. This ensures
              up-to-date info at the cost of latency proportional to
              page_size.
    """

    def __init__(self, sessions: List[Dict], page_size: int = 3, extractor=None, realtime: bool = False, concurrency: Optional[int] = None, use_processes: bool = False):
        self.sessions = sessions
        self.page_size = page_size
        self.current_page = 0
        self.total_pages = (len(sessions) + page_size - 1) // page_size
        self.extractor = extractor
        self.realtime = realtime
        # 并发设置（默认自适应：每页条目数；可传入覆盖）
        self.concurrency: Optional[int] = None if concurrency is None else max(1, int(concurrency))
        self.use_processes = bool(use_processes)
        self._last_page_elapsed_ms: Optional[int] = None
        self._last_page_concurrency: Optional[int] = None
        self.show_help = False  # 是否显示帮助面板

    def _recompute_pagination(self) -> None:
        self.total_pages = (len(self.sessions) + self.page_size - 1) // self.page_size
        if self.current_page >= self.total_pages:
            self.current_page = max(0, self.total_pages - 1)

    def display_page(self):
        if _should_clear():
            print("\033[2J\033[H", end='', file=sys.stderr)
        width = shutil.get_terminal_size((80, 24)).columns if sys.stderr.isatty() else 80
        sep_len = min(60, width)
        print(_c("🚀 CCC - Claude 会话管理器", _Style.BOLD, _Style.CYAN), file=sys.stderr)
        print("─" * sep_len, file=sys.stderr)

        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.sessions))

        # 计算当前页的会话信息（实时）
        page_sessions: List[Dict] = []
        t0 = time.perf_counter()
        if self.extractor and end_idx > start_idx:
            # Always compute in realtime
            indices = list(range(start_idx, end_idx))
            base_items = [self.sessions[i] for i in indices]
            # 自适应并发：默认使用线程，并发数=当前页条目数
            effective_conc = self.concurrency if self.concurrency is not None else len(base_items)
            effective_conc = max(1, effective_conc)
            try:
                if self.use_processes and effective_conc > 1:
                    # 使用进程池并发计算
                    from concurrent.futures import ProcessPoolExecutor
                    from .extractor import process_session_worker
                    args = [(k, item['path']) for k, item in enumerate(base_items)]
                    results: Dict[int, Dict] = {}
                    with ProcessPoolExecutor(max_workers=effective_conc) as ex:
                        for idx, info in ex.map(process_session_worker, args):
                            info['path'] = base_items[idx]['path']
                            results[idx] = info
                    page_sessions = [results[i] if i in results else base_items[i] for i in range(len(base_items))]
                elif effective_conc > 1:
                    # 使用线程池并发计算（适合IO）
                    from concurrent.futures import ThreadPoolExecutor, as_completed
                    def _compute(item: Dict) -> Dict:
                        try:
                            info = self.extractor.get_session_info(item['path'])
                            info['path'] = item['path']
                            return info
                        except Exception:
                            return item
                    page_sessions = [None] * len(base_items)  # type: ignore[list-item]
                    with ThreadPoolExecutor(max_workers=effective_conc) as ex:
                        future_to_idx = {ex.submit(_compute, it): i for i, it in enumerate(base_items)}
                        for fut in as_completed(future_to_idx):
                            i = future_to_idx[fut]
                            try:
                                page_sessions[i] = fut.result()
                            except Exception:
                                page_sessions[i] = base_items[i]
                    page_sessions = [ps if ps is not None else base_items[i] for i, ps in enumerate(page_sessions)]
                else:
                    # 串行计算
                    for item in base_items:
                        try:
                            info = self.extractor.get_session_info(item['path'])
                            info['path'] = item['path']
                            page_sessions.append(info)
                        except Exception:
                            page_sessions.append(item)
            except Exception:
                # 发生并发错误时回退到串行
                for item in base_items:
                    try:
                        info = self.extractor.get_session_info(item['path'])
                        info['path'] = item['path']
                        page_sessions.append(info)
                    except Exception:
                        page_sessions.append(item)
        else:
            page_sessions = [self.sessions[i] for i in range(start_idx, end_idx)]
        t1 = time.perf_counter()
        self._last_page_elapsed_ms = int((t1 - t0) * 1000)
        # 记录实际并发度
        try:
            self._last_page_concurrency = effective_conc if (self.extractor and end_idx > start_idx) else 1
        except Exception:
            self._last_page_concurrency = None

        for i in range(start_idx, end_idx):
            session = page_sessions[i - start_idx]
            local_idx = i - start_idx
            display_idx = local_idx + 1
            idx_render = _c(f"[{display_idx}] ", _Style.MAGENTA, _Style.BOLD)
            print(f"\n{idx_render}", end='', file=sys.stderr)
            self._display_session(session)

        print("\n" + "─" * sep_len, file=sys.stderr)

        # 帮助面板（可切换），在标题下方显示，避免底部拥挤
        if self.show_help:
            help_lines = [
                _c("帮助 • 快捷键说明", _Style.BOLD),
                "  [1~N] 选择当前页的第 N 个会话",
                f"  [n] 下一页    [Shift+n]/[b] 上一页",
                "  [g] 第一页    [G] 最后一页",
                f"  [j] 跳转至指定页  [s] 每页数量(当前: {self.page_size})",
                "  [h] 关闭帮助  [q] 退出",
                "  [q] 退出",
            ]
            for line in help_lines:
                print(line, file=sys.stderr)
            print("-" * sep_len, file=sys.stderr)
        
        # 构建底部状态栏（根据宽度自适应）
        def _format_status_line() -> str:
            # 在更宽的屏幕显示更完整的信息，包括每页数量
            if width >= 70:
                extra_perf = ""
                if self._last_page_elapsed_ms is not None:
                    conc = self._last_page_concurrency if self._last_page_concurrency else 1
                    extra_perf = f"  •  并发 {conc}  •  耗时 {self._last_page_elapsed_ms} ms"
                return (
                    f"📄 第 {self.current_page + 1}/{self.total_pages} 页  •  "
                    f"共 {len(self.sessions)} 会话  •  每页 {self.page_size} 条" + extra_perf
                )
            elif width >= 50:
                perf = ""
                if self._last_page_elapsed_ms is not None:
                    conc = self._last_page_concurrency if self._last_page_concurrency else 1
                    perf = f"  •  并发 {conc}  •  {self._last_page_elapsed_ms}ms"
                return (
                    f"📄 第 {self.current_page + 1}/{self.total_pages} 页  •  "
                    f"共 {len(self.sessions)}  •  每页 {self.page_size}" + perf
                )
            else:
                return f"📄 {self.current_page + 1}/{self.total_pages}  •  {len(self.sessions)}会话"
        
        # 构建操作提示 - 更清晰的布局，按宽度自适应
        actions_main: List[str] = []
        actions_extra: List[str] = []
        
        # 说明数字键选择
        num_sessions = end_idx - start_idx
        if width >= 70:
            sel_text = "按 1 选择" if num_sessions == 1 else f"按 1~{num_sessions} 选择"
        elif width >= 50:
            sel_text = "1 选择" if num_sessions == 1 else f"1~{num_sessions} 选择"
        else:
            sel_text = "选择 1" if num_sessions == 1 else f"选择 1~{num_sessions}"
        actions_main.append(sel_text)
        
        # 分页导航
        if self.total_pages > 1:
            has_next = self.current_page < self.total_pages - 1
            has_prev = self.current_page > 0
            # 构造分页提示
            next_str_full = "[n] 下页 ↓"
            prev_str_full = "[Shift+n]/[b] 上页 ↑"
            next_str_mid = "[n]↓"
            prev_str_mid = "[N/b]↑"
            next_str_narrow = "n↓"
            prev_str_narrow = "N/b↑"
            if width >= 70:
                next_hint = next_str_full if has_next else _c(next_str_full, _Style.DIM)
                prev_hint = prev_str_full if has_prev else _c(prev_str_full, _Style.DIM)
                actions_main.append(f"翻页: {next_hint} | {prev_hint}")
                actions_main.append("[g/G] 首/末页")
            elif width >= 50:
                next_hint = next_str_mid if has_next else _c(next_str_mid, _Style.DIM)
                prev_hint = prev_str_mid if has_prev else _c(prev_str_mid, _Style.DIM)
                actions_main.append(f"翻: {next_hint} {prev_hint}")
                actions_main.append("g/G 首/末")
            else:
                next_hint = next_str_narrow if has_next else _c(next_str_narrow, _Style.DIM)
                prev_hint = prev_str_narrow if has_prev else _c(prev_str_narrow, _Style.DIM)
                actions_main.append(f"翻页: {next_hint}  {prev_hint}")
                actions_main.append("首末: g/G")

        if width >= 70:
            actions_extra.extend([
                "[j] 跳转",
                f"[s] 每页 {self.page_size}",
                "[h] 帮助",
                "[q] 退出",
            ])
        elif width >= 50:
            actions_extra.extend([
                "j 跳转",
                f"s 每页{self.page_size}",
                "h 帮助",
                "q 退出",
            ])
        else:
            actions_extra.append(f"其他: j 跳转 | s 每页{self.page_size} | h 帮助 | q 退出")
        
        # 底部状态栏显示 - 两行显示，更清晰
        print("\n" + "═" * sep_len, file=sys.stderr)
        print(_c(_format_status_line(), _Style.BOLD), file=sys.stderr)
        # 根据宽度将 actions 分行输出，避免自动换行导致混乱
        if width >= 70:
            all_actions = actions_main + actions_extra
            print(_c("操作:", _Style.DIM) + " " + "  |  ".join(all_actions), file=sys.stderr)
        elif width >= 50:
            print(_c("操作:", _Style.DIM) + " " + "  |  ".join(actions_main), file=sys.stderr)
            if actions_extra:
                print("       " + "  |  ".join(actions_extra), file=sys.stderr)
        else:
            # 多行清晰模式（不做极限压缩）
            print(_c("操作:", _Style.DIM), file=sys.stderr)
            for a in actions_main:
                print("  " + a, file=sys.stderr)
            for a in actions_extra:
                print("  " + a, file=sys.stderr)

    def _display_session(self, session: Dict):
        from datetime import datetime
        # 在渲染每个会话时独立计算宽度，避免引用外部局部变量
        try:
            width = shutil.get_terminal_size((80, 24)).columns if sys.stderr.isatty() else 80
        except Exception:
            width = 80
        mtime = datetime.fromtimestamp(session['mtime'])
        now = datetime.now()
        abs_time = mtime.strftime('%Y-%m-%d %H:%M')
        weekday = _weekday_cn(mtime)
        rel = _relative_time_text(now, mtime)
        # 时间行也按宽度适配
        if width >= 60:
            parts = [f"{abs_time} ({weekday})", rel]
        else:
            parts = [f"{abs_time}", rel]
        if session.get('duration'):
            parts.append(f"时长 {session['duration']}")
        time_text = "  ·  ".join(parts)
        print(_c("⏰  ", _Style.YELLOW) + time_text, file=sys.stderr)
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
        # 摘要与主题（更清晰、可回忆）
        if session.get('summaries'):
            summary = session['summaries'][0]
            if len(summary) > 80:
                summary = summary[:77] + "..."
            print(_c("📌 摘要: ", _Style.BLUE) + summary, file=sys.stderr)
        elif session.get('topics'):
            topics_str = ' / '.join(session['topics'][:3])
            print(_c("📚 主题: ", _Style.BLUE) + topics_str, file=sys.stderr)
        meaningful_msgs = session.get('meaningful_messages', [])
        last_msgs = session.get('last_messages', [])
        # 更加清晰的预览：展示开头与最近的各两句，帮助快速回忆
        if meaningful_msgs or last_msgs:
            print(_c("💬 预览:", _Style.BOLD), file=sys.stderr)
            head_shown = 0
            for msg in meaningful_msgs:
                if head_shown >= 2:
                    break
                if '[Tool' in msg or '[Thinking]' in msg:
                    continue
                content = msg[2:].strip() if (msg.startswith('👤') or msg.startswith('🤖')) else msg
                content = content[:60] + ("..." if len(content) > 60 else "")
                role = '👤' if msg.startswith('👤') else ('🤖' if msg.startswith('🤖') else '•')
                print(f"   🔸 开头 {head_shown+1}: {role} {content}", file=sys.stderr)
                head_shown += 1
            tail_shown = 0
            if last_msgs and last_msgs != meaningful_msgs:
                for msg in last_msgs:
                    if tail_shown >= 2:
                        break
                    if '[Tool' in msg or '[Thinking]' in msg:
                        continue
                    content = msg[2:].strip() if (msg.startswith('👤') or msg.startswith('🤖')) else msg
                    content = content[:60] + ("..." if len(content) > 60 else "")
                    role = '👤' if msg.startswith('👤') else ('🤖' if msg.startswith('🤖') else '•')
                    print(f"   🔚 最近 {tail_shown+1}: {role} {content}", file=sys.stderr)
                    tail_shown += 1
        print("", file=sys.stderr)

    def get_single_char(self):
        """Read a single char if possible; fallback to line mode.

        Returns the raw character (preserving case), or empty string.
        """
        if not TERMIOS_AVAILABLE or not sys.stdin.isatty():
            line = input(_c("\n👉 选择: ", _Style.MAGENTA))
            return (line.strip()[:1] if line else '')  # 保留原始大小写
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == '\x03':
                raise KeyboardInterrupt
            return ch if ch else ''
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            sys.stderr.write('\r\033[K')
            sys.stderr.flush()

    def run(self) -> Optional[Dict]:
        try:
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
                if ch == 'n' and self.current_page < self.total_pages - 1:
                    self.current_page += 1
                if (ch == 'N' or ch == 'b' or ch == 'B') and self.current_page > 0:
                    self.current_page -= 1
                if ch == 'g':  # 跳到第一页
                    self.current_page = 0
                if ch == 'G' and self.total_pages > 0:  # 跳到最后一页
                    self.current_page = self.total_pages - 1
                if ch in ['s', 'S']:
                    try:
                        prompt = _c(f"设置每页数量(当前 {self.page_size})，请输入数字(1-20): ", _Style.MAGENTA)
                        size_input = input(prompt).strip()
                        if size_input.isdigit():
                            new_size = int(size_input)
                            if 1 <= new_size <= 20:
                                self.page_size = new_size
                                self._recompute_pagination()
                    except EOFError:
                        pass
                if ch in ['h', 'H']:
                    self.show_help = not self.show_help
        except KeyboardInterrupt:
            print("\n👋 已退出", file=sys.stderr)
            return None
