"""
Environment configuration for QA Automation LTI Tool
Supports development/staging/production environments with Canvas LTI 1.3 integration
Enhanced with multi-instance Canvas support for Test/Beta/Prod progression
Enhanced with deployment configuration and environment validation
"""

import os
import base64
import secrets
import logging
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field, validator
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings, Field, validator

logger = logging.getLogger(__name__)

@dataclass
class CanvasInstanceConfig:
    """Configuration for a specific Canvas instance."""
    name: str
    base_url: str
    client_id: str
    client_secret: Optional[str] = None
    private_key_base64: Optional[str] = None
    api_timeout: int = 30
    api_max_retries: int = 3
    rate_limit_per_minute: int = 180  # 90% of Canvas 200/min limit
    rate_limit_per_hour: int = 4800   # 80% of Canvas 6000/hour limit
    description: str = ""
    
    @property
    def private_key(self) -> Optional[str]:
        """Decode base64 private key for use."""
        if self.private_key_base64:
            try:
                return base64.b64decode(self.private_key_base64).decode('utf-8')
            except Exception as e:
                logger.error(f"Failed to decode private key for {self.name}: {e}")
                return None
        return None
    
    @property
    def api_base_url(self) -> str:
        """Canvas API base URL."""
        return f"{self.base_url}/api/v1"
    
    def validate(self) -> bool:
        """Validate Canvas instance configuration."""
        if not all([self.name, self.base_url, self.client_id]):
            return False
        
        if not self.private_key_base64:
            logger.warning(f"Canvas instance {self.name} missing private key")
            return False
            
        if not self.private_key:
            logger.error(f"Canvas instance {self.name} has invalid private key encoding")
            return False
            
        return True


