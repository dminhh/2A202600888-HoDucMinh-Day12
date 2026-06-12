# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found in develop/app.py

1. **Hardcode secrets** (dòng 17-18): `OPENAI_API_KEY` và `DATABASE_URL` nằm trực tiếp trong code — push lên GitHub là lộ ngay
2. **Không có config management** (dòng 21-22): `DEBUG`, `MAX_TOKENS` hardcode, không đọc từ environment variables
3. **Dùng print() thay vì proper logging** (dòng 33-38): Không có log level, format chuẩn, và còn log ra secret tại dòng 34
4. **Không có health check endpoint** (dòng 42-43): Platform không biết khi nào container crash để tự restart
5. **Port/host cố định** (dòng 51-53): `host="localhost"` (không nhận kết nối từ ngoài container), `port=8000` hardcode, `reload=True` chạy trong production

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Why Important? |
|---------|---------|------------|----------------|
| Config | Hardcode trong code | Đọc từ env vars qua `settings` | Bảo mật, linh hoạt theo môi trường, không lộ secret khi push code |
| Health check | Không có | `/health` + `/ready` | Platform cần để biết khi nào restart container hoặc route traffic |
| Logging | `print()` + log secret | JSON structured, không log secret | Dễ parse, tìm kiếm trên log aggregator (Datadog, Loki...) |
| Shutdown | Đột ngột | Graceful (SIGTERM handler + lifespan) | Hoàn thành request đang xử lý trước khi tắt, tránh mất dữ liệu |
| Host binding | `localhost` | `0.0.0.0` | Trong container phải bind `0.0.0.0` mới nhận được traffic từ bên ngoài |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. **Base image là gì?** → `python:3.11` (full distribution, ~1GB)
2. **Working directory là gì?** → `/app`
3. **Tại sao COPY requirements.txt trước?** → Tận dụng Docker layer cache: nếu code thay đổi nhưng requirements không đổi, bước `pip install` được cache lại, không cần cài lại từ đầu → build nhanh hơn
4. **CMD vs ENTRYPOINT khác nhau thế nào?** → `CMD` có thể bị override khi `docker run <image> <command>`, còn `ENTRYPOINT` thì không bị override (luôn chạy cố định)

### Exercise 2.3: Image size comparison

- **Develop (single-stage):** 1.15 GB
- **Production (multi-stage):** 160 MB
- **Nhỏ hơn:** ~7x

**Lý do:**
- Stage 1 (builder): dùng `python:3.11-slim`, cài gcc + libpq-dev + pip install vào `/root/.local`
- Stage 2 (runtime): copy chỉ `site-packages` từ stage 1, không mang theo gcc, apt cache, build tools
- Kết quả: image cuối sạch và nhỏ hơn rất nhiều

### Exercise 2.4: Docker Compose architecture diagram

```
                    Internet
                       |
                  port 80/443
                       |
              +-----------------+
              |     Nginx       |  reverse proxy + load balancer
              |  (nginx:alpine) |
              +--------+--------+
                       | round-robin
             +---------+---------+
             v                   v
        +---------+         +---------+
        | agent 1 |         | agent 2 |   (scale với --scale agent=N)
        |  :8000  |         |  :8000  |
        +----+----+         +----+----+
             |                   |
             +----------+--------+
                        |
           +------------+------------+
           v                         v
   +---------------+        +----------------+
   |     Redis     |        |     Qdrant     |
   | (cache +      |        | (vector DB     |
   |  rate limit)  |        |  for RAG)      |
   +---------------+        +----------------+
```

**Services được start:** `agent`, `redis`, `qdrant`, `nginx`

**Cách communicate:**
- Tất cả trong network `internal` (bridge) — isolate khỏi bên ngoài
- Chỉ Nginx expose port 80/443 ra internet, agent không expose trực tiếp
- Agent depends_on redis và qdrant (chờ healthy mới start)
- Volumes `redis_data` và `qdrant_data` persist khi restart

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
- URL: https://labday12-production-699f.up.railway.app
- Platform: Railway
- Deploy command: `railway up`

