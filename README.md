# VeriTrust

**Open Source Identity Verification & Fraud Intelligence Platform**

> Production-grade FastAPI backend with configurable fraud rules, risk scoring, JWT authentication, and full observability — all running locally with `docker compose up`.

[![CI](https://github.com/yourusername/veritrust/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/veritrust/actions)
[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🚀 Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/veritrust.git
cd veritrust

# 2. Copy environment config
cp .env.example .env

# 3. Launch everything
docker compose up --build

# 4. Verify services are up
curl http://localhost:8000/api/v1/health
```

**That's it.** All 9 services start automatically.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  FastAPI Application                │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Routers │→ │ Services │→ │  Repositories    │  │
│  │  (API)   │  │(Business)│  │  (Data Access)   │  │
│  └──────────┘  └──────────┘  └────────┬─────────┘  │
│                                        │             │
│  ┌─────────────────┐   ┌──────────────────────────┐ │
│  │  SQLAlchemy 2   │   │    Redis (Cache/Sessions)│ │
│  │  (AsyncSession) │   └──────────────────────────┘ │
│  └────────┬────────┘                                 │
└───────────┼─────────────────────────────────────────┘
            ↓
    PostgreSQL 16          LocalStack (S3/SQS)
```

### Verification Pipeline

```
Request Input
    ↓
Email Validation     ─ Disposable domain check
    ↓
Phone Validation     ─ E.164 format (phonenumbers)
    ↓
PAN Validation       ─ Regex: [A-Z]{5}[0-9]{4}[A-Z]
    ↓
Device Check         ─ Redis blacklist lookup
    ↓
IP Velocity Check    ─ Redis sliding window counter
    ↓
Fraud Rules          ─ DB-configurable rule engine
    ↓
Risk Score (0-100)   ─ Clamped aggregate
    ↓
Decision             ─ 0-30: APPROVED | 31-60: REVIEW | 61-100: REJECT
    ↓
Audit Log            ─ Async via Celery
```

---

## 🐳 Services

| Service | URL | Credentials |
|---|---|---|
| **API** | http://localhost:8000 | JWT / API Key |
| **Swagger UI** | http://localhost:8000/docs | — |
| **ReDoc** | http://localhost:8000/redoc | — |
| **Mailpit UI** | http://localhost:8025 | — |
| **Grafana** | http://localhost:3000 | admin / veritrust |
| **Prometheus** | http://localhost:9090 | — |
| **LocalStack** | http://localhost:4566 | test / test |
| **PostgreSQL** | localhost:5432 | veritrust / veritrust |
| **Redis** | localhost:6379 | — |

---

## 📡 API Reference

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register user + organization |
| `POST` | `/api/v1/auth/login` | Get token pair |
| `POST` | `/api/v1/auth/refresh` | Rotate refresh token |
| `POST` | `/api/v1/auth/logout` | Revoke refresh token |
| `GET` | `/api/v1/auth/me` | Current user profile |

### Verification

> Uses `X-Api-Key: vt_live_...` header

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/verify` | Submit verification request |
| `GET` | `/api/v1/verify/{id}` | Get result details |
| `GET` | `/api/v1/verify/history` | List history (paginated) |

**Request:**
```json
{
  "name": "John Doe",
  "email": "john@gmail.com",
  "phone": "+919999999999",
  "pan": "ABCDE1234F",
  "ip_address": "103.44.12.34",
  "device_id": "device_123"
}
```

**Response:**
```json
{
  "verification_id": "550e8400-e29b-41d4-a716-446655440000",
  "risk_score": 42,
  "decision": "REVIEW",
  "reasons": ["Disposable email", "Phone seen previously"],
  "processing_ms": 45
}
```

### Fraud Engine

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/fraud/rules` | List all rules |
| `POST` | `/api/v1/fraud/rules` | Create custom rule |
| `PUT` | `/api/v1/fraud/rules/{id}` | Update rule |
| `DELETE` | `/api/v1/fraud/rules/{id}` | Delete rule |
| `POST` | `/api/v1/fraud/simulate` | Dry-run (no DB write) |

### Default Fraud Rules

| Rule | Type | Score Impact |
|---|---|---|
| Disposable Email | email | +25 |
| Invalid PAN Format | document | +20 |
| Phone Reused | phone | +15 |
| Blacklisted Device | device | +30 |
| High Velocity | velocity | +25 |
| Country Mismatch | geo | +15 |

### Organizations & API Keys

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/organizations` | Create org |
| `GET` | `/api/v1/organizations/{id}` | Get org |
| `PUT` | `/api/v1/organizations/{id}` | Update org |
| `POST` | `/api/v1/apikeys` | Create API key |
| `GET` | `/api/v1/apikeys` | List API keys |
| `DELETE` | `/api/v1/apikeys/{id}` | Revoke API key |

### Dashboard

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/dashboard` | Stats overview |
| `GET` | `/api/v1/dashboard/analytics?period=30d` | Time-series data |
| `GET` | `/api/v1/audit` | Audit logs (paginated) |
| `GET` | `/api/v1/health` | Liveness + readiness |

---

## 🔐 Authentication Flow

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"full_name":"John Doe","email":"john@acme.com","password":"SecurePass123!","organization_name":"Acme Corp"}'

# 2. Create API Key
curl -X POST http://localhost:8000/api/v1/apikeys \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Production Key"}'

# 3. Submit Verification
curl -X POST http://localhost:8000/api/v1/verify \
  -H "X-Api-Key: vt_live_..." \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","email":"john@gmail.com","pan":"ABCDE1234F","phone":"+919999999999"}'
```

---

## 🛠️ Development

### Prerequisites
- Docker Desktop 4.x+
- make (optional, for shortcuts)

### Makefile Commands

```bash
make dev          # Start all services with hot reload
make test         # Run test suite in Docker
make test-cov     # Run tests with coverage report (≥80% required)
make migrate      # Run pending DB migrations
make lint         # Ruff lint check
make format       # Auto-format code
make typecheck    # MyPy type checking
make logs         # Follow API logs
make db-shell     # Open psql shell
make aws-health   # Check LocalStack status
make secret       # Generate a new SECRET_KEY
```

### Running Tests Locally

```bash
# Install dependencies
pip install uv
uv pip install -e ".[dev]" aiosqlite

# Run tests (uses SQLite in-memory)
pytest tests/ --cov=app --cov-fail-under=80 -v
```

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | JWT signing key (min 32 chars) |
| `DATABASE_URL` | postgresql+asyncpg://... | PostgreSQL connection string |
| `REDIS_URL` | redis://localhost:6379/0 | Redis connection |
| `AWS_ENDPOINT_URL` | http://localhost:4566 | LocalStack endpoint (null for real AWS) |
| `S3_BUCKET_NAME` | veritrust-docs | S3 bucket for documents |
| `MAILPIT_HOST` | localhost | SMTP host |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 15 | JWT access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 30 | Refresh token TTL |
| `RATE_LIMIT_PER_MINUTE` | 100 | API key rate limit |
| `ENVIRONMENT` | development | development \| staging \| production |

---

## 📦 Project Structure

```
VeriTrust/
├── app/
│   ├── api/v1/          # FastAPI routers (auth, verify, fraud, …)
│   ├── core/            # Config, security, logging, exceptions, DI
│   ├── db/              # SQLAlchemy engine + session factory
│   ├── models/          # ORM models (9 tables)
│   ├── schemas/         # Pydantic v2 schemas
│   ├── repositories/    # Data access layer (8 repos)
│   ├── services/        # Business logic (auth, verification, fraud, …)
│   ├── middleware/       # Audit + rate limiting
│   ├── workers/         # Celery tasks
│   ├── utils/           # Validators, crypto, AWS client
│   └── main.py          # App factory
├── alembic/             # DB migrations
├── tests/               # Pytest unit + integration tests
├── docker/              # Dockerfile, Prometheus, Loki, Grafana configs
├── scripts/             # LocalStack init script
├── docs/                # Postman collection
├── docker-compose.yml
├── pyproject.toml
└── Makefile
```

---

## 🧪 Postman Collection

Import `docs/postman_collection.json` into Postman.

The collection includes environment variables and auto-extract scripts for tokens. Set `base_url` to `http://localhost:8000`.

---

## 📊 Monitoring

- **Prometheus** scrapes `/metrics` every 15s
- **Grafana** at `localhost:3000` (admin/veritrust)
- **Loki** collects structured JSON logs from the API
- **Mailpit** at `localhost:8025` catches all outbound email

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI 0.115, Python 3.13 |
| Validation | Pydantic v2 |
| Database | PostgreSQL 16 + SQLAlchemy 2 (async) |
| Migrations | Alembic |
| Cache | Redis 7 |
| Queue | Celery + Redis |
| Storage | LocalStack (S3/SQS) → AWS in production |
| Auth | JWT (HS256), bcrypt |
| Monitoring | Prometheus + Grafana |
| Logging | structlog + Loki |
| Email | Mailpit (SMTP mock) |
| Testing | Pytest + pytest-asyncio |
| CI | GitHub Actions |

---

## 📄 License

MIT — see [LICENSE](LICENSE)