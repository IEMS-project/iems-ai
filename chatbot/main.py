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
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

# Thiết lập encoding UTF-8 cho Windows
if sys.platform.startswith('win'):
    import codecs
    import io
    # Tạo wrapper để tránh lỗi "raw stream has been detached"
    try:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
    except (ValueError, AttributeError):
        # Nếu stream đã bị detach, tạo lại
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Thêm đường dẫn project vào Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from services.chatbot_service import CompanyChatbot
from services.jwt_service import get_token_info, extract_user_id_from_token
from services.user_service import get_user_manager
from db.mongodb_manager import get_mongodb_manager

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

# Khởi tạo chatbot - chỉ khởi tạo các component cần thiết
print("Đang khởi tạo chatbot...")
try:
    # Khởi tạo MongoDB connection
    mongodb_connection_string = "mongodb+srv://iems_db_conservation:F4cvU0iZ3lbMQb57@iems.vgujzeu.mongodb.net/"
    print("🔌 Đang kết nối MongoDB...")
    from db.mongodb_manager import initialize_mongodb
    if initialize_mongodb(mongodb_connection_string, "iems_chatbot"):
        print("✅ Đã kết nối MongoDB thành công!")
    else:
        print("⚠️ Không thể kết nối MongoDB. Chạy ở chế độ offline.")
    
    # Không khởi tạo CompanyChatbot global vì cần JWT token
    # Chỉ kiểm tra các component cần thiết
    from services.document_retriever import get_relevant_docs
    from services.answer_generator import generate_answer
    print("✅ Các component chatbot đã sẵn sàng!")
    chatbot_ready = True
except Exception as e:
    print(f"❌ Lỗi khởi tạo component: {e}")
    chatbot_ready = False

