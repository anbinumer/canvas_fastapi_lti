"""
QA Tasks API Routes

Provides REST API endpoints for QA automation task management including:
- Starting and managing Find & Replace tasks
- Task status monitoring and control
- Course content analysis and validation
- Task history and results
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

# from core.dependencies import require_lti_session, get_canvas_context  # TODO: Implement dependencies
from app.core.exceptions import QAAutomationException
from qa_framework.base import (
    QATaskType,
    CanvasContentType,
    TaskStatus,
    QAExecution,
    FindReplaceConfig
)
from services.qa_orchestrator import get_qa_orchestrator
from services.session_service import SessionService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/qa", tags=["QA Automation"])

# Pydantic models for API requests/responses

class URLMapping(BaseModel):
    """URL mapping for find and replace operations"""
    find: str = Field(..., description="URL to search for")
    replace: str = Field(..., description="URL to replace with")
    
    @validator('find', 'replace')
    def validate_urls(cls, v):
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")
        return v.strip()


class StartFindReplaceRequest(BaseModel):
    """Request to start a Find & Replace QA task"""
    url_mappings: List[URLMapping] = Field(..., min_items=1, description="List of URL mappings")
    content_types: Optional[List[str]] = Field(
        default=None, 
        description="Content types to scan (default: all)"
    )
    task_options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional task configuration options"
    )
    
    @validator('content_types')
    def validate_content_types(cls, v):
        if v is not None:
            valid_types = [ct.value for ct in CanvasContentType]
            invalid_types = [ct for ct in v if ct not in valid_types]
            if invalid_types:
                raise ValueError(f"Invalid content types: {invalid_types}")
        return v


class TaskStatusResponse(BaseModel):
    """Task status response"""
    task_id: str
    status: str
    progress: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    execution_time_seconds: Optional[float] = None


class CourseContentSummaryResponse(BaseModel):
    """Course content summary response"""
    course_id: str
    content_types: Dict[str, int]
    total_items: int
    scan_estimate_minutes: int
    error: Optional[str] = None


class AvailableTasksResponse(BaseModel):
    """Available QA tasks response"""
    tasks: List[Dict[str, Any]]


class CanvasValidationResponse(BaseModel):
    """Canvas access validation response"""
    valid: bool
    message: str
    user_info: Optional[Dict[str, Any]] = None
    course_info: Optional[Dict[str, Any]] = None
    permissions: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# API Endpoints

@router.get("/tasks/available", response_model=AvailableTasksResponse)
async def get_available_tasks(
):
    """
    Get list of available QA automation tasks.
    
    Returns information about all available QA tasks including their
    configurations, requirements, and examples.
    """
    try:
        orchestrator = get_qa_orchestrator()
        tasks = await orchestrator.get_available_tasks()
        
        return AvailableTasksResponse(tasks=tasks)
        
    except Exception as e:
        logger.error(f"Failed to get available tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve available tasks")


@router.get("/canvas/validate", response_model=CanvasValidationResponse)
async def validate_canvas_access(
    required_permissions: Optional[str] = None
):
    """
    Validate Canvas API access and check permissions.
    
    Tests Canvas API connectivity and optionally validates specific permissions
    required for QA operations.
    """
    try:
        orchestrator = get_qa_orchestrator()
        
        # Parse required permissions if provided
        permissions_list = None
        if required_permissions:
            permissions_list = [p.strip() for p in required_permissions.split(',')]
        
        validation_result = await orchestrator.validate_canvas_access(
            canvas_context, permissions_list
        )
        
        return CanvasValidationResponse(**validation_result)
        
    except Exception as e:
        logger.error(f"Canvas validation failed: {e}")
        return CanvasValidationResponse(
            valid=False,
            message="Canvas validation failed",
            error=str(e)
        )


@router.get("/course/content-summary", response_model=CourseContentSummaryResponse)
async def get_course_content_summary(
    content_types: Optional[str] = None
):
    """
    Get summary of course content for QA planning.
    
    Provides counts of different content types and estimated processing time
    to help Learning Designers plan QA operations.
    """
    try:
        orchestrator = get_qa_orchestrator()
        
        # Parse content types if provided
        content_types_list = None
        if content_types:
            content_type_names = [ct.strip() for ct in content_types.split(',')]
            content_types_list = []
            for name in content_type_names:
                try:
                    content_types_list.append(CanvasContentType(name))
                except ValueError:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid content type: {name}"
                    )
        
        summary = await orchestrator.get_course_content_summary(
            canvas_context, content_types_list
        )
        
        return CourseContentSummaryResponse(**summary)
        
    except Exception as e:
        logger.error(f"Failed to get course content summary: {e}")
        return CourseContentSummaryResponse(
            course_id=canvas_context.get('course_id', ''),
            content_types={},
            total_items=0,
            scan_estimate_minutes=0,
            error=str(e)
        )


@router.post("/tasks/find-replace/start")
async def start_find_replace_task(
    request: StartFindReplaceRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start a Find & Replace QA automation task.
    
    Initiates scanning of Canvas course content for specified URLs and
    replaces them with new URLs. The task runs in the background and
    progress can be monitored via WebSocket or status endpoints.
    """
    try:
        orchestrator = get_qa_orchestrator()
        
        # Convert URL mappings to dictionaries
        url_mappings = [
            {"find": mapping.find, "replace": mapping.replace}
            for mapping in request.url_mappings
        ]
        
        # Convert content types to enum values
        content_types = None
        if request.content_types:
            content_types = [CanvasContentType(ct) for ct in request.content_types]
        
        # Start the task
        execution = await orchestrator.start_find_replace_task(
            url_mappings=url_mappings,
            canvas_context=canvas_context,
            content_types=content_types,
            task_options=request.task_options
        )
        
        # Schedule cleanup in background
        background_tasks.add_task(
            orchestrator.cleanup_completed_tasks,
            max_age_hours=24
        )
        
        return {
            "task_id": execution.task_id,
            "status": execution.status.value,
            "message": f"Find & Replace task started for course {canvas_context.get('course_id')}",
            "url_mappings_count": len(url_mappings),
            "content_types": [ct.value for ct in (content_types or list(CanvasContentType))],
            "started_at": execution.started_at.isoformat() if execution.started_at else None
        }
        
    except QAAutomationException as e:
        logger.error(f"QA automation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Failed to start Find & Replace task: {e}")
        raise HTTPException(status_code=500, detail="Failed to start Find & Replace task")


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
):
    """
    Get current status of a QA task.
    
    Returns detailed information about task progress, current stage,
    and results if the task is completed.
    """
    try:
        orchestrator = get_qa_orchestrator()
        execution = await orchestrator.get_task_status(task_id)
        
        if not execution:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Build response
        response = TaskStatusResponse(
            task_id=task_id,
            status=execution.status.value,
            started_at=execution.started_at.isoformat() if execution.started_at else None,
            completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
            execution_time_seconds=execution.execution_time_seconds
        )
        
        # Add progress information
        if execution.current_progress:
            response.progress = {
                "stage": execution.current_progress.stage.value,
                "current": execution.current_progress.current,
                "total": execution.current_progress.total,
                "percentage": execution.current_progress.percentage,
                "message": execution.current_progress.message,
                "updated_at": execution.current_progress.updated_at.isoformat()
            }
        
        # Add result information if completed
        if execution.status == TaskStatus.COMPLETED and execution.result:
            response.result = {
                "total_findings": execution.result.total_findings,
                "content_types_processed": [ct.value for ct in execution.result.content_types_processed],
                "items_by_content_type": execution.result.items_by_content_type,
                "total_items_scanned": execution.result.total_items_scanned,
                "execution_summary": execution.result.execution_summary
            }
        
        # Add error information if failed
        if execution.status == TaskStatus.FAILED:
            response.error = execution.error_message
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve task status")


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
):
    """
    Cancel a running QA task.
    
    Attempts to gracefully stop a running task. Tasks that are already
    completed or failed cannot be cancelled.
    """
    try:
        orchestrator = get_qa_orchestrator()
        
        # Check if task exists
        execution = await orchestrator.get_task_status(task_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Check if task can be cancelled
        if execution.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot cancel task with status: {execution.status.value}"
            )
        
        # Cancel the task
        cancelled = await orchestrator.cancel_task(task_id)
        
        if not cancelled:
            raise HTTPException(status_code=500, detail="Failed to cancel task")
        
        return {
            "task_id": task_id,
            "message": "Task cancelled successfully",
            "cancelled_at": execution.completed_at.isoformat() if execution.completed_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel task")


@router.get("/tasks/history")
async def get_task_history(
    course_id: Optional[str] = None,
    task_type: Optional[str] = None,
    limit: int = 50
):
    """
    Get task execution history for the current user.
    
    Returns a list of recent QA task executions with their results,
    optionally filtered by course or task type.
    """
    try:
        orchestrator = get_qa_orchestrator()
        
        # Use course from context if not specified
        filter_course_id = course_id or canvas_context.get('course_id')
        
        # Parse task type if provided
        filter_task_type = None
        if task_type:
            try:
                filter_task_type = QATaskType(task_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid task type: {task_type}")
        
        # Get task history
        executions = await orchestrator.get_task_history(
            user_id=canvas_context['user_id'],
            course_id=filter_course_id,
            task_type=filter_task_type,
            limit=limit
        )
        
        # Format response
        history = []
        for execution in executions:
            item = {
                "task_id": execution.task_id,
                "task_type": execution.config.task_type.value,
                "course_id": execution.config.course_id,
                "status": execution.status.value,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "execution_time_seconds": execution.execution_time_seconds
            }
            
            # Add result summary if available
            if execution.result:
                item["result_summary"] = {
                    "total_findings": execution.result.total_findings,
                    "total_items_scanned": execution.result.total_items_scanned,
                    "content_types_processed": len(execution.result.content_types_processed)
                }
            
            history.append(item)
        
        return {
            "history": history,
            "total_count": len(history),
            "filters": {
                "course_id": filter_course_id,
                "task_type": task_type,
                "limit": limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve task history")


@router.get("/tasks/{task_id}/results")
async def get_task_results(
    task_id: str,
    format: str = "json"
):
    """
    Get detailed results for a completed QA task.
    
    Returns comprehensive results including all findings, statistics,
    and execution details. Supports JSON format by default.
    """
    try:
        orchestrator = get_qa_orchestrator()
        execution = await orchestrator.get_task_status(task_id)
        
        if not execution:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if execution.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=400, 
                detail=f"Task results not available. Status: {execution.status.value}"
            )
        
        if not execution.result:
            raise HTTPException(status_code=404, detail="Task results not found")
        
        # Format results based on requested format
        if format.lower() == "json":
            return {
                "task_id": task_id,
                "task_type": execution.config.task_type.value,
                "course_id": execution.config.course_id,
                "completed_at": execution.completed_at.isoformat(),
                "execution_time_seconds": execution.execution_time_seconds,
                "results": {
                    "total_findings": execution.result.total_findings,
                    "total_items_scanned": execution.result.total_items_scanned,
                    "content_types_processed": [ct.value for ct in execution.result.content_types_processed],
                    "items_by_content_type": execution.result.items_by_content_type,
                    "findings": [
                        {
                            "content_type": finding.content_type.value,
                            "content_id": finding.content_id,
                            "content_title": finding.content_title,
                            "content_url": finding.content_url,
                            "finding_type": finding.finding_type,
                            "description": finding.description,
                            "severity": finding.severity,
                            "old_value": finding.old_value,
                            "new_value": finding.new_value,
                            "additional_data": finding.additional_data
                        }
                        for finding in execution.result.findings
                    ],
                    "execution_summary": execution.result.execution_summary
                }
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task results: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve task results") 