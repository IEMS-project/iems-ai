## Chatbot RAG tài liệu nội bộ (Python + LangChain + FAISS + Ollama)

### Mô tả
Chatbot hỏi đáp dựa trên tài liệu trong thư mục `documents/`, sử dụng LangChain, FAISS và Ollama model `qwen2.5:latest` chạy local.

**Tính năng mới: 🧠 Quản lý Nhiều Cuộc Hội Thoại + MongoDB**
- Chatbot có thể quản lý nhiều cuộc hội thoại đồng thời
- Tên cuộc hội thoại được tạo tự động dựa trên câu hỏi đầu tiên
- Chuyển đổi giữa các cuộc hội thoại khác nhau
- Mỗi cuộc hội thoại có trí nhớ riêng biệt
- **Lưu trữ dài hạn trong MongoDB theo userID**
- **Quản lý nhiều users với dữ liệu riêng biệt**
- Quản lý với các lệnh `/new`, `/list`, `/switch`, `/delete`, `/current`, `/user`, `/sync`

**Hỗ trợ 3 chế độ:**
- CLI: Giao diện dòng lệnh với trí nhớ
- Web: Giao diện web Flask
- **Backend API: API riêng biệt cho React frontend** ⭐

### Cấu trúc
```
chatbot-rag/
├── documents/                    # Tài liệu nguồn
├── vectorstore/                  # Vector database
│   └── company_docs/
├── config/                       # Cấu hình model
│   └── model_config.py
├── data_processing/              # Xử lý dữ liệu
│   └── build_vectorstore.py
├── rag_pipeline/                 # Pipeline RAG
│   ├── retriever.py
│   ├── generator.py
│   ├── chatbot.py
│   ├── memory.py                 # 🧠 Trí nhớ conversation
│   ├── conversation_manager.py   # 📋 Quản lý nhiều cuộc hội thoại
│   ├── database.py               # 🗄️ MongoDB integration
│   └── user_manager.py           # 👤 Quản lý user và session
├── prompts/                      # Prompt templates
│   ├── system_prompt.txt
│   ├── user_prompt_template.txt
│   └── prompt_manager.py
├── backend/                      # Backend API (FastAPI) ⭐
│   ├── main.py
│   ├── requirements.txt
│   ├── README.md
│   └── react_integration_example.js
├── web_interface/                # Web interface
│   └── templates/
├── run_chatbot.py               # CLI mode
├── run_web.py                   # Web mode
├── run_backend.py               # Backend API mode ⭐
├── web_app.py                   # Flask web app
├── requirements.txt
└── README.md
```

### Chuẩn bị môi trường
1. Cài Python 3.10+
2. Cài đặt Ollama:
   - Windows: https://ollama.ai/download
   - Hoặc: `winget install Ollama.Ollama`
3. Tải model Qwen2.5:
   ```bash
   ollama pull qwen2.5:latest
   ```
4. Khởi động Ollama server:
   ```bash
   ollama serve
   ```
5. Cài thư viện Python (bao gồm PyMongo):
   ```bash
   pip install -r requirements.txt
   ```
6. (Tùy chọn) Chạy script kiểm tra setup:
   ```bash
   python check_ollama.py
   ```

### Xây dựng vectorstore
Đặt các file `.txt` vào `documents/`, sau đó chạy:
```bash
python -m data_processing.build_vectorstore
```

## Cách sử dụng

### 1. CLI Mode (Dòng lệnh) 🧠
```bash
python run_chatbot.py
```
**Tính năng quản lý cuộc hội thoại + MongoDB:**
- Tạo nhiều cuộc hội thoại với tên tự động
- Chuyển đổi giữa các cuộc hội thoại khác nhau
- Mỗi cuộc hội thoại có trí nhớ riêng biệt
- **Lưu trữ dài hạn trong MongoDB theo userID**
- **Quản lý nhiều users với dữ liệu riêng biệt**
- Lệnh đặc biệt:
  - `/user <id>` - Chuyển sang user khác
  - `/new` - Tạo cuộc hội thoại mới
  - `/list` - Xem danh sách cuộc hội thoại
  - `/switch <id>` - Chuyển sang cuộc hội thoại khác
  - `/delete <id>` - Xóa cuộc hội thoại
  - `/current` - Xem thông tin cuộc hội thoại hiện tại
  - `/memory` - Xem tóm tắt lịch sử hội thoại hiện tại
  - `/clear` - Xóa lịch sử hội thoại hiện tại
  - `/sync` - Đồng bộ dữ liệu vào database
  - `/help` - Hiển thị hướng dẫn
- Nhập câu hỏi bình thường, gõ `exit` hoặc `quit` để thoát

### 2. Web Mode (Giao diện web)
```bash
python run_web.py
```
Truy cập: http://localhost:5000

### 3. Backend API Mode (Cho React) ⭐
```bash
python run_backend.py
```
- API chạy tại: http://localhost:8000
- API docs: http://localhost:8000/docs
- Hỗ trợ CORS cho React frontend

#### Cài đặt dependencies cho backend:
```bash
pip install -r backend/requirements.txt
```

#### API Endpoints:
- `POST /api/chat` - Gửi câu hỏi
- `GET /api/status` - Kiểm tra trạng thái
- `GET /api/health` - Health check

#### Tích hợp với React:
Xem file `backend/react_integration_example.js` để biết cách tích hợp với React frontend.

### Ghi chú
- Model sinh: `qwen2.5:latest` (chạy local với Ollama)
- Endpoint: `http://localhost:11434` (Ollama local)
- Embedding: SentenceTransformers local (`all-MiniLM-L6-v2`)
- Vector database: FAISS (thay vì ChromaDB để tránh vấn đề SQLite)

### Troubleshooting
- **Lỗi kết nối Ollama**: Đảm bảo `ollama serve` đang chạy
- **Model không tìm thấy**: Chạy `ollama pull qwen2.5:latest`
- **Chậm**: Model local có thể chậm hơn cloud API, đây là bình thường


