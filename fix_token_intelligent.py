#!/usr/bin/env python3
"""
智能token计算 - 根据会话类型自适应
"""

def create_intelligent_fix():
    """生成智能的token计算修复"""
    
    fix_code = '''
# 修改 ccdrc/extractor.py 的 get_session_info 方法

def get_session_info(self, session_path: Path) -> Dict:
    """获取会话的详细信息 - 智能版"""
    # ... 前面代码保持不变 ...
    
    try:
        messages = self.parse_session(session_path)
        info['message_count'] = len(messages)
        
        # 智能token计算 - 根据会话类型自适应
        total_json_chars = 0
        text_content_chars = 0
        tool_use_count = 0
        summary_chars = 0
        
        for msg in messages:
            msg_type = msg.get('type', '')
            
            # 统计工具调用
            if 'tool_use' in str(msg):
                tool_use_count += 1
            
            # 统计summary（这些通常很大）
            if msg_type == 'summary':
                summary_text = msg.get('summary', '')
                summary_chars += len(summary_text)
            
            # 计算JSON大小
            try:
                msg_json = json.dumps(msg, ensure_ascii=False, separators=(',', ':'))
                total_json_chars += len(msg_json)
            except:
                total_json_chars += 1000
            
            # 提取文本内容
            content = self._get_message_content(msg)
            if content:
                text_content_chars += len(content)
        
        # 智能计算策略
        if tool_use_count > len(messages) * 0.3:
            # 工具调用密集型会话（>30%是工具调用）
            # Claude实际上对工具调用有优化，不会完全按JSON计算
            # 使用更保守的估算
            
            # 工具调用的有效负载约占50%（其余是模板）
            effective_json = total_json_chars * 0.5
            total_tokens = int(effective_json / 4)  # 平均4字符/token
            
        elif summary_chars > total_json_chars * 0.5:
            # Summary主导型会话（summary占>50%）
            # Summary是压缩后的内容，token密度高
            
            summary_tokens = summary_chars / 3  # Summary密度高
            other_tokens = (total_json_chars - summary_chars) / 4
            total_tokens = int(summary_tokens + other_tokens)
            
        else:
            # 常规对话型会话
            # 使用标准计算方法
            
            text_tokens = text_content_chars / 3.5
            structure_chars = total_json_chars - text_content_chars
            structure_tokens = structure_chars / 2.5
            total_tokens = int((text_tokens + structure_tokens) * 1.09)
        
        # 基于文件大小的合理性检查
        # 经验值：1KB通常在 50-150 tokens之间
        file_size_kb = session_path.stat().st_size / 1024
        min_tokens = int(file_size_kb * 50)
        max_tokens = int(file_size_kb * 150)
        
        # 限制在合理范围内
        if total_tokens < min_tokens:
            total_tokens = min_tokens
        elif total_tokens > max_tokens:
            # 工具调用密集的会话可能确实很大，但要有上限
            total_tokens = max_tokens
        
        info['tokens'] = total_tokens
        
        # 调试信息
        info['token_debug'] = {
            'tool_use_count': tool_use_count,
            'tool_use_ratio': tool_use_count / len(messages) if messages else 0,
            'text_ratio': text_content_chars / total_json_chars if total_json_chars else 0,
            'calculation_method': 'tool_heavy' if tool_use_count > len(messages) * 0.3 
                                  else 'summary' if summary_chars > total_json_chars * 0.5
                                  else 'standard'
        }
'''
    
    print("智能Token计算方案")
    print("="*60)
    print("""
问题分析：
1. 工具调用密集会话：JSON巨大但实际token没那么多
2. Summary会话：压缩内容，token密度高
3. 常规对话：标准计算即可

解决方案：
1. 检测会话类型（工具调用比例）
2. 不同类型用不同算法
3. 添加合理性上下限（50-150 tokens/KB）
""")
    
    return fix_code

if __name__ == "__main__":
    fix = create_intelligent_fix()
    print(fix)