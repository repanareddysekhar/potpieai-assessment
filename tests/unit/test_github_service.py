"""
Tests for GitHub service functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from github import Github, GithubException

from app.services.github_service import GitHubService


class TestGitHubService:
    """Test cases for GitHubService."""

    def test_github_service_init_with_token(self):
        """Test GitHubService initialization with token."""
        service = GitHubService(github_token="test-token")
        
        assert service.token == "test-token"
        assert service.github is not None

    def test_parse_repo_url_valid_https(self):
        """Test parsing valid HTTPS GitHub URLs."""
        service = GitHubService()
        
        test_cases = [
            "https://github.com/owner/repo",
            "https://github.com/owner/repo.git",
            "https://github.com/owner/repo/",
        ]
        
        for url in test_cases:
            owner, repo = service._parse_repo_url(url)
            assert owner == "owner"
            assert repo == "repo"

    def test_parse_repo_url_valid_https_with_git(self):
        """Test parsing HTTPS URLs with .git extension."""
        service = GitHubService()
        
        owner, repo = service._parse_repo_url("https://github.com/user/project.git")
        assert owner == "user"
        assert repo == "project"

    def test_parse_repo_url_invalid_format(self):
        """Test parsing invalid URL formats."""
        service = GitHubService()

        invalid_urls = [
            "not-a-url",
            "https://gitlab.com/owner/repo",
            "https://github.com/",
            "https://github.com/owner",
        ]

        for url in invalid_urls:
            with pytest.raises(ValueError):
                service._parse_repo_url(url)

    def test_parse_repo_url_missing_parts(self):
        """Test parsing URLs with missing owner or repo."""
        service = GitHubService()

        invalid_urls = [
            "https://github.com/owner",
            "https://github.com/",
        ]

        for url in invalid_urls:
            with pytest.raises(ValueError):
                service._parse_repo_url(url)

    @patch('app.services.github_service.Github')
    def test_get_pull_request_success(self, mock_github_class):
        """Test successful pull request retrieval."""
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo
        
        mock_pr = Mock()
        mock_pr.number = 123
        mock_pr.title = "Test PR"
        mock_pr.body = "Test description"
        mock_repo.get_pull.return_value = mock_pr
        
        service = GitHubService(github_token="test-token")
        result = service.get_pull_request_data("https://github.com/owner/repo", 123)
        
        assert result["number"] == 123
        assert result["title"] == "Test PR"
        assert result["body"] == "Test description"

    @patch('app.services.github_service.Github')
    def test_get_pull_request_files_no_files(self, mock_github_class):
        """Test pull request with no files."""
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo
        
        mock_pr = Mock()
        mock_pr.get_files.return_value = []
        mock_repo.get_pull.return_value = mock_pr
        
        service = GitHubService(github_token="test-token")
        result = service.get_pull_request_diffs("https://github.com/owner/repo", 123)
        
        assert result == []

    def test_github_service_error_handling(self):
        """Test error handling in GitHub service."""
        service = GitHubService()
        
        with patch.object(service.github, 'get_repo') as mock_get_repo:
            mock_get_repo.side_effect = GithubException(404, "Not Found")
            
            with pytest.raises(Exception, match="Failed to fetch PR data"):
                service.get_pull_request_data("https://github.com/owner/repo", 123)

    def test_github_service_rate_limit_handling(self):
        """Test rate limit handling."""
        service = GitHubService()
        
        with patch.object(service.github, 'get_repo') as mock_get_repo:
            mock_get_repo.side_effect = GithubException(403, "Rate limit exceeded")
            
            with pytest.raises(Exception, match="Failed to fetch PR data"):
                service.get_pull_request_data("https://github.com/owner/repo", 123)



    def test_github_service_authentication_error(self):
        """Test authentication error handling."""
        service = GitHubService()
        
        with patch.object(service.github, 'get_repo') as mock_get_repo:
            mock_get_repo.side_effect = GithubException(401, "Bad credentials")
            
            with pytest.raises(Exception, match="Failed to fetch PR data"):
                service.get_pull_request_data("https://github.com/owner/repo", 123)
