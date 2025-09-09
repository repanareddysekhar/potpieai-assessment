"""
GitHub API service for fetching pull request data and diffs.
"""
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import requests
from github import Github, GithubException

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class GitHubService:
    """Service for interacting with GitHub API."""

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize GitHub service.

        Args:
            github_token: Optional GitHub token for authentication
        """
        self.token = github_token or settings.github_token
        self.github = Github(self.token) if self.token else Github()

    def _parse_repo_url(self, repo_url: str) -> tuple[str, str]:
        """
        Parse GitHub repository URL to extract owner and repo name.

        Args:
            repo_url: GitHub repository URL

        Returns:
            Tuple of (owner, repo_name)
        """
        # Handle different URL formats
        patterns = [
            r'github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$',
            r'github\.com/([^/]+)/([^/]+)/.*',
        ]

        for pattern in patterns:
            match = re.search(pattern, repo_url)
            if match:
                owner, repo_name = match.groups()
                # Remove .git suffix if present
                repo_name = repo_name.replace('.git', '')
                return owner, repo_name

        raise ValueError(f"Invalid GitHub repository URL: {repo_url}")

    def get_pull_request_data(self, repo_url: str, pr_number: int) -> Dict[str, Any]:
        """
        Fetch pull request data from GitHub.

        Args:
            repo_url: GitHub repository URL
            pr_number: Pull request number

        Returns:
            Dictionary containing PR data
        """
        try:
            logger.info("Starting PR data fetch",
                       repo_url=repo_url,
                       pr_number=pr_number,
                       has_token=bool(self.token))

            owner, repo_name = self._parse_repo_url(repo_url)
            logger.info("Parsed repository URL",
                       owner=owner,
                       repo=repo_name,
                       pr_number=pr_number)

            logger.info("Connecting to GitHub API")
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            logger.info("Repository accessed successfully",
                       repo_full_name=repo.full_name,
                       repo_language=repo.language,
                       repo_private=repo.private)

            logger.info("Fetching pull request data")
            pr = repo.get_pull(pr_number)

            logger.info("Pull request accessed successfully",
                       pr_title=pr.title,
                       pr_state=pr.state,
                       pr_author=pr.user.login,
                       pr_mergeable=pr.mergeable,
                       pr_merged=pr.merged)

            # Extract relevant PR information
            pr_data = {
                "number": pr.number,
                "title": pr.title,
                "body": pr.body or "",
                "state": pr.state,
                "author": pr.user.login,
                "created_at": pr.created_at.isoformat(),
                "updated_at": pr.updated_at.isoformat(),
                "base_branch": pr.base.ref,
                "head_branch": pr.head.ref,
                "base_sha": pr.base.sha,
                "head_sha": pr.head.sha,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files": pr.changed_files,
                "commits": pr.commits,
                "url": pr.html_url,
                "repository": {
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "owner": owner,
                    "language": repo.language,
                    "description": repo.description
                }
            }

            logger.info("PR data extraction completed",
                       pr_number=pr_number,
                       changed_files=pr.changed_files,
                       additions=pr.additions,
                       deletions=pr.deletions,
                       commits=pr.commits,
                       base_branch=pr.base.ref,
                       head_branch=pr.head.ref)

            return pr_data

        except GithubException as e:
            logger.error("GitHub API error",
                        repo_url=repo_url,
                        pr_number=pr_number,
                        error=str(e),
                        status_code=getattr(e, 'status', None),
                        exc_info=True)
            raise Exception(f"Failed to fetch PR data: {e}")
        except Exception as e:
            logger.error("Unexpected error fetching PR data",
                        repo_url=repo_url,
                        pr_number=pr_number,
                        error=str(e),
                        exc_info=True)
            raise

    def _detect_language(self, filename: str) -> Optional[str]:
        """
        Detect programming language from file extension or filename patterns.

        Args:
            filename: Name of the file

        Returns:
            Programming language or None if not detected
        """
        # Handle special filenames without extensions
        filename_lower = filename.lower()
        special_files = {
            'readme': 'markdown',
            'readme.txt': 'text',
            'license': 'text',
            'changelog': 'markdown',
            'makefile': 'makefile',
            'dockerfile': 'dockerfile',
            'jenkinsfile': 'groovy',
            'vagrantfile': 'ruby',
            'gemfile': 'ruby',
            'rakefile': 'ruby',
            'package.json': 'json',
            'composer.json': 'json',
            'requirements.txt': 'text',
            'setup.py': 'python',
            'setup.cfg': 'ini',
            'pyproject.toml': 'toml',
            'cargo.toml': 'toml',
            '.gitignore': 'text',
            '.env': 'text'
        }

        # Check for exact filename matches first
        if filename_lower in special_files:
            return special_files[filename_lower]

        # Check for partial matches (e.g., README.md, README.rst)
        for pattern, lang in special_files.items():
            if filename_lower.startswith(pattern.lower()):
                return lang

        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.sh': 'bash',
            '.sql': 'sql',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.less': 'less',
            '.xml': 'xml',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.rst': 'rst',
            '.txt': 'text',
            '.toml': 'toml',
            '.ini': 'ini',
            '.cfg': 'ini',
            '.conf': 'text',
            '.dockerfile': 'dockerfile',
            '.r': 'r',
            '.m': 'matlab',
            '.pl': 'perl',
            '.lua': 'lua',
            '.vim': 'vim'
        }

        # Get file extension
        if '.' in filename:
            ext = '.' + filename.split('.')[-1].lower()
            return extension_map.get(ext)

        # Check for special files without extensions
        special_files = {
            'dockerfile': 'dockerfile',
            'makefile': 'makefile',
            'rakefile': 'ruby',
            'gemfile': 'ruby'
        }

        return special_files.get(filename.lower())

    def _get_file_content(self, repo, filename: str, sha: str) -> str:
        """
        Get file content from repository.

        Args:
            repo: GitHub repository object
            filename: Name of the file
            sha: Commit SHA

        Returns:
            File content as string
        """
        try:
            file_content = repo.get_contents(filename, ref=sha)
            if file_content.encoding == 'base64':
                import base64
                return base64.b64decode(file_content.content).decode('utf-8')
            else:
                return file_content.decoded_content.decode('utf-8')
        except Exception as e:
            logger.warning("Failed to decode file content", filename=filename, error=str(e))
            return ""

    def get_pull_request_diffs(self, repo_url: str, pr_number: int) -> List[Dict[str, Any]]:
        """
        Fetch file diffs for a pull request.

        Args:
            repo_url: GitHub repository URL
            pr_number: Pull request number

        Returns:
            List of file diff data
        """
        try:
            owner, repo_name = self._parse_repo_url(repo_url)
            logger.info("Starting PR diffs fetch",
                       owner=owner,
                       repo=repo_name,
                       pr_number=pr_number)

            repo = self.github.get_repo(f"{owner}/{repo_name}")
            pr = repo.get_pull(pr_number)

            logger.info("Fetching changed files from PR")
            files = pr.get_files()
            files_list = list(files)  # Convert to list to get count

            logger.info("Found changed files",
                       total_files=len(files_list))

            file_diffs = []

            for i, file in enumerate(files_list):
                logger.info("Processing file",
                           file_index=f"{i+1}/{len(files_list)}",
                           filename=file.filename,
                           status=file.status,
                           additions=file.additions,
                           deletions=file.deletions,
                           changes=file.changes)

                # Detect programming language from file extension
                language = self._detect_language(file.filename)
                logger.info("Language detected",
                           filename=file.filename,
                           language=language)

                file_diff = {
                    "filename": file.filename,
                    "status": file.status,  # added, modified, removed, renamed
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "changes": file.changes,
                    "patch": file.patch or "",
                    "language": language,
                    "blob_url": file.blob_url,
                    "raw_url": file.raw_url,
                    "contents_url": file.contents_url
                }

                # Get file content if it's a new or modified file
                if file.status in ["added", "modified"] and language:
                    logger.info("Fetching file content",
                               filename=file.filename,
                               status=file.status)
                    try:
                        file_content = self._get_file_content(repo, file.filename, pr.head.sha)
                        file_diff["content"] = file_content
                        logger.info("File content fetched successfully",
                                   filename=file.filename,
                                   content_length=len(file_content) if file_content else 0)
                    except Exception as e:
                        logger.warning("Failed to fetch file content",
                                     filename=file.filename,
                                     error=str(e))
                        file_diff["content"] = None
                else:
                    logger.info("Skipping content fetch",
                               filename=file.filename,
                               reason=f"status={file.status}, language={language}")
                    file_diff["content"] = None

                file_diffs.append(file_diff)

            # Log summary by language and status
            language_counts = {}
            status_counts = {}
            for diff in file_diffs:
                lang = diff.get("language") or "unknown"
                status = diff.get("status", "unknown")
                language_counts[lang] = language_counts.get(lang, 0) + 1
                status_counts[status] = status_counts.get(status, 0) + 1

            logger.info("PR diffs fetch completed",
                       pr_number=pr_number,
                       total_files=len(file_diffs),
                       language_breakdown=language_counts,
                       status_breakdown=status_counts)

            return file_diffs

        except GithubException as e:
            logger.error("GitHub API error fetching diffs",
                        repo_url=repo_url,
                        pr_number=pr_number,
                        error=str(e),
                        status_code=getattr(e, 'status', None),
                        exc_info=True)
            raise Exception(f"Failed to fetch PR diffs: {e}")
        except Exception as e:
            logger.error("Unexpected error fetching PR diffs",
                        repo_url=repo_url,
                        pr_number=pr_number,
                        error=str(e),
                        exc_info=True)
            raise