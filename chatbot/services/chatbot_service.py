"""
Chatbot RAG hoàn chỉnh: kết hợp retriever (truy xuất ngữ cảnh) và generator (sinh câu trả lời).

Luồng xử lý:
1) Nhận câu hỏi từ người dùng
2) Gọi retriever để lấy top các đoạn liên quan
3) Gọi generator để sinh câu trả lời tiếng Việt dựa trên ngữ cảnh và lịch sử hội thoại
4) Trả về câu trả lời cho lớp giao diện (CLI)
"""

from __future__ import annotations

from typing import List, Dict

from langchain_core.documents import Document

from services.document_retriever import get_relevant_docs
from services.answer_generator import generate_answer, generate_answer_stream
from models.conversation_memory import ConversationMemory
from models.conversation import ConversationManager
from services.user_service import UserManager
from services.jwt_service import extract_user_id_from_token, validate_jwt_token


class CompanyChatbot:
    """Chatbot hỏi đáp tài liệu nội bộ công ty dựa trên RAG với JWT authentication và MongoDB."""

    def __init__(self, jwt_token: str, top_k: int = 3, max_memory_turns: int = 10, max_conversations: int = 10) -> None:
        """
        Khởi tạo chatbot với JWT authentication và MongoDB.
        
        Args:
            jwt_token: JWT token để lấy userID
            top_k: Số lượng document liên quan nhất để lấy từ retriever
            max_memory_turns: Số lượt hội thoại tối đa để lưu trong memory
            max_conversations: Số lượng cuộc hội thoại tối đa
        """
        # Validate JWT token và lấy userID
        if not validate_jwt_token(jwt_token):
            raise ValueError("JWT token không hợp lệ hoặc đã hết hạn")
        
        user_id = extract_user_id_from_token(jwt_token)
        if not user_id:
            raise ValueError("Không thể lấy userID từ JWT token")
        
        self.jwt_token = jwt_token
        self.user_id = user_id
        self.top_k = top_k
        self.user_manager = UserManager(user_id)

    def ask(self, query: str) -> str:
        """Nhận câu hỏi và trả về câu trả lời tiếng Việt dựa trên tài liệu nội bộ và lịch sử hội thoại."""
        if not query or not query.strip():
            return "Vui long nhap cau hoi ro rang."

        # Validate JWT token trước khi xử lý
        if not self.validate_jwt_token():
            return "❌ JWT token không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại."

        # Lấy conversation hiện tại (đã được tạo ở API level nếu cần)
        current_conv = self.user_manager.get_current_conversation()
        if not current_conv:
            # Fallback: tạo conversation mới nếu không có (trường hợp hiếm)
            conv_id = self.user_manager.create_conversation(query)
            print(f"[chatbot] User {self.user_id}: Fallback tạo cuộc hội thoại mới")

        print("[chatbot] Đang truy vấn các đoạn liên quan...")
        docs: List[Document] = get_relevant_docs(query, k=self.top_k)

        print("[chatbot] Đang tạo câu trả lời từ LLM với lịch sử hội thoại...")
        current_conv = self.user_manager.get_current_conversation()
        answer: str = generate_answer(query, docs, current_conv.memory)

        # Lưu lượt hội thoại vào memory và database
        self.user_manager.add_turn(query, answer)

        print("[chatbot] Hoàn thành.")
        return answer

    def ask_stream(self, query: str):
        """Nhận câu hỏi và trả về streaming câu trả lời tiếng Việt dựa trên tài liệu nội bộ và lịch sử hội thoại."""
        if not query or not query.strip():
            yield "Vui long nhap cau hoi ro rang."
            return

        # Validate JWT token trước khi xử lý
        if not self.validate_jwt_token():
            yield "❌ JWT token không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại."
            return

        # Lấy conversation hiện tại (đã được tạo ở API level nếu cần)
        current_conv = self.user_manager.get_current_conversation()
        if not current_conv:
            # Fallback: tạo conversation mới nếu không có (trường hợp hiếm)
            conv_id = self.user_manager.create_conversation(query)
            print(f"[chatbot] User {self.user_id}: Fallback tạo cuộc hội thoại mới")

        print("[chatbot] Đang truy vấn các đoạn liên quan...")
        docs: List[Document] = get_relevant_docs(query, k=self.top_k)

        print("[chatbot] Dang sinh cau tra loi streaming tu LLM...")
        current_conv = self.user_manager.get_current_conversation()
        answer_chunks = []
        for chunk in generate_answer_stream(query, docs, current_conv.memory):
            answer_chunks.append(chunk)
            yield chunk

        # Lưu lượt hội thoại vào memory và database (ghép các chunk thành câu trả lời hoàn chỉnh)
        full_answer = "".join(answer_chunks)
        print(f"[chatbot] Đang lưu lượt hội thoại vào database...")
        print(f"[chatbot] Question: {query[:50]}...")
        print(f"[chatbot] Answer length: {len(full_answer)}")
        
        success = self.user_manager.add_turn(query, full_answer)
        if success:
            print(f"[chatbot] ✅ Đã lưu lượt hội thoại vào database thành công")
        else:
            print(f"[chatbot] ❌ Lỗi lưu lượt hội thoại vào database")

        print("[chatbot] Hoan tat streaming.")

    def clear_memory(self) -> None:
        """Xóa lịch sử hội thoại của cuộc hội thoại hiện tại."""
        self.user_manager.clear_current_memory()
        print("[chatbot] Đã xóa lịch sử hội thoại hiện tại.")

    def get_memory_summary(self) -> str:
        """Lấy tóm tắt lịch sử hội thoại hiện tại."""
        return self.user_manager.get_memory_summary()

    def get_memory_count(self) -> int:
        """Lấy số lượng lượt hội thoại đã lưu."""
        return self.user_manager.get_memory_count()

    def create_new_conversation(self, first_question: str) -> str:
        """Tạo cuộc hội thoại mới với câu hỏi đầu tiên."""
        conv_id = self.user_manager.create_conversation(first_question)
        print(f"[chatbot] User {self.user_id}: Tạo cuộc hội thoại mới")
        return conv_id

    def switch_conversation(self, conv_id: str) -> bool:
        """Chuyển sang cuộc hội thoại khác."""
        success = self.user_manager.switch_conversation(conv_id)
        if success:
            print(f"[chatbot] User {self.user_id}: Chuyển sang cuộc hội thoại {conv_id}")
        return success

    def get_conversation_list(self) -> List[Dict]:
        """Lấy danh sách tất cả cuộc hội thoại."""
        return self.user_manager.get_conversation_list()

    def delete_conversation(self, conv_id: str) -> bool:
        """Xóa cuộc hội thoại."""
        return self.user_manager.delete_conversation(conv_id)

    def get_current_conversation_info(self) -> Dict:
        """Lấy thông tin cuộc hội thoại hiện tại."""
        return self.user_manager.get_current_conversation_info()
    
    def sync_to_database(self) -> bool:
        """Đồng bộ dữ liệu vào database."""
        return self.user_manager.sync_to_database()
    
    def validate_jwt_token(self) -> bool:
        """Validate JWT token hiện tại."""
        return validate_jwt_token(self.jwt_token)
    
    def get_user_id(self) -> str:
        """Lấy userID từ JWT token."""
        return self.user_id
    
    def get_jwt_token(self) -> str:
        """Lấy JWT token hiện tại."""
        return self.jwt_token
    
    def update_jwt_token(self, new_token: str) -> bool:
        """
        Cập nhật JWT token mới.
        
        Args:
            new_token: JWT token mới
            
        Returns:
            True nếu cập nhật thành công, False nếu token không hợp lệ
        """
        if not validate_jwt_token(new_token):
            return False
        
        new_user_id = extract_user_id_from_token(new_token)
        if not new_user_id:
            return False
        
        # Kiểm tra userID có thay đổi không
        if new_user_id != self.user_id:
            print(f"⚠️ UserID thay đổi từ {self.user_id} sang {new_user_id}")
            # Tạo UserManager mới cho user khác
            self.user_id = new_user_id
            self.user_manager = UserManager(new_user_id)
        
        self.jwt_token = new_token
        print(f"✅ Đã cập nhật JWT token cho user: {self.user_id}")
        return True


