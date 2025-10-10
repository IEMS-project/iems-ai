"""
Script tạo VectorStore (FAISS) từ các tài liệu văn bản trong thư mục `documents/`.

Chức năng chính:
1) Đọc tất cả file .txt trong `documents/`
2) Tiền xử lý và tách đoạn (chunk) với chunk_size=500, chunk_overlap=100
3) Tạo embedding bằng SentenceTransformers local (qua config.get_embeddings)
4) Lưu vào FAISS tại `vectorstore/company_docs/`
5) In log quá trình để tiện theo dõi

Chạy script:
    python -m data_processing.build_vectorstore

Yêu cầu môi trường:
- Đã cài đặt các thư viện trong requirements.txt
- Ollama đang chạy (ollama serve)
"""

from __future__ import annotations

import os
import glob
from typing import List

from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from config.model_config import get_embeddings


DOCUMENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "documents")
PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vectorstore", "company_docs")


def load_text_documents(documents_dir: str) -> List:
    """Đọc tất cả file `.txt` và trả về danh sách Document của LangChain.

    - Bỏ qua file rỗng hoặc không thể đọc.
    - Sử dụng TextLoader để giữ metadata gồm đường dẫn file.
    """
    pattern = os.path.join(documents_dir, "*.txt")
    file_paths = sorted(glob.glob(pattern))
    if not file_paths:
        print(f"[build_vectorstore] Khong tim thay file .txt trong: {documents_dir}")
    documents = []
    for path in file_paths:
        try:
            loader = TextLoader(path, encoding="utf-8")
            docs = loader.load()
            documents.extend(docs)
            print(f"[build_vectorstore] Da nap: {os.path.basename(path)} (so doan: {len(docs)})")
        except Exception as exc:
            print(f"[build_vectorstore] Bo qua {path} vi loi: {exc}")
    return documents


def split_documents(documents: List) -> List:
    """Tách văn bản thành các chunk cố định, chồng lấn một phần.

    - chunk_size=500, chunk_overlap=100 theo yêu cầu.
    - Dùng RecursiveCharacterTextSplitter để tôn trọng cấu trúc câu/đoạn tốt hơn.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", " ", ""],
    )
    split_docs = splitter.split_documents(documents)
    print(f"[build_vectorstore] Da tach thanh {len(split_docs)} chunk")
    return split_docs


def build_and_persist_faiss(chunks: List, persist_dir: str) -> None:
    """Tạo FAISS vector store từ các chunk và lưu xuống ổ đĩa."""
    os.makedirs(persist_dir, exist_ok=True)

    embeddings = get_embeddings()
    
    try:
        print("[build_vectorstore] Dang tao FAISS VectorStore va nhung embedding...")
        
        # Tạo FAISS vectorstore từ documents
        vectorstore = FAISS.from_documents(
            documents=chunks,
            embedding=embeddings,
        )
        
        # Lưu vectorstore
        vectorstore.save_local(persist_dir)
        print(f"[build_vectorstore] Da luu VectorStore tai: {persist_dir}")
        
    except Exception as e:
        print(f"[build_vectorstore] Loi khi tao VectorStore: {e}")
        raise


def main() -> None:
    print("[build_vectorstore] Bat dau xay dung VectorStore tu thu muc documents/")
    print(f"[build_vectorstore] Thu muc tai lieu: {DOCUMENTS_DIR}")
    print(f"[build_vectorstore] Thu muc luu vector: {PERSIST_DIR}")

    documents = load_text_documents(DOCUMENTS_DIR)
    if not documents:
        print("[build_vectorstore] Khong co tai lieu de xu ly. Ket thuc.")
        return

    chunks = split_documents(documents)
    if not chunks:
        print("[build_vectorstore] Khong tao duoc chunk nao. Ket thuc.")
        return

    build_and_persist_faiss(chunks, PERSIST_DIR)
    print("[build_vectorstore] Hoan tat.")


if __name__ == "__main__":
    main()


