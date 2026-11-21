"""Tasks API router: CRUD operations, filtering, search, and metrics."""

import math
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from taskforge.auth import get_current_user
from taskforge.database import get_db
from taskforge.schemas import (
    TaskListResponse,
    TaskPriority,
    TaskResponse,
    TaskStatsResponse,
    TaskStatus,
    TaskCreateRequest,
    TaskUpdateRequest,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(req: TaskCreateRequest, current_user: dict = Depends(get_current_user)):
    """Create a new task belonging to the authenticated user."""
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tasks (id, user_id, title, description, status, priority, due_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                current_user["id"],
                req.title.strip(),
                req.description.strip() if req.description else None,
                TaskStatus.TODO.value,
                req.priority.value,
                req.due_date,
                now,
                now,
            ),
        )

    return TaskResponse(
        id=task_id,
        user_id=current_user["id"],
        title=req.title.strip(),
        description=req.description.strip() if req.description else None,
        status=TaskStatus.TODO,
        priority=req.priority,
        due_date=req.due_date,
        created_at=now,
        updated_at=now,
    )


@router.get("", response_model=TaskListResponse)
def list_tasks(
    current_user: dict = Depends(get_current_user),
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    priority_filter: Optional[TaskPriority] = Query(None, alias="priority"),
    search: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    """List and paginate tasks owned by the current user with optional filtering."""
    query = "SELECT id, user_id, title, description, status, priority, due_date, created_at, updated_at FROM tasks WHERE user_id = ?"
    count_query = "SELECT COUNT(*) FROM tasks WHERE user_id = ?"
    params = [current_user["id"]]
    count_params = [current_user["id"]]

    if status_filter:
        query += " AND status = ?"
        count_query += " AND status = ?"
        params.append(status_filter.value)
        count_params.append(status_filter.value)

    if priority_filter:
        query += " AND priority = ?"
        count_query += " AND priority = ?"
        params.append(priority_filter.value)
        count_params.append(priority_filter.value)

    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        count_query += " AND (title LIKE ? OR description LIKE ?)"
        like_term = f"%{search.strip()}%"
        params.extend([like_term, like_term])
        count_params.extend([like_term, like_term])

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    offset = (page - 1) * page_size
    params.extend([page_size, offset])

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]

        cursor.execute(query, params)
        rows = cursor.fetchall()

    items = [
        TaskResponse(
            id=r["id"],
            user_id=r["user_id"],
            title=r["title"],
            description=r["description"],
            status=TaskStatus(r["status"]),
            priority=TaskPriority(r["priority"]),
            due_date=r["due_date"],
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"]),
        )
        for r in rows
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return TaskListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/stats/summary", response_model=TaskStatsResponse)
def get_task_stats(current_user: dict = Depends(get_current_user)):
    """Get aggregated status and priority statistics for the current user's tasks."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, priority FROM tasks WHERE user_id = ?", (current_user["id"],))
        rows = cursor.fetchall()

    total = len(rows)
    todo = sum(1 for r in rows if r["status"] == "todo")
    in_progress = sum(1 for r in rows if r["status"] == "in_progress")
    completed = sum(1 for r in rows if r["status"] == "completed")
    cancelled = sum(1 for r in rows if r["status"] == "cancelled")
    critical = sum(1 for r in rows if r["priority"] == "critical")
    high = sum(1 for r in rows if r["priority"] == "high")

    return TaskStatsResponse(
        total_tasks=total,
        todo_count=todo,
        in_progress_count=in_progress,
        completed_count=completed,
        cancelled_count=cancelled,
        critical_count=critical,
        high_count=high,
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, current_user: dict = Depends(get_current_user)):
    """Retrieve a specific task by ID if owned by the caller."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, title, description, status, priority, due_date, created_at, updated_at FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, current_user["id"]),
        )
        row = cursor.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found or access denied",
        )

    return TaskResponse(
        id=row["id"],
        user_id=row["user_id"],
        title=row["title"],
        description=row["description"],
        status=TaskStatus(row["status"]),
        priority=TaskPriority(row["priority"]),
        due_date=row["due_date"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    req: TaskUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update fields of an existing task owned by the caller."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, title, description, status, priority, due_date, created_at FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, current_user["id"]),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_id}' not found or access denied",
            )

        new_title = req.title.strip() if req.title is not None else row["title"]
        new_desc = req.description.strip() if req.description is not None else row["description"]
        new_status = req.status.value if req.status is not None else row["status"]
        new_priority = req.priority.value if req.priority is not None else row["priority"]
        new_due_date = req.due_date if req.due_date is not None else row["due_date"]
        now = datetime.now(timezone.utc).isoformat()

        cursor.execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, status = ?, priority = ?, due_date = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (new_title, new_desc, new_status, new_priority, new_due_date, now, task_id, current_user["id"]),
        )

    return TaskResponse(
        id=task_id,
        user_id=current_user["id"],
        title=new_title,
        description=new_desc,
        status=TaskStatus(new_status),
        priority=TaskPriority(new_priority),
        due_date=new_due_date,
        created_at=str(row["created_at"]),
        updated_at=now,
    )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a task owned by the caller."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tasks WHERE id = ? AND user_id = ?", (task_id, current_user["id"]))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_id}' not found or access denied",
            )
        cursor.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, current_user["id"]))

    return None
