"""
Module quản lý prompts từ file text.

Chức năng:
- Load system prompt và user prompt template từ file
- Cung cấp hàm để format prompt với context và question
"""

import os
from typing import Dict


PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


def load_prompt_file(filename: str) -> str:
    """Load nội dung prompt từ file text với UTF-8 encoding."""
    filepath = os.path.join(PROMPTS_DIR, filename)
    try:
        # Thử UTF-8 trước, nếu không được thì fallback về cp1252
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='cp1252') as f:
                return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Không tìm thấy file prompt: {filepath}")


def get_system_prompt() -> str:
    """Lấy system prompt từ file."""
    return load_prompt_file("system_prompt.txt")


def get_user_prompt_template() -> str:
    """Lấy user prompt template từ file."""
    return load_prompt_file("user_prompt_template.txt")


def format_user_prompt(context: str, question: str, conversation_history: str = "") -> str:
    """Format user prompt với context, question và conversation history."""
    template = get_user_prompt_template()
    
    # Format template với tất cả các placeholder
    return template.format(
        context=context, 
        question=question, 
        conversation_history=conversation_history
    )


def get_prompts() -> Dict[str, str]:
    """Lấy tất cả prompts dưới dạng dictionary."""
    return {
        "system": get_system_prompt(),
        "user_template": get_user_prompt_template(),
    }
