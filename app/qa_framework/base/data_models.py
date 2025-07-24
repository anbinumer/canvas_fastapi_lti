"""
QA Framework Data Models

This module defines the core data structures for the QA automation framework,
providing standardized interfaces for task configuration, results, and metadata.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field, validator


class TaskStatus(str, Enum):
    """Task execution status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProgressStage(str, Enum):
    """Progress tracking stage enumeration"""
    INITIALIZING = "initializing"
    VALIDATING = "validating"
    FETCHING_CONTENT = "fetching_content"
    PROCESSING = "processing"
    GENERATING_RESULTS = "generating_results"
    COMPLETED = "completed"


class QATaskType(str, Enum):
    """QA automation task types"""
    FIND_REPLACE = "find_replace"
    LINK_VALIDATION = "link_validation"
    ACCESSIBILITY_AUDIT = "accessibility_audit"
    # Future task types can be added here


class CanvasContentType(str, Enum):
    """Canvas content types for QA scanning"""
    SYLLABUS = "syllabus"
    PAGES = "pages"
    ASSIGNMENTS = "assignments"
    QUIZZES = "quizzes"
    DISCUSSIONS = "discussions"
    ANNOUNCEMENTS = "announcements"
    MODULES = "modules"
    FILES = "files"


class TaskConfig(BaseModel):
    """Base configuration for QA tasks"""
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    task_type: QATaskType
    course_id: str
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Task-specific configuration (to be extended by specific task configs)
    config_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Canvas context
    canvas_instance_url: str
    canvas_access_token: Optional[str] = None
    
    # Processing options
    content_types: List[CanvasContentType] = Field(default_factory=lambda: list(CanvasContentType))
    batch_size: int = Field(default=10, ge=1, le=50)
    timeout_seconds: int = Field(default=300, ge=30, le=1800)  # 5 minutes to 30 minutes
    
    class Config:
        use_enum_values = True


class FindReplaceConfig(TaskConfig):
    """Configuration for Find & Replace QA task"""
    task_type: QATaskType = QATaskType.FIND_REPLACE
    
    # URL mappings for find and replace
    url_mappings: List[Dict[str, str]] = Field(
        ..., 
        description="List of {'find': 'old_url', 'replace': 'new_url'} mappings"
    )
    
    # Processing options
    case_sensitive: bool = Field(default=False)
    whole_word_only: bool = Field(default=False)
    include_html_attributes: bool = Field(default=True)
    
    @validator('url_mappings')
    def validate_url_mappings(cls, v):
        if not v:
            raise ValueError("At least one URL mapping is required")
        
        for mapping in v:
            if not isinstance(mapping, dict):
                raise ValueError("Each URL mapping must be a dictionary")
            if 'find' not in mapping or 'replace' not in mapping:
                raise ValueError("Each URL mapping must have 'find' and 'replace' keys")
            if not mapping['find'].strip():
                raise ValueError("Find URL cannot be empty")
        
        return v


class ValidationResult(BaseModel):
    """Result of task configuration validation"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    def add_error(self, message: str):
        """Add a validation error"""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add a validation warning"""
        self.warnings.append(message)


class QAFinding(BaseModel):
    """Individual QA finding/result"""
    content_type: CanvasContentType
    content_id: str
    content_title: str
    content_url: Optional[str] = None
    
    # Finding details
    finding_type: str  # e.g., "url_found", "url_replaced", "broken_link"
    description: str
    severity: str = Field(default="info")  # info, warning, error
    
    # Location details
    location: Dict[str, Any] = Field(default_factory=dict)  # Line number, element, etc.
    
    # Before/after for replacements
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    additional_data: Dict[str, Any] = Field(default_factory=dict)


