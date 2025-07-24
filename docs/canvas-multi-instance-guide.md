# Canvas Multi-Instance Testing Guide

## Overview

The QA Automation LTI Tool supports multiple Canvas instances to enable safe progression from testing to production deployment. This guide covers configuration, testing, and deployment across ACU's Canvas environments.

## Canvas Instance Progression

### Testing Flow: Test → Beta → Prod

1. **Test Environment** (`www.aculeo.test.instructure.com`)
   - Initial development and functional testing
   - Safe environment for breaking changes
   - User acceptance testing with test data

2. **Beta Environment** (`www.aculeo.beta.instructure.com`)
   - Pre-production validation
   - Integration testing with real-like data
   - Performance and load testing

3. **Production Environment** (`www.aculeo.instructure.com`)
   - Live Canvas instance
   - Real user data and workflows
   - Full monitoring and error tracking

## Configuration Setup

### Environment Files

Create instance-specific environment files:

```bash
# Copy example files and configure
cp .env.test.example .env.test
cp .env.beta.example .env.beta
cp .env.prod.example .env.prod
```

### Canvas Instance Configuration

Each instance requires:

1. **Canvas Base URL**: The Canvas instance URL
2. **Client ID**: LTI 1.3 client identifier from Canvas
3. **Client Secret**: Optional Canvas client secret
4. **Private Key**: Base64-encoded LTI 1.3 private key

### Example Configuration

```bash
# Test Instance
CANVAS_ACTIVE_INSTANCE=test
CANVAS_TEST_BASE_URL=https://www.aculeo.test.instructure.com
CANVAS_TEST_CLIENT_ID=your_test_client_id
CANVAS_TEST_PRIVATE_KEY=your_base64_encoded_test_private_key

# Beta Instance  
CANVAS_BETA_BASE_URL=https://www.aculeo.beta.instructure.com
CANVAS_BETA_CLIENT_ID=your_beta_client_id
CANVAS_BETA_PRIVATE_KEY=your_base64_encoded_beta_private_key

# Production Instance
CANVAS_PROD_BASE_URL=https://www.aculeo.instructure.com
CANVAS_PROD_CLIENT_ID=your_prod_client_id
CANVAS_PROD_PRIVATE_KEY=your_base64_encoded_prod_private_key
```

## Running with Different Instances

### Method 1: Environment Files

```bash
# Test with Test instance
cp .env.test .env
uvicorn app.main:app --reload

# Test with Beta instance
cp .env.beta .env
uvicorn app.main:app --reload

# Test with Production instance
cp .env.prod .env
uvicorn app.main:app --reload
```

### Method 2: Environment Variables

```bash
# Switch to Test instance
export CANVAS_ACTIVE_INSTANCE=test
uvicorn app.main:app --reload

# Switch to Beta instance
export CANVAS_ACTIVE_INSTANCE=beta
uvicorn app.main:app --reload

# Switch to Production instance
export CANVAS_ACTIVE_INSTANCE=prod
uvicorn app.main:app --reload
```

### Method 3: Runtime Switching (Development)

```bash
# Start with any instance
uvicorn app.main:app --reload

# Switch instances via API (requires authentication)
curl -X POST "http://localhost:8000/health/canvas/switch-instance?instance_name=beta" \
  -H "Authorization: Bearer your_token"
```

## Canvas LTI Registration

Each Canvas instance requires separate LTI tool registration:

### 1. Test Instance Registration

1. Login to Canvas Test as administrator
2. Navigate to Admin → Developer Keys
3. Create new LTI Key with these settings:
   - **Key Name**: ACU QA Automation Tool (Test)
   - **Owner Email**: your-email@acu.edu.au
   - **Redirect URIs**: `https://your-qa-tool-test.domain.com/lti/launch`
   - **Target Link URI**: `https://your-qa-tool-test.domain.com/lti/launch`
   - **OpenID Connect Initiation URL**: `https://your-qa-tool-test.domain.com/lti/login`
   - **JWK Method**: Public JWK URL
   - **Public JWK URL**: `https://your-qa-tool-test.domain.com/.well-known/jwks.json`

### 2. Beta Instance Registration

Repeat the process for Canvas Beta with beta-specific URLs.

### 3. Production Instance Registration

Repeat the process for Canvas Production with production URLs.

## Health Check and Monitoring

### Check All Instances

```bash
# Check all configured instances
curl "http://localhost:8000/health/canvas"

# Check specific instance
curl "http://localhost:8000/health/canvas?instance=test"
curl "http://localhost:8000/health/canvas?instance=beta"
curl "http://localhost:8000/health/canvas?instance=prod"
```

### Get Instance Information

```bash
# Get all instance configurations
curl "http://localhost:8000/health/canvas/instances"
```

