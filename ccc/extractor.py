#!/usr/bin/env python3
"""
Claude Context Smart Extract Tool (package: ccc)

This tool scans local Claude Code session logs, summarizes context, and
optionally resumes or compresses a session for reloading via Claude CLI.
"""

import json
import os
import sys
import re
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Try import tool call sanitizer from current package; fallback to no-op shorteners.
# Use local aliases to avoid type conflicts when swapping implementations.
try:
    from .tool_call_sanitizer import (
        sanitize_tool_call as _sanitize_tool_call,
        sanitize_tool_result as _sanitize_tool_result,
    )
except Exception:
    def _sanitize_tool_call(tool_name: str, tool_input) -> str:
        return f"[Tool: {tool_name}]"

    def _sanitize_tool_result(result_content, max_length: int = 100) -> str:
        return "[Tool Result]"

# Tokenization support (tiktoken optional)
try:
    import tiktoken  # type: ignore
    TIKTOKEN_AVAILABLE = True
except Exception:
    tiktoken = None  # type: ignore[assignment]
    TIKTOKEN_AVAILABLE = False


class ClaudeContextExtractor:
    """Smart context extractor for Claude sessions."""

    def __init__(self, max_tokens: int = 100000, verbose: bool = False):
        self.max_tokens = max_tokens
        self.encoder = None
        self.verbose = verbose
        # Initialize tokenizer if available
        tokenizer = tiktoken if (TIKTOKEN_AVAILABLE and tiktoken is not None) else None  # type: ignore[truthy-function]
        if tokenizer:
            try:
                self.encoder = tokenizer.get_encoding("o200k_base")  # type: ignore[attr-defined]
                self.encoding_name = "o200k_base"
                self.vocab_size = self.encoder.n_vocab
            except Exception:
                try:
                    self.encoder = tokenizer.get_encoding("cl100k_base")  # type: ignore[attr-defined]
                    self.encoding_name = "cl100k_base"
                    self.vocab_size = self.encoder.n_vocab
                except Exception:
                    self.encoding_name = "estimation"
                    self.vocab_size = 0
        else:
            self.encoding_name = "estimation"
            self.vocab_size = 0

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken when possible; otherwise estimate."""
        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception:
                pass
        # Fallback estimation tuned for mixed Chinese/English
        total_chars = len(text)
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        non_chinese_chars = total_chars - chinese_chars
        if chinese_chars > non_chinese_chars:
            estimated = (chinese_chars * 1.8) + (non_chinese_chars / 3.5)
        else:
            estimated = non_chinese_chars / 3.5 + (chinese_chars * 1.8)
        if "```" in text:
            estimated *= 1.2
        if text.count("\n") > len(text) / 50:
            estimated *= 1.1
        estimated = max(total_chars / 10, min(estimated, total_chars / 2))
        return int(estimated)

    def find_claude_sessions(self) -> List[Path]:
        """Find Claude JSONL sessions under ~/.claude/projects, newest first."""
        claude_dir = Path.home() / ".claude" / "projects"
        if not claude_dir.exists():
            return []
        sessions: List[Path] = []
        for project_dir in claude_dir.iterdir():
            if project_dir.is_dir():
                for jsonl_file in project_dir.glob("*.jsonl"):
                    if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jsonl$",
                                jsonl_file.name):
                        if jsonl_file.stat().st_size > 1024:
                            sessions.append(jsonl_file)
        sessions.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return sessions

    def extract_meaningful_messages(self, messages: List[Dict], count: int = 5) -> List[str]:
        """Prefer user and assistant text, skip tool noise and thinking blobs."""
        meaningful: List[str] = []
        user_messages: List[Tuple[str, int]] = []
        assistant_messages: List[Tuple[str, int]] = []

        for msg in messages:
            role = None
            if "message" in msg and isinstance(msg["message"], dict):
                role = msg["message"].get("role")
            elif "type" in msg:
                if msg["type"] == "human":
                    role = "user"
                elif msg["type"] == "assistant":
                    role = "assistant"

            content = self._get_message_content(msg)
            if not content:
                continue
            if content.startswith("[Tool:") or content.startswith("[Tool Result]"):
                continue
            if content.startswith("[Thinking]"):
                continue
            if any(p in content for p in [
                "# 提取的对话上下文", "# 之前的对话上下文",
                "This session is being continued", "_共", "---",
                "[Request interrupted", "No response requested",
            ]):
                continue

            lines = content.split("\n")
            clean_lines: List[str] = []
            for line in lines:
                s = line.strip()
                if s and len(s) > 10 and not s.startswith("#") and not s.startswith("_"):
                    if s.startswith("**") and s.endswith("**"):
                        s = s[2:-2]
                    clean_lines.append(s)
            if clean_lines:
                clean_content = " ".join(clean_lines[:3])[:300]
                if role in ("user", "human"):
                    user_messages.append(("👤 " + clean_content, len(user_messages)))
                elif role == "assistant":
                    assistant_messages.append(("🤖 " + clean_content, len(assistant_messages)))
                else:
                    if any(marker in content for marker in ["用户:", "User:", "Human:"]):
                        user_messages.append(("👤 " + clean_content, len(user_messages)))
                    elif any(marker in content for marker in ["Claude:", "Assistant:", "助手:"]):
                        assistant_messages.append(("🤖 " + clean_content, len(assistant_messages)))

        add_u = 0
        add_a = 0
        while len(meaningful) < count and (add_u < len(user_messages) or add_a < len(assistant_messages)):
            if add_u < len(user_messages):
                meaningful.append(user_messages[add_u][0])
                add_u += 1
            if add_a < len(assistant_messages) and len(meaningful) < count:
                meaningful.append(assistant_messages[add_a][0])
                add_a += 1

        if len(meaningful) < 2:
            skip_patterns = [
                "# 提取的对话上下文", "# 之前的对话上下文",
                "This session is being continued", "_共", "---",
                "[Request interrupted", "No response requested",
                "[Tool Result] File created successfully",
                "[Tool Result] The file",
                "[Tool Result] Todos have been modified",
            ]
            keywords = {
                "bug": 5, "error": 5, "错误": 5, "fix": 4, "修复": 4,
                "implement": 4, "实现": 4, "create": 4, "创建": 4,
                "database": 3, "数据库": 3, "api": 3, "API": 3,
                "function": 3, "函数": 3, "class": 3, "类": 3,
                "test": 3, "测试": 3, "deploy": 3, "部署": 3,
                "webhook": 4, "line": 4, "LINE": 4, "telegram": 4,
                "docker": 3, "kubernetes": 3, "aws": 3, "azure": 3,
                "react": 3, "vue": 3, "python": 3, "javascript": 3,
                "install": 3, "安装": 3, "setup": 3, "配置": 3,
                "optimize": 3, "优化": 3, "performance": 3, "性能": 3,
            }
            scored: List[Tuple[int, str, str]] = []
            for msg in messages:
                content = self._get_message_content(msg)
                if not content:
                    continue
                if any(p in content for p in skip_patterns):
                    continue
                for line in content.split("\n"):
                    s = line.strip()
                    if not s or len(s) < 10 or s.startswith("#") or s.startswith("_") or s.startswith("**") or s == "---":
                        continue
                    if any(marker in s for marker in ["用户:", "Claude:", "助手:", "User:", "Human:", "Assistant:"]):
                        if ":" in s:
                            parts = s.split(":", 1)
                            if len(parts) > 1:
                                s = parts[1].strip()
                    if s.startswith("[Tool:") or s.startswith("[Tool Result]") or s.startswith("[Thinking]"):
                        continue
                    if not s or len(s) < 10:
                        continue
                    score = 0
                    lower_s = s.lower()
                    for k, w in keywords.items():
                        if k.lower() in lower_s:
                            score += w
                    if "?" in s or "？" in s:
                        score += 2
                    if any(c in s for c in ["()", "[]", "{}", "->", "=>"]):
                        score += 3
                    if re.search(r"\.(py|js|ts|jsx|tsx|java|go|rs|cpp|c|sh|yml|yaml|json)", s):
                        score += 4
                    if re.search(r"[0-9]+\.[0-9]+", s):
                        score += 2
                    preview = s[:300] if len(s) > 300 else s
                    scored.append((score, preview, s))
            scored.sort(key=lambda x: x[0], reverse=True)
            for score, preview, full in scored:
                is_dup = False
                for existing in meaningful:
                    if ("文件:" in preview and "文件:" in existing and
                            preview.split("文件:")[1][:10] == existing.split("文件:")[1][:10]):
                        is_dup = True
                        break
                    if len(set(preview.split()) & set(existing.split())) > len(preview.split()) * 0.6:
                        is_dup = True
                        break
                if not is_dup:
                    meaningful.append(preview)
                    if len(meaningful) >= count:
                        break
            if len(meaningful) < 2:
                for msg in messages[:5]:
                    content = self._get_message_content(msg)
                    if content:
                        for line in content.split("\n"):
                            s = line.strip()
                            if s and len(s) > 20 and not any(p in s for p in skip_patterns):
                                meaningful.append(s[:300])
                                break
                    if len(meaningful) >= count:
                        break
        return meaningful[:count]

    def identify_session_topics(self, messages: List[Dict], summaries: Optional[List[str]] = None, max_topics: int = 3) -> List[str]:
        """Identify main topics from summaries and early messages."""
        topic_keywords = {
            "CCC工具": ["ccc", "token", "会话", "claude", "context", "extract", "提取"],
            "包管理": ["pip", "pipx", "uvx", "uv", "install", "package", "安装", "包"],
            "Git操作": ["git", "commit", "push", "pull", "branch", "merge", "checkout"],
            "Docker": ["docker", "container", "dockerfile", "compose", "kubernetes", "k8s"],
            "测试": ["test", "pytest", "unittest", "测试", "testing", "spec"],
            "数据库": ["database", "sql", "postgres", "mysql", "mongodb", "数据库"],
            "API开发": ["api", "endpoint", "rest", "graphql", "webhook", "接口"],
            "前端开发": ["react", "vue", "angular", "javascript", "typescript", "css", "html"],
            "Python开发": ["python", "django", "flask", "fastapi", "poetry", "venv"],
            "配置文件": ["config", "yaml", "json", "toml", "配置", "settings", "设置", "codex"],
            "错误调试": ["error", "bug", "fix", "debug", "错误", "修复", "调试", "issue"],
            "文档": ["readme", "docs", "documentation", "文档", "markdown", "md"],
            "部署": ["deploy", "production", "server", "部署", "发布", "release"],
            "AI/LLM": ["claude", "gpt", "llm", "ai", "model", "模型", "prompt", "opus"],
            "消息平台": ["line", "telegram", "whatsapp", "discord", "slack", "webhook"],
        }
        scores: Dict[str, int] = {}
        if summaries:
            for s in summaries:
                sl = s.lower()
                for topic, kws in topic_keywords.items():
                    for kw in kws:
                        if kw.lower() in sl:
                            scores[topic] = scores.get(topic, 0) + 3
        for msg in messages[:50]:
            content = self._get_message_content(msg)
            if content:
                cl = content.lower()
                for topic, kws in topic_keywords.items():
                    for kw in kws:
                        if kw.lower() in cl:
                            scores[topic] = scores.get(topic, 0) + 1
        topics = [t for t, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:max_topics] if scores[t] > 1]
        return topics

    def get_session_info(self, session_path: Path) -> Dict:
        """Parse a session file and compute summary stats (with token count)."""
        info: Dict = {
            "path": session_path,
            "name": session_path.name,
            "size": session_path.stat().st_size,
            "mtime": session_path.stat().st_mtime,
            "message_count": 0,
            "meaningful_messages": [],
            "last_messages": [],
            "tokens": 0,
            "topics": [],
            "summaries": [],
            "git_branch": None,
            "duration": None,
            "project_dir": session_path.parent.name,
        }
        try:
            messages = self.parse_session(session_path)
            info["message_count"] = len(messages)
            first_ts = None
            last_ts = None
            summaries: List[str] = []
            for msg in messages:
                if msg.get("type") == "summary":
                    s = msg.get("summary", "")
                    if s and s not in summaries:
                        summaries.append(s)
                if not info["git_branch"] and msg.get("gitBranch"):
                    info["git_branch"] = msg["gitBranch"]
                if msg.get("timestamp"):
                    if not first_ts:
                        first_ts = msg["timestamp"]
                    last_ts = msg["timestamp"]
            info["summaries"] = summaries[:3]
            if first_ts and last_ts:
                try:
                    from datetime import datetime
                    start = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
                    end = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                    delta = end - start
                    if delta.days > 0:
                        info["duration"] = f"{delta.days}天"
                    elif delta.seconds > 3600:
                        info["duration"] = f"{delta.seconds // 3600}小时"
                    elif delta.seconds > 60:
                        info["duration"] = f"{delta.seconds // 60}分钟"
                    else:
                        info["duration"] = "刚刚"
                except Exception:
                    pass
            info["topics"] = self.identify_session_topics(messages, summaries)
            info["meaningful_messages"] = self.extract_meaningful_messages(messages[:30], count=5)
            if len(messages) > 10:
                info["last_messages"] = self.extract_meaningful_messages(messages[-30:], count=5)

            total_tokens = 0
            if self.verbose:
                print(f"  开始计算tokens，消息数: {len(messages)}", file=sys.stderr)
            if self.encoder:
                all_texts: List[str] = []
                for msg in messages:
                    try:
                        if "message" in msg:
                            message = msg["message"]
                            if "content" in message:
                                content = message["content"]
                                if isinstance(content, list):
                                    for item in content:
                                        if isinstance(item, dict):
                                            if "text" in item:
                                                all_texts.append(item["text"])
                                            if "thinking" in item:
                                                all_texts.append(item["thinking"])
                                            if "signature" in item:
                                                all_texts.append(item["signature"])
                                            if "input" in item and isinstance(item["input"], dict):
                                                for v in item["input"].values():
                                                    if isinstance(v, str):
                                                        all_texts.append(v)
                                            if "content" in item and isinstance(item["content"], str):
                                                all_texts.append(item["content"])
                                elif isinstance(content, str):
                                    all_texts.append(content)
                        if "toolUseResult" in msg:
                            result = msg["toolUseResult"]
                            for key in ["stdout", "stderr", "output", "error", "result"]:
                                if key in result and isinstance(result[key], str):
                                    all_texts.append(result[key])
                            if "results" in result and isinstance(result["results"], list):
                                for r in result["results"]:
                                    if isinstance(r, str):
                                        all_texts.append(r)
                            if "file" in result and isinstance(result["file"], dict):
                                if "content" in result["file"]:
                                    all_texts.append(result["file"]["content"])
                        if "summary" in msg:
                            all_texts.append(msg["summary"])
                    except Exception as e:
                        if self.verbose:
                            print(f"  ⚠ 处理消息失败: {str(e)[:50]}", file=sys.stderr)
                        continue
                if all_texts:
                    combined = " ".join(all_texts)
                    tokens = self.encoder.encode(combined)
                    total_tokens = len(tokens)
            else:
                for msg in messages:
                    total_tokens += len(str(msg)) // 10
            info["tokens"] = total_tokens
        except Exception as e:
            print(f"  ⚠  计算会话信息时出错: {str(e)[:50]}", file=sys.stderr)
        return info

    def parse_session(self, session_path: Path) -> List[Dict]:
        """Read a JSONL session file and clean tool-call pollution."""
        messages: List[Dict] = []
        try:
            with open(session_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        msg = json.loads(line.strip())
                        messages.append(msg)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"⚠  读取会话失败: {e}", file=sys.stderr)
        if messages and self.verbose:
            print("  🧹 清理工具调用JSON污染...", file=sys.stderr)
        messages = self._clean_tool_call_pollution(messages)
        return messages

    def _clean_tool_call_pollution(self, messages: List[Dict]) -> List[Dict]:
        """Remove only tool-call JSON blocks, keep normal JSON content."""
        import copy
        import re

        def clean_tool_json(text: str) -> str:
            if not text or "[Tool:" not in text:
                return text
            patterns = [
                (r"\[Tool:\s*Write\]\s*\{[^}]*\"file_path\"[^}]*\"content\"[^}]*\}", "[Created file]"),
                (r"\[Tool:\s*Edit\]\s*\{[^}]*\"file_path\"[^}]*\"old_string\"[^}]*\}", "[Edited file]"),
                (r"\[Tool:\s*Bash\]\s*\{[^}]*\"command\"[^}]*\}", "[Executed command]"),
                (r"\[Tool:\s*Grep\]\s*\{[^}]*\"pattern\"[^}]*\}", "[Searched]"),
                (r"\[Tool:\s*(\w+)\]\s*\{[^}]*\"input\"[^}]*\}", r"[Used tool: \1]"),
                (r"\[Tool:\s*(\w+)\]\s*\{\"[^\"]+\"\s*:\s*\"[^\"]+\"\}", r"[Used tool: \1]"),
            ]
            cleaned = text
            for pattern, replacement in patterns:
                cleaned = re.sub(pattern, replacement, cleaned, flags=re.DOTALL)
            return cleaned

        cleaned_messages: List[Dict] = []
        for msg in messages:
            msg_copy = copy.deepcopy(msg)
            def clean_recursive(obj):
                if isinstance(obj, dict):
                    for key, value in list(obj.items()):
                        if key == "text" and isinstance(value, str):
                            obj[key] = clean_tool_json(value)
                        elif key == "content":
                            if isinstance(value, str):
                                obj[key] = clean_tool_json(value)
                            elif isinstance(value, list):
                                for item in value:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        if "text" in item:
                                            item["text"] = clean_tool_json(item["text"])
                                    clean_recursive(item)
                        elif isinstance(value, (dict, list)):
                            clean_recursive(value)
                elif isinstance(obj, list):
                    for item in obj:
                        clean_recursive(item)
            clean_recursive(msg_copy)
            cleaned_messages.append(msg_copy)
        return cleaned_messages

    def _binary_search_truncate(self, content: str, target_tokens: int) -> str:
        """Binary search the best cut position to stay under target tokens."""
        if not content:
            return ""
        full_tokens = self.count_tokens(content)
        if full_tokens <= target_tokens:
            return content
        left, right = 0, len(content)
        best_pos = 0
        best_tokens = 0
        for _ in range(20):
            if left >= right - 1:
                break
            mid = (left + right) // 2
            truncated = content[:mid]
            tokens = self.count_tokens(truncated)
            if tokens <= target_tokens:
                if tokens > best_tokens:
                    best_pos = mid
                    best_tokens = tokens
                left = mid
            else:
                right = mid
        return content[:best_pos]

    def extract_key_messages(
        self,
        messages: List[Dict],
        front_tokens: int = 25000,
        back_tokens: int = 75000,
    ) -> Tuple[List[Dict], Dict]:
        """Extract key messages with a front/back token allocation.

        Inputs:
        - messages: list of Claude JSONL messages
        - front_tokens: tokens to keep from the beginning (default 25k)
        - back_tokens: tokens to keep from the end (default 75k)

        Output:
        - (extracted_messages, stats)
        """
        if not messages:
            return [], {}
        stats = {
            "total_messages": len(messages),
            "extracted_messages": 0,
            "total_tokens": 0,
            "extracted_tokens": 0,
            "compression_ratio": 0,
        }
        message_tokens: List[Tuple[Dict, str, int]] = []
        for msg in messages:
            content = self._get_message_content(msg)
            if content:
                tokens = self.count_tokens(content)
                message_tokens.append((msg, content, tokens))
                stats["total_tokens"] += tokens
            else:
                message_tokens.append((msg, "", 0))
        # Normalize invalid inputs
        FRONT_TOKENS = max(0, int(front_tokens))
        BACK_TOKENS = max(0, int(back_tokens))
        front_messages: List[Dict] = []
        back_messages: List[Dict] = []
        # Front slice with precise truncation for boundary message
        front_token_count = 0
        for i, (msg, content, tokens) in enumerate(message_tokens):
            if tokens == 0:
                continue
            if front_token_count + tokens <= FRONT_TOKENS:
                front_messages.append(msg)
                front_token_count += tokens
            else:
                remaining = FRONT_TOKENS - front_token_count
                if remaining > 100:
                    truncated_content = self._binary_search_truncate(content, remaining)
                    truncated_msg = msg.copy()
                    if "message" in truncated_msg and "content" in truncated_msg["message"]:
                        if isinstance(truncated_msg["message"]["content"], list):
                            for item in truncated_msg["message"]["content"]:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    item["text"] = truncated_content + "\n\n[...内容已截断...]\n"
                                    break
                        else:
                            truncated_msg["message"]["content"] = truncated_content + "\n\n[...内容已截断...]\n"
                    front_messages.append(truncated_msg)
                    front_token_count += self.count_tokens(truncated_content)
                break
        # Back slice from tail with precise truncation
        back_token_count = 0
        temp_back: List[Dict] = []
        front_msg_set = set(id(m) for m in front_messages)
        for i, (msg, content, tokens) in enumerate(reversed(message_tokens)):
            if tokens == 0:
                continue
            if id(msg) in front_msg_set:
                continue
            if back_token_count + tokens <= BACK_TOKENS:
                temp_back.append(msg)
                back_token_count += tokens
            else:
                remaining = BACK_TOKENS - back_token_count
                if remaining > 100:
                    rev = content[::-1]
                    truncated_rev = self._binary_search_truncate(rev, remaining)
                    truncated_content_only = truncated_rev[::-1]
                    truncated_msg = msg.copy()
                    truncated_content = "[...前面内容已省略...]\n\n" + truncated_content_only
                    if "message" in truncated_msg and "content" in truncated_msg["message"]:
                        if isinstance(truncated_msg["message"]["content"], list):
                            for item in truncated_msg["message"]["content"]:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    item["text"] = truncated_content
                                    break
                        else:
                            truncated_msg["message"]["content"] = truncated_content
                    temp_back.append(truncated_msg)
                    back_token_count += self.count_tokens(truncated_content)
                break
        back_messages = list(reversed(temp_back))
        # Merge in original order
        extracted: List[Dict] = []
        for msg, _, _ in message_tokens:
            if msg in front_messages or msg in back_messages:
                extracted.append(msg)
        actual_tokens = 0
        for msg in extracted:
            content = self._get_message_content(msg)
            if content:
                actual_tokens += self.count_tokens(content)
        stats["extracted_messages"] = len(extracted)
        stats["extracted_tokens"] = actual_tokens
        if stats["total_tokens"] > 0:
            stats["compression_ratio"] = 1 - (stats["extracted_tokens"] / stats["total_tokens"])  # type: ignore[assignment]
        return extracted, stats

    def _get_message_content(self, msg: Dict) -> str:
        """Extract all text content relevant to Claude context calculation."""
        texts: List[str] = []
        def extract_all(obj, depth=0):
            if depth > 10:
                return
            if isinstance(obj, dict):
                if "message" in obj and isinstance(obj["message"], dict):
                    extract_all(obj["message"], depth + 1)
                    return
                if "content" in obj:
                    content = obj["content"]
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict):
                                if item.get("type") == "text":
                                    t = item.get("text", "")
                                    if t:
                                        texts.append(t)
                                elif item.get("type") == "thinking":
                                    th = item.get("thinking", "")
                                    if th:
                                        texts.append(f"[Thinking] {th}")
                                    sig = item.get("signature", "")
                                    if sig:
                                        texts.append(f"[Signature] {sig}")
                                elif item.get("type") == "tool_use":
                                    tool_name = item.get("name", "unknown")
                                    tool_input = item.get("input", {})
                                    texts.append(_sanitize_tool_call(tool_name, tool_input))
                                elif item.get("type") == "tool_result":
                                    result_content = item.get("content", "")
                                    if isinstance(result_content, list):
                                        texts.append(f"[Tool results: {len(result_content)} items]")
                                    elif result_content:
                                        texts.append(_sanitize_tool_result(str(result_content)))
                            elif isinstance(item, str):
                                texts.append(item)
                    elif isinstance(content, str) and content:
                        texts.append(content)
                elif "text" in obj and isinstance(obj["text"], str):
                    texts.append(obj["text"])
                elif "thinking" in obj and isinstance(obj["thinking"], str):
                    texts.append(f"[Thinking] {obj['thinking']}")
        extract_all(msg)
        return "\n".join(texts)

    def create_context_summary(self, messages: List[Dict], stats: Dict) -> str:
        """Create final text summary for pasting or sending to Claude CLI."""
        summary = f"""# 提取的对话上下文
