#!/usr/bin/env python3
"""
Claude Context Smart Extract Tool
智能提取Claude对话上下文，优化token使用
"""

import json
import os
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import hashlib
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

# 导入工具调用净化器
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from tool_call_sanitizer import sanitize_tool_call, sanitize_tool_result
except ImportError:
    # 如果导入失败，提供简单的后备方案
    def sanitize_tool_call(tool_name, tool_input):
        return f"[Tool: {tool_name}]"
    def sanitize_tool_result(result_content, max_length=100):
        return "[Tool Result]"

# Token计算方式
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

class ClaudeContextExtractor:
    """Claude对话上下文智能提取器"""
    
    def __init__(self, max_tokens: int = 100000, verbose: bool = False):
        self.max_tokens = max_tokens
        self.encoder = None
        self.verbose = verbose
        
        if TIKTOKEN_AVAILABLE:
            try:
                # 尝试最新的o200k_base（GPT-4o和Claude 3.5使用）
                self.encoder = tiktoken.get_encoding("o200k_base")
                self.encoding_name = "o200k_base"
                self.vocab_size = self.encoder.n_vocab
            except Exception:
                try:
                    # 退回到cl100k_base
                    self.encoder = tiktoken.get_encoding("cl100k_base")
                    self.encoding_name = "cl100k_base"
                    self.vocab_size = self.encoder.n_vocab
                except Exception:
                    self.encoding_name = "estimation"
                    self.vocab_size = 0
        else:
            self.encoding_name = "estimation"
            self.vocab_size = 0
    
    def count_tokens(self, text: str) -> int:
        """精确计算token数量（使用tiktoken）"""
        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except:
                # 如果编码失败，使用估算
                pass
        
        # 改进的估算模式
        # Claude和GPT的tokenizer类似，但有区别
        # 基本规则：
        # - 英文：平均3-4个字符 = 1 token（包括空格）
        # - 中文：1个字符 ≈ 1.5-2 tokens
        # - 混合内容需要综合考虑
        
        total_chars = len(text)
        
        # 计算中文字符
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        non_chinese_chars = total_chars - chinese_chars
        
        # 基础估算
        if chinese_chars > non_chinese_chars:
            # 中文为主的内容
            estimated = (chinese_chars * 1.8) + (non_chinese_chars / 3.5)
        else:
            # 英文为主的内容
            # 对于英文，更准确的估算是总字符数除以3.5
            estimated = non_chinese_chars / 3.5 + (chinese_chars * 1.8)
        
        # 特殊情况调整
        if '```' in text:
            # 代码块token更多
            estimated *= 1.2
        
        if text.count('\n') > len(text) / 50:
            # 很多换行的内容（如日志、列表）token更多
            estimated *= 1.1
        
        # 确保不会太离谱
        # 最少：字符数/10（非常密集的内容）
        # 最多：字符数/2（非常稀疏的内容）
        estimated = max(total_chars / 10, min(estimated, total_chars / 2))
        
        return int(estimated)
    
    def find_claude_sessions(self) -> List[Path]:
        """查找所有Claude会话文件"""
        claude_dir = Path.home() / '.claude' / 'projects'
        
        if not claude_dir.exists():
            return []
        
        # 查找所有.jsonl文件
        sessions = []
        for project_dir in claude_dir.iterdir():
            if project_dir.is_dir():
                for jsonl_file in project_dir.glob('*.jsonl'):
                    # 只查找UUID格式的会话文件
                    if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jsonl$', 
                               jsonl_file.name):
                        # 过滤掉太小的文件（小于1KB通常是空会话）
                        if jsonl_file.stat().st_size > 1024:  # 大于1KB
                            sessions.append(jsonl_file)
        
        # 按修改时间排序（最新的在前）
        sessions.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return sessions
    
    def extract_meaningful_messages(self, messages: List[Dict], count: int = 5) -> List[str]:
        """提取有意义的消息内容，优先显示用户对话而非工具调用"""
        meaningful = []
        
        # 优先提取用户消息和Claude的文本回复
        user_messages = []
        assistant_messages = []
        
        for msg in messages:
            # 判断消息角色
            role = None
            if 'message' in msg and isinstance(msg['message'], dict):
                role = msg['message'].get('role')
            elif 'type' in msg:
                if msg['type'] == 'human':
                    role = 'user'
                elif msg['type'] == 'assistant':
                    role = 'assistant'
            
            content = self._get_message_content(msg)
            if not content:
                continue
                
            # 跳过工具调用和结果
            if content.startswith('[Tool:') or content.startswith('[Tool Result]'):
                continue
                
            # 跳过思考内容（太长）
            if content.startswith('[Thinking]'):
                continue
                
            # 跳过系统消息和模板
            if any(p in content for p in ['# 提取的对话上下文', '# 之前的对话上下文', 
                                          'This session is being continued', '_共', '---',
                                          '[Request interrupted', 'No response requested']):
                continue
            
            # 清理内容
            lines = content.split('\n')
            clean_lines = []
            for line in lines:
                line = line.strip()
                if line and len(line) > 10 and not line.startswith('#') and not line.startswith('_'):
                    # 移除markdown格式
                    if line.startswith('**') and line.endswith('**'):
                        line = line[2:-2]
                    clean_lines.append(line)
            
            if clean_lines:
                clean_content = ' '.join(clean_lines[:3])[:300]  # 取前3行，最多300字符
                if role == 'user' or role == 'human':
                    user_messages.append(('👤 ' + clean_content, len(user_messages)))
                elif role == 'assistant':
                    assistant_messages.append(('🤖 ' + clean_content, len(assistant_messages)))
                else:
                    # 未知角色，尝试从内容判断
                    if any(marker in content for marker in ['用户:', 'User:', 'Human:']):
                        user_messages.append(('👤 ' + clean_content, len(user_messages)))
                    elif any(marker in content for marker in ['Claude:', 'Assistant:', '助手:']):
                        assistant_messages.append(('🤖 ' + clean_content, len(assistant_messages)))
        
        # 交替添加用户和助手消息，保持对话流
        added_user = 0
        added_assistant = 0
        
        while len(meaningful) < count and (added_user < len(user_messages) or added_assistant < len(assistant_messages)):
            # 优先添加用户消息
            if added_user < len(user_messages):
                meaningful.append(user_messages[added_user][0])
                added_user += 1
            
            # 然后添加助手回复
            if added_assistant < len(assistant_messages) and len(meaningful) < count:
                meaningful.append(assistant_messages[added_assistant][0])
                added_assistant += 1
        
        # 如果还没有找到足够的消息，使用旧的逻辑作为后备
        if len(meaningful) < 2:
            skip_patterns = [
                '# 提取的对话上下文', '# 之前的对话上下文', 
                'This session is being continued', '_共', '---',
                '[Request interrupted', 'No response requested',
                '[Tool Result] File created successfully',
                '[Tool Result] The file',
                '[Tool Result] Todos have been modified'
            ]
            
            # 关键词权重（帮助识别重要内容）
            keywords = {
                'bug': 5, 'error': 5, '错误': 5, 'fix': 4, '修复': 4,
                'implement': 4, '实现': 4, 'create': 4, '创建': 4,
                'database': 3, '数据库': 3, 'api': 3, 'API': 3,
                'function': 3, '函数': 3, 'class': 3, '类': 3,
                'test': 3, '测试': 3, 'deploy': 3, '部署': 3,
                'webhook': 4, 'line': 4, 'LINE': 4, 'telegram': 4,
                'docker': 3, 'kubernetes': 3, 'aws': 3, 'azure': 3,
                'react': 3, 'vue': 3, 'python': 3, 'javascript': 3,
                'install': 3, '安装': 3, 'setup': 3, '配置': 3,
                'optimize': 3, '优化': 3, 'performance': 3, '性能': 3
            }
            
            scored_messages = []
            
            for msg in messages:
                content = self._get_message_content(msg)
                if not content:
                    continue
                
                # 跳过无意义内容
                if any(pattern in content for pattern in skip_patterns):
                    continue
            
                # 提取并评分每行
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                
                # 跳过太短或特殊标记
                if not line or len(line) < 10 or line.startswith('#') or \
                   line.startswith('_') or line.startswith('**') or line == '---':
                    continue
                
                # 清理对话标记
                if any(marker in line for marker in ['用户:', 'Claude:', '助手:', 'User:', 'Human:', 'Assistant:']):
                    if ':' in line:
                        parts = line.split(':', 1)
                        if len(parts) > 1:
                            line = parts[1].strip()
                
                # 跳过工具调用 - 这些内容对用户无意义
                if line.startswith('[Tool:') or line.startswith('[Tool Result]') or line.startswith('[Thinking]'):
                    continue
                
                if not line or len(line) < 10:
                    continue
                
                # 计算得分（包含的关键词越多分数越高）
                score = 0
                lower_line = line.lower()
                for keyword, weight in keywords.items():
                    if keyword.lower() in lower_line:
                        score += weight
                
                # 额外加分项
                if '?' in line or '？' in line:  # 问题
                    score += 2
                if any(c in line for c in ['()', '[]', '{}', '->', '=>']):  # 代码相关
                    score += 3
                if re.search(r'\.(py|js|ts|jsx|tsx|java|go|rs|cpp|c|sh|yml|yaml|json)', line):  # 文件名
                    score += 4
                if re.search(r'[0-9]+\.[0-9]+', line):  # 版本号
                    score += 2
                
                # 保存评分后的消息（保留完整内容）
                preview = line[:300] if len(line) > 300 else line
                scored_messages.append((score, preview, line))
        
            # 按得分排序，取最有特征的
            scored_messages.sort(key=lambda x: x[0], reverse=True)
            
            # 取前N个最有特征的消息，避免重复
            seen = set()
            seen_prefixes = set()  # 用于检查相似内容
            for score, preview, full in scored_messages:
                # 避免重复（相似度检查）
                preview_key = preview[:30].lower()
                preview_prefix = preview[:20].lower()
                
                # 跳过太相似的内容
                if preview_key not in seen and preview_prefix not in seen_prefixes:
                    # 额外检查：避免重复的文件名或命令
                    is_duplicate = False
                    for existing in meaningful:
                        # 检查是否是相同文件的不同操作
                        if ('文件:' in preview and '文件:' in existing and 
                            preview.split('文件:')[1][:10] == existing.split('文件:')[1][:10]):
                            is_duplicate = True
                            break
                        # 检查相似度
                        if len(set(preview.split()) & set(existing.split())) > len(preview.split()) * 0.6:
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        meaningful.append(preview)
                        seen.add(preview_key)
                        seen_prefixes.add(preview_prefix)
                        if len(meaningful) >= count:
                            break
        
            # 如果没找到有特征的，至少返回一些内容
            if len(meaningful) < 2:
                for msg in messages[:5]:
                    content = self._get_message_content(msg)
                    if content:
                        lines = content.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line and len(line) > 20 and not any(p in line for p in skip_patterns):
                                meaningful.append(line[:300])
                                break
                    if len(meaningful) >= count:
                        break
        
        return meaningful[:count]
    
    def identify_session_topics(self, messages: List[Dict], summaries: List[str] = None, max_topics: int = 3) -> List[str]:
        """识别会话的主要话题"""
        # 话题关键词和分类
        topic_keywords = {
            'CCDRC工具': ['ccdrc', 'token', '会话', 'claude', 'context', 'extract', '提取'],
            '包管理': ['pip', 'pipx', 'uvx', 'uv', 'install', 'package', '安装', '包'],
            'Git操作': ['git', 'commit', 'push', 'pull', 'branch', 'merge', 'checkout'],
            'Docker': ['docker', 'container', 'dockerfile', 'compose', 'kubernetes', 'k8s'],
            '测试': ['test', 'pytest', 'unittest', '测试', 'testing', 'spec'],
            '数据库': ['database', 'sql', 'postgres', 'mysql', 'mongodb', '数据库'],
            'API开发': ['api', 'endpoint', 'rest', 'graphql', 'webhook', '接口'],
            '前端开发': ['react', 'vue', 'angular', 'javascript', 'typescript', 'css', 'html'],
            'Python开发': ['python', 'django', 'flask', 'fastapi', 'poetry', 'venv'],
            '配置文件': ['config', 'yaml', 'json', 'toml', '配置', 'settings', '设置', 'codex'],
            '错误调试': ['error', 'bug', 'fix', 'debug', '错误', '修复', '调试', 'issue'],
            '文档': ['readme', 'docs', 'documentation', '文档', 'markdown', 'md'],
            '部署': ['deploy', 'production', 'server', '部署', '发布', 'release'],
            'AI/LLM': ['claude', 'gpt', 'llm', 'ai', 'model', '模型', 'prompt', 'opus'],
            '消息平台': ['line', 'telegram', 'whatsapp', 'discord', 'slack', 'webhook'],
        }
        
        # 计算每个话题的得分
        topic_scores = {}
        
        # 先分析摘要（如果有的话，权重更高）
        if summaries:
            for summary in summaries:
                summary_lower = summary.lower()
                for topic, keywords in topic_keywords.items():
                    for keyword in keywords:
                        if keyword.lower() in summary_lower:
                            # 摘要中的关键词权重更高
                            topic_scores[topic] = topic_scores.get(topic, 0) + 3
        
        # 分析消息内容
        for msg in messages[:50]:  # 只分析前50条消息
            content = self._get_message_content(msg)
            if content:
                content_lower = content.lower()
                for topic, keywords in topic_keywords.items():
                    for keyword in keywords:
                        if keyword.lower() in content_lower:
                            topic_scores[topic] = topic_scores.get(topic, 0) + 1
        
        # 按得分排序，返回前N个话题
        sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
        topics = [topic for topic, score in sorted_topics[:max_topics] if score > 1]
        
        return topics
    
    def get_session_info(self, session_path: Path) -> Dict:
        """获取会话的详细信息"""
        info = {
            'path': session_path,
            'name': session_path.name,
            'size': session_path.stat().st_size,
            'mtime': session_path.stat().st_mtime,
            'message_count': 0,
            'meaningful_messages': [],  # 有意义的消息列表
            'last_messages': [],  # 最后几条消息
            'tokens': 0,
            'topics': [],  # 会话主题
            'summaries': [],  # Claude生成的摘要
            'git_branch': None,  # Git分支
            'duration': None,  # 会话持续时间
            'project_dir': session_path.parent.name
        }
        
        try:
            messages = self.parse_session(session_path)
            info['message_count'] = len(messages)
            
            # 提取摘要和元信息
            first_timestamp = None
            last_timestamp = None
            summaries = []
            
            for msg in messages:
                # 提取摘要
                if msg.get('type') == 'summary':
                    summary_text = msg.get('summary', '')
                    if summary_text and summary_text not in summaries:
                        summaries.append(summary_text)
                
                # 提取Git分支（取第一个非空的）
                if not info['git_branch'] and msg.get('gitBranch'):
                    info['git_branch'] = msg['gitBranch']
                
                # 提取时间戳
                if msg.get('timestamp'):
                    if not first_timestamp:
                        first_timestamp = msg['timestamp']
                    last_timestamp = msg['timestamp']
            
            info['summaries'] = summaries[:3]  # 最多保留3个摘要
            
            # 计算会话持续时间
            if first_timestamp and last_timestamp:
                try:
                    from datetime import datetime
                    start = datetime.fromisoformat(first_timestamp.replace('Z', '+00:00'))
                    end = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00'))
                    duration = end - start
                    if duration.days > 0:
                        info['duration'] = f"{duration.days}天"
                    elif duration.seconds > 3600:
                        info['duration'] = f"{duration.seconds // 3600}小时"
                    elif duration.seconds > 60:
                        info['duration'] = f"{duration.seconds // 60}分钟"
                    else:
                        info['duration'] = "刚刚"
                except:
                    pass
            
            # 识别会话主题（结合摘要信息）
            info['topics'] = self.identify_session_topics(messages, summaries)
            
            # 提取有意义的消息（前面的）- 增加到5条以提供更多区分度
            info['meaningful_messages'] = self.extract_meaningful_messages(messages[:30], count=5)
            
            # 提取最后几条有意义的消息（更容易记住）- 增加到5条
            if len(messages) > 10:
                info['last_messages'] = self.extract_meaningful_messages(messages[-30:], count=5)
            
            # 准确计算：只算内容，不算JSON结构
            total_tokens = 0
            
            if self.verbose:
                print(f"  开始计算tokens，消息数: {len(messages)}", file=sys.stderr)
            
            if self.encoder:
                # 收集所有实际内容文本
                all_texts = []
                
                for msg in messages:
                    try:
                        # 提取不同类型的内容
                        msg_type = msg.get('type', '')
                        
                        # 1. 处理message字段中的内容
                        if 'message' in msg:
                            message = msg['message']
                            
                            # 提取content
                            if 'content' in message:
                                content = message['content']
                                if isinstance(content, list):
                                    for item in content:
                                        if isinstance(item, dict):
                                            # 文本内容
                                            if 'text' in item:
                                                all_texts.append(item['text'])
                                            # thinking内容（重要！）
                                            if 'thinking' in item:
                                                all_texts.append(item['thinking'])
                                            # signature签名（全部计入）
                                            if 'signature' in item:
                                                all_texts.append(item['signature'])
                                            # tool输入参数
                                            if 'input' in item and isinstance(item['input'], dict):
                                                for value in item['input'].values():
                                                    if isinstance(value, str):
                                                        all_texts.append(value)
                                            # 嵌套的content
                                            if 'content' in item and isinstance(item['content'], str):
                                                all_texts.append(item['content'])
                                elif isinstance(content, str):
                                    all_texts.append(content)
                        
                        # 2. 处理toolUseResult字段（工具执行结果）
                        if 'toolUseResult' in msg:
                            result = msg['toolUseResult']
                            # stdout/stderr输出
                            for key in ['stdout', 'stderr', 'output', 'error', 'result']:
                                if key in result and isinstance(result[key], str):
                                    all_texts.append(result[key])
                            # results数组
                            if 'results' in result and isinstance(result['results'], list):
                                for r in result['results']:
                                    if isinstance(r, str):
                                        all_texts.append(r)
                            # file内容
                            if 'file' in result and isinstance(result['file'], dict):
                                if 'content' in result['file']:
                                    all_texts.append(result['file']['content'])
                        
                        # 3. 处理summary字段
                        if 'summary' in msg:
                            all_texts.append(msg['summary'])
                            
                    except Exception as e:
                        if self.verbose:
                            print(f"  ⚠ 处理消息失败: {str(e)[:50]}", file=sys.stderr)
                        continue
                
                # 计算所有文本的tokens
                if all_texts:
                    combined_text = ' '.join(all_texts)
                    tokens = self.encoder.encode(combined_text)
                    total_tokens = len(tokens)
                    
            else:
                # 没有tokenizer，用简单估算
                for msg in messages:
                    total_tokens += len(str(msg)) // 10
            
            info['tokens'] = total_tokens
            
        except Exception as e:
            # 记录错误但不崩溃
            print(f"  ⚠  计算会话信息时出错: {str(e)[:50]}", file=sys.stderr)
        
        return info
    
    def parse_session(self, session_path: Path) -> List[Dict]:
        """解析会话文件"""
        messages = []
        
        try:
            with open(session_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        msg = json.loads(line.strip())
                        messages.append(msg)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"⚠  读取会话失败: {e}", file=sys.stderr)
        
        # 清理工具调用JSON污染（保留正常JSON）
        if messages and self.verbose:
            print(f"  🧹 清理工具调用JSON污染...", file=sys.stderr)
        messages = self._clean_tool_call_pollution(messages)
        
        return messages
    
    def _clean_tool_call_pollution(self, messages: List[Dict]) -> List[Dict]:
        """清理工具调用JSON污染，保留正常的JSON数据"""
        import re
        import copy
        
        def clean_tool_json(text: str) -> str:
            """只清理工具调用JSON，保留其他JSON"""
            if not text or '[Tool:' not in text:
                return text
            
            # 清理模式：[Tool: Name] {json with specific keys}
            # 只清理包含工具调用特征键的JSON
            patterns = [
                # Write工具
                (r'\[Tool:\s*Write\]\s*\{[^}]*"file_path"[^}]*"content"[^}]*\}', '[Created file]'),
                # Edit工具
                (r'\[Tool:\s*Edit\]\s*\{[^}]*"file_path"[^}]*"old_string"[^}]*\}', '[Edited file]'),
                # Bash工具
                (r'\[Tool:\s*Bash\]\s*\{[^}]*"command"[^}]*\}', '[Executed command]'),
                # Grep工具
                (r'\[Tool:\s*Grep\]\s*\{[^}]*"pattern"[^}]*\}', '[Searched]'),
                # 通用工具JSON（包含input键）
                (r'\[Tool:\s*(\w+)\]\s*\{[^}]*"input"[^}]*\}', r'[Used tool: \1]'),
                # 其他明显的工具调用
                (r'\[Tool:\s*(\w+)\]\s*\{"[^"]+"\s*:\s*"[^"]+"\}', r'[Used tool: \1]'),
            ]
            
            cleaned = text
            for pattern, replacement in patterns:
                cleaned = re.sub(pattern, replacement, cleaned, flags=re.DOTALL)
            
            return cleaned
        
        cleaned_messages = []
        for msg in messages:
            msg_copy = copy.deepcopy(msg)
            
            # 递归清理消息内容
            def clean_recursive(obj):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key == 'text' and isinstance(value, str):
                            obj[key] = clean_tool_json(value)
                        elif key == 'content':
                            if isinstance(value, str):
                                obj[key] = clean_tool_json(value)
                            elif isinstance(value, list):
                                for item in value:
                                    if isinstance(item, dict) and item.get('type') == 'text':
                                        if 'text' in item:
                                            item['text'] = clean_tool_json(item['text'])
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
        """使用二分查找精确切割内容到目标token数
        
        Args:
            content: 要切割的内容
            target_tokens: 目标token数
        
        Returns:
            切割后的内容，确保token数不超过target_tokens
        """
        if not content:
            return ""
        
        # 首先检查完整内容
        full_tokens = self.count_tokens(content)
        if full_tokens <= target_tokens:
            return content
        
        # 二分查找最佳切割点
        left, right = 0, len(content)
        best_pos = 0
        best_tokens = 0
        
        # 最多迭代20次避免无限循环
        for _ in range(20):
            if left >= right - 1:
                break
                
            mid = (left + right) // 2
            truncated = content[:mid]
            tokens = self.count_tokens(truncated)
            
            if tokens <= target_tokens:
                # 记录最佳位置
                if tokens > best_tokens:
                    best_pos = mid
                    best_tokens = tokens
                left = mid
            else:
                right = mid
        
        # 返回最佳切割
        return content[:best_pos]
    
    def extract_key_messages(self, messages: List[Dict]) -> Tuple[List[Dict], Dict]:
        """智能提取关键消息 - 前25k + 后75k策略"""
        if not messages:
            return [], {}
        
        stats = {
            'total_messages': len(messages),
            'extracted_messages': 0,
            'total_tokens': 0,
            'extracted_tokens': 0,
            'compression_ratio': 0
        }
        
        # 计算所有消息的token
        message_tokens = []
        for msg in messages:
            content = self._get_message_content(msg)
            if content:
                tokens = self.count_tokens(content)
                message_tokens.append((msg, content, tokens))
                stats['total_tokens'] += tokens
            else:
                message_tokens.append((msg, '', 0))
        
        # 策略：前25k + 后75k = 100k tokens
        # 使用精确切割算法确保达到目标
        FRONT_TOKENS = 25000
        BACK_TOKENS = 75000
        
        front_messages = []
        back_messages = []
        
        # 1. 提取前25k tokens的消息（精确切割）
        front_token_count = 0
        for i, (msg, content, tokens) in enumerate(message_tokens):
            if tokens == 0:
                continue
                
            if front_token_count + tokens <= FRONT_TOKENS:
                # 完整添加这条消息
                front_messages.append(msg)
                front_token_count += tokens
            else:
                # 需要切割这条消息
                remaining_tokens = FRONT_TOKENS - front_token_count
                if remaining_tokens > 100:  # 如果剩余空间足够（>100 tokens），进行切割
                    # 使用二分查找精确切割内容
                    truncated_content = self._binary_search_truncate(content, remaining_tokens)
                    
                    # 创建切割后的消息
                    truncated_msg = msg.copy()
                    
                    # 更新消息内容
                    if 'message' in truncated_msg and 'content' in truncated_msg['message']:
                        if isinstance(truncated_msg['message']['content'], list):
                            for item in truncated_msg['message']['content']:
                                if item.get('type') == 'text':
                                    item['text'] = truncated_content + "\n\n[...内容已截断...]\n"
                                    break
                        else:
                            truncated_msg['message']['content'] = truncated_content + "\n\n[...内容已截断...]\n"
                    
                    front_messages.append(truncated_msg)
                    # 计算实际添加的tokens（而不是假设值）
                    actual_truncated_tokens = self.count_tokens(truncated_content)
                    front_token_count += actual_truncated_tokens
                break  # 达到目标，停止
        
        # 2. 提取后75k tokens的消息（从后往前，精确切割）
        back_token_count = 0
        temp_back = []
        front_msg_set = set(id(m) for m in front_messages)  # 用id避免比较整个dict
        
        for i, (msg, content, tokens) in enumerate(reversed(message_tokens)):
            if tokens == 0:
                continue
            # 跳过已经在front_messages中的消息
            if id(msg) in front_msg_set:
                continue
                
            if back_token_count + tokens <= BACK_TOKENS:
                # 完整添加这条消息
                temp_back.append(msg)
                back_token_count += tokens
            else:
                # 需要切割这条消息（从后面切）
                remaining_tokens = BACK_TOKENS - back_token_count
                if remaining_tokens > 100:  # 如果剩余空间足够（>100 tokens），进行切割
                    # 使用二分查找精确切割内容（从后面切）
                    # 先反转内容，切割，再反转回来
                    reversed_content = content[::-1]
                    truncated_reversed = self._binary_search_truncate(reversed_content, remaining_tokens)
                    truncated_content_only = truncated_reversed[::-1]
                    
                    # 创建切割后的消息（取后面部分）
                    truncated_msg = msg.copy()
                    truncated_content = "[...前面内容已省略...]\n\n" + truncated_content_only
                    
                    # 更新消息内容
                    if 'message' in truncated_msg and 'content' in truncated_msg['message']:
                        if isinstance(truncated_msg['message']['content'], list):
                            for item in truncated_msg['message']['content']:
                                if item.get('type') == 'text':
                                    item['text'] = truncated_content
                                    break
                        else:
                            truncated_msg['message']['content'] = truncated_content
                    
                    temp_back.append(truncated_msg)
                    # 计算实际添加的tokens（而不是假设值）
                    actual_truncated_tokens = self.count_tokens(truncated_content)
                    back_token_count += actual_truncated_tokens
                break  # 达到目标，停止
        
        # 反转back_messages恢复原始顺序
        back_messages = list(reversed(temp_back))
        
        # 合并消息（保持原始顺序）
        extracted = []
        for msg, _, _ in message_tokens:
            if msg in front_messages or msg in back_messages:
                extracted.append(msg)
        
        # 计算实际提取的tokens
        actual_tokens = 0
        for msg in extracted:
            content = self._get_message_content(msg)
            if content:
                actual_tokens += self.count_tokens(content)
        
        # 不需要额外补充，因为我们已经精确切割到目标值
        
        stats['extracted_messages'] = len(extracted)
        stats['extracted_tokens'] = actual_tokens
        
        if stats['total_tokens'] > 0:
            stats['compression_ratio'] = 1 - (stats['extracted_tokens'] / stats['total_tokens'])
        
        return extracted, stats
    
    def _get_message_content(self, msg: Dict) -> str:
        """提取消息内容 - 匹配Claude Code实际context计算
        
        包含所有会被Claude计入context的内容：
        - 用户/助手的文本消息
        - 思考内容(thinking)
        - 工具调用的输入参数
        - 工具结果（可能很大）
        """
        texts = []
        
        def extract_all(obj, depth=0):
            """递归提取所有文本内容"""
            if depth > 10:  # 防止无限递归
                return
            
            if isinstance(obj, dict):
                # 处理message字段
                if 'message' in obj and isinstance(obj['message'], dict):
                    extract_all(obj['message'], depth + 1)
                    return
                
                # 处理content字段
                if 'content' in obj:
                    content = obj['content']
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict):
                                # 文本内容
                                if item.get('type') == 'text':
                                    text = item.get('text', '')
                                    if text:
                                        texts.append(text)
                                # 思考内容 - Claude会计入context
                                elif item.get('type') == 'thinking':
                                    thinking = item.get('thinking', '')
                                    if thinking:
                                        texts.append(f"[Thinking] {thinking}")
                                    # 同时提取signature字段（thinking的签名）
                                    signature = item.get('signature', '')
                                    if signature:
                                        texts.append(f"[Signature] {signature}")
                                # 工具使用 - 使用净化器避免JSON污染
                                elif item.get('type') == 'tool_use':
                                    tool_name = item.get('name', 'unknown')
                                    tool_input = item.get('input', {})
                                    # 使用净化器转换，避免JSON格式污染上下文
                                    sanitized = sanitize_tool_call(tool_name, tool_input)
                                    texts.append(sanitized)
                                # 工具结果 - 使用净化器简化，避免过长内容
                                elif item.get('type') == 'tool_result':
                                    result_content = item.get('content', '')
                                    if isinstance(result_content, list):
                                        # 多个结果，简化表示
                                        texts.append(f"[Tool results: {len(result_content)} items]")
                                    elif result_content:
                                        # 使用净化器简化结果
                                        sanitized_result = sanitize_tool_result(str(result_content))
                                        texts.append(sanitized_result)
                            elif isinstance(item, str):
                                texts.append(item)
                    elif isinstance(content, str) and content:
                        texts.append(content)
                
                # 直接的text字段
                elif 'text' in obj and isinstance(obj['text'], str):
                    texts.append(obj['text'])
                # 直接的thinking字段
                elif 'thinking' in obj and isinstance(obj['thinking'], str):
                    texts.append(f"[Thinking] {obj['thinking']}")
        
        extract_all(msg)
        return '\n'.join(texts)
    
    def create_context_summary(self, messages: List[Dict], stats: Dict) -> str:
        """创建上下文摘要"""
        summary = f"""# 提取的对话上下文
_共{stats['extracted_messages']}条消息，压缩率{stats['compression_ratio']:.1%}_

---

"""
        
        for msg in messages:
            content = self._get_message_content(msg)
            if content:
                # 判断角色
                role = "👤 用户"
                if 'type' in msg:
                    if msg['type'] == 'assistant' or msg['type'] == 'tool_use':
                        role = "🤖 Claude"
                elif 'message' in msg and 'role' in msg['message']:
                    if msg['message']['role'] == 'assistant':
                        role = "🤖 Claude"
                
                # 不再截断内容，保留完整消息
                # 如果需要控制总长度，应该在选择消息时就处理，而不是在输出时截断
                
                summary += f"**{role}**: {content}\n\n"
        
        summary += f"""---

_使用{self.encoding_name}编码器，提取了{stats['extracted_tokens']}个token_"""
        
        return summary
    
    def get_preview(self, messages: List[Dict], preview_lines: int = 3) -> Dict:
        """获取消息预览（开头和结尾）"""
        preview = {
            'total_messages': len(messages),
            'head': [],
            'tail': [],
            'head_text': '',
            'tail_text': ''
        }
        
        if not messages:
            return preview
        
        # 获取开头消息
        for i, msg in enumerate(messages[:preview_lines]):
            content = self._get_message_content(msg)
            if content:
                # 判断角色
                role = "👤 用户"
                if 'type' in msg:
                    if msg['type'] == 'assistant' or msg['type'] == 'tool_use':
                        role = "🤖 Claude"
                elif 'message' in msg and 'role' in msg['message']:
                    if msg['message']['role'] == 'assistant':
                        role = "🤖 Claude"
                
                # 截断过长内容用于预览
                if len(content) > 200:
                    content = content[:200] + "..."
                
                preview['head'].append({
                    'index': i + 1,
                    'role': role,
                    'content': content
                })
        
        # 获取结尾消息
        tail_start = max(preview_lines, len(messages) - preview_lines)
        for i, msg in enumerate(messages[tail_start:], start=tail_start):
            content = self._get_message_content(msg)
            if content:
                # 判断角色
                role = "👤 用户"
                if 'type' in msg:
                    if msg['type'] == 'assistant' or msg['type'] == 'tool_use':
                        role = "🤖 Claude"
                elif 'message' in msg and 'role' in msg['message']:
                    if msg['message']['role'] == 'assistant':
                        role = "🤖 Claude"
                
                # 截断过长内容用于预览
                if len(content) > 200:
                    content = content[:200] + "..."
                
                preview['tail'].append({
                    'index': i + 1,
                    'role': role,
                    'content': content
                })
        
        # 生成预览文本
        head_lines = []
        for item in preview['head']:
            head_lines.append(f"  [{item['index']:3d}] {item['role']}: {item['content']}")
        preview['head_text'] = '\n'.join(head_lines)
        
        tail_lines = []
        for item in preview['tail']:
            tail_lines.append(f"  [{item['index']:3d}] {item['role']}: {item['content']}")
        preview['tail_text'] = '\n'.join(tail_lines)
        
        return preview

