"""
Tests for task service functionality.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json

from app.services.task_service import TaskService
from app.models.schemas import TaskStatus, TaskStatusResponse


class TestTaskService:
    """Test cases for TaskService."""

    def test_task_service_init(self):
        """Test TaskService initialization."""
        with patch('redis.from_url') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            
            service = TaskService()
            
            assert service.redis_client == mock_client

    def test_get_task_key(self):
        """Test task key generation."""
        service = TaskService()
        
        key = service._get_task_key("test-123")
        assert key == "task:test-123"

    @pytest.mark.asyncio
    async def test_check_cached_result_no_cache(self):
        """Test check_cached_result when no cache exists."""
        with patch('redis.from_url') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.get.return_value = None
            
            service = TaskService()
            result = await service.check_cached_result("https://github.com/owner/repo", 123)
            
            assert result is None



    @pytest.mark.asyncio
    async def test_get_task_status_not_found(self):
        """Test get_task_status for non-existent task."""
        with patch('redis.from_url') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.get.return_value = None
            
            service = TaskService()
            result = await service.get_task_status("non-existent")
            
            assert result is None



    def test_task_key_generation(self):
        """Test task key generation consistency."""
        service = TaskService()
        
        key1 = service._get_task_key("abc-123")
        key2 = service._get_task_key("abc-123")
        
        assert key1 == key2
        assert key1 == "task:abc-123"