_共{stats['extracted_messages']}条消息，压缩率{stats['compression_ratio']:.1%}_

---

"""
        for msg in messages:
            content = self._get_message_content(msg)
            if content:
                role = "👤 用户"
                if "type" in msg:
                    if msg["type"] in ("assistant", "tool_use"):
                        role = "🤖 Claude"
                elif "message" in msg and "role" in msg["message"]:
                    if msg["message"]["role"] == "assistant":
                        role = "🤖 Claude"
                summary += f"**{role}**: {content}\n\n"
        summary += f"""---

_使用{self.encoding_name}编码器，提取了{stats['extracted_tokens']}个token_"""
        return summary

    def get_preview(self, messages: List[Dict], preview_lines: int = 3) -> Dict:
        """Create head/tail preview snippet for quick inspection."""
        preview = {"total_messages": len(messages), "head": [], "tail": [], "head_text": "", "tail_text": ""}
        if not messages:
            return preview
        for i, msg in enumerate(messages[:preview_lines]):
            content = self._get_message_content(msg)
            if content:
                role = "👤 用户"
                if "type" in msg:
                    if msg["type"] in ("assistant", "tool_use"):
                        role = "🤖 Claude"
                elif "message" in msg and "role" in msg["message"]:
                    if msg["message"]["role"] == "assistant":
                        role = "🤖 Claude"
                if len(content) > 200:
                    content = content[:200] + "..."
                preview["head"].append({"index": i + 1, "role": role, "content": content})
        tail_start = max(preview_lines, len(messages) - preview_lines)
        for i, msg in enumerate(messages[tail_start:], start=tail_start):
            content = self._get_message_content(msg)
            if content:
                role = "👤 用户"
                if "type" in msg:
                    if msg["type"] in ("assistant", "tool_use"):
                        role = "🤖 Claude"
                elif "message" in msg and "role" in msg["message"]:
                    if msg["message"]["role"] == "assistant":
                        role = "🤖 Claude"
                if len(content) > 200:
                    content = content[:200] + "..."
                preview["tail"].append({"index": i + 1, "role": role, "content": content})
        preview["head_text"] = "\n".join([f"  [{it['index']:3d}] {it['role']}: {it['content']}" for it in preview["head"]])
        preview["tail_text"] = "\n".join([f"  [{it['index']:3d}] {it['role']}: {it['content']}" for it in preview["tail"]])
        return preview


def process_session_worker(args):
    """Worker used for parallel preloading (kept simple)."""
    idx, session_path = args
    try:
        extractor = ClaudeContextExtractor()
        info = extractor.get_session_info(session_path)
        info["needs_full_load"] = False
        return idx, info
    except Exception as e:
        info = {
            "path": session_path,
            "name": session_path.name,
            "size": session_path.stat().st_size,
            "mtime": session_path.stat().st_mtime,
            "message_count": 0,
            "meaningful_messages": [],
            "last_messages": [],
            "tokens": 0,
            "topics": [],
            "summaries": [],
            "git_branch": None,
            "duration": None,
            "project_dir": session_path.parent.name,
            "needs_full_load": True,
            "error": str(e)[:100],
        }
        return idx, info


def main():
    """Main CLI entry: always show interactive selector first."""
    parser = argparse.ArgumentParser(
        description="Claude对话上下文智能提取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--tokens", "-t", type=int, default=100000, help="最大token数量（默认100000）")
    parser.add_argument("--output", "-o", type=str, default=None, help="输出文件路径（默认输出到终端）")
    parser.add_argument("--send", action="store_true", help="直接发送到Claude CLI")
    parser.add_argument("--stats", action="store_true", help="显示详细统计信息")
    args = parser.parse_args()

    extractor = ClaudeContextExtractor(max_tokens=args.tokens)
    if args.stats:
        print(f"🔧 编码器: {extractor.encoding_name}", file=sys.stderr)
        if not TIKTOKEN_AVAILABLE:
            print("⚠  tiktoken未安装，使用估算模式", file=sys.stderr)

    sessions = extractor.find_claude_sessions()
    if not sessions:
        print("❌ 未找到Claude会话文件", file=sys.stderr)
        sys.exit(1)

    # Interactive selection UI
    from .interactive_ui import InteractiveSessionSelector

    print("⏳ 正在加载会话列表...", file=sys.stderr)
    session_infos: List[Dict] = []
    page_size = 3
    for session in sessions:
        info = {
            "path": session,
            "name": session.name,
            "size": session.stat().st_size,
            "mtime": session.stat().st_mtime,
            "message_count": 0,
            "meaningful_messages": [],
            "last_messages": [],
            "tokens": 0,
            "topics": [],
            "summaries": [],
            "git_branch": None,
            "duration": None,
            "project_dir": session.parent.name,
            "needs_full_load": True,
        }
        session_infos.append(info)

    print(f"  计算前 {page_size} 个会话...", file=sys.stderr)
    for i in range(min(page_size, len(session_infos))):
        try:
            full_info = extractor.get_session_info(session_infos[i]["path"])
            full_info["needs_full_load"] = False
            session_infos[i] = full_info
        except Exception as e:
            print(f"  ⚠ 加载会话 {i+1} 失败: {e}", file=sys.stderr)

    selector = InteractiveSessionSelector(session_infos, page_size=3, extractor=extractor)
    selected_info = selector.run()
    if not selected_info:
        sys.exit(0)

    selected = selected_info["path"]
    if selected_info.get("needs_full_load") or selected_info["message_count"] == 0:
        print("⏳ 正在分析选中的会话...", file=sys.stderr)
        full_info = extractor.get_session_info(selected)
        selected_info.update(full_info)

    # Detail screen
    from datetime import datetime as _dt
    print("📋 会话详情", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    mtime = _dt.fromtimestamp(selected_info["mtime"])    
    print(f"\n⏰ 时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
    print(f"📊 统计: {selected_info['message_count']} 条消息", file=sys.stderr)
    print(f"💾 大小: ≈{selected_info['tokens']:,} tokens(估算)", file=sys.stderr)
    if selected_info.get("summaries"):
        summary = selected_info["summaries"][0]
        if len(summary) > 70:
            summary = summary[:67] + "..."
        print(f"📌 主题: {summary}", file=sys.stderr)
    if selected_info.get("git_branch"):
        print(f"🌿 分支: {selected_info['git_branch']}", file=sys.stderr)

    print("\n💬 对话预览:", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    if selected_info.get("meaningful_messages"):
        print("\n🔸 开始对话:", file=sys.stderr)
        for i, msg in enumerate(selected_info["meaningful_messages"][:5], 1):
            if "[Tool" not in msg and "[Thinking]" not in msg:
                print(f"  {i}. {msg[:100]}", file=sys.stderr)
    if selected_info.get("last_messages"):
        print("\n🔚 最近对话:", file=sys.stderr)
        for i, msg in enumerate(selected_info["last_messages"][:5], 1):
            if "[Tool" not in msg and "[Thinking]" not in msg:
                print(f"  {i}. {msg[:100]}", file=sys.stderr)

    print("\n" + "=" * 60, file=sys.stderr)
    print("\n🎯 可选操作:", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    if selected_info["tokens"] == 0 or selected_info["message_count"] <= 2:
        print("⚠  这是一个空会话（无实际对话内容）", file=sys.stderr)
        print("\n  [D] 删除此空会话 (Delete)", file=sys.stderr)
        print("  [B] 返回列表 (Back)", file=sys.stderr)
        print("  [Q] 退出 (Quit)", file=sys.stderr)
    elif selected_info["tokens"] < 100000:
        print(f"✅ 会话较小 (≈{selected_info['tokens']:,} tokens < 100k)", file=sys.stderr)
        print("\n  [R] 直接恢复 (Resume) - 保留100%原始上下文", file=sys.stderr)
        print("      ⚡ 默认启用 --dangerously-skip-permissions", file=sys.stderr)
        print("  [C] 智能压缩 (Compress) - 小会话将直接恢复", file=sys.stderr)
        print("  [B] 返回列表 (Back)", file=sys.stderr)
        print("  [Q] 退出 (Quit)", file=sys.stderr)
    else:
        print(f"📊 会话大小: ≈{selected_info['tokens']:,} tokens(估算)", file=sys.stderr)
        print("\n  [R] 直接恢复 (Resume) - 保留100%原始上下文", file=sys.stderr)
        if selected_info["tokens"] > 200000:
            print("      ⚠  警告: 会话超过200k限制，可能无法完全加载", file=sys.stderr)
        print("      ⚡ 默认启用 --dangerously-skip-permissions", file=sys.stderr)
        print("  [C] 智能压缩 (Compress) - 提取关键信息", file=sys.stderr)
        print("      预计压缩后: ≈100,000 tokens(估算)", file=sys.stderr)
        print("      (保留前≈25k + 后≈75k tokens)", file=sys.stderr)
        print("  [B] 返回列表 (Back)", file=sys.stderr)
        print("  [Q] 退出 (Quit)", file=sys.stderr)

    print("\n" + "=" * 60, file=sys.stderr)
    prompt = "\n请选择操作 [R/C/B/Q]: "
    if selected_info["tokens"] == 0 or selected_info["message_count"] <= 2:
        prompt = "\n请选择操作 [D/B/Q]: "

    while True:
        try:
            choice = input(prompt).strip().lower()
            if choice == "q":
                print("\n👋 已退出", file=sys.stderr)
                sys.exit(0)
            elif choice == "b":
                print("\n🔄 返回会话列表...", file=sys.stderr)
                sys.argv = ["ccc"]
                main()
                return
            elif choice == "r":
                session_id = selected.stem
                print("\n🚀 正在使用 --resume 恢复会话...", file=sys.stderr)
                if selected_info["tokens"] > 200000:
                    print(f"⚠  警告: 会话包含 ≈{selected_info['tokens']:,} tokens(估算)，超过Claude的200k限制", file=sys.stderr)
                    print("   继续恢复可能会因为超出限制而失败", file=sys.stderr)
                print("⚡ 已启用 --dangerously-skip-permissions 跳过权限检查", file=sys.stderr)
                sys.stdout.flush()
                sys.stderr.flush()
                exit_code = os.system(f"claude --resume {session_id} --verbose --dangerously-skip-permissions")
                sys.exit(exit_code >> 8)
            elif choice == "d" and (selected_info["tokens"] == 0 or selected_info["message_count"] <= 2):
                print("\n🗑  正在删除空会话...", file=sys.stderr)
                try:
                    selected.unlink()
                    print("✅ 空会话已删除", file=sys.stderr)
                    print("\n🔄 返回会话列表...", file=sys.stderr)
                    sys.argv = ["ccc"]
                    main()
                    return
                except Exception as e:
                    print(f"❌ 删除失败: {e}", file=sys.stderr)
            elif choice == "c" and selected_info["tokens"] > 0:
                if selected_info["tokens"] < 100000:
                    session_id = selected.stem
                    print(f"\n✨ 会话较小（≈{selected_info['tokens']:,} tokens(估) < 100k），直接恢复", file=sys.stderr)
                    print("   （小会话压缩和恢复效果相同）", file=sys.stderr)
                    print("⚡ 已启用 --dangerously-skip-permissions 跳过权限检查", file=sys.stderr)
                    sys.stdout.flush()
                    sys.stderr.flush()
                    exit_code = os.system(f"claude --resume {session_id} --verbose --dangerously-skip-permissions")
                    sys.exit(exit_code >> 8)
                else:
                    print("\n🗃  正在进行智能压缩...", file=sys.stderr)
                    args.send = True
                    break
            else:
                if selected_info["tokens"] == 0 or selected_info["message_count"] <= 2:
                    print("⚠  无效选择，请输入 D/B/Q", file=sys.stderr)
                else:
                    print("⚠  无效选择，请输入 R/C/B/Q", file=sys.stderr)
        except KeyboardInterrupt:
            print("\n\n👋 已退出", file=sys.stderr)
            sys.exit(0)

    # Compression path (for large sessions)
    if args.stats:
        print(f"\n📖 解析会话: {selected.name}", file=sys.stderr)
    messages = extractor.parse_session(selected)
    if not messages:
        print("❌ 会话文件为空或格式错误", file=sys.stderr)
        sys.exit(1)
    total_tokens = selected_info.get("tokens", 0)
    print(f"\n⚠  正在压缩会话（≈{total_tokens:,} tokens估算）", file=sys.stderr)

    extracted, stats = extractor.extract_key_messages(messages)
    print("\n📊 压缩统计:", file=sys.stderr)
    print(f"  原始: {stats['total_messages']}条消息, ≈{stats['total_tokens']:,} tokens(估)", file=sys.stderr)
    print(f"  压缩后: {stats['extracted_messages']}条消息, ≈{stats['extracted_tokens']:,} tokens(估)", file=sys.stderr)
    print(f"  压缩率: {stats['compression_ratio']:.1%}", file=sys.stderr)
    print(f"  使用{extractor.encoding_name}编码器，提取了≈{stats['extracted_tokens']}个token(估算)", file=sys.stderr)

    summary = extractor.create_context_summary(extracted, stats)
    if args.output:
        if args.output == "/dev/stdout":
            print(summary)
        else:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(summary)
            print(f"✅ 已保存到: {args.output}", file=sys.stderr)
    elif args.send:
        import tempfile
        print("\n🚀 正在启动Claude...\n", file=sys.stderr)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
            tf.write(summary)
            temp_path = tf.name
        try:
            exit_code = os.system(f"cat '{temp_path}' | claude --verbose --dangerously-skip-permissions")
            exit_code = exit_code >> 8
            if exit_code == 0:
                print("\n✅ Claude会话已结束", file=sys.stderr)
            else:
                print(f"\n⚠  Claude退出代码: {exit_code}", file=sys.stderr)
        finally:
            os.unlink(temp_path)
    else:
        print(summary)


if __name__ == "__main__":
    main()
