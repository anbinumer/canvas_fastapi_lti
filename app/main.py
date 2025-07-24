"""
QA Automation LTI Tool - FastAPI Application Entry Point

This is the main FastAPI application for the Canvas LTI QA Automation Tool.
Designed for AI-assisted development and Canvas LTI 1.3 integration.
"""

from fastapi import FastAPI
from datetime import datetime

# Router imports (placeholder for future implementation)
# from app.api.routes import lti, qa_tasks, canvas, websockets

# Initialize FastAPI app
app = FastAPI(
    title="QA Automation LTI Tool",
    description="Canvas LTI 1.3 QA Automation Tool for Learning Designers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# TODO: Register routers when implemented
# app.include_router(lti.router, prefix="/lti", tags=["LTI"])
# app.include_router(qa_tasks.router, prefix="/api/v1/qa", tags=["QA Tasks"])
# app.include_router(canvas.router, prefix="/api/v1/canvas", tags=["Canvas"])
# app.include_router(websockets.router, prefix="/ws", tags=["WebSocket"])

# Basic health check endpoint for Railway monitoring
@app.get("/health")
async def health_check():
    """
    Railway health check endpoint
    Returns 200 status with timestamp for deployment monitoring
    """
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "service": "qa-automation-lti"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint providing basic API information"""
    return {
        "message": "QA Automation LTI Tool API",
        "docs": "/docs",
        "health": "/health"
    } 