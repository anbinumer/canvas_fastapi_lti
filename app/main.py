"""
QA Automation LTI Tool - FastAPI Application Entry Point

This is the main FastAPI application for the Canvas LTI QA Automation Tool.
Designed for AI-assisted development and Canvas LTI 1.3 integration.
"""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime

# Core imports
from app.core.config import get_settings
from app.core.security import (
    create_session_middleware,
    create_security_headers_middleware
)
from app.core.exceptions import (
    LTIAuthenticationError,
    LTIValidationError,
    SessionError,
    CanvasAPIError,
    QATaskError,
    ConfigurationError
)

# Middleware imports
from app.api.middleware.error_handling import (
    ErrorHandlingMiddleware,
    lti_authentication_error_handler,
    canvas_api_error_handler
)

# Router imports
from app.api.routes import lti, canvas, qa_tasks, websockets, health

# Get settings instance
settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version=settings.app_version,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None
)

# Mount static files for frontend assets
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Add middleware (order matters - first added is outermost)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(create_security_headers_middleware())

# Add session middleware with proper parameters
try:
    from starlette.middleware.sessions import SessionMiddleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        max_age=settings.session_expire_seconds,
        path="/",
        same_site=settings.session_cookie_samesite,
        https_only=settings.session_cookie_secure
    )
except ImportError:
    logger.warning("Session middleware not available - sessions disabled")

# Add exception handlers
app.add_exception_handler(LTIAuthenticationError, lti_authentication_error_handler)
app.add_exception_handler(CanvasAPIError, canvas_api_error_handler)

# Register routers
app.include_router(lti.router, prefix="/lti", tags=["LTI"])
app.include_router(canvas.router, prefix="/api/v1/canvas", tags=["Canvas"])
app.include_router(qa_tasks.router, prefix="/api/v1/qa", tags=["QA Tasks"])
app.include_router(websockets.router, prefix="/ws", tags=["WebSocket"])
app.include_router(health.router)


@app.get("/health")
async def health_check():
    """
    Railway health check endpoint with LTI configuration validation
    Returns 200 status with timestamp and configuration status
    """
    try:
        # Validate LTI configuration using new multi-instance structure
        lti_config_valid = False
        lti_config_message = "Not configured"
        
        try:
            # Get active Canvas instance configuration
            canvas_config = settings.get_canvas_instance_config()
            if canvas_config and canvas_config.client_id and canvas_config.private_key:
                lti_config_valid = True
                lti_config_message = "Valid"
            else:
                lti_config_message = "Missing required environment variables"
        except Exception as e:
            lti_config_message = f"Invalid: {str(e)}"
        
        # Get all configured Canvas instances
        all_instances = settings.get_all_canvas_instances()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "qa-automation-lti",
            "environment": settings.environment,
            "lti_config": {
                "valid": lti_config_valid,
                "message": lti_config_message,
                "active_instance": settings.canvas_active_instance,
                "canvas_instances": len(all_instances)
            },
            "endpoints": {
                "lti_login": f"{settings.base_url}/lti/login",
                "lti_launch": f"{settings.base_url}/lti/launch",
                "lti_jwks": f"{settings.base_url}/.well-known/jwks.json"
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "qa-automation-lti",
                "error": str(e)
            }
        )


@app.get("/")
async def root():
    """Root endpoint providing basic API information"""
    return {
        "message": "QA Automation LTI Tool API",
        "version": settings.app_version,
        "environment": settings.environment,
        "lti_ready": bool(settings.canvas_active_instance),
        "endpoints": {
            "health": "/health",
            "docs": "/docs" if settings.environment != "production" else None,
            "lti_config": "/lti/config",
            "lti_login": "/lti/login",
            "lti_launch": "/lti/launch"
        }
    }


@app.get("/lti-info")
async def lti_info():
    """
    Provide LTI integration information for Canvas administrators
    """
    return {
        "tool_name": settings.app_title,
        "tool_description": settings.app_description,
        "lti_version": "1.3",
        "canvas_compatibility": "Canvas LTI 1.3 Advantage",
        "configuration": {
            "target_link_uri": settings.lti_launch_url,
            "oidc_login_uri": settings.lti_login_url,
            "public_jwk_url": settings.lti_jwks_url,
            "custom_fields": {
                "course_id": "$Canvas.course.id",
                "user_id": "$Canvas.user.id",
                "user_roles": "$Canvas.membership.roles"
            }
        },
        "features": [
            "Canvas LTI 1.3 authentication",
            "Course context preservation",
            "Role-based access control",
            "iframe-compatible interface",
            "Session management"
        ],
        "privacy": {
            "data_storage": "Session-based, no permanent storage of Canvas content",
            "permissions": "Read access to course content via Canvas API",
            "compliance": "FERPA compliant session handling"
        }
    }


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info(f"Starting QA Automation LTI Tool v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Base URL: {settings.base_url}")
    
    # Validate configuration using new multi-instance structure
    try:
        canvas_config = settings.get_canvas_instance_config()
        if canvas_config and canvas_config.client_id and canvas_config.private_key:
            logger.info("LTI configuration validated successfully")
            logger.info(f"Active Canvas instance: {settings.canvas_active_instance}")
        else:
            logger.warning("LTI configuration incomplete - some features may not work")
    except Exception as e:
        logger.error(f"LTI configuration validation failed: {str(e)}")
    
    # Log configured Canvas instances
    all_instances = settings.get_all_canvas_instances()
    instance_names = list(all_instances.keys())
    logger.info(f"Configured Canvas instances: {', '.join(instance_names)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Shutting down QA Automation LTI Tool")


# Middleware to log requests (development only)
if settings.environment == "development":
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = datetime.utcnow()
        response = await call_next(request)
        process_time = (datetime.utcnow() - start_time).total_seconds()
        
        logger.debug(
            f"{request.method} {request.url.path} - "
            f"{response.status_code} - {process_time:.3f}s"
        )
        
        return response 