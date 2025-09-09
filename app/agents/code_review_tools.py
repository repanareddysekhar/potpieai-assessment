"""
Helper tools and utilities for the code review agent.
"""
import json
import re
from typing import Dict, List, Any

from app.models.schemas import CodeIssue, IssueType, FileAnalysis
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_file_analysis_prompt(file_data: Dict[str, Any]) -> str:
    """Create a prompt for analyzing a specific file."""

    filename = file_data["filename"]
    language = file_data.get("language", "unknown")
    patch = file_data.get("patch", "")
    content = file_data.get("content", "")

    logger.info("Creating file analysis prompt",
               filename=filename,
               language=language,
               has_patch=bool(patch),
               has_content=bool(content),
               patch_length=len(patch) if patch else 0,
               content_length=len(content) if content else 0,
               file_status=file_data.get("status", "unknown"))

    # Truncate content if too long to avoid token limits
    truncated_content = content[:2000] if content else ""
    content_truncated = len(content) > 2000 if content else False

    if content_truncated:
        logger.info("Content truncated for analysis",
                   filename=filename,
                   original_length=len(content),
                   truncated_length=len(truncated_content))

    prompt = f"""
    Analyze the following {language} file for code quality issues:

    File: {filename}
    Language: {language}
    Status: {file_data.get("status", "unknown")}

    Diff/Patch:
    ```
    {patch}
    ```

    {"Full file content:" if content else ""}
    {f"```{language}" if content else ""}
    {truncated_content}
    {f"```" if content else ""}
    {f"[Content truncated - showing first 2000 characters of {len(content)} total]" if content_truncated else ""}

    Please analyze this file and identify issues in the following categories:
    1. **style** - Code style and formatting issues
    2. **bug** - Potential bugs or errors
    3. **performance** - Performance improvement opportunities
    4. **security** - Security vulnerabilities
    5. **best_practice** - Best practices violations

    For each issue found, provide:
    - Type (one of: style, bug, performance, security, best_practice)
    - Line number (if applicable)
    - Description of the issue
    - Suggested fix
    - Severity (low, medium, high, critical)

    Return your analysis in the following JSON format:
    {{
        "issues": [
            {{
                "type": "style",
                "line": 15,
                "description": "Line too long (exceeds 80 characters)",
                "suggestion": "Break the line into multiple lines",
                "severity": "low"
            }}
        ]
    }}

    If no issues are found, return: {{"issues": []}}
    """

    logger.info("File analysis prompt created",
               filename=filename,
               prompt_length=len(prompt),
               includes_patch=bool(patch),
               includes_content=bool(content),
               content_was_truncated=content_truncated)

    return prompt


def parse_file_analysis_response(response_content: str, file_data: Dict[str, Any]) -> FileAnalysis:
    """Parse the LLM response and create a FileAnalysis object."""

    filename = file_data["filename"]

    logger.info("Starting response parsing",
               filename=filename,
               response_length=len(response_content),
               response_preview=response_content[:200] + "..." if len(response_content) > 200 else response_content)

    try:
        # Try to extract JSON from the response
        logger.info("Attempting to extract JSON from response", filename=filename)
        json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            logger.info("JSON extracted from response",
                       filename=filename,
                       json_length=len(json_str),
                       json_preview=json_str[:100] + "..." if len(json_str) > 100 else json_str)
            analysis_data = json.loads(json_str)
        else:
            # Fallback: try to parse the entire response as JSON
            logger.info("No JSON pattern found, trying to parse entire response", filename=filename)
            analysis_data = json.loads(response_content)

        issues_data = analysis_data.get("issues", [])
        logger.info("Extracted issues from analysis",
                   filename=filename,
                   issues_count=len(issues_data))

        issues = []
        for i, issue_data in enumerate(issues_data):
            try:
                logger.info("Processing issue",
                           filename=filename,
                           issue_index=i+1,
                           issue_data=issue_data)

                # Map string type to enum
                issue_type_str = issue_data.get("type", "style").lower()
                issue_type_map = {
                    "style": IssueType.STYLE,
                    "bug": IssueType.BUG,
                    "performance": IssueType.PERFORMANCE,
                    "security": IssueType.SECURITY,
                    "best_practice": IssueType.BEST_PRACTICE
                }
                issue_type = issue_type_map.get(issue_type_str, IssueType.STYLE)

                if issue_type_str not in issue_type_map:
                    logger.warning("Unknown issue type, defaulting to style",
                                 filename=filename,
                                 unknown_type=issue_type_str,
                                 available_types=list(issue_type_map.keys()))

                issue = CodeIssue(
                    type=issue_type,
                    line=issue_data.get("line", 1),
                    description=issue_data.get("description", ""),
                    suggestion=issue_data.get("suggestion", ""),
                    severity=issue_data.get("severity", "low")
                )
                issues.append(issue)

                logger.info("Issue processed successfully",
                           filename=filename,
                           issue_index=i+1,
                           issue_type=issue_type.value,
                           line=issue.line,
                           severity=issue.severity)

            except Exception as e:
                logger.warning("Failed to parse individual issue",
                             filename=filename,
                             issue_index=i+1,
                             issue_data=issue_data,
                             error=str(e),
                             exc_info=True)
                continue

        file_analysis = FileAnalysis(
            name=filename.split("/")[-1],
            path=filename,
            issues=issues,
            language=file_data.get("language")
        )

        logger.info("File analysis parsing completed successfully",
                   filename=filename,
                   total_issues=len(issues),
                   issue_types=[issue.type.value for issue in issues],
                   severities=[issue.severity for issue in issues])

        return file_analysis

    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON from analysis response",
                    filename=filename,
                    response_preview=response_content[:500] + "..." if len(response_content) > 500 else response_content,
                    json_error=str(e),
                    exc_info=True)

        # Return empty analysis on parse failure
        return FileAnalysis(
            name=filename.split("/")[-1],
            path=filename,
            issues=[],
            language=file_data.get("language")
        )

    except Exception as e:
        logger.error("Unexpected error during analysis response parsing",
                    filename=filename,
                    response_preview=response_content[:500] + "..." if len(response_content) > 500 else response_content,
                    error=str(e),
                    exc_info=True)

        # Return empty analysis on parse failure
        return FileAnalysis(
            name=filename.split("/")[-1],
            path=filename,
            issues=[],
            language=file_data.get("language")
        )