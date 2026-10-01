"""
Tests for API endpoints (/health, /api/v1/tasks, /api/v1/tasks/{id}, /api/v1/tasks/{id}/approve).
"""
import time
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data


@pytest.mark.asyncio
async def test_create_task_endpoint(client: AsyncClient, mock_redis):
    start_time = time.time()
    payload = {"prompt": "Research the key features of LangGraph and CrewAI."}
    response = await client.post("/api/v1/tasks", json=payload)
    elapsed_ms = (time.time() - start_time) * 1000

    assert response.status_code == 202
    assert elapsed_ms < 1000, f"Endpoint took {elapsed_ms}ms, expected under 1000ms"

    data = response.json()
    assert "task_id" in data
    assert data["status"] == "PENDING"
    assert len(data["task_id"]) > 0


@pytest.mark.asyncio
async def test_get_task_endpoint(client: AsyncClient, mock_redis):
    # 1. Create a task first
    payload = {"prompt": "Analyze LangGraph architecture"}
    create_res = await client.post("/api/v1/tasks", json=payload)
    assert create_res.status_code == 202
    task_id = create_res.json()["task_id"]

    # 2. Get task details
    get_res = await client.get(f"/api/v1/tasks/{task_id}")
    assert get_res.status_code == 200
    task_data = get_res.json()

    assert task_data["id"] == task_id
    assert task_data["prompt"] == payload["prompt"]
    assert task_data["status"] == "PENDING"
    assert "created_at" in task_data
    assert "updated_at" in task_data


@pytest.mark.asyncio
async def test_get_nonexistent_task(client: AsyncClient):
    response = await client.get("/api/v1/tasks/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_approve_task_endpoint(client: AsyncClient, mock_redis):
    # 1. Create task
    create_res = await client.post("/api/v1/tasks", json={"prompt": "Multi-agent review"})
    task_id = create_res.json()["task_id"]

    # 2. Call approve endpoint
    approve_payload = {"approved": True, "feedback": "Include security implications"}
    approve_res = await client.post(f"/api/v1/tasks/{task_id}/approve", json=approve_payload)

    assert approve_res.status_code == 200
    data = approve_res.json()
    assert data["task_id"] == task_id
    assert data["status"] == "RESUMED"

    # 3. Verify task status in database
    get_res = await client.get(f"/api/v1/tasks/{task_id}")
    assert get_res.json()["status"] == "RESUMED"
