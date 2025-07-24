"""
Abstract QA Task Base Class

This module defines the abstract base class that all QA automation tasks must inherit from,
ensuring a consistent interface for task registration, execution, and result handling.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .data_models import (
    QATaskConfig, 
    QAResult, 
    TaskInfo, 
    ValidationResult,
    ProgressUpdate,
    QAExecution,
    TaskStatus,
    ProgressStage
)


class ProgressTracker:
    """
    Progress tracking interface for QA tasks.
    
    Provides real-time progress updates during task execution,
    including WebSocket/SSE integration for frontend updates.
    """
    
    def __init__(self, task_id: str, execution: QAExecution):
        self.task_id = task_id
        self.execution = execution
        self._callbacks: List[callable] = []
    
    def add_callback(self, callback: callable):
        """Add a progress update callback"""
        self._callbacks.append(callback)
    
    async def update_progress(
        self, 
        stage: ProgressStage, 
        current: int, 
        total: int, 
        message: str = "",
        **kwargs
    ) -> ProgressUpdate:
        """
        Update task progress with current stage and completion status.
        
        Args:
            stage: Current execution stage
            current: Current item count
            total: Total item count  
            message: Human-readable progress message
            **kwargs: Additional progress data
            
        Returns:
            ProgressUpdate object with current status
        """
        progress = self.execution.update_progress(stage, current, total, message)
        
        # Add any additional data
        for key, value in kwargs.items():
            setattr(progress, key, value)
        
        # Notify all callbacks (for WebSocket/SSE updates)
        for callback in self._callbacks:
            try:
                if hasattr(callback, '__call__'):
                    await callback(progress)
            except Exception as e:
                # Log callback errors but don't fail the task
                import logging
                logging.error(f"Progress callback error: {e}")
        
        return progress
    
    async def update_status(self, status: TaskStatus, message: str = ""):
        """Update task status"""
        self.execution.status = status
        # Could trigger status-specific callbacks here
    
    async def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log an error during task execution"""
        import logging
        logging.error(f"QA Task {self.task_id} error: {error}", extra=context or {})
    
    async def complete_task(self, result: QAResult):
        """Mark task as completed with final results"""
        self.execution.complete_execution(result)


class QATask(ABC):
    """
    Abstract base class for all QA automation tasks.
    
    All QA tasks must inherit from this class and implement the required abstract methods.
    This ensures a consistent interface for task registration, execution, and result handling.
    """
    
    @abstractmethod
    async def execute(
        self, 
        config: QATaskConfig, 
        progress_tracker: ProgressTracker,
        canvas_context: Optional[Dict[str, Any]] = None,
        lti_context: Optional[Dict[str, Any]] = None
    ) -> QAResult:
        """
        Execute the QA automation task.
        
        Args:
            config: Task configuration containing parameters and settings
            progress_tracker: Progress tracking interface for real-time updates  
            canvas_context: Canvas course and user context from LTI launch
            lti_context: LTI-specific context and authentication data
            
        Returns:
            QAResult containing findings, statistics, and execution metadata
            
        Raises:
            QATaskError: If task execution fails
        """
        pass
    
    @abstractmethod
    def get_task_info(self) -> TaskInfo:
        """
        Get metadata and information about this QA task.
        
        Returns:
            TaskInfo containing task name, description, version, requirements, etc.
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: QATaskConfig) -> ValidationResult:
        """
        Validate task configuration before execution.
        
        Args:
            config: Task configuration to validate
            
        Returns:
            ValidationResult indicating if config is valid, with any errors/warnings
        """
        pass
    
    @abstractmethod
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for task configuration.
        
        Used for frontend form generation and API validation.
        
        Returns:
            JSON schema dictionary for task-specific configuration
        """
        pass
    
    # Optional hooks that tasks can override
    
    async def pre_execute(
        self, 
        config: QATaskConfig, 
        canvas_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Pre-execution hook called before main execute() method.
        
        Can be used for setup, validation, or permission checks.
        
        Args:
            config: Task configuration
            canvas_context: Canvas context from LTI
            
        Returns:
            True if execution should proceed, False to abort
        """
        return True
    
    async def post_execute(
        self, 
        config: QATaskConfig, 
        result: QAResult,
        canvas_context: Optional[Dict[str, Any]] = None
    ) -> QAResult:
        """
        Post-execution hook called after main execute() method.
        
        Can be used for cleanup, result processing, or notifications.
        
        Args:
            config: Task configuration
            result: Execution result from execute() method
            canvas_context: Canvas context from LTI
            
        Returns:
            Potentially modified QAResult
        """
        return result
    
    async def on_error(
        self, 
        error: Exception, 
        config: QATaskConfig,
        progress_tracker: ProgressTracker
    ):
        """
        Error handling hook called when execution fails.
        
        Args:
            error: Exception that caused the failure
            config: Task configuration
            progress_tracker: Progress tracker for error reporting
        """
        await progress_tracker.log_error(error, {
            'task_type': config.task_type,
            'task_id': config.task_id,
            'course_id': config.course_id
        })
    
    async def on_cancel(
        self, 
        config: QATaskConfig,
        progress_tracker: ProgressTracker
    ):
        """
        Cancellation hook called when task is cancelled by user.
        
        Args:
            config: Task configuration
            progress_tracker: Progress tracker for cancellation reporting
        """
        await progress_tracker.update_status(TaskStatus.CANCELLED, "Task cancelled by user")
    
    # Utility methods for common task operations
    
    def create_base_result(self, config: QATaskConfig) -> QAResult:
        """
        Create a base QAResult with common fields populated.
        
        Args:
            config: Task configuration
            
        Returns:
            QAResult with basic fields set
        """
        from datetime import datetime
        
        return QAResult(
            task_id=config.task_id,
            task_type=config.task_type,
            status=TaskStatus.RUNNING,
            started_at=datetime.utcnow()
        )
    
    def requires_canvas_permissions(self) -> List[str]:
        """
        Get list of Canvas permissions required by this task.
        
        Returns:
            List of Canvas permission strings
        """
        task_info = self.get_task_info()
        return task_info.required_canvas_permissions
    
    def supports_content_types(self) -> List[str]:
        """
        Get list of Canvas content types supported by this task.
        
        Returns:
            List of Canvas content type strings
        """
        task_info = self.get_task_info()
        return [ct.value for ct in task_info.supported_content_types]
    
    def get_display_name(self) -> str:
        """Get human-readable task name"""
        return self.get_task_info().name
    
    def get_description(self) -> str:
        """Get task description"""
        return self.get_task_info().description
    
    def get_version(self) -> str:
        """Get task version"""
        return self.get_task_info().version


# Base exception for QA task errors
class QATaskError(Exception):
    """Base exception for QA task execution errors"""
    
    def __init__(self, message: str, task_id: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.task_id = task_id
        self.details = details or {}


class QATaskConfigError(QATaskError):
    """Exception for QA task configuration errors"""
    pass


class QATaskExecutionError(QATaskError):
    """Exception for QA task execution errors"""
    pass


class QATaskCancelledError(QATaskError):
    """Exception for QA task cancellation"""
    pass


class QATaskTimeoutError(QATaskError):
    """Exception for QA task timeout"""
    pass 