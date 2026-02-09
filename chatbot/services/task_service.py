"""
Task Management Service: Fetches and prioritizes user's tasks from the task API.

Features:
- Detects task-related queries
- Fetches tasks from http://localhost:8080/task-service/tasks/my-tasks
- Analyzes and prioritizes tasks based on status, priority, and due date
- Returns formatted markdown response
"""

from __future__ import annotations

import requests
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
import re


def is_task_related_query(query: str) -> bool:
    """
    Kiểm tra xem câu hỏi có liên quan đến task/công việc không.
    
    Args:
        query: Câu hỏi của người dùng
        
    Returns:
        True nếu câu hỏi liên quan đến task
    """
    # Danh sách các từ khóa liên quan đến task (tiếng Việt và tiếng Anh)
    task_keywords = [
        # Tiếng Việt
        r'\bcông việc\b', r'\btask\b', r'\bviệc\b', r'\bđầu việc\b',
        r'\bcần làm\b', r'\bphải làm\b', r'\blàm gì\b', r'\bcần hoàn thành\b',
        r'\bưu tiên\b', r'\bhạn\b', r'\bdeadline\b', r'\bdự án\b',
        r'\bproject\b', r'\bhôm nay\b', r'\btuần này\b', r'\bngày mai\b',
        r'\bto.?do\b', r'\btodo\b', r'\bchecklist\b',
        # Tiếng Anh
        r'\btodo\b', r'\btask\b', r'\bwork\b', r'\bjob\b',
        r'\bassignment\b', r'\bpriority\b', r'\bdue\b', r'\bdeadline\b',
        r'\btoday\b', r'\btomorrow\b', r'\bthis week\b', r'\bproject\b',
    ]
    
    query_lower = query.lower()
    
    # Kiểm tra từng keyword
    for keyword in task_keywords:
        if re.search(keyword, query_lower):
            return True
    
    return False


def fetch_tasks(jwt_token: str, api_url: str = "http://localhost:8080/task-service/tasks/my-tasks") -> Tuple[bool, Optional[List[Dict]], Optional[str]]:
    """
    Lấy danh sách tasks từ API.
    
    Args:
        jwt_token: JWT token để authentication
        api_url: URL của API endpoint
        
    Returns:
        Tuple (success, tasks_data, error_message)
    """
    try:
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and "data" in data:
                return True, data["data"], None
            else:
                return False, None, f"API trả về status không thành công: {data.get('message', 'Unknown error')}"
        elif response.status_code == 401:
            return False, None, "JWT token không hợp lệ hoặc đã hết hạn"
        elif response.status_code == 404:
            return False, None, "API endpoint không tồn tại"
        else:
            return False, None, f"Lỗi khi gọi API: HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        return False, None, "Timeout khi kết nối tới task service"
    except requests.exceptions.ConnectionError:
        return False, None, "Không thể kết nối tới task service. Vui lòng kiểm tra xem service đã chạy chưa"
    except Exception as e:
        return False, None, f"Lỗi không xác định: {str(e)}"


def parse_date(date_str: Optional[str]) -> Optional[date]:
    """
    Chuyển đổi string date sang datetime.date.
    
    Args:
        date_str: String ngày tháng (YYYY-MM-DD hoặc ISO timestamp)
        
    Returns:
        datetime.date object hoặc None
    """
    if not date_str:
        return None
    
    try:
        # Thử parse ISO timestamp trước
        if 'T' in date_str:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
        # Thử parse YYYY-MM-DD
        else:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return None


def calculate_priority_score(task: Dict) -> Tuple[int, int, int]:
    """
    Tính điểm ưu tiên cho task.
    Trả về tuple (priority_score, days_until_due, status_score) để sort.
    
    Score cao hơn = ưu tiên cao hơn
    """
    # Priority score
    priority_map = {
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1,
    }
    priority_score = priority_map.get(task.get("priority", "LOW"), 0)
    
    # Status score (IN_PROGRESS được ưu tiên cao hơn TO_DO)
    status_map = {
        "IN_PROGRESS": 2,
        "TO_DO": 1,
        "COMPLETED": 0,
    }
    status_score = status_map.get(task.get("status", "TO_DO"), 0)
    
    # Days until due (âm nếu quá hạn, dương nếu còn thời gian)
    due_date = parse_date(task.get("dueDate"))
    if due_date:
        today = date.today()
        days_until_due = (due_date - today).days
    else:
        # Không có due date -> ưu tiên thấp (cho về cuối)
        days_until_due = 999
    
    # Trả về tuple để sort: (status_score desc, priority_score desc, days_until_due asc)
    # Nghĩa là: IN_PROGRESS trước, HIGH priority trước, sắp hết hạn trước
    return (status_score, priority_score, -days_until_due)


