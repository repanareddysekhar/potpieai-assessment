"""
Tests for Pydantic schemas and data models.
"""
import pytest
from pydantic import ValidationError

from app.models.schemas import (
    AnalyzePRRequest,
    TaskStatus,
    TaskResponse,
    IssueType,
    CodeIssue,
    FileAnalysis,
    AnalysisSummary,
    AnalysisResults,
    ErrorResponse
)


class TestAnalyzePRRequest:
    """Test cases for AnalyzePRRequest schema."""

    def test_analyze_pr_request_invalid_pr_number(self):
        """Test AnalyzePRRequest with invalid PR number."""
        with pytest.raises(ValidationError):
            AnalyzePRRequest(
                repo_url="https://github.com/owner/repo",
                pr_number=-1
            )

    def test_analyze_pr_request_missing_fields(self):
        """Test AnalyzePRRequest with missing required fields."""
        with pytest.raises(ValidationError):
            AnalyzePRRequest(repo_url="https://github.com/owner/repo")

    def test_analyze_pr_request_empty_repo_url(self):
        """Test AnalyzePRRequest with empty repo URL."""
        with pytest.raises(ValidationError):
            AnalyzePRRequest(repo_url="", pr_number=123)


class TestTaskStatus:
    """Test cases for TaskStatus enum."""

    def test_task_status_basic(self):
        """Test basic TaskStatus functionality."""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"


class TestTaskResponse:
    """Test cases for TaskResponse schema."""

    def test_basic_task_response(self):
        """Test basic TaskResponse creation."""
        response = TaskResponse(
            task_id="test-123",
            status=TaskStatus.PENDING
        )

        assert response.task_id == "test-123"
        assert response.status == TaskStatus.PENDING


class TestIssueType:
    """Test cases for IssueType enum."""

    def test_issue_type_values(self):
        """Test IssueType enum values."""
        assert IssueType.BUG == "bug"
        assert IssueType.STYLE == "style"
        assert IssueType.PERFORMANCE == "performance"
        assert IssueType.SECURITY == "security"

    def test_issue_type_membership(self):
        """Test IssueType membership."""
        assert "bug" in IssueType
        assert "style" in IssueType
        assert "performance" in IssueType
        assert "security" in IssueType
        assert "invalid" not in IssueType


class TestCodeIssue:
    """Test cases for CodeIssue schema."""

    def test_valid_code_issue(self):
        """Test valid CodeIssue creation."""
        issue = CodeIssue(
            type=IssueType.BUG,
            line=10,
            description="Potential null pointer",
            suggestion="Add null check"
        )
        
        assert issue.type == IssueType.BUG
        assert issue.line == 10
        assert issue.description == "Potential null pointer"
        assert issue.suggestion == "Add null check"

    def test_code_issue_with_optional_severity(self):
        """Test CodeIssue with optional severity."""
        issue = CodeIssue(
            type=IssueType.STYLE,
            line=5,
            description="Line too long",
            suggestion="Break into multiple lines",
            severity="medium"
        )
        
        assert issue.severity == "medium"

    def test_code_issue_invalid_line_number(self):
        """Test CodeIssue with invalid line number."""
        with pytest.raises(ValidationError):
            CodeIssue(
                type=IssueType.BUG,
                line=-1,
                description="Invalid line",
                suggestion="Fix it"
            )


class TestFileAnalysis:
    """Test cases for FileAnalysis schema."""

    def test_valid_file_analysis(self):
        """Test valid FileAnalysis creation."""
        issues = [
            CodeIssue(
                type=IssueType.STYLE,
                line=1,
                description="Missing docstring",
                suggestion="Add docstring"
            )
        ]
        
        analysis = FileAnalysis(
            name="test.py",
            path="src/test.py",
            language="python",
            issues=issues
        )
        
        assert analysis.name == "test.py"
        assert analysis.path == "src/test.py"
        assert analysis.language == "python"
        assert len(analysis.issues) == 1

    def test_file_analysis_no_issues(self):
        """Test FileAnalysis with no issues."""
        analysis = FileAnalysis(
            name="clean.py",
            path="src/clean.py",
            language="python",
            issues=[]
        )
        
        assert len(analysis.issues) == 0

    def test_file_analysis_optional_language(self):
        """Test FileAnalysis with optional language."""
        analysis = FileAnalysis(
            name="unknown",
            path="src/unknown",
            issues=[]
        )
        
        assert analysis.language is None


class TestAnalysisSummary:
    """Test cases for AnalysisSummary schema."""

    def test_valid_analysis_summary(self):
        """Test valid AnalysisSummary creation."""
        summary = AnalysisSummary(
            total_files=5,
            total_issues=10,
            critical_issues=2,
            files_with_issues=3,
            languages_detected=["python", "javascript"]
        )
        
        assert summary.total_files == 5
        assert summary.total_issues == 10
        assert summary.critical_issues == 2
        assert summary.files_with_issues == 3
        assert "python" in summary.languages_detected

    def test_analysis_summary_empty(self):
        """Test AnalysisSummary with empty values."""
        summary = AnalysisSummary(
            total_files=0,
            total_issues=0,
            critical_issues=0,
            files_with_issues=0,
            languages_detected=[]
        )
        
        assert summary.total_files == 0
        assert len(summary.languages_detected) == 0


class TestAnalysisResults:
    """Test cases for AnalysisResults schema."""

    def test_valid_analysis_results(self):
        """Test valid AnalysisResults creation."""
        files = [
            FileAnalysis(name="test.py", path="src/test.py", language="python", issues=[])
        ]
        summary = AnalysisSummary(
            total_files=1,
            total_issues=0,
            critical_issues=0,
            files_with_issues=0,
            languages_detected=["python"]
        )
        
        results = AnalysisResults(files=files, summary=summary)
        
        assert len(results.files) == 1
        assert results.summary.total_files == 1

    def test_analysis_results_empty(self):
        """Test AnalysisResults with empty data."""
        summary = AnalysisSummary(
            total_files=0,
            total_issues=0,
            critical_issues=0,
            files_with_issues=0,
            languages_detected=[]
        )
        
        results = AnalysisResults(files=[], summary=summary)
        
        assert len(results.files) == 0


class TestErrorResponse:
    """Test cases for ErrorResponse schema."""

    def test_valid_error_response(self):
        """Test valid ErrorResponse creation."""
        error = ErrorResponse(
            error="Validation failed",
            message="Invalid input data",
            details={"field": "repo_url", "issue": "Invalid URL format"}
        )
        
        assert error.error == "Validation failed"
        assert error.message == "Invalid input data"
        assert error.details["field"] == "repo_url"

    def test_error_response_without_details(self):
        """Test ErrorResponse without details."""
        error = ErrorResponse(
            error="Server error",
            message="Internal server error"
        )
        
        assert error.error == "Server error"
        assert error.details is None