class Settings(BaseSettings):
    """
    Application settings with environment-specific configuration
    Enhanced with multi-instance Canvas support and deployment configuration
    """
    
    # Application Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False)
    
    # FastAPI Configuration
    app_title: str = "QA Automation LTI Tool"
    app_description: str = "Canvas LTI 1.3 QA Automation Tool for Learning Designers"
    app_version: str = "2.4.0"
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    base_url: str = Field(default="http://localhost:8000", env="BASE_URL")
    
    # Session Configuration (Canvas iframe compatibility)
    secret_key: str = Field(default="dev-secret-key-change-in-production", env="SECRET_KEY")
    session_cookie_samesite: str = "None"  # Required for Canvas iframe
    session_cookie_secure: bool = True     # Required for Canvas iframe
    session_cookie_httponly: bool = True
    session_expire_seconds: int = 14400    # 4 hours
    
    # Security Headers (Canvas iframe compatibility)
    x_frame_options: str = "ALLOWALL"  # Required for Canvas iframe embedding
    
    # Multi-Instance Canvas Configuration
    canvas_active_instance: str = Field(default="test", env="CANVAS_ACTIVE_INSTANCE")
    
    # Canvas Instance Credentials - Test Environment
    canvas_test_base_url: str = Field(default="https://www.aculeo.test.instructure.com", env="CANVAS_TEST_BASE_URL")
    canvas_test_client_id: Optional[str] = Field(default=None, env="CANVAS_TEST_CLIENT_ID")
    canvas_test_client_secret: Optional[str] = Field(default=None, env="CANVAS_TEST_CLIENT_SECRET")
    canvas_test_private_key: Optional[str] = Field(default=None, env="CANVAS_TEST_PRIVATE_KEY")
    
    # Canvas Instance Credentials - Beta Environment
    canvas_beta_base_url: str = Field(default="https://www.aculeo.beta.instructure.com", env="CANVAS_BETA_BASE_URL")
    canvas_beta_client_id: Optional[str] = Field(default=None, env="CANVAS_BETA_CLIENT_ID")
    canvas_beta_client_secret: Optional[str] = Field(default=None, env="CANVAS_BETA_CLIENT_SECRET")
    canvas_beta_private_key: Optional[str] = Field(default=None, env="CANVAS_BETA_PRIVATE_KEY")
    
    # Canvas Instance Credentials - Production Environment
    canvas_prod_base_url: str = Field(default="https://www.aculeo.instructure.com", env="CANVAS_PROD_BASE_URL")
    canvas_prod_client_id: Optional[str] = Field(default=None, env="CANVAS_PROD_CLIENT_ID")
    canvas_prod_client_secret: Optional[str] = Field(default=None, env="CANVAS_PROD_CLIENT_SECRET")
    canvas_prod_private_key: Optional[str] = Field(default=None, env="CANVAS_PROD_PRIVATE_KEY")
    
    # Canvas API Configuration
    canvas_api_timeout: int = Field(default=30, env="CANVAS_API_TIMEOUT")
    canvas_api_max_retries: int = Field(default=3, env="CANVAS_API_MAX_RETRIES")
    canvas_rate_limit_per_minute: int = Field(default=180, env="CANVAS_RATE_LIMIT_PER_MINUTE")
    canvas_rate_limit_per_hour: int = Field(default=4800, env="CANVAS_RATE_LIMIT_PER_HOUR")
    
    # Database Configuration
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    database_pool_size: int = Field(default=5, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    
    # Redis Configuration
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    redis_max_connections: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    structured_logging: bool = Field(default=True, env="STRUCTURED_LOGGING")
    
    # Monitoring Configuration
    health_check_timeout: int = Field(default=30, env="HEALTH_CHECK_TIMEOUT")
    monitoring_enabled: bool = Field(default=True, env="MONITORING_ENABLED")
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    performance_monitoring: bool = Field(default=False, env="PERFORMANCE_MONITORING")
    
    # Security Configuration
    cors_origins: List[str] = Field(
        default=["https://*.instructure.com"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    content_security_policy: str = Field(
        default="frame-ancestors 'self' https://*.instructure.com",
        env="CONTENT_SECURITY_POLICY"
    )
    
    # Additional Security Headers
    strict_transport_security: Optional[str] = Field(default=None, env="STRICT_TRANSPORT_SECURITY")
    x_content_type_options: str = Field(default="nosniff", env="X_CONTENT_TYPE_OPTIONS")
    x_xss_protection: str = Field(default="1; mode=block", env="X_XSS_PROTECTION")
    
    # LTI 1.3 Configuration
    lti_launch_url: Optional[str] = Field(default=None, env="LTI_LAUNCH_URL")
    lti_login_url: Optional[str] = Field(default=None, env="LTI_LOGIN_URL")
    lti_jwks_url: Optional[str] = Field(default=None, env="LTI_JWKS_URL")
    lti_jwt_algorithm: str = Field(default="RS256", env="LTI_JWT_ALGORITHM")
    lti_jwt_expiration: int = Field(default=3600, env="LTI_JWT_EXPIRATION")
    lti_nonce_cache_ttl: int = Field(default=600, env="LTI_NONCE_CACHE_TTL")
    
    # Performance Configuration
    async_workers: int = Field(default=4, env="ASYNC_WORKERS")
    max_concurrent_tasks: int = Field(default=10, env="MAX_CONCURRENT_TASKS")
    task_timeout: int = Field(default=300, env="TASK_TIMEOUT")
    
    # WebSocket Configuration
    websocket_ping_interval: int = Field(default=30, env="WEBSOCKET_PING_INTERVAL")
    websocket_ping_timeout: int = Field(default=10, env="WEBSOCKET_PING_TIMEOUT")
    websocket_close_timeout: int = Field(default=10, env="WEBSOCKET_CLOSE_TIMEOUT")
    
    # QA Framework Configuration
    max_content_items_per_task: int = Field(default=1000, env="MAX_CONTENT_ITEMS_PER_TASK")
    max_task_duration_seconds: int = Field(default=1800, env="MAX_TASK_DURATION_SECONDS")
    progress_update_interval: int = Field(default=2, env="PROGRESS_UPDATE_INTERVAL")
    batch_size: int = Field(default=50, env="BATCH_SIZE")
    parallel_processing_limit: int = Field(default=5, env="PARALLEL_PROCESSING_LIMIT")
    memory_limit_mb: int = Field(default=512, env="MEMORY_LIMIT_MB")
    
    # Error Tracking Configuration
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    sentry_environment: Optional[str] = Field(default=None, env="SENTRY_ENVIRONMENT")
    sentry_traces_sample_rate: float = Field(default=0.1, env="SENTRY_TRACES_SAMPLE_RATE")
    
    # Testing Configuration
    testing: bool = Field(default=False, env="TESTING")
    test_database_url: Optional[str] = Field(default=None, env="TEST_DATABASE_URL")
    skip_canvas_api_calls: bool = Field(default=False, env="SKIP_CANVAS_API_CALLS")
    
    # Development Features
    enable_debug_routes: bool = Field(default=False, env="ENABLE_DEBUG_ROUTES")
    allow_unsafe_operations: bool = Field(default=False, env="ALLOW_UNSAFE_OPERATIONS")
    bypass_lti_validation: bool = Field(default=False, env="BYPASS_LTI_VALIDATION")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @validator("secret_key")
    def validate_secret_key(cls, v: str, values: Dict[str, Any]) -> str:
        """Validate secret key meets security requirements."""
        environment = values.get("environment", "development")
        
        if environment == "production":
            if len(v) < 32:
                raise ValueError("Production secret key must be at least 32 characters")
            if v in ["dev-secret-key-change-in-production", "test-secret-key-minimum-32-characters-long-change-this"]:
                raise ValueError("Production secret key cannot use default development values")
        elif len(v) < 16:
            raise ValueError("Secret key must be at least 16 characters")
            
        return v
        
    @validator("canvas_active_instance")
    def validate_canvas_instance(cls, v: str) -> str:
        """Validate Canvas instance name."""
        valid_instances = ["test", "beta", "prod"]
        if v not in valid_instances:
            raise ValueError(f"Canvas instance must be one of: {valid_instances}")
        return v
        
    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
        
    @validator("cors_origins", pre=True)
    def validate_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            # Handle JSON string format
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Handle comma-separated string
            return [origin.strip() for origin in v.split(",")]
        return v

    def get_canvas_instance_config(self, instance_name: Optional[str] = None) -> Optional[CanvasInstanceConfig]:
        """
        Get Canvas instance configuration by name.
        
        Args:
            instance_name: Name of the Canvas instance (test, beta, prod)
                          If None, uses canvas_active_instance
                          
        Returns:
            CanvasInstanceConfig object or None if not found
        """
        if instance_name is None:
            instance_name = self.canvas_active_instance
            
        configs = {
            "test": CanvasInstanceConfig(
                name="test",
                base_url=self.canvas_test_base_url,
                client_id=self.canvas_test_client_id,
                client_secret=self.canvas_test_client_secret,
                private_key_base64=self.canvas_test_private_key,
                api_timeout=self.canvas_api_timeout,
                api_max_retries=self.canvas_api_max_retries,
                rate_limit_per_minute=self.canvas_rate_limit_per_minute,
                rate_limit_per_hour=self.canvas_rate_limit_per_hour,
                description="Canvas Test Environment"
            ),
            "beta": CanvasInstanceConfig(
                name="beta",
                base_url=self.canvas_beta_base_url,
                client_id=self.canvas_beta_client_id,
                client_secret=self.canvas_beta_client_secret,
                private_key_base64=self.canvas_beta_private_key,
                api_timeout=self.canvas_api_timeout,
                api_max_retries=self.canvas_api_max_retries,
                rate_limit_per_minute=self.canvas_rate_limit_per_minute,
                rate_limit_per_hour=self.canvas_rate_limit_per_hour,
                description="Canvas Beta Environment"
            ),
            "prod": CanvasInstanceConfig(
                name="prod",
                base_url=self.canvas_prod_base_url,
                client_id=self.canvas_prod_client_id,
                client_secret=self.canvas_prod_client_secret,
                private_key_base64=self.canvas_prod_private_key,
                api_timeout=self.canvas_api_timeout,
                api_max_retries=self.canvas_api_max_retries,
                rate_limit_per_minute=self.canvas_rate_limit_per_minute,
                rate_limit_per_hour=self.canvas_rate_limit_per_hour,
                description="Canvas Production Environment"
            )
        }
        
        return configs.get(instance_name)

    def get_all_canvas_instances(self) -> Dict[str, CanvasInstanceConfig]:
        """Get all configured Canvas instances."""
        instances = {}
        for name in ["test", "beta", "prod"]:
            config = self.get_canvas_instance_config(name)
            if config and config.client_id:  # Only include configured instances
                instances[name] = config
        return instances

    def validate_environment(self) -> List[str]:
        """
        Validate environment configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Validate active Canvas instance configuration
        active_config = self.get_canvas_instance_config()
        if not active_config:
            errors.append(f"Canvas instance '{self.canvas_active_instance}' not configured")
        elif not active_config.validate():
            errors.append(f"Canvas instance '{self.canvas_active_instance}' configuration invalid")
            
        # Validate production-specific requirements
        if self.environment == "production":
            if self.debug:
                errors.append("Debug mode must be disabled in production")
            if self.allow_unsafe_operations:
                errors.append("Unsafe operations must be disabled in production")
            if self.bypass_lti_validation:
                errors.append("LTI validation bypass must be disabled in production")
            if not self.base_url.startswith("https://"):
                errors.append("Production base URL must use HTTPS")
                
        # Validate database configuration
        if not self.database_url and self.environment != "development":
            errors.append("Database URL required for non-development environments")
            
        # Validate Redis configuration for production
        if self.environment == "production" and not self.redis_url:
            errors.append("Redis URL required for production environment")
            
        # Validate LTI URLs
        if self.lti_launch_url and not self.lti_launch_url.startswith("https://"):
            errors.append("LTI launch URL must use HTTPS")
            
        return errors

    def get_lti_urls(self) -> Dict[str, str]:
        """Get LTI URLs with fallbacks."""
        base = self.base_url.rstrip("/")
        return {
            "launch_url": self.lti_launch_url or f"{base}/lti/launch",
            "login_url": self.lti_login_url or f"{base}/lti/login", 
            "jwks_url": self.lti_jwks_url or f"{base}/.well-known/jwks.json"
        }

    def generate_secure_secret_key(self) -> str:
        """Generate a cryptographically secure secret key."""
        return secrets.token_urlsafe(32)

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
        
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration for FastAPI."""
        return {
            "allow_origins": self.cors_origins,
            "allow_credentials": self.cors_allow_credentials,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["*"],
        }

    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers for responses."""
        headers = {
            "X-Frame-Options": self.x_frame_options,
            "X-Content-Type-Options": self.x_content_type_options,
            "X-XSS-Protection": self.x_xss_protection,
            "Content-Security-Policy": self.content_security_policy,
        }
        
        if self.strict_transport_security:
            headers["Strict-Transport-Security"] = self.strict_transport_security
            
        return headers


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment variables."""
    global settings
    settings = Settings()
    return settings


# Environment validation on startup
startup_errors = settings.validate_environment()
if startup_errors:
    error_msg = f"Environment validation failed:\n" + "\n".join(f"- {error}" for error in startup_errors)
    if settings.environment == "production":
        raise RuntimeError(error_msg)
    else:
        logger.warning(error_msg)

# Log configuration summary
logger.info(f"Application configured for {settings.environment} environment")
logger.info(f"Active Canvas instance: {settings.canvas_active_instance}")
logger.info(f"Base URL: {settings.base_url}")
if settings.database_url:
    logger.info("Database: Configured")
if settings.redis_url:
    logger.info("Redis: Configured")
logger.info(f"Monitoring: {'Enabled' if settings.monitoring_enabled else 'Disabled'}") 