**Test results:**
```bash
# Health check
$ curl https://labday12-production-699f.up.railway.app/health
{"status":"ok","uptime_seconds":1025.6,"platform":"Railway","timestamp":"2026-06-12T10:06:43.961619+00:00"}

# Ask endpoint
$ curl https://labday12-production-699f.up.railway.app/ask -X POST \
    -H "Content-Type: application/json" \
    -d '{"question": "Am I on the cloud?"}'
{"question":"Am I on the cloud?","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","platform":"Railway"}
```

### Exercise 3.2: So sánh `render.yaml` vs `railway.toml`

| | `railway.toml` | `render.yaml` |
|-|----------------|---------------|
| Format | TOML | YAML |
| Builder | Nixpacks (auto-detect) | Chỉ định runtime Python |
| Secrets | Set qua CLI/Dashboard | `sync: false` hoặc `generateValue: true` |
| Auto deploy | Không khai báo | `autoDeploy: true` khi push GitHub |
| Redis | Thêm riêng trên dashboard | Khai báo luôn trong file (`type: redis`) |
| Region | Không chỉ định | Chỉ định được (`singapore`) |

---

## Part 4: API Security

### Exercise 4.1-4.3: Test results

```bash
# Test không có key → 401
$ curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"Hello"}'
{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}
HTTP: 401

# Test sai key → 403
$ curl -X POST http://localhost:8000/ask -H "X-API-Key: wrong-key" -H "Content-Type: application/json" -d '{"question":"Hello"}'
{"detail":"Invalid API key."}
HTTP: 403

# Test đúng key → 200
$ curl -X POST http://localhost:8000/ask -H "X-API-Key: secret-key-123" -H "Content-Type: application/json" -d '{"question":"Hello"}'
{"question":"Hello","answer":"Đây là câu trả lời từ AI agent (mock)..."}
HTTP: 200

# Test rate limit (production, JWT auth, limit 10 req/phút):
Request 1-10:  HTTP 200
Request 11:    HTTP 429 Too Many Requests
Request 12:    HTTP 429 Too Many Requests
```

**API key check ở đâu?** `verify_api_key()` trong `develop/app.py:39`, inject vào `/ask` qua `Depends(verify_api_key)`

**Rotate key:** Thay env var `AGENT_API_KEY` và restart service

**JWT flow:** `POST /auth/token` → nhận JWT → gửi `Authorization: Bearer <token>` → server decode, extract user info

**Rate limiting algorithm:** Sliding Window Counter — mỗi user có 1 bucket đếm timestamp trong 60 giây. User: 10 req/phút, Admin: 100 req/phút. Vượt limit → 429 kèm header `Retry-After`.

### Exercise 4.4: Cost guard implementation

**Approach:** `CostGuard` class trong `production/cost_guard.py`
- Track `input_tokens` + `output_tokens` per user per ngày
- Tính cost dựa trên giá token ($0.15/1M input, $0.60/1M output)
- Per-user budget: $1/ngày → vượt → **402 Payment Required**
- Global budget: $10/ngày → vượt → **503 Service Unavailable**
- Cảnh báo log khi dùng 80% budget
- Production cần thay in-memory bằng Redis để scale multi-instance

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health & Readiness check

```python
@app.get("/health")
def health():
    """Liveness probe — container còn sống không?"""
    uptime = round(time.time() - START_TIME, 1)
    checks = {}
    try:
        import psutil
        mem = psutil.virtual_memory()
        checks["memory"] = {
            "status": "ok" if mem.percent < 90 else "degraded",
            "used_percent": mem.percent,
        }
    except ImportError:
        checks["memory"] = {"status": "ok", "note": "psutil not installed"}

    overall_status = "ok" if all(v.get("status") == "ok" for v in checks.values()) else "degraded"
    return {
        "status": overall_status,
        "uptime_seconds": uptime,
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }


@app.get("/ready")
def ready():
    """Readiness probe — sẵn sàng nhận traffic không?"""
    if not _is_ready:
        raise HTTPException(
            status_code=503,
            detail="Agent not ready. Check back in a few seconds.",
        )
    return {
        "ready": True,
        "in_flight_requests": _in_flight_requests,
    }
```

