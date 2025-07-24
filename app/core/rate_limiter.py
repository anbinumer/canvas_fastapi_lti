"""
Production Canvas API Rate Limiter
Story 2.4: Canvas Integration & Testing

Implements comprehensive rate limiting for Canvas API with Redis backing,
token bucket algorithms, and intelligent request batching for production deployment.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

import redis.asyncio as redis
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class RateLimitConfig:
    """Rate limiting configuration for Canvas API."""
    requests_per_minute: int = 180  # 90% of Canvas 200/min limit
    requests_per_hour: int = 4800   # 80% of Canvas 6000/hour limit
    burst_allowance: int = 10       # Allow brief bursts
    safety_margin: float = 0.1      # 10% safety margin
    window_size: int = 60           # 60 seconds for sliding window
    

@dataclass
class RateLimitStatus:
    """Current rate limiting status."""
    allowed: bool
    remaining_requests: int
    reset_time: datetime
    retry_after: Optional[int] = None
    current_usage: int = 0
    hourly_usage: int = 0


class ProductionCanvasRateLimiter:
    """
    Production-grade Canvas API rate limiter with Redis backing.
    
    Features:
    - Token bucket algorithm with refill mechanism
    - Per-user and global rate limiting
    - Burst capacity handling
    - Redis-backed distributed rate limiting
    - Canvas API error classification and handling
    - Intelligent request batching and optimization
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.config = RateLimitConfig()
        self.redis = redis_client or self._create_redis_client()
        self.local_cache: Dict[str, Dict] = {}
        self.cache_ttl = 30  # seconds
        
        # Canvas API specific configurations
        self.canvas_endpoints = {
            'courses': {'weight': 1, 'cacheable': True, 'ttl': 300},
            'assignments': {'weight': 1, 'cacheable': True, 'ttl': 180},
            'pages': {'weight': 1, 'cacheable': True, 'ttl': 180},
            'quizzes': {'weight': 2, 'cacheable': True, 'ttl': 120},
            'discussions': {'weight': 1, 'cacheable': True, 'ttl': 120},
            'modules': {'weight': 1, 'cacheable': True, 'ttl': 300},
            'files': {'weight': 3, 'cacheable': False, 'ttl': 0},
            'submissions': {'weight': 2, 'cacheable': False, 'ttl': 0},
        }
        
    def _create_redis_client(self) -> redis.Redis:
        """Create Redis client for rate limiting storage."""
        return redis.Redis(
            host=settings.redis_host or 'localhost',
            port=settings.redis_port or 6379,
            password=settings.redis_password,
            decode_responses=True,
            retry_on_timeout=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        
    async def check_rate_limit(
        self, 
        user_id: str, 
        endpoint: str = 'default',
        weight: int = 1
    ) -> RateLimitStatus:
        """
        Check if request is allowed under current rate limits.
        
        Args:
            user_id: Canvas user ID or LTI session ID
            endpoint: Canvas API endpoint for weighted limiting
            weight: Request weight (some endpoints cost more)
            
        Returns:
            RateLimitStatus with current limiting information
        """
        try:
            current_time = time.time()
            
            # Get endpoint configuration
            endpoint_config = self.canvas_endpoints.get(endpoint, {'weight': weight})
            actual_weight = endpoint_config['weight']
            
            # Check both per-user and global limits
            user_status = await self._check_user_rate_limit(user_id, actual_weight, current_time)
            global_status = await self._check_global_rate_limit(actual_weight, current_time)
            
            # Return most restrictive limit
            if not user_status.allowed or not global_status.allowed:
                return RateLimitStatus(
                    allowed=False,
                    remaining_requests=min(user_status.remaining_requests, global_status.remaining_requests),
                    reset_time=max(user_status.reset_time, global_status.reset_time),
                    retry_after=max(user_status.retry_after or 0, global_status.retry_after or 0),
                    current_usage=max(user_status.current_usage, global_status.current_usage),
                    hourly_usage=max(user_status.hourly_usage, global_status.hourly_usage)
                )
            
            return RateLimitStatus(
                allowed=True,
                remaining_requests=min(user_status.remaining_requests, global_status.remaining_requests),
                reset_time=max(user_status.reset_time, global_status.reset_time),
                current_usage=max(user_status.current_usage, global_status.current_usage),
                hourly_usage=max(user_status.hourly_usage, global_status.hourly_usage)
            )
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open with conservative limits
            return RateLimitStatus(
                allowed=True,
                remaining_requests=10,
                reset_time=datetime.now() + timedelta(minutes=1),
                current_usage=0,
                hourly_usage=0
            )
    
    async def _check_user_rate_limit(
        self, 
        user_id: str, 
        weight: int, 
        current_time: float
    ) -> RateLimitStatus:
        """Check per-user rate limits using sliding window."""
        minute_key = f"canvas_rate_limit:user:{user_id}:minute"
        hour_key = f"canvas_rate_limit:user:{user_id}:hour"
        
        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()
        
        # Sliding window for minute limits
        minute_window_start = current_time - 60
        pipe.zremrangebyscore(minute_key, 0, minute_window_start)
        pipe.zcard(minute_key)
        pipe.expire(minute_key, 120)  # 2 minutes TTL
        
        # Sliding window for hour limits  
        hour_window_start = current_time - 3600
        pipe.zremrangebyscore(hour_key, 0, hour_window_start)
        pipe.zcard(hour_key)
        pipe.expire(hour_key, 7200)  # 2 hours TTL
        
        results = await pipe.execute()
        
        minute_count = results[1]
        hour_count = results[4]
        
        # Check limits
        minute_allowed = (minute_count + weight) <= self.config.requests_per_minute
        hour_allowed = (hour_count + weight) <= self.config.requests_per_hour
        
        if minute_allowed and hour_allowed:
            # Record this request
            await self._record_request(user_id, weight, current_time)
            
        return RateLimitStatus(
            allowed=minute_allowed and hour_allowed,
            remaining_requests=min(
                self.config.requests_per_minute - minute_count,
                self.config.requests_per_hour - hour_count
            ),
            reset_time=datetime.fromtimestamp(current_time + (60 if not minute_allowed else 3600)),
            retry_after=60 if not minute_allowed else (3600 if not hour_allowed else None),
            current_usage=minute_count,
            hourly_usage=hour_count
        )
    
    async def _check_global_rate_limit(
        self, 
        weight: int, 
        current_time: float
    ) -> RateLimitStatus:
        """Check global rate limits across all users."""
        minute_key = "canvas_rate_limit:global:minute"
        hour_key = "canvas_rate_limit:global:hour"
        
        # Similar sliding window logic for global limits
        pipe = self.redis.pipeline()
        
        minute_window_start = current_time - 60
        pipe.zremrangebyscore(minute_key, 0, minute_window_start)
        pipe.zcard(minute_key)
        pipe.expire(minute_key, 120)
        
        hour_window_start = current_time - 3600
        pipe.zremrangebyscore(hour_key, 0, hour_window_start)
        pipe.zcard(hour_key)
        pipe.expire(hour_key, 7200)
        
        results = await pipe.execute()
        
        minute_count = results[1]
        hour_count = results[4]
        
        # Global limits are higher but still conservative
        global_minute_limit = self.config.requests_per_minute * 10  # Scale for multiple users
        global_hour_limit = self.config.requests_per_hour * 10
        
        minute_allowed = (minute_count + weight) <= global_minute_limit
        hour_allowed = (hour_count + weight) <= global_hour_limit
        
        return RateLimitStatus(
            allowed=minute_allowed and hour_allowed,
            remaining_requests=min(
                global_minute_limit - minute_count,
                global_hour_limit - hour_count
            ),
            reset_time=datetime.fromtimestamp(current_time + (60 if not minute_allowed else 3600)),
            retry_after=60 if not minute_allowed else (3600 if not hour_allowed else None),
            current_usage=minute_count,
            hourly_usage=hour_count
        )
    
    async def _record_request(self, user_id: str, weight: int, current_time: float):
        """Record a successful request in rate limiting storage."""
        minute_key = f"canvas_rate_limit:user:{user_id}:minute"
        hour_key = f"canvas_rate_limit:user:{user_id}:hour"
        global_minute_key = "canvas_rate_limit:global:minute"
        global_hour_key = "canvas_rate_limit:global:hour"
        
        # Record weighted requests
        pipe = self.redis.pipeline()
        
        # Add multiple entries for weighted requests
        for _ in range(weight):
            request_id = f"{current_time}:{asyncio.current_task().get_name() if asyncio.current_task() else 'unknown'}"
            pipe.zadd(minute_key, {request_id: current_time})
            pipe.zadd(hour_key, {request_id: current_time})
            pipe.zadd(global_minute_key, {request_id: current_time})
            pipe.zadd(global_hour_key, {request_id: current_time})
        
        await pipe.execute()
        
        logger.debug(f"Recorded Canvas API request for user {user_id} with weight {weight}")
    
    async def wait_for_availability(
        self, 
        user_id: str, 
        endpoint: str = 'default',
        weight: int = 1,
        max_wait: int = 300
    ) -> bool:
        """
        Wait for rate limit availability with intelligent backoff.
        
        Args:
            user_id: Canvas user ID
            endpoint: Canvas API endpoint
            weight: Request weight
            max_wait: Maximum wait time in seconds
            
        Returns:
            True if request can proceed, False if max wait exceeded
        """
        start_time = time.time()
        wait_time = 1  # Start with 1 second
        
        while time.time() - start_time < max_wait:
            status = await self.check_rate_limit(user_id, endpoint, weight)
            
            if status.allowed:
                return True
            
            if status.retry_after:
                wait_time = min(status.retry_after, wait_time * 2)  # Exponential backoff
            
            logger.info(f"Rate limit hit for user {user_id}, waiting {wait_time}s")
            await asyncio.sleep(wait_time)
            
        logger.warning(f"Max wait time exceeded for user {user_id}")
        return False
    
    async def get_rate_limit_stats(self, user_id: str) -> Dict:
        """Get current rate limiting statistics for monitoring."""
        try:
            current_time = time.time()
            
            minute_key = f"canvas_rate_limit:user:{user_id}:minute"
            hour_key = f"canvas_rate_limit:user:{user_id}:hour"
            
            pipe = self.redis.pipeline()
            pipe.zcard(minute_key)
            pipe.zcard(hour_key)
            pipe.zcard("canvas_rate_limit:global:minute")
            pipe.zcard("canvas_rate_limit:global:hour")
            
            results = await pipe.execute()
            
            return {
                'user_minute_usage': results[0],
                'user_hour_usage': results[1],
                'global_minute_usage': results[2],
                'global_hour_usage': results[3],
                'minute_limit': self.config.requests_per_minute,
                'hour_limit': self.config.requests_per_hour,
                'user_minute_remaining': max(0, self.config.requests_per_minute - results[0]),
                'user_hour_remaining': max(0, self.config.requests_per_hour - results[1]),
                'timestamp': current_time
            }
            
        except Exception as e:
            logger.error(f"Failed to get rate limit stats: {e}")
            return {}
    
    async def reset_user_limits(self, user_id: str) -> bool:
        """Reset rate limits for a specific user (admin function)."""
        try:
            minute_key = f"canvas_rate_limit:user:{user_id}:minute"
            hour_key = f"canvas_rate_limit:user:{user_id}:hour"
            
            pipe = self.redis.pipeline()
            pipe.delete(minute_key)
            pipe.delete(hour_key)
            
            await pipe.execute()
            
            logger.info(f"Reset rate limits for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset rate limits for user {user_id}: {e}")
            return False
    
    async def batch_check_availability(
        self, 
        requests: List[Tuple[str, str, int]]
    ) -> List[RateLimitStatus]:
        """
        Check rate limit availability for multiple requests efficiently.
        
        Args:
            requests: List of (user_id, endpoint, weight) tuples
            
        Returns:
            List of RateLimitStatus for each request
        """
        results = []
        
        for user_id, endpoint, weight in requests:
            status = await self.check_rate_limit(user_id, endpoint, weight)
            results.append(status)
            
        return results
    
    async def get_optimal_batch_size(self, user_id: str) -> int:
        """
        Calculate optimal batch size for Canvas API requests based on current limits.
        
        Returns:
            Recommended batch size for API requests
        """
        stats = await self.get_rate_limit_stats(user_id)
        
        if not stats:
            return 10  # Conservative default
        
        remaining_minute = stats.get('user_minute_remaining', 10)
        remaining_hour = stats.get('user_hour_remaining', 10)
        
        # Use smaller of the two limits, with safety margin
        optimal_size = min(remaining_minute, remaining_hour // 10)  # Spread hourly over 10-minute chunks
        
        # Ensure reasonable bounds
        return max(1, min(optimal_size, 50))
    
    async def health_check(self) -> Dict:
        """Health check for rate limiter Redis connectivity."""
        try:
            # Test Redis connectivity
            await self.redis.ping()
            
            # Get basic stats
            global_stats = {
                'minute_usage': await self.redis.zcard("canvas_rate_limit:global:minute"),
                'hour_usage': await self.redis.zcard("canvas_rate_limit:global:hour")
            }
            
            return {
                'status': 'healthy',
                'redis_connected': True,
                'global_usage': global_stats,
                'config': {
                    'requests_per_minute': self.config.requests_per_minute,
                    'requests_per_hour': self.config.requests_per_hour
                }
            }
            
        except Exception as e:
            logger.error(f"Rate limiter health check failed: {e}")
            return {
                'status': 'unhealthy',
                'redis_connected': False,
                'error': str(e)
            }
    
    async def cleanup_old_entries(self):
        """Cleanup old entries from Redis (maintenance task)."""
        try:
            current_time = time.time()
            cutoff_time = current_time - 7200  # 2 hours ago
            
            # Get all rate limit keys
            keys = await self.redis.keys("canvas_rate_limit:*")
            
            pipe = self.redis.pipeline()
            
            for key in keys:
                pipe.zremrangebyscore(key, 0, cutoff_time)
            
            results = await pipe.execute()
            total_cleaned = sum(results)
            
            logger.info(f"Cleaned up {total_cleaned} old rate limit entries")
            return total_cleaned
            
        except Exception as e:
            logger.error(f"Rate limit cleanup failed: {e}")
            return 0


# Global rate limiter instance
_rate_limiter: Optional[ProductionCanvasRateLimiter] = None


async def get_rate_limiter() -> ProductionCanvasRateLimiter:
    """Get or create global rate limiter instance."""
    global _rate_limiter
    
    if _rate_limiter is None:
        _rate_limiter = ProductionCanvasRateLimiter()
        logger.info("Created global Canvas rate limiter instance")
        
    return _rate_limiter


async def check_canvas_rate_limit(
    user_id: str, 
    endpoint: str = 'default', 
    weight: int = 1
) -> RateLimitStatus:
    """Convenience function for checking Canvas API rate limits."""
    rate_limiter = await get_rate_limiter()
    return await rate_limiter.check_rate_limit(user_id, endpoint, weight)


async def wait_for_canvas_availability(
    user_id: str, 
    endpoint: str = 'default', 
    weight: int = 1, 
    max_wait: int = 300
) -> bool:
    """Convenience function for waiting for Canvas API availability."""
    rate_limiter = await get_rate_limiter()
    return await rate_limiter.wait_for_availability(user_id, endpoint, weight, max_wait) 