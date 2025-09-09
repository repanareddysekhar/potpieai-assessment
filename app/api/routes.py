"""
API routes for the Code Review Agent.
"""
import uuid
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

from app.models.schemas import (
    AnalyzePRRequest,
    TaskResponse,
    TaskStatusResponse,
    ErrorResponse,
    TaskStatus
)
from app.services.task_service import TaskService
from app.services.celery_app import analyze_pr_task
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Dependency to get task service
def get_task_service() -> TaskService:
    return TaskService()


@router.post("/analyze-pr", response_model=TaskResponse)
async def analyze_pr(
    request: AnalyzePRRequest,
    task_service: TaskService = Depends(get_task_service)
) -> TaskResponse:
    """
    Analyze a GitHub pull request.

    This endpoint accepts a GitHub repository URL and PR number,
    then starts an asynchronous analysis task.
    """
    try:
        logger.info("Received PR analysis request",
                   repo_url=str(request.repo_url),
                   pr_number=request.pr_number)

        # Generate unique task ID
        task_id = str(uuid.uuid4())

        # Create task record
        await task_service.create_task(
            task_id=task_id,
            repo_url=str(request.repo_url),
            pr_number=request.pr_number,
            github_token=request.github_token
        )

        # Start Celery task
        analyze_pr_task.delay(
            task_id=task_id,
            repo_url=str(request.repo_url),
            pr_number=request.pr_number,
            github_token=request.github_token
        )

        logger.info("Started PR analysis task", task_id=task_id)

        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING
        )

    except Exception as e:
        logger.error("Failed to start PR analysis", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "task_creation_failed",
                "message": "Failed to create analysis task"
            }
        )


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
) -> TaskStatusResponse:
    """
    Get the status of an analysis task.

    Returns the current status and progress of the specified task.
    """
    try:
        logger.info("Checking task status", task_id=task_id)

        task_status = await task_service.get_task_status(task_id)

        if not task_status:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "task_not_found",
                    "message": f"Task {task_id} not found"
                }
            )

        return task_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get task status", task_id=task_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "status_check_failed",
                "message": "Failed to check task status"
            }
        )


@router.get("/results/{task_id}", response_model=TaskResponse)
async def get_task_results(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
) -> TaskResponse:
    """
    Get the results of a completed analysis task.

    Returns the analysis results if the task is completed,
    or an error if the task is not found or not completed.
    """
    try:
        logger.info("Retrieving task results", task_id=task_id)

        task_result = await task_service.get_task_results(task_id)

        if not task_result:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "task_not_found",
                    "message": f"Task {task_id} not found"
                }
            )

        if task_result.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "task_not_completed",
                    "message": f"Task {task_id} is not completed yet. Current status: {task_result.status}"
                }
            )

        return task_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get task results", task_id=task_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "results_retrieval_failed",
                "message": "Failed to retrieve task results"
            }
        )


@router.post("/retrigger/{task_id}", response_model=TaskResponse)
async def retrigger_task(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
) -> TaskResponse:
    """
    Retrigger a stuck or failed analysis task.

    This endpoint allows you to restart a task that may be stuck in processing
    or has failed. It will create a new task with the same parameters.
    """
    try:
        logger.info("Retriggering task", task_id=task_id)

        # Get the original task data
        original_task = await task_service.get_task_data(task_id)

        if not original_task:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "task_not_found",
                    "message": f"Task {task_id} not found"
                }
            )

        # Check if task is in a retriggerable state
        current_status = original_task.get("status")
        if current_status == "completed":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "task_already_completed",
                    "message": f"Task {task_id} is already completed. Cannot retrigger."
                }
            )

        # Generate new task ID
        new_task_id = str(uuid.uuid4())

        # Create new task with same parameters
        await task_service.create_task(
            task_id=new_task_id,
            repo_url=original_task.get("repo_url"),
            pr_number=original_task.get("pr_number"),
            github_token=original_task.get("github_token")
        )

        # Mark original task as cancelled
        await task_service.update_task_status(
            task_id,
            TaskStatus.CANCELLED,
            error_message=f"Retriggered as task {new_task_id}"
        )

        # Start new Celery task
        analyze_pr_task.delay(
            task_id=new_task_id,
            repo_url=original_task.get("repo_url"),
            pr_number=original_task.get("pr_number"),
            github_token=original_task.get("github_token")
        )

        logger.info("Task retriggered successfully",
                   original_task_id=task_id,
                   new_task_id=new_task_id)

        return TaskResponse(
            task_id=new_task_id,
            status=TaskStatus.PENDING
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrigger task", task_id=task_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "retrigger_failed",
                "message": "Failed to retrigger task"
            }
        )


