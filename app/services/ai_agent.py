"""
AI Agent for code review using LangGraph and OpenAI.
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict, Annotated

from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import (
    AnalysisResults,
    FileAnalysis,
    CodeIssue,
    AnalysisSummary,
    IssueType
)

logger = get_logger(__name__)


class AgentState(TypedDict):
    """State for the code review agent."""
    messages: Annotated[list, add_messages]
    pr_data: Dict[str, Any]
    file_diffs: List[Dict[str, Any]]
    current_file: Optional[Dict[str, Any]]
    file_analyses: List[FileAnalysis]
    summary: Optional[AnalysisSummary]
    step: str


class CodeReviewAgent:
    """AI agent for autonomous code review using LangGraph."""

    def __init__(self):
        """Initialize the code review agent."""
        self.llm = self._initialize_llm()
        self.graph = self._build_graph()

    def _initialize_llm(self) -> ChatOpenAI:
        """Initialize the language model."""
        if settings.openai_api_key:
            return ChatOpenAI(
                model="gpt-4-turbo-preview",
                temperature=0.1,
                api_key=settings.openai_api_key
            )
        else:
            # Fallback to Ollama if no OpenAI key
            from langchain_community.llms import Ollama
            return Ollama(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model
            )

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for code review."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("analyze_pr_context", self._analyze_pr_context)
        workflow.add_node("analyze_file", self._analyze_file)
        workflow.add_node("generate_summary", self._generate_summary)

        # Add edges
        workflow.set_entry_point("analyze_pr_context")
        workflow.add_edge("analyze_pr_context", "analyze_file")
        workflow.add_conditional_edges(
            "analyze_file",
            self._should_continue_analysis,
            {
                "continue": "analyze_file",
                "summarize": "generate_summary"
            }
        )
        workflow.add_edge("generate_summary", END)

        return workflow.compile()

    def _analyze_pr_context(self, state: AgentState) -> AgentState:
        """Analyze the overall PR context (optimized - skip LLM call for speed)."""
        pr_data = state["pr_data"]

        logger.info("Starting PR context analysis",
                   pr_number=pr_data.get('number'),
                   repository=pr_data.get('repository', {}).get('full_name'),
                   changed_files=pr_data.get('changed_files', 0),
                   additions=pr_data.get('additions', 0),
                   deletions=pr_data.get('deletions', 0))

        # Skip expensive LLM call for context - just prepare the context for file analysis
        system_prompt = """You are an expert code reviewer. You will analyze a GitHub pull request and provide detailed feedback.

        Your analysis should focus on:
        1. Code style and formatting issues
        2. Potential bugs or errors
        3. Performance improvements
        4. Security vulnerabilities
        5. Best practices adherence

        Be thorough but constructive in your feedback."""

        context_message = f"""
        Pull Request Analysis Context:

        Title: {pr_data.get('title', 'N/A')}
        Description: {pr_data.get('body', 'N/A')}
        Author: {pr_data.get('author', 'N/A')}
        Repository: {pr_data.get('repository', {}).get('full_name', 'N/A')}
        Language: {pr_data.get('repository', {}).get('language', 'N/A')}

        Changes Summary:
        - Files changed: {pr_data.get('changed_files', 0)}
        - Lines added: {pr_data.get('additions', 0)}
        - Lines deleted: {pr_data.get('deletions', 0)}
        """

        logger.info("Context prepared (skipping LLM call for performance)",
                   system_prompt_length=len(system_prompt),
                   context_message_length=len(context_message))

        # Store context without expensive LLM call
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_message)
        ]

        state["messages"] = messages
        state["step"] = "context_analyzed"
        state["file_analyses"] = []

        logger.info("PR context analysis completed successfully (optimized)")
        return state

    def _analyze_file(self, state: AgentState) -> AgentState:
        """Analyze a single file in the PR."""
        file_diffs = state["file_diffs"]
        current_analyses = state["file_analyses"]

        # Get next file to analyze
        current_index = len(current_analyses)
        if current_index >= len(file_diffs):
            logger.info("🏁 All files analyzed",
                       total_files=len(file_diffs),
                       files_processed=len(current_analyses))
            state["step"] = "files_analyzed"
            return state

        current_file = file_diffs[current_index]
        state["current_file"] = current_file

        # Log overall progress
        progress_percent = round((current_index / len(file_diffs)) * 100, 1)
        logger.info("📊 Analysis Progress",
                   current_file=current_file["filename"],
                   progress=f"{current_index}/{len(file_diffs)} files ({progress_percent}%)",
                   files_completed=current_index,
                   files_remaining=len(file_diffs) - current_index,
                   total_files=len(file_diffs))

        logger.info("📄 Starting file analysis",
                   filename=current_file["filename"],
                   file_index=f"{current_index + 1}/{len(file_diffs)}",
                   status=current_file.get("status"),
                   language=current_file.get("language"),
                   additions=current_file.get("additions", 0),
                   deletions=current_file.get("deletions", 0),
                   progress_percent=round((current_index / len(file_diffs)) * 100, 1))

        # Skip files that are deleted or binary
        if current_file["status"] == "removed":
            logger.info("Skipping removed file", filename=current_file["filename"])
            file_analysis = FileAnalysis(
                name=current_file["filename"].split("/")[-1],
                path=current_file["filename"],
                issues=[],
                language=current_file.get("language")
            )
            state["file_analyses"].append(file_analysis)
            return state

        if not current_file.get("language"):
            logger.info("Skipping file with unknown language",
                       filename=current_file["filename"])
            file_analysis = FileAnalysis(
                name=current_file["filename"].split("/")[-1],
                path=current_file["filename"],
                issues=[],
                language=current_file.get("language")
            )
            state["file_analyses"].append(file_analysis)
            return state

        # Prepare file analysis prompt
        logger.info("Preparing analysis prompt",
                   filename=current_file["filename"],
                   has_patch=bool(current_file.get("patch")),
                   has_content=bool(current_file.get("content")))

        file_prompt = self._create_file_analysis_prompt(current_file)

        logger.info("Analysis prompt created",
                   filename=current_file["filename"],
                   prompt_length=len(file_prompt))

        logger.info("🤖 Sending file to LLM for analysis",
                   filename=current_file["filename"],
                   prompt_length=len(file_prompt),
                   file_index=f"{current_index + 1}/{len(file_diffs)}",
                   estimated_time="10-30 seconds")

        try:
            # Use different invocation based on LLM type
            if hasattr(self.llm, 'invoke'):
                # For Ollama LLM, use string directly
                if 'ollama' in str(type(self.llm)).lower():
                    response = self.llm.invoke(file_prompt)
                else:
                    # For ChatOpenAI, use HumanMessage
                    response = self.llm.invoke([HumanMessage(content=file_prompt)])
            else:
                response = self.llm(file_prompt)

            logger.info("✅ LLM analysis completed",
                       filename=current_file["filename"],
                       response_length=len(response.content) if hasattr(response, 'content') else len(str(response)),
                       file_index=f"{current_index + 1}/{len(file_diffs)}")

            # Parse the response to extract issues
            logger.info("Parsing LLM response", filename=current_file["filename"])

            # Handle different response types
            if hasattr(response, 'content'):
                response_content = response.content
            else:
                response_content = str(response)

            logger.info("Response content extracted",
                       filename=current_file["filename"],
                       response_type=type(response).__name__,
                       content_length=len(response_content))

            file_analysis = self._parse_file_analysis_response(
                response_content,
                current_file
            )

            state["file_analyses"].append(file_analysis)
            logger.info("🎉 File analysis completed successfully",
                       filename=current_file["filename"],
                       issues_found=len(file_analysis.issues),
                       issue_types=[issue.type.value for issue in file_analysis.issues],
                       file_index=f"{current_index + 1}/{len(file_diffs)}",
                       files_remaining=len(file_diffs) - current_index - 1)

        except Exception as e:
            logger.error("Failed to analyze file",
                        filename=current_file["filename"],
                        error=str(e),
                        exc_info=True)
            # Create empty analysis for failed files
            file_analysis = FileAnalysis(
                name=current_file["filename"].split("/")[-1],
                path=current_file["filename"],
                issues=[],
                language=current_file.get("language")
            )
            state["file_analyses"].append(file_analysis)

        return state

    def _create_file_analysis_prompt(self, file_data: Dict[str, Any]) -> str:
        """Create a prompt for analyzing a specific file."""
        from app.agents.code_review_tools import create_file_analysis_prompt
        return create_file_analysis_prompt(file_data)

    def _parse_file_analysis_response(self, response_content: str, file_data: Dict[str, Any]) -> FileAnalysis:
        """Parse the LLM response and create a FileAnalysis object."""
        from app.agents.code_review_tools import parse_file_analysis_response
        return parse_file_analysis_response(response_content, file_data)

    def _should_continue_analysis(self, state: AgentState) -> str:
        """Determine if we should continue analyzing files or move to summary."""
        file_diffs = state["file_diffs"]
        current_analyses = state["file_analyses"]

        if len(current_analyses) >= len(file_diffs):
            return "summarize"
        else:
            return "continue"

    def _generate_summary(self, state: AgentState) -> AgentState:
        """Generate analysis summary."""
        logger.info("Starting summary generation")

        file_analyses = state["file_analyses"]

        logger.info("Calculating summary statistics",
                   total_file_analyses=len(file_analyses))

        # Calculate summary statistics
        total_files = len(file_analyses)
        total_issues = sum(len(analysis.issues) for analysis in file_analyses)

        # Count issues by severity
        severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        issue_type_counts = {}

        for analysis in file_analyses:
            for issue in analysis.issues:
                # Count by severity
                severity = issue.severity or "low"
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

                # Count by type
                issue_type = issue.type.value
                issue_type_counts[issue_type] = issue_type_counts.get(issue_type, 0) + 1

        critical_issues = severity_counts.get("critical", 0)
        files_with_issues = len([analysis for analysis in file_analyses if analysis.issues])

        # Get unique languages
        languages_detected = list(set(
            analysis.language for analysis in file_analyses
            if analysis.language
        ))

        logger.info("Summary statistics calculated",
                   total_files=total_files,
                   total_issues=total_issues,
                   critical_issues=critical_issues,
                   files_with_issues=files_with_issues,
                   severity_breakdown=severity_counts,
                   issue_type_breakdown=issue_type_counts,
                   languages_detected=languages_detected)

        # Log detailed file breakdown
        for i, analysis in enumerate(file_analyses):
            logger.info("File analysis summary",
                       file_index=i+1,
                       filename=analysis.path,
                       language=analysis.language,
                       issues_count=len(analysis.issues),
                       issue_types=[issue.type.value for issue in analysis.issues])

        summary = AnalysisSummary(
            total_files=total_files,
            total_issues=total_issues,
            critical_issues=critical_issues,
            files_with_issues=files_with_issues,
            languages_detected=languages_detected
        )

        state["summary"] = summary
        state["step"] = "completed"

        logger.info("Analysis summary generation completed successfully",
                   summary=summary.model_dump())

        return state

    def analyze_code_changes(self, pr_data: Dict[str, Any], file_diffs: List[Dict[str, Any]]) -> AnalysisResults:
        """
        Main method to analyze code changes in a PR.

        Args:
            pr_data: Pull request data from GitHub
            file_diffs: List of file diffs from the PR

        Returns:
            AnalysisResults containing the complete analysis
        """
        logger.info("Starting code analysis",
                   pr_number=pr_data.get("number"),
                   files_count=len(file_diffs))

        # Initialize state
        initial_state = AgentState(
            messages=[],
            pr_data=pr_data,
            file_diffs=file_diffs,
            current_file=None,
            file_analyses=[],
            summary=None,
            step="initialized"
        )

        # Run the analysis workflow
        final_state = self.graph.invoke(initial_state)

        # Create metadata
        metadata = {
            "analysis_timestamp": datetime.now().isoformat(),
            "pr_number": pr_data.get("number"),
            "repository": pr_data.get("repository", {}).get("full_name"),
            "total_commits": pr_data.get("commits", 0),
            "base_branch": pr_data.get("base_branch"),
            "head_branch": pr_data.get("head_branch")
        }

        # Return results
        return AnalysisResults(
            files=final_state["file_analyses"],
            summary=final_state["summary"],
            metadata=metadata
        )