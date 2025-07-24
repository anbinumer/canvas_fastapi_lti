"""
QA Execution Engine

This module provides asynchronous task execution for QA automation,
handling background processing, Canvas API rate limiting, and session persistence.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set
from uuid import uuid4

from .qa_task import QATask, ProgressTracker, QATaskError, QATaskExecutionError, QATaskTimeoutError
from .data_models import (
    QATaskConfig, QAResult, QAExecution, TaskStatus, ProgressStage,
    QATaskType, ProgressUpdate
)
from .task_registry import get_registry

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Canvas API rate limiter to handle 200/min and 5000/hour limits.
    """
    
    def __init__(self, calls_per_minute: int = 180, calls_per_hour: int = 4800):
        # Set slightly below Canvas limits for safety margin
        self.calls_per_minute = calls_per_minute
        self.calls_per_hour = calls_per_hour
        
        # Tracking
        self.minute_calls: List[float] = []
        self.hour_calls: List[float] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """
        Acquire permission to make a Canvas API call.
        
        Returns:
            True if call is allowed, False if rate limited
        """
        async with self._lock:
            now = time.time()
            
            # Clean old calls
            minute_ago = now - 60
            hour_ago = now - 3600
            
            self.minute_calls = [t for t in self.minute_calls if t > minute_ago]
            self.hour_calls = [t for t in self.hour_calls if t > hour_ago]
            
            # Check limits
            if len(self.minute_calls) >= self.calls_per_minute:
                return False
            if len(self.hour_calls) >= self.calls_per_hour:
                return False
            
            # Record this call
            self.minute_calls.append(now)
            self.hour_calls.append(now)
            
            return True
    
    async def wait_for_availability(self) -> float:
        """
        Wait until API call is available.
        
        Returns:
            Seconds waited
        """
        start_time = time.time()
        
        while not await self.acquire():
            await asyncio.sleep(1)  # Check every second
        
        return time.time() - start_time
    
    def get_remaining_calls(self) -> Dict[str, int]:
        """Get remaining API calls for minute and hour"""
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600
        
        minute_calls = len([t for t in self.minute_calls if t > minute_ago])
        hour_calls = len([t for t in self.hour_calls if t > hour_ago])
        
        return {
            'minute_remaining': max(0, self.calls_per_minute - minute_calls),
            'hour_remaining': max(0, self.calls_per_hour - hour_calls)
        }


