## Chatbot RAG tài liệu nội bộ (Python + LangChain + FAISS + Ollama)

### Mô tả
Chatbot hỏi đáp dựa trên tài liệu trong thư mục `documents/`, sử dụng LangChain, FAISS và Ollama model `qwen2.5:latest` chạy local.

**Hỗ trợ 3 chế độ:**
- CLI: Giao diện dòng lệnh
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
│   └── chatbot.py
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
5. Cài thư viện Python:
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

### 1. CLI Mode (Dòng lệnh)
```bash
python run_chatbot.py
```
Nhập câu hỏi, gõ `exit` hoặc `quit` để thoát.

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


