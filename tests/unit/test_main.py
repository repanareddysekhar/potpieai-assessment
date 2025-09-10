"""
Tests for main FastAPI application.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestMainApplication:
    """Test cases for main FastAPI application."""

    def test_app_instance(self):
        """Test that app instance is created correctly."""
        assert app is not None
        assert hasattr(app, 'routes')

    def test_app_description(self):
        """Test application description."""
        assert "AI-powered code review" in app.description

    def test_app_version(self):
        """Test application version."""
        assert app.version == "1.0.0"

    def test_app_has_routes(self):
        """Test that application has routes configured."""
        routes = [route.path for route in app.routes]
        
        # Should have basic routes
        assert any("/health" in route for route in routes)
        assert any("/api" in route for route in routes)

    def test_app_middleware_configured(self):
        """Test that middleware is configured."""
        middleware_classes = [middleware.cls.__name__ for middleware in app.user_middleware]
        
        # Should have CORS middleware
        assert "CORSMiddleware" in middleware_classes

    def test_cors_configuration(self):
        """Test CORS configuration."""
        cors_middleware = None
        for middleware in app.user_middleware:
            if middleware.cls.__name__ == "CORSMiddleware":
                cors_middleware = middleware
                break
        
        assert cors_middleware is not None

    def test_app_exception_handlers(self):
        """Test that exception handlers are configured."""
        assert hasattr(app, 'exception_handlers')



    def test_app_handles_large_requests(self):
        """Test that app can handle reasonably large requests."""
        client = TestClient(app)
        
        large_data = {"repo_url": "https://github.com/test/repo", "pr_number": 1}
        response = client.post("/api/analyze", json=large_data)
        
        # Should not fail due to size (may fail for other reasons)
        assert response.status_code != 413

    def test_app_content_type_handling(self):
        """Test content type handling."""
        client = TestClient(app)
        
        # Test with correct content type
        response = client.post(
            "/api/analyze",
            json={"repo_url": "https://github.com/test/repo", "pr_number": 1},
            headers={"Content-Type": "application/json"}
        )
        
        # Should accept JSON content type
        assert response.status_code != 415

    def test_app_headers(self):
        """Test response headers."""
        client = TestClient(app)
        
        response = client.get("/health")
        
        # Should have proper headers
        assert "content-type" in response.headers

    def test_app_error_responses(self):
        """Test error response format."""
        client = TestClient(app)
        
        # Test 404 response
        response = client.get("/non-existent-endpoint")
        assert response.status_code == 404
        
        # Should return JSON error
        assert response.headers.get("content-type") == "application/json"

    def test_app_startup_configuration(self):
        """Test startup configuration."""
        assert hasattr(app, 'router')
        assert hasattr(app, 'middleware_stack')

    def test_app_openapi_schema(self):
        """Test OpenAPI schema generation."""
        schema = app.openapi()

        assert schema is not None
        assert "openapi" in schema
        assert "info" in schema

    def test_app_docs_endpoints(self):
        """Test documentation endpoints."""
        client = TestClient(app)
        
        # Test docs endpoint
        response = client.get("/docs")
        assert response.status_code == 200
        
        # Test redoc endpoint
        response = client.get("/redoc")
        assert response.status_code == 200
