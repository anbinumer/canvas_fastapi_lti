"""
QA Orchestrator Service

Coordinates QA task execution, manages workflows, and provides high-level
interfaces for QA automation operations.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4

from qa_framework.base import (
    QAExecutionEngine,
    get_execution_engine,
    get_registry,
    QATaskConfig,
    QAResult,
    QAExecution,
    TaskStatus,
    QATaskType,
    CanvasContentType,
    FindReplaceConfig,
    ProgressUpdate,
    QATaskError
)
from qa_framework.utils import (
    get_progress_broadcaster,
    create_task_progress_tracker,
    handle_qa_error,
    ErrorCategory
)
from app.core.exceptions import QAAutomationException
from services.canvas_service import ProductionCanvasService
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)


class QAOrchestrator:
    """
    QA task orchestration service.
    
    Provides high-level interfaces for:
    - Starting and managing QA task executions
    - Coordinating Canvas API access and LTI context
    - Managing progress notifications and error handling
    - Providing task status and result retrieval
    """
    
    def __init__(self):
        """Initialize QA orchestrator"""
        self.execution_engine = get_execution_engine()
        self.task_registry = get_registry()
        self.progress_broadcaster = get_progress_broadcaster()
        self.session_service = SessionService()
        
        # Active task tracking
        self._active_tasks: Dict[str, QAExecution] = {}
        self._task_callbacks: Dict[str, List[Callable]] = {}
        
    async def start_find_replace_task(
        self,
        url_mappings: List[Dict[str, str]],
        canvas_context: Dict[str, Any],
        lti_context: Optional[Dict[str, Any]] = None,
        content_types: Optional[List[CanvasContentType]] = None,
        task_options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable] = None
    ) -> QAExecution:
        """
        Start a Find & Replace QA task.
        
        Args:
            url_mappings: List of URL mapping dictionaries with 'find' and 'replace' keys
            canvas_context: Canvas course and user context from LTI
            lti_context: LTI-specific context
            content_types: List of content types to process (default: all)
            task_options: Additional task configuration options
            progress_callback: Optional callback for progress updates
            
        Returns:
            QAExecution object tracking the task
        """
        try:
            # Validate required context
            if not canvas_context.get('course_id'):
                raise QAAutomationException("Course ID not found in Canvas context")
            
            if not canvas_context.get('user_id'):
                raise QAAutomationException("User ID not found in Canvas context")
            
            # Create task configuration
            config = FindReplaceConfig(
                task_id=str(uuid4()),
                task_type=QATaskType.FIND_REPLACE,
                course_id=canvas_context['course_id'],
                user_id=canvas_context['user_id'],
                canvas_instance_url=canvas_context.get('canvas_instance_url', ''),
                canvas_access_token=canvas_context.get('access_token'),
                url_mappings=url_mappings,
                content_types=content_types or list(CanvasContentType),
                case_sensitive=task_options.get('case_sensitive', False) if task_options else False,
                whole_word_only=task_options.get('whole_word_only', False) if task_options else False,
                include_html_attributes=task_options.get('include_html_attributes', True) if task_options else True
            )
            
            # Validate configuration
            task_class = self.task_registry.get_task_class('find_replace')
            if not task_class:
                raise QAAutomationException("Find & Replace task not found in registry")
            
            task_instance = task_class()
            validation_result = task_instance.validate_config(config)
            
            if not validation_result.is_valid:
                error_msg = f"Invalid task configuration: {', '.join(validation_result.errors)}"
                raise QAAutomationException(error_msg)
            
            # Log warnings if any
            if validation_result.warnings:
                for warning in validation_result.warnings:
                    logger.warning(f"Task configuration warning: {warning}")
            
            # Set up progress tracking
            if progress_callback:
                self._add_task_callback(config.task_id, progress_callback)
            
            # Start task execution
            execution = await self.execution_engine.execute_task(
                config=config,
                canvas_context=canvas_context,
                lti_context=lti_context,
                progress_callback=self._create_progress_callback(config.task_id)
            )
            
            # Track active task
            self._active_tasks[config.task_id] = execution
            
            logger.info(f"Started Find & Replace task: {config.task_id} for course {config.course_id}")
            
            return execution
            
        except Exception as e:
            logger.error(f"Failed to start Find & Replace task: {e}")
            
            # Handle error through framework
            error_info = await handle_qa_error(
                e, "", "find_replace", 
                canvas_context.get('user_id', ''),
                canvas_context.get('course_id', ''),
                canvas_context.get('canvas_instance_url', ''),
                "task_start"
            )
            
            raise QAAutomationException(error_info.user_message)
    
    async def get_task_status(self, task_id: str) -> Optional[QAExecution]:
        """
        Get current status of a QA task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            QAExecution object or None if not found
        """
        # Check active tasks first
        if task_id in self._active_tasks:
            return self._active_tasks[task_id]
        
        # Check execution engine
        return await self.execution_engine.get_execution_status(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running QA task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if task was cancelled successfully
        """
        try:
            # Cancel in execution engine
            cancelled = await self.execution_engine.cancel_execution(task_id)
            
            # Remove from active tasks
            if task_id in self._active_tasks:
                del self._active_tasks[task_id]
            
            # Clean up callbacks
            if task_id in self._task_callbacks:
                del self._task_callbacks[task_id]
            
            logger.info(f"Cancelled task: {task_id}")
            return cancelled
            
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
    
    async def get_task_history(
        self,
        user_id: str,
        course_id: Optional[str] = None,
        task_type: Optional[QATaskType] = None,
        limit: int = 50
    ) -> List[QAExecution]:
        """
        Get task execution history for a user.
        
        Args:
            user_id: User identifier
            course_id: Optional course filter
            task_type: Optional task type filter
            limit: Maximum number of results
            
        Returns:
            List of QAExecution objects
        """
        try:
            return await self.execution_engine.get_execution_history(
                user_id=user_id,
                course_id=course_id,
                task_type=task_type,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Failed to get task history: {e}")
            return []
    
    async def get_available_tasks(self) -> List[Dict[str, Any]]:
        """
        Get list of available QA tasks with their metadata.
        
        Returns:
            List of task information dictionaries
        """
        try:
            tasks = []
            
            for task_name in self.task_registry.list_tasks():
                task_info = self.task_registry.get_task_info(task_name)
                if task_info:
                    tasks.append({
                        'name': task_name,
                        'display_name': task_info.name,
                        'description': task_info.description,
                        'version': task_info.version,
                        'task_type': task_info.task_type.value,
                        'supported_content_types': [ct.value for ct in task_info.supported_content_types],
                        'required_permissions': task_info.required_canvas_permissions,
                        'help_text': task_info.help_text,
                        'examples': task_info.examples
                    })
            
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to get available tasks: {e}")
            return []
    
    async def validate_canvas_access(
        self,
        canvas_context: Dict[str, Any],
        required_permissions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate Canvas API access and permissions.
        
        Args:
            canvas_context: Canvas context from LTI
            required_permissions: List of required permissions to check
            
        Returns:
            Validation result dictionary
        """
        try:
            # Create Canvas service
            canvas_service = await create_canvas_service_from_lti(canvas_context)
            
            try:
                # Test basic connection
                user_info = await canvas_service.get_user_info()
                
                # Get course information
                course_id = canvas_context.get('course_id')
                course_info = {}
                permissions = {}
                
                if course_id:
                    course_info = await canvas_service.get_course(course_id)
                    
                    # Check permissions if specified
                    if required_permissions:
                        permissions = await canvas_service.get_course_permissions(course_id)
                
                return {
                    'valid': True,
                    'user_info': user_info,
                    'course_info': course_info,
                    'permissions': permissions,
                    'message': 'Canvas access validated successfully'
                }
                
            finally:
                await canvas_service.close()
                
        except Exception as e:
            logger.error(f"Canvas access validation failed: {e}")
            return {
                'valid': False,
                'error': str(e),
                'message': 'Canvas access validation failed'
            }
    
    async def get_course_content_summary(
        self,
        canvas_context: Dict[str, Any],
        content_types: Optional[List[CanvasContentType]] = None
    ) -> Dict[str, Any]:
        """
        Get summary of course content for QA planning.
        
        Args:
            canvas_context: Canvas context from LTI
            content_types: Content types to summarize (default: all)
            
        Returns:
            Content summary dictionary
        """
        try:
            canvas_service = await create_canvas_service_from_lti(canvas_context)
            course_id = canvas_context.get('course_id')
            
            if not course_id:
                raise ValueError("Course ID not found in context")
            
            summary = {
                'course_id': course_id,
                'content_types': {},
                'total_items': 0,
                'scan_estimate_minutes': 0
            }
            
            try:
                content_types = content_types or list(CanvasContentType)
                
                for content_type in content_types:
                    count = 0
                    
                    if content_type == CanvasContentType.SYLLABUS:
                        # Syllabus is always 1 item (if exists)
                        syllabus = await canvas_service.get_syllabus(course_id)
                        count = 1 if syllabus.get('syllabus_body') else 0
                    elif content_type == CanvasContentType.PAGES:
                        pages = await canvas_service.get_pages(course_id)
                        count = len(pages)
                    elif content_type == CanvasContentType.ASSIGNMENTS:
                        assignments = await canvas_service.get_assignments(course_id)
                        count = len(assignments)
                    elif content_type == CanvasContentType.QUIZZES:
                        quizzes = await canvas_service.get_quizzes(course_id)
                        count = len(quizzes)
                    elif content_type == CanvasContentType.DISCUSSIONS:
                        discussions = await canvas_service.get_discussions(course_id)
                        count = len(discussions)
                    elif content_type == CanvasContentType.ANNOUNCEMENTS:
                        announcements = await canvas_service.get_announcements(course_id)
                        count = len(announcements)
                    elif content_type == CanvasContentType.MODULES:
                        modules = await canvas_service.get_modules(course_id)
                        count = len(modules)
                    
                    summary['content_types'][content_type.value] = count
                    summary['total_items'] += count
                
                # Estimate scan time (rough calculation)
                # Assume 2-5 seconds per item depending on content type
                base_time = summary['total_items'] * 3  # seconds
                summary['scan_estimate_minutes'] = max(1, base_time // 60)
                
                return summary
                
            finally:
                await canvas_service.close()
                
        except Exception as e:
            logger.error(f"Failed to get course content summary: {e}")
            return {
                'error': str(e),
                'content_types': {},
                'total_items': 0,
                'scan_estimate_minutes': 0
            }
    
    def _add_task_callback(self, task_id: str, callback: Callable):
        """Add progress callback for a task"""
        if task_id not in self._task_callbacks:
            self._task_callbacks[task_id] = []
        self._task_callbacks[task_id].append(callback)
    
    def _create_progress_callback(self, task_id: str) -> Callable:
        """Create progress callback that broadcasts to all registered callbacks"""
        async def progress_callback(update: ProgressUpdate):
            try:
                # Broadcast via progress broadcaster
                await self.progress_broadcaster.broadcast_progress(update)
                
                # Call task-specific callbacks
                if task_id in self._task_callbacks:
                    for callback in self._task_callbacks[task_id]:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(update)
                            else:
                                callback(update)
                        except Exception as e:
                            logger.warning(f"Progress callback error: {e}")
                
            except Exception as e:
                logger.error(f"Progress broadcast error: {e}")
        
        return progress_callback
    
    async def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """
        Clean up completed task records older than specified age.
        
        Args:
            max_age_hours: Maximum age in hours for completed tasks
        """
        try:
            # Remove from active tasks
            completed_tasks = [
                task_id for task_id, execution in self._active_tasks.items()
                if execution.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
                and execution.completed_at
                and (datetime.utcnow() - execution.completed_at).total_seconds() > (max_age_hours * 3600)
            ]
            
            for task_id in completed_tasks:
                del self._active_tasks[task_id]
                if task_id in self._task_callbacks:
                    del self._task_callbacks[task_id]
            
            logger.info(f"Cleaned up {len(completed_tasks)} completed tasks")
            
        except Exception as e:
            logger.error(f"Failed to cleanup completed tasks: {e}")


# Global orchestrator instance
_orchestrator: Optional[QAOrchestrator] = None


def get_qa_orchestrator() -> QAOrchestrator:
    """Get global QA orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = QAOrchestrator()
    return _orchestrator 