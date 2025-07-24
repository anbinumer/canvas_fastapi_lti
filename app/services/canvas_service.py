"""
Enhanced Canvas Service with Production Rate Limiting and Error Handling
Story 2.4: Canvas Integration & Testing

Production-ready Canvas API service with comprehensive rate limiting,
error handling, retry logic, and performance optimizations.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
import json
import time

import aiohttp
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.core.rate_limiter import (
    get_rate_limiter, 
    ProductionCanvasRateLimiter,
    RateLimitStatus,
    wait_for_canvas_availability
)
from app.core.canvas_error_handler import (
    get_canvas_error_handler,
    CanvasErrorHandler,
    CanvasError,
    CanvasErrorType,
    RetryContext,
    RetryStrategy,
    classify_canvas_error
)

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class CanvasContent:
    """Structured Canvas content representation."""
    content_id: str
    content_type: str
    title: str
    content: str
    url: Optional[str] = None
    published: bool = True
    last_modified: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class BatchResult:
    """Result of batch Canvas API operations."""
    successful: List[Any]
    failed: List[Tuple[Any, CanvasError]]
    total_processed: int
    execution_time: float
    api_calls_made: int


class ProductionCanvasService:
    """
    Production-ready Canvas API service with comprehensive error handling,
    rate limiting, and performance optimizations for Story 2.4.
    """
    
    def __init__(self, 
                 base_url: str,
                 access_token: str,
                 user_id: Optional[str] = None,
                 session: Optional[aiohttp.ClientSession] = None):
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self.user_id = user_id or "default"
        self.session = session
        self._should_close_session = session is None
        
        # Production components
        self.rate_limiter: Optional[ProductionCanvasRateLimiter] = None
        self.error_handler: Optional[CanvasErrorHandler] = None
        
        # Performance tracking
        self.api_call_count = 0
        self.total_response_time = 0.0
        self.error_count = 0
        
        # Request batching configuration
        self.max_batch_size = 50
        self.concurrent_requests = 5
        self.request_timeout = 30
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def initialize(self):
        """Initialize production components and session."""
        if self.session is None:
            # Create session with production settings
            timeout = aiohttp.ClientTimeout(total=self.request_timeout)
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool size
                limit_per_host=20,  # Per-host connection limit
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'ACU-QA-Automation/1.0'
                }
            )
        
        # Initialize production components
        self.rate_limiter = await get_rate_limiter()
        self.error_handler = get_canvas_error_handler()
        
        logger.info(f"Canvas service initialized for user {self.user_id}")
    
    async def close(self):
        """Clean up resources."""
        if self.session and self._should_close_session:
            await self.session.close()
            self.session = None
        
        logger.info(f"Canvas service closed for user {self.user_id}")
    
    async def _make_request(self,
                           endpoint: str,
                           method: str = 'GET',
                           params: Optional[Dict] = None,
                           data: Optional[Dict] = None,
                           paginated: bool = True,
                           max_retries: int = 3) -> Union[Dict, List[Dict]]:
        """
        Make a Canvas API request with production-grade error handling and rate limiting.
        
        Args:
            endpoint: Canvas API endpoint (relative to base URL)
            method: HTTP method
            params: Query parameters
            data: Request body data
            paginated: Whether to handle pagination automatically
            max_retries: Maximum retry attempts
            
        Returns:
            API response data (single object or list for paginated results)
        """
        if not self.session:
            await self.initialize()
        
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"
        
        # Extract endpoint type for rate limiting
        endpoint_type = self._extract_endpoint_type(endpoint)
        
        # Wait for rate limit availability
        rate_limit_ok = await wait_for_canvas_availability(
            self.user_id, 
            endpoint_type, 
            weight=1, 
            max_wait=300
        )
        
        if not rate_limit_ok:
            raise Exception("Rate limit exceeded - unable to proceed")
        
        start_time = time.time()
        attempt = 0
        last_error = None
        
        while attempt < max_retries:
            attempt += 1
            
            try:
                # Make the actual request
                async with self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data if method != 'GET' else None
                ) as response:
                    
                    # Update performance metrics
                    self.api_call_count += 1
                    response_time = time.time() - start_time
                    self.total_response_time += response_time
                    
                    # Handle successful responses
                    if response.status == 200:
                        if paginated and method == 'GET':
                            return await self._handle_paginated_response(response, url, params)
                        else:
                            return await response.json()
                    
                    # Handle error responses
                    canvas_error = classify_canvas_error(
                        response=response,
                        context={
                            'endpoint': endpoint,
                            'method': method,
                            'attempt': attempt,
                            'user_id': self.user_id
                        }
                    )
                    
                    # Log the error
                    self.error_handler.log_error(canvas_error, {
                        'url': url,
                        'params': params
                    })
                    
                    self.error_count += 1
                    last_error = canvas_error
                    
                    # Check if we should retry
                    if not self.error_handler.should_retry(canvas_error, attempt):
                        break
                    
                    # Calculate retry delay
                    retry_context = RetryContext(
                        attempt=attempt,
                        max_attempts=max_retries,
                        last_error=canvas_error
                    )
                    
                    delay = await self.error_handler.calculate_retry_delay(retry_context)
                    if delay > 0:
                        logger.info(f"Retrying Canvas request after {delay:.2f}s (attempt {attempt})")
                        await asyncio.sleep(delay)
            
            except Exception as e:
                # Handle connection and other exceptions
                canvas_error = classify_canvas_error(
                    exception=e,
                    context={
                        'endpoint': endpoint,
                        'method': method,
                        'attempt': attempt,
                        'user_id': self.user_id
                    }
                )
                
                self.error_handler.log_error(canvas_error)
                self.error_count += 1
                last_error = canvas_error
                
                # Check if we should retry
                if not self.error_handler.should_retry(canvas_error, attempt):
                    break
                
                # Calculate retry delay
                retry_context = RetryContext(
                    attempt=attempt,
                    max_attempts=max_retries,
                    last_error=canvas_error
                )
                
                delay = await self.error_handler.calculate_retry_delay(retry_context)
                if delay > 0:
                    logger.info(f"Retrying Canvas request after {delay:.2f}s (attempt {attempt})")
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        if last_error:
            logger.error(f"Canvas API request failed after {attempt} attempts: {last_error.message}")
            raise Exception(f"Canvas API error: {last_error.user_message}")
        else:
            raise Exception("Canvas API request failed with unknown error")
    
    async def _handle_paginated_response(self,
                                       response: aiohttp.ClientResponse,
                                       url: str,
                                       params: Optional[Dict]) -> List[Dict]:
        """Handle paginated Canvas API responses efficiently."""
        all_results = []
        current_response = response
        current_params = params or {}
        
        while True:
            # Parse current page
            data = await current_response.json()
            if isinstance(data, list):
                all_results.extend(data)
            else:
                all_results.append(data)
            
            # Check for next page
            link_header = current_response.headers.get('Link', '')
            next_url = self._extract_next_page_url(link_header)
            
            if not next_url:
                break
            
            # Wait for rate limit before next page
            rate_limit_ok = await wait_for_canvas_availability(
                self.user_id, 
                'pagination', 
                weight=1, 
                max_wait=60
            )
            
            if not rate_limit_ok:
                logger.warning("Rate limit hit during pagination - returning partial results")
                break
            
            # Fetch next page
            try:
                async with self.session.get(next_url) as next_response:
                    self.api_call_count += 1
                    
                    if next_response.status != 200:
                        logger.warning(f"Pagination failed with status {next_response.status}")
                        break
                    
                    current_response = next_response
            except Exception as e:
                logger.warning(f"Pagination request failed: {e}")
                break
        
        logger.debug(f"Paginated request completed with {len(all_results)} total items")
        return all_results
    
    def _extract_endpoint_type(self, endpoint: str) -> str:
        """Extract endpoint type for rate limiting classification."""
        endpoint_lower = endpoint.lower()
        
        if 'course' in endpoint_lower:
            return 'courses'
        elif 'assignment' in endpoint_lower:
            return 'assignments'
        elif 'page' in endpoint_lower:
            return 'pages'
        elif 'quiz' in endpoint_lower:
            return 'quizzes'
        elif 'discussion' in endpoint_lower:
            return 'discussions'
        elif 'module' in endpoint_lower:
            return 'modules'
        elif 'file' in endpoint_lower:
            return 'files'
        elif 'submission' in endpoint_lower:
            return 'submissions'
        else:
            return 'default'
    
    def _extract_next_page_url(self, link_header: str) -> Optional[str]:
        """Extract next page URL from Link header."""
        if not link_header:
            return None
        
        # Parse Link header format: <url>; rel="next"
        links = link_header.split(',')
        for link in links:
            parts = link.strip().split(';')
            if len(parts) >= 2:
                url_part = parts[0].strip()
                rel_part = parts[1].strip()
                
                if 'rel="next"' in rel_part and url_part.startswith('<') and url_part.endswith('>'):
                    return url_part[1:-1]  # Remove < and >
        
        return None
    
    async def get_course_content_batch(self,
                                     course_id: str,
                                     content_types: List[str] = None,
                                     batch_size: int = None) -> List[CanvasContent]:
        """
        Get course content in optimized batches for performance.
        
        Args:
            course_id: Canvas course ID
            content_types: List of content types to fetch
            batch_size: Batch size for requests
            
        Returns:
            List of CanvasContent objects
        """
        if content_types is None:
            content_types = ['pages', 'assignments', 'quizzes', 'discussions', 'modules']
        
        if batch_size is None:
            batch_size = await self.rate_limiter.get_optimal_batch_size(self.user_id)
        
        all_content = []
        
        # Create tasks for parallel fetching
        tasks = []
        for content_type in content_types:
            task = self._fetch_content_type(course_id, content_type)
            tasks.append(task)
        
        # Execute tasks with concurrency limit
        semaphore = asyncio.Semaphore(self.concurrent_requests)
        
        async def bounded_fetch(task):
            async with semaphore:
                return await task
        
        bounded_tasks = [bounded_fetch(task) for task in tasks]
        results = await asyncio.gather(*bounded_tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {content_types[i]}: {result}")
            else:
                all_content.extend(result)
        
        logger.info(f"Fetched {len(all_content)} content items for course {course_id}")
        return all_content
    
    async def _fetch_content_type(self, course_id: str, content_type: str) -> List[CanvasContent]:
        """Fetch a specific content type with error handling."""
        try:
            endpoint = f"courses/{course_id}/{content_type}"
            
            # Special handling for different content types
            if content_type == 'pages':
                data = await self._make_request(endpoint, params={'include': ['body']})
            elif content_type == 'assignments':
                data = await self._make_request(endpoint, params={'include': ['description']})
            elif content_type == 'quizzes':
                data = await self._make_request(endpoint, params={'include': ['description']})
            elif content_type == 'discussions':
                data = await self._make_request(f"courses/{course_id}/discussion_topics")
            else:
                data = await self._make_request(endpoint)
            
            return self._convert_to_canvas_content(data, content_type)
            
        except Exception as e:
            logger.error(f"Failed to fetch {content_type} for course {course_id}: {e}")
            return []
    
    def _convert_to_canvas_content(self, data: List[Dict], content_type: str) -> List[CanvasContent]:
        """Convert Canvas API data to CanvasContent objects."""
        content_list = []
        
        for item in data:
            try:
                # Extract content based on type
                if content_type == 'pages':
                    content = item.get('body', '')
                    title = item.get('title', 'Untitled Page')
                elif content_type == 'assignments':
                    content = item.get('description', '')
                    title = item.get('name', 'Untitled Assignment')
                elif content_type == 'quizzes':
                    content = item.get('description', '')
                    title = item.get('title', 'Untitled Quiz')
                elif content_type == 'discussions':
                    content = item.get('message', '')
                    title = item.get('title', 'Untitled Discussion')
                else:
                    content = str(item.get('description', ''))
                    title = item.get('name', item.get('title', 'Untitled'))
                
                canvas_content = CanvasContent(
                    content_id=str(item.get('id', '')),
                    content_type=content_type.rstrip('s'),  # Remove plural
                    title=title,
                    content=content or '',
                    url=item.get('html_url'),
                    published=item.get('published', True),
                    last_modified=self._parse_date(item.get('updated_at')),
                    metadata=item
                )
                
                content_list.append(canvas_content)
                
            except Exception as e:
                logger.warning(f"Failed to convert {content_type} item to CanvasContent: {e}")
                continue
        
        return content_list
    
    def _parse_date(self, date_string: Optional[str]) -> Optional[datetime]:
        """Parse Canvas date string to datetime."""
        if not date_string:
            return None
        
        try:
            # Canvas uses ISO format: 2023-12-01T10:00:00Z
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        except Exception:
            return None
    
    async def update_content_batch(self,
                                 course_id: str,
                                 updates: List[Tuple[str, str, str]],
                                 batch_size: int = None) -> BatchResult:
        """
        Update multiple content items in optimized batches.
        
        Args:
            course_id: Canvas course ID
            updates: List of (content_type, content_id, new_content) tuples
            batch_size: Batch size for updates
            
        Returns:
            BatchResult with success/failure information
        """
        if batch_size is None:
            batch_size = await self.rate_limiter.get_optimal_batch_size(self.user_id)
        
        start_time = time.time()
        successful = []
        failed = []
        api_calls = 0
        
        # Process updates in batches
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            
            # Create tasks for this batch
            tasks = []
            for content_type, content_id, new_content in batch:
                task = self._update_single_content(course_id, content_type, content_id, new_content)
                tasks.append((task, (content_type, content_id, new_content)))
            
            # Execute batch with concurrency limit
            semaphore = asyncio.Semaphore(min(len(tasks), self.concurrent_requests))
            
            async def bounded_update(task_tuple):
                task, original_data = task_tuple
                async with semaphore:
                    return await task, original_data
            
            bounded_tasks = [bounded_update(task_tuple) for task_tuple in tasks]
            batch_results = await asyncio.gather(*bounded_tasks, return_exceptions=True)
            
            # Process batch results
            for result in batch_results:
                api_calls += 1
                
                if isinstance(result, Exception):
                    # Task itself failed
                    failed.append((None, classify_canvas_error(exception=result)))
                else:
                    try:
                        (update_result, original_data) = result
                        if isinstance(update_result, Exception):
                            # Update operation failed
                            error = classify_canvas_error(exception=update_result)
                            failed.append((original_data, error))
                        else:
                            # Update successful
                            successful.append(update_result)
                    except Exception as e:
                        failed.append((None, classify_canvas_error(exception=e)))
            
            # Small delay between batches to respect rate limits
            if i + batch_size < len(updates):
                await asyncio.sleep(0.5)
        
        execution_time = time.time() - start_time
        
        return BatchResult(
            successful=successful,
            failed=failed,
            total_processed=len(updates),
            execution_time=execution_time,
            api_calls_made=api_calls
        )
    
    async def _update_single_content(self,
                                   course_id: str,
                                   content_type: str,
                                   content_id: str,
                                   new_content: str) -> Dict:
        """Update a single content item."""
        endpoint_map = {
            'page': f"courses/{course_id}/pages/{content_id}",
            'assignment': f"courses/{course_id}/assignments/{content_id}",
            'quiz': f"courses/{course_id}/quizzes/{content_id}",
            'discussion': f"courses/{course_id}/discussion_topics/{content_id}"
        }
        
        content_field_map = {
            'page': 'body',
            'assignment': 'description',
            'quiz': 'description', 
            'discussion': 'message'
        }
        
        endpoint = endpoint_map.get(content_type)
        content_field = content_field_map.get(content_type)
        
        if not endpoint or not content_field:
            raise ValueError(f"Unsupported content type: {content_type}")
        
        # Prepare update data
        update_data = {
            content_type: {
                content_field: new_content
            }
        }
        
        return await self._make_request(
            endpoint=endpoint,
            method='PUT',
            data=update_data,
            paginated=False
        )
    
    async def validate_canvas_access(self) -> Dict[str, Any]:
        """Validate Canvas API access and permissions."""
        try:
            # Test basic API access
            profile = await self._make_request('users/self/profile', paginated=False)
            
            # Test course access if user_id available
            courses_accessible = False
            if self.user_id:
                try:
                    courses = await self._make_request('courses', params={'per_page': 1})
                    courses_accessible = len(courses) >= 0
                except Exception:
                    pass
            
            return {
                'valid': True,
                'user_profile': profile,
                'courses_accessible': courses_accessible,
                'api_calls_made': self.api_call_count,
                'average_response_time': (
                    self.total_response_time / max(1, self.api_call_count)
                ),
                'error_rate': self.error_count / max(1, self.api_call_count)
            }
            
        except Exception as e:
            canvas_error = classify_canvas_error(exception=e)
            return {
                'valid': False,
                'error': canvas_error.user_message,
                'error_type': canvas_error.error_type.value,
                'recoverable': canvas_error.recoverable
            }
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring."""
        rate_limit_stats = await self.rate_limiter.get_rate_limit_stats(self.user_id)
        error_stats = self.error_handler.get_error_statistics()
        
        return {
            'api_calls_made': self.api_call_count,
            'total_response_time': self.total_response_time,
            'average_response_time': (
                self.total_response_time / max(1, self.api_call_count)
            ),
            'error_count': self.error_count,
            'error_rate': self.error_count / max(1, self.api_call_count),
            'rate_limit_stats': rate_limit_stats,
            'error_breakdown': error_stats,
            'optimal_batch_size': await self.rate_limiter.get_optimal_batch_size(self.user_id)
        }


