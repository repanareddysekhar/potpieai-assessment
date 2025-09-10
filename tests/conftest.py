"""
Pytest configuration and shared fixtures.
"""
import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
import redis
from typing import Dict, Any, Generator
import json
from datetime import datetime, timedelta

from app.main import app
from app.core.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch('redis.from_url') as mock:
        mock_client = Mock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_github_service():
    """Mock GitHub service."""
    with patch('app.services.github_service.GitHubService') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_ai_agent():
    """Mock AI agent."""
    with patch('app.services.ai_agent.CodeReviewAgent') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_task_service():
    """Mock task service."""
    with patch('app.services.task_service.TaskService') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_cache_service():
    """Mock cache service."""
    with patch('app.services.cache_service.CacheService') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_pr_data():
    """Sample PR data for testing."""
    return {
        "repo_url": "https://github.com/owner/repo",
        "pr_number": 123,
        "files": [
            {
                "filename": "src/main.py",
                "status": "modified",
                "patch": "@@ -1,3 +1,4 @@\n def hello():\n+    print('world')\n     pass"
            }
        ]
    }


@pytest.fixture
def sample_analysis_results():
    """Sample analysis results for testing."""
    return {
        "files": [
            {
                "name": "main.py",
                "path": "src/main.py",
                "language": "python",
                "issues": [
                    {
                        "type": "style",
                        "line": 1,
                        "description": "Missing docstring",
                        "suggestion": "Add function docstring"
                    }
                ]
            }
        ],
        "summary": {
            "total_files": 1,
            "total_issues": 1,
            "critical_issues": 0,
            "files_with_issues": 1,
            "languages_detected": ["python"]
        }
    }


@pytest.fixture(autouse=True)
def clean_environment():
    """Clean environment variables for each test."""
    with patch.dict('os.environ', {
        'DATABASE_URL': 'sqlite:///test.db',
        'REDIS_URL': 'redis://localhost:6379/0',
        'CELERY_BROKER_URL': 'redis://localhost:6379/0',
        'CELERY_RESULT_BACKEND': 'redis://localhost:6379/0',
        'SECRET_KEY': 'test-secret-key',
        'DEBUG': 'false'
    }, clear=True):
        yield


# ============================================================================
# ENHANCED FIXTURES FOR COMPREHENSIVE TESTING
# ============================================================================

@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    yield f"sqlite:///{db_path}"

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def mock_redis_with_data():
    """Mock Redis client with predefined data."""
    with patch('redis.from_url') as mock:
        mock_client = Mock()

        # Mock data storage
        data_store = {}

        def mock_get(key):
            return data_store.get(key)

        def mock_set(key, value, ex=None):
            data_store[key] = value
            return True

        def mock_delete(key):
            return data_store.pop(key, None) is not None

        def mock_exists(key):
            return key in data_store

        def mock_keys(pattern="*"):
            if pattern == "*":
                return list(data_store.keys())
            # Simple pattern matching for tests
            return [k for k in data_store.keys() if pattern.replace("*", "") in k]

        mock_client.get = mock_get
        mock_client.set = mock_set
        mock_client.delete = mock_delete
        mock_client.exists = mock_exists
        mock_client.keys = mock_keys
        mock_client.info.return_value = {
            'connected_clients': 1,
            'used_memory_human': '1.5M',
            'total_commands_processed': 1000,
            'keyspace_hits': 500,
            'keyspace_misses': 300
        }

        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_github_pr():
    """Sample GitHub PR data."""
    return {
        "number": 123,
        "title": "Add new feature",
        "body": "This PR adds a new feature to the application",
        "state": "open",
        "user": {"login": "testuser"},
        "head": {
            "sha": "abc123",
            "ref": "feature-branch"
        },
        "base": {
            "sha": "def456",
            "ref": "main"
        },
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z"
    }


@pytest.fixture
def sample_github_files():
    """Sample GitHub PR files."""
    return [
        {
            "filename": "src/main.py",
            "status": "modified",
            "additions": 10,
            "deletions": 5,
            "changes": 15,
            "patch": "@@ -1,3 +1,4 @@\n def hello():\n+    print('world')\n     pass"
        },
        {
            "filename": "tests/test_main.py",
            "status": "added",
            "additions": 20,
            "deletions": 0,
            "changes": 20,
            "patch": "@@ -0,0 +1,20 @@\n+import pytest\n+\n+def test_hello():\n+    assert True"
        }
    ]


@pytest.fixture
def mock_github_service_with_data(sample_github_pr, sample_github_files):
    """Mock GitHub service with realistic data."""
    with patch('app.services.github_service.GitHubService') as mock:
        mock_instance = Mock()

        # Mock methods
        mock_instance.get_pull_request.return_value = sample_github_pr
        mock_instance.get_pull_request_files.return_value = sample_github_files
        mock_instance.parse_repo_url.return_value = ("owner", "repo")

        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def performance_timer():
    """Timer fixture for performance testing."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            self.end_time = time.perf_counter()

        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return Timer()


@pytest.fixture
def large_pr_data():
    """Large PR data for performance testing."""
    files = []
    for i in range(100):  # 100 files
        files.append({
            "filename": f"src/module_{i}.py",
            "status": "modified",
            "additions": 50,
            "deletions": 20,
            "changes": 70,
            "patch": f"@@ -1,10 +1,15 @@\n" + "\n".join([f"+    line_{j}" for j in range(50)])
        })

    return {
        "repo_url": "https://github.com/large/repo",
        "pr_number": 999,
        "files": files
    }
