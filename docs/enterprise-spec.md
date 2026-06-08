# RetroMind AI — Enterprise Technical Specification

## 1. Overview

This specification covers architecture, data models, API contracts, and implementation details for enterprise-grade features across security, observability, multi-tenancy, frontend, and DevOps.

---

## 2. Security Architecture

### 2.1 Role-Based Access Control (RBAC)

#### Data Model

Add a `workspace_roles` table and extend the `User` model:

```sql
CREATE TABLE workspace_roles (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workshop_id   UUID NOT NULL REFERENCES workshops(id) ON DELETE CASCADE,
    role          VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'operator', 'viewer')),
    invited_by    UUID REFERENCES users(id),
    invited_at    TIMESTAMPTZ,
    accepted_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, workshop_id)
);
```

Add to existing `User` model: `current_workshop_id` (UUID nullable) for multi-workshop users.

#### Permission Matrix

| Action | Admin | Operator | Viewer |
|--------|:-----:|:--------:|:------:|
| View assessments | ✅ | ✅ | ✅ |
| Start assessment | ✅ | ✅ | ❌ |
| View reports | ✅ | ✅ | ✅ |
| View settings | ✅ | ✅(read-only) | ❌ |
| Edit settings | ✅ | ❌ | ❌ |
| Manage team | ✅ | ❌ | ❌ |
| Billing | ✅ | ❌ | ❌ |
| Invite members | ✅ | ❌ | ❌ |
| Remove members | ✅ | ❌ | ❌ |
| View audit log | ✅ | ✅ | ❌ |

#### Implementation

- `backend/core/rbac.py` — Dependency `require_role(workshop_id, roles: list[str])` that checks `WorkspaceRoles` table.
- Add middleware that attaches `current_user_role` to request state.
- Existing endpoints: audit and add `require_role` where needed. Admin endpoints get `require_role(..., ["admin"])`.
- Migration `011_add_workspace_roles.py`.

### 2.2 OAuth / SSO

#### Providers

| Provider | Protocol | Library |
|----------|----------|---------|
| Google | OpenID Connect | `authlib` |
| Microsoft Azure AD | OpenID Connect | `authlib` |
| Generic SAML 2.0 | SAML | `python3-saml` |

#### Data Model

```sql
ALTER TABLE users ADD COLUMN sso_provider VARCHAR(20);
ALTER TABLE users ADD COLUMN sso_subject VARCHAR(255);
CREATE INDEX idx_users_sso ON users(sso_provider, sso_subject);
```

#### Flow

1. User clicks "Sign in with Google" → redirected to `/api/v1/auth/sso/google/authorize`.
2. Backend redirects to Google OAuth consent screen with state parameter (random nonce stored in Redis, 10min TTL).
3. User consents → Google redirects to `/api/v1/auth/sso/google/callback` with `code` and `state`.
4. Backend exchanges code for tokens, validates state, extracts `sub` and `email`.
5. If user exists with matching `sso_provider` + `sso_subject` → issue JWT.
6. If not → create new user or link to existing (if email matches and user is in "linking" mode).

#### Endpoints

```
GET  /api/v1/auth/sso/{provider}/authorize
     -> 302 (redirect to IdP)

GET  /api/v1/auth/sso/{provider}/callback
     -> 302 (redirect to frontend with JWT token)

POST /api/v1/auth/sso/link
     Authorization: Bearer <jwt>
     Body: { "provider": "google", "authorization_code": "..." }
     -> 200 { "status": "linked" }
```

### 2.3 Data Encryption at Rest

#### Storage Encryption

- Use `cryptography` library's `Fernet` (AES-256-CBC with HMAC) for file encryption.
- Encryption key stored in `ENCRYPTION_KEY` environment variable (base64-encoded 32-byte key).
- On upload: encrypt file bytes before passing to S3 client. Store encrypted blob.
- On read: fetch encrypted blob from S3, decrypt in memory, return to client.

