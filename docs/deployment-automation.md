# Deployment Automation & Operations Guide

## Overview

This guide covers automated deployment, rollback procedures, and operational workflows for the Canvas QA Automation Tool. This documentation supports **Story 2.4 Task 6.2: Automated Deployment Pipeline**.

## Deployment Pipeline Architecture

### Environment Progression
```
Development → Test → Beta → Production
     ↓         ↓      ↓         ↓
   Local    Railway  Railway  Railway
  Testing    Test    Beta     Prod
```

### Automated Deployment Flow
1. **Code Commit** → Triggers deployment pipeline
2. **Build & Test** → Automated testing and validation
3. **Deploy to Test** → Canvas test instance integration
4. **User Acceptance Testing** → Validation with Learning Designers
5. **Deploy to Beta** → Canvas beta instance validation
6. **Production Deployment** → Canvas production instance deployment

## Railway Deployment Commands

### Basic Deployment Commands

```bash
# Login to Railway
railway login

# List available projects and environments
railway status
railway environment list

# Deploy to specific environment
railway environment test
railway deploy

railway environment beta  
railway deploy

railway environment production
railway deploy
```

### Environment-Specific Deployment

```bash
# Deploy to Test Environment
railway deploy --environment test

# Deploy to Beta Environment  
railway deploy --environment beta

# Deploy to Production Environment
railway deploy --environment production
```

### Advanced Deployment Commands

```bash
# Deploy with specific service configuration
railway up --service qa-automation-test
railway up --service qa-automation-beta
railway up --service qa-automation-prod

# Deploy with custom variables
railway deploy --environment test --variable "LOG_LEVEL=DEBUG"

# Deploy from specific branch
railway deploy --environment test --detach --branch feature/new-feature
```

## Automated Deployment Scripts

### Test Environment Deployment Script

```bash
#!/bin/bash
# deploy-test.sh - Deploy to Canvas Test Environment

set -e

echo "🚀 Deploying QA Automation Tool to Test Environment..."

# Validate environment
if [ -z "$CANVAS_TEST_CLIENT_ID" ]; then
    echo "❌ Error: CANVAS_TEST_CLIENT_ID not configured"
    exit 1
fi

# Set Railway environment
railway environment test

# Deploy application
echo "📦 Deploying application..."
railway deploy

# Wait for deployment
echo "⏳ Waiting for deployment to complete..."
sleep 30

# Health check
echo "🏥 Running health checks..."
HEALTH_URL=$(railway status --json | jq -r '.deployments[0].url')/health
if curl -f "$HEALTH_URL" > /dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    exit 1
fi

# Canvas connectivity check
echo "🎨 Testing Canvas connectivity..."
CANVAS_HEALTH_URL="$HEALTH_URL/canvas?instance=test"
if curl -f "$CANVAS_HEALTH_URL" > /dev/null 2>&1; then
    echo "✅ Canvas test connectivity confirmed"
else
    echo "⚠️ Canvas test connectivity issues"
fi

echo "🎉 Test deployment completed successfully!"
echo "🔗 Access URL: $(railway status --json | jq -r '.deployments[0].url')"
```

### Beta Environment Deployment Script

```bash
#!/bin/bash
# deploy-beta.sh - Deploy to Canvas Beta Environment

set -e

echo "🚀 Deploying QA Automation Tool to Beta Environment..."

# Validate test deployment first
echo "✓ Validating test environment..."
if ! ./scripts/validate-test.sh; then
    echo "❌ Test environment validation failed. Aborting beta deployment."
    exit 1
fi

# Set Railway environment
railway environment beta

# Deploy application
echo "📦 Deploying to beta..."
railway deploy

# Wait for deployment
echo "⏳ Waiting for beta deployment..."
sleep 45

# Comprehensive health checks
echo "🏥 Running beta health checks..."
./scripts/health-check-beta.sh

echo "🎉 Beta deployment completed successfully!"
```

### Production Deployment Script

