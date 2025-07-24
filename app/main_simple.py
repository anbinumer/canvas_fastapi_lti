"""
QA Automation LTI Tool - Simplified FastAPI Application for Railway Testing
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="QA Automation LTI Tool",
    description="Canvas LTI 1.3 QA Automation Tool",
    version="2.4.0"
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "QA Automation LTI Tool API",
        "version": "2.4.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "health": "/health",
            "lti_info": "/lti-info",
            "jwks": "/.well-known/jwks.json",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "qa-automation-lti",
        "version": "2.4.0",
        "message": "Simplified version for Railway deployment testing"
    }

@app.get("/lti-info")
async def lti_info():
    """LTI integration information for Canvas administrators"""
    return {
        "tool_name": "QA Automation LTI Tool",
        "tool_description": "Canvas LTI 1.3 QA Automation Tool",
        "lti_version": "1.3",
        "canvas_compatibility": "Canvas LTI 1.3 Advantage",
        "configuration": {
            "target_link_uri": "https://canvasfastapilti-test.up.railway.app/lti/launch",
            "oidc_login_uri": "https://canvasfastapilti-test.up.railway.app/lti/login",
            "public_jwk_url": "https://canvasfastapilti-test.up.railway.app/.well-known/jwks.json",
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
        "status": "Configuration endpoints available - full LTI implementation in progress"
    }

@app.get("/.well-known/jwks.json")
async def jwks():
    """JWKS endpoint for LTI 1.3 authentication"""
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": "lti-key-1",
                "note": "Placeholder JWKS for Canvas Developer Key setup"
            }
        ]
    }

@app.get("/lti/login")
async def lti_login():
    """LTI login endpoint placeholder"""
    return {"message": "LTI login endpoint - implementation in progress"}

@app.get("/lti/launch")
async def lti_launch():
    """LTI launch endpoint placeholder"""
    return {"message": "LTI launch endpoint - implementation in progress"}

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("🚀 Starting QA Automation LTI Tool v2.4.0 (Simplified for Railway)")
    logger.info("✅ Essential LTI endpoints available for Canvas integration")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Shutting down QA Automation LTI Tool") 