class QAResult(BaseModel):
    """Complete QA task result"""
    task_id: str
    task_type: QATaskType
    status: TaskStatus
    
    # Execution metadata
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_time_seconds: Optional[float] = None
    
    # Results summary
    total_items_scanned: int = 0
    total_findings: int = 0
    findings_by_type: Dict[str, int] = Field(default_factory=dict)
    
    # Detailed findings
    findings: List[QAFinding] = Field(default_factory=list)
    
    # Processing statistics
    content_types_processed: List[CanvasContentType] = Field(default_factory=list)
    items_by_content_type: Dict[str, int] = Field(default_factory=dict)
    
    # Error information (if failed)
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = Field(default_factory=dict)
    
    # Canvas API statistics
    api_calls_made: int = 0
    api_rate_limit_hits: int = 0
    
    class Config:
        use_enum_values = True
    
    def add_finding(self, finding: QAFinding):
        """Add a finding to the results"""
        self.findings.append(finding)
        self.total_findings += 1
        
        # Update findings by type counter
        if finding.finding_type not in self.findings_by_type:
            self.findings_by_type[finding.finding_type] = 0
        self.findings_by_type[finding.finding_type] += 1
    
    def get_findings_by_severity(self, severity: str) -> List[QAFinding]:
        """Get findings filtered by severity"""
        return [f for f in self.findings if f.severity == severity]
    
    def get_findings_by_content_type(self, content_type: CanvasContentType) -> List[QAFinding]:
        """Get findings filtered by content type"""
        return [f for f in self.findings if f.content_type == content_type]


class TaskInfo(BaseModel):
    """QA task metadata and information"""
    name: str
    description: str
    version: str
    task_type: QATaskType
    
    # Requirements
    required_canvas_permissions: List[str] = Field(default_factory=list)
    supported_content_types: List[CanvasContentType] = Field(default_factory=list)
    
    # Configuration schema
    config_schema: Dict[str, Any] = Field(default_factory=dict)
    
    # Documentation
    help_text: Optional[str] = None
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class ProgressUpdate(BaseModel):
    """Progress tracking update"""
    task_id: str
    stage: ProgressStage
    current: int = 0
    total: int = 0
    percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    message: str = ""
    
    # Detailed progress
    current_content_type: Optional[CanvasContentType] = None
    items_processed: int = 0
    items_remaining: int = 0
    
    # Time estimates
    estimated_completion_seconds: Optional[float] = None
    
    # Canvas API status
    api_calls_made: int = 0
    rate_limit_remaining: Optional[int] = None
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class QAExecution(BaseModel):
    """QA task execution tracking"""
    task_id: str
    config: TaskConfig
    status: TaskStatus = TaskStatus.PENDING
    
    # Execution tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Progress tracking
    current_stage: ProgressStage = ProgressStage.INITIALIZING
    progress_updates: List[ProgressUpdate] = Field(default_factory=list)
    
    # Results
    result: Optional[QAResult] = None
    
    # Canvas context
    canvas_context: Dict[str, Any] = Field(default_factory=dict)
    lti_context: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True
    
    def update_progress(self, stage: ProgressStage, current: int, total: int, message: str = ""):
        """Update task progress"""
        self.current_stage = stage
        
        progress = ProgressUpdate(
            task_id=self.task_id,
            stage=stage,
            current=current,
            total=total,
            percentage=round((current / total * 100) if total > 0 else 0.0, 2),
            message=message
        )
        
        self.progress_updates.append(progress)
        return progress
    
    def start_execution(self):
        """Mark task as started"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()
    
    def complete_execution(self, result: QAResult):
        """Mark task as completed"""
        self.status = result.status
        self.completed_at = datetime.utcnow()
        self.result = result
    
    def fail_execution(self, error_message: str, error_details: Optional[Dict[str, Any]] = None):
        """Mark task as failed"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        
        # Create error result
        self.result = QAResult(
            task_id=self.task_id,
            task_type=self.config.task_type,
            status=TaskStatus.FAILED,
            started_at=self.started_at or datetime.utcnow(),
            error_message=error_message,
            error_details=error_details or {}
        )


# Type aliases for convenience
QATaskConfig = Union[TaskConfig, FindReplaceConfig]
ConfigDict = Dict[str, Any] 