```bash
#!/bin/bash
# deploy-production.sh - Deploy to Canvas Production Environment

set -e

echo "🚀 Deploying QA Automation Tool to Production Environment..."

# Validate prerequisites
echo "✓ Validating deployment prerequisites..."
if ! ./scripts/validate-production-readiness.sh; then
    echo "❌ Production readiness validation failed. Aborting deployment."
    exit 1
fi

# Create deployment backup point
echo "💾 Creating deployment backup point..."
BACKUP_POINT=$(date +"%Y%m%d_%H%M%S")
railway environment production
CURRENT_DEPLOYMENT=$(railway status --json | jq -r '.deployments[0].id')
echo "Backup point: $BACKUP_POINT (deployment: $CURRENT_DEPLOYMENT)"

# Deploy with monitoring
echo "📦 Deploying to production with monitoring..."
railway deploy

# Progressive health checking
echo "🏥 Running progressive health checks..."
./scripts/health-check-production.sh

# Post-deployment validation
echo "✅ Running post-deployment validation..."
./scripts/validate-production-deployment.sh

echo "🎉 Production deployment completed successfully!"
echo "📊 Monitor at: $(railway status --json | jq -r '.deployments[0].url')/health"
```

## Rollback Procedures

### Automatic Rollback Triggers

```bash
#!/bin/bash
# rollback-monitor.sh - Monitor deployment and trigger rollback if needed

DEPLOYMENT_URL=$(railway status --json | jq -r '.deployments[0].url')
HEALTH_ENDPOINT="$DEPLOYMENT_URL/health"

# Monitor health for 10 minutes
for i in {1..20}; do
    if ! curl -f "$HEALTH_ENDPOINT" > /dev/null 2>&1; then
        echo "❌ Health check failed (attempt $i/20)"
        if [ $i -ge 5 ]; then
            echo "🔄 Triggering automatic rollback..."
            ./scripts/rollback.sh
            exit 1
        fi
    else
        echo "✅ Health check passed (attempt $i/20)"
    fi
    sleep 30
done

echo "✅ Deployment stable after 10 minutes"
```

### Manual Rollback Script

```bash
#!/bin/bash
# rollback.sh - Manual rollback to previous deployment

set -e

ENVIRONMENT=${1:-production}

echo "🔄 Rolling back $ENVIRONMENT environment..."

# Set environment
railway environment $ENVIRONMENT

# Get deployment history
DEPLOYMENTS=$(railway deployments --json)
CURRENT_DEPLOYMENT=$(echo "$DEPLOYMENTS" | jq -r '.[0].id')
PREVIOUS_DEPLOYMENT=$(echo "$DEPLOYMENTS" | jq -r '.[1].id')

if [ "$PREVIOUS_DEPLOYMENT" = "null" ]; then
    echo "❌ No previous deployment found for rollback"
    exit 1
fi

echo "Current deployment: $CURRENT_DEPLOYMENT"
echo "Rolling back to: $PREVIOUS_DEPLOYMENT"

# Confirm rollback
read -p "Are you sure you want to rollback? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled"
    exit 1
fi

# Perform rollback
railway redeploy $PREVIOUS_DEPLOYMENT

# Wait and validate
echo "⏳ Waiting for rollback to complete..."
sleep 60

# Health check after rollback
if ./scripts/health-check.sh $ENVIRONMENT; then
    echo "✅ Rollback completed successfully"
else
    echo "❌ Rollback health check failed"
    exit 1
fi
```

### Emergency Rollback Procedure

```bash
#!/bin/bash
# emergency-rollback.sh - Emergency rollback with minimal validation

set -e

echo "🚨 EMERGENCY ROLLBACK INITIATED"

ENVIRONMENT=${1:-production}
railway environment $ENVIRONMENT

# Get last known good deployment
LAST_GOOD=$(railway deployments --json | jq -r '.[1].id')

# Immediate rollback
railway redeploy $LAST_GOOD --force

echo "🚨 Emergency rollback completed to deployment: $LAST_GOOD"
echo "📞 Notify operations team immediately"
```

## Health Check Scripts

### Comprehensive Health Check

```bash
#!/bin/bash
# health-check.sh - Comprehensive health check

ENVIRONMENT=${1:-test}
BASE_URL=$(railway status --environment $ENVIRONMENT --json | jq -r '.deployments[0].url')

echo "🏥 Running health checks for $ENVIRONMENT environment..."
echo "🔗 Base URL: $BASE_URL"

# Basic application health
if curl -f "$BASE_URL/health" > /dev/null 2>&1; then
    echo "✅ Application health: OK"
else
    echo "❌ Application health: FAILED"
    exit 1
fi

# Database connectivity
if curl -f "$BASE_URL/health/database" > /dev/null 2>&1; then
    echo "✅ Database connectivity: OK"
else
    echo "❌ Database connectivity: FAILED"
    exit 1
fi

# Redis connectivity
if curl -f "$BASE_URL/health/cache" > /dev/null 2>&1; then
    echo "✅ Redis connectivity: OK"
else
    echo "❌ Redis connectivity: FAILED"
    exit 1
fi

# Canvas connectivity (environment-specific)
CANVAS_INSTANCE=""
case $ENVIRONMENT in
    "test") CANVAS_INSTANCE="test" ;;
    "beta") CANVAS_INSTANCE="beta" ;;
    "production") CANVAS_INSTANCE="prod" ;;
esac

if curl -f "$BASE_URL/health/canvas?instance=$CANVAS_INSTANCE" > /dev/null 2>&1; then
    echo "✅ Canvas $CANVAS_INSTANCE connectivity: OK"
else
    echo "❌ Canvas $CANVAS_INSTANCE connectivity: FAILED"
    exit 1
fi

echo "✅ All health checks passed for $ENVIRONMENT"
```

