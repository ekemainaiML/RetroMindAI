# RetroMind AI — Enterprise Product Requirements

## Overview

This document defines product requirements for enterprise-grade features across Security, Observability & Reliability, Multi-Tenancy & Business, Frontend/UX, and DevOps. These features transform RetroMind AI from a single-workshop tool into a multi-tenant, enterprise-ready platform.

---

## 1. Security

### 1.1 Role-Based Access Control (RBAC) 📋

**Problem:** Currently, the only auth is a per-workshop API key or per-user JWT. There are no admin/operator/viewer roles inside a workshop, making it impossible to delegate access.

- As a workshop owner, I want to assign admin, operator, and viewer roles to team members so that I can control who can run assessments, modify settings, and view reports.
- As a workshop operator, I want to perform assessments without access to billing or admin settings so that I cannot accidentally change configuration.
- As a compliance auditor, I want viewer access to past assessments and reports so that I can verify compliance without modifying data.
- [ ] Default role is `operator` for new team members.
- [ ] Only `admin` can modify workshop settings, manage billing, and invite/remove members.
- [ ] `viewer` can read assessments, reports, and history but cannot start new assessments.
- [ ] Edge case: if a workshop has only one member, that member is auto-assigned `admin`.

### 1.2 OAuth / SSO (Google, Azure AD, SAML) ✅

**Problem:** No third-party identity provider support. Enterprise customers require SSO.

- As an enterprise workshop operator, I want to sign in with my Google/ Microsoft / corporate SSO account so that I don't need to manage yet another password.
- As a fleet operator, I want SAML-based SSO so that my organization's IT department can manage access centrally.
- [x] Google OAuth login is available as the first SSO provider.
- [x] Microsoft Azure AD login is available as the second SSO provider.
- [ ] Generic SAML 2.0 support is available for custom enterprise IdPs.
- [x] First-time SSO login auto-provisions a workshop account linked to the SSO identity.
- [x] Edge case: SSO identity already linked to a different workshop shows clear error and support contact.

### 1.3 Data Encryption at Rest 📋

**Problem:** Uploaded images on disk and assessment results in the database are unencrypted, creating compliance risk.

- As a security-conscious workshop owner, I want all uploaded vehicle images encrypted at rest so that customer data is protected even if storage is compromised.
- As a compliance officer, I want assessment data encrypted in the database so that we meet SOC2 and ISO 27001 requirements.
- [ ] All uploaded images are encrypted using AES-256-GCM before being written to object storage.
- [ ] All PII fields in PostgreSQL (workshop name, email, user names) are encrypted at the column level.
- [ ] Encryption keys are managed via environment-managed key (not hardcoded).
- [ ] Edge case: decryption failure on read logs an alert and returns a user-friendly error.

### 1.4 Audit Trail Depth ✅

**Problem:** Current audit logs track method/path/status but not before/after state or data access, which is a SOC2/ISO 27001 gap.

- As a security auditor, I want to see what changed (before and after values) for every state-modifying operation so that I can verify data integrity.
- As a workshop admin, I want to see who accessed each assessment and when so that I can detect unauthorized access.
- [x] Every CREATE, UPDATE, DELETE operation logs the complete before/after state of the affected entity.
- [x] Every read access to assessment data logs the user/API key, timestamp, and assessment ID.
- [x] Audit log UI is available to admin dashboard showing a filterable, searchable event stream.
- [x] Edge case: large before/after payloads are truncated with a `truncated: true` flag.

### 1.5 API Key Rotation Policy ✅

**Problem:** API keys can be renewed manually but there is no forced expiry or breach detection mechanism.

