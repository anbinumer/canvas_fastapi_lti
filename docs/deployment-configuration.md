# Production Deployment Configuration Guide

## Overview

This guide covers the complete deployment configuration for the Canvas QA Automation Tool across test, beta, and production environments. This documentation supports **Story 2.4 Task 6: Production Deployment Configuration**.

## Environment Progression Strategy

### Canvas Instance Mapping
- **Development/Test Environment** → Canvas Test Instance (`aculeo.test.instructure.com`)
- **Staging/Beta Environment** → Canvas Beta Instance (`aculeo.beta.instructure.com`)  
- **Production Environment** → Canvas Production Instance (`aculeo.instructure.com`)

## Task 6.1: Environment Variables and Secrets Management

### Environment File Structure

Create the following environment configuration files:

```bash
# Environment configuration files (create in project root)
.env.test           # Test environment configuration
.env.beta           # Beta environment configuration  
.env.prod           # Production environment configuration
.env.local          # Local development (optional)
```

### Test Environment Configuration (.env.test)

```bash
# ==============================================================================
# APPLICATION CONFIGURATION - TEST ENVIRONMENT
# ==============================================================================

# Environment Configuration
ENVIRONMENT=development
DEBUG=false
BASE_URL=https://qa-automation-test.railway.app

# Application Security
SECRET_KEY=test-secret-key-minimum-32-characters-long-change-this
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=None
SESSION_COOKIE_HTTPONLY=true
SESSION_EXPIRE_SECONDS=14400

# ==============================================================================
# CANVAS TEST INSTANCE CONFIGURATION
# ==============================================================================

# Active Canvas Instance
CANVAS_ACTIVE_INSTANCE=test

# Canvas Test Instance Credentials (configure with actual values)
CANVAS_TEST_BASE_URL=https://www.aculeo.test.instructure.com
CANVAS_TEST_CLIENT_ID=your_canvas_test_client_id_here
CANVAS_TEST_CLIENT_SECRET=your_canvas_test_client_secret_here
CANVAS_TEST_PRIVATE_KEY=your_base64_encoded_canvas_test_private_key_here

# Canvas API Configuration
CANVAS_API_TIMEOUT=30
CANVAS_API_MAX_RETRIES=3
CANVAS_RATE_LIMIT_PER_MINUTE=180
CANVAS_RATE_LIMIT_PER_HOUR=4800

# ==============================================================================
# DATABASE AND CACHE CONFIGURATION
# ==============================================================================

# PostgreSQL Database (Railway provides automatically)
# DATABASE_URL=postgresql://user:password@host:port/database

# Redis Cache (Railway provides automatically)  
# REDIS_URL=redis://host:port/0

# ==============================================================================
# MONITORING AND LOGGING
# ==============================================================================

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
STRUCTURED_LOGGING=true

# Health Checks and Monitoring
HEALTH_CHECK_TIMEOUT=30
MONITORING_ENABLED=true
METRICS_ENABLED=true

# ==============================================================================
# SECURITY CONFIGURATION
# ==============================================================================

# CORS Configuration (Canvas iframe compatibility)
CORS_ORIGINS=["https://*.instructure.com", "https://*.aculeo.test.instructure.com"]
CORS_ALLOW_CREDENTIALS=true

# Security Headers
X_FRAME_OPTIONS=ALLOWALL
CONTENT_SECURITY_POLICY=frame-ancestors 'self' https://*.instructure.com

# ==============================================================================
# LTI 1.3 CONFIGURATION
# ==============================================================================

# LTI URLs (adjust domain for your deployment)
LTI_LAUNCH_URL=https://qa-automation-test.railway.app/lti/launch
LTI_LOGIN_URL=https://qa-automation-test.railway.app/lti/login
LTI_JWKS_URL=https://qa-automation-test.railway.app/.well-known/jwks.json

# LTI Security
LTI_JWT_ALGORITHM=RS256
LTI_JWT_EXPIRATION=3600
LTI_NONCE_CACHE_TTL=600

# ==============================================================================
# PERFORMANCE CONFIGURATION
# ==============================================================================

# Application Performance
ASYNC_WORKERS=4
MAX_CONCURRENT_TASKS=10
TASK_TIMEOUT=300

# WebSocket Configuration
WEBSOCKET_PING_INTERVAL=30
WEBSOCKET_PING_TIMEOUT=10
WEBSOCKET_CLOSE_TIMEOUT=10

# QA Framework Performance
MAX_CONTENT_ITEMS_PER_TASK=1000
MAX_TASK_DURATION_SECONDS=1800
PROGRESS_UPDATE_INTERVAL=2
BATCH_SIZE=50
PARALLEL_PROCESSING_LIMIT=5
MEMORY_LIMIT_MB=512
```

### Beta Environment Configuration (.env.beta)

