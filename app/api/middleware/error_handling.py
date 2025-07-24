"""
Centralized error handling middleware for Canvas LTI integration
"""

import logging
import traceback
from typing import Dict, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ...core.config import settings
from ...core.exceptions import (
    QAAutomationException,
    LTIAuthenticationError,
    LTIValidationError,
    SessionError,
    CanvasAPIError,
    QATaskError,
    ConfigurationError
)


logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for centralized error handling with Canvas iframe compatibility
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            response = await call_next(request)
            return response
            
        except HTTPException as exc:
            return await self.handle_http_exception(request, exc)
            
        except QAAutomationException as exc:
            return await self.handle_qa_exception(request, exc)
            
        except Exception as exc:
            return await self.handle_unexpected_exception(request, exc)
    
    async def handle_http_exception(self, request: Request, exc: HTTPException) -> Response:
        """Handle FastAPI HTTP exceptions"""
        logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
        
        # Check if this is an API request
        if self.is_api_request(request):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "type": "http_error",
                        "message": exc.detail,
                        "status_code": exc.status_code
                    }
                },
                headers=exc.headers
            )
        
        # Return iframe-compatible error page for browser requests
        return await self.create_error_page(request, exc.status_code, exc.detail)
    
    async def handle_qa_exception(self, request: Request, exc: QAAutomationException) -> Response:
        """Handle custom QA Automation exceptions"""
        logger.error(f"QA Exception ({type(exc).__name__}): {exc.message}")
        
        # Map exception types to HTTP status codes
        status_code_map = {
            LTIAuthenticationError: 401,
            LTIValidationError: 400,
            SessionError: 401,
            CanvasAPIError: 502,
            QATaskError: 422,
            ConfigurationError: 500
        }
        
        status_code = status_code_map.get(type(exc), 500)
        
        if self.is_api_request(request):
            return JSONResponse(
                status_code=status_code,
                content={
                    "error": {
                        "type": type(exc).__name__,
                        "message": exc.message,
                        "details": exc.details,
                        "status_code": status_code
                    }
                }
            )
        
        # Return iframe-compatible error page
        return await self.create_error_page(request, status_code, exc.message, exc.details)
    
    async def handle_unexpected_exception(self, request: Request, exc: Exception) -> Response:
        """Handle unexpected exceptions"""
        error_id = self.generate_error_id()
        
        logger.error(
            f"Unexpected error ({error_id}): {str(exc)}",
            extra={
                "error_id": error_id,
                "exception_type": type(exc).__name__,
                "traceback": traceback.format_exc(),
                "request_path": str(request.url.path),
                "request_method": request.method
            }
        )
        
        # Don't expose internal errors in production
        if settings.environment == "production":
            error_message = "An internal server error occurred"
        else:
            error_message = f"Unexpected error: {str(exc)}"
        
        if self.is_api_request(request):
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "type": "internal_error",
                        "message": error_message,
                        "error_id": error_id,
                        "status_code": 500
                    }
                }
            )
        
        return await self.create_error_page(request, 500, error_message, {"error_id": error_id})
    
    def is_api_request(self, request: Request) -> bool:
        """Check if request is for API endpoint"""
        path = request.url.path
        accept_header = request.headers.get("accept", "")
        
        # API endpoints start with /api/ or request JSON
        return (
            path.startswith("/api/") or 
            path.startswith("/ws/") or
            "application/json" in accept_header
        )
    
    async def create_error_page(self, request: Request, status_code: int, 
                               message: str, details: Dict[str, Any] = None) -> HTMLResponse:
        """Create iframe-compatible error page"""
        details = details or {}
        
        # Get user context for personalization (if available)
        user_name = "User"
        try:
            if hasattr(request, 'session') and request.session.get('user_name'):
                user_name = request.session.get('user_name', 'User')
        except:
            pass
        
        # Create user-friendly error messages
        user_friendly_messages = {
            400: "There was a problem with your request. Please try again.",
            401: "Please log in through Canvas to access this tool.",
            403: "You don't have permission to access this feature.",
            404: "The page you're looking for could not be found.",
            422: "There was a problem processing your request.",
            500: "We're experiencing technical difficulties. Please try again later.",
            502: "We're having trouble connecting to Canvas. Please try again."
        }
        
        user_message = user_friendly_messages.get(status_code, message)
        
        # Create iframe-compatible HTML error page with ACU branding
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>QA Automation Tool - Error</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #F9F4F1;
                    color: #6B2C6B;
                    line-height: 1.6;
                }}
                .error-container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    border-left: 4px solid #D2492A;
                }}
                .error-header {{
                    display: flex;
                    align-items: center;
                    margin-bottom: 20px;
                }}
                .error-icon {{
                    width: 48px;
                    height: 48px;
                    background: #D2492A;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 24px;
                    margin-right: 15px;
                }}
                .error-title {{
                    color: #4A1A4A;
                    font-size: 24px;
                    margin: 0;
                }}
                .error-message {{
                    color: #6B2C6B;
                    font-size: 16px;
                    margin-bottom: 20px;
                }}
                .error-actions {{
                    display: flex;
                    gap: 10px;
                    flex-wrap: wrap;
                }}
                .btn {{
                    padding: 10px 20px;
                    border-radius: 4px;
                    text-decoration: none;
                    font-weight: 500;
                    display: inline-block;
                    transition: background-color 0.2s;
                }}
                .btn-primary {{
                    background: #D2492A;
                    color: white;
                }}
                .btn-primary:hover {{
                    background: #B8391F;
                }}
                .btn-secondary {{
                    background: #F4B942;
                    color: #4A1A4A;
                }}
                .btn-secondary:hover {{
                    background: #E6A830;
                }}
                .error-details {{
                    margin-top: 20px;
                    padding: 15px;
                    background: #F4ECE6;
                    border-radius: 4px;
                    font-size: 14px;
                    color: #6B2C6B;
                }}
                .support-info {{
                    margin-top: 20px;
                    padding: 15px;
                    background: #EDF7FF;
                    border-radius: 4px;
                    border-left: 3px solid #4A1A4A;
                }}
                @media (max-width: 480px) {{
                    .error-container {{
                        padding: 20px;
                        margin: 10px;
                    }}
                    .error-actions {{
                        flex-direction: column;
                    }}
                    .btn {{
                        text-align: center;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <div class="error-header">
                    <div class="error-icon">⚠</div>
                    <h1 class="error-title">Oops! Something went wrong</h1>
                </div>
                
                <div class="error-message">
                    <p>Hi {user_name},</p>
                    <p>{user_message}</p>
                </div>
                
                <div class="error-actions">
                    <a href="javascript:history.back()" class="btn btn-primary">Go Back</a>
                    <a href="javascript:location.reload()" class="btn btn-secondary">Try Again</a>
                </div>
                
                {"" if status_code >= 500 else f'''
                <div class="support-info">
                    <h3 style="margin-top: 0; color: #4A1A4A;">Need Help?</h3>
                    <p>If you continue to have problems, please contact your instructor or system administrator.</p>
                </div>
                '''}
                
                {f'''
                <div class="error-details">
                    <strong>Error Details:</strong><br>
                    Status Code: {status_code}<br>
                    {f"Error ID: {details.get('error_id', 'N/A')}<br>" if details.get('error_id') else ""}
                    {f"Additional Info: {str(details)}<br>" if details and settings.environment != "production" else ""}
                </div>
                ''' if settings.environment != "production" or details.get('error_id') else ""}
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(
            content=html_content,
            status_code=status_code,
            headers={
                "X-Frame-Options": settings.x_frame_options,
                "Content-Security-Policy": "default-src 'self' 'unsafe-inline'"
            }
        )
    
    def generate_error_id(self) -> str:
        """Generate unique error ID for tracking"""
        import uuid
        return f"ERR-{uuid.uuid4().hex[:8].upper()}"


# Error handler functions for specific exception types
async def lti_authentication_error_handler(request: Request, exc: LTIAuthenticationError):
    """Handle LTI authentication errors with redirect to login"""
    logger.error(f"LTI Authentication Error: {exc.message}")
    
    if ErrorHandlingMiddleware().is_api_request(request):
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "type": "lti_authentication_error",
                    "message": "LTI authentication required",
                    "redirect_to_canvas": True
                }
            }
        )
    
    # For browser requests, show user-friendly error page
    return await ErrorHandlingMiddleware().create_error_page(
        request, 
        401, 
        "Please access this tool through Canvas LMS",
        {"authentication_required": True}
    )


async def canvas_api_error_handler(request: Request, exc: CanvasAPIError):
    """Handle Canvas API errors with retry suggestions"""
    logger.error(f"Canvas API Error: {exc.message}")
    
    status_code = 502  # Bad Gateway for external service errors
    
    if ErrorHandlingMiddleware().is_api_request(request):
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "type": "canvas_api_error",
                    "message": "Canvas API is temporarily unavailable",
                    "retry_suggested": True,
                    "details": exc.details
                }
            }
        )
    
    return await ErrorHandlingMiddleware().create_error_page(
        request,
        status_code,
        "We're having trouble connecting to Canvas. Please try again in a moment.",
        {"service": "Canvas API", "retry_suggested": True}
    ) 