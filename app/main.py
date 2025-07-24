"""
QA Automation LTI Tool - Simplified FastAPI Application for Railway Testing
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
from app.api.routes.lti import router as lti_router

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="QA Automation LTI Tool",
    description="Canvas LTI 1.3 QA Automation Tool",
    version="2.4.0"
)

app.include_router(lti_router)

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
            "lti_login": "/lti/login",
            "lti_launch": "/lti/launch (GET/POST)",
            "lti_deep_linking": "/lti/deep-linking (GET/POST)",
            "privacy_policy": "/privacy-policy",
            "terms_of_service": "/terms-of-service",
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
            "redirect_uris": [
                "https://canvasfastapilti-test.up.railway.app/lti/launch",
                "https://canvasfastapilti-test.up.railway.app/lti/deep-linking"
            ],
            "privacy_policy_url": "https://canvasfastapilti-test.up.railway.app/privacy-policy",
            "terms_of_service_url": "https://canvasfastapilti-test.up.railway.app/terms-of-service",
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
            "Session management",
            "Deep linking support",
            "Multi-method endpoint support (GET/POST)"
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

@app.get("/privacy-policy")
async def privacy_policy():
    """Privacy policy endpoint"""
    return {
        "tool": "QA Automation LTI Tool", 
        "privacy_policy": "This tool accesses Canvas content for QA automation purposes only. No personal data is stored permanently.",
        "data_usage": "Session-based processing only",
        "compliance": "FERPA compliant"
    }

@app.get("/terms-of-service")
async def terms_of_service():
    """Terms of service endpoint"""
    return {
        "tool": "QA Automation LTI Tool",
        "terms": "This tool is provided for educational QA automation purposes.",
        "usage": "Authorized educational use only",
        "version": "2.4.0"
    }

@app.get("/debug/routes")
async def debug_routes():
    return [{"path": route.path, "methods": list(route.methods)} for route in app.routes]

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("🚀 Starting QA Automation LTI Tool v2.4.0 (Simplified for Railway)")
    logger.info("✅ Essential LTI endpoints available for Canvas integration")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Shutting down QA Automation LTI Tool") 