class QAExecutionEngine:
    """
    Asynchronous execution engine for QA automation tasks.
    
    Handles background processing, Canvas API rate limiting, progress tracking,
    and session persistence for long-running operations.
    """
    
    def __init__(self):
        self._active_executions: Dict[str, QAExecution] = {}
        self._execution_tasks: Dict[str, asyncio.Task] = {}
        self._rate_limiter = RateLimiter()
        self._progress_callbacks: Dict[str, List[Callable]] = {}
        self._cancellation_tokens: Set[str] = set()
    
    async def execute_task(
        self,
        config: QATaskConfig,
        canvas_context: Optional[Dict[str, Any]] = None,
        lti_context: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable] = None
    ) -> QAExecution:
        """
        Execute a QA automation task asynchronously.
        
        Args:
            config: Task configuration
            canvas_context: Canvas course and user context
            lti_context: LTI-specific context
            progress_callback: Callback for progress updates
            
        Returns:
            QAExecution object for tracking
        """
        # Create execution tracking
        execution = QAExecution(
            task_id=config.task_id,
            config=config,
            canvas_context=canvas_context or {},
            lti_context=lti_context or {}
        )
        
        self._active_executions[config.task_id] = execution
        
        # Set up progress callback
        if progress_callback:
            self._progress_callbacks[config.task_id] = [progress_callback]
        
        # Start background task
        task = asyncio.create_task(
            self._execute_task_background(execution)
        )
        self._execution_tasks[config.task_id] = task
        
        logger.info(f"Started QA task execution: {config.task_id} ({config.task_type})")
        
        return execution
    
    async def _execute_task_background(self, execution: QAExecution):
        """
        Background task execution with error handling and cleanup.
        """
        task_id = execution.task_id
        config = execution.config
        
        try:
            # Mark as started
            execution.start_execution()
            await self._notify_progress(execution, ProgressStage.INITIALIZING, 0, 100, "Initializing task")
            
            # Get task class from registry
            registry = get_registry()
            task_class = registry.get_task_class(config.task_type.value)
            
            if not task_class:
                raise QATaskExecutionError(f"Task type '{config.task_type}' not found", task_id)
            
            # Create task instance
            task_instance = task_class()
            
            # Validate configuration
            await self._notify_progress(execution, ProgressStage.VALIDATING, 10, 100, "Validating configuration")
            validation_result = task_instance.validate_config(config)
            
            if not validation_result.is_valid:
                error_msg = f"Configuration validation failed: {', '.join(validation_result.errors)}"
                raise QATaskExecutionError(error_msg, task_id)
            
            # Create progress tracker
            progress_tracker = ProgressTracker(task_id, execution)
            
            # Add progress callbacks
            if task_id in self._progress_callbacks:
                for callback in self._progress_callbacks[task_id]:
                    progress_tracker.add_callback(callback)
            
            # Check for cancellation
            if task_id in self._cancellation_tokens:
                await task_instance.on_cancel(config, progress_tracker)
                return
            
            # Pre-execution hook
            if not await task_instance.pre_execute(config, execution.canvas_context):
                raise QATaskExecutionError("Pre-execution check failed", task_id)
            
            # Check timeout
            start_time = time.time()
            timeout_seconds = config.timeout_seconds
            
            # Main execution with timeout
            try:
                result = await asyncio.wait_for(
                    task_instance.execute(
                        config, 
                        progress_tracker, 
                        execution.canvas_context, 
                        execution.lti_context
                    ),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                raise QATaskTimeoutError(f"Task execution timed out after {timeout_seconds} seconds", task_id)
            
            # Check for cancellation before post-processing
            if task_id in self._cancellation_tokens:
                await task_instance.on_cancel(config, progress_tracker)
                return
            
            # Post-execution hook
            result = await task_instance.post_execute(config, result, execution.canvas_context)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            result.execution_time_seconds = execution_time
            result.completed_at = datetime.utcnow()
            
            # Complete execution
            execution.complete_execution(result)
            
            await self._notify_progress(execution, ProgressStage.COMPLETED, 100, 100, "Task completed successfully")
            
            logger.info(f"QA task completed successfully: {task_id} ({execution_time:.2f}s)")
            
        except QATaskError as e:
            # Handle QA-specific errors
            await self._handle_task_error(execution, e)
            
        except Exception as e:
            # Handle unexpected errors
            error = QATaskExecutionError(f"Unexpected error during task execution: {str(e)}", task_id)
            await self._handle_task_error(execution, error)
            
        finally:
            # Cleanup
            await self._cleanup_execution(task_id)
    
    async def _handle_task_error(self, execution: QAExecution, error: QATaskError):
        """Handle task execution errors"""
        task_id = execution.task_id
        
        logger.error(f"QA task failed: {task_id} - {error}")
        
        # Fail the execution
        execution.fail_execution(str(error), getattr(error, 'details', {}))
        
        # Notify progress
        await self._notify_progress(
            execution, 
            ProgressStage.COMPLETED, 
            0, 100, 
            f"Task failed: {error}"
        )
        
        # Call error hook if task instance is available
        try:
            registry = get_registry()
            task_class = registry.get_task_class(execution.config.task_type.value)
            if task_class:
                task_instance = task_class()
                progress_tracker = ProgressTracker(task_id, execution)
                await task_instance.on_error(error, execution.config, progress_tracker)
        except Exception as hook_error:
            logger.error(f"Error in task error hook: {hook_error}")
    
    async def _notify_progress(
        self, 
        execution: QAExecution, 
        stage: ProgressStage, 
        current: int, 
        total: int, 
        message: str
    ):
        """Notify progress callbacks"""
        task_id = execution.task_id
        
        # Update execution progress
        progress = execution.update_progress(stage, current, total, message)
        
        # Add rate limiting info
        remaining = self._rate_limiter.get_remaining_calls()
        progress.rate_limit_remaining = remaining.get('minute_remaining')
        
        # Notify callbacks
        if task_id in self._progress_callbacks:
            for callback in self._progress_callbacks[task_id]:
                try:
                    await callback(progress)
                except Exception as e:
                    logger.error(f"Progress callback error for {task_id}: {e}")
    
    async def _cleanup_execution(self, task_id: str):
        """Clean up execution resources"""
        try:
            # Remove from active executions
            self._active_executions.pop(task_id, None)
            
            # Cancel and remove task
            if task_id in self._execution_tasks:
                task = self._execution_tasks.pop(task_id)
                if not task.done():
                    task.cancel()
            
            # Remove callbacks
            self._progress_callbacks.pop(task_id, None)
            
            # Remove cancellation token
            self._cancellation_tokens.discard(task_id)
            
        except Exception as e:
            logger.error(f"Error during execution cleanup for {task_id}: {e}")
    
    def get_execution(self, task_id: str) -> Optional[QAExecution]:
        """Get execution by task ID"""
        return self._active_executions.get(task_id)
    
    def list_active_executions(self) -> List[QAExecution]:
        """Get list of active executions"""
        return list(self._active_executions.values())
    
    def get_execution_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get execution status"""
        execution = self._active_executions.get(task_id)
        return execution.status if execution else None
    
    async def cancel_execution(self, task_id: str) -> bool:
        """
        Cancel a running execution.
        
        Args:
            task_id: Task ID to cancel
            
        Returns:
            True if cancellation initiated, False if task not found
        """
        if task_id not in self._active_executions:
            return False
        
        # Mark for cancellation
        self._cancellation_tokens.add(task_id)
        
        # Update status
        execution = self._active_executions[task_id]
        execution.status = TaskStatus.CANCELLED
        
        # Cancel the background task
        if task_id in self._execution_tasks:
            task = self._execution_tasks[task_id]
            task.cancel()
        
        logger.info(f"Cancelled QA task execution: {task_id}")
        return True
    
    def add_progress_callback(self, task_id: str, callback: Callable):
        """Add progress callback for a task"""
        if task_id not in self._progress_callbacks:
            self._progress_callbacks[task_id] = []
        self._progress_callbacks[task_id].append(callback)
    
    def get_rate_limiter(self) -> RateLimiter:
        """Get the Canvas API rate limiter"""
        return self._rate_limiter
    
    async def wait_for_completion(self, task_id: str, timeout: Optional[float] = None) -> Optional[QAExecution]:
        """
        Wait for task completion.
        
        Args:
            task_id: Task ID to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            Final execution state or None if timeout
        """
        if task_id not in self._execution_tasks:
            return self._active_executions.get(task_id)
        
        try:
            task = self._execution_tasks[task_id]
            await asyncio.wait_for(task, timeout=timeout)
            return self._active_executions.get(task_id)
        except asyncio.TimeoutError:
            return None
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get execution engine statistics"""
        active_count = len(self._active_executions)
        status_counts = {}
        
        for execution in self._active_executions.values():
            status = execution.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        rate_limit_info = self._rate_limiter.get_remaining_calls()
        
        return {
            'active_executions': active_count,
            'status_breakdown': status_counts,
            'rate_limit_remaining': rate_limit_info,
            'cancellation_tokens': len(self._cancellation_tokens)
        }


# Global execution engine instance
_global_engine = QAExecutionEngine()


def get_execution_engine() -> QAExecutionEngine:
    """Get the global QA execution engine"""
    return _global_engine 