```python
# backend/core/crypto.py
from cryptography.fernet import Fernet

cipher = Fernet(settings.encryption_key)

def encrypt_file(data: bytes) -> bytes:
    return cipher.encrypt(data)

def decrypt_file(encrypted: bytes) -> bytes:
    return cipher.decrypt(encrypted)
```

#### PII Column Encryption

- Use `sqlalchemy-utils` `EncryptedType` for PII columns: `workshops.name`, `workshops.email`, `users.name`, `users.email`.
- Key: same `ENCRYPTION_KEY` environment variable.

### 2.4 Audit Trail — Before/After State

#### Data Model

```sql
CREATE TABLE audit_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_type      VARCHAR(20) NOT NULL CHECK (actor_type IN ('user', 'api_key', 'system')),
    actor_id        VARCHAR(255) NOT NULL,
    workshop_id     UUID REFERENCES workshops(id),
    action          VARCHAR(20) NOT NULL CHECK (action IN ('create', 'read', 'update', 'delete')),
    entity_type     VARCHAR(50) NOT NULL,
    entity_id       UUID NOT NULL,
    before_state    JSONB,
    after_state     JSONB,
    truncated       BOOLEAN DEFAULT FALSE,
    metadata        JSONB,
    correlation_id  UUID
);

CREATE INDEX idx_audit_workshop ON audit_events(workshop_id, timestamp DESC);
CREATE INDEX idx_audit_entity ON audit_events(entity_type, entity_id);
```

#### Implementation

- `backend/core/audit.py` — Extend existing audit logger.
- Use SQLAlchemy event listeners (`after_insert`, `after_update`, `after_delete`) on primary entities (intake, jobs, workshops, users).
- Serialize before/after state as JSONB. Truncate to 4KB if payload exceeds threshold.
- Expose via: `GET /api/v1/admin/audit-log?workshop_id=...&entity_type=...&from=...&to=...`

### 2.5 API Key Rotation & Breach Detection

#### Key Rotation

- `expires_at` column added to workshop (or separate api_keys table).
- Cron job (daily) checks for keys expiring in 14 days and 3 days → sends notification email.
- On API key auth, check `expires_at > NOW()`. If expired → 401.
- Renewal: `POST /api/v1/auth/renew-key` returns new key with fresh `expires_at`.

#### Breach Detection

- Redis-based counter: `apikey_breach:{key_prefix}:{hour_bucket}` → set of IPs.
- Background task checks every minute: if any key has >3 distinct IPs in current 5-min window → auto-revoke.
- Revocation: set `api_key_revoked_at = NOW()`, send alert email.
- Allowlisted IPs stored in `api_key_ip_allowlist` JSONB column.

### 2.6 Rate Limiting Per Tier

#### Tier Limits

| Tier | Rate Limit | Burst | Assessment/month | Storage |
|------|:----------:|:-----:|:----------------:|:-------:|
| Free | 100/min | 200/10s | 10 | 500MB |
| Pro | 500/min | 1000/10s | 100 | 5GB |
| Enterprise | 5000/min | 10000/10s | Unlimited | 50GB |

#### Implementation

- Extend `backend/core/limiter.py` to read `workshop.tier` from request state.
- Use `slowapi` with a custom key function: `lambda: f"{workshop_id}:{tier}"`.
- Return rate limit headers on every response.
- Rate limit exceeded → 429 with JSON body `{"detail": "Rate limit exceeded. Upgrade at /settings/billing", "retry_after": 12}`.

---

## 3. Observability Architecture

### 3.1 Deep Health Checks

```
GET /health
-> 200 {
    "status": "ok" | "degraded" | "down",
    "version": "1.0.0",
    "uptime_seconds": 123456,
    "checks": {
        "postgresql":    { "status": "ok", "latency_ms": 2 },
        "redis":         { "status": "ok", "latency_ms": 1 },
        "neo4j":         { "status": "degraded", "latency_ms": 500, "message": "High latency" },
        "queue_depth":   { "status": "ok", "depth": 3 },
        "model_onnx":    { "status": "ok", "latency_ms": 45 },
        "object_store":  { "status": "ok", "latency_ms": 120 }
    }
}

GET /health/ready
-> 200 { "status": "ok" }
-> 503 { "status": "not_ready", "failing": ["postgresql"] }
```

