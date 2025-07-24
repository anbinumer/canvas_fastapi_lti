"""
LTI authentication & session management security framework
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.config import settings
from core.exceptions import LTIAuthenticationError, SessionError
from services.lti_service import lti_service
from services.session_service import session_service


logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


class LTISecurityService:
    """
    Security service for LTI authentication and session management
    Enhanced with multi-instance Canvas support
    """
    
    def __init__(self):
        # Get list of configured Canvas instances
        self.allowed_canvas_instances = self._get_allowed_canvas_instances()
        
    def _get_allowed_canvas_instances(self) -> List[str]:
        """Get list of allowed Canvas instances from configuration"""
        canvas_instances = settings.get_all_canvas_instances()
        allowed_domains = []
        
        for instance_config in canvas_instances.values():
            try:
                # Extract domain from base_url
                domain = instance_config.base_url.replace("https://", "").replace("http://", "")
                domain = domain.rstrip("/")
                allowed_domains.append(domain)
            except Exception as e:
                logger.warning(f"Failed to extract domain from Canvas instance {instance_config.name}: {e}")
                
        # Add fallback domains if no instances configured
        if not allowed_domains:
            allowed_domains = [
                "www.aculeo.test.instructure.com",
                "www.aculeo.beta.instructure.com", 
                "www.aculeo.instructure.com"
            ]
            
        return allowed_domains
        
    def validate_canvas_instance(self, issuer: str) -> bool:
        """Validate that the Canvas instance is trusted"""
        try:
            # Extract domain from issuer URL
            domain = issuer.replace("https://", "").replace("http://", "")
            domain = domain.rstrip("/")
            
            return domain in self.allowed_canvas_instances
            
        except Exception as e:
            logger.error(f"Error validating Canvas instance {issuer}: {str(e)}")
            return False

    def validate_lti_token(self, token: str) -> Dict[str, Any]:
        """
        Validate LTI 1.3 JWT token
        """
        try:
            # Use the LTI service to validate the token
            return lti_service.validate_lti_launch(None, token)  # Request will be handled by LTI service
            
        except Exception as e:
            logger.error(f"LTI token validation failed: {str(e)}")
            raise LTIAuthenticationError(f"Invalid LTI token: {str(e)}")

    def create_session_token(self, session_data: Dict[str, Any]) -> str:
        """
        Create a secure session token for Canvas iframe compatibility
        """
        try:
            # Use session service to create token
            return session_service.create_session_token(session_data)
            
        except Exception as e:
            logger.error(f"Session token creation failed: {str(e)}")
            raise SessionError(f"Session creation failed: {str(e)}")

    def verify_session_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode session token
        """
        try:
            return session_service.verify_session_token(token)
            
        except Exception as e:
            logger.error(f"Session token verification failed: {str(e)}")
            raise SessionError(f"Session verification failed: {str(e)}")

    def get_canvas_instance_for_issuer(self, issuer: str) -> Optional[str]:
        """
        Get Canvas instance name for a given issuer URL
        """
        canvas_instances = settings.get_all_canvas_instances()
        
        for instance_name, instance_config in canvas_instances.items():
            if issuer.rstrip('/') == instance_config.base_url.rstrip('/'):
                return instance_name
                
        return None

    def check_user_permissions(self, user_roles: List[str], required_role: str = "instructor") -> bool:
        """
        Check if user has required permissions for QA operations
        """
        role_mappings = {
            "instructor": [
                "http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor",
                "http://purl.imsglobal.org/vocab/lis/v2/membership#ContentDeveloper",
                "http://purl.imsglobal.org/vocab/lis/v2/membership#TeachingAssistant"
            ],
            "learner": [
                "http://purl.imsglobal.org/vocab/lis/v2/membership#Learner"
            ],
            "any": []  # Any authenticated user
        }
        
        if required_role == "any":
            return True
            
        allowed_roles = role_mappings.get(required_role, [])
        return any(role in allowed_roles for role in user_roles)


# Global security service instance
lti_security_service = LTISecurityService()


