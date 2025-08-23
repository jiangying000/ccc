def binary_search_truncate(self, content: str, target_tokens: int) -> str:
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

def extract_key_messages_improved(self, messages: List[Dict]) -> Tuple[List[Dict], Dict]:
    """改进的智能提取 - 使用精确切割确保达到100k"""
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
    FRONT_TOKENS = 25000
    BACK_TOKENS = 75000
    
    front_messages = []
    back_messages = []
    
    # 1. 提取前25k tokens（使用精确切割）
    front_token_count = 0
    for i, (msg, content, tokens) in enumerate(message_tokens):
        if tokens == 0:
            continue
            
        if front_token_count + tokens <= FRONT_TOKENS:
            # 完整添加
            front_messages.append(msg)
            front_token_count += tokens
        else:
            # 需要精确切割
            remaining_tokens = FRONT_TOKENS - front_token_count
            if remaining_tokens > 100:
                # 使用二分查找精确切割
                truncated_content = self.binary_search_truncate(content, remaining_tokens)
                
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
                # 计算实际添加的tokens
                front_token_count += self.count_tokens(truncated_content)
            break
    
    # 2. 提取后75k tokens（从后往前，精确切割）
    back_token_count = 0
    temp_back = []
    front_msg_set = set(id(m) for m in front_messages)
    
    for i, (msg, content, tokens) in enumerate(reversed(message_tokens)):
        if tokens == 0:
            continue
        if id(msg) in front_msg_set:
            continue
            
        if back_token_count + tokens <= BACK_TOKENS:
            # 完整添加
            temp_back.append(msg)
            back_token_count += tokens
        else:
            # 需要精确切割（从后面切）
            remaining_tokens = BACK_TOKENS - back_token_count
            if remaining_tokens > 100:
                # 使用二分查找，但是从后面切
                # 先反转内容，切割，再反转回来
                reversed_content = content[::-1]
                truncated_reversed = self.binary_search_truncate(reversed_content, remaining_tokens)
                truncated_content = truncated_reversed[::-1]
                
                # 创建切割后的消息
                truncated_msg = msg.copy()
                truncated_content = "[...前面内容已省略...]\n\n" + truncated_content
                
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
                # 计算实际添加的tokens
                back_token_count += self.count_tokens(truncated_content)
            break
    
    # 反转恢复顺序
    back_messages = list(reversed(temp_back))
    
    # 合并消息
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
    
    stats['extracted_messages'] = len(extracted)
    stats['extracted_tokens'] = actual_tokens
    
    if stats['total_tokens'] > 0:
        stats['compression_ratio'] = 1 - (stats['extracted_tokens'] / stats['total_tokens'])
    
    return extracted, stats