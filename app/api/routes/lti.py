"""
LTI (Learning Tools Interoperability) route handlers for Canvas integration.
Handles LTI 1.3 authentication, session management, and Canvas context.
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings

from app.core.exceptions import LTIAuthenticationError, LTIValidationError
from app.core.security import verify_lti_token, create_session_token
from app.services.lti_service import LTIService
from app.services.session_service import SessionService

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router and templates
router = APIRouter(prefix="/lti", tags=["lti"])
templates = Jinja2Templates(directory="templates")

# Get application settings
settings = get_settings()

# Initialize services
lti_service = LTIService()
session_service = SessionService()


class LTILaunchRequest(BaseModel):
    """LTI Launch Request validation model."""
    iss: str
    aud: str
    sub: str
    exp: int
    iat: int
    nonce: str
    # Canvas specific claims
    custom_canvas_course_id: Optional[str] = None
    custom_canvas_user_id: Optional[str] = None
    # Additional LTI claims
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    roles: Optional[list] = None


@router.post("/launch", response_class=HTMLResponse)
async def lti_launch(
    request: Request,
    id_token: str = Form(...),
    state: str = Form(...),
):
    """
    Handle LTI 1.3 launch from Canvas.
    """
    try:
        logger.info("LTI launch initiated")
        
        # Validate the LTI token
        payload = verify_lti_token(id_token)
        logger.info(f"LTI token validated for user: {payload.get('sub', 'unknown')}")
        
        # Extract user and course information
        user_info = {
            "id": payload.get("sub"),
            "name": payload.get("name", ""),
            "given_name": payload.get("given_name", ""),
            "family_name": payload.get("family_name", ""),
            "email": payload.get("email", ""),
            "roles": payload.get("https://purl.imsglobal.org/spec/lti/claim/roles", []),
        }
        
        # Extract Canvas context
        canvas_context = {
            "course_id": payload.get("https://purl.imsglobal.org/spec/lti/claim/context", {}).get("id"),
            "course_name": payload.get("https://purl.imsglobal.org/spec/lti/claim/context", {}).get("title", ""),
            "launch_url": str(request.url),
            "canvas_url": payload.get("https://purl.imsglobal.org/spec/lti/claim/tool_platform", {}).get("url", ""),
        }
        
        # Create session data
        session_data = {
            "user": user_info,
            "canvas": canvas_context,
            "lti_payload": payload,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=8)).isoformat(),
        }
        
        session_token = create_session_token(session_data)
        
        # Create session using your session service
        try:
            session_service.create_lti_session(request, user_info, canvas_context, payload)
            logger.info("Session created successfully")
        except Exception as e:
            logger.warning(f"Session creation failed, continuing: {e}")
        
        # Render the dashboard template
        return templates.TemplateResponse("qa-dashboard.html", {
            "request": request,
            "user": user_info,
            "canvas": canvas_context,
        })
        
    except Exception as e:
        logger.error(f"Unexpected error during LTI launch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during LTI launch"
        )


@router.get("/session", response_model=Dict[str, Any])
async def get_session_info(
    request: Request
):
    """
    Get current session information for the authenticated user.
    
    Returns user context, Canvas information, and session validity.
    """
    try:
        session_token = request.cookies.get("lti_session")
        if not session_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No session token found"
            )
        
        session_data = await session_service.get_session(session_token)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session"
            )
        
        # Check if session is still valid
        expires_at = datetime.fromisoformat(session_data["expires_at"])
        is_valid = datetime.utcnow() < expires_at
        
        return {
            "valid": is_valid,
            "user": session_data.get("user", {}),
            "canvas": session_data.get("canvas", {}),
            "session": {
                "created_at": session_data.get("created_at"),
                "expires_at": session_data.get("expires_at"),
                "expires": expires_at.isoformat(),
            },
        }
        
    except Exception as e:
        logger.error(f"Error retrieving session info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session information"
        )


@router.post("/refresh-session", response_model=Dict[str, Any])
async def refresh_session(
    request: Request
):
    """
    Refresh the current session, extending its expiration time.
    """
    try:
        session_token = request.cookies.get("lti_session")
        if not session_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No session token found"
            )
        
        # Get current session data
        session_data = await session_service.get_session(session_token)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session"
            )
        
        # Update expiration time
        new_expires_at = datetime.utcnow() + timedelta(hours=8)
        session_data["expires_at"] = new_expires_at.isoformat()
        
        # Update session in storage
        await session_service.update_session(session_token, session_data)
        
        logger.info(f"Session refreshed for user: {current_user.get('id', 'unknown')}")
        
        return {
            "valid": True,
            "user": session_data.get("user", {}),
            "canvas": session_data.get("canvas", {}),
            "session": {
                "created_at": session_data.get("created_at"),
                "expires_at": session_data.get("expires_at"),
                "expires": new_expires_at.isoformat(),
            },
        }
        
    except Exception as e:
        logger.error(f"Error refreshing session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh session"
        )


@router.post("/logout")
async def logout(
    request: Request
):
    """
    Logout the current user and invalidate the session.
    """
    try:
        session_token = request.cookies.get("lti_session")
        if session_token:
            await session_service.delete_session(session_token)
            logger.info(f"User logged out: {current_user.get('id', 'unknown')}")
        
        # Create response and clear session cookie
        response = RedirectResponse(
            url="/logged-out",
            status_code=status.HTTP_302_FOUND
        )
        response.delete_cookie(key="lti_session")
        
        return response
        
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout"
        )


@router.get("/config", response_model=Dict[str, Any])
async def get_lti_config():
    """
    Get LTI configuration information for Canvas integration.
    
    This endpoint provides the necessary configuration details for setting up
    the LTI tool in Canvas.
    """
    try:
        config = {
            "title": "ACU QA Automation Tool",
            "description": "Quality Assurance automation for Canvas course content",
            "oidc_initiation_url": f"{settings.base_url}/lti/login",
            "target_link_uri": f"{settings.base_url}/lti/launch",
            "scopes": [
                "https://purl.imsglobal.org/spec/lti-ags/scope/lineitem",
                "https://purl.imsglobal.org/spec/lti-ags/scope/result.readonly",
                "https://purl.imsglobal.org/spec/lti-ags/scope/score",
            ],
            "extensions": [
                {
                    "domain": settings.domain,
                    "tool_id": "acu_qa_automation",
                    "platform": "canvas.instructure.com",
                    "settings": {
                        "placements": [
                            {
                                "placement": "course_navigation",
                                "message_type": "LtiResourceLinkRequest",
                                "target_link_uri": f"{settings.base_url}/lti/launch",
                                "text": "QA Automation",
                                "icon_url": f"{settings.base_url}/static/images/qa-icon.png",
                            }
                        ]
                    }
                }
            ],
            "public_jwk_url": f"{settings.base_url}/.well-known/jwks.json",
            "custom_fields": {
                "canvas_course_id": "$Canvas.course.id",
                "canvas_user_id": "$Canvas.user.id",
            }
        }
        
        return config
        
    except Exception as e:
        logger.error(f"Error getting LTI config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get LTI configuration"
        )


@router.get("/login")
@router.post("/login")
async def lti_login(request: Request):
    try:
        # Handle both GET (query params) and POST (form data)
        if request.method == "GET":
            params = dict(request.query_params)
        else:  # POST
            form_data = await request.form()
            params = dict(form_data)
        
        # Log what we received
        logger.info(f"LTI login - Method: {request.method}")
        logger.info(f"LTI login - Received params: {params}")
        
        # Extract parameters
        iss = params.get('iss')
        login_hint = params.get('login_hint')
        target_link_uri = params.get('target_link_uri')
        client_id = params.get('client_id')
        lti_message_hint = params.get('lti_message_hint')
        
        logger.info(f"Canvas sent target_link_uri: '{target_link_uri}'")
        
        # Check required parameters
        if not iss:
            return {
                "error": "Missing iss parameter",
                "method": request.method,
                "all_params": params,
                "headers": dict(request.headers)
            }
        
        if not login_hint or not target_link_uri or not client_id:
            return {
                "error": "Missing required parameters",
                "method": request.method,
                "received": params,
                "required": ["iss", "login_hint", "target_link_uri", "client_id"]
            }
        
        # Generate state and nonce for security
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        
        # Build authorization URL for Canvas
        auth_params = {
            "response_type": "id_token",
            "scope": "openid",
            "client_id": client_id,
            "redirect_uri": target_link_uri,  # This must match Canvas config exactly
            "login_hint": login_hint,
            "state": state,
            "nonce": nonce,
            "response_mode": "form_post",
            "prompt": "none",
        }

        logger.info(f"Sending back to Canvas with redirect_uri: '{target_link_uri}'")
        
        # Only add lti_message_hint if it exists
        if lti_message_hint:
            auth_params["lti_message_hint"] = lti_message_hint
        
        # Construct Canvas authorization URL
        auth_url = f"{iss}/api/lti/authorize_redirect"
        query_string = "&".join([f"{k}={v}" for k, v in auth_params.items()])
        redirect_url = f"{auth_url}?{query_string}"
        
        logger.info(f"Full redirect URL: {redirect_url}")
        
        return RedirectResponse(
            url=redirect_url,
            status_code=status.HTTP_302_FOUND
        )
        
    except Exception as e:
        logger.error(f"Error during LTI login: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "error": "Exception occurred",
            "details": str(e),
            "method": request.method
        }


@router.get("/health")
async def health_check():
    """
    Health check endpoint for LTI service.
    """
    try:
        # Perform basic health checks
        session_health = await session_service.health_check()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "lti": "operational",
                "sessions": "operational" if session_health else "degraded",
            },
            "version": settings.version,
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        ) 