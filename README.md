# IEMS AI

> **iems-ai** là module trí tuệ nhân tạo (AI) của hệ thống IEMS. Hiện tại repo này chứa module **Chatbot** với khả năng trả lời câu hỏi dựa trên tài liệu nội bộ.

---

## 🗂 Cấu trúc hiện tại

```
iems-ai/
│
├─ chatbot/                    # Module Chatbot - RAG-based
│  ├─ config/                  # Cấu hình model
│  ├─ data_processing/         # Xử lý dữ liệu và vectorstore
│  ├─ documents/               # Tài liệu nội bộ
│  ├─ prompts/                 # Prompt templates
│  ├─ rag_pipeline/            # RAG pipeline
│  ├─ vectorstore/             # Vector embeddings
│  ├─ main.py                  # Entry point
│  ├─ run_chatbot.py           # Script chạy chatbot
│  └─ README.md                # Hướng dẫn chatbot
│
└─ README.md                   # File này
```

---

## ⚙️ Công nghệ sử dụng

- **Python** với **OpenAI GPT**
- **RAG** (Retrieval-Augmented Generation)
- **FAISS** vector store
- **LangChain** framework

---

## 🚀 Hướng dẫn sử dụng

### 1. Cài đặt
```bash
cd chatbot
pip install -r requirements.txt
```

### 2. Chạy chatbot
```bash
python run_chatbot.py
```

### 3. Sử dụng
Chatbot sẽ trả lời câu hỏi dựa trên tài liệu nội bộ trong thư mục `documents/`.

---

## 📌 Tích hợp với IEMS

Chatbot có thể được tích hợp vào hệ thống IEMS thông qua API calls từ frontend/backend.

---

## 💡 Mở rộng trong tương lai

Repo này được thiết kế để dễ dàng thêm các module AI khác như:
- NLP processing
- Recommendation system  
- Analytics AI
- Voice assistant

---

**Made with ❤️ by IEMS Team**