- `/health` (Liveness probe): trả về status, uptime, memory check. Platform restart container nếu non-200.
- `/ready` (Readiness probe): trả về 503 khi `_is_ready = False` (đang startup/shutdown). Load balancer không route traffic vào.

### Exercise 5.2: Graceful shutdown

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    # Startup
    _is_ready = True

    yield

    # Shutdown — chờ in-flight requests hoàn thành
    _is_ready = False
    timeout = 30
    elapsed = 0
    while _in_flight_requests > 0 and elapsed < timeout:
        logger.info(f"Waiting for {_in_flight_requests} in-flight requests...")
        time.sleep(1)
        elapsed += 1
    logger.info("Shutdown complete")


def handle_sigterm(signum, frame):
    """Bắt SIGTERM từ platform, để uvicorn xử lý graceful shutdown."""
    logger.info(f"Received signal {signum} — uvicorn will handle graceful shutdown")

signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)
```

### Exercise 5.3: Stateless design

| Anti-pattern | Production |
|---|---|
| `conversation_history = {}` (in-memory) | `redis.setex(f"session:{id}", ...)` |
| Instance die → mất data | Redis persist → bất kỳ instance nào đọc được |

### Exercise 5.4-5.5: Load balancing test

```bash
$ docker compose up --scale agent=3 -d
# 3 containers: production-agent-1, production-agent-2, production-agent-3
# Nginx load balancer: port 8080

$ curl http://localhost:8080/health
{"status":"ok","instance_id":"instance-c15909","storage":"redis","redis_connected":true}

# Gọi 6 requests → Nginx phân tán round-robin:
Request 1: served_by=instance-5d8762
Request 2: served_by=instance-90e243
Request 3: served_by=instance-c15909
Request 4: served_by=instance-5d8762
Request 5: served_by=instance-90e243
Request 6: served_by=instance-c15909
```

Kết quả: mỗi request được serve bởi instance khác nhau theo vòng. State lưu trong Redis nên conversation vẫn còn dù instance thay đổi.

---

## Part 6: Final Project

### Public URL
https://lab12-part6-production-719a.up.railway.app

### Project structure
```
my-production-agent/
├── app/
│   ├── main.py          # FastAPI app + health/ready/ask endpoints
│   ├── config.py        # 12-factor config từ env vars
│   ├── auth.py          # API Key authentication
│   ├── rate_limiter.py  # Sliding window rate limiter
│   └── cost_guard.py    # Monthly budget guard
├── utils/
│   └── mock_llm.py
├── Dockerfile           # Multi-stage build
├── docker-compose.yml   # agent + redis + nginx
├── nginx.conf           # Load balancer config
├── railway.toml         # Railway deployment config
├── requirements.txt
├── .env.example
├── .dockerignore
└── README.md
```

### Test results

```bash
# Health check → 200
$ curl https://lab12-part6-production-719a.up.railway.app/health
{"status":"ok","version":"1.0.0","environment":"production","uptime_seconds":132.3,...}

# Không có key → 401
$ curl -X POST https://lab12-part6-production-719a.up.railway.app/ask \
    -H "Content-Type: application/json" -d '{"question":"Hello"}'
HTTP 401 - {"detail":"Missing API key. Include header: X-API-Key: <your-key>"}

# Đúng key → 200
$ curl -X POST https://lab12-part6-production-719a.up.railway.app/ask \
    -H "X-API-Key: my-secret-key-2026" \
    -H "Content-Type: application/json" \
    -d '{"question":"What is deployment?"}'
{"question":"What is deployment?","answer":"Deployment là quá trình đưa code từ máy bạn lên server để người khác dùng được.","model":"gpt-4o-mini","timestamp":"2026-06-12T16:35:54.024004+00:00"}
```

### Production checklist
- [x] All code runs without errors
- [x] Multi-stage Dockerfile (image ~160MB < 500MB)
- [x] API key authentication (401 without key)
- [x] Rate limiting (10 req/min per key)
- [x] Cost guard ($10/month per user)
- [x] Health check endpoint `/health`
- [x] Readiness check endpoint `/ready`
- [x] Graceful shutdown (SIGTERM handler + lifespan)
- [x] Stateless design (Redis-backed session)
- [x] Structured JSON logging
- [x] Deploy lên Railway — public URL hoạt động