- As a security admin, I want API keys to expire automatically after a configurable period (default 90 days) so that stale keys are not a risk.
- As a workshop owner, I want to be notified when an API key is about to expire so that I can rotate it before service disruption.
- [x] API keys have a configurable `expires_at` field (default 90 days from creation).
- [ ] A warning email is sent 14 days and 3 days before key expiry.
- [x] Expired keys return 401 with a clear message.
- [x] Breach detection: if the same key is used from >3 distinct IPs within 5 minutes, the key is auto-revoked and an alert is sent.
- [x] Edge case: keys used in automated CI/CD pipelines can opt out of IP-based breach detection via an allowlist.

### 1.6 Rate Limiting Per Tier ✅

**Problem:** A single 1000 request/minute limit regardless of workshop tier — no upsell mechanism exists.

- As a platform operator, I want to enforce different rate limits per subscription tier so that I can monetize higher usage.
- As a free-tier workshop, I want clear visibility into my rate limit and remaining quota so that I'm not surprised by blocks.
- [x] Rate limits are configurable per tier.
- [x] Rate limit headers are returned on every API response.
- [x] When limit is exceeded, response is 429 with `Retry-After` header.
- [x] Edge case: burst allowance is permitted to handle short spikes.

---

## 2. Observability & Reliability

### 2.1 Deep Health Checks ✅

**Problem:** `/health` returns OK if the server is up. No DB/Redis/Neo4j/queue-depth/model checks exist, so degraded state cannot be detected.

- As a platform operator, I want a `/health` endpoint that checks every dependency (PostgreSQL, Redis, Neo4j, queue depth, model readiness) so that I can detect degraded state before customers are affected.
- [x] `/health` returns individual status for each dependency with `ok`, `degraded`, or `down`.
- [ ] `/health/ready` returns OK only when all critical dependencies (DB + Redis) are responsive.
- [x] Queue depth is reported via Prometheus metrics.
- [ ] Model health checks verify that ONNX/PyTorch models load and produce output on a synthetic input.
- [x] Edge case: non-critical dependency being down reports `degraded` but does not fail the readiness check.

### 2.2 Structured JSON Logging 📋

**Problem:** Plain text logging output with no correlation IDs makes debugging production issues difficult.

- As a backend engineer, I want structured JSON logs with correlation IDs so that I can trace a single request across API, worker, and database.
- [ ] All log output is structured JSON with keys: `timestamp`, `level`, `logger`, `message`, `correlation_id`, `service`, `environment`.
- [ ] Every incoming request generates a `correlation_id` (UUIDv7) that is propagated to workers via job metadata.
- [ ] Logs include request duration, status code, and route pattern for every request.
- [ ] Edge case: if correlation_id cannot be propagated (e.g., external webhook), a new one is generated and the parent_id is logged as `null`.

### 2.3 Distributed Tracing (OpenTelemetry) 📋

**Problem:** No OpenTelemetry tracing across API → Worker → DB makes it impossible to trace failed assessments end-to-end.

- As a platform engineer, I want end-to-end tracing from API request through worker pipeline to database queries so that I can identify bottlenecks and diagnose failures.
- [ ] OpenTelemetry SDK is instrumented in the FastAPI application with auto-instrumentation for HTTP, Redis, PostgreSQL, and RQ.
- [ ] Traces are exported to a configurable OTLP endpoint (Jaeger, Grafana Tempo, or SigNoz).
- [ ] Each assessment pipeline stage is a distinct span with duration, status, and input size attributes.
- [ ] Edge case: if the tracing backend is unreachable, the application logs a warning and continues without tracing (non-blocking).

### 2.4 Circuit Breakers ✅

**Problem:** Neo4j, Redis, OpenAI/Anthropic calls have no circuit breaker, so a downstream failure can cascade and degrade the entire system.

- As a platform engineer, I want circuit breakers on all external service calls so that a single downstream failure does not cascade across the system.
- [x] Circuit breakers are implemented for: Neo4j queries, Redis operations, OpenAI API calls, Anthropic API calls, and object storage operations.
- [x] Circuit states: `closed` (normal), `open` (failing — requests fail fast), `half-open` (probing recovery).
- [x] After 5 consecutive failures, circuit opens for 30 seconds (configurable per service).
- [x] After 30 seconds, circuit transitions to half-open and allows 1 probe request. Success closes it; failure reopens it.
- [ ] Circuit state changes are exposed as a Prometheus metric.
- [x] Edge case: during open state, the system degrades gracefully (e.g., Neo4j circuit open → use heuristic fallback).

