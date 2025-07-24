"""
QA Automation Framework

This framework provides a modular, extensible architecture for QA automation tasks
in Canvas LMS environments. Learning Technologists can easily add new QA scripts
using AI coding assistance while maintaining consistent interfaces and error handling.

## Quick Start

```python
from app.qa_framework import QATask, register_qa_task, get_execution_engine

@register_qa_task(
    name="my_qa_task",
    description="Custom QA automation task",
    version="1.0.0",
    canvas_permissions=["read_course_content"]
)
class MyQATask(QATask):
    # Implement required methods here
    pass

# Execute a task
engine = get_execution_engine()
execution = await engine.execute_task(config, canvas_context, lti_context)
```

## Components

- **Base Classes**: Abstract QA task interface and data models
- **Task Registry**: Dynamic task discovery and registration
- **Execution Engine**: Asynchronous task processing with Canvas API rate limiting
- **Progress Tracking**: Real-time progress updates via WebSocket/SSE
- **Error Handling**: Comprehensive Canvas API error classification and recovery
"""

# Core framework components
from .base import (
    # Abstract base classes
    QATask,
    ProgressTracker,
    
    # Data models
    TaskConfig,
    FindReplaceConfig,
    ValidationResult,
    QAFinding,
    QAResult,
    TaskInfo,
    ProgressUpdate,
    QAExecution,
    
    # Enums
    TaskStatus,
    ProgressStage,
    QATaskType,
    CanvasContentType,
    
    # Type aliases
    QATaskConfig,
    ConfigDict,
    
    # Task registry
    QATaskRegistry,
    get_registry,
    register_qa_task,
    list_tasks,
    get_task_class,
    get_task_info,
    discover_tasks,
    reload_tasks,
    
    # Execution engine
    QAExecutionEngine,
    RateLimiter,
    get_execution_engine,
    
    # Exceptions
    QATaskError,
    QATaskConfigError,
    QATaskExecutionError,
    QATaskCancelledError,
    QATaskTimeoutError
)

# Utility components
from .utils import (
    # Progress tracking
    ProgressBroadcaster,
    TaskProgressTracker,
    get_progress_broadcaster,
    create_task_progress_tracker,
    send_progress_update,
    notify_canvas_progress,
    notify_canvas_api_call,
    
    # Error handling
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

__version__ = "2.1.0"
__author__ = "ACU Learning Technology Team"

__all__ = [
    # Core framework
    "QATask",
    "ProgressTracker",
    "TaskConfig",
    "FindReplaceConfig",
    "ValidationResult",
    "QAFinding",
    "QAResult",
    "TaskInfo",
    "ProgressUpdate",
    "QAExecution",
    "TaskStatus",
    "ProgressStage",
    "QATaskType",
    "CanvasContentType",
    "QATaskConfig",
    "ConfigDict",
    
    # Registry and execution
    "QATaskRegistry",
    "get_registry",
    "register_qa_task",
    "list_tasks",
    "get_task_class",
    "get_task_info",
    "discover_tasks",
    "reload_tasks",
    "QAExecutionEngine",
    "RateLimiter",
    "get_execution_engine",
    
    # Progress and error handling
    "ProgressBroadcaster",
    "TaskProgressTracker",
    "get_progress_broadcaster",
    "create_task_progress_tracker",
    "send_progress_update",
    "notify_canvas_progress",
    "notify_canvas_api_call",
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
    
    # Exceptions
    "QATaskError",
    "QATaskConfigError",
    "QATaskExecutionError",
    "QATaskCancelledError",
    "QATaskTimeoutError"
] 