"""
Chatbot RAG hoàn chỉnh: kết hợp retriever (truy xuất ngữ cảnh) và generator (sinh câu trả lời).

Luồng xử lý:
1) Nhận câu hỏi từ người dùng
2) Gọi retriever để lấy top các đoạn liên quan
3) Gọi generator để sinh câu trả lời tiếng Việt dựa trên ngữ cảnh
4) Trả về câu trả lời cho lớp giao diện (CLI)
"""

from __future__ import annotations

from typing import List

from langchain_core.documents import Document

from rag_pipeline.retriever import get_relevant_docs
from rag_pipeline.generator import generate_answer, generate_answer_stream


class CompanyChatbot:
    """Chatbot hỏi đáp tài liệu nội bộ công ty dựa trên RAG."""

    def __init__(self, top_k: int = 3) -> None:
        self.top_k = top_k

    def ask(self, query: str) -> str:
        """Nhận câu hỏi và trả về câu trả lời tiếng Việt dựa trên tài liệu nội bộ."""
        if not query or not query.strip():
            return "Vui long nhap cau hoi ro rang."

        print("[chatbot] Dang truy van cac doan lien quan...")
        docs: List[Document] = get_relevant_docs(query, k=self.top_k)

        print("[chatbot] Dang sinh cau tra loi tu LLM...")
        answer: str = generate_answer(query, docs)

        print("[chatbot] Hoan tat.")
        return answer

    def ask_stream(self, query: str):
        """Nhận câu hỏi và trả về streaming câu trả lời tiếng Việt dựa trên tài liệu nội bộ."""
        if not query or not query.strip():
            yield "Vui long nhap cau hoi ro rang."
            return

        print("[chatbot] Dang truy van cac doan lien quan...")
        docs: List[Document] = get_relevant_docs(query, k=self.top_k)

        print("[chatbot] Dang sinh cau tra loi streaming tu LLM...")
        for chunk in generate_answer_stream(query, docs):
            yield chunk

        print("[chatbot] Hoan tat streaming.")


