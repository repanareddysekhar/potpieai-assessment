"""
Celery application configuration and tasks.
"""
import asyncio
from typing import Optional

from celery import Celery
from celery.signals import worker_ready, worker_shutdown

from app.core.config import settings
from app.core.logging import get_logger
from app.services.github_service import GitHubService
from app.services.ai_agent import CodeReviewAgent
from app.services.task_service import TaskService
from app.models.schemas import TaskStatus

logger = get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "code_review_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.services.celery_app"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handle worker ready signal."""
    logger.info("Celery worker is ready")


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handle worker shutdown signal."""
    logger.info("Celery worker is shutting down")


@celery_app.task(bind=True, name="analyze_pr_task")
def analyze_pr_task(
    self,
    task_id: str,
    repo_url: str,
    pr_number: int,
    github_token: Optional[str] = None
):
    """
    Celery task to analyze a GitHub pull request.

    Args:
        task_id: Unique task identifier
        repo_url: GitHub repository URL
        pr_number: Pull request number
        github_token: Optional GitHub token for authentication
    """
    import time
    start_time = time.time()

    logger.info("🚀 Starting PR analysis task",
               task_id=task_id,
               repo_url=repo_url,
               pr_number=pr_number,
               has_github_token=bool(github_token),
               celery_task_id=self.request.id)

    try:
        # Update task status to processing
        logger.info("📝 Updating task status to processing", task_id=task_id)
        task_service = TaskService()

        # Create new event loop for async operations
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(task_service.update_task_status(task_id, TaskStatus.PROCESSING))

            # Initialize services
            logger.info("🔧 Initializing services", task_id=task_id)
            github_service = GitHubService(github_token)
            ai_agent = CodeReviewAgent()
            logger.info("✅ Services initialized successfully", task_id=task_id)

            # Fetch PR data
            logger.info("📥 Starting PR data fetch", task_id=task_id)
            pr_data = github_service.get_pull_request_data(repo_url, pr_number)
            logger.info("✅ PR data fetched successfully",
                       task_id=task_id,
                       pr_title=pr_data.get('title', 'N/A'),
                       changed_files=pr_data.get('changed_files', 0),
                       additions=pr_data.get('additions', 0),
                       deletions=pr_data.get('deletions', 0))

            # Get file diffs
            logger.info("📄 Starting file diffs fetch", task_id=task_id)
            file_diffs = github_service.get_pull_request_diffs(repo_url, pr_number)
            logger.info("✅ File diffs fetched successfully",
                       task_id=task_id,
                       total_files=len(file_diffs),
                       files_with_content=len([f for f in file_diffs if f.get('content')]))

            # Analyze code with AI agent
            logger.info("🤖 Starting AI analysis",
                       task_id=task_id,
                       files_to_analyze=len(file_diffs))
            analysis_results = ai_agent.analyze_code_changes(pr_data, file_diffs)
            logger.info("✅ AI analysis completed successfully",
                       task_id=task_id,
                       total_issues=analysis_results.summary.total_issues if analysis_results.summary else 0,
                       critical_issues=analysis_results.summary.critical_issues if analysis_results.summary else 0)

            # Store results
            logger.info("💾 Storing analysis results", task_id=task_id)
            loop.run_until_complete(task_service.store_task_results(task_id, analysis_results))
            logger.info("✅ Results stored successfully", task_id=task_id)

            # Update task status to completed
            logger.info("🏁 Updating task status to completed", task_id=task_id)
            loop.run_until_complete(task_service.update_task_status(task_id, TaskStatus.COMPLETED))

        finally:
            loop.close()

        # Calculate execution time
        end_time = time.time()
        execution_time = end_time - start_time

        logger.info("🎉 PR analysis completed successfully",
                   task_id=task_id,
                   execution_time_seconds=execution_time,
                   total_files_analyzed=len(file_diffs),
                   total_issues_found=analysis_results.summary.total_issues if analysis_results.summary else 0)

        return {
            "task_id": task_id,
            "status": "completed",
            "execution_time": execution_time,
            "files_analyzed": len(file_diffs),
            "issues_found": analysis_results.summary.total_issues if analysis_results.summary else 0
        }

    except Exception as e:
        logger.error("❌ PR analysis failed",
                    task_id=task_id,
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True)

        # Update task status to failed
        try:
            logger.info("📝 Updating task status to failed", task_id=task_id)
            task_service = TaskService()

            # Create new event loop for error handling
            error_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(error_loop)

            try:
                error_loop.run_until_complete(task_service.update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    error_message=str(e)
                ))
                logger.info("✅ Task status updated to failed", task_id=task_id)
            finally:
                error_loop.close()

        except Exception as update_error:
            logger.error("❌ Failed to update task status to failed",
                        task_id=task_id,
                        error=str(update_error),
                        exc_info=True)

        # Re-raise the exception for Celery to handle
        raise