def create_canvas_service_from_lti(lti_context: Dict) -> ProductionCanvasService:
    """Create Canvas service from LTI context information with multi-instance support."""
    from app.core.config import get_settings
    
    settings = get_settings()
    canvas_context = lti_context.get('canvas', {})
    user_context = lti_context.get('user', {})
    
    # Get active Canvas instance configuration
    active_instance = settings.get_active_canvas_instance()
    
    if not active_instance:
        raise ValueError("No active Canvas instance configured")
    
    # Use active instance configuration
    canvas_url = active_instance.base_url
    access_token = canvas_context.get('access_token', '')
    
    if not access_token:
        # In production, this should trigger OAuth flow
        raise ValueError("Canvas access token not available")
    
    user_id = user_context.get('id', 'unknown')
    
    logger.info(f"Creating Canvas service for instance '{settings.canvas_active_instance}' at {canvas_url}")
    
    return ProductionCanvasService(
        base_url=canvas_url,
        access_token=access_token,
        user_id=user_id
    )


def create_canvas_service_for_instance(instance_name: str, access_token: str, user_id: str = "unknown") -> ProductionCanvasService:
    """Create Canvas service for a specific instance."""
    from app.core.config import get_settings
    
    settings = get_settings()
    instances = settings.get_canvas_instances()
    
    if instance_name not in instances:
        raise ValueError(f"Canvas instance '{instance_name}' not configured. Available instances: {list(instances.keys())}")
    
    instance_config = instances[instance_name]
    
    logger.info(f"Creating Canvas service for instance '{instance_name}' at {instance_config.base_url}")
    
    return ProductionCanvasService(
        base_url=instance_config.base_url,
        access_token=access_token,
        user_id=user_id
    ) 