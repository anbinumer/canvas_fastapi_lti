"""
Test health check endpoint functionality
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint returns 200 status"""
    response = client.get("/health")
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "qa-automation-lti"
    assert "timestamp" in data


def test_root_endpoint():
    """Test root endpoint returns basic API information"""
    response = client.get("/")
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["message"] == "QA Automation LTI Tool API"
    assert data["docs"] == "/docs"
    assert data["health"] == "/health" 