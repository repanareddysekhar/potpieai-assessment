"""
Test data fixtures and utilities.
Centralized location for test data used across multiple test files.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any


class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_github_pr(
        number: int = 123,
        title: str = "Test PR",
        state: str = "open",
        user_login: str = "testuser"
    ) -> Dict[str, Any]:
        """Create GitHub PR test data."""
        return {
            "number": number,
            "title": title,
            "body": f"Test description for PR #{number}",
            "state": state,
            "user": {"login": user_login},
            "head": {
                "sha": f"abc{number}",
                "ref": "feature-branch"
            },
            "base": {
                "sha": f"def{number}",
                "ref": "main"
            },
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z",
            "html_url": f"https://github.com/test/repo/pull/{number}",
            "diff_url": f"https://github.com/test/repo/pull/{number}.diff",
            "patch_url": f"https://github.com/test/repo/pull/{number}.patch"
        }
    
    @staticmethod
    def create_github_file(
        filename: str = "test.py",
        status: str = "modified",
        additions: int = 10,
        deletions: int = 5,
        patch: str = None
    ) -> Dict[str, Any]:
        """Create GitHub file test data."""
        if patch is None:
            patch = f"@@ -1,3 +1,4 @@\n def test():\n+    print('hello')\n     pass"
        
        return {
            "filename": filename,
            "status": status,
            "additions": additions,
            "deletions": deletions,
            "changes": additions + deletions,
            "patch": patch,
            "blob_url": f"https://github.com/test/repo/blob/abc123/{filename}",
            "raw_url": f"https://github.com/test/repo/raw/abc123/{filename}"
        }
    
    @staticmethod
    def create_analysis_result(
        files_count: int = 1,
        issues_per_file: int = 2
    ) -> Dict[str, Any]:
        """Create analysis result test data."""
        files = []
        total_issues = 0
        
        for i in range(files_count):
            issues = []
            for j in range(issues_per_file):
                issues.append({
                    "type": "warning" if j % 2 == 0 else "error",
                    "line": (j + 1) * 10,
                    "description": f"Test issue {j + 1}",
                    "suggestion": f"Fix issue {j + 1}",
                    "severity": "medium"
                })
            
            files.append({
                "name": f"file_{i + 1}.py",
                "path": f"src/file_{i + 1}.py",
                "language": "python",
                "issues": issues,
                "lines_of_code": 100 + i * 50,
                "complexity_score": 5.0 + i
            })
            
            total_issues += len(issues)
        
        return {
            "files": files,
            "summary": {
                "total_files": files_count,
                "total_issues": total_issues,
                "critical_issues": total_issues // 4,
                "files_with_issues": files_count,
                "languages_detected": ["python"],
                "total_lines": sum(f["lines_of_code"] for f in files),
                "average_complexity": sum(f["complexity_score"] for f in files) / files_count
            },
            "metadata": {
                "analysis_time": 2.5,
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0"
            }
        }
    
    @staticmethod
    def create_task_data(
        task_id: str = "test-task-123",
        status: str = "pending",
        repo_url: str = "https://github.com/test/repo",
        pr_number: int = 123
    ) -> Dict[str, Any]:
        """Create task test data."""
        base_data = {
            "task_id": task_id,
            "status": status,
            "repo_url": repo_url,
            "pr_number": pr_number,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if status == "completed":
            base_data.update({
                "results": TestDataFactory.create_analysis_result(),
                "completed_at": datetime.utcnow().isoformat(),
                "progress": 100.0,
                "message": "Analysis completed successfully"
            })
        elif status == "processing":
            base_data.update({
                "progress": 50.0,
                "message": "Analyzing files..."
            })
        elif status == "failed":
            base_data.update({
                "error_message": "Analysis failed due to test error",
                "progress": 0.0,
                "message": "Analysis failed"
            })
        else:  # pending
            base_data.update({
                "progress": 0.0,
                "message": "Task is queued for processing"
            })
        
        return base_data
    
    @staticmethod
    def create_cache_stats() -> Dict[str, Any]:
        """Create cache statistics test data."""
        return {
            "connected_clients": 3,
            "used_memory": "2.5M",
            "total_commands_processed": 15000,
            "keyspace_hits": 8500,
            "keyspace_misses": 3200,
            "hit_rate": 72.65,
            "uptime_in_seconds": 86400,
            "redis_version": "7.0.0"
        }
    
    @staticmethod
    def create_large_pr_files(count: int = 100) -> List[Dict[str, Any]]:
        """Create large number of PR files for performance testing."""
        files = []
        
        for i in range(count):
            # Create different file types
            if i % 4 == 0:
                filename = f"src/module_{i}.py"
                language = "python"
            elif i % 4 == 1:
                filename = f"src/component_{i}.js"
                language = "javascript"
            elif i % 4 == 2:
                filename = f"tests/test_{i}.py"
                language = "python"
            else:
                filename = f"docs/readme_{i}.md"
                language = "markdown"
            
            # Create realistic patch
            lines_added = 20 + (i % 30)
            lines_removed = 5 + (i % 10)
            
            patch_lines = [f"@@ -{i+1},{lines_removed} +{i+1},{lines_added} @@"]
            for j in range(lines_added):
                patch_lines.append(f"+    new_line_{j}")
            for j in range(lines_removed):
                patch_lines.append(f"-    old_line_{j}")
            
            files.append({
                "filename": filename,
                "status": "modified" if i % 3 != 0 else "added",
                "additions": lines_added,
                "deletions": lines_removed,
                "changes": lines_added + lines_removed,
                "patch": "\n".join(patch_lines),
                "language": language
            })
        
        return files
    
    @staticmethod
    def create_error_scenarios() -> Dict[str, Dict[str, Any]]:
        """Create various error scenarios for testing."""
        return {
            "github_api_error": {
                "error_type": "GitHubAPIError",
                "status_code": 404,
                "message": "Repository not found",
                "details": {"resource": "repository", "field": "name"}
            },
            "rate_limit_error": {
                "error_type": "RateLimitError", 
                "status_code": 403,
                "message": "API rate limit exceeded",
                "details": {"limit": 5000, "remaining": 0, "reset": 1640995200}
            },
            "validation_error": {
                "error_type": "ValidationError",
                "status_code": 422,
                "message": "Invalid input data",
                "details": {"field": "pr_number", "issue": "must be positive integer"}
            },
            "redis_connection_error": {
                "error_type": "RedisConnectionError",
                "message": "Failed to connect to Redis server",
                "details": {"host": "localhost", "port": 6379}
            },
            "timeout_error": {
                "error_type": "TimeoutError",
                "message": "Operation timed out",
                "details": {"timeout": 30, "operation": "github_api_call"}
            }
        }


# Predefined test data sets
SAMPLE_REPOS = [
    "https://github.com/octocat/Hello-World",
    "https://github.com/microsoft/vscode",
    "https://github.com/facebook/react",
    "https://github.com/google/tensorflow",
    "https://github.com/torvalds/linux"
]

SAMPLE_PR_NUMBERS = [1, 42, 123, 999, 1337]

SAMPLE_FILE_EXTENSIONS = [
    ".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", 
    ".rs", ".rb", ".php", ".swift", ".kt", ".scala"
]

SAMPLE_ISSUE_TYPES = [
    "error", "warning", "info", "style", "security", 
    "performance", "maintainability", "complexity"
]

# Test environment configurations
TEST_ENVIRONMENTS = {
    "unit": {
        "redis_mock": True,
        "github_mock": True,
        "database": "sqlite:///:memory:",
        "debug": True
    },
    "integration": {
        "redis_mock": False,
        "github_mock": True,
        "database": "sqlite:///test_integration.db",
        "debug": True
    },
    "e2e": {
        "redis_mock": False,
        "github_mock": False,
        "database": "sqlite:///test_e2e.db",
        "debug": False
    },
    "performance": {
        "redis_mock": False,
        "github_mock": True,
        "database": "sqlite:///test_performance.db",
        "debug": False
    }
}
