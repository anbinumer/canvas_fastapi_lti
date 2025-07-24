"""
Error Handling Framework

This module provides comprehensive error handling for QA automation tasks,
including Canvas API error classification, recovery mechanisms, and debugging support.
"""

import logging
import time
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union
from dataclasses import dataclass

from ..base.qa_task import QATaskError, QATaskExecutionError, QATaskTimeoutError

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification"""
    CANVAS_API = "canvas_api"
    TASK_CONFIG = "task_config"
    DATA_PROCESSING = "data_processing"
    SYSTEM = "system"
    AUTHENTICATION = "authentication"
    RATE_LIMITING = "rate_limiting"
    NETWORK = "network"
    TIMEOUT = "timeout"


class RecoveryStrategy(str, Enum):
    """Error recovery strategies"""
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    ABORT = "abort"
    USER_INTERVENTION = "user_intervention"


@dataclass
class ErrorContext:
    """Context information for errors"""
    task_id: str
    task_type: str
    user_id: str
    course_id: str
    canvas_instance: str
    timestamp: datetime
    stage: str
    additional_data: Dict[str, Any]


@dataclass
class ErrorInfo:
    """Comprehensive error information"""
    error: Exception
    category: ErrorCategory
    severity: ErrorSeverity
    recovery_strategy: RecoveryStrategy
    context: ErrorContext
    user_message: str
    technical_message: str
    suggested_actions: List[str]
    can_retry: bool = False
    retry_delay_seconds: int = 0
    max_retries: int = 0


class CanvasAPIErrorClassifier:
    """
    Classifier for Canvas API errors with recovery strategies.
    """
    
    # Canvas API error patterns
    ERROR_PATTERNS = {
        # Authentication errors
        "unauthorized": {
            "category": ErrorCategory.AUTHENTICATION,
            "severity": ErrorSeverity.HIGH,
            "recovery": RecoveryStrategy.USER_INTERVENTION,
            "user_message": "Authentication failed. Please check your Canvas access permissions.",
            "can_retry": False
        },
        "forbidden": {
            "category": ErrorCategory.AUTHENTICATION,
            "severity": ErrorSeverity.HIGH,
            "recovery": RecoveryStrategy.USER_INTERVENTION,
            "user_message": "Access denied. You may not have permission to access this content.",
            "can_retry": False
        },
        
        # Rate limiting errors
        "rate limit": {
            "category": ErrorCategory.RATE_LIMITING,
            "severity": ErrorSeverity.MEDIUM,
            "recovery": RecoveryStrategy.RETRY,
            "user_message": "Canvas API rate limit reached. Waiting before retrying...",
            "can_retry": True,
            "retry_delay": 60,
            "max_retries": 5
        },
        "too many requests": {
            "category": ErrorCategory.RATE_LIMITING,
            "severity": ErrorSeverity.MEDIUM,
            "recovery": RecoveryStrategy.RETRY,
            "user_message": "Too many requests to Canvas. Slowing down and retrying...",
            "can_retry": True,
            "retry_delay": 30,
            "max_retries": 3
        },
        
        # Network errors
        "connection": {
            "category": ErrorCategory.NETWORK,
            "severity": ErrorSeverity.MEDIUM,
            "recovery": RecoveryStrategy.RETRY,
            "user_message": "Network connection issue. Retrying...",
            "can_retry": True,
            "retry_delay": 10,
            "max_retries": 3
        },
        "timeout": {
            "category": ErrorCategory.TIMEOUT,
            "severity": ErrorSeverity.MEDIUM,
            "recovery": RecoveryStrategy.RETRY,
            "user_message": "Request timed out. Retrying with longer timeout...",
            "can_retry": True,
            "retry_delay": 5,
            "max_retries": 2
        },
        
        # Canvas-specific errors
        "not found": {
            "category": ErrorCategory.CANVAS_API,
            "severity": ErrorSeverity.LOW,
            "recovery": RecoveryStrategy.SKIP,
            "user_message": "Content not found or may have been deleted.",
            "can_retry": False
        },
        "invalid": {
            "category": ErrorCategory.TASK_CONFIG,
            "severity": ErrorSeverity.HIGH,
            "recovery": RecoveryStrategy.ABORT,
            "user_message": "Invalid configuration or parameters.",
            "can_retry": False
        }
    }
    
    @classmethod
    def classify_error(cls, error: Exception, context: ErrorContext) -> ErrorInfo:
        """
        Classify an error and determine recovery strategy.
        
        Args:
            error: Exception to classify
            context: Error context information
            
        Returns:
            ErrorInfo with classification and recovery strategy
        """
        error_str = str(error).lower()
        
        # Find matching pattern
        error_config = None
        for pattern, config in cls.ERROR_PATTERNS.items():
            if pattern in error_str:
                error_config = config
                break
        
        # Default classification for unknown errors
        if not error_config:
            error_config = {
                "category": ErrorCategory.SYSTEM,
                "severity": ErrorSeverity.MEDIUM,
                "recovery": RecoveryStrategy.RETRY,
                "user_message": "An unexpected error occurred during QA processing.",
                "can_retry": True,
                "retry_delay": 5,
                "max_retries": 1
            }
        
        # Create ErrorInfo
        return ErrorInfo(
            error=error,
            category=ErrorCategory(error_config["category"]),
            severity=ErrorSeverity(error_config["severity"]),
            recovery_strategy=RecoveryStrategy(error_config["recovery"]),
            context=context,
            user_message=error_config["user_message"],
            technical_message=f"{type(error).__name__}: {str(error)}",
            suggested_actions=cls._get_suggested_actions(error_config),
            can_retry=error_config.get("can_retry", False),
            retry_delay_seconds=error_config.get("retry_delay", 0),
            max_retries=error_config.get("max_retries", 0)
        )
    
    @classmethod
    def _get_suggested_actions(cls, error_config: Dict[str, Any]) -> List[str]:
        """Get suggested actions based on error configuration"""
        category = error_config["category"]
        
        if category == ErrorCategory.AUTHENTICATION:
            return [
                "Check your Canvas login status",
                "Verify you have the required permissions",
                "Contact your Canvas administrator if the issue persists"
            ]
        elif category == ErrorCategory.RATE_LIMITING:
            return [
                "The system will automatically retry after a delay",
                "Consider reducing the scope of your QA task",
                "Try running the task during off-peak hours"
            ]
        elif category == ErrorCategory.NETWORK:
            return [
                "Check your internet connection",
                "The system will automatically retry",
                "Contact support if the issue persists"
            ]
        elif category == ErrorCategory.CANVAS_API:
            return [
                "Check if the content still exists in Canvas",
                "Verify the course is accessible",
                "Contact Canvas support if needed"
            ]
        else:
            return [
                "The system will attempt to recover automatically",
                "Contact support if the issue persists"
            ]


class QAErrorHandler:
    """
    Comprehensive error handler for QA automation tasks.
    
    Provides error classification, recovery mechanisms, logging,
    and user-friendly error reporting.
    """
    
    def __init__(self):
        self.error_history: List[ErrorInfo] = []
        self.retry_counts: Dict[str, int] = {}
        self.max_history_size = 1000
    
    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        task_id: Optional[str] = None
    ) -> ErrorInfo:
        """
        Handle an error with classification and recovery.
        
        Args:
            error: Exception to handle
            context: Error context
            task_id: Optional task ID for tracking
            
        Returns:
            ErrorInfo with handling result
        """
        # Classify the error
        error_info = CanvasAPIErrorClassifier.classify_error(error, context)
        
        # Log the error
        await self._log_error(error_info)
        
        # Store in history
        self._store_error_history(error_info)
        
        # Update retry tracking
        if task_id and error_info.can_retry:
            retry_key = f"{task_id}:{type(error).__name__}"
            self.retry_counts[retry_key] = self.retry_counts.get(retry_key, 0) + 1
            
            # Check if max retries exceeded
            if self.retry_counts[retry_key] > error_info.max_retries:
                error_info.can_retry = False
                error_info.recovery_strategy = RecoveryStrategy.ABORT
                error_info.user_message = "Maximum retry attempts exceeded. Please try again later."
        
        return error_info
    
    async def _log_error(self, error_info: ErrorInfo):
        """Log error with appropriate level"""
        log_data = {
            'task_id': error_info.context.task_id,
            'category': error_info.category.value,
            'severity': error_info.severity.value,
            'recovery_strategy': error_info.recovery_strategy.value,
            'error_type': type(error_info.error).__name__,
            'course_id': error_info.context.course_id,
            'user_id': error_info.context.user_id
        }
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(error_info.technical_message, extra=log_data)
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error(error_info.technical_message, extra=log_data)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(error_info.technical_message, extra=log_data)
        else:
            logger.info(error_info.technical_message, extra=log_data)
        
        # Add stack trace for debugging
        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.debug(f"Stack trace for {error_info.context.task_id}:\n{traceback.format_exc()}")
    
    def _store_error_history(self, error_info: ErrorInfo):
        """Store error in history with size limit"""
        self.error_history.append(error_info)
        
        # Limit history size
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
    
    def get_error_statistics(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Get error statistics"""
        errors = self.error_history
        if task_id:
            errors = [e for e in errors if e.context.task_id == task_id]
        
        if not errors:
            return {"total_errors": 0}
        
        # Count by category
        category_counts = {}
        severity_counts = {}
        recovery_counts = {}
        
        for error in errors:
            category = error.category.value
            severity = error.severity.value
            recovery = error.recovery_strategy.value
            
            category_counts[category] = category_counts.get(category, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            recovery_counts[recovery] = recovery_counts.get(recovery, 0) + 1
        
        return {
            "total_errors": len(errors),
            "by_category": category_counts,
            "by_severity": severity_counts,
            "by_recovery_strategy": recovery_counts,
            "most_recent": errors[-1].timestamp.isoformat() if errors else None
        }
    
    def get_recent_errors(self, task_id: Optional[str] = None, limit: int = 10) -> List[ErrorInfo]:
        """Get recent errors"""
        errors = self.error_history
        if task_id:
            errors = [e for e in errors if e.context.task_id == task_id]
        
        return errors[-limit:] if errors else []
    
    def should_retry(self, task_id: str, error_type: Type[Exception]) -> bool:
        """Check if an error type should be retried for a task"""
        retry_key = f"{task_id}:{error_type.__name__}"
        return self.retry_counts.get(retry_key, 0) == 0
    
    def clear_retry_counts(self, task_id: str):
        """Clear retry counts for a task"""
        keys_to_remove = [k for k in self.retry_counts.keys() if k.startswith(f"{task_id}:")]
        for key in keys_to_remove:
            del self.retry_counts[key]
    
    def create_user_error_report(self, task_id: str) -> Dict[str, Any]:
        """Create a user-friendly error report"""
        task_errors = [e for e in self.error_history if e.context.task_id == task_id]
        
        if not task_errors:
            return {"has_errors": False}
        
        # Group by category
        error_groups = {}
        for error in task_errors:
            category = error.category.value
            if category not in error_groups:
                error_groups[category] = []
            error_groups[category].append(error)
        
        # Create summary
        summary = {
            "has_errors": True,
            "total_errors": len(task_errors),
            "error_groups": {},
            "recommended_actions": set()
        }
        
        for category, errors in error_groups.items():
            group_info = {
                "count": len(errors),
                "severity": max(e.severity.value for e in errors),
                "messages": [e.user_message for e in errors[-3:]],  # Last 3 messages
                "suggested_actions": []
            }
            
            # Collect suggested actions
            for error in errors:
                group_info["suggested_actions"].extend(error.suggested_actions)
                summary["recommended_actions"].update(error.suggested_actions)
            
            summary["error_groups"][category] = group_info
        
        summary["recommended_actions"] = list(summary["recommended_actions"])
        
        return summary


# Global error handler instance
_global_error_handler = QAErrorHandler()


def get_error_handler() -> QAErrorHandler:
    """Get the global error handler"""
    return _global_error_handler


async def handle_qa_error(
    error: Exception,
    task_id: str,
    task_type: str,
    user_id: str,
    course_id: str,
    canvas_instance: str,
    stage: str = "unknown",
    **additional_data
) -> ErrorInfo:
    """
    Convenience function to handle QA errors.
    
    Args:
        error: Exception to handle
        task_id: Task identifier
        task_type: Type of QA task
        user_id: User identifier
        course_id: Canvas course ID
        canvas_instance: Canvas instance URL
        stage: Current processing stage
        **additional_data: Additional context data
        
    Returns:
        ErrorInfo with handling result
    """
    context = ErrorContext(
        task_id=task_id,
        task_type=task_type,
        user_id=user_id,
        course_id=course_id,
        canvas_instance=canvas_instance,
        timestamp=datetime.utcnow(),
        stage=stage,
        additional_data=additional_data
    )
    
    handler = get_error_handler()
    return await handler.handle_error(error, context, task_id)


def create_qa_task_error(
    message: str,
    task_id: str,
    category: ErrorCategory = ErrorCategory.SYSTEM,
    **details
) -> QATaskError:
    """
    Create a QA task error with additional context.
    
    Args:
        message: Error message
        task_id: Task identifier
        category: Error category
        **details: Additional error details
        
    Returns:
        QATaskError with context
    """
    error_details = {
        "category": category.value,
        "timestamp": datetime.utcnow().isoformat(),
        **details
    }
    
    return QATaskError(message, task_id, error_details) 