def process_session_worker(args):
    """多进程worker函数 - 处理单个会话"""
    idx, session_path = args
    try:
        # 创建新的extractor实例（每个进程独立）
        extractor = ClaudeContextExtractor()
        info = extractor.get_session_info(session_path)
        info['needs_full_load'] = False
        return idx, info
    except Exception as e:
        # 出错时返回默认值
        info = {
            'path': session_path,
            'name': session_path.name,
            'size': session_path.stat().st_size,
            'mtime': session_path.stat().st_mtime,
            'message_count': 0,
            'meaningful_messages': [],
            'last_messages': [],
            'tokens': 0,
            'topics': [],
            'summaries': [],
            'git_branch': None,
            'duration': None,
            'project_dir': session_path.parent.name,
            'needs_full_load': True,
            'error': str(e)[:100]
        }
        return idx, info

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Claude对话上下文智能提取工具',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 简化：默认就是交互模式
    parser.add_argument(
        '--tokens', '-t',
        type=int,
        default=100000,
        help='最大token数量（默认100000）'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='输出文件路径（默认输出到终端）'
    )
    
    parser.add_argument(
        '--send',
        action='store_true',
        help='直接发送到Claude CLI'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='显示详细统计信息'
    )
    
    args = parser.parse_args()
    
    # 创建提取器
    extractor = ClaudeContextExtractor(max_tokens=args.tokens)
    
    # 显示编码器信息
    if args.stats:
        print(f"🔧 编码器: {extractor.encoding_name}", file=sys.stderr)
        if not TIKTOKEN_AVAILABLE:
            print("⚠  tiktoken未安装，使用估算模式", file=sys.stderr)
    
    # 查找会话
    sessions = extractor.find_claude_sessions()
    
    if not sessions:
        print("❌ 未找到Claude会话文件", file=sys.stderr)
        sys.exit(1)
    
    # 默认进入交互式选择（简化流程）
    if True:  # 总是使用交互模式
        # 使用新的分页UI
        from .interactive_ui import InteractiveSessionSelector
        
        # 预加载会话信息（只加载第一页）
        print("⏳ 正在加载会话列表...", file=sys.stderr)
        session_infos = []
        page_size = 3  # 与UI的page_size匹配
        
        # 只获取基本信息，不计算tokens（延迟加载）
        for session in sessions:
            # 快速获取基本信息
            info = {
                'path': session,
                'name': session.name,
                'size': session.stat().st_size,
                'mtime': session.stat().st_mtime,
                'message_count': 0,  # 延迟加载
                'meaningful_messages': [],
                'last_messages': [],
                'tokens': 0,  # 延迟加载
                'topics': [],
                'summaries': [],
                'git_branch': None,
                'duration': None,
                'project_dir': session.parent.name,
                'needs_full_load': True  # 标记需要加载
            }
            session_infos.append(info)
        
        # 只计算第一页的会话（前3个）
        print(f"  计算前 {page_size} 个会话...", file=sys.stderr)
        for i in range(min(page_size, len(session_infos))):
            try:
                full_info = extractor.get_session_info(session_infos[i]['path'])
                full_info['needs_full_load'] = False
                session_infos[i] = full_info
            except Exception as e:
                print(f"  ⚠ 加载会话 {i+1} 失败: {e}", file=sys.stderr)
        
        # 创建并运行选择器（传入extractor用于延迟加载）
        selector = InteractiveSessionSelector(session_infos, page_size=3, extractor=extractor)
        selected_info = selector.run()
        
        if not selected_info:
            sys.exit(0)
        
        selected = selected_info['path']
        
        # 如果选中的会话还没有完整加载，现在加载
        if selected_info.get('needs_full_load') or selected_info['message_count'] == 0:
            print("⏳ 正在分析选中的会话...", file=sys.stderr)
            full_info = extractor.get_session_info(selected)
            selected_info.update(full_info)
        
        # 显示详细的确认信息
        
        # Avoid ANSI clear-screen sequences to prevent rendering issues on iOS Termius
        # Previously used: print("\033[2J\033[H", end='', file=sys.stderr)
        print("📋 会话详情", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        
        # 显示会话基本信息
        from datetime import datetime
        mtime = datetime.fromtimestamp(selected_info['mtime'])
        print(f"\n⏰ 时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
        print(f"📊 统计: {selected_info['message_count']} 条消息", file=sys.stderr)
        print(f"💾 大小: ≈{selected_info['tokens']:,} tokens(估算)", file=sys.stderr)
        
        if selected_info.get('summaries'):
            summary = selected_info['summaries'][0]
            if len(summary) > 70:
                summary = summary[:67] + "..."
            print(f"📌 主题: {summary}", file=sys.stderr)
        
        if selected_info.get('git_branch'):
            print(f"🌿 分支: {selected_info['git_branch']}", file=sys.stderr)
        
        # 显示更详细的对话内容
        print(f"\n💬 对话预览:", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        
        # 显示前5条有意义的消息
        if selected_info.get('meaningful_messages'):
            print("\n🔸 开始对话:", file=sys.stderr)
            for i, msg in enumerate(selected_info['meaningful_messages'][:5], 1):
                # 清理工具调用
                if '[Tool' not in msg and '[Thinking]' not in msg:
                    if msg.startswith('👤') or msg.startswith('🤖'):
                        print(f"  {i}. {msg[:100]}", file=sys.stderr)
                    else:
                        print(f"  {i}. {msg[:100]}", file=sys.stderr)
        
        # 显示最后5条消息
        if selected_info.get('last_messages'):
            print("\n🔚 最近对话:", file=sys.stderr)
            for i, msg in enumerate(selected_info['last_messages'][:5], 1):
                if '[Tool' not in msg and '[Thinking]' not in msg:
                    if msg.startswith('👤') or msg.startswith('🤖'):
                        print(f"  {i}. {msg[:100]}", file=sys.stderr)
                    else:
                        print(f"  {i}. {msg[:100]}", file=sys.stderr)
        
        # 显示可选操作
        print("\n" + "=" * 60, file=sys.stderr)
        print("\n🎯 可选操作:", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        
        # 特殊处理空会话
        if selected_info['tokens'] == 0 or selected_info['message_count'] <= 2:
            print("⚠  这是一个空会话（无实际对话内容）", file=sys.stderr)
            print("\n  [D] 删除此空会话 (Delete)", file=sys.stderr)
            print("  [B] 返回列表 (Back)", file=sys.stderr)
            print("  [Q] 退出 (Quit)", file=sys.stderr)
        elif selected_info['tokens'] < 100000:
            print(f"✅ 会话较小 (≈{selected_info['tokens']:,} tokens < 100k)", file=sys.stderr)
            print("\n  [R] 直接恢复 (Resume) - 保留100%原始上下文", file=sys.stderr)
            print("      ⚡ 默认启用 --dangerously-skip-permissions", file=sys.stderr)
            print("  [C] 智能压缩 (Compress) - 小会话将直接恢复", file=sys.stderr)
            print("  [B] 返回列表 (Back)", file=sys.stderr)
            print("  [Q] 退出 (Quit)", file=sys.stderr)
        else:
            print(f"📊 会话大小: ≈{selected_info['tokens']:,} tokens(估算)", file=sys.stderr)
            print("\n  [R] 直接恢复 (Resume) - 保留100%原始上下文", file=sys.stderr)
            if selected_info['tokens'] > 200000:
                print(f"      ⚠  警告: 会话超过200k限制，可能无法完全加载", file=sys.stderr)
            print("      ⚡ 默认启用 --dangerously-skip-permissions", file=sys.stderr)
            print("  [C] 智能压缩 (Compress) - 提取关键信息", file=sys.stderr)
            print("      预计压缩后: ≈100,000 tokens(估算)", file=sys.stderr)
            print("      (保留前≈25k + 后≈75k tokens)", file=sys.stderr)
            print("  [B] 返回列表 (Back)", file=sys.stderr)
            print("  [Q] 退出 (Quit)", file=sys.stderr)
        
        
        # 询问用户选择
        print("\n" + "=" * 60, file=sys.stderr)
        
        # 根据会话类型调整提示
        if selected_info['tokens'] == 0 or selected_info['message_count'] <= 2:
            prompt = "\n请选择操作 [D/B/Q]: "
        else:
            prompt = "\n请选择操作 [R/C/B/Q]: "
        
        while True:
            try:
                choice = input(prompt).strip().lower()
                
                if choice == 'q':
                    print("\n👋 已退出", file=sys.stderr)
                    sys.exit(0)
                    
                elif choice == 'b':
                    # 返回会话选择（重新运行主函数）
                    print("\n🔄 返回会话列表...", file=sys.stderr)
                    # 重新调用main函数
                    sys.argv = ['ccdrc']
                    main()
                    return
                    
                elif choice == 'r':
                    # 直接恢复（对所有大小的会话都允许）
                    session_id = selected.stem
                    print(f"\n🚀 正在使用 --resume 恢复会话...", file=sys.stderr)
                    if selected_info['tokens'] > 200000:
                        print(f"⚠  警告: 会话包含 ≈{selected_info['tokens']:,} tokens(估算)，超过Claude的200k限制", file=sys.stderr)
                        print("   继续恢复可能会因为超出限制而失败", file=sys.stderr)
                    print(f"⚡ 已启用 --dangerously-skip-permissions 跳过权限检查", file=sys.stderr)
                    
                    # FIX: 使用os.system保持终端状态，确保token显示
                    import os
                    # 强制刷新所有缓冲区
                    sys.stdout.flush()
                    sys.stderr.flush()
                    # 添加--verbose确保token显示
                    cmd = f'claude --resume {session_id} --verbose --dangerously-skip-permissions'
                    exit_code = os.system(cmd)
                    sys.exit(exit_code >> 8)
                        
                elif choice == 'd' and (selected_info['tokens'] == 0 or selected_info['message_count'] <= 2):
                    # 删除空会话
                    print(f"\n🗑  正在删除空会话...", file=sys.stderr)
                    try:
                        selected.unlink()  # 删除文件
                        print("✅ 空会话已删除", file=sys.stderr)
                        print("\n🔄 返回会话列表...", file=sys.stderr)
                        sys.argv = ['ccdrc']
                        main()
                        return
                    except Exception as e:
                        print(f"❌ 删除失败: {e}", file=sys.stderr)
                        
                elif choice == 'c' and selected_info['tokens'] > 0:
                    # 用户选择压缩
                    if selected_info['tokens'] < 100000:
                        # <100k，直接恢复（压缩后结果一样）
                        session_id = selected.stem
                        print(f"\n✨ 会话较小（≈{selected_info['tokens']:,} tokens(估) < 100k），直接恢复", file=sys.stderr)
                        print(f"   （小会话压缩和恢复效果相同）", file=sys.stderr)
                        print(f"⚡ 已启用 --dangerously-skip-permissions 跳过权限检查", file=sys.stderr)
                        
                        # FIX: 使用os.system保持终端状态，确保token显示
                        import os
                        # 强制刷新所有缓冲区
                        sys.stdout.flush()
                        sys.stderr.flush()
                        # 添加--verbose确保token显示
                        cmd = f'claude --resume {session_id} --verbose --dangerously-skip-permissions'
                        exit_code = os.system(cmd)
                        sys.exit(exit_code >> 8)
                    else:
                        # >=100k，进行压缩
                        print(f"\n🗃  正在进行智能压缩...", file=sys.stderr)
                        # 交互模式下，压缩后自动发送给Claude
                        args.send = True
                        break  # 继续执行后续的压缩逻辑
                    
                else:
                    if selected_info['tokens'] == 0 or selected_info['message_count'] <= 2:
                        print("⚠  无效选择，请输入 D/B/Q", file=sys.stderr)
                    else:
                        print("⚠  无效选择，请输入 R/C/B/Q", file=sys.stderr)
                    
            except KeyboardInterrupt:
                print("\n\n👋 已退出", file=sys.stderr)
                sys.exit(0)
    
    # 解析会话（用户已经在交互界面选择了压缩，且tokens>=100k）
    if args.stats:
        print(f"\n📖 解析会话: {selected.name}", file=sys.stderr)
    
    messages = extractor.parse_session(selected)
    
    if not messages:
        print("❌ 会话文件为空或格式错误", file=sys.stderr)
        sys.exit(1)
    
    # 获取token数用于显示
    total_tokens = selected_info.get('tokens', 0)
    
    # 执行到这里说明用户选择了C且tokens>=100k，直接进行压缩
    print(f"\n⚠  正在压缩会话（≈{total_tokens:,} tokens估算）", file=sys.stderr)
    
    # 提取关键消息
    extracted, stats = extractor.extract_key_messages(messages)
    
    # 显示统计（交互模式下总是显示）
    print(f"\n📊 压缩统计:", file=sys.stderr)
    print(f"  原始: {stats['total_messages']}条消息, ≈{stats['total_tokens']:,} tokens(估)", file=sys.stderr)
    print(f"  压缩后: {stats['extracted_messages']}条消息, ≈{stats['extracted_tokens']:,} tokens(估)", file=sys.stderr)
    print(f"  压缩率: {stats['compression_ratio']:.1%}", file=sys.stderr)
    print(f"  使用{extractor.encoder.name}编码器，提取了≈{stats['extracted_tokens']}个token(估算)", file=sys.stderr)
    
    # 发送到Claude时需要确认（但交互模式选择后不需要）
    # 现在总是交互模式，所以不需要再次确认
    need_confirm = False
    
    if need_confirm:
        # 获取预览
        preview = extractor.get_preview(extracted, preview_lines=3)
        
        # 显示预览信息
        print("\n" + "=" * 60, file=sys.stderr)
        print("📋 会话预览", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f"\n📊 统计:", file=sys.stderr)
        print(f"  • 会话文件: {selected.name}", file=sys.stderr)
        print(f"  • 消息总数: {stats['extracted_messages']} 条", file=sys.stderr)
        print(f"  • Token总数: {stats['extracted_tokens']} tokens", file=sys.stderr)
        print(f"  • 压缩率: {stats['compression_ratio']:.1%}", file=sys.stderr)
        
        print(f"\n📝 开头内容（前{len(preview['head'])}条）:", file=sys.stderr)
        print(preview['head_text'], file=sys.stderr)
        
        if preview['total_messages'] > 6:
            print(f"\n  ... 省略 {preview['total_messages'] - 6} 条消息 ...", file=sys.stderr)
        
        print(f"\n📝 结尾内容（后{len(preview['tail'])}条）:", file=sys.stderr)
        print(preview['tail_text'], file=sys.stderr)
        
        print("\n" + "=" * 60, file=sys.stderr)
        
        # 询问用户确认
        while True:
            print("\n❓ 是否发送到Claude？", file=sys.stderr)
            print("  [Y] 是，发送", file=sys.stderr)
            print("  [N] 否，取消", file=sys.stderr)
            print("  [R] 重新选择会话", file=sys.stderr)
            
            try:
                choice = input("请选择 (Y/n/r): ").strip().lower()
                if choice == '' or choice == 'y':
                    # 继续发送
                    break
                elif choice == 'n':
                    print("\n❌ 已取消", file=sys.stderr)
                    sys.exit(0)
                elif choice == 'r':
                    # 重新选择会话
                    print("\n🔄 重新选择会话...", file=sys.stderr)
                    # 递归调用main（实际上应该重构为循环）
                    sys.argv = ['ccdrc-extract']
                    if args.send:
                        sys.argv.append('--send')
                    if args.stats:
                        sys.argv.append('--stats')
                    main()
                    return
                else:
                    print("⚠  请输入 Y、N 或 R", file=sys.stderr)
            except KeyboardInterrupt:
                print("\n\n❌ 已取消", file=sys.stderr)
                sys.exit(0)
    
    # 创建摘要
    summary = extractor.create_context_summary(extracted, stats)
    
    # 输出结果
    if args.output:
        if args.output == '/dev/stdout':
            print(summary)
        else:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(summary)
            print(f"✅ 已保存到: {args.output}", file=sys.stderr)
    elif args.send:
        # 通过管道发送到Claude
        # FIX: 使用os.system和临时文件保持终端状态
        import os
        import tempfile
        print("\n🚀 正在启动Claude...\n", file=sys.stderr)
        
        # 创建临时文件存储内容
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tf:
            tf.write(summary)
            temp_path = tf.name
        
        try:
            # 使用os.system确保终端状态正确传递，添加--verbose确保token显示
            exit_code = os.system(f'cat "{temp_path}" | claude --verbose --dangerously-skip-permissions')
            exit_code = exit_code >> 8  # 获取实际退出码
            
            # Claude已经退出，根据返回码判断
            if exit_code == 0:
                print("\n✅ Claude会话已结束", file=sys.stderr)
            else:
                print(f"\n⚠  Claude退出代码: {exit_code}", file=sys.stderr)
        finally:
            os.unlink(temp_path)
    else:
        print(summary)

if __name__ == '__main__':
    main()