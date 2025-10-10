"""
Cấu hình LLM và Embeddings dùng Ollama local thông qua LangChain.

Yêu cầu:
- Cài đặt Ollama và pull model qwen2.5:latest
- Chạy Ollama server: ollama serve

Ghi chú triển khai:
- Dùng `langchain_ollama` để tạo `ChatOllama` kết nối với Ollama local
- Model sinh câu trả lời: "qwen2.5:latest" (chạy local)
- Embedding: dùng SentenceTransformers local
"""

from __future__ import annotations

import os
from typing import Optional, List

from dotenv import load_dotenv
load_dotenv()

from langchain_ollama import ChatOllama
from langchain_core.embeddings import Embeddings

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


# Giá trị mặc định cho Ollama local
DEFAULT_CHAT_MODEL: str = os.getenv("RAG_CHAT_MODEL", "qwen2.5:latest")
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def check_ollama_connection() -> bool:
    """Kiểm tra kết nối tới Ollama server."""
    import requests
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False


class LocalEmbeddings(Embeddings):
    """Embedding class sử dụng SentenceTransformers local."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers không được cài đặt. "
                "Chạy: pip install sentence-transformers"
            )
        self.model = SentenceTransformer(model_name)
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed danh sách documents."""
        embeddings = self.model.encode(texts)
        return embeddings.tolist()
    
    def embed_query(self, text: str) -> List[float]:
        """Embed một query."""
        embedding = self.model.encode([text])
        return embedding[0].tolist()


def get_llm(model: Optional[str] = None) -> ChatOllama:
    """Tạo LLM client (ChatOllama) đã cấu hình sẵn cho Ollama local.

    - Trả về: đối tượng ChatOllama dùng trong LangChain
    - Tham số:
        model: cho phép override model mặc định nếu cần
    """
    model_name = model or DEFAULT_CHAT_MODEL
    
    # Kiểm tra kết nối tới Ollama
    if not check_ollama_connection():
        raise ConnectionError(
            f"Không thể kết nối tới Ollama server tại {OLLAMA_BASE_URL}. "
            "Vui lòng đảm bảo Ollama đang chạy: ollama serve"
        )

    # ChatOllama của langchain_ollama kết nối trực tiếp với Ollama local
    llm = ChatOllama(
        model=model_name,
        base_url=OLLAMA_BASE_URL,
        # Cấu hình mặc định an toàn cho chatbot nội bộ
        temperature=0.2,
        timeout=120,  # Tăng timeout vì model local có thể chậm hơn
    )
    return llm


def get_embeddings(model: Optional[str] = None) -> LocalEmbeddings:
    """Tạo embedding client sử dụng SentenceTransformers local.

    - Dùng SentenceTransformers để tránh vấn đề với OpenRouter API.
    - Model mặc định: "all-MiniLM-L6-v2" (nhẹ, nhanh, chất lượng tốt)
    """
    model_name = model or "all-MiniLM-L6-v2"
    embeddings = LocalEmbeddings(model_name=model_name)
    return embeddings


