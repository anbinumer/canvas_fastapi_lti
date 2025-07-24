"""
QA Framework Base Module

Core components for the QA automation framework including abstract base classes,
data models, and common interfaces.
"""

from .qa_task import (
    QATask,
    ProgressTracker,
    QATaskError,
    QATaskConfigError,
    QATaskExecutionError,
    QATaskCancelledError,
    QATaskTimeoutError
)

from .data_models import (
    # Core data models
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
    ConfigDict
)

from .task_registry import (
    QATaskRegistry,
    get_registry,
    register_qa_task,
    list_tasks,
    get_task_class,
    get_task_info,
    discover_tasks,
    reload_tasks
)

from .execution_engine import (
    QAExecutionEngine,
    RateLimiter,
    get_execution_engine
)

__all__ = [
    # Abstract base classes
    "QATask",
    "ProgressTracker",
    
    # Data models
    "TaskConfig",
    "FindReplaceConfig", 
    "ValidationResult",
    "QAFinding",
    "QAResult",
    "TaskInfo",
    "ProgressUpdate",
    "QAExecution",
    
    # Enums
    "TaskStatus",
    "ProgressStage", 
    "QATaskType",
    "CanvasContentType",
    
    # Type aliases
    "QATaskConfig",
    "ConfigDict",
    
    # Task registry
    "QATaskRegistry",
    "get_registry",
    "register_qa_task",
    "list_tasks",
    "get_task_class", 
    "get_task_info",
    "discover_tasks",
    "reload_tasks",
    
    # Execution engine
    "QAExecutionEngine",
    "RateLimiter",
    "get_execution_engine",
    
    # Exceptions
    "QATaskError",
    "QATaskConfigError",
    "QATaskExecutionError", 
    "QATaskCancelledError",
    "QATaskTimeoutError"
] 