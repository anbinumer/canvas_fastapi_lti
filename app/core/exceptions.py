"""
Custom exception handlers for QA Automation LTI Tool
"""

from fastapi import HTTPException
from typing import Optional, Dict, Any


class QAAutomationException(Exception):
    """Base exception for QA Automation tool"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class LTIAuthenticationError(QAAutomationException):
    """LTI authentication failed"""
    
    def __init__(self, message: str = "LTI authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class LTIValidationError(QAAutomationException):
    """LTI message validation failed"""
    
    def __init__(self, message: str = "LTI message validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class SessionError(QAAutomationException):
    """Session management error"""
    
    def __init__(self, message: str = "Session error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class CanvasAPIError(QAAutomationException):
    """Canvas API interaction error"""
    
    def __init__(self, message: str = "Canvas API error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class QATaskError(QAAutomationException):
    """QA task execution error"""
    
    def __init__(self, message: str = "QA task error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class ConfigurationError(QAAutomationException):
    """Application configuration error"""
    
    def __init__(self, message: str = "Configuration error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


# HTTP Exception Classes for FastAPI
class LTIHTTPException(HTTPException):
    """Base HTTP exception for LTI-related errors"""
    
    def __init__(self, status_code: int = 400, detail: str = "LTI error", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class LTIAuthenticationHTTPException(LTIHTTPException):
    """HTTP exception for LTI authentication failures"""
    
    def __init__(self, detail: str = "LTI authentication failed", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=401, detail=detail, headers=headers)


class LTIValidationHTTPException(LTIHTTPException):
    """HTTP exception for LTI validation failures"""
    
    def __init__(self, detail: str = "LTI message validation failed", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=400, detail=detail, headers=headers)


class SessionHTTPException(LTIHTTPException):
    """HTTP exception for session-related errors"""
    
    def __init__(self, detail: str = "Session error", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=401, detail=detail, headers=headers)


class CanvasAPIHTTPException(LTIHTTPException):
    """HTTP exception for Canvas API errors"""
    
    def __init__(self, status_code: int = 502, detail: str = "Canvas API error", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers) 