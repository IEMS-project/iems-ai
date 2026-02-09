"""
Module quản lý database MongoDB cho lưu trữ lịch sử hội thoại.

Chức năng:
- Kết nối MongoDB với connection string
- Lưu trữ và truy xuất lịch sử hội thoại theo userID
- Quản lý conversations và turns
- Đồng bộ hóa dữ liệu giữa memory và database
"""

from __future__ import annotations

import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, DuplicateKeyError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    print("⚠️ PyMongo không được cài đặt. Chạy: pip install pymongo")

from models.conversation_memory import ConversationMemory, ConversationTurn
from models.conversation import Conversation, ConversationManager


@dataclass
class UserConversation:
    """Cấu trúc dữ liệu cho conversation trong MongoDB."""
    user_id: str
    conversation_id: str
    name: str
    created_at: datetime
    updated_at: datetime
    turns: List[Dict[str, Any]]
    is_active: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi thành dictionary để lưu vào MongoDB."""
        return {
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "turns": self.turns,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserConversation":
        """Tạo UserConversation từ dictionary từ MongoDB."""
        return cls(
            user_id=data["user_id"],
            conversation_id=data["conversation_id"],
            name=data["name"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            turns=data["turns"],
            is_active=data.get("is_active", False)
        )


class MongoDBManager:
    """Quản lý kết nối và thao tác với MongoDB."""
    
    def __init__(self, connection_string: str, database_name: str = "iems_chatbot"):
        """
        Khởi tạo MongoDB manager.
        
        Args:
            connection_string: Connection string MongoDB
            database_name: Tên database
        """
        if not MONGODB_AVAILABLE:
            raise ImportError("PyMongo không được cài đặt. Chạy: pip install pymongo")
        
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[MongoClient] = None
        self.db = None
        self.conversations_collection = None
        
        # Kết nối database
        self._connect()
    
    def _connect(self) -> bool:
        """Kết nối đến MongoDB."""
        try:
            self.client = MongoClient(self.connection_string)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[self.database_name]
            self.conversations_collection = self.db["conversations"]
            
            # Tạo index cho performance
            self.conversations_collection.create_index([("user_id", 1), ("conversation_id", 1)], unique=True)
            self.conversations_collection.create_index([("user_id", 1), ("is_active", 1)])
            
            print(f"✅ Đã kết nối MongoDB: {self.database_name}")
            return True
        except ConnectionFailure as e:
            print(f"❌ Lỗi kết nối MongoDB: {e}")
            return False
        except Exception as e:
            print(f"❌ Lỗi không xác định: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Kiểm tra kết nối MongoDB."""
        try:
            if self.client:
                self.client.admin.command('ping')
                return True
        except:
            pass
        return False
    
    def save_conversation(self, user_id: str, conversation: Conversation) -> bool:
        """
        Lưu conversation vào MongoDB.
        
        Args:
            user_id: ID của user
            conversation: Conversation object
            
        Returns:
            True nếu lưu thành công, False nếu có lỗi
        """
        try:
            print(f"[mongodb] Đang lưu conversation {conversation.id} cho user {user_id}")
            print(f"[mongodb] Conversation name: {conversation.name}")
            print(f"[mongodb] Conversation turns count: {len(conversation.memory.conversation_history)}")
            
            # Chuyển đổi conversation thành format MongoDB
            turns_data = []
            for turn in conversation.memory.conversation_history:
                turns_data.append(turn.to_dict())
            
            print(f"[mongodb] Turns data length: {len(turns_data)}")
            
            user_conv = UserConversation(
                user_id=user_id,
                conversation_id=conversation.id,
                name=conversation.name,
                created_at=conversation.created_at,
                updated_at=datetime.now(),
                turns=turns_data,
                is_active=conversation.is_active
            )
            
            print(f"[mongodb] Đang upsert vào collection...")
            
            # Upsert (insert hoặc update)
            result = self.conversations_collection.replace_one(
                {"user_id": user_id, "conversation_id": conversation.id},
                user_conv.to_dict(),
                upsert=True
            )
            
            print(f"[mongodb] Upsert result: matched={result.matched_count}, modified={result.modified_count}, upserted_id={result.upserted_id}")
            print(f"💾 Đã lưu conversation {conversation.id} cho user {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi lưu conversation: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_user_conversations(self, user_id: str) -> List[Conversation]:
        """
        Tải tất cả conversations của user từ MongoDB.
        
        Args:
            user_id: ID của user
            
        Returns:
            List các Conversation objects
        """
        try:
            conversations = []
            cursor = self.conversations_collection.find({"user_id": user_id})
            
            for doc in cursor:
                # Tạo ConversationMemory từ turns
                memory = ConversationMemory()
                for turn_data in doc["turns"]:
                    turn = ConversationTurn.from_dict(turn_data)
                    memory.conversation_history.append(turn)
                
                # Tạo Conversation object
                conversation = Conversation(
                    id=doc["conversation_id"],
                    name=doc["name"],
                    created_at=doc["created_at"],
                    memory=memory,
                    is_active=doc.get("is_active", False)
                )
                conversations.append(conversation)
            
            print(f"📥 Đã tải {len(conversations)} conversations cho user {user_id}")
            return conversations
            
        except Exception as e:
            print(f"❌ Lỗi tải conversations: {e}")
            return []
    
    def load_conversation_by_id(self, user_id: str, conversation_id: str) -> Optional[UserConversation]:
        """
        Tải một conversation cụ thể từ MongoDB.
        
        Args:
            user_id: ID của user
            conversation_id: ID của conversation
            
        Returns:
            UserConversation object hoặc None nếu không tìm thấy
        """
        try:
            doc = self.conversations_collection.find_one({
                "user_id": user_id,
                "conversation_id": conversation_id
            })
            
            if doc:
                return UserConversation.from_dict(doc)
            else:
                print(f"❌ Không tìm thấy conversation {conversation_id} của user {user_id}")
                return None
                
        except Exception as e:
            print(f"❌ Lỗi tải conversation: {e}")
            return None
    
    def get_active_conversation(self, user_id: str) -> Optional[Conversation]:
        """
        Lấy conversation đang active của user.
        
        Args:
            user_id: ID của user
            
        Returns:
            Conversation đang active hoặc None
        """
        try:
            doc = self.conversations_collection.find_one({
                "user_id": user_id,
                "is_active": True
            })
            
            if doc:
                # Tạo ConversationMemory từ turns
                memory = ConversationMemory()
                for turn_data in doc["turns"]:
                    turn = ConversationTurn.from_dict(turn_data)
                    memory.conversation_history.append(turn)
                
                # Tạo Conversation object
                conversation = Conversation(
                    id=doc["conversation_id"],
                    name=doc["name"],
                    created_at=doc["created_at"],
                    memory=memory,
                    is_active=doc.get("is_active", False)
                )
                
                print(f"📌 Đã tải conversation active: {conversation.name}")
                return conversation
            
            return None
            
        except Exception as e:
            print(f"❌ Lỗi tải conversation active: {e}")
            return None
    
    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        """
        Xóa conversation của user.
        
        Args:
            user_id: ID của user
            conversation_id: ID của conversation
            
        Returns:
            True nếu xóa thành công, False nếu có lỗi
        """
        try:
            result = self.conversations_collection.delete_one({
                "user_id": user_id,
                "conversation_id": conversation_id
            })
            
            if result.deleted_count > 0:
                print(f"🗑️ Đã xóa conversation {conversation_id} của user {user_id}")
                return True
            else:
                print(f"❌ Không tìm thấy conversation {conversation_id} của user {user_id}")
                return False
                
        except Exception as e:
            print(f"❌ Lỗi xóa conversation: {e}")
            return False
    
    def update_conversation_name(self, user_id: str, conversation_id: str, new_name: str) -> bool:
        """
        Cập nhật tên conversation của user.
        
        Args:
            user_id: ID của user
            conversation_id: ID của conversation
            new_name: Tên mới cho conversation
            
        Returns:
            True nếu cập nhật thành công, False nếu có lỗi
        """
        try:
            result = self.conversations_collection.update_one(
                {
                    "user_id": user_id,
                    "conversation_id": conversation_id
                },
                {
                    "$set": {
                        "name": new_name,
                        "updated_at": datetime.now()
                    }
                }
            )
            
            if result.modified_count > 0:
                print(f"✏️ Đã đổi tên conversation {conversation_id} thành '{new_name}' của user {user_id}")
                return True
            else:
                print(f"❌ Không tìm thấy conversation {conversation_id} của user {user_id}")
                return False
                
        except Exception as e:
            print(f"❌ Lỗi đổi tên conversation: {e}")
            return False
    
    def update_conversation_active_status(self, user_id: str, conversation_id: str, is_active: bool) -> bool:
        """
        Cập nhật trạng thái active của conversation.
        
        Args:
            user_id: ID của user
            conversation_id: ID của conversation
            is_active: Trạng thái active mới
            
        Returns:
            True nếu cập nhật thành công, False nếu có lỗi
        """
        try:
            # Set tất cả conversations của user thành inactive
            if is_active:
                self.conversations_collection.update_many(
                    {"user_id": user_id},
                    {"$set": {"is_active": False}}
                )
            
            # Set conversation cụ thể thành active/inactive
            result = self.conversations_collection.update_one(
                {"user_id": user_id, "conversation_id": conversation_id},
                {"$set": {"is_active": is_active, "updated_at": datetime.now()}}
            )
            
            if result.modified_count > 0:
                status = "active" if is_active else "inactive"
                print(f"🔄 Đã cập nhật conversation {conversation_id} thành {status}")
                return True
            else:
                print(f"❌ Không tìm thấy conversation {conversation_id} của user {user_id}")
                return False
                
        except Exception as e:
            print(f"❌ Lỗi cập nhật trạng thái conversation: {e}")
            return False
    
    def get_user_conversation_list(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Lấy danh sách conversations của user.
        
        Args:
            user_id: ID của user
            
        Returns:
            List các conversation info
        """
        try:
            conversations = []
            cursor = self.conversations_collection.find(
                {"user_id": user_id},
                {"conversation_id": 1, "name": 1, "created_at": 1, "is_active": 1, "turns": 1}
            ).sort("created_at", -1)
            
            for doc in cursor:
                conversations.append({
                    "id": doc["conversation_id"],
                    "name": doc["name"],
                    "created_at": doc["created_at"].strftime("%Y-%m-%d %H:%M"),
                    "turn_count": len(doc["turns"]),
                    "is_active": doc.get("is_active", False)
                })
            
            return conversations
            
        except Exception as e:
            print(f"❌ Lỗi lấy danh sách conversations: {e}")
            return []
    
    def close_connection(self):
        """Đóng kết nối MongoDB."""
        if self.client:
            self.client.close()
            print("🔌 Đã đóng kết nối MongoDB")


# Global MongoDB manager instance
_mongodb_manager: Optional[MongoDBManager] = None


def get_mongodb_manager() -> Optional[MongoDBManager]:
    """Lấy global MongoDB manager instance."""
    return _mongodb_manager


def initialize_mongodb(connection_string: str, database_name: str = "iems_chatbot") -> bool:
    """
    Khởi tạo MongoDB connection.
    
    Args:
        connection_string: MongoDB connection string
        database_name: Tên database
        
    Returns:
        True nếu khởi tạo thành công, False nếu có lỗi
    """
    global _mongodb_manager
    
    try:
        _mongodb_manager = MongoDBManager(connection_string, database_name)
        if _mongodb_manager.is_connected():
            return True
        else:
            _mongodb_manager = None
            return False
    except Exception as e:
        print(f"❌ Lỗi khởi tạo MongoDB: {e}")
        return False


def is_mongodb_available() -> bool:
    """Kiểm tra MongoDB có sẵn sàng không."""
    return _mongodb_manager is not None and _mongodb_manager.is_connected()



