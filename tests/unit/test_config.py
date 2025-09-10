"""
Tests for configuration settings.
"""
import pytest
import os
from unittest.mock import patch

from app.core.config import Settings, settings


class TestSettings:
    """Test cases for Settings configuration."""

    def test_settings_with_environment_variables(self):
        """Test configuration with environment variables."""
        env_vars = {
            "API_HOST": "127.0.0.1",
            "API_PORT": "8080",
            "DEBUG": "true",
            "DATABASE_URL": "postgresql://test:test@localhost/testdb",
            "REDIS_URL": "redis://localhost:6380/1",
            "CELERY_BROKER_URL": "redis://localhost:6380/1",
            "CELERY_RESULT_BACKEND": "redis://localhost:6380/1",
            "SECRET_KEY": "test-secret-key",
            "GITHUB_TOKEN": "test-github-token",
            "OPENAI_API_KEY": "test-openai-key"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            test_settings = Settings()

            assert test_settings.api_host == "127.0.0.1"
            assert test_settings.api_port == 8080
            assert test_settings.debug is True
            assert test_settings.database_url == "postgresql://test:test@localhost/testdb"
            assert test_settings.redis_url == "redis://localhost:6380/1"
            assert test_settings.github_token == "test-github-token"
            assert test_settings.openai_api_key == "test-openai-key"

    def test_settings_case_insensitive(self):
        """Test that environment variables are case insensitive."""
        env_vars = {
            "api_host": "192.168.1.1",
            "API_PORT": "9000",
            "SECRET_KEY": "test-secret"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            test_settings = Settings()

            assert test_settings.api_host == "192.168.1.1"
            assert test_settings.api_port == 9000

    def test_settings_type_conversion(self):
        """Test that environment variables are properly converted to correct types."""
        env_vars = {
            "API_PORT": "3000",
            "DEBUG": "false",
            "SECRET_KEY": "test-secret"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            test_settings = Settings()

            assert isinstance(test_settings.api_port, int)
            assert test_settings.api_port == 3000
            assert isinstance(test_settings.debug, bool)
            assert test_settings.debug is False

    def test_settings_boolean_conversion(self):
        """Test boolean conversion from environment variables."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
        ]

        for env_value, expected in test_cases:
            env_vars = {
                "DEBUG": env_value,
                "SECRET_KEY": "test-secret"
            }

            with patch.dict(os.environ, env_vars, clear=True):
                test_settings = Settings()
                assert test_settings.debug is expected

    def test_global_settings_instance(self):
        """Test that global settings instance is accessible."""
        assert settings is not None
        assert isinstance(settings, Settings)