### Example Response

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "active_instance": "test",
  "instance_summary": {
    "active_instance": "test",
    "active_instance_url": "https://www.aculeo.test.instructure.com",
    "available_instances": ["test", "beta", "prod"],
    "total_instances": 3,
    "instances_detail": {
      "test": {
        "base_url": "https://www.aculeo.test.instructure.com",
        "description": "ACU Canvas Test Environment",
        "configured": true
      },
      "beta": {
        "base_url": "https://www.aculeo.beta.instructure.com", 
        "description": "ACU Canvas Beta Environment",
        "configured": true
      },
      "prod": {
        "base_url": "https://www.aculeo.instructure.com",
        "description": "ACU Canvas Production Environment",
        "configured": true
      }
    }
  }
}
```

## Testing Workflow

### Phase 1: Test Instance Validation

1. **Configure Test Environment**
   ```bash
   export CANVAS_ACTIVE_INSTANCE=test
   ```

2. **Run Health Checks**
   ```bash
   curl "http://localhost:8000/health/canvas?instance=test"
   ```

3. **Test LTI Launch**
   - Launch tool from Canvas Test course
   - Verify authentication flow
   - Test QA automation functionality

4. **Run UAT Scenarios**
   ```bash
   python -m pytest tests/test_user_acceptance.py -v
   ```

### Phase 2: Beta Instance Validation

1. **Switch to Beta**
   ```bash
   export CANVAS_ACTIVE_INSTANCE=beta
   ```

2. **Validate Integration**
   - Test with beta course data
   - Verify performance characteristics
   - Test error handling scenarios

3. **Load Testing**
   - Simulate multiple concurrent users
   - Test large course processing
   - Monitor resource usage

### Phase 3: Production Deployment

1. **Final Validation**
   ```bash
   export CANVAS_ACTIVE_INSTANCE=prod
   ```

2. **Production Readiness Check**
   - Verify all health checks pass
   - Confirm monitoring setup
   - Test rollback procedures

3. **Go Live**
   - Deploy to production infrastructure
   - Monitor initial usage
   - Be ready for rollback if needed

## Troubleshooting

### Common Issues

1. **Instance Not Configured**
   ```bash
   # Check available instances
   curl "http://localhost:8000/health/canvas/instances"
   
   # Verify environment variables
   echo $CANVAS_TEST_CLIENT_ID
   echo $CANVAS_TEST_PRIVATE_KEY
   ```

2. **LTI Authentication Fails**
   ```bash
   # Validate instance configuration
   curl "http://localhost:8000/health/canvas?instance=test"
   
   # Check Canvas developer key configuration
   # Verify redirect URIs match your deployment URLs
   ```

3. **Rate Limiting Issues**
   ```bash
   # Check rate limit status
   curl "http://localhost:8000/health/performance"
   
   # Reset rate limits if needed (admin only)
   curl -X POST "http://localhost:8000/health/rate-limit/reset"
   ```

### Error Codes

- **400**: Instance not configured or invalid request
- **401**: Authentication required for instance switching
- **503**: Instance health check failed
- **500**: Internal server error during instance operations

## Security Considerations

### Private Key Management

- Store private keys securely (never commit to version control)
- Use different private keys for each instance
- Rotate keys regularly according to ACU security policy

### Environment Separation

- Test data should not contain production information
- Beta environment should use anonymized data when possible
- Production credentials should be strictly controlled

### Access Control

- Instance switching requires authentication
- Monitor instance switching in production
- Log all configuration changes

## Deployment Automation

### Railway Deployment

Update `railway.toml` for instance-specific deployments:

```toml
[environments.test]
variables = { 
  ENVIRONMENT = "development",
  CANVAS_ACTIVE_INSTANCE = "test"
}

[environments.beta]
variables = { 
  ENVIRONMENT = "staging",
  CANVAS_ACTIVE_INSTANCE = "beta"
}

[environments.production]
variables = { 
  ENVIRONMENT = "production", 
  CANVAS_ACTIVE_INSTANCE = "prod"
}
```

### GitHub Actions

Example workflow for multi-instance testing:

```yaml
name: Multi-Instance Canvas Testing

on: [push, pull_request]

jobs:
  test-instances:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        instance: [test, beta]
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: pip install -r requirements-dev.txt
    
    - name: Test ${{ matrix.instance }} instance
      env:
        CANVAS_ACTIVE_INSTANCE: ${{ matrix.instance }}
        CANVAS_TEST_CLIENT_ID: ${{ secrets.CANVAS_TEST_CLIENT_ID }}
        CANVAS_BETA_CLIENT_ID: ${{ secrets.CANVAS_BETA_CLIENT_ID }}
      run: |
        python -m pytest tests/test_canvas_integration.py
```

## Monitoring and Alerts

### Production Monitoring

- Set up alerts for instance health check failures
- Monitor Canvas API rate limit usage
- Track instance switching events
- Alert on configuration validation failures

### Metrics to Track

- Instance health check response times
- Canvas API error rates by instance
- Rate limit utilization by instance
- LTI authentication success rates

This multi-instance approach ensures safe, systematic testing and deployment across ACU's Canvas environments while maintaining system reliability and user experience. 