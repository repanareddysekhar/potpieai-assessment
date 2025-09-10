"""
End-to-end tests for complete application workflows.
Tests the entire system from API request to final response.
"""
import pytest
import time
import requests
from unittest.mock import patch, Mock


@pytest.mark.e2e
@pytest.mark.slow
class TestFullWorkflow:
    """End-to-end tests for complete application workflows."""
    
    @pytest.fixture(autouse=True)
    def setup_e2e_environment(self):
        """Setup environment for E2E tests."""
        # This would typically start the actual application
        # For now, we'll use the test client
        pass
    
    def test_complete_pr_analysis_workflow(self, client):
        """Test complete PR analysis workflow from start to finish."""
        # Step 1: Submit PR for analysis
        pr_request = {
            "repo_url": "https://github.com/octocat/Hello-World",
            "pr_number": 1
        }
        
        with patch('app.services.github_service.GitHubService') as mock_github:
            # Mock GitHub service responses
            mock_github_instance = Mock()
            mock_github_instance.get_pull_request.return_value = {
                "number": 1,
                "title": "Test PR",
                "body": "Test description",
                "state": "open"
            }
            mock_github_instance.get_pull_request_files.return_value = [
                {
                    "filename": "test.py",
                    "status": "modified",
                    "patch": "@@ -1,3 +1,4 @@\n def test():\n+    print('hello')\n     pass"
                }
            ]
            mock_github.return_value = mock_github_instance
            
            # Submit analysis request
            response = client.post("/api/v1/analyze-pr", json=pr_request)
            assert response.status_code == 200
            
            task_data = response.json()
            task_id = task_data["task_id"]
            assert task_id is not None
            
            # Step 2: Check task status
            status_response = client.get(f"/api/v1/status/{task_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            assert status_data["task_id"] == task_id
            assert status_data["status"] in ["pending", "processing", "completed"]
            
            # Step 3: Verify task appears in task list
            tasks_response = client.get("/api/v1/tasks")
            assert tasks_response.status_code == 200
            
            tasks_data = tasks_response.json()
            task_ids = [task["task_id"] for task in tasks_data["tasks"]]
            assert task_id in task_ids
    
    def test_cache_workflow_e2e(self, client):
        """Test end-to-end cache workflow."""
        pr_request = {
            "repo_url": "https://github.com/test/cache-repo",
            "pr_number": 42
        }
        
        with patch('app.services.github_service.GitHubService'):
            # Step 1: First request (cache miss)
            response1 = client.post("/api/v1/analyze-pr", json=pr_request)
            assert response1.status_code == 200
            task1_data = response1.json()
            
            # Step 2: Check cache stats
            cache_stats_response = client.get("/api/v1/cache/stats")
            assert cache_stats_response.status_code == 200
            
            # Step 3: Second request for same PR (potential cache hit)
            response2 = client.post("/api/v1/analyze-pr", json=pr_request)
            assert response2.status_code == 200
            task2_data = response2.json()
            
            # Both requests should succeed
            assert "task_id" in task1_data
            assert "task_id" in task2_data
            
            # Step 4: Invalidate cache
            invalidate_response = client.delete("/api/v1/cache/pr/test/cache-repo/42")
            assert invalidate_response.status_code == 200
            
            invalidate_data = invalidate_response.json()
            assert invalidate_data["status"] == "success"
            assert invalidate_data["pr_number"] == 42
    
    def test_error_handling_e2e(self, client):
        """Test end-to-end error handling."""
        # Test invalid repo URL
        invalid_request = {
            "repo_url": "not-a-valid-url",
            "pr_number": 1
        }
        
        response = client.post("/api/v1/analyze-pr", json=invalid_request)
        assert response.status_code == 422
        
        # Test non-existent task
        response = client.get("/api/v1/status/non-existent-task-id")
        assert response.status_code == 404
        
        # Test invalid PR number
        invalid_pr_request = {
            "repo_url": "https://github.com/test/repo",
            "pr_number": -1
        }
        
        response = client.post("/api/v1/analyze-pr", json=invalid_pr_request)
        assert response.status_code == 422
    
    def test_health_check_e2e(self, client):
        """Test health check endpoint end-to-end."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "code-review-agent"
    
    def test_api_documentation_e2e(self, client):
        """Test API documentation endpoints."""
        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
        assert "/api/v1/analyze-pr" in schema["paths"]
        
        # Test Swagger UI (should redirect or return HTML)
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_concurrent_requests_e2e(self, client):
        """Test handling of concurrent requests."""
        import concurrent.futures
        import threading
        
        def make_request(pr_number):
            """Make a single PR analysis request."""
            with patch('app.services.github_service.GitHubService'):
                response = client.post("/api/v1/analyze-pr", json={
                    "repo_url": f"https://github.com/test/concurrent-repo",
                    "pr_number": pr_number
                })
                return response.status_code, response.json()
        
        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(1, 6)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        for status_code, data in results:
            assert status_code == 200
            assert "task_id" in data
    
    def test_large_pr_handling_e2e(self, client, large_pr_data):
        """Test handling of large PR data."""
        with patch('app.services.github_service.GitHubService') as mock_github:
            mock_github_instance = Mock()
            mock_github_instance.get_pull_request.return_value = {
                "number": large_pr_data["pr_number"],
                "title": "Large PR",
                "body": "PR with many files",
                "state": "open"
            }
            mock_github_instance.get_pull_request_files.return_value = large_pr_data["files"]
            mock_github.return_value = mock_github_instance
            
            # Submit large PR for analysis
            response = client.post("/api/v1/analyze-pr", json={
                "repo_url": large_pr_data["repo_url"],
                "pr_number": large_pr_data["pr_number"]
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "task_id" in data
    
    def test_api_rate_limiting_e2e(self, client):
        """Test API rate limiting behavior."""
        # Make rapid requests to test rate limiting
        responses = []
        
        with patch('app.services.github_service.GitHubService'):
            for i in range(10):  # Make 10 rapid requests
                response = client.post("/api/v1/analyze-pr", json={
                    "repo_url": "https://github.com/test/rate-limit-repo",
                    "pr_number": i + 1
                })
                responses.append(response.status_code)
        
        # Most requests should succeed (we don't have rate limiting implemented yet)
        # But this test ensures the system can handle rapid requests
        success_count = sum(1 for status in responses if status == 200)
        assert success_count >= 8  # Allow for some potential failures


@pytest.mark.e2e
@pytest.mark.smoke
class TestSmokeTests:
    """Smoke tests for basic functionality."""
    
    def test_application_starts(self, client):
        """Test that the application starts and responds."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_basic_api_endpoints_respond(self, client):
        """Test that basic API endpoints respond."""
        endpoints = [
            "/health",
            "/api/v1/cache/stats",
            "/api/v1/tasks",
            "/openapi.json"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [200, 404]  # 404 is acceptable for some endpoints
    
    def test_api_accepts_valid_requests(self, client):
        """Test that API accepts valid requests."""
        with patch('app.services.github_service.GitHubService'):
            response = client.post("/api/v1/analyze-pr", json={
                "repo_url": "https://github.com/test/smoke-repo",
                "pr_number": 1
            })
            
            # Should not return server error
            assert response.status_code < 500
