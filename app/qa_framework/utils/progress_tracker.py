"""
Progress Tracking Utilities

This module provides real-time progress tracking for QA automation tasks,
including WebSocket/SSE integration for Canvas LTI interface updates.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Callable
from weakref import WeakSet

from qa_framework.base.data_models import ProgressUpdate, ProgressStage, TaskStatus

logger = logging.getLogger(__name__)


class ProgressBroadcaster:
    """
    Centralized progress broadcasting for real-time updates.
    
    Manages WebSocket connections and provides progress updates to
    Canvas LTI interface and other clients.
    """
    
    def __init__(self):
        self._websocket_connections: WeakSet = WeakSet()
        self._task_subscribers: Dict[str, Set[Callable]] = {}
        self._progress_history: Dict[str, List[ProgressUpdate]] = {}
        self._max_history_size = 100
    
    def add_websocket_connection(self, websocket):
        """Add a WebSocket connection for progress updates"""
        self._websocket_connections.add(websocket)
        logger.debug(f"Added WebSocket connection: {id(websocket)}")
    
    def remove_websocket_connection(self, websocket):
        """Remove a WebSocket connection"""
        self._websocket_connections.discard(websocket)
        logger.debug(f"Removed WebSocket connection: {id(websocket)}")
    
    def subscribe_to_task(self, task_id: str, callback: Callable):
        """Subscribe to progress updates for a specific task"""
        if task_id not in self._task_subscribers:
            self._task_subscribers[task_id] = set()
        self._task_subscribers[task_id].add(callback)
    
    def unsubscribe_from_task(self, task_id: str, callback: Callable):
        """Unsubscribe from task progress updates"""
        if task_id in self._task_subscribers:
            self._task_subscribers[task_id].discard(callback)
            if not self._task_subscribers[task_id]:
                del self._task_subscribers[task_id]
    
    async def broadcast_progress(self, progress: ProgressUpdate):
        """
        Broadcast progress update to all connected clients.
        
        Args:
            progress: Progress update to broadcast
        """
        task_id = progress.task_id
        
        # Store in history
        if task_id not in self._progress_history:
            self._progress_history[task_id] = []
        
        self._progress_history[task_id].append(progress)
        
        # Limit history size
        if len(self._progress_history[task_id]) > self._max_history_size:
            self._progress_history[task_id] = self._progress_history[task_id][-self._max_history_size:]
        
        # Prepare message
        message = {
            'type': 'progress_update',
            'data': progress.dict()
        }
        
        # Broadcast to WebSocket connections
        await self._broadcast_to_websockets(message)
        
        # Notify task-specific subscribers
        await self._notify_task_subscribers(task_id, progress)
    
    async def _broadcast_to_websockets(self, message: Dict[str, Any]):
        """Broadcast message to all WebSocket connections"""
        if not self._websocket_connections:
            return
        
        message_str = json.dumps(message)
        
        # Create tasks for all connections
        tasks = []
        for websocket in list(self._websocket_connections):
            tasks.append(self._send_websocket_message(websocket, message_str))
        
        # Send to all connections concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_websocket_message(self, websocket, message: str):
        """Send message to a single WebSocket connection"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.warning(f"Failed to send WebSocket message: {e}")
            # Remove failed connection
            self._websocket_connections.discard(websocket)
    
    async def _notify_task_subscribers(self, task_id: str, progress: ProgressUpdate):
        """Notify task-specific subscribers"""
        if task_id not in self._task_subscribers:
            return
        
        # Notify all subscribers for this task
        for callback in list(self._task_subscribers[task_id]):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress)
                else:
                    callback(progress)
            except Exception as e:
                logger.error(f"Error in progress callback for task {task_id}: {e}")
                # Remove failed callback
                self._task_subscribers[task_id].discard(callback)
    
    def get_task_progress_history(self, task_id: str) -> List[ProgressUpdate]:
        """Get progress history for a task"""
        return self._progress_history.get(task_id, [])
    
    def get_latest_progress(self, task_id: str) -> Optional[ProgressUpdate]:
        """Get the latest progress update for a task"""
        history = self._progress_history.get(task_id, [])
        return history[-1] if history else None
    
    def clear_task_history(self, task_id: str):
        """Clear progress history for a task"""
        self._progress_history.pop(task_id, None)
        self._task_subscribers.pop(task_id, None)
    
    def get_active_tasks(self) -> List[str]:
        """Get list of tasks with active progress tracking"""
        return list(self._progress_history.keys())
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            'active_websockets': len(self._websocket_connections),
            'task_subscribers': {
                task_id: len(callbacks) 
                for task_id, callbacks in self._task_subscribers.items()
            },
            'tasks_with_history': len(self._progress_history)
        }


