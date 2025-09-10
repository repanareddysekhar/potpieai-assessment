"""
Task service for managing analysis tasks and results.
"""
import json
import redis
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import (
    TaskStatus,
    TaskResponse,
    TaskStatusResponse,
    AnalysisResults
)
from app.services.cache_service import CacheService

logger = get_logger(__name__)


class TaskService:
    """Service for managing analysis tasks and storing results."""

    def __init__(self):
        """Initialize the task service with Redis connection."""
        self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        self.cache_service = CacheService()

    def _get_task_key(self, task_id: str) -> str:
        """Get Redis key for a task."""
        return f"task:{task_id}"

    def _get_results_key(self, task_id: str) -> str:
        """Get Redis key for task results."""
        return f"results:{task_id}"

    async def check_cached_result(self, repo_url: str, pr_number: int) -> Optional[Dict[str, Any]]:
        """
        Check if we have a cached result for this PR.

        Args:
            repo_url: GitHub repository URL
            pr_number: Pull request number

        Returns:
            Cached analysis result if available, None otherwise
        """
        try:
            cached_result = self.cache_service.get_cached_pr_analysis_result(repo_url, pr_number)

            if cached_result:
                logger.info("Found cached analysis result",
                           repo_url=repo_url,
                           pr_number=pr_number)
                return cached_result

            logger.info("No cached result found",
                       repo_url=repo_url,
                       pr_number=pr_number)
            return None

        except Exception as e:
            logger.error("Error checking cached result",
                        repo_url=repo_url,
                        pr_number=pr_number,
                        error=str(e))
            return None

    async def create_task(
        self,
        task_id: str,
        repo_url: str,
        pr_number: int,
        github_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new analysis task, checking cache first.

        Args:
            task_id: Unique task identifier
            repo_url: GitHub repository URL
            pr_number: Pull request number
            github_token: Optional GitHub token

        Returns:
            Cached result if available, None if new task created
        """
        # Check for cached result first
        cached_result = await self.check_cached_result(repo_url, pr_number)
        if cached_result:
            # Store the cached result as completed task
            task_data = {
                "task_id": task_id,
                "status": TaskStatus.COMPLETED.value,
                "repo_url": repo_url,
                "pr_number": pr_number,
                "github_token": github_token,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat()
            }

            # Store task data
            self.redis_client.setex(
                self._get_task_key(task_id),
                86400,  # 24 hours
                json.dumps(task_data)
            )

            # Store cached results
            await self.store_task_results(task_id, cached_result)

            logger.info("Task completed with cached result",
                       task_id=task_id,
                       repo_url=repo_url,
                       pr_number=pr_number)

            return cached_result

        # No cached result, create new task
        task_data = {
            "task_id": task_id,
            "status": TaskStatus.PENDING.value,
            "repo_url": repo_url,
            "pr_number": pr_number,
            "github_token": github_token,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        # Store task data in Redis with TTL (24 hours)
        self.redis_client.setex(
            self._get_task_key(task_id),
            86400,  # 24 hours
            json.dumps(task_data)
        )

        logger.info("New task created", task_id=task_id, repo_url=repo_url, pr_number=pr_number)
        return None

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update task status.

        Args:
            task_id: Task identifier
            status: New task status
            error_message: Optional error message for failed tasks
        """
        logger.info("Updating task status",
                   task_id=task_id,
                   new_status=status.value,
                   has_error_message=bool(error_message))

        task_key = self._get_task_key(task_id)
        task_data_str = self.redis_client.get(task_key)

        if not task_data_str:
            logger.error("Task not found for status update",
                        task_id=task_id,
                        redis_key=task_key)
            return

        try:
            task_data = json.loads(task_data_str)
            old_status = task_data.get("status", "unknown")

            task_data["status"] = status.value
            task_data["updated_at"] = datetime.now().isoformat()

            if status == TaskStatus.COMPLETED:
                task_data["completed_at"] = datetime.now().isoformat()
                logger.info("Task completion timestamp added", task_id=task_id)

            if error_message:
                task_data["error_message"] = error_message
                logger.info("Error message added to task",
                           task_id=task_id,
                           error_length=len(error_message))

            # Update task data in Redis
            self.redis_client.setex(task_key, 86400, json.dumps(task_data))

            logger.info("Task status updated successfully",
                       task_id=task_id,
                       old_status=old_status,
                       new_status=status.value,
                       redis_key=task_key)

        except json.JSONDecodeError as e:
            logger.error("Failed to parse task data for status update",
                        task_id=task_id,
                        error=str(e))
        except Exception as e:
            logger.error("Failed to update task status",
                        task_id=task_id,
                        error=str(e),
                        exc_info=True)

    async def get_task_status(self, task_id: str) -> Optional[TaskStatusResponse]:
        """
        Get task status.

        Args:
            task_id: Task identifier

        Returns:
            TaskStatusResponse or None if task not found
        """
        task_key = self._get_task_key(task_id)
        task_data_str = self.redis_client.get(task_key)

        if not task_data_str:
            return None

        task_data = json.loads(task_data_str)

        return TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus(task_data["status"]),
            progress=self._calculate_progress(task_data["status"]),
            message=self._get_status_message(task_data["status"]),
            created_at=task_data.get("created_at")
        )

    async def store_task_results(self, task_id: str, results: AnalysisResults) -> None:
        """
        Store analysis results and cache them for future use.

        Args:
            task_id: Task identifier
            results: Analysis results to store
        """
        logger.info("Storing task results",
                   task_id=task_id,
                   total_files=len(results.files),
                   total_issues=results.summary.total_issues if results.summary else 0)

        results_key = self._get_results_key(task_id)

        try:
            # Convert results to dict for JSON serialization
            results_dict = results.model_dump()
            results_json = json.dumps(results_dict)

            logger.info("Results serialized",
                       task_id=task_id,
                       json_size_bytes=len(results_json),
                       redis_key=results_key)

            # Store results in Redis with TTL (24 hours)
            self.redis_client.setex(
                results_key,
                86400,  # 24 hours
                results_json
            )

            # Also cache the results for future PR analysis requests
            task_data = await self.get_task_status(task_id)
            if task_data and hasattr(task_data, 'repo_url') and hasattr(task_data, 'pr_number'):
                # Get repo_url and pr_number from task data
                task_key = self._get_task_key(task_id)
                task_json = self.redis_client.get(task_key)
                if task_json:
                    task_info = json.loads(task_json)
                    repo_url = task_info.get('repo_url')
                    pr_number = task_info.get('pr_number')

                    if repo_url and pr_number:
                        # Cache the analysis result for future requests
                        self.cache_service.cache_pr_analysis_result(
                            repo_url=repo_url,
                            pr_number=pr_number,
                            result=results_dict,
                            ttl=3600  # 1 hour cache
                        )

                        logger.info("Results cached for future requests",
                                   task_id=task_id,
                                   repo_url=repo_url,
                                   pr_number=pr_number)

            logger.info("Task results stored successfully",
                       task_id=task_id,
                       redis_key=results_key,
                       ttl_hours=24)

        except Exception as e:
            logger.error("Failed to store task results",
                        task_id=task_id,
                        error=str(e),
                        exc_info=True)
            raise

    async def get_task_results(self, task_id: str) -> Optional[TaskResponse]:
        """
        Get task results.

        Args:
            task_id: Task identifier

        Returns:
            TaskResponse or None if task not found
        """
        task_key = self._get_task_key(task_id)
        results_key = self._get_results_key(task_id)

        task_data_str = self.redis_client.get(task_key)
        if not task_data_str:
            return None

        task_data = json.loads(task_data_str)

        # Get results if available
        results = None
        if task_data["status"] == TaskStatus.COMPLETED.value:
            results_str = self.redis_client.get(results_key)
            if results_str:
                results_dict = json.loads(results_str)
                results = AnalysisResults(**results_dict)

        return TaskResponse(
            task_id=task_id,
            status=TaskStatus(task_data["status"]),
            results=results,
            error_message=task_data.get("error_message"),
            created_at=task_data.get("created_at"),
            completed_at=task_data.get("completed_at")
        )

    def _calculate_progress(self, status: str) -> float:
        """Calculate progress percentage based on status."""
        progress_map = {
            TaskStatus.PENDING.value: 0.0,
            TaskStatus.PROCESSING.value: 50.0,
            TaskStatus.COMPLETED.value: 100.0,
            TaskStatus.FAILED.value: 0.0,
            TaskStatus.CANCELLED.value: 0.0
        }
        return progress_map.get(status, 0.0)

    def _get_status_message(self, status: str) -> str:
        """Get human-readable status message."""
        message_map = {
            TaskStatus.PENDING.value: "Task is queued for processing",
            TaskStatus.PROCESSING.value: "Analyzing pull request...",
            TaskStatus.COMPLETED.value: "Analysis completed successfully",
            TaskStatus.FAILED.value: "Analysis failed",
            TaskStatus.CANCELLED.value: "Task was cancelled"
        }
        return message_map.get(status, "Unknown status")

    async def get_task_data(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get raw task data from Redis.

        Args:
            task_id: Task identifier

        Returns:
            Task data dictionary or None if not found
        """
        logger.info("Retrieving task data", task_id=task_id)

        task_key = self._get_task_key(task_id)
        task_data_str = self.redis_client.get(task_key)

        if not task_data_str:
            logger.warning("Task data not found", task_id=task_id, redis_key=task_key)
            return None

        try:
            task_data = json.loads(task_data_str)
            logger.info("Task data retrieved successfully",
                       task_id=task_id,
                       status=task_data.get("status"),
                       repo_url=task_data.get("repo_url"))
            return task_data
        except json.JSONDecodeError as e:
            logger.error("Failed to parse task data",
                        task_id=task_id,
                        error=str(e))
            return None

    async def list_tasks(self, status_filter: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        List tasks with optional status filtering.

        Args:
            status_filter: Optional status to filter by
            limit: Maximum number of tasks to return

        Returns:
            List of task data dictionaries
        """
        logger.info("Listing tasks", status_filter=status_filter, limit=limit)

        try:
            # Get all task keys
            task_keys = self.redis_client.keys("task:*")
            logger.info("Found task keys", count=len(task_keys))

            tasks = []
            for task_key in task_keys:
                task_data_str = self.redis_client.get(task_key)
                if task_data_str:
                    try:
                        task_data = json.loads(task_data_str)

                        # Apply status filter if specified
                        if status_filter and task_data.get("status") != status_filter:
                            continue

                        # Add task ID to the data
                        task_data["task_id"] = task_key.replace("task:", "")
                        tasks.append(task_data)

                    except json.JSONDecodeError:
                        logger.warning("Skipping invalid task data", task_key=task_key)
                        continue

            # Sort by creation time (newest first)
            tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            # Apply limit
            tasks = tasks[:limit]

            logger.info("Tasks listed successfully",
                       total_found=len(tasks),
                       status_filter=status_filter)

            return tasks

        except Exception as e:
            logger.error("Failed to list tasks", error=str(e), exc_info=True)
            raise

    async def cleanup_stuck_tasks(self, max_age_hours: int = 2) -> Dict[str, Any]:
        """
        Clean up tasks that have been stuck in processing state for too long.

        Args:
            max_age_hours: Maximum age in hours for a task to be considered stuck

        Returns:
            Dictionary with cleanup results
        """
        logger.info("Starting stuck task cleanup", max_age_hours=max_age_hours)

        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            cutoff_iso = cutoff_time.isoformat()

            # Get all task keys
            task_keys = self.redis_client.keys("task:*")

            checked_count = 0
            cleaned_count = 0
            stuck_tasks = []

            for task_key in task_keys:
                task_data_str = self.redis_client.get(task_key)
                if task_data_str:
                    try:
                        task_data = json.loads(task_data_str)
                        checked_count += 1

                        # Check if task is stuck in processing
                        if (task_data.get("status") == "processing" and
                            task_data.get("created_at", "") < cutoff_iso):

                            task_id = task_key.replace("task:", "")

                            # Mark as failed
                            await self.update_task_status(
                                task_id,
                                TaskStatus.FAILED,
                                error_message=f"Task stuck in processing for more than {max_age_hours} hours"
                            )

                            stuck_tasks.append({
                                "task_id": task_id,
                                "created_at": task_data.get("created_at"),
                                "repo_url": task_data.get("repo_url"),
                                "pr_number": task_data.get("pr_number")
                            })

                            cleaned_count += 1

                            logger.info("Cleaned stuck task",
                                       task_id=task_id,
                                       created_at=task_data.get("created_at"))

                    except json.JSONDecodeError:
                        logger.warning("Skipping invalid task data during cleanup", task_key=task_key)
                        continue

            result = {
                "checked_count": checked_count,
                "cleaned_count": cleaned_count,
                "max_age_hours": max_age_hours,
                "cutoff_time": cutoff_iso,
                "stuck_tasks": stuck_tasks
            }

            logger.info("Stuck task cleanup completed",
                       checked=checked_count,
                       cleaned=cleaned_count)

            return result

        except Exception as e:
            logger.error("Failed to cleanup stuck tasks", error=str(e), exc_info=True)
            raise