### 2.5 Backup & Disaster Recovery ✅

**Problem:** No automated PostgreSQL backup, no Neo4j dump, no restore procedure — data loss risk is unaddressed.

- As a platform operator, I want automated daily backups of PostgreSQL and Neo4j so that I can recover from data loss within 1 hour.
- [x] PostgreSQL: automated `pg_dump` runs daily, compressed and uploaded to object storage (`infra/backup/pg_dump.sh`). Retention: 30 daily.
- [ ] Neo4j: automated `neo4j-admin database dump` runs daily, uploaded to object storage.
- [ ] A documented restore procedure exists in `docs/ops/disaster-recovery.md`.
- [ ] Backup success/failure is monitored via health check and alerting.
- [x] Edge case: backup fails — partial file is deleted, alert fires.

### 2.6 Alerting 📋

**Problem:** Prometheus metrics exist but there are no rules, no dashboard, and no pager — operating blind in production.

- As a platform operator, I want predefined alerting rules and a Grafana dashboard so that I am notified before issues reach customers.
- [ ] Alerting rules cover: API error rate >5% over 5min, P95 latency >5s, queue depth >100, circuit breaker open, backup failure, disk usage >85%.
- [ ] A Grafana dashboard is provided with panels for: request rate, error rate, latency (P50/P95/P99), queue depth, circuit breaker states, DB connections, rate limit hit count.
- [ ] A `/metrics` endpoint exposes all Prometheus metrics.
- [ ] Alerts route to a configurable webhook (Slack, PagerDuty, or email).
- [ ] Edge case: alerting backend unreachable — alerts are buffered locally and retried up to 3 times.

---

## 3. Multi-Tenancy & Business

### 3.1 Subscription Tiers ✅

**Problem:** `Workshop.tier` column exists but there is no pricing, payment, or plan enforcement — cannot monetize.

- As a platform operator, I want to define subscription tiers (Free, Pro, Enterprise) with specific feature limits so that I can monetize the platform.
- As a workshop owner, I want to see my current plan, usage, and upgrade options so that I can choose the right tier.
- [x] Tiers: Free (1 active user, 10 assessments/month, 100 images), Pro (5 users, 100 assessments/month, 1000 images), Enterprise (unlimited).
- [x] Tier enforcement happens at API middleware: requests exceeding tier limits return 402 Payment Required.
- [x] A billing settings page shows current plan, usage stats, and upgrade/downgrade flow.
- [x] Stripe integration handles payment processing with monthly/yearly billing (endpoints: `/billing/create-checkout`, `/billing/subscription`, `/billing/stripe-webhook`).
- [x] Edge case: payment fails — workshop is downgraded to Free tier at the end of the billing period, with 7-day grace period.

### 3.2 Team Management 📋

**Problem:** Single user per workshop, no invitations or roles — cannot grow workshop accounts.

- As a workshop admin, I want to invite team members via email so that my whole team can use RetroMind AI.
- [ ] Admin can send invitations from the Team Settings page. Invitations expire after 72 hours.
- [ ] Invited user receives an email with a unique signup link. Clicking it creates an account linked to the workshop.
- [ ] Admin can assign roles (admin/operator/viewer) during invitation or after acceptance.
- [ ] Admin can remove team members. Removed members lose access immediately.
- [ ] Edge case: invited user already has an account — they are prompted to link the workshop to their existing account.

### 3.3 Email Notifications ✅

**Problem:** No email for job completion, compliance pass/fail, or digests — no engagement loop exists.