# JWT Authentication dependency
async def get_current_user(authorization: str = Header(None)):
    """
    Dependency để extract user từ JWT token trong Authorization header.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token từ "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication scheme. Expected 'Bearer'",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate JWT token
    token_info = get_token_info(token)
    if not token_info['valid'] or token_info['expired']:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired JWT token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = token_info['user_id']
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in JWT token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "user_id": user_id,
        "token": token,
        "token_info": token_info
    }

# Pydantic models cho request/response
class ChatRequest(BaseModel):
    question: str
    conversationId: Optional[str] = None

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

class UserInfoResponse(BaseModel):
    user_id: str
    valid: bool
    expired: bool
    expiration: Optional[str] = None
    verified: bool

class ConversationListResponse(BaseModel):
    conversations: list
    current_conversation: Optional[dict] = None

class MemoryResponse(BaseModel):
    summary: str
    count: int

@app.get("/", response_model=dict)
async def root():
    """Root endpoint với thông tin API."""
    return {
        "message": "Company Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/api/chat",
            "chat_stream": "/api/chat/stream",
            "user_info": "/api/user/info",
            "conversations": "/api/user/conversations",
            "conversation_messages": "/api/user/conversations/{conversation_id}/messages",
            "memory": "/api/user/memory",
            "switch_conversation": "/api/user/conversations/switch",
            "rename_conversation": "/api/user/conversations/{conversation_id}/rename",
            "delete_conversation": "/api/user/conversations/{conversation_id}",
            "clear_memory": "/api/user/memory/clear",
            "status": "/api/status", 
            "health": "/api/health"
        }
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """API endpoint để xử lý câu hỏi từ người dùng với JWT authentication."""
    try:
        user_id = current_user["user_id"]
        jwt_token = current_user["token"]
        
        print(f"[API] User {user_id} asked: {request.question}")
        
        if not request.question or not request.question.strip():
            raise HTTPException(
                status_code=400,
                detail="Vui lòng nhập câu hỏi"
            )
        
        if not chatbot_ready:
            raise HTTPException(
                status_code=503,
                detail="Chatbot chưa sẵn sàng. Vui lòng thử lại sau."
            )
        
        # Lấy UserManager cho user này (sẽ load conversations từ DB)
        user_manager = get_user_manager(user_id)
        
        # Xử lý conversationId từ request
        target_conversation_id = request.conversationId
        print(f"[API] ConversationId from request: {target_conversation_id}")
        
        # Nếu có conversationId cụ thể, chuyển sang conversation đó
        if target_conversation_id:
            print(f"[API] Switching to conversation: {target_conversation_id}")
            user_manager.switch_conversation(target_conversation_id)
        # Nếu conversationId = null, tạo conversation mới hoàn toàn
        elif target_conversation_id is None:
            print(f"[API] Creating completely new conversation (conversationId = null)")
            # Tạo conversation mới ngay lập tức với câu hỏi đầu tiên
            new_conv_id = user_manager.create_conversation(request.question)
            print(f"[API] Created new conversation: {new_conv_id}")
            # Chuyển sang conversation mới này
            user_manager.switch_conversation(new_conv_id)
        
        # Tạo chatbot instance cho user này với JWT token
        user_chatbot = CompanyChatbot(
            jwt_token=jwt_token,
            top_k=3,
            max_memory_turns=10,
            max_conversations=10
        )
        
        # Gọi chatbot để trả lời
        print(f"[API] Đang xử lý câu hỏi cho user {user_id}: {request.question}")
        answer = user_chatbot.ask(request.question)
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
async def chat_stream(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """API endpoint streaming để xử lý câu hỏi từ người dùng với JWT authentication."""
    try:
        user_id = current_user["user_id"]
        jwt_token = current_user["token"]
        
        print(f"[API] User {user_id} streaming question: {request.question}")
        
        if not request.question or not request.question.strip():
            raise HTTPException(
                status_code=400,
                detail="Vui lòng nhập câu hỏi"
            )
        
        if not chatbot_ready:
            raise HTTPException(
                status_code=503,
                detail="Chatbot chưa sẵn sàng. Vui lòng thử lại sau."
            )
        
        # Lấy UserManager cho user này (sẽ load conversations từ DB)
        user_manager = get_user_manager(user_id)
        
        # Xử lý conversationId từ request
        target_conversation_id = request.conversationId
        print(f"[API] ConversationId from request: {target_conversation_id}")
        
        # Nếu có conversationId cụ thể, chuyển sang conversation đó
        if target_conversation_id:
            print(f"[API] Switching to conversation: {target_conversation_id}")
            user_manager.switch_conversation(target_conversation_id)
        # Nếu conversationId = null, tạo conversation mới hoàn toàn
        elif target_conversation_id is None:
            print(f"[API] Creating completely new conversation (conversationId = null)")
            # Tạo conversation mới ngay lập tức với câu hỏi đầu tiên
            new_conv_id = user_manager.create_conversation(request.question)
            print(f"[API] Created new conversation: {new_conv_id}")
            # Chuyển sang conversation mới này
            user_manager.switch_conversation(new_conv_id)
        
        # Tạo chatbot instance cho user này với JWT token
        user_chatbot = CompanyChatbot(
            jwt_token=jwt_token,
            top_k=3,
            max_memory_turns=10,
            max_conversations=10
        )
        
        def generate_stream():
            try:
                print(f"[API] Đang xử lý streaming câu hỏi cho user {user_id}: {request.question}")
                
                # Gọi chatbot để trả lời với streaming
                for chunk in user_chatbot.ask_stream(request.question):
                    # Gửi chunk dưới dạng Server-Sent Events
                    data = {
                        "type": "chunk",
                        "content": chunk,
                        "question": request.question,
                        "user_id": user_id
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                
                # Gửi signal kết thúc
                end_data = {
                    "type": "end",
                    "question": request.question,
                    "user_id": user_id
                }
                yield f"data: {json.dumps(end_data, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                print(f"[API] Lỗi streaming: {e}")
                error_data = {
                    "type": "error",
                    "error": str(e),
                    "question": request.question,
                    "user_id": user_id
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
        chatbot_ready=chatbot_ready,
        status="ready" if chatbot_ready else "not_ready"
    )

# User Management Endpoints
@app.get("/api/user/info", response_model=UserInfoResponse)
async def get_user_info(current_user: dict = Depends(get_current_user)):
    """Lấy thông tin user từ JWT token."""
    token_info = current_user["token_info"]
    return UserInfoResponse(
        user_id=current_user["user_id"],
        valid=token_info["valid"],
        expired=token_info["expired"],
        expiration=token_info["expiration"],
        verified=token_info["verified"]
    )

@app.get("/api/user/conversations", response_model=ConversationListResponse)
async def get_conversations(current_user: dict = Depends(get_current_user)):
    """Lấy danh sách cuộc hội thoại của user."""
    try:
        user_id = current_user["user_id"]
        jwt_token = current_user["token"]
        
        # Lấy UserManager cho user này (sẽ load conversations từ DB)
        user_manager = get_user_manager(user_id)
        
        conversations = user_manager.get_conversation_list()
        current_info = user_manager.get_current_conversation_info()
        
        return ConversationListResponse(
            conversations=conversations,
            current_conversation=current_info
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi lấy danh sách cuộc hội thoại: {str(e)}"
        )

@app.get("/api/user/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Lấy danh sách tin nhắn của một cuộc hội thoại cụ thể."""
    try:
        user_id = current_user["user_id"]
        jwt_token = current_user["token"]
        
        # Lấy UserManager cho user này (sẽ load conversations từ DB)
        user_manager = get_user_manager(user_id)
        
        # Load conversation trực tiếp từ MongoDB thay vì từ memory
        mongodb_manager = get_mongodb_manager()
        if mongodb_manager:
            # Load conversation từ MongoDB
            conversation_data = mongodb_manager.load_conversation_by_id(user_id, conversation_id)
            if conversation_data:
                # Convert từ MongoDB format sang frontend format
                messages = []
                turns = []
                
                if conversation_data.turns:
                    for turn in conversation_data.turns:
                        # Add user message
                        messages.append({
                            "id": f"{turn['timestamp']}_user",
                            "content": turn['question'],
                            "role": "user",
                            "timestamp": turn['timestamp'],
                            "isUser": True
                        })
                        # Add bot message
                        messages.append({
                            "id": f"{turn['timestamp']}_bot",
                            "content": turn['answer'],
                            "role": "assistant",
                            "timestamp": turn['timestamp'],
                            "isUser": False
                        })
                        
                        # Add to turns
                        turns.append({
                            "question": turn['question'],
                            "answer": turn['answer'],
                            "timestamp": turn['timestamp']
                        })
                
                return {
                    "success": True,
                    "conversation_id": conversation_id,
                    "messages": messages,
                    "turns": turns
                }
        
        # Fallback về UserManager nếu không có MongoDB
        messages = user_manager.get_conversation_messages(conversation_id)
        
        # Lấy conversation để có thể trả về turns nếu cần
        conversation = user_manager.conversation_manager.conversations.get(conversation_id)
        turns = []
        if conversation and conversation.memory.conversation_history:
            turns = [
                {
                    "question": turn.question,
                    "answer": turn.answer,
                    "timestamp": turn.timestamp.isoformat()
                }
                for turn in conversation.memory.conversation_history
            ]
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "messages": messages,
            "turns": turns
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi lấy tin nhắn cuộc hội thoại: {str(e)}"
        )

