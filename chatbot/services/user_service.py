"""
Module quản lý user và tích hợp với MongoDB.

Chức năng:
- Quản lý userID và session
- Tích hợp với MongoDB để lưu trữ conversations
- Đồng bộ hóa dữ liệu giữa memory và database
- Quản lý user context
"""

from __future__ import annotations

import uuid
from typing import Optional, Dict, List, Any
from datetime import datetime

from models.conversation import ConversationManager, Conversation
from db.mongodb_manager import get_mongodb_manager, is_mongodb_available


class UserManager:
    """Quản lý user và tích hợp với MongoDB."""
    
    def __init__(self, user_id: str):
        """
        Khởi tạo UserManager cho một user.
        
        Args:
            user_id: ID của user
        """
        self.user_id = user_id
        self.conversation_manager = ConversationManager()
        self.mongodb_available = is_mongodb_available()
        
        # Load conversations từ MongoDB nếu có
        if self.mongodb_available:
            self._load_user_conversations()
    
    def _load_user_conversations(self) -> None:
        """Tải conversations của user từ MongoDB."""
        mongodb_manager = get_mongodb_manager()
        if not mongodb_manager:
            return
        
        try:
            conversations = mongodb_manager.load_user_conversations(self.user_id)
            
            # Load vào conversation manager
            for conv in conversations:
                self.conversation_manager.conversations[conv.id] = conv
                
                # Set conversation active nếu cần
                if conv.is_active:
                    self.conversation_manager.current_conversation_id = conv.id
            
            print(f"👤 Đã tải {len(conversations)} conversations cho user {self.user_id}")
            
        except Exception as e:
            print(f"❌ Lỗi tải conversations cho user {self.user_id}: {e}")
    
    def _save_conversation(self, conversation: Conversation) -> bool:
        """Lưu conversation vào MongoDB."""
        print(f"[user_manager] _save_conversation called for conversation {conversation.id}")
        
        if not self.mongodb_available:
            print(f"[user_manager] ⚠️ MongoDB không khả dụng, không lưu")
            return True  # Không có MongoDB, coi như thành công
        
        mongodb_manager = get_mongodb_manager()
        if not mongodb_manager:
            print(f"[user_manager] ❌ Không có MongoDB manager")
            return False
        
        print(f"[user_manager] Đang gọi mongodb_manager.save_conversation...")
        result = mongodb_manager.save_conversation(self.user_id, conversation)
        print(f"[user_manager] MongoDB save_conversation result: {result}")
        
        return result
    
    def create_conversation(self, first_question: str) -> str:
        """
        Tạo cuộc hội thoại mới cho user.
        
        Args:
            first_question: Câu hỏi đầu tiên
            
        Returns:
            ID của conversation mới
        """
        # Tạo conversation trong manager
        conv_id = self.conversation_manager.create_conversation(first_question)
        conversation = self.conversation_manager.conversations[conv_id]
        
        # Lưu vào MongoDB
        self._save_conversation(conversation)
        
        print(f"👤 User {self.user_id}: Tạo conversation '{conversation.name}'")
        return conv_id
    
    def switch_conversation(self, conv_id: str) -> bool:
        """
        Chuyển sang conversation khác.
        
        Args:
            conv_id: ID của conversation
            
        Returns:
            True nếu chuyển thành công
        """
        success = self.conversation_manager.switch_conversation(conv_id)
        
        if success and self.mongodb_available:
            # Cập nhật trạng thái active trong MongoDB
            mongodb_manager = get_mongodb_manager()
            if mongodb_manager:
                mongodb_manager.update_conversation_active_status(
                    self.user_id, conv_id, True
                )
        
        return success
    
    def add_turn(self, question: str, answer: str) -> bool:
        """
        Thêm lượt hội thoại vào conversation hiện tại.
        
        Args:
            question: Câu hỏi
            answer: Câu trả lời
            
        Returns:
            True nếu thêm thành công
        """
        print(f"[user_manager] Đang thêm lượt hội thoại cho user {self.user_id}")
        print(f"[user_manager] MongoDB available: {self.mongodb_available}")
        
        success = self.conversation_manager.add_turn(question, answer)
        print(f"[user_manager] ConversationManager add_turn result: {success}")
        
        if success and self.mongodb_available:
            # Lưu conversation đã cập nhật vào MongoDB
            current_conv = self.conversation_manager.get_current_conversation()
            if current_conv:
                print(f"[user_manager] Đang lưu conversation {current_conv.id} vào MongoDB...")
                save_success = self._save_conversation(current_conv)
                print(f"[user_manager] MongoDB save result: {save_success}")
            else:
                print(f"[user_manager] ❌ Không có conversation hiện tại để lưu")
        elif not self.mongodb_available:
            print(f"[user_manager] ⚠️ MongoDB không khả dụng, chỉ lưu local")
        
        return success
    
    def get_current_conversation(self) -> Optional[Conversation]:
        """Lấy conversation hiện tại."""
        return self.conversation_manager.get_current_conversation()
    
    def get_conversation_list(self) -> List[Dict[str, Any]]:
        """Lấy danh sách conversations của user."""
        if self.mongodb_available:
            mongodb_manager = get_mongodb_manager()
            if mongodb_manager:
                return mongodb_manager.get_user_conversation_list(self.user_id)
        
        # Fallback về local data
        return self.conversation_manager.get_conversation_list()
    
    def delete_conversation(self, conv_id: str) -> bool:
        """
        Xóa conversation.
        
        Args:
            conv_id: ID của conversation
            
        Returns:
            True nếu xóa thành công
        """
        # Xóa từ conversation manager
        success = self.conversation_manager.delete_conversation(conv_id)
        
        if success and self.mongodb_available:
            # Xóa từ MongoDB
            mongodb_manager = get_mongodb_manager()
            if mongodb_manager:
                mongodb_manager.delete_conversation(self.user_id, conv_id)
        
        return success
    
    def rename_conversation(self, conv_id: str, new_name: str) -> bool:
        """
        Đổi tên conversation.
        
        Args:
            conv_id: ID của conversation
            new_name: Tên mới cho conversation
            
        Returns:
            True nếu đổi tên thành công
        """
        # Đổi tên trong conversation manager
        success = self.conversation_manager.rename_conversation(conv_id, new_name)
        
        if success and self.mongodb_available:
            # Cập nhật trong MongoDB
            mongodb_manager = get_mongodb_manager()
            if mongodb_manager:
                mongodb_manager.update_conversation_name(self.user_id, conv_id, new_name)
        
        return success
    
    def clear_current_memory(self) -> bool:
        """Xóa memory của conversation hiện tại."""
        success = self.conversation_manager.clear_current_memory()
        
        if success and self.mongodb_available:
            # Lưu conversation đã xóa memory vào MongoDB
            current_conv = self.conversation_manager.get_current_conversation()
            if current_conv:
                self._save_conversation(current_conv)
        
        return success
    
    def get_memory_summary(self) -> str:
        """Lấy tóm tắt memory của conversation hiện tại."""
        return self.conversation_manager.get_memory_summary()
    
    def get_memory_count(self) -> int:
        """Lấy số lượt hội thoại của conversation hiện tại."""
        return self.conversation_manager.get_memory_count()
    
    def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Lấy danh sách tin nhắn của một conversation cụ thể."""
        try:
            print(f"[user_manager] Đang lấy messages cho conversation {conversation_id}")
            print(f"[user_manager] Available conversations: {list(self.conversation_manager.conversations.keys())}")
            
            # Tìm conversation trong conversation manager
            if conversation_id in self.conversation_manager.conversations:
                conversation = self.conversation_manager.conversations[conversation_id]
                print(f"[user_manager] Tìm thấy conversation: {conversation.name}")
                print(f"[user_manager] Conversation turns count: {len(conversation.memory.conversation_history)}")
                
                messages = []
                
                # Convert conversation turns to message format
                for turn in conversation.memory.conversation_history:
                    print(f"[user_manager] Processing turn: {turn.question[:50]}...")
                    
                    # Add user message
                    messages.append({
                        "id": f"{turn.timestamp}_user",
                        "content": turn.question,
                        "role": "user",
                        "timestamp": turn.timestamp.isoformat(),
                        "isUser": True
                    })
                    
                    # Add bot message
                    messages.append({
                        "id": f"{turn.timestamp}_bot",
                        "content": turn.answer,
                        "role": "assistant", 
                        "timestamp": turn.timestamp.isoformat(),
                        "isUser": False
                    })
                
                print(f"[user_manager] Generated {len(messages)} messages")
                return messages
            else:
                print(f"[user_manager] ❌ Không tìm thấy conversation {conversation_id}")
                print(f"[user_manager] Available conversations: {list(self.conversation_manager.conversations.keys())}")
                return []
                
        except Exception as e:
            print(f"[user_manager] ❌ Lỗi lấy messages của conversation {conversation_id}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_current_conversation_info(self) -> Dict[str, Any]:
        """Lấy thông tin conversation hiện tại."""
        return self.conversation_manager.get_current_conversation_info()
    
    def sync_to_database(self) -> bool:
        """
        Đồng bộ tất cả conversations hiện tại vào database.
        
        Returns:
            True nếu đồng bộ thành công
        """
        if not self.mongodb_available:
            return True
        
        try:
            mongodb_manager = get_mongodb_manager()
            if not mongodb_manager:
                return False
            
            # Lưu tất cả conversations
            for conv in self.conversation_manager.conversations.values():
                if not mongodb_manager.save_conversation(self.user_id, conv):
                    return False
            
            print(f"🔄 Đã đồng bộ {len(self.conversation_manager.conversations)} conversations cho user {self.user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi đồng bộ database: {e}")
            return False


class UserSessionManager:
    """Quản lý sessions của nhiều users."""
    
    def __init__(self):
        """Khởi tạo session manager."""
        self.user_sessions: Dict[str, UserManager] = {}
    
    def get_user_manager(self, user_id: str) -> UserManager:
        """
        Lấy UserManager cho user, tạo mới nếu chưa có.
        
        Args:
            user_id: ID của user
            
        Returns:
            UserManager cho user
        """
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = UserManager(user_id)
            print(f"👤 Tạo session mới cho user: {user_id}")
        
        return self.user_sessions[user_id]
    
    def remove_user_session(self, user_id: str) -> bool:
        """
        Xóa session của user.
        
        Args:
            user_id: ID của user
            
        Returns:
            True nếu xóa thành công
        """
        if user_id in self.user_sessions:
            # Đồng bộ dữ liệu trước khi xóa
            self.user_sessions[user_id].sync_to_database()
            del self.user_sessions[user_id]
            print(f"👤 Đã xóa session của user: {user_id}")
            return True
        return False
    
    def get_all_users(self) -> List[str]:
        """Lấy danh sách tất cả users đang active."""
        return list(self.user_sessions.keys())
    
    def sync_all_users(self) -> bool:
        """
        Đồng bộ tất cả users vào database.
        
        Returns:
            True nếu đồng bộ thành công
        """
        try:
            for user_manager in self.user_sessions.values():
                if not user_manager.sync_to_database():
                    return False
            return True
        except Exception as e:
            print(f"❌ Lỗi đồng bộ tất cả users: {e}")
            return False


# Global session manager
_session_manager: Optional[UserSessionManager] = None


def get_session_manager() -> UserSessionManager:
    """Lấy global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = UserSessionManager()
    return _session_manager


def get_user_manager(user_id: str) -> UserManager:
    """Lấy UserManager cho user."""
    return get_session_manager().get_user_manager(user_id)


def generate_user_id() -> str:
    """Tạo user ID mới."""
    return f"user_{uuid.uuid4().hex[:8]}"



