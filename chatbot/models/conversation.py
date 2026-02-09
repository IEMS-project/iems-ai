"""
Module quản lý nhiều cuộc hội thoại với tên tự động.

Chức năng:
- Tạo và quản lý nhiều cuộc hội thoại
- Đặt tên tự động dựa trên câu hỏi đầu tiên
- Chuyển đổi giữa các cuộc hội thoại
- Lưu trữ và khôi phục cuộc hội thoại
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

from models.conversation_memory import ConversationMemory, ConversationTurn


@dataclass
class Conversation:
    """Một cuộc hội thoại với tên và memory."""
    id: str
    name: str
    created_at: datetime
    memory: ConversationMemory
    is_active: bool = False
    
    def to_dict(self) -> Dict:
        """Chuyển đổi thành dictionary để lưu trữ."""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
            "memory": self.memory.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Conversation":
        """Tạo Conversation từ dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            created_at=datetime.fromisoformat(data["created_at"]),
            memory=ConversationMemory.from_dict(data["memory"]),
            is_active=data.get("is_active", False)
        )


class ConversationManager:
    """Quản lý nhiều cuộc hội thoại với tên tự động."""
    
    def __init__(self, max_conversations: int = 10, max_turns_per_conversation: int = 10):
        """
        Khởi tạo conversation manager.
        
        Args:
            max_conversations: Số lượng cuộc hội thoại tối đa
            max_turns_per_conversation: Số lượt hội thoại tối đa mỗi cuộc hội thoại
        """
        self.max_conversations = max_conversations
        self.max_turns_per_conversation = max_turns_per_conversation
        self.conversations: Dict[str, Conversation] = {}
        self.current_conversation_id: Optional[str] = None
    
    def _generate_conversation_name(self, first_question: str) -> str:
        """
        Tạo tên cuộc hội thoại từ câu hỏi đầu tiên.
        
        Args:
            first_question: Câu hỏi đầu tiên của cuộc hội thoại
            
        Returns:
            Tên cuộc hội thoại được tạo
        """
        # Làm sạch câu hỏi
        cleaned = re.sub(r'[^\w\s]', '', first_question.lower())
        words = cleaned.split()
        
        # Lấy 3-5 từ đầu tiên
        if len(words) <= 3:
            name = " ".join(words)
        else:
            name = " ".join(words[:4])
        
        # Giới hạn độ dài
        if len(name) > 30:
            name = name[:27] + "..."
        
        # Thêm timestamp để tránh trùng lặp
        timestamp = datetime.now().strftime("%H:%M")
        return f"{name} ({timestamp})"
    
    def _generate_conversation_id(self) -> str:
        """Tạo ID duy nhất cho cuộc hội thoại."""
        return f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def create_conversation(self, first_question: str) -> str:
        """
        Tạo cuộc hội thoại mới.
        
        Args:
            first_question: Câu hỏi đầu tiên của cuộc hội thoại
            
        Returns:
            ID của cuộc hội thoại mới
        """
        # Tạo tên tự động
        name = self._generate_conversation_name(first_question)
        conv_id = self._generate_conversation_id()
        
        # Tạo cuộc hội thoại mới
        conversation = Conversation(
            id=conv_id,
            name=name,
            created_at=datetime.now(),
            memory=ConversationMemory(max_turns=self.max_turns_per_conversation),
            is_active=True
        )
        
        # Deactivate cuộc hội thoại hiện tại
        if self.current_conversation_id:
            self.conversations[self.current_conversation_id].is_active = False
        
        # Thêm cuộc hội thoại mới
        self.conversations[conv_id] = conversation
        self.current_conversation_id = conv_id
        
        # Giới hạn số lượng cuộc hội thoại
        if len(self.conversations) > self.max_conversations:
            self._cleanup_old_conversations()
        
        return conv_id
    
    def switch_conversation(self, conv_id: str) -> bool:
        """
        Chuyển sang cuộc hội thoại khác.
        
        Args:
            conv_id: ID của cuộc hội thoại
            
        Returns:
            True nếu chuyển thành công, False nếu không tìm thấy
        """
        if conv_id not in self.conversations:
            return False
        
        # Deactivate cuộc hội thoại hiện tại
        if self.current_conversation_id:
            self.conversations[self.current_conversation_id].is_active = False
        
        # Activate cuộc hội thoại mới
        self.conversations[conv_id].is_active = True
        self.current_conversation_id = conv_id
        
        return True
    
    def get_current_conversation(self) -> Optional[Conversation]:
        """Lấy cuộc hội thoại hiện tại."""
        if self.current_conversation_id:
            return self.conversations.get(self.current_conversation_id)
        return None
    
    def get_conversation_list(self) -> List[Dict]:
        """Lấy danh sách tất cả cuộc hội thoại."""
        conversations = []
        for conv in self.conversations.values():
            conversations.append({
                "id": conv.id,
                "name": conv.name,
                "created_at": conv.created_at.strftime("%Y-%m-%d %H:%M"),
                "turn_count": conv.memory.get_history_count(),
                "is_active": conv.is_active
            })
        return sorted(conversations, key=lambda x: x["created_at"], reverse=True)
    
    def delete_conversation(self, conv_id: str) -> bool:
        """
        Xóa cuộc hội thoại.
        
        Args:
            conv_id: ID của cuộc hội thoại
            
        Returns:
            True nếu xóa thành công, False nếu không tìm thấy
        """
        if conv_id not in self.conversations:
            return False
        
        # Nếu đang xóa cuộc hội thoại hiện tại, chuyển sang cuộc hội thoại khác
        if self.current_conversation_id == conv_id:
            remaining_conversations = [c for c in self.conversations.values() if c.id != conv_id]
            if remaining_conversations:
                # Chuyển sang cuộc hội thoại gần nhất
                latest = max(remaining_conversations, key=lambda x: x.created_at)
                self.switch_conversation(latest.id)
            else:
                self.current_conversation_id = None
        
        del self.conversations[conv_id]
        return True
    
    def rename_conversation(self, conv_id: str, new_name: str) -> bool:
        """
        Đổi tên cuộc hội thoại.
        
        Args:
            conv_id: ID của cuộc hội thoại
            new_name: Tên mới cho cuộc hội thoại
            
        Returns:
            True nếu đổi tên thành công, False nếu không tìm thấy
        """
        if conv_id not in self.conversations:
            return False
        
        self.conversations[conv_id].name = new_name
        return True
    
    def _cleanup_old_conversations(self):
        """Xóa các cuộc hội thoại cũ nhất."""
        # Sắp xếp theo thời gian tạo (cũ nhất trước)
        sorted_conversations = sorted(
            self.conversations.values(),
            key=lambda x: x.created_at
        )
        
        # Xóa cuộc hội thoại cũ nhất (trừ cuộc hội thoại hiện tại)
        for conv in sorted_conversations:
            if conv.id != self.current_conversation_id:
                del self.conversations[conv.id]
                break
    
    def get_memory_summary(self) -> str:
        """Lấy tóm tắt memory của cuộc hội thoại hiện tại."""
        current = self.get_current_conversation()
        if current:
            return current.memory.get_conversation_summary()
        return "Chưa có cuộc hội thoại nào."
    
    def get_memory_count(self) -> int:
        """Lấy số lượt hội thoại của cuộc hội thoại hiện tại."""
        current = self.get_current_conversation()
        if current:
            return current.memory.get_history_count()
        return 0
    
    def get_current_conversation_info(self) -> Optional[Dict]:
        """Lấy thông tin cuộc hội thoại hiện tại."""
        current = self.get_current_conversation()
        if current:
            return {
                "id": current.id,
                "name": current.name,
                "created_at": current.created_at.strftime("%Y-%m-%d %H:%M"),
                "turn_count": current.memory.get_history_count(),
                "is_active": current.is_active
            }
        return None
    
    def add_turn(self, question: str, answer: str) -> bool:
        """
        Thêm lượt hội thoại vào cuộc hội thoại hiện tại.
        
        Args:
            question: Câu hỏi
            answer: Câu trả lời
            
        Returns:
            True nếu thêm thành công, False nếu không có cuộc hội thoại hiện tại
        """
        current = self.get_current_conversation()
        if current:
            current.memory.add_turn(question, answer)
            return True
        return False
    
    def clear_current_memory(self) -> bool:
        """Xóa memory của cuộc hội thoại hiện tại."""
        current = self.get_current_conversation()
        if current:
            current.memory.clear()
            return True
        return False
    
    def to_dict(self) -> Dict:
        """Chuyển đổi manager thành dictionary để lưu trữ."""
        return {
            "max_conversations": self.max_conversations,
            "max_turns_per_conversation": self.max_turns_per_conversation,
            "current_conversation_id": self.current_conversation_id,
            "conversations": {conv_id: conv.to_dict() for conv_id, conv in self.conversations.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ConversationManager":
        """Tạo ConversationManager từ dictionary."""
        manager = cls(
            max_conversations=data.get("max_conversations", 10),
            max_turns_per_conversation=data.get("max_turns_per_conversation", 10)
        )
        manager.current_conversation_id = data.get("current_conversation_id")
        
        conversations_data = data.get("conversations", {})
        for conv_id, conv_data in conversations_data.items():
            manager.conversations[conv_id] = Conversation.from_dict(conv_data)
        
        return manager