### Performance Validation Script

```bash
#!/bin/bash
# performance-check.sh - Performance validation

ENVIRONMENT=${1:-test}
BASE_URL=$(railway status --environment $ENVIRONMENT --json | jq -r '.deployments[0].url')

echo "⚡ Running performance checks for $ENVIRONMENT..."

# Response time check
RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' "$BASE_URL/health")
if (( $(echo "$RESPONSE_TIME < 2.0" | bc -l) )); then
    echo "✅ Response time: ${RESPONSE_TIME}s (< 2s)"
else
    echo "⚠️ Response time: ${RESPONSE_TIME}s (> 2s)"
fi

# Memory usage check
MEMORY_USAGE=$(curl -s "$BASE_URL/health/metrics" | jq -r '.memory_usage_mb')
if [ "$MEMORY_USAGE" -lt 400 ]; then
    echo "✅ Memory usage: ${MEMORY_USAGE}MB (< 400MB)"
else
    echo "⚠️ Memory usage: ${MEMORY_USAGE}MB (> 400MB)"
fi

# Load test (light)
echo "🔄 Running light load test..."
for i in {1..10}; do
    curl -s "$BASE_URL/health" > /dev/null &
done
wait

echo "✅ Performance validation completed"
```

## Deployment Validation

### Production Readiness Validation

```bash
#!/bin/bash
# validate-production-readiness.sh - Validate production deployment readiness

echo "🔍 Validating production deployment readiness..."

# Check environment variables
REQUIRED_VARS=(
    "CANVAS_PROD_CLIENT_ID"
    "CANVAS_PROD_PRIVATE_KEY"
    "SECRET_KEY"
    "DATABASE_URL"
    "REDIS_URL"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing required variable: $var"
        exit 1
    fi
done

echo "✅ Environment variables validated"

# Validate beta environment health
echo "🧪 Validating beta environment..."
if ! ./scripts/health-check.sh beta; then
    echo "❌ Beta environment health check failed"
    exit 1
fi

# Security check
echo "🔐 Running security validation..."
if [ "$DEBUG" = "true" ]; then
    echo "❌ Debug mode enabled in production"
    exit 1
fi

if [ ${#SECRET_KEY} -lt 32 ]; then
    echo "❌ Production secret key too short"
    exit 1
fi

echo "✅ Production readiness validation passed"
```

### Canvas Integration Validation

```bash
#!/bin/bash
# validate-canvas-integration.sh - Validate Canvas integration

ENVIRONMENT=${1:-test}
BASE_URL=$(railway status --environment $ENVIRONMENT --json | jq -r '.deployments[0].url')

echo "🎨 Validating Canvas integration for $ENVIRONMENT..."

# Get Canvas instance for environment
CANVAS_INSTANCE=""
case $ENVIRONMENT in
    "test") CANVAS_INSTANCE="test" ;;
    "beta") CANVAS_INSTANCE="beta" ;;
    "production") CANVAS_INSTANCE="prod" ;;
esac

# Test Canvas API connectivity
CANVAS_HEALTH=$(curl -s "$BASE_URL/health/canvas?instance=$CANVAS_INSTANCE")
if echo "$CANVAS_HEALTH" | jq -r '.status' | grep -q "healthy"; then
    echo "✅ Canvas API connectivity: OK"
else
    echo "❌ Canvas API connectivity: FAILED"
    echo "Response: $CANVAS_HEALTH"
    exit 1
fi

# Test LTI endpoints
LTI_ENDPOINTS=(
    "/lti/login"
    "/.well-known/jwks.json"
)

for endpoint in "${LTI_ENDPOINTS[@]}"; do
    if curl -f "$BASE_URL$endpoint" > /dev/null 2>&1; then
        echo "✅ LTI endpoint $endpoint: OK"
    else
        echo "❌ LTI endpoint $endpoint: FAILED"
        exit 1
    fi
done

echo "✅ Canvas integration validation passed"
```