- As a workshop operator, I want to receive an email when my assessment is complete so that I don't have to keep polling the page.
- As a fleet manager, I want a daily digest email showing all assessments completed that day so that I can track team productivity.
- [x] Email notifications for: assessment complete, assessment failed, API key expiring, team invitation, payment receipt, portal invite.
- [ ] Daily digest email (opt-in) summarizes all assessments completed in the last 24 hours.
- [x] Email preferences are configurable in Settings (which events trigger email, digest opt-in).
- [x] Emails are sent via a configurable SMTP backend (SendGrid, SES, or custom SMTP via aiosmtplib).
- [x] Edge case: email delivery fails — log the failure and show a warning badge in Settings.

### 3.4 Usage Quotas & Metering ✅

**Problem:** Only `daily_intake_limit` exists. No monthly quota, no overage tracking, no API call counting — cannot enforce limits.

- As a platform operator, I want to track monthly usage across assessments, API calls, storage, and images so that I can enforce tier limits.
- As a workshop owner, I want to see my current billing period usage so that I can avoid overage charges.
- [x] Metering tracks: assessments completed, API calls, storage bytes, images uploaded, recommendations generated.
- [x] Usage counters reset monthly on the billing anniversary date.
- [ ] At 80% and 100% of tier limit, a warning toast appears in the UI and a warning email is sent.
- [x] When limit is exceeded, assessment creation is blocked with a clear upgrade prompt.
- [x] Edge case: Enterprise tier has no hard limits but reports usage for informational purposes.

### 3.5 White-Labeling ✅

**Problem:** No custom logo, brand colors, or domain per workshop — cannot resell to fleets.

- As a fleet operator, I want to rebrand RetroMind AI with my company's logo and colors so that my customers see my brand.
- [x] Workshop admins can upload a custom logo (PNG/SVG, max 2MB) in Settings.
- [x] Primary and secondary brand colors are configurable via a color picker (`/api/v1/workshop/branding`).
- [ ] A custom domain (e.g., assessments.myfleet.com) can be configured with automatic TLS via Caddy.
- [x] The default "RetroMind AI" branding is replaced throughout the UI (header, emails, reports).
- [x] Edge case: logo upload fails due to format — show validation error with supported formats.

### 3.6 Customer Portal ✅

**Problem:** No way for vehicle owners to track progress or approve recommendations — missed B2B2C channel.

- As a vehicle owner, I want to see the status of my vehicle's retrofit assessment so that I can track progress without calling the workshop.
- As a workshop owner, I want to share a branded customer portal link with my clients so that they can approve recommendations digitally.
- [x] Each assessment generates a unique customer portal link (`POST /api/v1/intake/{id}/portal`).
- [x] Portal shows: vehicle details, current status, feasibility score, key findings (non-technical), recommendation summary, and an approval button.
- [x] Customer can approve or request changes to the recommendation. Changes request triggers a notification to the workshop (`POST /api/v1/portal/{token}/respond`).
- [x] Portal is mobile-responsive and requires no login (token-based access via the unique link).
- [ ] Edge case: customer does not respond for 7 days — a reminder email is sent automatically.

### 3.7 PDF Report Export ✅

**Problem:** The 13-section report is JSON-only. There is no downloadable PDF with charts, making workshops unable to print reports.

- As a workshop operator, I want to download a PDF version of the compliance report so that I can print it for the customer.
- [x] PDF report includes all sections of the compliance report with proper formatting (WeasyPrint HTML → PDF).
- [x] Charts and visualizations (feasibility gauge, risk breakdown) are rendered as embedded images in the PDF.
- [x] Workshop logo and branding are applied to the PDF header (logo embedded as `data:` URI).
- [x] PDF generation happens synchronously via `POST /api/v1/reports/{intake_id}/export-pdf` returning `StreamingResponse`.
- [x] Edge case: PDF generation — uses dedicated renderers for all 14 section types.

### 3.8 Batch Operations ✅