# Dependency functions for FastAPI
async def require_lti_session(request: Request) -> Dict[str, Any]:
    """
    Dependency to require valid LTI session
    """
    try:
        if not session_service.validate_session(request):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Valid LTI session required"
            )
        
        user_context = session_service.get_user_context(request)
        if not user_context:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User context not found in session"
            )
        
        return user_context
        
    except Exception as e:
        logger.error(f"LTI session validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="LTI authentication required"
        )


async def require_instructor_role(request: Request) -> Dict[str, Any]:
    """
    Dependency to require instructor role
    """
    user_context = await require_lti_session(request)
    
    user_roles = user_context.get('roles', [])
    if not lti_security_service.check_user_permissions(user_roles, "instructor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor role required for QA operations"
        )
    
    return user_context


async def get_optional_user_context(request: Request) -> Optional[Dict[str, Any]]:
    """
    Optional dependency to get user context if available
    """
    try:
        if session_service.validate_session(request):
            return session_service.get_user_context(request)
    except Exception:
        pass
    
    return None


def verify_lti_token(token: str) -> Dict[str, Any]:
    """
    Verify LTI 1.3 JWT token (standalone function)
    """
    return lti_security_service.validate_lti_token(token)


def create_session_token(session_data: Dict[str, Any]) -> str:
    """
    Create session token (standalone function)
    """
    return lti_security_service.create_session_token(session_data)


def create_security_headers_middleware():
    """
    Create security headers middleware for Canvas iframe compatibility
    """
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response
    
    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next) -> Response:
            response = await call_next(request)
            
            # Add security headers from settings
            headers = settings.get_security_headers()
            for header_name, header_value in headers.items():
                response.headers[header_name] = header_value
            
            return response
    
    return SecurityHeadersMiddleware


def create_session_middleware():
    """
    Create session middleware with Canvas iframe compatibility
    """
    from starlette.middleware.sessions import SessionMiddleware
    
    return SessionMiddleware(
        secret_key=settings.secret_key,
        max_age=settings.session_expire_seconds,
        same_site=settings.session_cookie_samesite,
        https_only=settings.session_cookie_secure
    )


# Rate limiting decorator for Canvas API calls (placeholder for future implementation)
def canvas_api_rate_limit(func):
    """
    Decorator for Canvas API rate limiting
    """
    async def wrapper(*args, **kwargs):
        # TODO: Implement rate limiting logic in future stories
        return await func(*args, **kwargs)
    return wrapper


# Security validation functions
def validate_lti_launch_security(request: Request, launch_data: Dict[str, Any]) -> bool:
    """
    Comprehensive security validation for LTI launch
    """
    try:
        # Validate Canvas instance
        issuer = launch_data.get('iss', '')
        if not lti_security_service.validate_canvas_instance(issuer):
            logger.error(f"Untrusted Canvas instance in launch: {issuer}")
            return False
        
        # Validate security headers
        if not lti_security_service.validate_lti_security_headers(request):
            logger.error("LTI security headers validation failed")
            return False
        
        # Validate required claims
        required_claims = ['iss', 'sub', 'aud', 'exp', 'iat', 'nonce']
        for claim in required_claims:
            if claim not in launch_data:
                logger.error(f"Missing required LTI claim: {claim}")
                return False
        
        # Validate timestamp (exp should be in the future)
        import time
        current_time = int(time.time())
        exp_time = launch_data.get('exp', 0)
        
        if exp_time <= current_time:
            logger.error("LTI launch token expired")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"LTI launch security validation failed: {str(e)}")
        return False


def create_trusted_origins_list() -> List[str]:
    """
    Create list of trusted origins for CSRF protection
    """
    trusted_origins = [settings.base_url]
    
    # Add all allowed Canvas instances
    for instance in settings.allowed_canvas_instances:
        trusted_origins.append(f"https://{instance}")
        # Also add without https for local development
        if settings.environment == "development":
            trusted_origins.append(f"http://{instance}")
    
    return trusted_origins 