@router.delete("/cancel/{task_id}")
async def cancel_task(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
) -> dict:
    """
    Cancel a running or pending task.

    This endpoint allows you to cancel a task that is currently running
    or waiting in the queue.
    """
    try:
        logger.info("Cancelling task", task_id=task_id)

        # Check if task exists
        task_status = await task_service.get_task_status(task_id)
        if not task_status:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "task_not_found",
                    "message": f"Task {task_id} not found"
                }
            )

        # Check if task can be cancelled
        if task_status.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "task_not_cancellable",
                    "message": f"Task {task_id} is in {task_status.status} state and cannot be cancelled"
                }
            )

        # Cancel the task
        await task_service.update_task_status(
            task_id,
            TaskStatus.CANCELLED,
            error_message="Task cancelled by user request"
        )

        # Try to revoke the Celery task if it's still in queue
        try:
            from app.services.celery_app import celery_app
            celery_app.control.revoke(task_id, terminate=True)
            logger.info("Celery task revoked", task_id=task_id)
        except Exception as e:
            logger.warning("Failed to revoke Celery task", task_id=task_id, error=str(e))

        logger.info("Task cancelled successfully", task_id=task_id)

        return {
            "message": f"Task {task_id} has been cancelled",
            "task_id": task_id,
            "status": "cancelled"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel task", task_id=task_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "cancel_failed",
                "message": "Failed to cancel task"
            }
        )


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = None,
    limit: int = 20,
    task_service: TaskService = Depends(get_task_service)
) -> Dict[str, Any]:
    """
    List all tasks with optional filtering.

    Args:
        status: Optional status filter (pending, processing, completed, failed, cancelled)
        limit: Maximum number of tasks to return (default: 20)

    Returns:
        Dictionary containing list of tasks and summary statistics
    """
    try:
        logger.info("Listing tasks", status_filter=status, limit=limit)

        tasks = await task_service.list_tasks(status_filter=status, limit=limit)

        # Calculate summary statistics
        total_tasks = len(tasks)
        status_counts = {}
        for task in tasks:
            task_status = task.get("status", "unknown")
            status_counts[task_status] = status_counts.get(task_status, 0) + 1

        logger.info("Tasks listed successfully",
                   total_tasks=total_tasks,
                   status_filter=status,
                   status_breakdown=status_counts)

        return {
            "tasks": tasks,
            "total": total_tasks,
            "status_filter": status,
            "status_counts": status_counts,
            "limit": limit
        }

    except Exception as e:
        logger.error("Failed to list tasks", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "list_tasks_failed",
                "message": "Failed to retrieve task list"
            }
        )


@router.post("/cleanup-stuck-tasks")
async def cleanup_stuck_tasks(
    max_age_hours: int = 2,
    task_service: TaskService = Depends(get_task_service)
) -> Dict[str, Any]:
    """
    Clean up tasks that have been stuck in processing state for too long.

    Args:
        max_age_hours: Maximum age in hours for a task to be considered stuck (default: 2)

    Returns:
        Summary of cleanup operation
    """
    try:
        logger.info("Starting stuck task cleanup", max_age_hours=max_age_hours)

        cleanup_result = await task_service.cleanup_stuck_tasks(max_age_hours)

        logger.info("Stuck task cleanup completed",
                   tasks_cleaned=cleanup_result.get("cleaned_count", 0),
                   tasks_checked=cleanup_result.get("checked_count", 0))

        return cleanup_result

    except Exception as e:
        logger.error("Failed to cleanup stuck tasks", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "cleanup_failed",
                "message": "Failed to cleanup stuck tasks"
            }
        )