### 3.2 Structured JSON Logging

#### Log Format

```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=structlog.threadlocal.wrap_dict(dict),
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

#### Correlation ID Middleware

```python
@api.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid7()))
    request.state.correlation_id = correlation_id
    with structlog.contextvars.bind_contextvars(correlation_id=correlation_id):
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
```

### 3.3 Distributed Tracing

#### Dependencies

- `opentelemetry-distro`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-httpx`, `opentelemetry-instrumentation-sqlalchemy`, `opentelemetry-instrumentation-redis`, `opentelemetry-exporter-otlp`

#### Span Structure per Assessment

```
POST /api/v1/intake/{id}/analyze
  ├── enqueue_job (Redis)
  └── Worker: process_assessment
      ├── upload_validation
      ├── image_quality_check
      ├── vehicle_classification
      │   ├── onnx_inference
      │   └── clip_inference (if enabled)
      ├── geometry_extraction
      ├── deviation_detection
      ├── feasibility_scoring
      ├── risk_analysis
      ├── battery_optimization
      │   └── generative_refinement (if enabled)
      ├── wiring_generation
      │   └── generative_refinement (if enabled)
      └── digital_twin
```

### 3.4 Circuit Breakers

#### Circuit Breaker Pattern

```python
from circuitbreaker import circuit

@circuit(
    failure_threshold=5,
    recovery_timeout=30,
    expected_exception=(ConnectionError, TimeoutError),
    name="neo4j_query"
)
def neo4j_query(query, params):
    ...
```

Or custom implementation in `backend/core/circuit_breaker.py`:

```python
class CircuitBreaker:
    states: dict[str, CircuitState]  # service_name -> state

    async def call(self, service: str, fn, fallback=None):
        state = self.states.get(service, CircuitState.CLOSED)
        if state == CircuitState.OPEN:
            if fallback: return await fallback()
            raise CircuitBreakerOpenError(service)
        try:
            result = await fn()
            self._record_success(service)
            return result
        except Exception:
            self._record_failure(service)
            if fallback: return await fallback()
            raise
```

#### Wrapped Services

| Service | Fallback |
|---------|----------|
| Neo4j | Heuristic recommendation engine |
| Redis | Local in-memory cache (degraded) |
| OpenAI | Skip generative refinement |
| Anthropic | Skip generative refinement |
| Object Storage | Return cached/empty result |

### 3.5 Backup & DR

#### Infrastructure

```
backup/
├── pg_dump.sh          # pg_dump -> gzip -> s3 cp (parallel)
├── neo4j_dump.sh       # neo4j-admin dump -> gzip -> s3 cp
├── restore_pg.sh       # s3 cp -> gunzip -> pg_restore
├── restore_neo4j.sh    # s3 cp -> gunzip -> neo4j-admin load
└── schedule.sh         # Cron wrapper with retry + alert
```

#### Retention Policy

| Backup Type | Frequency | Retention |
|-------------|-----------|-----------|
| PostgreSQL full | Daily 02:00 UTC | 30 daily + 12 monthly |
| Neo4j full | Daily 03:00 UTC | 30 daily + 12 monthly |
| WAL archiving | Continuous (if enabled) | 7 days |

### 3.6 Alerting

#### Prometheus Rules (`infra/prometheus/alerts.yml`)

```yaml
groups:
  - name: retro-mind-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels: { severity: critical }
      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 5
        for: 5m
        labels: { severity: warning }
      - alert: QueueDepth
        expr: rq_queue_depth > 100
        for: 2m
        labels: { severity: warning }
      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state{state="open"} > 0
        labels: { severity: critical }
      - alert: BackupFailed
        expr: backup_success{job="pg_dump"} == 0
        labels: { severity: critical }
      - alert: DiskSpace
        expr: (disk_total_bytes - disk_free_bytes) / disk_total_bytes > 0.85
        labels: { severity: warning }
```

