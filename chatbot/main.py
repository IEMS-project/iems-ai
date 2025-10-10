# -*- coding: utf-8 -*-
"""
Backend API cho Chatbot RAG tài liệu nội bộ.
Sử dụng FastAPI để tạo REST API cho React frontend.

Endpoints:
- POST /api/chat - Gửi câu hỏi và nhận câu trả lời
- GET /api/status - Kiểm tra trạng thái chatbot
- GET /api/health - Health check
"""

import sys
import os
import json
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

# Thiết lập encoding UTF-8 cho Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

# Thêm đường dẫn project vào Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from rag_pipeline.chatbot import CompanyChatbot

# Khởi tạo FastAPI app
app = FastAPI(
    title="Company Chatbot API",
    description="API cho chatbot hỏi đáp tài liệu nội bộ công ty",
    version="1.0.0"
)

# Cấu hình CORS để cho phép React frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",  # React dev server (Create React App)
        "http://localhost:5173", 
        "http://127.0.0.1:5173",  # Vite dev server
        "http://localhost:4173", 
        "http://127.0.0.1:4173",  # Vite preview server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo chatbot
print("Đang khởi tạo chatbot...")
try:
    chatbot = CompanyChatbot(top_k=3)
    print("✅ Chatbot đã sẵn sàng!")
except Exception as e:
    print(f"❌ Lỗi khởi tạo chatbot: {e}")
    chatbot = None

# Pydantic models cho request/response
class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    success: bool
    answer: Optional[str] = None
    question: Optional[str] = None
    error: Optional[str] = None

class StatusResponse(BaseModel):
    chatbot_ready: bool
    status: str

class HealthResponse(BaseModel):
    status: str
    message: str

@app.get("/", response_model=dict)
async def root():
    """Root endpoint với thông tin API."""
    return {
        "message": "Company Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/api/chat",
            "chat_stream": "/api/chat/stream",
            "status": "/api/status", 
            "health": "/api/health"
        }
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """API endpoint để xử lý câu hỏi từ người dùng."""
    try:
        print(f"[API] Received question: {request.question}")
        
        if not request.question or not request.question.strip():
            raise HTTPException(
                status_code=400,
                detail="Vui lòng nhập câu hỏi"
            )
        
        if not chatbot:
            raise HTTPException(
                status_code=503,
                detail="Chatbot chưa sẵn sàng. Vui lòng thử lại sau."
            )
        
        # Gọi chatbot để trả lời
        print(f"[API] Đang xử lý câu hỏi: {request.question}")
        answer = chatbot.ask(request.question)
        print(f"[API] Đã tạo câu trả lời: {answer[:100]}...")
        
        return ChatResponse(
            success=True,
            answer=answer,
            question=request.question
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Lỗi: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Có lỗi xảy ra: {str(e)}"
        )

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """API endpoint streaming để xử lý câu hỏi từ người dùng."""
    try:
        print(f"[API] Received streaming question: {request.question}")
        
        if not request.question or not request.question.strip():
            raise HTTPException(
                status_code=400,
                detail="Vui lòng nhập câu hỏi"
            )
        
        if not chatbot:
            raise HTTPException(
                status_code=503,
                detail="Chatbot chưa sẵn sàng. Vui lòng thử lại sau."
            )
        
        def generate_stream():
            try:
                print(f"[API] Đang xử lý streaming câu hỏi: {request.question}")
                
                # Gọi chatbot để trả lời với streaming
                for chunk in chatbot.ask_stream(request.question):
                    # Gửi chunk dưới dạng Server-Sent Events
                    data = {
                        "type": "chunk",
                        "content": chunk,
                        "question": request.question
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                
                # Gửi signal kết thúc
                end_data = {
                    "type": "end",
                    "question": request.question
                }
                yield f"data: {json.dumps(end_data, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                print(f"[API] Lỗi streaming: {e}")
                error_data = {
                    "type": "error",
                    "error": str(e),
                    "question": request.question
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Lỗi: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Có lỗi xảy ra: {str(e)}"
        )

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Kiểm tra trạng thái chatbot."""
    return StatusResponse(
        chatbot_ready=chatbot is not None,
        status="ready" if chatbot else "not_ready"
    )

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        message="API đang hoạt động bình thường"
    )

if __name__ == "__main__":
    print("🚀 Khởi động backend API server...")
    print("📱 API sẽ chạy tại: http://localhost:8000")
    print("📚 API docs: http://localhost:8000/docs")
    print("🛑 Nhấn Ctrl+C để dừng server")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
