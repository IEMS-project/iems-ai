"""
Giao diện CLI cho chatbot RAG tài liệu nội bộ công ty.

Cách sử dụng:
1) Cài đặt và khởi động Ollama: `ollama serve`
2) Tải model: `ollama pull qwen2.5:latest`
3) Xây dựng vectorstore: `python -m data_processing.build_vectorstore`
4) Chạy chatbot: `python run_chatbot.py`
5) Gõ câu hỏi; nhập `exit` hoặc `quit` để thoát
"""

from __future__ import annotations

import sys

from rag_pipeline.chatbot import CompanyChatbot


def main() -> None:
    # Khởi tạo chatbot với top_k=3 theo yêu cầu
    bot = CompanyChatbot(top_k=3)

    print("===== Chatbot Tai Lieu Noi Bo (RAG) =====")
    print("Nhap cau hoi cua ban. Go 'exit' hoac 'quit' de thoat.")

    while True:
        try:
            # Đọc câu hỏi từ stdin. Dùng strip() để loại bỏ khoảng trắng thừa.
            query = input("Ban: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTam biet!")
            break

        # Điều kiện thoát
        if query.lower() in {"exit", "quit"}:
            print("Tam biet!")
            break

        if not query:
            print("Vui long nhap cau hoi hop le.")
            continue

        # Gọi chatbot để lấy câu trả lời
        answer = bot.ask(query)
        print(f"Bot: {answer}\n")


if __name__ == "__main__":
    main()


