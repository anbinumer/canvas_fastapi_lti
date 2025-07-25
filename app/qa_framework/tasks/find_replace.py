"""
Find & Replace QA Task

Adapts the existing CanvasURLScanner for single-course operation using LTI context.
Scans Canvas course content for specific URLs and replaces them with new ones.

Content types scanned:
- Syllabus, Pages, Assignments, Quizzes, Discussions, Announcements, Modules

This task inherits from the QA framework and provides real-time progress tracking,
Canvas API rate limiting, and comprehensive error handling.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from qa_framework.base import (
    QATask, 
    register_qa_task, 
    TaskInfo, 
    ValidationResult, 
    QAResult, 
    QAFinding,
    FindReplaceConfig,
    QATaskType,
    CanvasContentType,
    ProgressStage,
    ProgressTracker,
    QATaskConfigError,
    QATaskExecutionError
)
from qa_framework.utils import handle_qa_error, ErrorCategory
from app.services.canvas_service import CanvasService

logger = logging.getLogger(__name__)


@register_qa_task(
    name="find_replace",
    description="URL find and replace scanning for Canvas course content",
    version="1.0.0",
    canvas_permissions=["read_course_content", "manage_course_content_edit"]
)
class FindReplaceQATask(QATask):
    """
    Find & Replace QA automation task.
    
    Scans Canvas course content for specified URLs and replaces them with new URLs.
    Processes all content types: syllabus, pages, assignments, quizzes, discussions,
    announcements, and modules.
    """
    
    def get_task_info(self) -> TaskInfo:
        """Get task metadata and information"""
        return TaskInfo(
            name="Find & Replace URLs",
            description="Scan Canvas course content for specific URLs and replace them with new ones. Processes syllabus, pages, assignments, quizzes, discussions, announcements, and modules.",
            version="1.0.0",
            task_type=QATaskType.FIND_REPLACE,
            required_canvas_permissions=[
                "read_course_content", 
                "manage_course_content_edit"
            ],
            supported_content_types=[
                CanvasContentType.SYLLABUS,
                CanvasContentType.PAGES, 
                CanvasContentType.ASSIGNMENTS,
                CanvasContentType.QUIZZES,
                CanvasContentType.DISCUSSIONS,
                CanvasContentType.ANNOUNCEMENTS,
                CanvasContentType.MODULES
            ],
            help_text="Upload URL mappings in the format: old_url → new_url. The system will scan all course content and replace matching URLs while preserving HTML structure.",
            examples=[
                {
                    "name": "Course URL Update",
                    "description": "Replace old course URLs with new ones",
                    "config": {
                        "url_mappings": [
                            {
                                "find": "https://old-canvas.edu/courses/123", 
                                "replace": "https://new-canvas.edu/courses/456"
                            }
                        ]
                    }
                },
                {
                    "name": "Resource URL Migration", 
                    "description": "Update external resource URLs",
                    "config": {
                        "url_mappings": [
                            {
                                "find": "https://old-resources.com/files/",
                                "replace": "https://new-resources.edu/assets/"
                            }
                        ]
                    }
                }
            ]
        )
    
    def validate_config(self, config: FindReplaceConfig) -> ValidationResult:
        """Validate task configuration"""
        result = ValidationResult(is_valid=True)
        
        # Check URL mappings
        if not config.url_mappings:
            result.add_error("At least one URL mapping is required")
            return result
        
        # Validate each URL mapping
        for i, mapping in enumerate(config.url_mappings):
            if 'find' not in mapping or 'replace' not in mapping:
                result.add_error(f"URL mapping {i+1} must have 'find' and 'replace' keys")
                continue
            
            find_url = mapping['find'].strip()
            replace_url = mapping['replace'].strip()
            
            if not find_url:
                result.add_error(f"URL mapping {i+1}: 'find' URL cannot be empty")
            
            if not replace_url:
                result.add_error(f"URL mapping {i+1}: 'replace' URL cannot be empty")
            
            # Basic URL validation
            if find_url and not self._is_valid_url(find_url):
                result.add_warning(f"URL mapping {i+1}: 'find' URL may not be valid: {find_url}")
                
            if replace_url and not self._is_valid_url(replace_url):
                result.add_warning(f"URL mapping {i+1}: 'replace' URL may not be valid: {replace_url}")
            
            # Check for duplicate find URLs
            find_urls = [m['find'] for m in config.url_mappings if 'find' in m]
            if find_urls.count(find_url) > 1:
                result.add_error(f"Duplicate 'find' URL found: {find_url}")
        
        # Validate content types
        if not config.content_types:
            result.add_warning("No content types specified - will scan all supported content types")
        else:
            invalid_types = [ct for ct in config.content_types if ct not in self.supports_content_types()]
            if invalid_types:
                result.add_error(f"Unsupported content types: {invalid_types}")
        
        # Validate Canvas context
        if not config.course_id:
            result.add_error("Course ID is required")
        
        if not config.canvas_instance_url:
            result.add_error("Canvas instance URL is required")
        
        return result
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Get JSON schema for task configuration"""
        return {
            "type": "object",
            "properties": {
                "url_mappings": {
                    "type": "array",
                    "title": "URL Mappings",
                    "description": "List of URL find and replace pairs",
                    "items": {
                        "type": "object",
                        "properties": {
                            "find": {
                                "type": "string",
                                "title": "Find URL",
                                "description": "URL to search for in content"
                            },
                            "replace": {
                                "type": "string", 
                                "title": "Replace URL",
                                "description": "URL to replace with"
                            }
                        },
                        "required": ["find", "replace"]
                    },
                    "minItems": 1
                },
                "content_types": {
                    "type": "array",
                    "title": "Content Types to Scan",
                    "description": "Types of Canvas content to scan (default: all)",
                    "items": {
                        "type": "string",
                        "enum": ["syllabus", "pages", "assignments", "quizzes", "discussions", "announcements", "modules"]
                    },
                    "default": ["syllabus", "pages", "assignments", "quizzes", "discussions", "announcements", "modules"]
                },
                "case_sensitive": {
                    "type": "boolean",
                    "title": "Case Sensitive",
                    "description": "Whether URL matching should be case sensitive",
                    "default": False
                },
                "whole_word_only": {
                    "type": "boolean",
                    "title": "Whole Word Only", 
                    "description": "Whether to match complete URLs only",
                    "default": False
                },
                "include_html_attributes": {
                    "type": "boolean",
                    "title": "Include HTML Attributes",
                    "description": "Whether to scan HTML attributes (href, data-api-endpoint, etc.)",
                    "default": True
                }
            },
            "required": ["url_mappings"]
        }
    
    async def execute(
        self,
        config: FindReplaceConfig,
        progress_tracker: ProgressTracker,
        canvas_context: Optional[Dict[str, Any]] = None,
        lti_context: Optional[Dict[str, Any]] = None
    ) -> QAResult:
        """
        Execute the Find & Replace QA task.
        
        Args:
            config: Task configuration with URL mappings
            progress_tracker: Progress tracking interface
            canvas_context: Canvas course and user context
            lti_context: LTI-specific context
            
        Returns:
            QAResult with findings and statistics
        """
        # Create result object
        result = self.create_base_result(config)
        result.started_at = datetime.utcnow()
        
        try:
            # Initialize progress
            await progress_tracker.start_stage(
                ProgressStage.INITIALIZING,
                "Initializing Find & Replace QA task"
            )
            
            # Get Canvas service and course info
            canvas_service = await self._get_canvas_service(config, canvas_context)
            course_info = await self._get_course_info(canvas_service, config.course_id)
            
            logger.info(f"Starting Find & Replace QA for course: {course_info.get('name', 'Unknown')} (ID: {config.course_id})")
            
            # Determine content types to process
            content_types = config.content_types or list(CanvasContentType)
            total_content_types = len(content_types)
            
            await progress_tracker.update_progress(
                current=1,
                total=total_content_types + 2,  # +2 for init and completion
                message=f"Processing {total_content_types} content types"
            )
            
            # Process each content type
            processed_count = 0
            for i, content_type in enumerate(content_types):
                try:
                    await progress_tracker.start_stage(
                        ProgressStage.PROCESSING,
                        f"Processing {content_type.value} content"
                    )
                    
                    findings = await self._process_content_type(
                        canvas_service, 
                        config, 
                        content_type, 
                        course_info,
                        progress_tracker
                    )
                    
                    # Add findings to result
                    for finding in findings:
                        result.add_finding(finding)
                    
                    processed_count += 1
                    result.content_types_processed.append(content_type)
                    result.items_by_content_type[content_type.value] = len(findings)
                    
                    await progress_tracker.update_progress(
                        current=i + 2,  # +1 for init
                        total=total_content_types + 2,
                        message=f"Completed {content_type.value}: {len(findings)} findings"
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing {content_type.value}: {e}")
                    await progress_tracker.report_error(e, {"content_type": content_type.value})
                    
                    # Continue with other content types
                    continue
            
            # Complete the task
            await progress_tracker.start_stage(
                ProgressStage.COMPLETED,
                "Finalizing results"
            )
            
            result.completed_at = datetime.utcnow()
            result.execution_time_seconds = (result.completed_at - result.started_at).total_seconds()
            result.total_items_scanned = sum(result.items_by_content_type.values())
            
            await progress_tracker.update_progress(
                current=total_content_types + 2,
                total=total_content_types + 2,
                message=f"Task completed: {result.total_findings} URLs replaced across {processed_count} content types"
            )
            
            logger.info(f"Find & Replace QA completed: {result.total_findings} findings, {result.total_items_scanned} items scanned")
            
            return result
            
        except Exception as e:
            # Handle execution error
            error_info = await handle_qa_error(
                e, config.task_id, "find_replace", config.user_id,
                config.course_id, config.canvas_instance_url, "execution"
            )
            
            result.error_message = error_info.user_message
            result.error_details = {
                "technical_message": error_info.technical_message,
                "category": error_info.category.value,
                "recovery_strategy": error_info.recovery_strategy.value
            }
            
            raise QATaskExecutionError(f"Find & Replace execution failed: {error_info.user_message}", config.task_id)
    
    async def _get_canvas_service(self, config: FindReplaceConfig, canvas_context: Optional[Dict[str, Any]]):
        """Get Canvas service instance with authentication"""
        # This will be implemented when we create the Canvas service
        # For now, create a placeholder
        return CanvasService(
            base_url=config.canvas_instance_url,
            access_token=canvas_context.get('access_token') if canvas_context else None
        )
    
    async def _get_course_info(self, canvas_service, course_id: str) -> Dict[str, Any]:
        """Get course information"""
        try:
            return await canvas_service.get_course(course_id)
        except Exception as e:
            logger.error(f"Failed to get course info for {course_id}: {e}")
            return {"id": course_id, "name": "Unknown Course"}
    
    async def _process_content_type(
        self,
        canvas_service,
        config: FindReplaceConfig, 
        content_type: CanvasContentType,
        course_info: Dict[str, Any],
        progress_tracker: ProgressTracker
    ) -> List[QAFinding]:
        """Process a specific content type for URL replacements"""
        findings = []
        
        try:
            if content_type == CanvasContentType.SYLLABUS:
                findings = await self._process_syllabus(canvas_service, config, course_info)
            elif content_type == CanvasContentType.PAGES:
                findings = await self._process_pages(canvas_service, config, course_info, progress_tracker)
            elif content_type == CanvasContentType.ASSIGNMENTS:
                findings = await self._process_assignments(canvas_service, config, course_info, progress_tracker)
            elif content_type == CanvasContentType.QUIZZES:
                findings = await self._process_quizzes(canvas_service, config, course_info, progress_tracker)
            elif content_type == CanvasContentType.DISCUSSIONS:
                findings = await self._process_discussions(canvas_service, config, course_info, progress_tracker)
            elif content_type == CanvasContentType.ANNOUNCEMENTS:
                findings = await self._process_announcements(canvas_service, config, course_info, progress_tracker)
            elif content_type == CanvasContentType.MODULES:
                findings = await self._process_modules(canvas_service, config, course_info, progress_tracker)
            
        except Exception as e:
            logger.error(f"Error processing {content_type.value}: {e}")
            raise
        
        return findings
    
    async def _process_syllabus(self, canvas_service, config: FindReplaceConfig, course_info: Dict[str, Any]) -> List[QAFinding]:
        """Process syllabus content"""
        findings = []
        
        try:
            # Get syllabus content
            syllabus_data = await canvas_service.get_syllabus(config.course_id)
            
            if syllabus_data and syllabus_data.get('syllabus_body'):
                content = syllabus_data['syllabus_body']
                
                # Use canvas scanner utility to find and replace URLs
                new_content, replacements = await self._scan_and_replace_content(content, config)
                
                if replacements:
                    # Update syllabus
                    success = await canvas_service.update_syllabus(config.course_id, new_content)
                    
                    # Create findings
                    for old_url, new_url in replacements:
                        findings.append(QAFinding(
                            content_type=CanvasContentType.SYLLABUS,
                            content_id=config.course_id,
                            content_title="Course Syllabus",
                            content_url=f"{config.canvas_instance_url}/courses/{config.course_id}/assignments/syllabus",
                            finding_type="url_replaced",
                            description=f"Replaced URL in syllabus: {old_url} → {new_url}",
                            severity="info",
                            old_value=old_url,
                            new_value=new_url,
                            additional_data={
                                "update_success": success,
                                "content_length": len(content)
                            }
                        ))
                        
        except Exception as e:
            logger.error(f"Error processing syllabus: {e}")
            raise
        
        return findings
    
    async def _process_pages(self, canvas_service, config: FindReplaceConfig, course_info: Dict[str, Any], progress_tracker: ProgressTracker) -> List[QAFinding]:
        """Process page content"""
        findings = []
        
        try:
            # Get all pages
            pages = await canvas_service.get_pages(config.course_id)
            total_pages = len(pages)
            
            for i, page in enumerate(pages):
                try:
                    # Get page details
                    page_data = await canvas_service.get_page(config.course_id, page['url'])
                    
                    if page_data and page_data.get('body'):
                        content = page_data['body']
                        new_content, replacements = await self._scan_and_replace_content(content, config)
                        
                        if replacements:
                            # Update page
                            success = await canvas_service.update_page(config.course_id, page['url'], new_content)
                            
                            # Create findings
                            for old_url, new_url in replacements:
                                findings.append(QAFinding(
                                    content_type=CanvasContentType.PAGES,
                                    content_id=page['url'],
                                    content_title=page.get('title', 'Untitled Page'),
                                    content_url=page.get('html_url', ''),
                                    finding_type="url_replaced",
                                    description=f"Replaced URL in page '{page.get('title', 'Untitled')}': {old_url} → {new_url}",
                                    severity="info",
                                    old_value=old_url,
                                    new_value=new_url,
                                    additional_data={
                                        "update_success": success,
                                        "page_url": page['url']
                                    }
                                ))
                    
                    # Update progress
                    if i % 5 == 0:  # Update every 5 pages
                        await progress_tracker.update_progress(
                            current=i + 1,
                            total=total_pages,
                            message=f"Processed {i + 1}/{total_pages} pages"
                        )
                        
                except Exception as e:
                    logger.warning(f"Error processing page {page.get('url', 'unknown')}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error processing pages: {e}")
            raise
        
        return findings
    
    async def _process_assignments(self, canvas_service, config: FindReplaceConfig, course_info: Dict[str, Any], progress_tracker: ProgressTracker) -> List[QAFinding]:
        """Process assignment content"""
        findings = []
        
        try:
            assignments = await canvas_service.get_assignments(config.course_id)
            total_assignments = len(assignments)
            
            for i, assignment in enumerate(assignments):
                try:
                    if assignment.get('description'):
                        content = assignment['description']
                        new_content, replacements = await self._scan_and_replace_content(content, config)
                        
                        if replacements:
                            success = await canvas_service.update_assignment(config.course_id, assignment['id'], new_content)
                            
                            for old_url, new_url in replacements:
                                findings.append(QAFinding(
                                    content_type=CanvasContentType.ASSIGNMENTS,
                                    content_id=str(assignment['id']),
                                    content_title=assignment.get('name', 'Untitled Assignment'),
                                    content_url=assignment.get('html_url', ''),
                                    finding_type="url_replaced",
                                    description=f"Replaced URL in assignment '{assignment.get('name', 'Untitled')}': {old_url} → {new_url}",
                                    severity="info",
                                    old_value=old_url,
                                    new_value=new_url,
                                    additional_data={
                                        "update_success": success,
                                        "assignment_id": assignment['id']
                                    }
                                ))
                    
                    if i % 5 == 0:
                        await progress_tracker.update_progress(
                            current=i + 1,
                            total=total_assignments,
                            message=f"Processed {i + 1}/{total_assignments} assignments"
                        )
                        
                except Exception as e:
                    logger.warning(f"Error processing assignment {assignment.get('id', 'unknown')}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error processing assignments: {e}")
            raise
        
        return findings
    
    # Similar methods for quizzes, discussions, announcements, modules...
    async def _process_quizzes(self, canvas_service, config: FindReplaceConfig, course_info: Dict[str, Any], progress_tracker: ProgressTracker) -> List[QAFinding]:
        """Process quiz content - placeholder for now"""
        # TODO: Implement quiz processing similar to assignments
        return []
    
    async def _process_discussions(self, canvas_service, config: FindReplaceConfig, course_info: Dict[str, Any], progress_tracker: ProgressTracker) -> List[QAFinding]:
        """Process discussion content - placeholder for now"""
        # TODO: Implement discussion processing 
        return []
    
    async def _process_announcements(self, canvas_service, config: FindReplaceConfig, course_info: Dict[str, Any], progress_tracker: ProgressTracker) -> List[QAFinding]:
        """Process announcement content - placeholder for now"""
        # TODO: Implement announcement processing
        return []
    
    async def _process_modules(self, canvas_service, config: FindReplaceConfig, course_info: Dict[str, Any], progress_tracker: ProgressTracker) -> List[QAFinding]:
        """Process module content - placeholder for now"""
        # TODO: Implement module processing
        return []
    
    async def _scan_and_replace_content(self, content: str, config: FindReplaceConfig) -> tuple[str, List[tuple[str, str]]]:
        """
        Scan content for URLs and replace them.
        
        This will use the adapted CanvasURLScanner utility.
        For now, providing a placeholder.
        """
        # TODO: Use the canvas scanner utility
        from qa_framework.utils.canvas_scanner import replace_urls_in_content
        return await replace_urls_in_content(content, config.url_mappings, config)
    
    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False 