#### Grafana Dashboard

Provided as `infra/grafana/dashboard.json` (exportable JSON model) with panels:
- **RPS & Error Rate** — Time series, rate of requests by status code
- **Latency (P50/P95/P99)** — Time series with thresholds
- **Queue Depth** — Gauge + time series
- **Circuit Breakers** — State table per service
- **DB Connections** — Active/idle/waiting
- **Rate Limit Hits** — 429 count per tier
- **Backup Status** — Last success time, age of latest backup

---

## 4. Multi-Tenancy Architecture

### 4.1 Subscription & Billing

#### Data Model

```sql
ALTER TABLE workshops ADD COLUMN stripe_customer_id VARCHAR(255);
ALTER TABLE workshops ADD COLUMN stripe_subscription_id VARCHAR(255);
ALTER TABLE workshops ADD COLUMN subscription_status VARCHAR(20) DEFAULT 'active'
    CHECK (subscription_status IN ('active', 'past_due', 'canceled', 'trialing'));
ALTER TABLE workshops ADD COLUMN billing_period_start TIMESTAMPTZ;
ALTER TABLE workshops ADD COLUMN billing_period_end TIMESTAMPTZ;
ALTER TABLE workshops ADD COLUMN trial_ends_at TIMESTAMPTZ;
```

#### Pricing Plans

Add a `pricing_plans` table:

```sql
CREATE TABLE pricing_plans (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tier            VARCHAR(20) NOT NULL UNIQUE CHECK (tier IN ('free', 'pro', 'enterprise')),
    name            VARCHAR(100) NOT NULL,
    price_monthly   INTEGER NOT NULL,      -- cents
    price_yearly    INTEGER NOT NULL,      -- cents
    max_users       INTEGER,
    max_assessments INTEGER,
    max_storage_mb  INTEGER,
    rate_limit      INTEGER,
    features        JSONB NOT NULL DEFAULT '[]'
);
```

#### Stripe Integration

- Webhook endpoints: `POST /api/v1/billing/stripe-webhook` (signature-verified).
- Events handled: `checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`, `customer.subscription.updated`, `customer.subscription.deleted`.
- On `invoice.payment_failed`: set `subscription_status = 'past_due'`, send email, 7-day grace period.
- After 7 days past due: downgrade to Free tier.

### 4.2 Team Management

#### Invitation Flow

1. Admin POSTs `/api/v1/workshop/invite` with `{ email, role }`.
2. System creates `WorkspaceInvitation` record, sends email with unique `token` (signed JWT, 72h expiry).
3. Recipient clicks link → frontend calls `POST /api/v1/auth/accept-invite { token }`.
4. If recipient has no account: redirect to signup with invitation token pre-filled.
5. After signup/login: `WorkspaceRoles` record created with `accepted_at = NOW()`.

#### API

```
GET    /api/v1/workshop/members                     -> list members with roles
POST   /api/v1/workshop/invite                      -> { email, role }
DELETE /api/v1/workshop/members/{user_id}            -> remove member
PATCH  /api/v1/workshop/members/{user_id}/role       -> { role }
GET    /api/v1/workshop/invitations                  -> list pending invitations
DELETE /api/v1/workshop/invitations/{invitation_id}  -> revoke invitation
```

### 4.3 Email Notifications

#### Email Service

```
INFRASTRUCTURE/
├── email/
    ├── sender.py         # SMTP/SendGrid/SES abstraction
    ├── templates/
    │   ├── assessment_complete.html
    │   ├── assessment_failed.html
    │   ├── compliance_pass.html
    │   ├── compliance_fail.html
    │   ├── api_key_expiring.html
    │   ├── team_invitation.html
    │   ├── payment_receipt.html
    │   ├── payment_failed.html
    │   └── daily_digest.html
    └── scheduler.py      # RQ job for daily digest
```

