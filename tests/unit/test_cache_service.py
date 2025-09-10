"""
Tests for the cache service.
"""
import pytest
from unittest.mock import Mock, patch
import json

from app.services.cache_service import CacheService


class TestCacheService:
    """Test cases for CacheService."""

    @patch('app.services.cache_service.redis.from_url')
    def test_cache_service_init(self, mock_redis_from_url):
        """Test cache service initialization."""
        cache_service = CacheService()

        assert cache_service.default_ttl == 3600
        mock_redis_from_url.assert_called_once()

    @patch('app.services.cache_service.redis.from_url')
    def test_generate_cache_key(self, mock_redis_from_url):
        """Test cache key generation."""
        cache_service = CacheService()

        key1 = cache_service._generate_cache_key("test", param1="value1", param2="value2")
        key2 = cache_service._generate_cache_key("test", param2="value2", param1="value1")

        # Same parameters in different order should generate same key
        assert key1 == key2
        assert key1.startswith("test:")

    @patch('app.services.cache_service.redis.from_url')
    def test_pr_analysis_cache_key(self, mock_redis_from_url):
        """Test PR analysis cache key generation."""
        cache_service = CacheService()

        key = cache_service.get_pr_analysis_cache_key(
            "https://github.com/test/repo",
            123
        )

        assert key.startswith("pr_analysis:")

    @patch('app.services.cache_service.redis.from_url')
    def test_file_analysis_cache_key(self, mock_redis_from_url):
        """Test file analysis cache key generation."""
        cache_service = CacheService()

        key = cache_service.get_file_analysis_cache_key(
            "https://github.com/test/repo",
            123,
            "src/main.py",
            "abc123"
        )

        assert key.startswith("file_analysis:")

    def test_cache_key_consistency(self):
        """Test that cache keys are consistent for same parameters."""
        # This test doesn't need Redis mocking
        from app.services.cache_service import CacheService

        # Create a temporary instance just for testing key generation
        cache_service = CacheService.__new__(CacheService)

        key1 = cache_service._generate_cache_key("test", param1="value1", param2="value2")
        key2 = cache_service._generate_cache_key("test", param2="value2", param1="value1")

        # Same parameters in different order should generate same key
        assert key1 == key2
        assert key1.startswith("test:")

        # Different parameters should generate different keys
        key3 = cache_service._generate_cache_key("test", param1="different", param2="value2")
        assert key1 != key3
