"""
Canvas API proxy endpoints
"""

from fastapi import APIRouter

# Canvas API proxy endpoints will be implemented in Epic 2
router = APIRouter()

# Placeholder endpoint
@router.get("/status")
async def canvas_status():
    """Canvas API status - placeholder endpoint"""
    return {"status": "Canvas API endpoints coming in Epic 2"} 