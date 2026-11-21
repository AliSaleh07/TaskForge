"""Tests for task CRUD, pagination, filtering, security isolation, and statistics."""

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def user_tokens(client: TestClient):
    """Create two separate users and return their JWT tokens."""
    # User 1
    client.post(
        "/api/v1/auth/register",
        json={"username": "user_one", "email": "user1@example.com", "password": "Password123"},
    )
    res1 = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "user_one", "password": "Password123"},
    )
    token1 = res1.json()["access_token"]

    # User 2
    client.post(
        "/api/v1/auth/register",
        json={"username": "user_two", "email": "user2@example.com", "password": "Password123"},
    )
    res2 = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "user_two", "password": "Password123"},
    )
    token2 = res2.json()["access_token"]

    return {"token1": token1, "token2": token2}


def test_task_lifecycle_and_ownership(client: TestClient, user_tokens):
    headers1 = {"Authorization": f"Bearer {user_tokens['token1']}"}
    headers2 = {"Authorization": f"Bearer {user_tokens['token2']}"}

    # 1. Create a task for User 1
    create_res = client.post(
        "/api/v1/tasks",
        headers=headers1,
        json={
            "title": "Implement JWT Auth",
            "description": "Ensure HMAC-SHA256 signature verification works",
            "priority": "critical",
            "due_date": "2026-12-01",
        },
    )
    assert create_res.status_code == 201
    task = create_res.json()
    task_id = task["id"]
    assert task["title"] == "Implement JWT Auth"
    assert task["status"] == "todo"
    assert task["priority"] == "critical"

    # 2. Get task by ID (User 1)
    get_res = client.get(f"/api/v1/tasks/{task_id}", headers=headers1)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == task_id

    # 3. Security Isolation: User 2 must NOT be able to view User 1's task
    forbidden_get = client.get(f"/api/v1/tasks/{task_id}", headers=headers2)
    assert forbidden_get.status_code == 404

    # 4. Security Isolation: User 2 must NOT be able to modify User 1's task
    forbidden_update = client.put(
        f"/api/v1/tasks/{task_id}",
        headers=headers2,
        json={"title": "Hacked Title"},
    )
    assert forbidden_update.status_code == 404

    # 5. User 1 updates task
    update_res = client.put(
        f"/api/v1/tasks/{task_id}",
        headers=headers1,
        json={"status": "in_progress", "priority": "high"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "in_progress"
    assert update_res.json()["priority"] == "high"

    # 6. User 1 checks stats
    stats_res = client.get("/api/v1/tasks/stats/summary", headers=headers1)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_tasks"] == 1
    assert stats["in_progress_count"] == 1

    # 7. List and filter tasks
    list_res = client.get("/api/v1/tasks?status=in_progress", headers=headers1)
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1

    list_empty = client.get("/api/v1/tasks?status=completed", headers=headers1)
    assert list_empty.json()["total"] == 0

    # 8. User 1 deletes task
    del_res = client.delete(f"/api/v1/tasks/{task_id}", headers=headers1)
    assert del_res.status_code == 204

    # 9. Verify task is gone
    gone_res = client.get(f"/api/v1/tasks/{task_id}", headers=headers1)
    assert gone_res.status_code == 404
