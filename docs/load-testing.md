# Performance & Load Testing

## Scenarios (Locust)

Run against the local or production Docker stack:

```bash
# Install locust
pip install locust

# Start with 10 users, 2/sec spawn rate, headless
locust -f tests/locustfile.py \
  --host=http://localhost:8000 \
  --users=10 \
  --spawn-rate=2 \
  --run-time=5m \
  --headless \
  --csv=results/load-test
```

| Scenario          | Weight | Endpoint(s)                              |
|-------------------|--------|------------------------------------------|
| Health check      | 3      | `GET /health`                            |
| Poll job          | 2      | `GET /api/v1/jobs/{id}`                  |
| Upload & analyze  | 1      | `POST /intake` + `POST /intake/{id}/analyze` |
| Get intake        | 1      | `GET /api/v1/intake/{id}`                |

## Bottlenecks Addressed

### 1. DB Connection Pooling
- QueuePool(10, overflow=20) — confirmed in `core/database.py`
- Pre-ping enabled, recycle 3600s
- **Limit:** ~30 concurrent DB connections before pool exhaustion

### 2. RQ Worker Concurrency
- **Before:** Single worker process, one job at a time
- **After:** `WORKER_CONCURRENCY` env var (default 1, recommended 2–4 on Oracle VM)
- Spawns `N` worker processes via `multiprocessing.Process`
- Set in docker-compose.prod.yml via `${WORKER_CONCURRENCY:-2}`

### 3. Image Processing — Resolution Downscale
- **Before:** Full-resolution images fed to OpenCV (classifier, geometry, deviation detector)
- **After:** `ai/downscale.py` — downscales images to `IMAGE_MAX_DIMENSION` (default 1920px) on the longest edge before passing to pipeline stages
- Uses `cv2.INTER_AREA` for quality downscaling
- Large images can be 5–10x smaller, significantly reducing OpenCV processing time

### 4. Poll Endpoint — Redis Cache
- **Before:** Every poll hits PostgreSQL with a JOIN query
- **After:** `poll_cache_ttl=2s` — cached in Redis (key: `job_cache:{job_id}:{workshop_id}`)
- Terminal status responses cached; non-terminal (queued/running) skip cache
- Falls back gracefully if Redis is unavailable
- At 50 polls/sec, this saves ~50 DB queries/sec for completed jobs

## Expected Throughput

| Metric                | Before           | After (estimated)  |
|-----------------------|------------------|--------------------|
| Max polls/sec         | ~20 (DB-bound)   | ~200+ (cached)     |
| Concurrent assessments| 1 (single worker)| 2–4 (multi-worker) |
| Image processing/job  | ~15s (full res)  | ~8s (downscaled)   |
| DB pool utilization   | 30 connections   | 30 connections     |

## Running the Full Suite

```bash
# Fast tests (CI)
docker compose run --rm backend-api python3 -m pytest tests/ -q

# Slow tests (full pipeline)
docker compose run --rm backend-api python3 -m pytest tests/test_integration_pipeline.py --runslow

# Load test
locust -f tests/locustfile.py --headless -u 10 -r 2 --run-time 3m
```
