"""
QA Task Registry System

This module provides dynamic discovery and registration of QA automation tasks,
enabling Learning Technologists to add new QA scripts using AI coding assistance.
"""

import importlib
import inspect
import logging
import os
import pkgutil
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Set

from .qa_task import QATask, QATaskError
from .data_models import TaskInfo, QATaskType, ValidationResult

logger = logging.getLogger(__name__)


class QATaskRegistry:
    """
    Registry for QA automation tasks with dynamic discovery and validation.
    
    Supports hot-reload during development for Learning Technologist workflow.
    """
    
    def __init__(self):
        self._tasks: Dict[str, Type[QATask]] = {}
        self._task_info: Dict[str, TaskInfo] = {}
        self._task_metadata: Dict[str, Dict[str, Any]] = {}
        self._registered_modules: Set[str] = set()
    
    def register_task(
        self, 
        task_class: Type[QATask],
        name: Optional[str] = None,
        description: Optional[str] = None,
        version: str = "1.0.0",
        canvas_permissions: Optional[List[str]] = None,
        **metadata
    ) -> bool:
        """
        Register a QA task class.
        
        Args:
            task_class: QA task class inheriting from QATask
            name: Task name (defaults to class name)
            description: Task description
            version: Task version
            canvas_permissions: Required Canvas permissions
            **metadata: Additional task metadata
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Validate task class
            if not issubclass(task_class, QATask):
                logger.error(f"Task class {task_class.__name__} must inherit from QATask")
                return False
            
            # Get task info from the class
            try:
                # Create a temporary instance to get task info
                temp_instance = task_class()
                task_info = temp_instance.get_task_info()
            except Exception as e:
                logger.error(f"Failed to get task info for {task_class.__name__}: {e}")
                return False
            
            # Use provided name or default to task info name
            task_name = name or task_info.name
            
            # Check for conflicts
            if task_name in self._tasks:
                existing_info = self._task_info[task_name]
                logger.warning(f"Task '{task_name}' already registered (v{existing_info.version})")
                
                # Allow version updates
                if version > existing_info.version:
                    logger.info(f"Updating task '{task_name}' from v{existing_info.version} to v{version}")
                else:
                    logger.error(f"Task '{task_name}' v{version} conflicts with existing v{existing_info.version}")
                    return False
            
            # Register the task
            self._tasks[task_name] = task_class
            self._task_info[task_name] = task_info
            self._task_metadata[task_name] = {
                'name': task_name,
                'description': description or task_info.description,
                'version': version,
                'canvas_permissions': canvas_permissions or task_info.required_canvas_permissions,
                'class_name': task_class.__name__,
                'module': task_class.__module__,
                **metadata
            }
            
            logger.info(f"Successfully registered QA task: {task_name} v{version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register task {task_class.__name__}: {e}")
            return False
    
    def unregister_task(self, name: str) -> bool:
        """
        Unregister a QA task.
        
        Args:
            name: Task name to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        if name not in self._tasks:
            logger.warning(f"Task '{name}' not found for unregistration")
            return False
        
        del self._tasks[name]
        del self._task_info[name]
        del self._task_metadata[name]
        
        logger.info(f"Unregistered QA task: {name}")
        return True
    
    def get_task_class(self, name: str) -> Optional[Type[QATask]]:
        """Get registered task class by name"""
        return self._tasks.get(name)
    
    def get_task_info(self, name: str) -> Optional[TaskInfo]:
        """Get task information by name"""
        return self._task_info.get(name)
    
    def get_task_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """Get task metadata by name"""
        return self._task_metadata.get(name)
    
    def list_tasks(self) -> List[str]:
        """Get list of all registered task names"""
        return list(self._tasks.keys())
    
    def list_task_info(self) -> List[TaskInfo]:
        """Get list of all registered task info"""
        return list(self._task_info.values())
    
    def list_task_metadata(self) -> List[Dict[str, Any]]:
        """Get list of all task metadata"""
        return list(self._task_metadata.values())
    
    def get_tasks_by_type(self, task_type: QATaskType) -> List[str]:
        """Get tasks filtered by type"""
        return [
            name for name, info in self._task_info.items()
            if info.task_type == task_type
        ]
    
    def validate_task(self, name: str) -> ValidationResult:
        """
        Validate a registered task.
        
        Args:
            name: Task name to validate
            
        Returns:
            ValidationResult with any issues found
        """
        result = ValidationResult(is_valid=True)
        
        if name not in self._tasks:
            result.add_error(f"Task '{name}' not found")
            return result
        
        task_class = self._tasks[name]
        task_info = self._task_info[name]
        
        # Validate task class structure
        required_methods = ['execute', 'get_task_info', 'validate_config', 'get_config_schema']
        for method_name in required_methods:
            if not hasattr(task_class, method_name):
                result.add_error(f"Task class missing required method: {method_name}")
        
        # Validate task info completeness
        if not task_info.name:
            result.add_error("Task info missing name")
        if not task_info.description:
            result.add_error("Task info missing description")
        if not task_info.version:
            result.add_error("Task info missing version")
        
        # Check for Canvas permissions
        if not task_info.required_canvas_permissions:
            result.add_warning("No Canvas permissions specified - task may have limited access")
        
        return result
    
    def discover_tasks(self, package_path: str = "app.qa_framework.tasks") -> int:
        """
        Discover and load QA tasks from specified package.
        
        Args:
            package_path: Python package path to scan for tasks
            
        Returns:
            Number of tasks discovered and registered
        """
        discovered_count = 0
        
        try:
            # Import the tasks package
            try:
                package = importlib.import_module(package_path)
            except ImportError:
                logger.warning(f"Tasks package '{package_path}' not found - skipping discovery")
                return 0
            
            # Get package directory
            if hasattr(package, '__path__'):
                package_dir = package.__path__[0]
            else:
                logger.warning(f"Package '{package_path}' has no __path__ - skipping discovery")
                return 0
            
            # Discover modules in the package
            for finder, module_name, ispkg in pkgutil.iter_modules([package_dir]):
                if ispkg:
                    # Recursively discover subpackages
                    sub_package_path = f"{package_path}.{module_name}"
                    discovered_count += self.discover_tasks(sub_package_path)
                    continue
                
                full_module_name = f"{package_path}.{module_name}"
                
                # Skip already loaded modules unless in development mode
                if full_module_name in self._registered_modules:
                    continue
                
                try:
                    # Import the module
                    module = importlib.import_module(full_module_name)
                    self._registered_modules.add(full_module_name)
                    
                    # Find QA task classes in the module
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (issubclass(obj, QATask) and 
                            obj != QATask and 
                            obj.__module__ == full_module_name):
                            
                            # Check if class has registration decorator metadata
                            if hasattr(obj, '_qa_task_metadata'):
                                metadata = obj._qa_task_metadata
                                if self.register_task(obj, **metadata):
                                    discovered_count += 1
                            else:
                                # Try to register with default metadata
                                if self.register_task(obj):
                                    discovered_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to load module '{full_module_name}': {e}")
                    continue
            
            logger.info(f"Task discovery completed: {discovered_count} tasks found in '{package_path}'")
            
        except Exception as e:
            logger.error(f"Task discovery failed for '{package_path}': {e}")
        
        return discovered_count
    
    def reload_tasks(self, package_path: str = "app.qa_framework.tasks") -> int:
        """
        Reload tasks for development hot-reload.
        
        Args:
            package_path: Python package path to reload
            
        Returns:
            Number of tasks reloaded
        """
        # Clear registered modules to force reload
        modules_to_reload = [m for m in self._registered_modules if m.startswith(package_path)]
        for module_name in modules_to_reload:
            self._registered_modules.discard(module_name)
            
            # Reload the module if it's already imported
            if module_name in importlib.sys.modules:
                try:
                    importlib.reload(importlib.sys.modules[module_name])
                except Exception as e:
                    logger.error(f"Failed to reload module '{module_name}': {e}")
        
        # Clear existing tasks from this package
        tasks_to_remove = []
        for task_name, metadata in self._task_metadata.items():
            if metadata.get('module', '').startswith(package_path):
                tasks_to_remove.append(task_name)
        
        for task_name in tasks_to_remove:
            self.unregister_task(task_name)
        
        # Re-discover tasks
        return self.discover_tasks(package_path)
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        stats = {
            'total_tasks': len(self._tasks),
            'registered_modules': len(self._registered_modules),
            'tasks_by_type': {},
            'tasks_by_version': {},
        }
        
        # Count by type
        for info in self._task_info.values():
            task_type = info.task_type.value
            stats['tasks_by_type'][task_type] = stats['tasks_by_type'].get(task_type, 0) + 1
        
        # Count by version
        for metadata in self._task_metadata.values():
            version = metadata.get('version', 'unknown')
            stats['tasks_by_version'][version] = stats['tasks_by_version'].get(version, 0) + 1
        
        return stats


