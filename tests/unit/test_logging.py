"""
Tests for the logging module.
"""
import pytest
import logging
from unittest.mock import patch, Mock
import structlog

from app.core.logging import get_logger, setup_logging


class TestLogging:
    """Test cases for logging functionality."""

    def test_get_logger_returns_structlog_logger(self):
        """Test that get_logger returns a structlog logger."""
        logger = get_logger("test_module")
        
        # Should return a structlog logger
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'critical')

    def test_get_logger_with_different_names(self):
        """Test that get_logger works with different module names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        logger3 = get_logger("app.services.test")
        
        # All should be valid loggers
        assert logger1 is not None
        assert logger2 is not None
        assert logger3 is not None
        
        # They should be different instances or at least handle different names
        assert hasattr(logger1, 'info')
        assert hasattr(logger2, 'info')
        assert hasattr(logger3, 'info')

    def test_get_logger_with_empty_name(self):
        """Test get_logger with empty name."""
        logger = get_logger("")
        assert logger is not None
        assert hasattr(logger, 'info')

    def test_get_logger_with_none_name(self):
        """Test get_logger with None name."""
        logger = get_logger(None)
        assert logger is not None
        assert hasattr(logger, 'info')

    @patch('app.core.logging.structlog')
    def test_setup_logging_configuration(self, mock_structlog):
        """Test that setup_logging configures structlog properly."""
        mock_configure = Mock()
        mock_structlog.configure = mock_configure
        
        setup_logging()
        
        # Verify that structlog.configure was called
        mock_configure.assert_called_once()
        
        # Get the call arguments
        call_args = mock_configure.call_args
        assert call_args is not None

    def test_setup_logging_can_be_called_multiple_times(self):
        """Test that setup_logging can be called multiple times without error."""
        # Should not raise any exceptions
        setup_logging()
        setup_logging()
        setup_logging()

    def test_logger_methods_exist(self):
        """Test that logger has all expected methods."""
        logger = get_logger("test")
        
        # Test that all standard logging methods exist
        assert callable(getattr(logger, 'debug', None))
        assert callable(getattr(logger, 'info', None))
        assert callable(getattr(logger, 'warning', None))
        assert callable(getattr(logger, 'error', None))
        assert callable(getattr(logger, 'critical', None))

    def test_logger_can_log_messages(self):
        """Test that logger can actually log messages without error."""
        logger = get_logger("test_logging")
        
        # These should not raise exceptions
        try:
            logger.info("Test info message")
            logger.debug("Test debug message")
            logger.warning("Test warning message")
            logger.error("Test error message")
        except Exception as e:
            pytest.fail(f"Logger raised unexpected exception: {e}")

    def test_logger_with_structured_data(self):
        """Test that logger can handle structured data."""
        logger = get_logger("test_structured")
        
        # Test logging with additional structured data
        try:
            logger.info("Test message with data", 
                       user_id=123, 
                       action="test_action",
                       metadata={"key": "value"})
            
            logger.error("Test error with context",
                        error_code="TEST_001",
                        component="test_module",
                        details={"error": "test error"})
        except Exception as e:
            pytest.fail(f"Structured logging raised unexpected exception: {e}")

    def test_logger_with_different_data_types(self):
        """Test that logger can handle different data types."""
        logger = get_logger("test_types")
        
        try:
            # Test with various data types
            logger.info("Test with string", value="string_value")
            logger.info("Test with int", value=42)
            logger.info("Test with float", value=3.14)
            logger.info("Test with bool", value=True)
            logger.info("Test with list", value=[1, 2, 3])
            logger.info("Test with dict", value={"nested": "dict"})
            logger.info("Test with None", value=None)
        except Exception as e:
            pytest.fail(f"Logger with different data types raised exception: {e}")

    @patch('app.core.logging.structlog.get_logger')
    def test_get_logger_calls_structlog_get_logger(self, mock_get_logger):
        """Test that get_logger calls structlog.get_logger with correct name."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        result = get_logger("test_module")
        
        mock_get_logger.assert_called_once_with("test_module")
        assert result == mock_logger

    def test_logger_name_handling(self):
        """Test that logger handles various name formats correctly."""
        test_names = [
            "simple_name",
            "app.module.submodule",
            "CamelCaseName",
            "name_with_123_numbers",
            "name-with-dashes",
            "name.with.dots.and_underscores",
        ]
        
        for name in test_names:
            logger = get_logger(name)
            assert logger is not None
            assert hasattr(logger, 'info')
            
            # Test that it can log without error
            try:
                logger.info(f"Test message from {name}")
            except Exception as e:
                pytest.fail(f"Logger with name '{name}' failed: {e}")

    def test_logging_integration(self):
        """Test basic logging integration."""
        # Setup logging
        setup_logging()
        
        # Get a logger
        logger = get_logger("integration_test")
        
        # Test that we can log various levels
        try:
            logger.debug("Debug message for integration test")
            logger.info("Info message for integration test", test_id="integration_001")
            logger.warning("Warning message for integration test", component="test")
            logger.error("Error message for integration test", error_type="test_error")
        except Exception as e:
            pytest.fail(f"Logging integration test failed: {e}")

    def test_logger_performance(self):
        """Test that logger creation is reasonably fast."""
        import time
        
        start_time = time.time()
        
        # Create multiple loggers
        for i in range(100):
            logger = get_logger(f"performance_test_{i}")
            logger.info("Performance test message", iteration=i)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (less than 1 second for 100 loggers)
        assert duration < 1.0, f"Logger creation took too long: {duration} seconds"

    def test_logger_memory_usage(self):
        """Test that repeated logger creation doesn't cause memory issues."""
        # Create many loggers with same name - should reuse or not cause issues
        loggers = []
        for i in range(50):
            logger = get_logger("memory_test")
            loggers.append(logger)
            logger.info("Memory test message", iteration=i)
        
        # All loggers should be valid
        for logger in loggers:
            assert logger is not None
            assert hasattr(logger, 'info')

    def test_setup_logging_idempotent(self):
        """Test that setup_logging is idempotent."""
        # Call setup_logging multiple times
        setup_logging()
        logger1 = get_logger("idempotent_test")
        
        setup_logging()
        logger2 = get_logger("idempotent_test")
        
        setup_logging()
        logger3 = get_logger("idempotent_test")
        
        # All loggers should work
        logger1.info("Test message 1")
        logger2.info("Test message 2")
        logger3.info("Test message 3")