@app.get("/api/user/memory", response_model=MemoryResponse)
async def get_memory(current_user: dict = Depends(get_current_user)):
    """Lấy tóm tắt lịch sử hội thoại hiện tại."""
    try:
        user_id = current_user["user_id"]
        jwt_token = current_user["token"]
        
        # Lấy UserManager cho user này (sẽ load conversations từ DB)
        user_manager = get_user_manager(user_id)
        
        summary = user_manager.get_memory_summary()
        count = user_manager.get_memory_count()
        
        return MemoryResponse(
            summary=summary,
            count=count
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi lấy thông tin memory: {str(e)}"
        )


@app.post("/api/user/conversations/switch")
async def switch_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Chuyển sang cuộc hội thoại khác."""
    try:
        user_id = current_user["user_id"]
        jwt_token = current_user["token"]
        
        # Lấy UserManager cho user này (sẽ load conversations từ DB)
        user_manager = get_user_manager(user_id)
        
        if user_manager.switch_conversation(conversation_id):
            return {
                "success": True,
                "message": f"Đã chuyển sang cuộc hội thoại: {conversation_id}"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy cuộc hội thoại với ID: {conversation_id}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi chuyển cuộc hội thoại: {str(e)}"
        )

@app.patch("/api/user/conversations/{conversation_id}/rename")
async def rename_conversation(
    conversation_id: str,
    new_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Đổi tên cuộc hội thoại."""
    try:
        user_id = current_user["user_id"]
        jwt_token = current_user["token"]
        
        # Lấy UserManager cho user này (sẽ load conversations từ DB)
        user_manager = get_user_manager(user_id)
        
        if user_manager.rename_conversation(conversation_id, new_name):
            return {
                "success": True,
                "message": f"Đã đổi tên cuộc hội thoại thành: {new_name}"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy cuộc hội thoại với ID: {conversation_id}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi đổi tên cuộc hội thoại: {str(e)}"
        )

@app.delete("/api/user/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Xóa cuộc hội thoại."""
    try:
        user_id = current_user["user_id"]
        jwt_token = current_user["token"]
        
        # Lấy UserManager cho user này (sẽ load conversations từ DB)
        user_manager = get_user_manager(user_id)
        
        if user_manager.delete_conversation(conversation_id):
            return {
                "success": True,
                "message": f"Đã xóa cuộc hội thoại: {conversation_id}"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy cuộc hội thoại với ID: {conversation_id}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi xóa cuộc hội thoại: {str(e)}"
        )

@app.post("/api/user/memory/clear")
async def clear_memory(current_user: dict = Depends(get_current_user)):
    """Xóa lịch sử hội thoại hiện tại."""
    try:
        user_id = current_user["user_id"]
        jwt_token = current_user["token"]
        
        # Lấy UserManager cho user này (sẽ load conversations từ DB)
        user_manager = get_user_manager(user_id)
        
        user_manager.clear_current_memory()
        
        return {
            "success": True,
            "message": "Đã xóa lịch sử hội thoại hiện tại"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi xóa memory: {str(e)}"
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
