# ACU Canvas Instance Configuration Guide

## ACU Canvas Environment URLs

The QA Automation LTI Tool is configured to work with ACU's three Canvas environments:

### 🧪 **Test Environment**
- **URL**: `https://www.aculeo.test.instructure.com`
- **Purpose**: Development and functional testing
- **Environment Variable**: `CANVAS_ACTIVE_INSTANCE=test`
- **Safe for**: Breaking changes, experimental features, test data

### 🔄 **Beta Environment**  
- **URL**: `https://www.aculeo.beta.instructure.com`
- **Purpose**: Pre-production validation and user acceptance testing
- **Environment Variable**: `CANVAS_ACTIVE_INSTANCE=beta`
- **Safe for**: Performance testing, final validation before production

### 🚀 **Production Environment**
- **URL**: `https://www.aculeo.instructure.com`
- **Purpose**: Live Canvas instance with real user data
- **Environment Variable**: `CANVAS_ACTIVE_INSTANCE=prod`
- **Used for**: Production deployment, real QA automation workflows

## Quick Configuration

### Environment Variables Required

For each Canvas instance you want to use, set these environment variables:

```bash
# Test Instance
CANVAS_TEST_BASE_URL=https://www.aculeo.test.instructure.com
CANVAS_TEST_CLIENT_ID=your_test_client_id_from_canvas
CANVAS_TEST_PRIVATE_KEY=your_base64_encoded_test_private_key

# Beta Instance
CANVAS_BETA_BASE_URL=https://www.aculeo.beta.instructure.com
CANVAS_BETA_CLIENT_ID=your_beta_client_id_from_canvas
CANVAS_BETA_PRIVATE_KEY=your_base64_encoded_beta_private_key

# Production Instance
CANVAS_PROD_BASE_URL=https://www.aculeo.instructure.com
CANVAS_PROD_CLIENT_ID=your_prod_client_id_from_canvas
CANVAS_PROD_PRIVATE_KEY=your_base64_encoded_prod_private_key

# Set active instance
CANVAS_ACTIVE_INSTANCE=test  # or beta, or prod
```

### Canvas Developer Key Registration

For each Canvas instance, you'll need to register the LTI tool as a Developer Key:

1. **Login to Canvas** as an administrator
2. **Navigate to** Admin → Developer Keys → LTI Key
3. **Create new LTI Key** with these settings:
   - **Key Name**: ACU QA Automation Tool ({Environment})
   - **Owner Email**: your-email@acu.edu.au
   - **Target Link URI**: `https://your-deployment-url/lti/launch`
   - **OpenID Connect Initiation URL**: `https://your-deployment-url/lti/login`
   - **JWK Method**: Public JWK URL
   - **Public JWK URL**: `https://your-deployment-url/.well-known/jwks.json`

### Testing Instance Switching

```bash
# Check current configuration
curl "http://localhost:8000/health/canvas/instances"

# Test specific instance health
curl "http://localhost:8000/health/canvas?instance=test"
curl "http://localhost:8000/health/canvas?instance=beta"
curl "http://localhost:8000/health/canvas?instance=prod"

# Switch active instance (requires authentication)
curl -X POST "http://localhost:8000/health/canvas/switch-instance?instance_name=beta"
```

## Deployment Recommendations

### Test → Beta → Prod Progression

1. **Start with Test**: Develop and validate functionality
   ```bash
   export CANVAS_ACTIVE_INSTANCE=test
   uvicorn app.main:app --reload
   ```

2. **Move to Beta**: Pre-production validation
   ```bash
   export CANVAS_ACTIVE_INSTANCE=beta
   uvicorn app.main:app --reload
   ```

3. **Deploy to Production**: Live environment
   ```bash
   export CANVAS_ACTIVE_INSTANCE=prod
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

### Railway.com Deployment

The project is configured for Railway deployment with automatic environment mapping:

- **Development/Test branches** → Test Canvas instance
- **Staging/Beta branches** → Beta Canvas instance
- **Production branch** → Production Canvas instance

## Security Notes

- **Never commit** Canvas credentials or private keys to version control
- **Use separate credentials** for each Canvas environment
- **Rotate keys regularly** according to ACU security policy
- **Monitor access logs** for each Canvas instance

## Support

For Canvas instance access or LTI registration assistance, contact:
- **ACU IT Support** for Canvas administrator access
- **Learning Technology Team** for LTI tool registration guidance

This configuration ensures safe, systematic testing and deployment across all ACU Canvas environments while maintaining data security and system reliability. 