```bash
# ==============================================================================
# APPLICATION CONFIGURATION - BETA ENVIRONMENT
# ==============================================================================

# Environment Configuration
ENVIRONMENT=staging
DEBUG=false
BASE_URL=https://qa-automation-beta.railway.app

# Application Security (use different secret key!)
SECRET_KEY=beta-secret-key-minimum-32-characters-long-change-this
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=None
SESSION_COOKIE_HTTPONLY=true
SESSION_EXPIRE_SECONDS=14400

# ==============================================================================
# CANVAS BETA INSTANCE CONFIGURATION
# ==============================================================================

# Active Canvas Instance
CANVAS_ACTIVE_INSTANCE=beta

# Canvas Beta Instance Credentials
CANVAS_BETA_BASE_URL=https://www.aculeo.beta.instructure.com
CANVAS_BETA_CLIENT_ID=your_canvas_beta_client_id_here
CANVAS_BETA_CLIENT_SECRET=your_canvas_beta_client_secret_here
CANVAS_BETA_PRIVATE_KEY=your_base64_encoded_canvas_beta_private_key_here

# Canvas API Configuration (same as test)
CANVAS_API_TIMEOUT=30
CANVAS_API_MAX_RETRIES=3
CANVAS_RATE_LIMIT_PER_MINUTE=180
CANVAS_RATE_LIMIT_PER_HOUR=4800

# ==============================================================================
# CORS AND SECURITY (Beta specific)
# ==============================================================================

CORS_ORIGINS=["https://*.instructure.com", "https://*.aculeo.beta.instructure.com"]
CONTENT_SECURITY_POLICY=frame-ancestors 'self' https://*.instructure.com

# ==============================================================================
# LTI CONFIGURATION (Beta URLs)
# ==============================================================================

LTI_LAUNCH_URL=https://qa-automation-beta.railway.app/lti/launch
LTI_LOGIN_URL=https://qa-automation-beta.railway.app/lti/login
LTI_JWKS_URL=https://qa-automation-beta.railway.app/.well-known/jwks.json

# [Additional configuration same as test environment]
```

### Production Environment Configuration (.env.prod)

```bash
# ==============================================================================
# APPLICATION CONFIGURATION - PRODUCTION ENVIRONMENT
# ==============================================================================

# Environment Configuration
ENVIRONMENT=production
DEBUG=false
BASE_URL=https://qa-automation.acu.edu.au

# Application Security (STRONG production secret key!)
SECRET_KEY=production-secret-key-minimum-32-characters-very-secure
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=None
SESSION_COOKIE_HTTPONLY=true
SESSION_EXPIRE_SECONDS=14400

# ==============================================================================
# CANVAS PRODUCTION INSTANCE CONFIGURATION
# ==============================================================================

# Active Canvas Instance
CANVAS_ACTIVE_INSTANCE=prod

# Canvas Production Instance Credentials
CANVAS_PROD_BASE_URL=https://www.aculeo.instructure.com
CANVAS_PROD_CLIENT_ID=your_canvas_prod_client_id_here
CANVAS_PROD_CLIENT_SECRET=your_canvas_prod_client_secret_here
CANVAS_PROD_PRIVATE_KEY=your_base64_encoded_canvas_prod_private_key_here

# Canvas API Configuration (production-grade limits)
CANVAS_API_TIMEOUT=30
CANVAS_API_MAX_RETRIES=5
CANVAS_RATE_LIMIT_PER_MINUTE=150  # More conservative for production
CANVAS_RATE_LIMIT_PER_HOUR=4000   # More conservative for production

# ==============================================================================
# PRODUCTION LOGGING AND MONITORING
# ==============================================================================

LOG_LEVEL=WARNING
LOG_FORMAT=json
STRUCTURED_LOGGING=true

# Enhanced monitoring for production
HEALTH_CHECK_TIMEOUT=60
MONITORING_ENABLED=true
METRICS_ENABLED=true
PERFORMANCE_MONITORING=true

# Error Tracking (configure with your service)
SENTRY_DSN=your_production_sentry_dsn_here
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1

# ==============================================================================
# PRODUCTION SECURITY
# ==============================================================================

CORS_ORIGINS=["https://*.instructure.com", "https://*.aculeo.instructure.com"]
CONTENT_SECURITY_POLICY=frame-ancestors 'self' https://*.instructure.com

# Enhanced security headers
STRICT_TRANSPORT_SECURITY=max-age=31536000; includeSubDomains
X_CONTENT_TYPE_OPTIONS=nosniff
X_XSS_PROTECTION=1; mode=block

# ==============================================================================
# PRODUCTION LTI CONFIGURATION
# ==============================================================================

LTI_LAUNCH_URL=https://qa-automation.acu.edu.au/lti/launch
LTI_LOGIN_URL=https://qa-automation.acu.edu.au/lti/login
LTI_JWKS_URL=https://qa-automation.acu.edu.au/.well-known/jwks.json

# [Additional configuration with production-grade settings]
```

## Secrets Management Strategy

### 1. Railway Environment Variables

Configure sensitive values in Railway dashboard:

