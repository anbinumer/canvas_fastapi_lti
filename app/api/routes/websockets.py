"""
WebSocket API Routes

Provides WebSocket endpoints for real-time QA automation progress updates
and live communication between the frontend and QA execution engine.
"""

import json
import logging
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.websockets import WebSocketState

# from core.dependencies import get_canvas_context  # TODO: Implement dependencies
from qa_framework.utils import get_progress_broadcaster
from app.services.qa_orchestrator import get_qa_orchestrator
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

# Create router for WebSocket endpoints
router = APIRouter(prefix="/ws", tags=["WebSocket"])

# Connection manager for WebSocket clients
class QAWebSocketManager:
    """
    Manages WebSocket connections for QA automation progress updates.
    
    Handles client connections, task subscriptions, and real-time
    progress broadcasting to subscribed clients.
    """
    
    def __init__(self):
        """Initialize WebSocket manager"""
        # Active WebSocket connections
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Task subscriptions - maps task_id to set of connection_ids
        self.task_subscriptions: Dict[str, Set[str]] = {}
        
        # User subscriptions - maps user_id to set of connection_ids  
        self.user_subscriptions: Dict[str, Set[str]] = {}
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: str, course_id: str = None):
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            connection_id: Unique connection identifier
            user_id: User ID from LTI context
            course_id: Optional course ID
        """
        await websocket.accept()
        
        # Store connection
        self.active_connections[connection_id] = websocket
        
        # Store metadata
        self.connection_metadata[connection_id] = {
            'user_id': user_id,
            'course_id': course_id,
            'connected_at': None  # Will be set by datetime if needed
        }
        
        # Add to user subscriptions
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = set()
        self.user_subscriptions[user_id].add(connection_id)
        
        logger.info(f"WebSocket connected: {connection_id} for user {user_id}")
    
    def disconnect(self, connection_id: str):
        """
        Remove a WebSocket connection.
        
        Args:
            connection_id: Connection identifier to remove
        """
        if connection_id in self.active_connections:
            # Remove from active connections
            del self.active_connections[connection_id]
            
            # Get metadata before removing
            metadata = self.connection_metadata.get(connection_id, {})
            user_id = metadata.get('user_id')
            
            # Remove from task subscriptions
            for task_id, connections in self.task_subscriptions.items():
                connections.discard(connection_id)
            
            # Remove empty task subscriptions
            self.task_subscriptions = {
                task_id: connections 
                for task_id, connections in self.task_subscriptions.items() 
                if connections
            }
            
            # Remove from user subscriptions
            if user_id and user_id in self.user_subscriptions:
                self.user_subscriptions[user_id].discard(connection_id)
                if not self.user_subscriptions[user_id]:
                    del self.user_subscriptions[user_id]
            
            # Remove metadata
            if connection_id in self.connection_metadata:
                del self.connection_metadata[connection_id]
            
            logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def subscribe_to_task(self, connection_id: str, task_id: str):
        """
        Subscribe a connection to task progress updates.
        
        Args:
            connection_id: Connection identifier
            task_id: Task to subscribe to
        """
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = set()
        
        self.task_subscriptions[task_id].add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to task {task_id}")
    
    async def unsubscribe_from_task(self, connection_id: str, task_id: str):
        """
        Unsubscribe a connection from task progress updates.
        
        Args:
            connection_id: Connection identifier  
            task_id: Task to unsubscribe from
        """
        if task_id in self.task_subscriptions:
            self.task_subscriptions[task_id].discard(connection_id)
            
            # Remove empty subscriptions
            if not self.task_subscriptions[task_id]:
                del self.task_subscriptions[task_id]
            
            logger.info(f"Connection {connection_id} unsubscribed from task {task_id}")
    
    async def send_personal_message(self, message: str, connection_id: str):
        """
        Send a message to a specific WebSocket connection.
        
        Args:
            message: Message to send
            connection_id: Target connection
        """
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {e}")
                # Remove disconnected connection
                self.disconnect(connection_id)
    
    async def broadcast_to_task_subscribers(self, message: str, task_id: str):
        """
        Broadcast a message to all connections subscribed to a task.
        
        Args:
            message: Message to broadcast
            task_id: Task identifier
        """
        if task_id in self.task_subscriptions:
            connections = self.task_subscriptions[task_id].copy()
            
            for connection_id in connections:
                await self.send_personal_message(message, connection_id)
    
    async def broadcast_to_user(self, message: str, user_id: str):
        """
        Broadcast a message to all connections for a user.
        
        Args:
            message: Message to broadcast
            user_id: User identifier
        """
        if user_id in self.user_subscriptions:
            connections = self.user_subscriptions[user_id].copy()
            
            for connection_id in connections:
                await self.send_personal_message(message, connection_id)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)
    
    def get_task_subscriber_count(self, task_id: str) -> int:
        """Get number of connections subscribed to a task"""
        return len(self.task_subscriptions.get(task_id, set()))


# Global WebSocket manager instance
ws_manager = QAWebSocketManager()


@router.websocket("/qa/progress/{user_id}")
async def websocket_qa_progress(
    websocket: WebSocket,
    user_id: str,
    course_id: str = None
):
    """
    WebSocket endpoint for QA automation progress updates.
    
    Provides real-time updates for QA task execution including:
    - Task progress notifications
    - Status changes (started, completed, failed)
    - Error notifications
    - Task results when available
    
    Args:
        websocket: WebSocket connection
        user_id: User identifier from LTI context
        course_id: Optional course identifier for filtering
    """
    # Generate unique connection ID
    import uuid
    connection_id = str(uuid.uuid4())
    
    try:
        # Accept connection
        await ws_manager.connect(websocket, connection_id, user_id, course_id)
        
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            'type': 'connection',
            'status': 'connected',
            'connection_id': connection_id,
            'message': 'QA progress WebSocket connected'
        }))
        
        # Main message handling loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                message_type = message.get('type')
                
                if message_type == 'subscribe':
                    # Subscribe to task progress
                    task_id = message.get('task_id')
                    if task_id:
                        await ws_manager.subscribe_to_task(connection_id, task_id)
                        await websocket.send_text(json.dumps({
                            'type': 'subscription',
                            'status': 'subscribed',
                            'task_id': task_id,
                            'message': f'Subscribed to task {task_id}'
                        }))
                    else:
                        await websocket.send_text(json.dumps({
                            'type': 'error',
                            'message': 'Task ID required for subscription'
                        }))
                
                elif message_type == 'unsubscribe':
                    # Unsubscribe from task progress
                    task_id = message.get('task_id')
                    if task_id:
                        await ws_manager.unsubscribe_from_task(connection_id, task_id)
                        await websocket.send_text(json.dumps({
                            'type': 'subscription',
                            'status': 'unsubscribed',
                            'task_id': task_id,
                            'message': f'Unsubscribed from task {task_id}'
                        }))
                
                elif message_type == 'ping':
                    # Respond to ping with pong
                    await websocket.send_text(json.dumps({
                        'type': 'pong',
                        'timestamp': message.get('timestamp')
                    }))
                
                elif message_type == 'get_status':
                    # Get current task status
                    task_id = message.get('task_id')
                    if task_id:
                        orchestrator = get_qa_orchestrator()
                        execution = await orchestrator.get_task_status(task_id)
                        
                        if execution:
                            await websocket.send_text(json.dumps({
                                'type': 'task_status',
                                'task_id': task_id,
                                'status': execution.status.value,
                                'progress': {
                                    'stage': execution.current_progress.stage.value if execution.current_progress else 'unknown',
                                    'current': execution.current_progress.current if execution.current_progress else 0,
                                    'total': execution.current_progress.total if execution.current_progress else 0,
                                    'percentage': execution.current_progress.percentage if execution.current_progress else 0,
                                    'message': execution.current_progress.message if execution.current_progress else ''
                                } if execution.current_progress else None
                            }))
                        else:
                            await websocket.send_text(json.dumps({
                                'type': 'error',
                                'message': f'Task {task_id} not found'
                            }))
                
                else:
                    # Unknown message type
                    await websocket.send_text(json.dumps({
                        'type': 'error',
                        'message': f'Unknown message type: {message_type}'
                    }))
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    'type': 'error',
                    'message': 'Invalid JSON message format'
                }))
            
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket.send_text(json.dumps({
                    'type': 'error',
                    'message': 'Internal server error'
                }))
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    
    finally:
        # Clean up connection
        ws_manager.disconnect(connection_id)


# Progress broadcaster integration
class WebSocketProgressBroadcaster:
    """
    Integrates the WebSocket manager with the QA framework progress broadcaster.
    
    Receives progress updates from the QA execution engine and broadcasts
    them to subscribed WebSocket clients.
    """
    
    def __init__(self, ws_manager: QAWebSocketManager):
        """
        Initialize progress broadcaster.
        
        Args:
            ws_manager: WebSocket manager instance
        """
        self.ws_manager = ws_manager
    
    async def broadcast_progress_update(self, update_data: Dict):
        """
        Broadcast progress update to WebSocket clients.
        
        Args:
            update_data: Progress update data from QA framework
        """
        try:
            task_id = update_data.get('task_id')
            if not task_id:
                return
            
            # Format message for WebSocket clients
            message = json.dumps({
                'type': 'progress_update',
                'task_id': task_id,
                'data': update_data
            })
            
            # Broadcast to task subscribers
            await self.ws_manager.broadcast_to_task_subscribers(message, task_id)
            
            # Also broadcast to user if user_id is available
            user_id = update_data.get('user_id')
            if user_id:
                await self.ws_manager.broadcast_to_user(message, user_id)
                
        except Exception as e:
            logger.error(f"Failed to broadcast progress update: {e}")
    
    async def broadcast_task_completion(self, task_id: str, result_data: Dict):
        """
        Broadcast task completion notification.
        
        Args:
            task_id: Completed task identifier
            result_data: Task result data
        """
        try:
            message = json.dumps({
                'type': 'task_completed',
                'task_id': task_id,
                'result': result_data
            })
            
            await self.ws_manager.broadcast_to_task_subscribers(message, task_id)
            
        except Exception as e:
            logger.error(f"Failed to broadcast task completion: {e}")
    
    async def broadcast_task_error(self, task_id: str, error_data: Dict):
        """
        Broadcast task error notification.
        
        Args:
            task_id: Failed task identifier
            error_data: Error information
        """
        try:
            message = json.dumps({
                'type': 'task_error',
                'task_id': task_id,
                'error': error_data
            })
            
            await self.ws_manager.broadcast_to_task_subscribers(message, task_id)
            
        except Exception as e:
            logger.error(f"Failed to broadcast task error: {e}")


# Initialize WebSocket progress broadcaster
ws_progress_broadcaster = WebSocketProgressBroadcaster(ws_manager)


@router.get("/qa/connections/stats")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics.
    
    Returns information about active connections and subscriptions
    for monitoring and debugging purposes.
    """
    return {
        'total_connections': ws_manager.get_connection_count(),
        'active_task_subscriptions': len(ws_manager.task_subscriptions),
        'active_user_subscriptions': len(ws_manager.user_subscriptions),
        'task_subscriber_counts': {
            task_id: ws_manager.get_task_subscriber_count(task_id)
            for task_id in ws_manager.task_subscriptions.keys()
        }
    }


# Export WebSocket manager and broadcaster for use in other modules
__all__ = ['router', 'ws_manager', 'ws_progress_broadcaster'] 