#### Email Preferences Model

```sql
CREATE TABLE email_preferences (
    user_id             UUID PRIMARY KEY REFERENCES users(id),
    assessment_complete BOOLEAN DEFAULT TRUE,
    assessment_failed   BOOLEAN DEFAULT TRUE,
    compliance_alerts   BOOLEAN DEFAULT TRUE,
    api_key_expiry      BOOLEAN DEFAULT TRUE,
    team_invitations    BOOLEAN DEFAULT TRUE,
    billing             BOOLEAN DEFAULT TRUE,
    daily_digest        BOOLEAN DEFAULT FALSE,
    digest_frequency    VARCHAR(10) DEFAULT 'daily'
);
```

### 4.4 Usage Quotas & Metering

#### Metering Data Model

```sql
CREATE TABLE usage_metering (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workshop_id     UUID NOT NULL REFERENCES workshops(id),
    metric          VARCHAR(50) NOT NULL,
    amount          INTEGER NOT NULL DEFAULT 0,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE MATERIALIZED VIEW monthly_usage AS
SELECT
    workshop_id,
    metric,
    DATE_TRUNC('month', recorded_at) AS month,
    SUM(amount) AS total
FROM usage_metering
GROUP BY workshop_id, metric, DATE_TRUNC('month', recorded_at);
```

#### Metrics Tracked

| Metric | Unit | Incremented When |
|--------|------|-----------------|
| `assessments_completed` | count | Job reaches `completed` |
| `api_calls` | count | Every API request (after auth) |
| `storage_bytes` | bytes | Image upload |
| `images_uploaded` | count | Image upload |
| `recommendations_generated` | count | Assessment completes |

### 4.5 White-Labeling

#### Data Model

```sql
ALTER TABLE workshops ADD COLUMN branding JSONB DEFAULT '{}'::jsonb;
-- { "logo_url": "...", "primary_color": "#2563eb", "secondary_color": "#7c3aed", "custom_domain": "..." }
```

#### Implementation

- CSS custom properties (`--brand-primary`, `--brand-secondary`) injected via API response + stored in localStorage.
- Logo URL returned in `GET /api/v1/workshop/settings` and applied to header/email templates/reports.
- Custom domain: Caddy automatically provisions TLS certs. Workshop's DNS must CNAME to platform domain.
- PDF reports: logo + brand colors applied via WeasyPrint or Playwright PDF.

### 4.6 Customer Portal

#### Data Model

```sql
ALTER TABLE jobs ADD COLUMN customer_token VARCHAR(64) UNIQUE;
ALTER TABLE jobs ADD COLUMN customer_status VARCHAR(20) DEFAULT 'pending'
    CHECK (customer_status IN ('pending', 'viewed', 'approved', 'changes_requested'));
ALTER TABLE jobs ADD COLUMN customer_approved_at TIMESTAMPTZ;
ALTER TABLE jobs ADD COLUMN customer_notes TEXT;
```

#### Portal Page

- Route: `GET /customer/{token}` (no auth required).
- Renders: vehicle summary, status, feasibility score (non-technical), recommendation summary, approve/request changes buttons.
- Token is a random 64-char hex string (sha256 hashed in DB for storage).
- Token expires after 30 days of inactivity.

### 4.7 PDF Report Export

#### Flow

1. User clicks "Download PDF" on report page.
2. Frontend calls `POST /api/v1/reports/{assessment_id}/export-pdf`.
3. Backend enqueues PDF generation job (RQ worker).
4. Worker uses Playwright (headless Chromium) or WeasyPrint to render HTML → PDF.
5. PDF is uploaded to object storage. Job status updated to `ready` with download URL.
6. If generation >30s: email notification with download link.

#### Endpoints