**Problem:** Cannot start 10 assessments at once for a mini-fleet, which slows fleet business.

- As a fleet operator, I want to upload photos for multiple vehicles at once so that I can assess an entire mini-fleet in one session.
- [x] Batch upload accepts a ZIP file containing folders per vehicle (`POST /api/v1/batch/intake`).
- [x] The system creates N assessments in parallel and reports progress as a batch summary dashboard (`/batch` page).
- [x] Batch summary shows: total submitted, completed, failed, average feasibility score (`GET /api/v1/batch/{id}`).
- [x] Individual assessment results are still accessible from the History page.
- [x] Edge case: some images in a batch fail validation — those vehicles are marked as failed with specific error, others continue.

### 3.9 Mobile Field Capture ✅

**Problem:** No PWA or mobile app for mechanics to capture photos in the workshop, creating friction in the capture workflow.

- As a workshop mechanic, I want to capture vehicle photos using my phone camera directly in the RetroMind app so that I don't need a separate camera.
- [x] A mobile-responsive camera capture UI (`/capture`) guides the user through 6 required views with an overlay.
- [x] Photos are captured using the native Camera API (MediaDevices.getUserMedia) and uploaded immediately.
- [x] The capture flow works offline: photos are stored in IndexedDB and uploaded when connectivity is restored.
- [x] A PWA manifest and service worker enable "Add to Home Screen" on Android and iOS.
- [x] Edge case: camera access denied — show a file upload fallback option.

---

## 4. Frontend / UX

### 4.1 Internationalization (i18n) 📋

**Problem:** No Hindi/Tamil/Bengali support for the Indian market, limiting Tier 2/3 adoption.

- As a Hindi-speaking workshop operator, I want the UI in Hindi so that I can use RetroMind AI comfortably.
- [ ] The frontend uses next-intl for internationalization with locale detection from browser settings.
- [ ] Initial supported locales: `en` (English), `hi` (Hindi), `ta` (Tamil), `bn` (Bengali), `te` (Telugu), `kn` (Kannada).
- [ ] Locale selection is persisted in user preferences and can be changed via a language picker in the header.
- [ ] All user-facing strings are externalized to locale JSON files. No hardcoded UI strings remain.
- [ ] Edge case: a string is missing for the current locale — fall back to English with a console warning.

### 4.2 PWA / Offline Support ✅

**Problem:** No service worker, no install prompt, no offline caching — won't work in low-connectivity workshops.

- As a workshop operator in a rural area with poor internet, I want to use RetroMind AI offline so that my work is not blocked by connectivity.
- [x] A service worker caches the app shell (`_next/` static assets) for offline access.
- [ ] The assessment history page works offline using IndexedDB-cached data.
- [x] Photo captures are queued in IndexedDB and synced when connectivity returns.
- [x] A connectivity indicator in the header shows online/offline status and pending sync count.
- [x] The "Add to Home Screen" install prompt is shown to returning visitors on mobile.
- [x] Edge case: user is offline and tries to start a new assessment — UI shows "Photos will be uploaded when connected" with a local-only intake form.

### 4.3 Accessibility (a11y) 📋

**Problem:** No WCAG compliance, screen reader, or keyboard navigation audit — legal risk.

- As a visually impaired user, I want screen reader support so that I can use RetroMind AI with my assistive technology.
- [ ] Full WCAG 2.1 AA compliance is targeted.
- [ ] All interactive elements have accessible labels and roles.
- [ ] Keyboard navigation works for all primary workflows (upload, assessment review, settings).
- [ ] Color contrast meets WCAG AA standards (4.5:1 for normal text, 3:1 for large text).
- [ ] Focus indicators are visible and logical.
- [ ] An a11y audit report is generated as part of CI.
- [ ] Edge case: custom-branded colors may reduce contrast — an automated check warns admins if their brand colors fail contrast requirements.

### 4.4 Skeleton Loading States 📋