def filter_and_prioritize_tasks(tasks: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    Lọc và ưu tiên các tasks.
    
    Args:
        tasks: Danh sách tất cả tasks
        
    Returns:
        Tuple (top_tasks, other_tasks)
    """
    # Chỉ lấy tasks chưa hoàn thành
    active_tasks = [
        task for task in tasks 
        if task.get("status") in ["TO_DO", "IN_PROGRESS"]
    ]
    
    # Sort theo priority score
    sorted_tasks = sorted(
        active_tasks,
        key=lambda t: calculate_priority_score(t),
        reverse=True
    )
    
    # Lấy top 3-5 tasks (tùy số lượng)
    num_top_tasks = min(5, len(sorted_tasks))
    top_tasks = sorted_tasks[:num_top_tasks]
    other_tasks = sorted_tasks[num_top_tasks:]
    
    return top_tasks, other_tasks


def format_task_markdown(task: Dict, include_reason: bool = False) -> str:
    """
    Format một task thành markdown string.
    
    Args:
        task: Task object
        include_reason: Có bao gồm lý do ưu tiên không
        
    Returns:
        Markdown formatted string
    """
    title = task.get("title", "Untitled")
    project_name = task.get("projectName", "Unknown Project")
    due_date = task.get("dueDate", "No due date")
    priority = task.get("priority", "LOW")
    task_type = task.get("taskType", "TASK")
    status = task.get("status", "TO_DO")
    
    # Format due date
    due_date_obj = parse_date(due_date)
    if due_date_obj:
        today = date.today()
        days_diff = (due_date_obj - today).days
        if days_diff < 0:
            due_date_display = f"{due_date} (Quá hạn {abs(days_diff)} ngày)"
        elif days_diff == 0:
            due_date_display = f"{due_date} (Hôm nay!)"
        elif days_diff == 1:
            due_date_display = f"{due_date} (Ngày mai)"
        elif days_diff <= 3:
            due_date_display = f"{due_date} (Còn {days_diff} ngày)"
        else:
            due_date_display = f"{due_date} (Còn {days_diff} ngày)"
    else:
        due_date_display = "Không có deadline"
    
    # Build markdown without emoji
    result = f"**{title}**\n"
    result += f"  - Project: {project_name}\n"
    result += f"  - Status: {status}\n"
    result += f"  - Due: {due_date_display}\n"
    result += f"  - Priority: {priority}\n"
    result += f"  - Type: {task_type}\n"
    
    # Add reason if requested
    if include_reason:
        reason = generate_priority_reason(task)
        result += f"  - Lý do ưu tiên: {reason}\n"
    
    return result


def generate_priority_reason(task: Dict) -> str:
    """
    Tạo lý do tại sao task này được ưu tiên.
    
    Args:
        task: Task object
        
    Returns:
        Reason string
    """
    reasons = []
    
    # Check status
    if task.get("status") == "IN_PROGRESS":
        reasons.append("đang thực hiện")
    
    # Check priority
    if task.get("priority") == "HIGH":
        reasons.append("độ ưu tiên cao")
    
    # Check due date
    due_date_obj = parse_date(task.get("dueDate"))
    if due_date_obj:
        today = date.today()
        days_diff = (due_date_obj - today).days
        if days_diff < 0:
            reasons.append(f"đã quá hạn {abs(days_diff)} ngày")
        elif days_diff == 0:
            reasons.append("deadline hôm nay")
        elif days_diff <= 3:
            reasons.append(f"sắp đến hạn (còn {days_diff} ngày)")
    
    if not reasons:
        return "Task quan trọng cần hoàn thành"
    
    return ", ".join(reasons).capitalize()


def generate_task_response(top_tasks: List[Dict], other_tasks: List[Dict]) -> str:
    """
    Tạo response markdown cho task prioritization.
    
    Args:
        top_tasks: Top 3-5 tasks ưu tiên
        other_tasks: Các tasks còn lại
        
    Returns:
        Markdown formatted response
    """
    today = date.today().strftime("%d/%m/%Y")
    
    response = f"# Danh sách công việc ưu tiên - {today}\n\n"
    
    # Top tasks
    if top_tasks:
        response += f"## Top {len(top_tasks)} việc cần làm trước:\n\n"
        for idx, task in enumerate(top_tasks, 1):
            response += f"### {idx}. {format_task_markdown(task, include_reason=True)}\n"
    else:
        response += "## Tuyệt vời! Bạn không có task nào cần làm ngay bây giờ.\n\n"
    
    # Other tasks
    if other_tasks:
        response += f"\n## Các việc khác ({len(other_tasks)} tasks):\n\n"
        for task in other_tasks:
            response += f"- {format_task_markdown(task, include_reason=False)}\n"
    
    # Summary
    total_tasks = len(top_tasks) + len(other_tasks)
    response += f"\n---\n**Tổng cộng: {total_tasks} tasks đang active**\n"
    
    return response


def handle_task_query(jwt_token: str, query: str) -> str:
    """
    Xử lý câu hỏi liên quan đến tasks.
    
    Args:
        jwt_token: JWT token để authentication
        query: Câu hỏi của người dùng
        
    Returns:
        Response string (markdown formatted)
    """
    print("[task_service] Đang xử lý câu hỏi về tasks...")
    
    # Fetch tasks from API
    success, tasks, error = fetch_tasks(jwt_token)
    
    if not success:
        return f"❌ Không thể lấy danh sách tasks: {error}"
    
    if not tasks:
        return "ℹ️ Bạn chưa có task nào được gán. Hãy liên hệ với project manager để được gán công việc nhé!"
    
    print(f"[task_service] Đã lấy được {len(tasks)} tasks từ API")
    
    # Filter and prioritize
    top_tasks, other_tasks = filter_and_prioritize_tasks(tasks)
    
    # Generate response
    response = generate_task_response(top_tasks, other_tasks)
    
    print("[task_service] Hoàn thành xử lý task query")
    return response