class TaskProgressTracker:
    """
    Enhanced progress tracker for individual QA tasks.
    
    Provides detailed progress reporting with time estimation,
    Canvas API statistics, and performance metrics.
    """
    
    def __init__(self, task_id: str, broadcaster: Optional[ProgressBroadcaster] = None):
        self.task_id = task_id
        self.broadcaster = broadcaster or get_progress_broadcaster()
        
        # Progress tracking
        self.start_time = time.time()
        self.stage_start_times: Dict[ProgressStage, float] = {}
        self.stage_durations: Dict[ProgressStage, float] = {}
        
        # Statistics
        self.api_calls_made = 0
        self.items_processed = 0
        self.errors_encountered = 0
        
        # Current state
        self.current_stage = ProgressStage.INITIALIZING
        self.current_progress = 0.0
        self.current_message = ""
        
        # Time estimation
        self.estimated_total_items = 0
        self.processing_rate_items_per_second = 0.0
    
    async def start_stage(self, stage: ProgressStage, message: str = ""):
        """Start a new progress stage"""
        now = time.time()
        
        # Record duration of previous stage
        if self.current_stage in self.stage_start_times:
            duration = now - self.stage_start_times[self.current_stage]
            self.stage_durations[self.current_stage] = duration
        
        # Start new stage
        self.current_stage = stage
        self.stage_start_times[stage] = now
        self.current_message = message
        
        await self._update_progress()
    
    async def update_progress(
        self, 
        current: int, 
        total: int, 
        message: str = "",
        **kwargs
    ):
        """Update progress within current stage"""
        self.current_progress = (current / total * 100) if total > 0 else 0
        self.current_message = message or self.current_message
        
        # Update statistics
        if 'api_calls' in kwargs:
            self.api_calls_made += kwargs['api_calls']
        
        if 'items_processed' in kwargs:
            self.items_processed = kwargs['items_processed']
            
        if 'errors' in kwargs:
            self.errors_encountered += kwargs['errors']
        
        # Calculate processing rate
        if self.items_processed > 0:
            elapsed = time.time() - self.start_time
            self.processing_rate_items_per_second = self.items_processed / elapsed
        
        # Update estimated total if provided
        if 'estimated_total' in kwargs:
            self.estimated_total_items = kwargs['estimated_total']
        
        await self._update_progress(current, total, **kwargs)
    
    async def _update_progress(self, current: int = 0, total: int = 100, **kwargs):
        """Send progress update to broadcaster"""
        now = datetime.utcnow()
        
        # Calculate time estimates
        estimated_completion_seconds = None
        if (self.processing_rate_items_per_second > 0 and 
            self.estimated_total_items > 0 and 
            self.items_processed < self.estimated_total_items):
            
            remaining_items = self.estimated_total_items - self.items_processed
            estimated_completion_seconds = remaining_items / self.processing_rate_items_per_second
        
        # Create progress update
        progress = ProgressUpdate(
            task_id=self.task_id,
            stage=self.current_stage,
            current=current,
            total=total,
            percentage=self.current_progress,
            message=self.current_message,
            items_processed=self.items_processed,
            items_remaining=max(0, self.estimated_total_items - self.items_processed),
            estimated_completion_seconds=estimated_completion_seconds,
            api_calls_made=self.api_calls_made,
            timestamp=now,
            **kwargs
        )
        
        # Broadcast update
        await self.broadcaster.broadcast_progress(progress)
        
        return progress
    
    async def complete_stage(self, stage: ProgressStage, message: str = ""):
        """Complete current stage"""
        await self.start_stage(stage, message)
        await self.update_progress(100, 100, message)
    
    async def report_error(self, error: Exception, context: Dict[str, Any] = None):
        """Report an error during processing"""
        self.errors_encountered += 1
        
        error_message = f"Error in {self.current_stage.value}: {str(error)}"
        await self.update_progress(
            current=0, 
            total=100, 
            message=error_message,
            error_details=context or {}
        )
    
    def get_stage_duration(self, stage: ProgressStage) -> Optional[float]:
        """Get duration of a completed stage in seconds"""
        return self.stage_durations.get(stage)
    
    def get_total_elapsed_time(self) -> float:
        """Get total elapsed time since start"""
        return time.time() - self.start_time
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        elapsed = self.get_total_elapsed_time()
        
        return {
            'total_elapsed_seconds': elapsed,
            'items_processed': self.items_processed,
            'processing_rate_per_second': self.processing_rate_items_per_second,
            'api_calls_made': self.api_calls_made,
            'errors_encountered': self.errors_encountered,
            'stage_durations': dict(self.stage_durations),
            'current_stage': self.current_stage.value,
            'current_progress_percentage': self.current_progress
        }


# Global progress broadcaster instance
_global_broadcaster = ProgressBroadcaster()


def get_progress_broadcaster() -> ProgressBroadcaster:
    """Get the global progress broadcaster"""
    return _global_broadcaster


def create_task_progress_tracker(task_id: str) -> TaskProgressTracker:
    """Create a new task progress tracker"""
    return TaskProgressTracker(task_id, get_progress_broadcaster())


async def send_progress_update(
    task_id: str,
    stage: ProgressStage,
    current: int,
    total: int,
    message: str = "",
    **kwargs
) -> ProgressUpdate:
    """
    Convenience function to send a progress update.
    
    Args:
        task_id: Task identifier
        stage: Current progress stage
        current: Current progress value
        total: Total progress value
        message: Progress message
        **kwargs: Additional progress data
        
    Returns:
        ProgressUpdate object
    """
    progress = ProgressUpdate(
        task_id=task_id,
        stage=stage,
        current=current,
        total=total,
        percentage=(current / total * 100) if total > 0 else 0,
        message=message,
        timestamp=datetime.utcnow(),
        **kwargs
    )
    
    broadcaster = get_progress_broadcaster()
    await broadcaster.broadcast_progress(progress)
    
    return progress


# Canvas-specific progress helpers
async def notify_canvas_progress(
    task_id: str,
    content_type: str,
    items_processed: int,
    total_items: int,
    message: str = ""
):
    """Notify Canvas-specific progress"""
    await send_progress_update(
        task_id=task_id,
        stage=ProgressStage.PROCESSING,
        current=items_processed,
        total=total_items,
        message=message,
        current_content_type=content_type,
        items_processed=items_processed
    )


async def notify_canvas_api_call(task_id: str, endpoint: str, response_time: float):
    """Notify Canvas API call completion"""
    await send_progress_update(
        task_id=task_id,
        stage=ProgressStage.FETCHING_CONTENT,
        current=0,
        total=100,
        message=f"API call to {endpoint} completed in {response_time:.2f}s",
        api_endpoint=endpoint,
        api_response_time=response_time
    ) 