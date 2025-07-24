# QA Automation LTI Tool

Canvas LTI 1.3 QA Automation Tool for Learning Designers at Australian Catholic University.

## Overview

This FastAPI application provides a Canvas-integrated LTI tool that automates QA processes for course content. It features a modular QA framework designed for extension by Learning Technologists using AI coding assistants.

## Features

- **Canvas LTI 1.3 Integration**: Seamless authentication and Canvas iframe compatibility
- **Modular QA Framework**: Extensible architecture for adding new QA automation tasks  
- **ACU Branding**: Professional interface with ACU color palette and design patterns
- **Railway Deployment**: Automated deployment with GitHub integration
- **Real-time Progress**: WebSocket/SSE progress updates for long-running QA operations

## Tech Stack

- **Backend**: FastAPI 0.104+ with Python 3.11+
- **Database**: PostgreSQL with Redis caching
- **Authentication**: Canvas LTI 1.3 OAuth with PyLTI1p3
- **Deployment**: Railway platform with GitHub auto-deploy
- **Testing**: pytest with Canvas API mocking
- **Code Quality**: black, ruff, mypy for AI-assisted development

## Development Setup

### Prerequisites

- Python 3.11+
- Git
- Railway CLI (for deployment)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Canvas_FASTAPI_LTI
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Run development server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access the application**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health
   - Root: http://localhost:8000/

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_health.py -v
```

### Code Quality

```bash
# Format code
black app/ tests/

# Lint code
ruff check app/ tests/

# Type checking
mypy app/
```

## Railway Deployment

### Initial Setup

1. **Install Railway CLI**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login to Railway**
   ```bash
   railway login
   ```

3. **Create Railway project**
   ```bash
   railway init
   ```

4. **Connect to GitHub**
   ```bash
   railway connect
   ```

### Environment Variables

Set the following environment variables in Railway:

```bash
# Required for all environments
ENVIRONMENT=production  # or staging, development

# LTI Configuration (to be added in Story 1.2)
# CANVAS_CLIENT_ID=your_canvas_client_id
# CANVAS_CLIENT_SECRET=your_canvas_client_secret
# LTI_PRIVATE_KEY=your_base64_encoded_private_key

# Database (Railway managed)
# DATABASE_URL=automatically_provided_by_railway
# REDIS_URL=automatically_provided_by_railway
```

### Deployment Process

Railway automatically deploys from the main branch when:
1. Code is pushed to GitHub main branch
2. Railway detects changes and triggers build
3. Application deploys using railway.toml configuration
4. Health check at `/health` validates deployment

### Adding Services

```bash
# Add PostgreSQL
railway add postgresql

# Add Redis
railway add redis
```

## Canvas LTI Configuration

### Developer Key Setup (Canvas Admin)

1. Navigate to Canvas Admin → Developer Keys
2. Create new LTI key with:
   - **Public JWK URL**: `https://your-app.railway.app/.well-known/jwks.json`
   - **Target Link URI**: `https://your-app.railway.app/lti/launch`
   - **OpenID Connect Initiation URL**: `https://your-app.railway.app/lti/login`

### External Tool Configuration

Add tool to Canvas course with:
- **Consumer Key**: Use Canvas Developer Key ID
- **Shared Secret**: Not needed for LTI 1.3
- **Launch URL**: `https://your-app.railway.app/lti/launch`

## Project Structure

```
Canvas_FASTAPI_LTI/
├── app/                          # FastAPI application
│   ├── main.py                   # Application entry point
│   ├── core/                     # Core functionality
│   │   ├── config.py             # Environment configuration
│   │   ├── dependencies.py       # FastAPI dependencies
│   │   ├── security.py           # LTI authentication
│   │   └── exceptions.py         # Exception handlers
│   ├── api/                      # API routes and middleware
│   ├── services/                 # Business logic services
│   ├── qa_framework/             # Modular QA framework
│   ├── models/                   # Database models
│   ├── integrations/             # External service integrations
│   └── utils/                    # Utility functions
├── tests/                        # Test suite
├── docs/                         # Documentation
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies
├── railway.toml                  # Railway deployment config
└── README.md                     # This file
```

## Contributing

1. Follow the existing code style (black, ruff, mypy)
2. Write tests for new functionality
3. Update documentation as needed
4. Ensure all tests pass before committing

## License

Copyright Australian Catholic University. All rights reserved. 