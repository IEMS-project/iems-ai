"""
Generator: Sinh câu trả lời tiếng Việt từ LLM dựa trên context lấy từ retriever.

- Dùng `get_llm()` từ `config/model_config.py`
- Load prompts từ file trong thư mục `prompts/`
- Gộp nhiều đoạn context thành một prompt hướng dẫn rõ ràng
- Trả về câu trả lời tự nhiên, dễ hiểu, trích dẫn theo ngữ cảnh nội bộ
"""

from __future__ import annotations

from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

from config.model_config import get_llm
from prompts.prompt_manager import get_system_prompt, format_user_prompt


def _render_context(docs: List[Document]) -> str:
    """Ghép nhiều Document thành một chuỗi context, có phân tách rõ ràng."""
    if not docs:
        return "(Không tìm thấy thông tin liên quan trong tài liệu nội bộ)"
    rendered = []
    for idx, d in enumerate(docs, 1):
        source = d.metadata.get("source", "<unknown>")
        rendered.append(f"[Đoạn {idx} — nguồn: {source}]\n{d.page_content}")
    return "\n\n---\n\n".join(rendered)


def generate_answer(query: str, context_docs: List[Document]) -> str:
    """Gọi LLM để sinh câu trả lời dựa trên các đoạn context cung cấp.

    - query: câu hỏi của người dùng
    - context_docs: danh sách Document từ retriever
    - trả về: chuỗi câu trả lời tiếng Việt
    """
    print("[generator] Chuẩn bị prompt và gọi LLM...")
    llm = get_llm()

    # Load prompts từ file
    system_prompt = get_system_prompt()
    context_str = _render_context(context_docs)
    user_prompt = format_user_prompt(context_str, query)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt),
    ])

    chain = prompt | llm
    result = chain.invoke({})

    # `result` là một AIMessage; cần lấy .content
    answer = getattr(result, "content", None)
    if not answer:
        return "Xin lỗi, tôi chưa thể tạo câu trả lời lúc này. Bạn có thể thử lại sau nhé! 😊"
    print("[generator] Hoàn tất sinh câu trả lời.")
    return answer.strip()


def generate_answer_stream(query: str, context_docs: List[Document]):
    """Gọi LLM để sinh câu trả lời streaming dựa trên các đoạn context cung cấp.

    - query: câu hỏi của người dùng
    - context_docs: danh sách Document từ retriever
    - trả về: generator của các chunk text
    """
    print("[generator] Chuẩn bị prompt và gọi LLM streaming...")
    llm = get_llm()

    # Load prompts từ file
    system_prompt = get_system_prompt()
    context_str = _render_context(context_docs)
    user_prompt = format_user_prompt(context_str, query)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt),
    ])

    chain = prompt | llm
    
    try:
        # Streaming response từ LLM
        for chunk in chain.stream({}):
            if hasattr(chunk, 'content') and chunk.content:
                yield chunk.content
    except Exception as e:
        print(f"[generator] Lỗi streaming: {e}")
        yield f"Xin lỗi, có lỗi xảy ra khi tạo câu trả lời: {str(e)}"


