"""
Retriever mở lại FAISS VectorStore và cung cấp hàm truy xuất top-k đoạn liên quan.

Chức năng chính:
- Nạp FAISS từ thư mục `vectorstore/company_docs`
- Cung cấp hàm `get_relevant_docs(query, k=3)` trả về danh sách Document liên quan nhất
- In log các bước để dễ theo dõi quá trình truy vấn
"""

from __future__ import annotations

import os
from typing import List

from langchain_community.vectorstores import FAISS


PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vectorstore", "company_docs")


def load_vectorstore(persist_dir: str = PERSIST_DIR):
    """Mở lại FAISS VectorStore đã được lưu trước đó."""
    print(f"[retriever] Dang mo VectorStore tu: {persist_dir}")
    from config.model_config import get_embeddings
    embeddings = get_embeddings()
    vectorstore = FAISS.load_local(persist_dir, embeddings, allow_dangerous_deserialization=True)
    return vectorstore


def get_relevant_docs(query: str, k: int = 3):
    """Trả về top-k đoạn liên quan nhất dựa trên truy vấn.

    - Sử dụng phương thức similarity_search của FAISS
    - Trả về danh sách Document (LangChain)
    """
    if not query or not query.strip():
        print("[retriever] Cau truy van trong. Tra ve danh sach rong.")
        return []

    print(f"[retriever] Nhan truy van: {query}")
    vectorstore = load_vectorstore()
    print("[retriever] Thuc hien similarity_search...")
    docs = vectorstore.similarity_search(query, k=k)
    print(f"[retriever] Tim duoc {len(docs)} doan phu hop nhat.")
    for i, d in enumerate(docs, 1):
        source = d.metadata.get("source", "<unknown>")
        print(f"[retriever] Top {i} — nguon: {os.path.basename(source)} — do dai: {len(d.page_content)}")
    return docs


