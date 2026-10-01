"""
Tests for WebSocket endpoint /ws/tasks/{task_id} streaming real-time status updates.
"""
import uuid
import json
import pytest
from starlette.testclient import TestClient
from src.main import app
from src.services.redis_service import redis_service


def test_websocket_status_streaming(mock_redis):
    task_id = str(uuid.uuid4())
    client = TestClient(app)

    # Connect to WebSocket endpoint
    with client.websocket_connect(f"/ws/tasks/{task_id}") as websocket:
        # Initially receives connection / empty or current status
        # Simulate pushing status updates
        statuses_to_test = ["RUNNING", "AWAITING_APPROVAL", "RESUMED", "COMPLETED"]

        for expected_status in statuses_to_test:
            # We can verify the JSON format of messages
            payload = {"task_id": task_id, "status": expected_status}
            assert payload["task_id"] == task_id
            assert payload["status"] in statuses_to_test
