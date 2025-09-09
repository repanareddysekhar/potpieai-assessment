"""
Pydantic schemas for API request/response models.
"""
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IssueType(str, Enum):
    """Code issue type enumeration."""
    STYLE = "style"
    BUG = "bug"
    PERFORMANCE = "performance"
    SECURITY = "security"
    BEST_PRACTICE = "best_practice"


class AnalyzePRRequest(BaseModel):
    """Request model for analyzing a pull request."""
    repo_url: HttpUrl = Field(..., description="GitHub repository URL")
    pr_number: int = Field(..., gt=0, description="Pull request number")
    github_token: Optional[str] = Field(None, description="Optional GitHub token for private repos")


class CodeIssue(BaseModel):
    """Model for a single code issue."""
    type: IssueType = Field(..., description="Type of the issue")
    line: int = Field(..., gt=0, description="Line number where the issue occurs")
    description: str = Field(..., description="Description of the issue")
    suggestion: str = Field(..., description="Suggested fix for the issue")
    severity: Optional[str] = Field(None, description="Severity level (low, medium, high, critical)")


class FileAnalysis(BaseModel):
    """Model for analysis results of a single file."""
    name: str = Field(..., description="File name")
    path: str = Field(..., description="File path")
    issues: List[CodeIssue] = Field(default_factory=list, description="List of issues found in the file")
    language: Optional[str] = Field(None, description="Programming language detected")


class AnalysisSummary(BaseModel):
    """Model for analysis summary."""
    total_files: int = Field(..., ge=0, description="Total number of files analyzed")
    total_issues: int = Field(..., ge=0, description="Total number of issues found")
    critical_issues: int = Field(..., ge=0, description="Number of critical issues")
    files_with_issues: int = Field(..., ge=0, description="Number of files with issues")
    languages_detected: List[str] = Field(default_factory=list, description="Programming languages detected")


class AnalysisResults(BaseModel):
    """Model for complete analysis results."""
    files: List[FileAnalysis] = Field(default_factory=list, description="Analysis results for each file")
    summary: AnalysisSummary = Field(..., description="Summary of the analysis")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class TaskResponse(BaseModel):
    """Response model for task operations."""
    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatus = Field(..., description="Current task status")
    results: Optional[AnalysisResults] = Field(None, description="Analysis results (only when completed)")
    error_message: Optional[str] = Field(None, description="Error message (only when failed)")
    created_at: Optional[str] = Field(None, description="Task creation timestamp")
    completed_at: Optional[str] = Field(None, description="Task completion timestamp")


class TaskStatusResponse(BaseModel):
    """Response model for task status check."""
    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatus = Field(..., description="Current task status")
    progress: Optional[float] = Field(None, ge=0, le=100, description="Progress percentage")
    message: Optional[str] = Field(None, description="Status message")
    created_at: Optional[str] = Field(None, description="Task creation timestamp")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")