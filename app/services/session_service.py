"""
User session and context management for Canvas LTI integration
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from fastapi import Request, Response
from app.core.config import settings
from app.core.exceptions import SessionError, LTIValidationError


logger = logging.getLogger(__name__)


class SessionService:
    """
    Manages user sessions and LTI context with Canvas iframe compatibility
    """
    
    def __init__(self):
        self.session_timeout = settings.session_expire_seconds
        
    def create_lti_session(self, request: Request, user_context: Dict[str, Any], 
                          canvas_context: Dict[str, Any], launch_data: Dict[str, Any]) -> str:
        """
        Create a new LTI session with user and Canvas context
        """
        try:
            session_id = self._generate_session_id(user_context.get('user_id'))
            
            # Store LTI context in session
            session_data = {
                # User Information
                'lti_user_id': user_context.get('user_id'),
                'user_name': user_context.get('name'),
                'user_given_name': user_context.get('given_name'),
                'user_family_name': user_context.get('family_name'),
                'user_email': user_context.get('email'),
                'user_roles': user_context.get('roles', []),
                'user_picture': user_context.get('picture'),
                'user_locale': user_context.get('locale', 'en'),
                
                # Canvas Context
                'canvas_course_id': canvas_context.get('course_id'),
                'canvas_course_name': canvas_context.get('course_name'),
                'canvas_context_id': canvas_context.get('context_id'),
                'canvas_context_type': canvas_context.get('context_type', []),
                'canvas_instance_url': canvas_context.get('canvas_instance_url'),
                'canvas_deployment_id': canvas_context.get('deployment_id'),
                'canvas_resource_link_id': canvas_context.get('resource_link_id'),
                'canvas_resource_link_title': canvas_context.get('resource_link_title'),
                'canvas_launch_presentation': canvas_context.get('launch_presentation', {}),
                'canvas_custom_claims': canvas_context.get('custom_claims', {}),
                
                # Session Metadata
                'session_id': session_id,
                'lti_launch_data': launch_data,  # Store full launch data for reference
                'session_created': datetime.utcnow().isoformat(),
                'session_expires': (datetime.utcnow() + timedelta(seconds=self.session_timeout)).isoformat(),
                'last_activity': datetime.utcnow().isoformat(),
                'is_instructor': self._is_instructor(user_context.get('roles', [])),
                'is_learner': self._is_learner(user_context.get('roles', [])),
                
                # Canvas API Context (for future use)
                'canvas_api_base_url': self._extract_api_base_url(canvas_context.get('canvas_instance_url')),
                'canvas_api_token': None,  # Will be populated when needed
                
                # QA Tool Context
                'qa_task_history': [],
                'user_preferences': {},
                'active_qa_tasks': {}
            }
            
            # Store in request session
            for key, value in session_data.items():
                request.session[key] = value
            
            logger.info(f"LTI session created for user {user_context.get('user_id')} in course {canvas_context.get('course_id')}")
            
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create LTI session: {str(e)}")
            raise SessionError(f"Session creation failed: {str(e)}")
    
    def validate_session(self, request: Request) -> bool:
        """
        Validate that the current session is valid and not expired
        """
        try:
            # Check if LTI user ID exists in session
            lti_user_id = request.session.get('lti_user_id')
            if not lti_user_id:
                return False
            
            # Check session expiration
            session_expires = request.session.get('session_expires')
            if not session_expires:
                return False
            
            expires_dt = datetime.fromisoformat(session_expires)
            if datetime.utcnow() > expires_dt:
                logger.info(f"Session expired for user {lti_user_id}")
                return False
            
            # Update last activity
            self.update_last_activity(request)
            
            return True
            
        except Exception as e:
            logger.error(f"Session validation error: {str(e)}")
            return False
    
    def get_user_context(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Get user context from session
        """
        if not self.validate_session(request):
            return None
        
        return {
            'user_id': request.session.get('lti_user_id'),
            'name': request.session.get('user_name'),
            'given_name': request.session.get('user_given_name'),
            'family_name': request.session.get('user_family_name'),
            'email': request.session.get('user_email'),
            'roles': request.session.get('user_roles', []),
            'picture': request.session.get('user_picture'),
            'locale': request.session.get('user_locale', 'en'),
            'is_instructor': request.session.get('is_instructor', False),
            'is_learner': request.session.get('is_learner', False)
        }
    
    def get_canvas_context(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Get Canvas context from session
        """
        if not self.validate_session(request):
            return None
        
        return {
            'course_id': request.session.get('canvas_course_id'),
            'course_name': request.session.get('canvas_course_name'),
            'context_id': request.session.get('canvas_context_id'),
            'context_type': request.session.get('canvas_context_type', []),
            'instance_url': request.session.get('canvas_instance_url'),
            'deployment_id': request.session.get('canvas_deployment_id'),
            'resource_link_id': request.session.get('canvas_resource_link_id'),
            'resource_link_title': request.session.get('canvas_resource_link_title'),
            'launch_presentation': request.session.get('canvas_launch_presentation', {}),
            'custom_claims': request.session.get('canvas_custom_claims', {}),
            'api_base_url': request.session.get('canvas_api_base_url')
        }
    
    def update_last_activity(self, request: Request) -> None:
        """
        Update the last activity timestamp for the session
        """
        try:
            request.session['last_activity'] = datetime.utcnow().isoformat()
        except Exception as e:
            logger.error(f"Failed to update last activity: {str(e)}")
    
    def extend_session(self, request: Request, additional_seconds: int = None) -> bool:
        """
        Extend the session expiration time
        """
        try:
            if not self.validate_session(request):
                return False
            
            if additional_seconds is None:
                additional_seconds = self.session_timeout
            
            new_expiry = datetime.utcnow() + timedelta(seconds=additional_seconds)
            request.session['session_expires'] = new_expiry.isoformat()
            
            logger.debug(f"Session extended for user {request.session.get('lti_user_id')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to extend session: {str(e)}")
            return False
    
    def clear_session(self, request: Request) -> None:
        """
        Clear all session data
        """
        try:
            user_id = request.session.get('lti_user_id', 'unknown')
            request.session.clear()
            logger.info(f"Session cleared for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to clear session: {str(e)}")
    
    def store_canvas_api_token(self, request: Request, api_token: str) -> bool:
        """
        Store Canvas API token in session (when available)
        """
        try:
            if not self.validate_session(request):
                return False
            
            request.session['canvas_api_token'] = api_token
            request.session['canvas_api_token_stored'] = datetime.utcnow().isoformat()
            
            logger.debug(f"Canvas API token stored for user {request.session.get('lti_user_id')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store Canvas API token: {str(e)}")
            return False
    
    def get_canvas_api_token(self, request: Request) -> Optional[str]:
        """
        Get Canvas API token from session
        """
        if not self.validate_session(request):
            return None
        
        return request.session.get('canvas_api_token')
    
    def store_user_preference(self, request: Request, key: str, value: Any) -> bool:
        """
        Store user preference in session
        """
        try:
            if not self.validate_session(request):
                return False
            
            preferences = request.session.get('user_preferences', {})
            preferences[key] = value
            request.session['user_preferences'] = preferences
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store user preference: {str(e)}")
            return False
    
    def get_user_preference(self, request: Request, key: str, default: Any = None) -> Any:
        """
        Get user preference from session
        """
        if not self.validate_session(request):
            return default
        
        preferences = request.session.get('user_preferences', {})
        return preferences.get(key, default)
    
    def add_qa_task_to_history(self, request: Request, task_data: Dict[str, Any]) -> bool:
        """
        Add QA task to user's history
        """
        try:
            if not self.validate_session(request):
                return False
            
            history = request.session.get('qa_task_history', [])
            
            # Add timestamp if not present
            if 'timestamp' not in task_data:
                task_data['timestamp'] = datetime.utcnow().isoformat()
            
            history.append(task_data)
            
            # Keep only last 50 tasks to prevent session bloat
            if len(history) > 50:
                history = history[-50:]
            
            request.session['qa_task_history'] = history
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add QA task to history: {str(e)}")
            return False
    
    def get_qa_task_history(self, request: Request) -> List[Dict[str, Any]]:
        """
        Get user's QA task history
        """
        if not self.validate_session(request):
            return []
        
        return request.session.get('qa_task_history', [])
    
    def _generate_session_id(self, user_id: str) -> str:
        """
        Generate a unique session ID
        """
        import uuid
        return f"lti_session_{user_id}_{uuid.uuid4().hex[:8]}"
    
    def _extract_api_base_url(self, canvas_instance_url: str) -> str:
        """
        Extract Canvas API base URL from instance URL
        """
        if not canvas_instance_url:
            return ""
        
        # Remove trailing slashes and add API path
        base_url = canvas_instance_url.rstrip('/')
        return f"{base_url}/api/v1"
    
    def _is_instructor(self, user_roles: List[str]) -> bool:
        """Check if user has instructor privileges"""
        instructor_roles = [
            "http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor",
            "http://purl.imsglobal.org/vocab/lis/v2/membership#ContentDeveloper",
            "http://purl.imsglobal.org/vocab/lis/v2/membership#TeachingAssistant"
        ]
        return any(role in instructor_roles for role in user_roles)
    
    def _is_learner(self, user_roles: List[str]) -> bool:
        """Check if user is a learner"""
        learner_roles = [
            "http://purl.imsglobal.org/vocab/lis/v2/membership#Learner"
        ]
        return any(role in learner_roles for role in user_roles)
    
    def get_session_info(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive session information for debugging
        """
        if not self.validate_session(request):
            return None
        
        return {
            'session_id': request.session.get('session_id'),
            'user_id': request.session.get('lti_user_id'),
            'course_id': request.session.get('canvas_course_id'),
            'session_created': request.session.get('session_created'),
            'session_expires': request.session.get('session_expires'),
            'last_activity': request.session.get('last_activity'),
            'is_instructor': request.session.get('is_instructor', False),
            'canvas_instance': request.session.get('canvas_instance_url'),
            'has_api_token': bool(request.session.get('canvas_api_token')),
            'qa_tasks_count': len(request.session.get('qa_task_history', [])),
            'preferences_count': len(request.session.get('user_preferences', {}))
        }
    
    async def get_session_data(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Get complete session data including user and Canvas context.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Complete session data or None if no valid session
        """
        try:
            # Check if session is valid
            if not self.validate_session(request):
                return {
                    "valid": False,
                    "message": "No active LTI session",
                    "user": None,
                    "canvas": None,
                    "session": None
                }
            
            # Get user and canvas context
            user_context = self.get_user_context(request)
            canvas_context = self.get_canvas_context(request)
            
            # Get session info
            session_info = {
                "session_id": request.session.get('session_id'),
                "created_at": request.session.get('session_created'),
                "last_activity": request.session.get('last_activity'),
                "expires": request.session.get('session_expires')
            }
            
            return {
                "valid": True,
                "user": user_context,
                "canvas": canvas_context,
                "session": session_info
            }
            
        except Exception as e:
            logger.error(f"Error getting session data: {str(e)}")
            return {
                "valid": False,
                "error": str(e),
                "message": "Session validation failed",
                "user": None,
                "canvas": None,
                "session": None
            }


# Global session service instance
session_service = SessionService() 