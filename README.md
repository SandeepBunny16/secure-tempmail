# 🔐 SecureTempMail

<div align="center">

**Production-Ready Temporary Email System**

*Self-hosted • Privacy-focused • Zero External Dependencies*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/postgres-%23316192.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?logo=redis&logoColor=white)](https://redis.io/)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [API Documentation](#-api-documentation)
- [Security](#-security)
- [Deployment](#-deployment)
- [Development](#-development)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**SecureTempMail** is a production-grade, self-hosted temporary email system designed for maximum privacy and security. Run entirely on your infrastructure with zero external dependencies.

### Why SecureTempMail?

- **🔒 Privacy-First**: End-to-end encryption, no telemetry, no external services
- **🚀 Production-Ready**: Enterprise-grade code with comprehensive testing
- **🛡️ Secure by Default**: Rate limiting, sanitization, authentication
- **📦 Easy Deployment**: Docker Compose setup, one command to run
- **🎨 Modern UI**: Clean, responsive web interface
- **📊 Observable**: Prometheus metrics, structured logging
- **⚡ High Performance**: Async architecture, Redis caching
- **🔧 Configurable**: Extensive configuration options

---

## ✨ Features

### Core Features

- **📧 SMTP Server**: Built-in aiosmtpd server receives emails directly
- **🔐 End-to-End Encryption**: AES-256 encryption for all message bodies
- **⏰ Auto-Expiry**: Configurable TTL with automatic cleanup
- **🎯 REST API**: Complete RESTful API with OpenAPI documentation
- **🌐 Web UI**: Modern, responsive interface with Tailwind CSS
- **📨 Email Parsing**: RFC-5322 compliant email parsing
- **🧹 HTML Sanitization**: XSS prevention with Bleach library
- **📎 Attachments**: Support for email attachments with size limits

### Security Features

- **🔑 Token Authentication**: Bearer token auth for API access
- **🚦 Rate Limiting**: Per-IP rate limiting (configurable)
- **🛡️ Input Validation**: Comprehensive input validation with Pydantic
- **🧼 HTML Sanitization**: Prevents XSS attacks
- **🔒 SQL Injection Protection**: Parameterized queries
- **🔐 Encrypted Storage**: Messages encrypted at rest
- **🚫 No Telemetry**: Zero data collection or external calls
- **🐳 Container Security**: Non-root user, no-new-privileges

### Operational Features

- **📊 Metrics**: Prometheus metrics endpoint
- **📝 Structured Logging**: JSON logging for easy parsing
- **🏥 Health Checks**: Comprehensive health check endpoints
- **🔄 Auto-Cleanup**: Background worker for TTL enforcement
- **📈 Monitoring**: Grafana dashboard included
- **🚨 Alerting**: Prometheus alert rules
- **🔧 Configuration**: Environment-based config

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Internet / Your Domain                   │
│                   (MX record points here)                    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Port 25/8025 (SMTP)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    SMTP Server (aiosmtpd)                    │
│  • Validates recipient addresses                            │
│  • Parses RFC-5322 messages                                 │
│  • Encrypts and stores                                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                   Storage Layer                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │   PostgreSQL     │  │      Redis       │                │
│  │  • Inbox data    │  │  • TTL tracking  │                │
│  │  • Messages      │  │  • Rate limiting │                │
│  │  • Encrypted     │  │  • Cache         │                │
│  └──────────────────┘  └──────────────────┘                │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│               FastAPI REST API (Port 8000)                   │
│  • POST /api/v1/inboxes - Create inbox                     │
│  • GET /api/v1/inboxes/{id}/messages - List messages       │
│  • GET /api/v1/messages/{id} - Get message                 │
│  • DELETE /api/v1/inboxes/{id} - Delete inbox              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                   Web UI (Tailwind CSS)                      │
│  • Inbox management                                         │
│  • Message viewing (sanitized HTML)                         │
│  • Copy-to-clipboard                                        │
│  • Mobile-responsive                                        │
└─────────────────────────────────────────────────────────────┘

Background Workers:
┌─────────────────────────────────────────────────────────────┐
│  TTL Cleanup Worker (runs every 5 minutes)                  │
│  • Checks Redis for expired inboxes                         │
│  • Securely deletes messages and inbox data                 │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, aiosmtpd
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Frontend**: HTML, Tailwind CSS, Vanilla JavaScript
- **Deployment**: Docker, Docker Compose
- **Monitoring**: Prometheus, Grafana

---

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Domain with MX record (for production)
- Ports available: 8000 (API), 8025/25 (SMTP), 5432 (PostgreSQL), 6379 (Redis)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/SandeepBunny16/secure-tempmail.git
cd secure-tempmail

# 2. Generate secure keys
bash scripts/generate-keys.sh

# 3. Create .env file
cp .env.example .env

# 4. Edit .env and add the generated keys
nano .env
# Update these critical values:
# - SECRET_KEY (from step 2)
# - ENCRYPTION_KEY (from step 2)
# - API_KEY (from step 2)
# - POSTGRES_PASSWORD (strong password)
# - REDIS_PASSWORD (strong password)
# - APP_DOMAIN (your domain)

# 5. Start all services
docker-compose up -d

# 6. Check service status
docker-compose ps

# 7. View logs
docker-compose logs -f api

# 8. Health check
curl http://localhost:8000/health
```

### First Steps

```bash
# Create your first inbox
curl -X POST http://localhost:8000/api/v1/inboxes \
  -H "Content-Type: application/json" \
  -d '{}'

# Response:
# {
#   "inbox_id": "abc123...",
#   "address": "tmp_xyz789@yourdomain.com",
#   "token": "bearer_token_here",
#   "expires_at": "2025-11-24T17:30:00Z"
# }

# Send a test email
bash scripts/test-email.sh localhost 8025 tmp_xyz789@yourdomain.com

# Check for emails
curl http://localhost:8000/api/v1/inboxes/abc123/messages \
  -H "Authorization: Bearer bearer_token_here"

# Access Web UI
# Open http://localhost:8000 in your browser
```

---

## ⚙️ Configuration

All configuration is done via environment variables in the `.env` file.

### Critical Security Settings

```bash
# MUST CHANGE THESE!
SECRET_KEY=<32-byte-hex>        # Generate with: openssl rand -hex 32
ENCRYPTION_KEY=<32-byte-hex>    # Generate with: openssl rand -hex 32
API_KEY=<32-byte-hex>           # Generate with: openssl rand -hex 32
POSTGRES_PASSWORD=<strong-pwd>  # Strong password
REDIS_PASSWORD=<strong-pwd>     # Strong password
```

### Email Settings

```bash
APP_DOMAIN=tempmail.yourdomain.com  # Your domain
DEFAULT_TTL_HOURS=24                # Inbox lifetime
MAX_EMAILS_PER_INBOX=50             # Max emails per inbox
MAX_EMAIL_SIZE_MB=10                # Max email size
ADDRESS_LENGTH=24                   # Generated address length
```

### Rate Limiting

```bash
RATE_LIMIT_PER_MINUTE=60            # Requests/min per IP
RATE_LIMIT_PER_HOUR=1000            # Requests/hour per IP
INBOX_CREATION_LIMIT_PER_HOUR=10    # Inbox creations/hour per IP
```

### See [.env.example](.env.example) for all options.

---

## 📚 API Documentation

### Base URL

```
Production: https://yourdomain.com/api/v1
Local: http://localhost:8000/api/v1
```

### Authentication

- **Public endpoints**: No authentication
- **Inbox-specific endpoints**: Bearer token (returned on inbox creation)
- **Admin endpoints**: API key in `X-API-Key` header

### Endpoints

#### Create Inbox

```bash
POST /api/v1/inboxes
Content-Type: application/json

{}

# Response:
{
  "inbox_id": "string",
  "address": "string",
  "token": "string",
  "expires_at": "datetime"
}
```

#### List Messages

```bash
GET /api/v1/inboxes/{inbox_id}/messages
Authorization: Bearer {token}

# Response:
{
  "messages": [
    {
      "id": "string",
      "from": "string",
      "subject": "string",
      "preview": "string",
      "received_at": "datetime",
      "has_attachments": boolean
    }
  ],
  "count": integer
}
```

#### Get Message

```bash
GET /api/v1/messages/{message_id}
Authorization: Bearer {token}

# Response:
{
  "id": "string",
  "from": "string",
  "to": "string",
  "subject": "string",
  "body_html": "string",
  "body_text": "string",
  "received_at": "datetime",
  "attachments": []
}
```

#### Delete Inbox

```bash
DELETE /api/v1/inboxes/{inbox_id}
Authorization: Bearer {token}

# Response:
{
  "message": "Inbox deleted successfully"
}
```

### Interactive Documentation

Open http://localhost:8000/docs for full Swagger UI documentation.

---

## 🔒 Security

### Security Features

✅ **Encryption**: AES-256 encryption for message bodies  
✅ **Authentication**: Token-based auth for all protected endpoints  
✅ **Rate Limiting**: Protection against abuse  
✅ **Input Validation**: Comprehensive validation with Pydantic  
✅ **HTML Sanitization**: XSS prevention with Bleach  
✅ **SQL Injection Protection**: Parameterized queries  
✅ **CORS Protection**: Configurable CORS policy  
✅ **Security Headers**: Helmet-style security headers  
✅ **No Telemetry**: Zero external data collection  
✅ **Container Security**: Non-root user, minimal privileges  

### Best Practices

1. **Change default keys**: Always generate new keys (see Quick Start)
2. **Use HTTPS**: Enable SSL/TLS in production (see Deployment)
3. **Update regularly**: Keep dependencies updated
4. **Monitor logs**: Watch for suspicious activity
5. **Backup regularly**: Backup database and encryption keys
6. **Limit access**: Use firewall rules to restrict access
7. **Enable metrics**: Monitor with Prometheus/Grafana

### Security Checklist

- [ ] Generated new SECRET_KEY, ENCRYPTION_KEY, API_KEY
- [ ] Set strong POSTGRES_PASSWORD and REDIS_PASSWORD
- [ ] Configured CORS_ORIGINS for your domain
- [ ] Enabled HTTPS with valid SSL certificate
- [ ] Configured rate limiting
- [ ] Reviewed and adjusted TTL settings
- [ ] Configured backup strategy
- [ ] Set up monitoring and alerting
- [ ] Reviewed logs regularly
- [ ] Tested disaster recovery

---

## 🚢 Deployment

### Docker Compose (Recommended)

See [Quick Start](#-quick-start) for basic deployment.

### Production Deployment

```bash
# Use production compose file
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### DNS Configuration

```dns
# A Record (for web access)
yourdomain.com.    300    IN    A    YOUR_VPS_IP

# MX Record (for email reception)
yourdomain.com.    300    IN    MX   10 yourdomain.com.
```

### SSL/TLS Setup

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed SSL setup instructions.

### Kubernetes

Kubernetes manifests are available in the `k8s/` directory.

```bash
# Apply all manifests
kubectl apply -f k8s/
```

---

## 🛠️ Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Set environment variables
export $(cat .env | xargs)

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000

# In another terminal, start SMTP server
python -m app.smtp.server

# In another terminal, start worker
python -m app.workers.ttl_cleanup
```

### Project Structure

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed project structure.

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api/test_inboxes.py

# Run integration tests
pytest tests/integration/
```

### Test Coverage

Target: 90%+ code coverage

---

## 🔧 Troubleshooting

### Common Issues

#### SMTP Not Receiving Emails

```bash
# Check MX record
dig MX yourdomain.com

# Check SMTP port
telnet yourdomain.com 25

# Check SMTP logs
docker-compose logs smtp
```

#### Database Connection Issues

```bash
# Check PostgreSQL status
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Connect to database
docker-compose exec postgres psql -U tempmail -d tempmail
```

#### Redis Connection Issues

```bash
# Check Redis status
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli -a <REDIS_PASSWORD> ping
```

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for more solutions.

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write/update tests
5. Run tests and linting
6. Submit a pull request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [aiosmtpd](https://github.com/aio-libs/aiosmtpd) - Async SMTP server
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit
- [Bleach](https://github.com/mozilla/bleach) - HTML sanitization

---

<div align="center">

**⭐ Star this repo if you find it useful! ⭐**

[Report Bug](https://github.com/SandeepBunny16/secure-tempmail/issues) • [Request Feature](https://github.com/SandeepBunny16/secure-tempmail/issues)

</div>