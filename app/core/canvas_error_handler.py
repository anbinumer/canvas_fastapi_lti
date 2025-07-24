"""
Canvas API Error Handler
Story 2.4: Canvas Integration & Testing

Comprehensive error classification, handling, and recovery for Canvas API interactions
in production environment with intelligent retry logic and user-friendly messaging.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
import json

import aiohttp
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CanvasErrorType(Enum):
    """Classification of Canvas API error types."""
    # Transient errors that should be retried
    NETWORK_TIMEOUT = "network_timeout"
    NETWORK_CONNECTION = "network_connection"  
    SERVER_ERROR = "server_error"
    GATEWAY_ERROR = "gateway_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    
    # Rate limiting
    RATE_LIMITED = "rate_limited"
    
    # Authentication and authorization
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    TOKEN_EXPIRED = "token_expired"
    
    # Data and request errors
    NOT_FOUND = "not_found"
    BAD_REQUEST = "bad_request"
    VALIDATION_ERROR = "validation_error"
    CONFLICT = "conflict"
    
    # Canvas-specific errors
    CANVAS_MAINTENANCE = "canvas_maintenance"
    CANVAS_OVERLOADED = "canvas_overloaded"
    CANVAS_FEATURE_DISABLED = "canvas_feature_disabled"
    
    # Unknown/unclassified
    UNKNOWN = "unknown"


class RetryStrategy(Enum):
    """Retry strategies for different error types."""
    NO_RETRY = "no_retry"
    IMMEDIATE_RETRY = "immediate_retry"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    RATE_LIMIT_BACKOFF = "rate_limit_backoff"


@dataclass
class CanvasError:
    """Structured Canvas API error information."""
    error_type: CanvasErrorType
    http_status: Optional[int]
    message: str
    user_message: str
    retry_strategy: RetryStrategy
    retry_after: Optional[int] = None
    max_retries: int = 3
    context: Dict[str, Any] = None
    recoverable: bool = True
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.context is None:
            self.context = {}


@dataclass
class RetryContext:
    """Context for retry operations."""
    attempt: int
    max_attempts: int
    last_error: CanvasError
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: bool = True


class CanvasErrorHandler:
    """
    Production Canvas API error handler with intelligent classification,
    retry logic, and user-friendly error messaging.
    """
    
    def __init__(self):
        self.error_patterns = self._initialize_error_patterns()
        self.retry_configs = self._initialize_retry_configs()
        self.error_stats = {}
        
    def _initialize_error_patterns(self) -> Dict[str, CanvasErrorType]:
        """Initialize error pattern matching for Canvas API responses."""
        return {
            # HTTP status code patterns
            '401': CanvasErrorType.UNAUTHORIZED,
            '403': CanvasErrorType.FORBIDDEN,
            '404': CanvasErrorType.NOT_FOUND,
            '400': CanvasErrorType.BAD_REQUEST,
            '409': CanvasErrorType.CONFLICT,
            '422': CanvasErrorType.VALIDATION_ERROR,
            '429': CanvasErrorType.RATE_LIMITED,
            '500': CanvasErrorType.SERVER_ERROR,
            '502': CanvasErrorType.GATEWAY_ERROR,
            '503': CanvasErrorType.SERVICE_UNAVAILABLE,
            '504': CanvasErrorType.GATEWAY_ERROR,
            
            # Canvas-specific error message patterns
            'maintenance': CanvasErrorType.CANVAS_MAINTENANCE,
            'temporarily unavailable': CanvasErrorType.SERVICE_UNAVAILABLE,
            'rate limit': CanvasErrorType.RATE_LIMITED,
            'token expired': CanvasErrorType.TOKEN_EXPIRED,
            'invalid token': CanvasErrorType.UNAUTHORIZED,
            'insufficient privileges': CanvasErrorType.FORBIDDEN,
            'feature not enabled': CanvasErrorType.CANVAS_FEATURE_DISABLED,
            'overloaded': CanvasErrorType.CANVAS_OVERLOADED,
            
            # Network error patterns
            'timeout': CanvasErrorType.NETWORK_TIMEOUT,
            'connection': CanvasErrorType.NETWORK_CONNECTION,
            'dns': CanvasErrorType.NETWORK_CONNECTION,
        }
    
    def _initialize_retry_configs(self) -> Dict[CanvasErrorType, Dict]:
        """Initialize retry configurations for different error types."""
        return {
            # Transient errors - retry with exponential backoff
            CanvasErrorType.NETWORK_TIMEOUT: {
                'strategy': RetryStrategy.EXPONENTIAL_BACKOFF,
                'max_retries': 5,
                'base_delay': 2.0,
                'max_delay': 60.0
            },
            CanvasErrorType.NETWORK_CONNECTION: {
                'strategy': RetryStrategy.EXPONENTIAL_BACKOFF,
                'max_retries': 3,
                'base_delay': 1.0,
                'max_delay': 30.0
            },
            CanvasErrorType.SERVER_ERROR: {
                'strategy': RetryStrategy.EXPONENTIAL_BACKOFF,
                'max_retries': 3,
                'base_delay': 5.0,
                'max_delay': 120.0
            },
            CanvasErrorType.GATEWAY_ERROR: {
                'strategy': RetryStrategy.LINEAR_BACKOFF,
                'max_retries': 3,
                'base_delay': 10.0,
                'max_delay': 60.0
            },
            CanvasErrorType.SERVICE_UNAVAILABLE: {
                'strategy': RetryStrategy.EXPONENTIAL_BACKOFF,
                'max_retries': 5,
                'base_delay': 30.0,
                'max_delay': 300.0
            },
            
            # Rate limiting - special handling
            CanvasErrorType.RATE_LIMITED: {
                'strategy': RetryStrategy.RATE_LIMIT_BACKOFF,
                'max_retries': 10,
                'base_delay': 60.0,
                'max_delay': 900.0
            },
            
            # Canvas-specific issues
            CanvasErrorType.CANVAS_MAINTENANCE: {
                'strategy': RetryStrategy.LINEAR_BACKOFF,
                'max_retries': 3,
                'base_delay': 300.0,  # 5 minutes
                'max_delay': 1800.0   # 30 minutes
            },
            CanvasErrorType.CANVAS_OVERLOADED: {
                'strategy': RetryStrategy.EXPONENTIAL_BACKOFF,
                'max_retries': 5,
                'base_delay': 60.0,
                'max_delay': 600.0
            },
            
            # No retry scenarios
            CanvasErrorType.UNAUTHORIZED: {
                'strategy': RetryStrategy.NO_RETRY,
                'max_retries': 0
            },
            CanvasErrorType.FORBIDDEN: {
                'strategy': RetryStrategy.NO_RETRY,
                'max_retries': 0
            },
            CanvasErrorType.NOT_FOUND: {
                'strategy': RetryStrategy.NO_RETRY,
                'max_retries': 0
            },
            CanvasErrorType.BAD_REQUEST: {
                'strategy': RetryStrategy.NO_RETRY,
                'max_retries': 0
            },
            CanvasErrorType.VALIDATION_ERROR: {
                'strategy': RetryStrategy.NO_RETRY,
                'max_retries': 0
            },
            CanvasErrorType.CANVAS_FEATURE_DISABLED: {
                'strategy': RetryStrategy.NO_RETRY,
                'max_retries': 0
            },
            
            # Token expired - special case (might need re-authentication)
            CanvasErrorType.TOKEN_EXPIRED: {
                'strategy': RetryStrategy.IMMEDIATE_RETRY,
                'max_retries': 1  # One retry after token refresh
            }
        }
    
    def classify_error(
        self, 
        response: Optional[aiohttp.ClientResponse] = None,
        exception: Optional[Exception] = None,
        context: Optional[Dict] = None
    ) -> CanvasError:
        """
        Classify a Canvas API error and determine appropriate handling.
        
        Args:
            response: HTTP response from Canvas API
            exception: Exception that occurred
            context: Additional context information
            
        Returns:
            CanvasError with classification and handling information
        """
        context = context or {}
        
        if response is not None:
            return self._classify_http_error(response, context)
        elif exception is not None:
            return self._classify_exception_error(exception, context)
        else:
            return self._create_unknown_error(context)
    
    def _classify_http_error(self, response: aiohttp.ClientResponse, context: Dict) -> CanvasError:
        """Classify HTTP response errors from Canvas API."""
        status_code = response.status
        
        # Try to get response text for additional context
        response_text = ""
        error_details = {}
        
        try:
            if hasattr(response, '_body') and response._body:
                response_text = response._body.decode('utf-8', errors='ignore')
                try:
                    error_details = json.loads(response_text)
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass
        
        # Classify based on status code first
        error_type = self._get_error_type_from_status(status_code)
        
        # Refine classification based on response content
        if response_text:
            error_type = self._refine_error_type_from_content(error_type, response_text.lower())
        
        # Get retry configuration
        retry_config = self.retry_configs.get(error_type, {})
        
        # Create error messages
        technical_message = f"Canvas API {status_code}: {response_text[:200]}"
        user_message = self._create_user_message(error_type, status_code, error_details)
        
        # Extract retry-after header for rate limiting
        retry_after = None
        if error_type == CanvasErrorType.RATE_LIMITED:
            retry_after = self._extract_retry_after(response)
        
        return CanvasError(
            error_type=error_type,
            http_status=status_code,
            message=technical_message,
            user_message=user_message,
            retry_strategy=retry_config.get('strategy', RetryStrategy.NO_RETRY),
            retry_after=retry_after,
            max_retries=retry_config.get('max_retries', 0),
            context={**context, 'response_details': error_details},
            recoverable=self._is_recoverable(error_type)
        )
    
    def _classify_exception_error(self, exception: Exception, context: Dict) -> CanvasError:
        """Classify exception-based errors."""
        exception_type = type(exception).__name__
        exception_message = str(exception).lower()
        
        # Map exception types to Canvas error types
        if isinstance(exception, asyncio.TimeoutError):
            error_type = CanvasErrorType.NETWORK_TIMEOUT
        elif isinstance(exception, aiohttp.ClientConnectorError):
            error_type = CanvasErrorType.NETWORK_CONNECTION
        elif isinstance(exception, aiohttp.ClientTimeout):
            error_type = CanvasErrorType.NETWORK_TIMEOUT
        elif 'ssl' in exception_message or 'certificate' in exception_message:
            error_type = CanvasErrorType.NETWORK_CONNECTION
        else:
            # Check message patterns
            error_type = CanvasErrorType.UNKNOWN
            for pattern, pattern_type in self.error_patterns.items():
                if pattern in exception_message:
                    error_type = pattern_type
                    break
        
        retry_config = self.retry_configs.get(error_type, {})
        
        technical_message = f"{exception_type}: {str(exception)}"
        user_message = self._create_user_message(error_type, None, {'exception': exception_type})
        
        return CanvasError(
            error_type=error_type,
            http_status=None,
            message=technical_message,
            user_message=user_message,
            retry_strategy=retry_config.get('strategy', RetryStrategy.EXPONENTIAL_BACKOFF),
            max_retries=retry_config.get('max_retries', 3),
            context={**context, 'exception_type': exception_type},
            recoverable=True  # Most exceptions are recoverable
        )
    
    def _get_error_type_from_status(self, status_code: int) -> CanvasErrorType:
        """Get error type from HTTP status code."""
        status_str = str(status_code)
        return self.error_patterns.get(status_str, CanvasErrorType.UNKNOWN)
    
    def _refine_error_type_from_content(self, initial_type: CanvasErrorType, content: str) -> CanvasErrorType:
        """Refine error type based on response content."""
        for pattern, pattern_type in self.error_patterns.items():
            if isinstance(pattern, str) and pattern in content:
                # Content patterns override status code patterns
                if pattern_type != initial_type and len(pattern) > 3:  # Ignore short patterns
                    return pattern_type
        
        return initial_type
    
    def _extract_retry_after(self, response: aiohttp.ClientResponse) -> Optional[int]:
        """Extract retry-after header from response."""
        retry_after_header = response.headers.get('Retry-After')
        if retry_after_header:
            try:
                return int(retry_after_header)
            except ValueError:
                # Might be an HTTP date, convert to seconds
                try:
                    from email.utils import parsedate_to_datetime
                    retry_date = parsedate_to_datetime(retry_after_header)
                    return max(0, int((retry_date - datetime.utcnow()).total_seconds()))
                except Exception:
                    pass
        
        return None
    
    def _create_user_message(
        self, 
        error_type: CanvasErrorType, 
        status_code: Optional[int], 
        details: Dict
    ) -> str:
        """Create user-friendly error messages."""
        user_messages = {
            CanvasErrorType.NETWORK_TIMEOUT: "Connection to Canvas timed out. Please try again in a few moments.",
            CanvasErrorType.NETWORK_CONNECTION: "Unable to connect to Canvas. Please check your internet connection and try again.",
            CanvasErrorType.SERVER_ERROR: "Canvas is experiencing technical difficulties. Please try again in a few minutes.",
            CanvasErrorType.GATEWAY_ERROR: "Canvas servers are temporarily unavailable. Please try again shortly.",
            CanvasErrorType.SERVICE_UNAVAILABLE: "Canvas is temporarily unavailable for maintenance. Please try again later.",
            CanvasErrorType.RATE_LIMITED: "Too many requests to Canvas. Please wait a moment before trying again.",
            CanvasErrorType.UNAUTHORIZED: "Authentication failed. Please refresh the page and try again.",
            CanvasErrorType.FORBIDDEN: "You don't have permission to perform this action in Canvas.",
            CanvasErrorType.NOT_FOUND: "The requested Canvas content could not be found.",
            CanvasErrorType.BAD_REQUEST: "Invalid request to Canvas. Please check your input and try again.",
            CanvasErrorType.VALIDATION_ERROR: "Canvas rejected the request due to validation errors.",
            CanvasErrorType.CONFLICT: "Conflict with existing Canvas data. Please refresh and try again.",
            CanvasErrorType.CANVAS_MAINTENANCE: "Canvas is currently undergoing maintenance. Please try again later.",
            CanvasErrorType.CANVAS_OVERLOADED: "Canvas is experiencing high load. Please try again in a few minutes.",
            CanvasErrorType.CANVAS_FEATURE_DISABLED: "This Canvas feature is not enabled for your institution.",
            CanvasErrorType.TOKEN_EXPIRED: "Your Canvas session has expired. Please refresh the page.",
            CanvasErrorType.UNKNOWN: "An unexpected error occurred while communicating with Canvas."
        }
        
        base_message = user_messages.get(error_type, user_messages[CanvasErrorType.UNKNOWN])
        
        # Add specific details for certain error types
        if error_type == CanvasErrorType.RATE_LIMITED and 'retry_after' in details:
            retry_after = details['retry_after']
            base_message += f" Please wait {retry_after} seconds before trying again."
        
        return base_message
    
    def _is_recoverable(self, error_type: CanvasErrorType) -> bool:
        """Determine if an error type is recoverable."""
        non_recoverable = {
            CanvasErrorType.FORBIDDEN,
            CanvasErrorType.NOT_FOUND,
            CanvasErrorType.BAD_REQUEST,
            CanvasErrorType.VALIDATION_ERROR,
            CanvasErrorType.CANVAS_FEATURE_DISABLED
        }
        
        return error_type not in non_recoverable
    
    def _create_unknown_error(self, context: Dict) -> CanvasError:
        """Create error for unknown/unclassified issues."""
        return CanvasError(
            error_type=CanvasErrorType.UNKNOWN,
            http_status=None,
            message="Unknown Canvas API error",
            user_message="An unexpected error occurred. Please try again.",
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_retries=2,
            context=context,
            recoverable=True
        )
    
    async def calculate_retry_delay(self, retry_context: RetryContext) -> float:
        """Calculate delay for retry based on strategy and context."""
        error_config = self.retry_configs.get(retry_context.last_error.error_type, {})
        strategy = retry_context.last_error.retry_strategy
        
        base_delay = error_config.get('base_delay', retry_context.base_delay)
        max_delay = error_config.get('max_delay', retry_context.max_delay)
        
        if strategy == RetryStrategy.NO_RETRY:
            return 0
        
        elif strategy == RetryStrategy.IMMEDIATE_RETRY:
            return 0.1  # Small delay to avoid immediate hammering
        
        elif strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = base_delay * retry_context.attempt
            
        elif strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = base_delay * (2 ** (retry_context.attempt - 1))
            
        elif strategy == RetryStrategy.RATE_LIMIT_BACKOFF:
            # Use retry-after header if available, otherwise exponential backoff
            if retry_context.last_error.retry_after:
                delay = retry_context.last_error.retry_after
            else:
                delay = base_delay * (1.5 ** (retry_context.attempt - 1))
        
        else:
            delay = base_delay
        
        # Apply jitter to avoid thundering herd
        if retry_context.jitter:
            import random
            delay = delay * (0.5 + 0.5 * random.random())
        
        return min(delay, max_delay)
    
    def should_retry(self, error: CanvasError, attempt: int) -> bool:
        """Determine if an error should be retried."""
        if error.retry_strategy == RetryStrategy.NO_RETRY:
            return False
        
        return attempt <= error.max_retries
    
    def log_error(self, error: CanvasError, context: Optional[Dict] = None):
        """Log Canvas API error with appropriate level and context."""
        log_context = {
            'error_type': error.error_type.value,
            'http_status': error.http_status,
            'recoverable': error.recoverable,
            'retry_strategy': error.retry_strategy.value,
            'timestamp': error.timestamp.isoformat(),
            **(context or {}),
            **error.context
        }
        
        # Choose log level based on error severity
        if error.error_type in [CanvasErrorType.SERVER_ERROR, CanvasErrorType.CANVAS_MAINTENANCE]:
            logger.error(f"Canvas API Error: {error.message}", extra=log_context)
        elif error.error_type in [CanvasErrorType.RATE_LIMITED, CanvasErrorType.NETWORK_TIMEOUT]:
            logger.warning(f"Canvas API Warning: {error.message}", extra=log_context)
        elif error.recoverable:
            logger.info(f"Canvas API Info: {error.message}", extra=log_context)
        else:
            logger.error(f"Canvas API Non-recoverable: {error.message}", extra=log_context)
        
        # Update error statistics
        self._update_error_stats(error)
    
    def _update_error_stats(self, error: CanvasError):
        """Update error statistics for monitoring."""
        error_key = error.error_type.value
        
        if error_key not in self.error_stats:
            self.error_stats[error_key] = {
                'count': 0,
                'first_seen': error.timestamp,
                'last_seen': error.timestamp,
                'recoverable_count': 0,
                'non_recoverable_count': 0
            }
        
        stats = self.error_stats[error_key]
        stats['count'] += 1
        stats['last_seen'] = error.timestamp
        
        if error.recoverable:
            stats['recoverable_count'] += 1
        else:
            stats['non_recoverable_count'] += 1
    
    def get_error_statistics(self) -> Dict:
        """Get error statistics for monitoring and analysis."""
        return {
            'error_stats': self.error_stats,
            'total_errors': sum(stats['count'] for stats in self.error_stats.values()),
            'error_types': list(self.error_stats.keys()),
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def reset_error_statistics(self):
        """Reset error statistics (for testing or maintenance)."""
        self.error_stats.clear()
        logger.info("Canvas error statistics reset")


# Global error handler instance
_error_handler: Optional[CanvasErrorHandler] = None


def get_canvas_error_handler() -> CanvasErrorHandler:
    """Get or create global Canvas error handler instance."""
    global _error_handler
    
    if _error_handler is None:
        _error_handler = CanvasErrorHandler()
        logger.info("Created global Canvas error handler instance")
    
    return _error_handler


def classify_canvas_error(
    response: Optional[aiohttp.ClientResponse] = None,
    exception: Optional[Exception] = None,
    context: Optional[Dict] = None
) -> CanvasError:
    """Convenience function for classifying Canvas API errors."""
    handler = get_canvas_error_handler()
    return handler.classify_error(response, exception, context) 