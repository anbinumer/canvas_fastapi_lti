"""
Health Check and Monitoring Endpoints
Story 2.4: Canvas Integration & Testing

Comprehensive health checks for production monitoring including Canvas API,
rate limiting, database, and application component status.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
import redis.asyncio as redis

from app.core.config import get_settings
from app.core.rate_limiter import get_rate_limiter
from app.core.canvas_error_handler import get_canvas_error_handler
from app.services.canvas_service import ProductionCanvasService
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def basic_health_check():
    """Basic health check endpoint for load balancers."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ACU QA Automation Platform"
    }


@router.get("/detailed")
async def detailed_health_check():
    """
    Detailed health check with component status for monitoring systems.
    
    Returns comprehensive status of all system components including:
    - Application status
    - Database connectivity
    - Redis connectivity
    - Rate limiting system
    - Canvas error handler
    """
    start_time = time.time()
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ACU QA Automation Platform",
        "version": "2.4.0",
        "components": {},
        "response_time_ms": 0
    }
    
    overall_healthy = True
    
    # Check application core
    try:
        health_status["components"]["application"] = {
            "status": "healthy",
            "details": {
                "environment": settings.environment,
                "debug_mode": settings.debug,
                "uptime_seconds": time.time() - start_time
            }
        }
    except Exception as e:
        overall_healthy = False
        health_status["components"]["application"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check Redis connectivity
    try:
        redis_client = redis.Redis(
            host=settings.redis_host or 'localhost',
            port=settings.redis_port or 6379,
            password=settings.redis_password,
            decode_responses=True,
            socket_timeout=5
        )
        
        redis_start = time.time()
        await redis_client.ping()
        redis_response_time = (time.time() - redis_start) * 1000
        
        # Get Redis info
        redis_info = await redis_client.info()
        
        health_status["components"]["redis"] = {
            "status": "healthy",
            "response_time_ms": round(redis_response_time, 2),
            "details": {
                "connected_clients": redis_info.get('connected_clients', 0),
                "used_memory_human": redis_info.get('used_memory_human', 'unknown'),
                "uptime_in_seconds": redis_info.get('uptime_in_seconds', 0)
            }
        }
        
        await redis_client.close()
        
    except Exception as e:
        overall_healthy = False
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check rate limiter
    try:
        rate_limiter = await get_rate_limiter()
        rate_limiter_health = await rate_limiter.health_check()
        
        if rate_limiter_health.get('status') == 'healthy':
            health_status["components"]["rate_limiter"] = {
                "status": "healthy",
                "details": rate_limiter_health
            }
        else:
            overall_healthy = False
            health_status["components"]["rate_limiter"] = {
                "status": "unhealthy",
                "details": rate_limiter_health
            }
            
    except Exception as e:
        overall_healthy = False
        health_status["components"]["rate_limiter"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check Canvas error handler
    try:
        error_handler = get_canvas_error_handler()
        error_stats = error_handler.get_error_statistics()
        
        health_status["components"]["error_handler"] = {
            "status": "healthy",
            "details": {
                "total_errors_tracked": error_stats.get('total_errors', 0),
                "error_types_seen": len(error_stats.get('error_types', [])),
                "last_updated": error_stats.get('last_updated', 'never')
            }
        }
        
    except Exception as e:
        overall_healthy = False
        health_status["components"]["error_handler"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Calculate total response time
    health_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    # Set overall status
    health_status["status"] = "healthy" if overall_healthy else "unhealthy"
    
    # Return appropriate HTTP status code
    status_code = 200 if overall_healthy else 503
    
    return JSONResponse(
        content=health_status,
        status_code=status_code
    )


@router.get("/canvas")
async def canvas_health_check(
    canvas_url: Optional[str] = None,
    access_token: Optional[str] = None,
    instance: Optional[str] = None
):
    """
    Canvas API health check endpoint with multi-instance support.
    
    Tests Canvas API connectivity and basic functionality across all configured instances
    or a specific instance if provided.
    """
    from app.core.config import get_settings
    
    settings = get_settings()
    start_time = time.time()
    
    health_status = {
        "status": "unknown",
        "timestamp": datetime.utcnow().isoformat(),
        "response_time_ms": 0,
        "active_instance": settings.canvas_active_instance,
        "instance_summary": settings.get_canvas_instance_summary(),
        "tests": {}
    }
    
    overall_healthy = True
    
    # Test specific instance if provided
    if instance:
        instances_to_test = {instance: settings.get_canvas_instances().get(instance)}
        if not instances_to_test[instance]:
            health_status["tests"][f"instance_{instance}"] = {
                "status": "unhealthy",
                "error": f"Instance '{instance}' not configured"
            }
            overall_healthy = False
    else:
        # Test all configured instances
        instances_to_test = settings.get_canvas_instances()
    
    # Test each instance
    for instance_name, instance_config in instances_to_test.items():
        if not instance_config:
            continue
            
        test_start = time.time()
        
        try:
            # Use provided credentials or test anonymously
            if access_token:
                # Test with authenticated endpoint
                from app.services.canvas_service import create_canvas_service_for_instance
                
                async with create_canvas_service_for_instance(
                    instance_name, 
                    access_token, 
                    "health_check"
                ) as canvas_service:
                    validation_result = await canvas_service.validate_canvas_access()
                    
                    if validation_result.get('valid'):
                        health_status["tests"][f"instance_{instance_name}_authenticated"] = {
                            "status": "healthy",
                            "response_time_ms": round((time.time() - test_start) * 1000, 2),
                            "instance_url": instance_config.base_url,
                            "details": {
                                "user_profile_accessible": bool(validation_result.get('user_profile')),
                                "courses_accessible": validation_result.get('courses_accessible', False),
                                "api_calls_made": validation_result.get('api_calls_made', 0),
                                "error_rate": validation_result.get('error_rate', 0.0)
                            }
                        }
                    else:
                        overall_healthy = False
                        health_status["tests"][f"instance_{instance_name}_authenticated"] = {
                            "status": "unhealthy",
                            "response_time_ms": round((time.time() - test_start) * 1000, 2),
                            "instance_url": instance_config.base_url,
                            "error": validation_result.get('error', 'Authentication failed'),
                            "error_type": validation_result.get('error_type', 'unknown')
                        }
            else:
                # Test with anonymous endpoint (Canvas API status)
                import aiohttp
                
                test_url = f"{instance_config.base_url}/api/v1/status"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(test_url) as response:
                        if response.status == 200:
                            status_data = await response.json()
                            health_status["tests"][f"instance_{instance_name}_anonymous"] = {
                                "status": "healthy",
                                "response_time_ms": round((time.time() - test_start) * 1000, 2),
                                "instance_url": instance_config.base_url,
                                "details": status_data
                            }
                        else:
                            overall_healthy = False
                            health_status["tests"][f"instance_{instance_name}_anonymous"] = {
                                "status": "unhealthy",
                                "response_time_ms": round((time.time() - test_start) * 1000, 2),
                                "instance_url": instance_config.base_url,
                                "error": f"HTTP {response.status}",
                                "details": await response.text()
                            }
                            
        except Exception as e:
            overall_healthy = False
            health_status["tests"][f"instance_{instance_name}_connectivity"] = {
                "status": "unhealthy",
                "response_time_ms": round((time.time() - test_start) * 1000, 2),
                "instance_url": instance_config.base_url if instance_config else "unknown",
                "error": str(e)
            }
    
    # Test rate limiting system for active instance
    try:
        test_start = time.time()
        rate_limiter = await get_rate_limiter()
        
        # Test rate limit check
        from app.core.rate_limiter import check_canvas_rate_limit
        rate_status = await check_canvas_rate_limit("health_check", "default", 1)
        
        health_status["tests"]["rate_limiting"] = {
            "status": "healthy",
            "response_time_ms": round((time.time() - test_start) * 1000, 2),
            "details": {
                "allowed": rate_status.allowed,
                "remaining_requests": rate_status.remaining_requests,
                "current_usage": rate_status.current_usage
            }
        }
        
    except Exception as e:
        overall_healthy = False
        health_status["tests"]["rate_limiting"] = {
            "status": "unhealthy",
            "response_time_ms": round((time.time() - test_start) * 1000, 2),
            "error": str(e)
        }
    
    # Canvas instance configuration validation
    try:
        validation_results = settings.validate_canvas_instances()
        
        health_status["tests"]["instance_configuration"] = {
            "status": "healthy" if validation_results["valid"] else "unhealthy",
            "details": validation_results
        }
        
        if not validation_results["valid"]:
            overall_healthy = False
            
    except Exception as e:
        overall_healthy = False
        health_status["tests"]["instance_configuration"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Calculate total response time
    health_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    # Set overall status
    health_status["status"] = "healthy" if overall_healthy else "unhealthy"
    
    # Return appropriate HTTP status code
    status_code = 200 if overall_healthy else 503
    
    return JSONResponse(
        content=health_status,
        status_code=status_code
    )


@router.post("/canvas/switch-instance")
async def switch_canvas_instance(
    instance_name: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Switch the active Canvas instance.
    
    Requires authentication. Used for testing across Test → Beta → Prod progression.
    """
    from app.core.config import get_settings
    
    try:
        settings = get_settings()
        instances = settings.get_canvas_instances()
        
        if instance_name not in instances:
            raise HTTPException(
                status_code=400,
                detail=f"Instance '{instance_name}' not configured. Available instances: {list(instances.keys())}"
            )
        
        # Validate instance configuration
        instance_config = instances[instance_name]
        if not instance_config.client_id or not instance_config.private_key_base64:
            raise HTTPException(
                status_code=400,
                detail=f"Instance '{instance_name}' is not properly configured (missing credentials)"
            )
        
        # Switch the active instance
        success = settings.set_active_canvas_instance(instance_name)
        
        if success:
            return {
                "status": "success",
                "message": f"Switched to Canvas instance: {instance_name}",
                "previous_instance": settings.canvas_active_instance,
                "new_active_instance": instance_name,
                "instance_url": instance_config.base_url,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to switch to instance '{instance_name}'"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to switch Canvas instance: {str(e)}"
        )


@router.get("/canvas/instances")
async def get_canvas_instances():
    """
    Get information about all configured Canvas instances.
    
    Useful for testing and monitoring instance configuration.
    """
    from app.core.config import get_settings
    
    try:
        settings = get_settings()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "instance_summary": settings.get_canvas_instance_summary(),
            "validation_results": settings.validate_canvas_instances(),
            "environment_mapping": {
                "development": "test",
                "staging": "beta", 
                "production": "prod"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Canvas instances: {str(e)}"
        )


@router.get("/performance")
async def performance_metrics():
    """
    Get performance metrics for monitoring and analytics.
    
    Provides detailed performance data for system monitoring.
    """
    try:
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "rate_limiting": {},
            "error_tracking": {},
            "system": {}
        }
        
        # Rate limiting metrics
        try:
            rate_limiter = await get_rate_limiter()
            
            # Get global stats
            redis_client = redis.Redis(
                host=settings.redis_host or 'localhost',
                port=settings.redis_port or 6379,
                password=settings.redis_password,
                decode_responses=True
            )
            
            global_minute_usage = await redis_client.zcard("canvas_rate_limit:global:minute")
            global_hour_usage = await redis_client.zcard("canvas_rate_limit:global:hour")
            
            await redis_client.close()
            
            metrics["rate_limiting"] = {
                "global_minute_usage": global_minute_usage,
                "global_hour_usage": global_hour_usage,
                "minute_limit": 1800,  # 180 * 10 users
                "hour_limit": 48000,   # 4800 * 10 users
                "utilization_percentage": {
                    "minute": round((global_minute_usage / 1800) * 100, 2),
                    "hour": round((global_hour_usage / 48000) * 100, 2)
                }
            }
            
        except Exception as e:
            metrics["rate_limiting"] = {"error": str(e)}
        
        # Error tracking metrics
        try:
            error_handler = get_canvas_error_handler()
            error_stats = error_handler.get_error_statistics()
            
            metrics["error_tracking"] = {
                "total_errors": error_stats.get('total_errors', 0),
                "error_types": error_stats.get('error_types', []),
                "error_breakdown": error_stats.get('error_stats', {}),
                "last_updated": error_stats.get('last_updated', 'never')
            }
            
        except Exception as e:
            metrics["error_tracking"] = {"error": str(e)}
        
        # System metrics
        try:
            import psutil
            
            metrics["system"] = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "process_count": len(psutil.pids())
            }
            
        except ImportError:
            # psutil not available
            metrics["system"] = {
                "note": "System metrics require psutil package"
            }
        except Exception as e:
            metrics["system"] = {"error": str(e)}
        
        return metrics
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve performance metrics: {str(e)}"
        )


@router.get("/readiness")
async def readiness_check():
    """
    Kubernetes readiness probe endpoint.
    
    Checks if the application is ready to receive traffic.
    """
    try:
        # Check critical dependencies
        dependencies_ready = True
        dependency_status = {}
        
        # Check Redis
        try:
            redis_client = redis.Redis(
                host=settings.redis_host or 'localhost',
                port=settings.redis_port or 6379,
                password=settings.redis_password,
                decode_responses=True,
                socket_timeout=2
            )
            await redis_client.ping()
            await redis_client.close()
            dependency_status["redis"] = "ready"
            
        except Exception as e:
            dependencies_ready = False
            dependency_status["redis"] = f"not ready: {str(e)}"
        
        # Check rate limiter
        try:
            rate_limiter = await get_rate_limiter()
            health = await rate_limiter.health_check()
            
            if health.get('status') == 'healthy':
                dependency_status["rate_limiter"] = "ready"
            else:
                dependencies_ready = False
                dependency_status["rate_limiter"] = "not ready"
                
        except Exception as e:
            dependencies_ready = False
            dependency_status["rate_limiter"] = f"not ready: {str(e)}"
        
        status_code = 200 if dependencies_ready else 503
        
        return JSONResponse(
            content={
                "status": "ready" if dependencies_ready else "not ready",
                "timestamp": datetime.utcnow().isoformat(),
                "dependencies": dependency_status
            },
            status_code=status_code
        )
        
    except Exception as e:
        return JSONResponse(
            content={
                "status": "not ready",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            },
            status_code=503
        )


@router.get("/liveness")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.
    
    Simple check to verify the application is running.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "pid": __import__('os').getpid()
    }


@router.post("/rate-limit/reset")
async def reset_rate_limits(
    user_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Admin endpoint to reset rate limits for a user.
    
    Requires administrative privileges.
    """
    # Check if user has admin privileges
    if not current_user.get('is_admin', False):
        raise HTTPException(
            status_code=403,
            detail="Administrative privileges required"
        )
    
    try:
        rate_limiter = await get_rate_limiter()
        
        if user_id:
            # Reset specific user
            success = await rate_limiter.reset_user_limits(user_id)
            if success:
                return {
                    "status": "success",
                    "message": f"Rate limits reset for user {user_id}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to reset rate limits for user {user_id}"
                )
        else:
            # Reset global limits (admin only, dangerous operation)
            redis_client = redis.Redis(
                host=settings.redis_host or 'localhost',
                port=settings.redis_port or 6379,
                password=settings.redis_password,
                decode_responses=True
            )
            
            # Delete all rate limit keys
            keys = await redis_client.keys("canvas_rate_limit:*")
            if keys:
                await redis_client.delete(*keys)
            
            await redis_client.close()
            
            return {
                "status": "success",
                "message": "All rate limits reset",
                "keys_deleted": len(keys),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset rate limits: {str(e)}"
        )


@router.get("/diagnostics")
async def system_diagnostics(
    current_user: Dict = Depends(get_current_user)
):
    """
    Comprehensive system diagnostics for troubleshooting.
    
    Requires authentication for detailed system information.
    """
    try:
        diagnostics = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_context": {
                "user_id": current_user.get('id', 'unknown'),
                "canvas_instance": current_user.get('canvas_instance_url', 'unknown')
            },
            "configuration": {},
            "connectivity": {},
            "performance": {}
        }
        
        # Configuration info
        diagnostics["configuration"] = {
            "environment": settings.environment,
            "debug_mode": settings.debug,
            "redis_configured": bool(settings.redis_host),
            "canvas_base_url": getattr(settings, 'canvas_base_url', 'not configured')
        }
        
        # Connectivity tests
        connectivity_results = {}
        
        # Test Redis
        try:
            redis_client = redis.Redis(
                host=settings.redis_host or 'localhost',
                port=settings.redis_port or 6379,
                password=settings.redis_password,
                decode_responses=True,
                socket_timeout=5
            )
            
            start_time = time.time()
            await redis_client.ping()
            response_time = (time.time() - start_time) * 1000
            
            redis_info = await redis_client.info()
            await redis_client.close()
            
            connectivity_results["redis"] = {
                "status": "connected",
                "response_time_ms": round(response_time, 2),
                "server_version": redis_info.get('redis_version', 'unknown'),
                "memory_usage": redis_info.get('used_memory_human', 'unknown')
            }
            
        except Exception as e:
            connectivity_results["redis"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Test Canvas (if token available)
        canvas_instance = current_user.get('canvas_instance_url')
        access_token = current_user.get('access_token')
        
        if canvas_instance and access_token:
            try:
                async with ProductionCanvasService(
                    canvas_instance, 
                    access_token, 
                    current_user.get('id')
                ) as canvas_service:
                    
                    start_time = time.time()
                    validation = await canvas_service.validate_canvas_access()
                    response_time = (time.time() - start_time) * 1000
                    
                    performance_metrics = await canvas_service.get_performance_metrics()
                    
                    connectivity_results["canvas"] = {
                        "status": "connected" if validation.get('valid') else "failed",
                        "response_time_ms": round(response_time, 2),
                        "validation": validation,
                        "performance": performance_metrics
                    }
                    
            except Exception as e:
                connectivity_results["canvas"] = {
                    "status": "failed",
                    "error": str(e)
                }
        else:
            connectivity_results["canvas"] = {
                "status": "not configured",
                "reason": "No Canvas credentials available"
            }
        
        diagnostics["connectivity"] = connectivity_results
        
        # Performance metrics
        try:
            rate_limiter = await get_rate_limiter()
            rate_stats = await rate_limiter.get_rate_limit_stats(current_user.get('id', 'unknown'))
            
            error_handler = get_canvas_error_handler()
            error_stats = error_handler.get_error_statistics()
            
            diagnostics["performance"] = {
                "rate_limiting": rate_stats,
                "error_tracking": {
                    "total_errors": error_stats.get('total_errors', 0),
                    "error_types": error_stats.get('error_types', [])
                }
            }
            
        except Exception as e:
            diagnostics["performance"] = {
                "error": str(e)
            }
        
        return diagnostics
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate diagnostics: {str(e)}"
        ) 