```bash
# Required Secrets (set in Railway environment variables)
SECRET_KEY                    # Application secret key
CANVAS_TEST_CLIENT_ID        # Canvas test client ID
CANVAS_TEST_CLIENT_SECRET    # Canvas test client secret  
CANVAS_TEST_PRIVATE_KEY      # Canvas test private key (base64)
CANVAS_BETA_CLIENT_ID        # Canvas beta client ID
CANVAS_BETA_CLIENT_SECRET    # Canvas beta client secret
CANVAS_BETA_PRIVATE_KEY      # Canvas beta private key (base64)
CANVAS_PROD_CLIENT_ID        # Canvas production client ID
CANVAS_PROD_CLIENT_SECRET    # Canvas production client secret
CANVAS_PROD_PRIVATE_KEY      # Canvas production private key (base64)
```

### 2. Private Key Encoding

Canvas LTI 1.3 private keys must be base64 encoded:

```bash
# Encode private key for storage
base64 -i canvas_private_key.pem | tr -d '\n' > canvas_private_key.base64

# Use the base64 string in environment variables
CANVAS_TEST_PRIVATE_KEY=LS0tLS1CRUdJTi...your_base64_key...FURFI0FURS0tLS0t
```

### 3. Environment Variable Validation

The application validates required environment variables on startup:

```python
# Required variables for each environment
REQUIRED_TEST_VARS = [
    "CANVAS_TEST_BASE_URL",
    "CANVAS_TEST_CLIENT_ID", 
    "CANVAS_TEST_PRIVATE_KEY"
]

REQUIRED_BETA_VARS = [
    "CANVAS_BETA_BASE_URL",
    "CANVAS_BETA_CLIENT_ID",
    "CANVAS_BETA_PRIVATE_KEY"  
]

REQUIRED_PROD_VARS = [
    "CANVAS_PROD_BASE_URL", 
    "CANVAS_PROD_CLIENT_ID",
    "CANVAS_PROD_PRIVATE_KEY"
]
```

## Security Best Practices

### 1. Secret Key Requirements
- Minimum 32 characters
- Use cryptographically secure random generation
- Different keys for each environment
- Regular rotation schedule

### 2. Canvas Credentials Security
- Store in Railway environment variables only
- Never commit to version control
- Use minimal required Canvas permissions
- Regular audit of Canvas developer key usage

### 3. Database Security
- Railway provides encrypted PostgreSQL
- Automatic backups enabled
- Connection string never exposed in logs
- Read-only replicas for analytics (if needed)

### 4. Network Security
- HTTPS only for all environments
- Proper CORS configuration for Canvas iframe
- Security headers configured
- Canvas CSP compliance

## Deployment Commands

### Test Environment Deployment

```bash
# Deploy to Railway test environment
railway login
railway environment test
railway deploy

# Or deploy with specific environment
railway up --environment test
```

### Environment Switching

```bash
# Switch Railway environments
railway environment test    # Switch to test
railway environment beta    # Switch to beta  
railway environment prod    # Switch to production

# Deploy to current environment
railway deploy
```

### Manual Environment Setup

```bash
# Copy environment file for local testing
cp .env.test .env

# Start application with test configuration
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Configuration Validation

The application includes startup validation:

```python
# Validate environment configuration on startup
async def validate_environment():
    """Validate all required environment variables are present."""
    
    # Check active Canvas instance configuration
    active_instance = settings.canvas_active_instance
    required_vars = get_required_vars_for_instance(active_instance)
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var.lower(), None):
            missing_vars.append(var)
    
    if missing_vars:
        raise EnvironmentError(f"Missing required variables: {missing_vars}")
    
    # Validate Canvas connectivity
    canvas_config = settings.get_canvas_instance_config(active_instance)
    if not await test_canvas_connectivity(canvas_config):
        raise EnvironmentError(f"Cannot connect to Canvas {active_instance}")
```

## Next Steps

After completing Task 6.1 (Environment Configuration):

1. **Task 6.2**: Set up automated deployment pipeline
2. **Task 6.3**: Configure database backup procedures  
3. **Task 6.4**: Implement security scanning
4. **Task 6.5**: Create operational runbooks
5. **Task 6.6**: Set up monitoring and alerting

## Canvas Test Instance Setup

To begin testing with the Canvas test instance:

1. **Configure Canvas Test LTI Tool**:
   - Login to Canvas Test as administrator
   - Go to Admin → Developer Keys → +LTI Key
   - Configure with test environment URLs

2. **Deploy Test Environment**:
   - Configure .env.test with Canvas test credentials
   - Deploy to Railway test environment
   - Validate health checks

3. **Test LTI Integration**:
   - Install tool in test course
   - Verify LTI 1.3 authentication
   - Test QA automation functionality

## Support and Troubleshooting

### Health Check Endpoints
- `/health` - Application health
- `/health/canvas` - Canvas connectivity
- `/health/database` - Database connectivity
- `/health/cache` - Redis cache status

### Configuration Testing
```bash
# Test Canvas configuration
curl "https://qa-automation-test.railway.app/health/canvas?instance=test"

# Test application health
curl "https://qa-automation-test.railway.app/health"
```

### Common Issues
1. **Canvas Authentication Failures**: Check private key encoding and client ID
2. **CORS Issues**: Verify Canvas domain in CORS_ORIGINS
3. **Database Connection**: Railway provides DATABASE_URL automatically
4. **Rate Limiting**: Check Canvas API limits and rate limiter configuration 