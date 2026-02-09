"""
Module quản lý trí nhớ conversation cho chatbot.

Chức năng:
- Lưu trữ lịch sử conversation (câu hỏi và câu trả lời)
- Quản lý độ dài conversation để tránh vượt quá giới hạn token
- Cung cấp context conversation cho generator
"""

from __future__ import annotations

from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConversationTurn:
    """Một lượt hội thoại gồm câu hỏi và câu trả lời."""
    question: str
    answer: str
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi thành dictionary để lưu trữ."""
        return {
            "question": self.question,
            "answer": self.answer,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationTurn":
        """Tạo ConversationTurn từ dictionary."""
        return cls(
            question=data["question"],
            answer=data["answer"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


class ConversationMemory:
    """Quản lý trí nhớ conversation cho chatbot."""
    
    def __init__(self, max_turns: int = 10):
        """
        Khởi tạo conversation memory.
        
        Args:
            max_turns: Số lượt hội thoại tối đa để lưu trữ (mặc định 10)
        """
        self.max_turns = max_turns
        self.conversation_history: List[ConversationTurn] = []
    
    def add_turn(self, question: str, answer: str) -> None:
        """
        Thêm một lượt hội thoại vào memory.
        
        Args:
            question: Câu hỏi của người dùng
            answer: Câu trả lời của chatbot
        """
        turn = ConversationTurn(
            question=question,
            answer=answer,
            timestamp=datetime.now()
        )
        
        self.conversation_history.append(turn)
        
        # Giữ chỉ số lượng conversation gần nhất
        if len(self.conversation_history) > self.max_turns:
            self.conversation_history = self.conversation_history[-self.max_turns:]
    
    def get_recent_context(self, num_turns: int = 5) -> str:
        """
        Lấy context từ các lượt hội thoại gần nhất.
        
        Args:
            num_turns: Số lượt hội thoại gần nhất để lấy (mặc định 5)
            
        Returns:
            Chuỗi context conversation
        """
        if not self.conversation_history:
            return ""
        
        # Lấy các lượt gần nhất
        recent_turns = self.conversation_history[-num_turns:]
        
        context_parts = []
        for turn in recent_turns:
            context_parts.append(f"Q: {turn.question}")
            context_parts.append(f"A: {turn.answer}")
            context_parts.append("")  # Dòng trống để phân cách
        
        return "\n".join(context_parts).strip()
    
    def get_conversation_summary(self) -> str:
        """
        Lấy tóm tắt conversation hiện tại.
        
        Returns:
            Chuỗi tóm tắt conversation
        """
        if not self.conversation_history:
            return "Chưa có lịch sử hội thoại."
        
        total_turns = len(self.conversation_history)
        first_turn = self.conversation_history[0]
        last_turn = self.conversation_history[-1]
        
        return f"Đã có {total_turns} lượt hội thoại từ {first_turn.timestamp.strftime('%H:%M')} đến {last_turn.timestamp.strftime('%H:%M')}"
    
    def clear(self) -> None:
        """Xóa toàn bộ lịch sử conversation."""
        self.conversation_history.clear()
    
    def get_history_count(self) -> int:
        """Lấy số lượng lượt hội thoại đã lưu."""
        return len(self.conversation_history)
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi memory thành dictionary để lưu trữ."""
        return {
            "max_turns": self.max_turns,
            "conversation_history": [turn.to_dict() for turn in self.conversation_history]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMemory":
        """Tạo ConversationMemory từ dictionary."""
        memory = cls(max_turns=data.get("max_turns", 10))
        memory.conversation_history = [
            ConversationTurn.from_dict(turn_data) 
            for turn_data in data.get("conversation_history", [])
        ]
        return memory
