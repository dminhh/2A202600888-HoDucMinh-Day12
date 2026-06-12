# Deployment Information

## Public URL
https://labday12-production-699f.up.railway.app

## Platform
Railway

## Test Commands

### Health Check
```bash
curl https://labday12-production-699f.up.railway.app/health
# Expected: {"status":"ok","uptime_seconds":...,"platform":"Railway","timestamp":"..."}
```

### API Test
```bash
curl -X POST https://labday12-production-699f.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Am I on the cloud?"}'
# Expected: {"question":"Am I on the cloud?","answer":"...","platform":"Railway"}
```

## Environment Variables Set
- PORT (auto-injected by Railway)
- AGENT_API_KEY

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
