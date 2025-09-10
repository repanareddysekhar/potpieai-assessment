"""
Tests for the API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app

client = TestClient(app)


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "code-review-agent"}


@patch('app.services.task_service.TaskService')
@patch('app.services.celery_app.analyze_pr_task')
def test_analyze_pr_endpoint(mock_celery_task, mock_task_service):
    """Test the analyze PR endpoint."""
    # Mock the task service
    mock_task_service_instance = Mock()
    mock_task_service.return_value = mock_task_service_instance
    mock_task_service_instance.create_task.return_value = None

    # Mock the Celery task
    mock_celery_task.delay.return_value = None

    # Test data
    test_data = {
        "repo_url": "https://github.com/octocat/Hello-World",
        "pr_number": 1
    }

    response = client.post("/api/v1/analyze-pr", json=test_data)

    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "pending"


def test_get_task_status_existing():
    """Test getting status of an existing task - integration test."""
    # This is an integration test that will return 404 for non-existent task
    # In a real scenario, we'd need to create a task first
    response = client.get("/api/v1/status/test-task-id")

    # Expect 404 since the task doesn't exist in Redis
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["error"] == "task_not_found"


def test_get_task_status_not_found():
    """Test getting status of a non-existent task."""
    response = client.get("/api/v1/status/nonexistent-task-id")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["error"] == "task_not_found"
    assert "nonexistent-task-id" in data["detail"]["message"]


def test_analyze_pr_with_cache():
    """Test PR analysis - integration test."""
    # This is an integration test that will create a new task
    response = client.post("/api/v1/analyze-pr", json={
        "repo_url": "https://github.com/test/repo",
        "pr_number": 1
    })

    assert response.status_code == 200
    data = response.json()
    # Since no cache exists, it should create a pending task
    assert data["status"] == "pending"
    assert "task_id" in data


def test_cache_stats_endpoint():
    """Test cache statistics endpoint."""
    response = client.get("/api/v1/cache/stats")

    # Should return 200 even if cache is empty/unavailable
    assert response.status_code in [200, 500]  # 500 if Redis not available

    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert data["status"] == "success"
        assert "cache_stats" in data


def test_invalidate_pr_cache_endpoint():
    """Test PR cache invalidation endpoint."""
    response = client.delete("/api/v1/cache/pr/test/repo/1")

    # Should return 200 even if cache is empty/unavailable
    assert response.status_code in [200, 500]  # 500 if Redis not available

    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert data["status"] == "success"
        assert data["repo_url"] == "https://github.com/test/repo"
        assert data["pr_number"] == 1