**Problem:** Most pages (history, analytics, settings) lack loading skeletons, creating bad UX during loading.

- As a workshop operator, I want to see skeleton placeholders while pages load so that I know content is coming and the page isn't empty.
- [ ] Every page that fetches data has a skeleton loading state that matches the page layout.
- [ ] Skeletons use a subtle shimmer animation.
- [ ] Skeletons are shown immediately on navigation, not after a delay.
- [ ] Error states (if data fails to load) are visually distinct from skeletons.
- [ ] Edge case: data loads very quickly (<200ms) — skeleton is still shown briefly to prevent layout shift.

### 4.5 Error Boundaries ✅

**Problem:** `ErrorBoundary.tsx` exists but many pages don't wrap content in it — a crash can blank the entire page.

- [x] Every page route wraps its content in an ErrorBoundary with a page-level fallback UI.
- [x] The ErrorBoundary fallback includes: an error message, a "Try Again" button, and a "Contact Support" link.
- [x] Error details are logged to Sentry for debugging.
- [x] The Header and AppShell remain visible even when a page-level error boundary catches an error.
- [x] Edge case: the error boundary itself crashes — a top-level error boundary catches it and shows a minimal "Something went wrong" fallback.

---

## 5. DevOps

### 5.1 CI/CD Secrets 📋

**Problem:** Deploy workflow fails because `ORACLE_HOST/USER/SSH_KEY` aren't set in GitHub Secrets — can't deploy.

- [ ] All required secrets are documented in a `.github/secrets-template.md` file.
- [ ] A CI workflow validates that all required secrets are present before attempting deploy. If missing, the workflow fails with a clear message listing which secrets are absent.
- [ ] Secrets are organized by environment (dev/staging/prod) with clear naming conventions.
- [ ] A `check-secrets` job runs before the `deploy` job and fails fast if secrets are missing.

### 5.2 Dependency Vulnerability Scanning 📋

**Problem:** No pip audit, npm audit, or Dependabot — supply chain risk is unmanaged.

- [ ] `pip-audit` runs in CI for Python dependencies on every PR and push to main.
- [ ] `npm audit` runs in CI for JavaScript dependencies on every PR and push to main.
- [ ] Dependabot is enabled for the repository with weekly checks for both pip and npm.
- [ ] Critical vulnerabilities block the CI pipeline. High/moderate vulnerabilities generate warnings.
- [ ] A monthly dependency update PR is auto-generated to keep dependencies current.

### 5.3 Database Migration CI

**Problem:** No `alembic upgrade head` step runs on a test database during CI — migrations may break in production.

- [ ] CI runs `alembic upgrade head` against a fresh PostgreSQL 16 test container before any test execution.
- [ ] If migrations fail, the CI pipeline stops immediately with the migration error output.
- [ ] A migration rollback test (`alembic downgrade -1`) is also run to verify reversibility.
- [ ] Migration files are linted for common issues (nullable columns on new tables, missing downgrade).

### 5.4 Container Image Signing / CVE Scanning

**Problem:** Container images are built but not scanned or signed — security risk.

- [ ] Container images are scanned with Trivy (or Grype) during CI build. Critical CVEs block the build.
- [ ] Images are signed using cosign with a keyless signing approach (OIDC-based via GitHub OIDC token).
- [ ] Signed images are stored in a container registry with attestation.
- [ ] A nightly scan re-scans the currently deployed images and alerts on new CVEs.
- [ ] Edge case: signing fails — the build continues with a warning (signing is non-blocking).

---

## Non-Goals (Enterprise Phase)

- Custom SLA contracts with per-customer uptime guarantees (requires multi-region infra).
- On-premise deployment option (requires private registry, air-gapped install scripts).
- PCI DSS compliance (no credit card data stored — Stripe handles payments).
- FedRAMP / IL4+ certification (deferred — requires dedicated infrastructure).
- Real-time multi-user collaboration in the digital twin (deferred to v3).