# Global registry instance
_global_registry = QATaskRegistry()


def get_registry() -> QATaskRegistry:
    """Get the global QA task registry"""
    return _global_registry


def register_qa_task(
    name: Optional[str] = None,
    description: Optional[str] = None,
    version: str = "1.0.0",
    canvas_permissions: Optional[List[str]] = None,
    **metadata
):
    """
    Decorator for registering QA tasks.
    
    Usage:
        @register_qa_task(
            name="find_replace",
            description="URL find and replace scanning",
            version="1.0.0",
            canvas_permissions=["read_course_content"]
        )
        class FindReplaceQATask(QATask):
            pass
    """
    def decorator(task_class: Type[QATask]):
        # Store metadata on the class for discovery
        task_class._qa_task_metadata = {
            'name': name,
            'description': description,
            'version': version,
            'canvas_permissions': canvas_permissions,
            **metadata
        }
        
        # Register immediately if registry is available
        try:
            registry = get_registry()
            registry.register_task(task_class, name, description, version, canvas_permissions, **metadata)
        except Exception as e:
            logger.warning(f"Failed to register task {task_class.__name__} via decorator: {e}")
        
        return task_class
    
    return decorator


# Convenience functions
def list_tasks() -> List[str]:
    """List all registered task names"""
    return get_registry().list_tasks()


def get_task_class(name: str) -> Optional[Type[QATask]]:
    """Get task class by name"""
    return get_registry().get_task_class(name)


def get_task_info(name: str) -> Optional[TaskInfo]:
    """Get task info by name"""
    return get_registry().get_task_info(name)


def discover_tasks() -> int:
    """Discover all available QA tasks"""
    return get_registry().discover_tasks()


def reload_tasks() -> int:
    """Reload tasks for development"""
    return get_registry().reload_tasks() 