```
POST   /api/v1/reports/{assessment_id}/export-pdf
       -> 202 { "export_job_id": "uuid", "status": "processing" }

GET    /api/v1/reports/{assessment_id}/export-pdf/{export_job_id}
       -> 200 { "status": "ready", "download_url": "..." }
       -> 200 { "status": "processing" }
       -> 404
```

### 4.8 Batch Operations

#### Batch Flow

```
POST /api/v1/batch/intake
Content-Type: multipart/form-data
{ "batch_file": <zip> }

-> 202 {
    "batch_id": "uuid",
    "total": 10,
    "jobs": [
        { "vehicle_name": "vehicle_01", "intake_id": "uuid", "status": "created" },
        { "vehicle_name": "vehicle_02", "intake_id": "uuid", "status": "created" },
        { "vehicle_name": "vehicle_03", "intake_id": "uuid", "status": "validation_failed", "error": "Missing mandatory view: left_side_profile" }
    ]
}
```

#### Batch Dashboard

```
GET /api/v1/batch/{batch_id}
-> 200 {
    "batch_id": "uuid",
    "total": 10,
    "completed": 5,
    "failed": 1,
    "avg_feasibility": 72.3,
    "jobs": [ ... ]
}
```

### 4.9 Mobile Field Capture

#### Camera Capture UI

- Uses `MediaDevices.getUserMedia` with `facingMode: "environment"`.
- View-specific overlay guides: rectangle outline for each mandatory view.
- After capture: image is validated client-side (blur detection via Laplacian variance), shows retake prompt if blurry.
- Upload: `POST /api/v1/intake` with captured blob.

#### Offline Support

- Service worker caches: app shell, assessment history (IndexedDB), captured photos (IndexedDB, up to 50MB quota).
- Background sync: when connectivity returns, queued photos are uploaded and pending intakes are submitted.
- Offline indicator in header: "Offline — X photos pending sync".

---

## 5. Frontend Architecture

### 5.1 Internationalization

#### Setup

```
frontend/
├── messages/
│   ├── en.json
│   ├── hi.json
│   ├── ta.json
│   ├── bn.json
│   ├── te.json
│   └── kn.json
├── i18n.ts              # next-intl configuration
└── components/
    └── LanguagePicker.tsx
```

#### Implementation

- Use `next-intl` for routing-based i18n (`/en/history`, `/hi/history`).
- Default locale from `Accept-Language` header or `en`.
- All user-facing strings externalized. CI checks for missing translation keys.

### 5.2 PWA

#### Manifest

```json
{
  "name": "RetroMind AI",
  "short_name": "RetroMind",
  "description": "EV Retrofit Intelligence Platform",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0f172a",
  "theme_color": "#3b82f6",
  "icons": [...]
}
```

#### Service Worker

- `frontend/public/sw.js` — Workbox-based service worker.
- Precaches: app shell (HTML, JS, CSS, fonts).
- Runtime caches: API responses (history, settings) with NetworkFirst strategy.
- Offline fallback page: `offline.html`.

### 5.3 Accessibility

#### Checklist

- [ ] All images have `alt` text.
- [ ] All form inputs have associated `<label>`.
- [ ] Color contrast ≥ 4.5:1 (normal text), ≥ 3:1 (large text).
- [ ] Focus order follows visual order.
- [ ] Interactive elements are keyboard accessible.
- [ ] ARIA landmarks used: `<nav>`, `<main>`, `<aside>`.
- [ ] Error messages are announced by screen readers (`aria-live="polite"`).
- [ ] Custom components have appropriate ARIA roles.

#### CI Check

- `pa11y-ci` runs on every PR against all routes. Fail build on new violations.

### 5.4 Skeleton Loading

#### Component Pattern

```tsx
function Skeleton({ className }: { className?: string }) {
  return <div className={`animate-pulse bg-gray-200 rounded ${className}`} />;
}

// Page-level skeleton:
function HistoryPageSkeleton() {
  return (
    <div className="space-y-4">
      {[1,2,3].map(i => (
        <div key={i} className="flex gap-4">
          <Skeleton className="w-24 h-24" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}
```

