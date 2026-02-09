"""
Giao diện CLI cho chatbot RAG tài liệu nội bộ công ty với MongoDB và quản lý user.

Cách sử dụng:
1) Cài đặt và khởi động Ollama: `ollama serve`
2) Tải model: `ollama pull qwen2.5:latest`
3) Cài đặt MongoDB: `pip install pymongo`
4) Xây dựng vectorstore: `python -m data_processing.build_vectorstore`
5) Chạy chatbot: `python run_chatbot.py`
6) Gõ câu hỏi; nhập `exit` hoặc `quit` để thoát

Lệnh đặc biệt:
- `/user <id>` - Chuyển sang user khác
- `/memory` - Xem tóm tắt lịch sử hội thoại hiện tại
- `/clear` - Xóa lịch sử hội thoại hiện tại
- `/new` - Tạo cuộc hội thoại mới
- `/list` - Xem danh sách cuộc hội thoại
- `/switch <id>` - Chuyển sang cuộc hội thoại khác
- `/delete <id>` - Xóa cuộc hội thoại
- `/current` - Xem thông tin cuộc hội thoại hiện tại
- `/sync` - Đồng bộ dữ liệu vào database
- `/help` - Hiển thị hướng dẫn
"""

from __future__ import annotations

import sys

from services.chatbot_service import CompanyChatbot
from db.mongodb_manager import initialize_mongodb, is_mongodb_available
from services.user_service import get_user_manager, generate_user_id
from services.jwt_service import get_token_info


def show_help():
    """Hiển thị hướng dẫn sử dụng."""
    print("\n=== HƯỚNG DẪN SỬ DỤNG CHATBOT ===")
    print("• Gõ câu hỏi bình thường để hỏi chatbot")
    print("• Chatbot có thể quản lý nhiều cuộc hội thoại với tên tự động")
    print("• Dữ liệu được lưu trữ trong MongoDB theo userID")
    print("\nLệnh đặc biệt:")
    print("• /jwt <token> - Cập nhật JWT token mới")
    print("• /jwt-info - Xem thông tin JWT token hiện tại")
    print("• /user <id> - Chuyển sang user khác")
    print("• /memory - Xem tóm tắt lịch sử hội thoại hiện tại")
    print("• /clear - Xóa lịch sử hội thoại hiện tại")
    print("• /new - Tạo cuộc hội thoại mới")
    print("• /list - Xem danh sách cuộc hội thoại")
    print("• /switch <id> - Chuyển sang cuộc hội thoại khác")
    print("• /delete <id> - Xóa cuộc hội thoại")
    print("• /current - Xem thông tin cuộc hội thoại hiện tại")
    print("• /sync - Đồng bộ dữ liệu vào database")
    print("• /help - Hiển thị hướng dẫn này")
    print("• exit/quit - Thoát chương trình")
    print("=" * 60 + "\n")