## Monitoring and Alerting

### Deployment Monitoring

```bash
#!/bin/bash
# monitor-deployment.sh - Monitor deployment status

ENVIRONMENT=${1:-production}
DURATION=${2:-600}  # 10 minutes default

echo "📊 Monitoring $ENVIRONMENT deployment for ${DURATION}s..."

START_TIME=$(date +%s)
ALERTS_SENT=0

while [ $(($(date +%s) - START_TIME)) -lt $DURATION ]; do
    if ! ./scripts/health-check.sh $ENVIRONMENT > /dev/null 2>&1; then
        ALERTS_SENT=$((ALERTS_SENT + 1))
        echo "⚠️ Health check failed (alert #$ALERTS_SENT)"
        
        if [ $ALERTS_SENT -ge 3 ]; then
            echo "🚨 Multiple health check failures - considering rollback"
            # Add alerting logic here (Slack, email, etc.)
        fi
    else
        ALERTS_SENT=0  # Reset alert counter on successful check
        echo "✅ Health check passed"
    fi
    
    sleep 30
done

echo "📊 Monitoring completed for $ENVIRONMENT"
```

### Log Monitoring

```bash
#!/bin/bash
# monitor-logs.sh - Monitor application logs for errors

ENVIRONMENT=${1:-production}

echo "📜 Monitoring logs for $ENVIRONMENT..."

# Stream Railway logs and monitor for errors
railway logs --environment $ENVIRONMENT --follow | while read line; do
    # Check for error patterns
    if echo "$line" | grep -i "error\|exception\|failed\|timeout"; then
        echo "🚨 Error detected: $line"
        # Add alerting logic here
    fi
    
    # Check for Canvas API errors
    if echo "$line" | grep -i "canvas.*error\|rate.limit\|unauthorized"; then
        echo "🎨 Canvas API issue: $line"
        # Add Canvas-specific alerting
    fi
done
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy QA Automation Tool

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run tests
        run: pytest
      - name: Run security scan
        run: bandit -r app/

  deploy-test:
    needs: test
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Test
        run: ./scripts/deploy-test.sh
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}

  deploy-production:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Production
        run: ./scripts/deploy-production.sh
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## Usage Instructions

### Initial Setup

1. **Configure Railway CLI**:
   ```bash
   npm install -g @railway/cli
   railway login
   ```

2. **Set up environments**:
   ```bash
   # Create or link Railway project
   railway init
   
   # Configure environments
   railway environment create test
   railway environment create beta
   railway environment create production
   ```

3. **Configure secrets**:
   ```bash
   # Set secrets for each environment
   railway environment test
   railway variables set CANVAS_TEST_CLIENT_ID="your_test_client_id"
   railway variables set CANVAS_TEST_PRIVATE_KEY="your_test_private_key"
   
   railway environment production
   railway variables set CANVAS_PROD_CLIENT_ID="your_prod_client_id"
   railway variables set CANVAS_PROD_PRIVATE_KEY="your_prod_private_key"
   ```

### Daily Operations

1. **Deploy to Test**:
   ```bash
   ./scripts/deploy-test.sh
   ```

2. **Promote to Beta**:
   ```bash
   ./scripts/deploy-beta.sh
   ```

3. **Deploy to Production**:
   ```bash
   ./scripts/deploy-production.sh
   ```

4. **Monitor Deployment**:
   ```bash
   ./scripts/monitor-deployment.sh production 300
   ```

5. **Emergency Rollback**:
   ```bash
   ./scripts/emergency-rollback.sh production
   ```

## Best Practices

### Deployment Safety
- Always validate test environment before promoting
- Use progressive deployment with health checks
- Maintain deployment backup points
- Monitor for 10+ minutes after production deployment

### Rollback Strategy
- Automated rollback on health check failures
- Manual rollback procedures documented
- Emergency rollback for critical issues
- Rollback validation required

### Monitoring
- Continuous health monitoring
- Canvas API connectivity monitoring
- Performance metric tracking
- Error rate alerting

This deployment automation framework ensures safe, reliable deployments of the Canvas QA Automation Tool across all environments while providing robust rollback capabilities and comprehensive monitoring. 