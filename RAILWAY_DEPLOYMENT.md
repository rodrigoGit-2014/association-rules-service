# Railway Deployment Guide - Association Rules Service

## Problem Fixed: CORS and Port Configuration

Your service was facing a CORS error because the production frontend URL was not in the allowed origins list.

### Changes Applied:

1. **Added PORT configuration** in `app/core/config.py` - Railway can now set the port dynamically
2. **Updated Dockerfile CMD** to use `PORT` environment variable
3. **Updated main.py** to use `settings.PORT` instead of hardcoded port
4. **Added production frontend to CORS origins** in `.env.example`

---

## Railway Environment Variables Setup

### Required Environment Variables

Set these in your Railway service dashboard:

```bash
# Database (PostgreSQL service URL)
DATABASE_URL=postgresql://user:password@host:port/database

# Redis (Redis service URL)
REDIS_URL=redis://default:password@redis.railway.internal:6379/2
CELERY_BROKER_URL=redis://default:password@redis.railway.internal:6379/2
CELERY_RESULT_BACKEND=redis://default:password@redis.railway.internal:6379/2

# CORS - IMPORTANT: Add your production frontend URL
CORS_ORIGINS=["https://canasta-analytics-web-production.up.railway.app","http://localhost:3000","http://localhost:8080"]

# Application
APP_NAME=Apriori Market Basket Analysis API v2
APP_VERSION=2.0.0
LOG_LEVEL=INFO
DEBUG=false

# Port (Railway will set this automatically, but you can override)
PORT=8002

# Performance
CACHE_TTL_SECONDS=900
SYNC_THRESHOLD=50000
MATVIEW_REFRESH_MINUTES=30
BATCH_SIZE=10000
```

### IMPORTANT: CORS_ORIGINS Format

Railway requires the JSON array format for the list:
```bash
CORS_ORIGINS=["https://canasta-analytics-web-production.up.railway.app","http://localhost:3000"]
```

**Alternative (Allow all origins - less secure but simpler for testing):**
```bash
CORS_ORIGINS=["*"]
```

---

## Deployment Steps

### 1. Commit and Push Changes

```bash
git add .
git commit -m "Fix CORS and port configuration for Railway deployment"
git push origin v2
```

### 2. Configure Railway Environment Variables

1. Go to your Railway dashboard
2. Select the `association-rules-service` project
3. Click on the service
4. Go to "Variables" tab
5. Add/update the environment variables listed above
6. **Most important:** Set `CORS_ORIGINS` to include your frontend URL

### 3. Trigger Redeployment

Railway should automatically redeploy after pushing to git. If not:
1. Go to "Deployments" tab
2. Click "Deploy" on the latest commit

### 4. Verify Deployment

After deployment completes, test these endpoints:

#### Health Check
```bash
curl https://association-rules-service-production.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "Apriori Market Basket Analysis API v2",
  "version": "2.0.0"
}
```

#### CORS Test (from browser console on your frontend)
```javascript
fetch('https://association-rules-service-production.up.railway.app/api/v1/transactions/baskets?start_date=2023-01-01&end_date=2026-03-23&limit=10&offset=0')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)
```

If CORS is fixed, you should see data instead of the CORS error.

---

## Troubleshooting

### Issue: Still Getting CORS Error

**Possible Causes:**
1. `CORS_ORIGINS` not set correctly in Railway
2. Frontend URL has typo
3. Need to redeploy after setting env variables

**Solutions:**
1. Double-check the exact frontend URL (including `https://`)
2. Verify environment variable in Railway dashboard
3. Trigger a manual redeploy
4. Check Railway logs for startup errors

### Issue: 502 Bad Gateway

**Possible Causes:**
1. Service failed to start
2. Database connection failed
3. Redis connection failed
4. Missing environment variables

**Solutions:**
1. Check Railway logs:
   - Go to "Deployments" tab
   - Click on latest deployment
   - View logs for errors

2. Verify services are running:
   - PostgreSQL service is up
   - Redis service is up

3. Check DATABASE_URL format:
   ```
   postgresql://user:password@host:port/database
   ```

4. Check Redis URL format:
   ```
   redis://default:password@redis.railway.internal:6379/2
   ```

### Issue: Port Binding Error

**Cause:** Railway sets `PORT` dynamically, your app must listen on it

**Solution:**
- ✅ Already fixed in Dockerfile: `--port ${PORT:-8002}`
- Railway will automatically set PORT, and the app will use it

### Issue: Service Starts but API Returns 404

**Possible Causes:**
1. Wrong API prefix path
2. Router not properly configured

**Solutions:**
1. Verify API prefix is `/api/v1` in config
2. Test with full path: `/api/v1/transactions/baskets`
3. Check `/docs` endpoint for API documentation

---

## Architecture on Railway

```
┌─────────────────────────────────────────┐
│  Frontend (canasta-analytics-web)      │
│  https://canasta-analytics-web-        │
│  production.up.railway.app              │
└─────────────┬───────────────────────────┘
              │ HTTPS requests
              │ (CORS headers validated)
              ↓
┌─────────────────────────────────────────┐
│  Backend (association-rules-service)    │
│  https://association-rules-service-     │
│  production.up.railway.app              │
│  - FastAPI (Uvicorn)                    │
│  - 2 workers                            │
│  - PORT from Railway                    │
└─────┬───────────────────────┬───────────┘
      │                       │
      │ Connects to           │ Connects to
      ↓                       ↓
┌─────────────┐         ┌─────────────┐
│ PostgreSQL  │         │   Redis     │
│  Service    │         │  Service    │
│  (Railway)  │         │  (Railway)  │
└─────────────┘         └─────────────┘
```

---

## Best Practices

1. **Never commit `.env` file** - Use `.env.example` as template
2. **Use Railway's internal DNS** for service-to-service communication:
   - PostgreSQL: Use Railway's `DATABASE_URL` variable reference
   - Redis: Use `redis.railway.internal` instead of public URL
3. **Set appropriate log level** - Use `INFO` for production
4. **Monitor logs** - Railway dashboard shows real-time logs
5. **Use health checks** - `/health` endpoint for monitoring

---

## Celery Worker Setup (If Needed)

If you need background tasks, you'll need to run Celery worker. Railway runs ONE process per service, so you have two options:

### Option 1: Single Service with Both Processes

Create `start.sh`:
```bash
#!/bin/bash
celery -A celery_app.celery worker --loglevel=info --concurrency=2 &
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8002} --workers 2
```

Update Dockerfile:
```dockerfile
COPY start.sh .
RUN chmod +x start.sh
CMD ["./start.sh"]
```

### Option 2: Separate Service for Worker (Recommended)

Create a second Railway service:
- **Service Name**: `association-rules-worker`
- **Start Command**: `celery -A celery_app.celery worker --loglevel=info --concurrency=2`
- **Environment Variables**: Same as API service

---

## Next Steps

1. ✅ Push changes to git
2. ✅ Set environment variables in Railway
3. ✅ Verify deployment health
4. ✅ Test CORS from frontend
5. 📊 Monitor logs for any errors
6. 🔄 Set up Celery worker if needed

---

## Support

If you continue to have issues:
1. Check Railway logs for detailed error messages
2. Verify all environment variables are set correctly
3. Ensure PostgreSQL and Redis services are running
4. Test each service independently (health checks)