def main() -> None:
    # Khởi tạo MongoDB connection
    mongodb_connection_string = "mongodb+srv://iems_db_conservation:F4cvU0iZ3lbMQb57@iems.vgujzeu.mongodb.net/"
    
    print("🔌 Đang kết nối MongoDB...")
    if initialize_mongodb(mongodb_connection_string, "iems_chatbot"):
        print("✅ Đã kết nối MongoDB thành công!")
    else:
        print("⚠️ Không thể kết nối MongoDB. Chạy ở chế độ offline.")
    
    # Nhập JWT token
    print("\n🔐 JWT Authentication:")
    jwt_token = input("Nhập JWT token của bạn: ").strip()
    
    if not jwt_token:
        print("❌ Vui lòng nhập JWT token hợp lệ.")
        return
    
    try:
        # Khởi tạo chatbot với JWT token
        bot = CompanyChatbot(jwt_token=jwt_token, top_k=3, max_memory_turns=10, max_conversations=10)
        print(f"✅ Đã khởi tạo chatbot cho user: {bot.get_user_id()}")
    except ValueError as e:
        print(f"❌ Lỗi JWT: {e}")
        return

    print("🤖 Chatbot với MongoDB và quản lý user đã sẵn sàng!")
    print("Gõ '/help' để xem hướng dẫn, 'quit' hoặc 'exit' để thoát\n")

    while True:
        try:
            # Đọc câu hỏi từ stdin. Dùng strip() để loại bỏ khoảng trắng thừa.
            query = input("Bạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTạm biệt!")
            break

        # Điều kiện thoát
        if query.lower() in {"exit", "quit"}:
            # Đồng bộ dữ liệu trước khi thoát
            print("🔄 Đang đồng bộ dữ liệu...")
            bot.sync_to_database()
            print("Tạm biệt!")
            break

        if not query:
            print("Vui lòng nhập câu hỏi hợp lệ.")
            continue

        # Xử lý lệnh đặc biệt
        if query.startswith("/"):
            if query == "/help":
                show_help()
            elif query.startswith("/jwt "):
                new_jwt_token = query.split(" ", 1)[1].strip()
                if new_jwt_token:
                    if bot.update_jwt_token(new_jwt_token):
                        print(f"✅ Đã cập nhật JWT token cho user: {bot.get_user_id()}\n")
                    else:
                        print(f"❌ JWT token không hợp lệ.\n")
                else:
                    print("❌ Vui lòng nhập JWT token.\n")
            elif query == "/jwt-info":
                token_info = get_token_info(bot.get_jwt_token())
                print(f"\n🔐 Thông tin JWT token:")
                print(f"   ✅ Valid: {token_info['valid']}")
                print(f"   🔐 Verified: {token_info.get('verified', 'Unknown')}")
                print(f"   👤 User ID: {token_info['user_id']}")
                print(f"   ⏰ Expired: {token_info['expired']}")
                print(f"   📅 Expiration: {token_info['expiration']}")
                print(f"   🔑 Available keys: {token_info.get('available_keys', [])}")
                if token_info.get('payload'):
                    print(f"   📋 Payload: {token_info['payload']}")
                print()
            elif query.startswith("/user "):
                new_user_id = query.split(" ", 1)[1].strip()
                if new_user_id:
                    # Đồng bộ dữ liệu hiện tại trước khi chuyển user
                    bot.sync_to_database()
                    
                    # Tạo chatbot mới cho user
                    current_user_id = new_user_id
                    bot = CompanyChatbot(user_id=current_user_id, top_k=3, max_memory_turns=10, max_conversations=10)
                    print(f"👤 Đã chuyển sang user: {current_user_id}\n")
                else:
                    print("❌ Vui lòng nhập user ID.\n")
            elif query == "/memory":
                summary = bot.get_memory_summary()
                count = bot.get_memory_count()
                print(f"\n📝 Lịch sử hội thoại hiện tại: {summary}")
                print(f"📊 Số lượt hội thoại: {count}\n")
            elif query == "/clear":
                bot.clear_memory()
                print("🗑️ Đã xóa lịch sử hội thoại hiện tại.\n")
            elif query == "/new":
                first_question = input("Nhập câu hỏi đầu tiên cho cuộc hội thoại mới: ").strip()
                if first_question:
                    conv_id = bot.create_new_conversation(first_question)
                    print(f"✅ Đã tạo cuộc hội thoại mới với ID: {conv_id}\n")
                else:
                    print("❌ Vui lòng nhập câu hỏi.\n")
            elif query == "/list":
                conversations = bot.get_conversation_list()
                if conversations:
                    print("\n📋 Danh sách cuộc hội thoại:")
                    for i, conv in enumerate(conversations, 1):
                        status = "🟢" if conv["is_active"] else "⚪"
                        print(f"{i}. {status} {conv['name']} (ID: {conv['id']})")
                        print(f"   📅 Tạo: {conv['created_at']} | 💬 Lượt: {conv['turn_count']}")
                    print()
                else:
                    print("📋 Chưa có cuộc hội thoại nào.\n")
            elif query.startswith("/switch "):
                conv_id = query.split(" ", 1)[1].strip()
                if bot.switch_conversation(conv_id):
                    print(f"✅ Đã chuyển sang cuộc hội thoại: {conv_id}\n")
                else:
                    print(f"❌ Không tìm thấy cuộc hội thoại với ID: {conv_id}\n")
            elif query.startswith("/delete "):
                conv_id = query.split(" ", 1)[1].strip()
                if bot.delete_conversation(conv_id):
                    print(f"✅ Đã xóa cuộc hội thoại: {conv_id}\n")
                else:
                    print(f"❌ Không tìm thấy cuộc hội thoại với ID: {conv_id}\n")
            elif query == "/current":
                current_info = bot.get_current_conversation_info()
                if current_info:
                    print(f"\n📌 Cuộc hội thoại hiện tại:")
                    print(f"   🏷️ Tên: {current_info['name']}")
                    print(f"   🆔 ID: {current_info['id']}")
                    print(f"   📅 Tạo: {current_info['created_at']}")
                    print(f"   💬 Lượt hội thoại: {current_info['turn_count']}\n")
                else:
                    print("📌 Chưa có cuộc hội thoại nào.\n")
            elif query == "/sync":
                if bot.sync_to_database():
                    print("✅ Đã đồng bộ dữ liệu vào database.\n")
                else:
                    print("❌ Lỗi đồng bộ dữ liệu.\n")
            else:
                print("❌ Lệnh không hợp lệ. Gõ '/help' để xem hướng dẫn.\n")
            continue

        # Gọi chatbot để lấy câu trả lời
        answer = bot.ask(query)
        print(f"Bot: {answer}\n")


if __name__ == "__main__":
    main()


