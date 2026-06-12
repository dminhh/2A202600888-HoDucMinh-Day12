# My Production Agent

Production-ready AI agent built for Day 12 lab — AICB-P1 VinUniversity 2026.

## Features

- API Key authentication
- Rate limiting (10 req/min)
- Cost guard ($10/month)
- Health + Readiness checks
- Graceful shutdown
- Stateless design (Redis)
- Multi-stage Docker build
- JSON structured logging

## Setup

```bash
cp .env.example .env.local
# Edit .env.local with your values
```

## Run locally

```bash
docker compose up --scale agent=3
```

Test:
```bash
# Health
curl http://localhost/health

# Ask (with API key)
curl -X POST http://localhost/ask \
  -H "X-API-Key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is deployment?"}'
```

## Deploy to Railway

```bash
railway login
railway init
railway up
railway domain
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_API_KEY` | `dev-key-change-me` | API key for authentication |
| `PORT` | `8000` | Server port |
| `ENVIRONMENT` | `development` | Environment name |
| `RATE_LIMIT_PER_MINUTE` | `10` | Max requests per minute |
| `MONTHLY_BUDGET_USD` | `10.0` | Monthly budget per user |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/` | GET | No | App info |
| `/health` | GET | No | Liveness probe |
| `/ready` | GET | No | Readiness probe |
| `/ask` | POST | Yes | Ask the agent |