### 5.5 Error Boundaries

#### Per-Page Wrapping

```tsx
// layout.tsx (per-page or per-section)
export default function PageLayout({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary fallback={<PageErrorFallback />}>
      {children}
    </ErrorBoundary>
  );
}

function PageErrorFallback({ error, resetErrorBoundary }: { error: Error; resetErrorBoundary: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center p-8">
      <h2 className="text-xl font-semibold">Something went wrong</h2>
      <p className="text-gray-500 mt-2">{error.message}</p>
      <button onClick={resetErrorBoundary} className="mt-4 btn-primary">
        Try Again
      </button>
    </div>
  );
}
```

---

## 6. DevOps Architecture

### 6.1 CI/CD Pipeline Updates

```yaml
# .github/workflows/ci.yml additions
jobs:
  secrets-check:
    runs-on: ubuntu-latest
    steps:
      - run: |
          MISSING=""
          for secret in ORACLE_HOST ORACLE_USER SSH_KEY; do
            if [ -z "${{ secrets[secret] }}" ]; then MISSING="$MISSING $secret"; fi
          done
          if [ -n "$MISSING" ]; then echo "Missing secrets:$MISSING"; exit 1; fi

  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install pip-audit
      - run: pip-audit -r backend/requirements.txt
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: npm audit --audit-level=high
        working-directory: frontend

  migration-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_DB: test, POSTGRES_PASSWORD: test }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r backend/requirements.txt
      - run: alembic upgrade head
        working-directory: backend
        env: { DATABASE_URL: "postgresql://postgres:test@localhost/test" }
      - run: alembic downgrade -1
        working-directory: backend
        env: { DATABASE_URL: "postgresql://postgres:test@localhost/test" }

  container-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -f backend/Dockerfile.prod -t app .
      - uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'app'
          format: 'sarif'
          output: 'trivy-results.sarif'
          exit-code: '1'
          severity: 'CRITICAL'
```

### 6.2 Container Image Signing

```yaml
# .github/workflows/deploy.yml additions
sign:
  runs-on: ubuntu-latest
  needs: [test]
  steps:
    - uses: sigstore/cosign-installer@v3
    - run: cosign sign --yes <image>@<digest>
      env:
        COSIGN_EXPERIMENTAL: 1  # keyless signing via OIDC
```

### 6.3 Infrastructure Updates

```yaml
# docker-compose.prod.yml additions
services:
  prometheus:
    image: prom/prometheus
    volumes: [./infra/prometheus:/etc/prometheus]
  grafana:
    image: grafana/grafana
    volumes: [./infra/grafana:/etc/grafana/provisioning]
  backup-scheduler:
    build: ./infra/backup
    volumes: [backup-data:/data]
```

---

## 7. Database Migrations Summary

| Migration | Description |
|-----------|-------------|
| 011 | `workspace_roles` table, RBAC support |
| 012 | SSO fields on users, OAuth state cache |
| 013 | `audit_events` table with before/after state |
| 014 | API key expiry, breach detection columns |
| 015 | Pricing plans, billing fields, usage metering |
| 016 | Email preferences, notification templates |
| 017 | Batch operations tracking |
| 018 | Customer portal fields, invite tokens |
| 019 | Workshop branding config (JSONB) |

---

## 8. Env Variables Additions

| Variable | Purpose |
|----------|---------|
| `ENCRYPTION_KEY` | AES-256 encryption key (base64) |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `AZURE_CLIENT_ID` | Azure AD OAuth client ID |
| `AZURE_CLIENT_SECRET` | Azure AD OAuth client secret |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `SAML_METADATA_URL` | SAML IdP metadata URL |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` | Email sender config |
| `STRIPE_SECRET_KEY` | Stripe API secret key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `OTLP_ENDPOINT` | OpenTelemetry collector endpoint |
| `BACKUP_S3_BUCKET` | S3 bucket for backups |
| `CUSTOM_DOMAIN_REGEXP` | Allowed custom domain pattern |
