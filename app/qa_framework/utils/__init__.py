"""
QA Framework Utils Module

This module contains utility classes and functions for the QA automation framework,
including progress tracking, error handling, and Canvas integration utilities.
"""

from .progress_tracker import (
    ProgressBroadcaster,
    TaskProgressTracker,
    get_progress_broadcaster,
    create_task_progress_tracker,
    send_progress_update,
    notify_canvas_progress,
    notify_canvas_api_call
)

from .error_handler import (
    ErrorSeverity,
    ErrorCategory,
    RecoveryStrategy,
    ErrorContext,
    ErrorInfo,
    CanvasAPIErrorClassifier,
    QAErrorHandler,
    get_error_handler,
    handle_qa_error,
    create_qa_task_error
)

from .canvas_scanner import (
    replace_urls_in_content,
    extract_urls_from_content,
    validate_html_content,
    sanitize_content_for_canvas
)

__all__ = [
    # Progress tracking
    "ProgressBroadcaster",
    "TaskProgressTracker", 
    "get_progress_broadcaster",
    "create_task_progress_tracker",
    "send_progress_update",
    "notify_canvas_progress",
    "notify_canvas_api_call",
    
    # Error handling
    "ErrorSeverity",
    "ErrorCategory",
    "RecoveryStrategy",
    "ErrorContext",
    "ErrorInfo",
    "CanvasAPIErrorClassifier",
    "QAErrorHandler",
    "get_error_handler",
    "handle_qa_error",
    "create_qa_task_error",
    
    # Canvas scanner utilities
    "replace_urls_in_content",
    "extract_urls_from_content", 
    "validate_html_content",
    "sanitize_content_for_canvas"
] 