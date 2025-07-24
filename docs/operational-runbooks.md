# Operational Runbooks & Incident Response

## Overview

This document provides comprehensive operational runbooks and incident response procedures for the Canvas QA Automation Tool. This documentation supports **Story 2.4 Task 6.5: Operational Runbooks and Incident Response Procedures**.

## Table of Contents

1. [System Overview](#system-overview)
2. [Daily Operations](#daily-operations)
3. [Incident Response](#incident-response)
4. [Canvas-Specific Issues](#canvas-specific-issues)
5. [Performance Issues](#performance-issues)
6. [Database Operations](#database-operations)
7. [Security Incidents](#security-incidents)
8. [Disaster Recovery](#disaster-recovery)
9. [Maintenance Procedures](#maintenance-procedures)
10. [Contact Information](#contact-information)

## System Overview

### Architecture Components
- **Application**: FastAPI Python application on Railway
- **Database**: PostgreSQL (Railway managed)
- **Cache**: Redis (Railway managed)
- **Canvas Integration**: LTI 1.3 with multiple Canvas instances
- **Monitoring**: Health checks and performance metrics

### Environment Instances
- **Test**: Canvas Test instance (`aculeo.test.instructure.com`)
- **Beta**: Canvas Beta instance (`aculeo.beta.instructure.com`)
- **Production**: Canvas Production instance (`aculeo.instructure.com`)

### Key URLs
- **Test**: `https://qa-automation-test.railway.app`
- **Beta**: `https://qa-automation-beta.railway.app`
- **Production**: `https://qa-automation.acu.edu.au`

## Daily Operations

### Morning Health Check Routine

```bash
#!/bin/bash
# Morning health check for all environments

echo "🌅 Starting morning health check routine..."

ENVIRONMENTS=("test" "beta" "production")

for env in "${ENVIRONMENTS[@]}"; do
    echo "🏥 Checking $env environment..."
    
    # Basic health check
    if ./scripts/health-check.sh $env; then
        echo "✅ $env: Healthy"
    else
        echo "🚨 $env: Issues detected"
        # Trigger alert
        ./scripts/alert.sh "$env environment health check failed"
    fi
    
    # Performance check
    ./scripts/performance-check.sh $env
done

echo "✅ Morning health check completed"
```

### Canvas API Health Monitoring

```bash
#!/bin/bash
# Monitor Canvas API health across all instances

echo "🎨 Checking Canvas API health..."

INSTANCES=("test" "beta" "prod")

for instance in "${INSTANCES[@]}"; do
    HEALTH_RESPONSE=$(curl -s "https://qa-automation-$instance.railway.app/health/canvas?instance=$instance")
    STATUS=$(echo "$HEALTH_RESPONSE" | jq -r '.status')
    
    if [ "$STATUS" = "healthy" ]; then
        echo "✅ Canvas $instance: Healthy"
    else
        echo "🚨 Canvas $instance: $STATUS"
        # Log Canvas-specific details
        echo "$HEALTH_RESPONSE" | jq '.canvas_details'
    fi
done
```

### User Activity Monitoring

```bash
#!/bin/bash
# Monitor user activity and QA task execution

echo "👥 Monitoring user activity..."

# Check active sessions
ACTIVE_SESSIONS=$(curl -s "https://qa-automation.acu.edu.au/health/metrics" | jq -r '.active_sessions')
echo "Active sessions: $ACTIVE_SESSIONS"

# Check QA tasks in progress
ACTIVE_TASKS=$(curl -s "https://qa-automation.acu.edu.au/health/metrics" | jq -r '.active_qa_tasks')
echo "Active QA tasks: $ACTIVE_TASKS"

# Check recent errors
ERROR_COUNT=$(curl -s "https://qa-automation.acu.edu.au/health/metrics" | jq -r '.recent_errors')
if [ "$ERROR_COUNT" -gt 5 ]; then
    echo "⚠️ High error count: $ERROR_COUNT"
    ./scripts/alert.sh "High error count detected: $ERROR_COUNT errors"
fi
```

## Incident Response

### Incident Severity Levels

#### Severity 1 - Critical (Response: Immediate)
- **Description**: Complete service outage, Canvas integration failure
- **Response Time**: 15 minutes
- **Examples**: 
  - Application completely down
  - Canvas authentication failure preventing all access
  - Data corruption or loss

#### Severity 2 - High (Response: 30 minutes)  
- **Description**: Partial service degradation, performance issues
- **Response Time**: 30 minutes
- **Examples**:
  - Slow response times (>5 seconds)
  - Canvas API rate limiting affecting users
  - Database connectivity issues

#### Severity 3 - Medium (Response: 2 hours)
- **Description**: Minor functionality issues, non-critical features
- **Response Time**: 2 hours
- **Examples**:
  - Individual QA task failures
  - WebSocket connection issues
  - Non-critical UI problems

#### Severity 4 - Low (Response: Next business day)
- **Description**: Cosmetic issues, feature requests
- **Response Time**: Next business day
- **Examples**:
  - UI styling issues
  - Documentation updates
  - Performance optimizations

### Incident Response Playbooks

#### 1. Application Down (Severity 1)

**Symptoms**: Health checks failing, 500/502 errors, application unreachable

**Response Steps**:

1. **Immediate Assessment** (0-5 minutes)
   ```bash
   # Check application status
   curl -f https://qa-automation.acu.edu.au/health
   
   # Check Railway deployment status
   railway status --environment production
   
   # Check recent deployments
   railway deployments --environment production --limit 5
   ```

2. **Emergency Actions** (5-15 minutes)
   ```bash
   # If recent deployment caused issue, rollback immediately
   ./scripts/emergency-rollback.sh production
   
   # If infrastructure issue, check Railway status
   railway logs --environment production --tail 100
   ```

3. **Communication** (Immediate)
   - Notify stakeholders via Slack/email
   - Update status page if available
   - Log incident in incident management system

4. **Resolution Verification**
   ```bash
   # Verify rollback success
   ./scripts/health-check.sh production
   
   # Test Canvas integration
   ./scripts/validate-canvas-integration.sh production
   ```

#### 2. Canvas Authentication Failure (Severity 1)

**Symptoms**: LTI launch failures, 401 unauthorized errors from Canvas

**Response Steps**:

1. **Diagnosis** (0-10 minutes)
   ```bash
   # Check Canvas API connectivity
   curl -s "https://qa-automation.acu.edu.au/health/canvas?instance=prod"
   
   # Check LTI endpoint availability
   curl -f "https://qa-automation.acu.edu.au/.well-known/jwks.json"
   ```

2. **Canvas-Specific Checks**
   - Verify Canvas developer key status in Canvas admin
   - Check private key configuration
   - Validate client ID matches Canvas configuration
   - Check Canvas maintenance status

3. **Resolution Actions**
   ```bash
   # Restart application to refresh Canvas tokens
   railway restart --environment production
   
   # Test Canvas connectivity after restart
   ./scripts/validate-canvas-integration.sh production
   ```

#### 3. Performance Degradation (Severity 2)

**Symptoms**: Response times >5 seconds, high memory usage, timeouts

**Response Steps**:

1. **Performance Assessment**
   ```bash
   # Check current performance metrics
   ./scripts/performance-check.sh production
   
   # Monitor resource usage
   curl -s "https://qa-automation.acu.edu.au/health/metrics"
   ```

2. **Identify Bottlenecks**
   - Check database query performance
   - Monitor Canvas API response times
   - Analyze QA task execution patterns
   - Review concurrent user load

3. **Mitigation Actions**
   ```bash
   # Scale up application workers if needed
   railway variables set ASYNC_WORKERS=8 --environment production
   railway restart --environment production
   
   # Reduce Canvas API rate limits temporarily
   railway variables set CANVAS_RATE_LIMIT_PER_MINUTE=100 --environment production
   ```

#### 4. Database Issues (Severity 2)

**Symptoms**: Database connection errors, slow queries, data inconsistencies

**Response Steps**:

1. **Database Health Check**
   ```bash
   # Check database connectivity
   curl -f "https://qa-automation.acu.edu.au/health/database"
   
   # Check Railway database status
   railway status --environment production
   ```

2. **Database Diagnostics**
   - Check active connections
   - Review slow query logs
   - Monitor disk space usage
   - Check backup status

3. **Recovery Actions**
   ```bash
   # Restart application if connection pool issues
   railway restart --environment production
   
   # Scale database resources if needed (via Railway dashboard)
   # Restore from backup if data corruption detected
   ```

## Canvas-Specific Issues

### Canvas API Rate Limiting

**Symptoms**: 429 errors, Canvas API quota exceeded warnings

**Resolution**:
```bash
# Check current rate limit status
curl -s "https://qa-automation.acu.edu.au/health/canvas/rate-limits"

# Temporarily reduce rate limits
railway variables set CANVAS_RATE_LIMIT_PER_MINUTE=120 --environment production
railway restart --environment production

# Monitor Canvas API usage
./scripts/monitor-canvas-api.sh
```

### Canvas Maintenance Windows

**Preparation Steps**:
1. Subscribe to Canvas status updates
2. Schedule maintenance notifications for users
3. Prepare degraded service mode if needed
4. Document Canvas maintenance schedule

**During Canvas Maintenance**:
```bash
# Enable Canvas maintenance mode
railway variables set CANVAS_MAINTENANCE_MODE=true --environment production

# Monitor Canvas availability
while true; do
    if curl -f "https://aculeo.instructure.com" > /dev/null 2>&1; then
        echo "Canvas is back online"
        break
    fi
    sleep 60
done

# Disable maintenance mode
railway variables set CANVAS_MAINTENANCE_MODE=false --environment production
```

### LTI Configuration Issues

**Common Issues and Solutions**:

1. **Invalid JWT Signature**
   - Verify private key encoding (base64)
   - Check client ID matches Canvas configuration
   - Validate JWT algorithm (RS256)

2. **Nonce Validation Failures**
   - Clear nonce cache
   - Check system clock synchronization
   - Verify nonce TTL configuration

3. **Canvas Deep Linking Issues**
   - Validate deep linking URL configuration
   - Check Canvas placement settings
   - Verify proper message types in LTI launch

## Performance Issues

### High Memory Usage

**Symptoms**: Memory usage >80%, out of memory errors

**Investigation**:
```bash
# Check current memory usage
curl -s "https://qa-automation.acu.edu.au/health/metrics" | jq '.memory_usage_mb'

# Review memory-intensive operations
railway logs --environment production | grep "memory"
```

**Resolution**:
```bash
# Restart application to clear memory
railway restart --environment production

# Increase memory limits if needed
railway variables set MEMORY_LIMIT_MB=1024 --environment production

# Reduce concurrent task processing
railway variables set MAX_CONCURRENT_TASKS=5 --environment production
```

### Slow QA Task Execution

**Symptoms**: QA tasks taking >5 minutes, user complaints about slow processing

**Investigation**:
- Check Canvas API response times
- Review QA task complexity (content volume)
- Monitor database query performance
- Analyze WebSocket update frequency

**Resolution**:
```bash
# Optimize QA task batch processing
railway variables set BATCH_SIZE=25 --environment production

# Reduce parallel processing to avoid overwhelming Canvas API
railway variables set PARALLEL_PROCESSING_LIMIT=3 --environment production

# Increase progress update interval to reduce WebSocket overhead
railway variables set PROGRESS_UPDATE_INTERVAL=5 --environment production
```

## Database Operations

### Backup Verification

**Daily Backup Check**:
```bash
#!/bin/bash
# Verify daily database backups

echo "💾 Checking database backup status..."

# Railway automatically backs up databases
# Check backup status via Railway CLI
railway database backups --environment production

# Verify backup recency
LAST_BACKUP=$(railway database backups --environment production --json | jq -r '.[0].created_at')
echo "Last backup: $LAST_BACKUP"
```

### Database Restore Procedure

**Emergency Database Restore**:
```bash
#!/bin/bash
# Emergency database restore procedure

echo "🚨 EMERGENCY DATABASE RESTORE"
echo "This will restore the database to a previous backup point"

# List available backups
railway database backups --environment production

# Restore from specific backup (replace BACKUP_ID)
read -p "Enter backup ID to restore from: " BACKUP_ID
railway database restore $BACKUP_ID --environment production

echo "Database restore initiated. Monitor progress via Railway dashboard."
```

### Database Migration

**Schema Migration Procedure**:
```bash
#!/bin/bash
# Database schema migration

echo "🔄 Running database migration..."

# Create backup before migration
railway database backup --environment production

# Run migrations (if using Alembic or similar)
railway run --environment production "alembic upgrade head"

# Verify migration success
./scripts/health-check.sh production
```

## Security Incidents

### Suspected Security Breach

**Immediate Response**:
1. **Isolate**: Consider taking affected environment offline
2. **Assess**: Determine scope and impact
3. **Contain**: Prevent further damage
4. **Notify**: Alert security team and stakeholders

**Investigation Steps**:
```bash
# Check access logs for suspicious activity
railway logs --environment production | grep -E "(failed|unauthorized|suspicious)"

# Review recent authentication attempts
curl -s "https://qa-automation.acu.edu.au/health/security-metrics"

# Check for unusual Canvas API usage patterns
./scripts/analyze-canvas-usage.sh
```

### Credential Compromise

**Response Actions**:
```bash
# Immediately rotate compromised credentials
railway variables set SECRET_KEY="$(openssl rand -base64 32)" --environment production

# Rotate Canvas private key if compromised
railway variables set CANVAS_PROD_PRIVATE_KEY="new_base64_encoded_key" --environment production

# Restart application to use new credentials
railway restart --environment production

# Force logout of all existing sessions
curl -X POST "https://qa-automation.acu.edu.au/admin/force-logout-all"
```

### Canvas Security Issues

**Canvas Account Compromise**:
1. Immediately disable compromised Canvas developer key
2. Generate new Canvas developer key and private key
3. Update application configuration with new credentials
4. Notify Canvas administrators
5. Review Canvas audit logs for suspicious activity

## Disaster Recovery

### Complete Service Recovery

**Scenario**: Complete infrastructure failure, need to rebuild from scratch

**Recovery Steps**:

1. **Infrastructure Setup**
   ```bash
   # Create new Railway project
   railway init
   
   # Configure environments
   railway environment create production
   railway environment production
   ```

2. **Configuration Restoration**
   ```bash
   # Restore environment variables from secure backup
   ./scripts/restore-environment-config.sh production
   
   # Deploy application
   railway deploy --environment production
   ```

3. **Database Restoration**
   ```bash
   # Restore database from backup
   railway database restore LATEST_BACKUP_ID --environment production
   ```

4. **Validation**
   ```bash
   # Comprehensive health check
   ./scripts/health-check.sh production
   
   # Canvas integration validation
   ./scripts/validate-canvas-integration.sh production
   
   # User acceptance testing
   ./scripts/uat-validation.sh production
   ```

### Data Recovery Procedures

**QA Task Data Loss**:
1. Check database backups for recoverable data
2. Review Canvas audit logs for task execution history
3. Restore from most recent clean backup
4. Notify affected users of data recovery status

## Maintenance Procedures

### Scheduled Maintenance

**Monthly Maintenance Checklist**:
- [ ] Review security updates and patches
- [ ] Update dependencies and libraries
- [ ] Review and rotate secrets/credentials
- [ ] Check backup integrity
- [ ] Performance optimization review
- [ ] Canvas API usage analysis
- [ ] User feedback review

**Maintenance Window Procedure**:
```bash
# 1. Notify users of maintenance window
./scripts/notify-maintenance.sh "2024-01-15 02:00 EST" "4 hours"

# 2. Create pre-maintenance backup
railway database backup --environment production

# 3. Deploy updates during maintenance window
./scripts/deploy-production.sh

# 4. Post-maintenance validation
./scripts/comprehensive-health-check.sh production

# 5. Notify users of maintenance completion
./scripts/notify-maintenance-complete.sh
```

### Dependency Updates

**Security Update Procedure**:
```bash
# Check for security vulnerabilities
pip audit

# Update requirements with security fixes
pip install --upgrade package-name

# Test in development environment first
./scripts/deploy-test.sh

# Run comprehensive testing
pytest tests/security/

# Deploy to production during maintenance window
./scripts/deploy-production.sh
```

## Contact Information

### Escalation Matrix

**Level 1 - Operations Team**
- **Primary**: operations@acu.edu.au
- **Secondary**: sys-admin@acu.edu.au
- **Phone**: +61-x-xxxx-xxxx

**Level 2 - Development Team**
- **Primary**: dev-team@acu.edu.au
- **Lead Developer**: lead-dev@acu.edu.au
- **Phone**: +61-x-xxxx-xxxx

**Level 3 - Canvas Support**
- **Canvas Support**: support@instructure.com
- **ACU Canvas Admin**: canvas-admin@acu.edu.au
- **Emergency**: Canvas emergency support line

**Level 4 - Infrastructure**
- **Railway Support**: support@railway.app
- **Infrastructure Team**: infra@acu.edu.au

### Emergency Contacts

**After Hours Emergency**:
- **Operations Manager**: +61-xxx-xxx-xxx
- **IT Director**: +61-xxx-xxx-xxx
- **Canvas Administrator**: +61-xxx-xxx-xxx

### Communication Channels

**Status Updates**:
- **Slack**: #qa-automation-status
- **Email**: qa-automation-alerts@acu.edu.au
- **Status Page**: status.acu.edu.au/qa-automation

**Incident Management**:
- **Ticket System**: JIRA/ServiceNow
- **Emergency Line**: IT Helpdesk +61-xxx-xxx-xxx

## Monitoring and Alerting

### Critical Alerts

**Alert Thresholds**:
- Application response time > 5 seconds
- Error rate > 5% over 5 minutes
- Canvas API errors > 10 per minute
- Memory usage > 90%
- Database connection failures
- Health check failures for 3+ consecutive checks

**Alert Destinations**:
- Slack: #qa-automation-alerts
- Email: on-call-team@acu.edu.au
- SMS: Critical alerts only

### Health Check Schedule

**Continuous Monitoring**:
- Application health: Every 30 seconds
- Canvas connectivity: Every 60 seconds
- Database health: Every 60 seconds
- Performance metrics: Every 5 minutes

**Daily Reports**:
- Morning health summary (8:00 AM)
- End-of-day status report (6:00 PM)
- Weekly performance summary (Mondays)

This operational runbook provides comprehensive procedures for maintaining the Canvas QA Automation Tool, responding to incidents, and ensuring reliable service delivery across all Canvas environments. 