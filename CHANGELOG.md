# Changelog

All notable changes to RetroMind AI are documented here.

## [Unreleased]

### Fixed
- Email notifications: worker now checks preferences before sending, uses correct PUT method, fires only after build result succeeds
- Admin auth: accepts workshop API keys (not just hardcoded `dev-admin-key`), removed duplicate useEffect race
- Knowledge graph sizing: enlarged viewBox (1200×800), increased node radius and physics constants
- Settings renew key: added success card with Copy button for new API key
- Digital twin: fixed float32 serialization crash, fixed `underbody_center` KeyError
- Service worker: only caches `_next/` static assets (no HTML) to prevent stale page + fresh JS mismatch
- Job expiry: completed jobs no longer expire; only failed/timed_out/cancelled expire after 30 min
- Vehicle validation: shows error overlay on invalid vehicle instead of proceeding
- Capture page: auto-starts camera on mount, correct analysis trigger after 3rd view

### Documentation
- enterprise-prd.md: all sections marked with ✅ shipped / 📋 planned status
- enterprise-spec.md: updated with actual implementation details (schemas, endpoints, flows)
- enterprise-implementation-roadmap.md: per-feature status with summary table
- user-guide.md: added enterprise feature walkthroughs (portal, batch, branding, notifications, billing, team)
- spec.md: added enterprise API endpoints section, updated architecture stack and bounded contexts
- README.md: added enterprise features table, updated architecture diagram
- architecture.md: added MailHog, SSO, FreeCAD, Stripe, R2 to topology and connections

## [v1.0.0] — 2026-06-09

### Enterprise Phase E5 — White-Labeling, Batch, Mobile Capture
- White-labeling: branding API (`/workshop/branding`), settings UI with logo upload and color picker, PDF branding
- Batch operations: ZIP upload, parallel intake creation, batch dashboard (`/batch`), per-job tracking
- Mobile field capture: camera UI at `/capture`, 6-view guide overlays, blur detection, offline IndexedDB queue

### Enterprise Phase E4 — Customer Portal, PDF Export, Email
- Customer portal: token-based sharing, approve/reject flow, portal session management
- PDF report export: WeasyPrint HTML→PDF, 14 section renderers, data URI logo embedding
- Email notifications: `email_preferences` table, `PUT /notifications/preferences`, SMTP sender (aiosmtplib)
- Audit trail: before/after state logging for all CREATE/UPDATE/DELETE operations

### Enterprise Phase E3 — Multi-Tenancy, SSO, Billing
- Subscription tiers Free/Pro/Enterprise with Stripe integration (checkout, webhook, customer portal)
- Usage metering: tracks assessments, API calls, storage, images per billing period
- SSO: Google OAuth and Microsoft Azure AD login, auto-provisioning, SAML support
- Team management: invitation system with role assignment (admin/operator/viewer)

### Enterprise Phase E2 — Observability & Reliability
- Health check endpoint (`/health`) with per-dependency status
- Circuit breakers for Neo4j, Redis, OpenAI, Anthropic, object storage
- Prometheus metrics for request rate, error rate, latency, queue depth
- PostgreSQL backup script (`infra/backup/pg_dump.sh`) with S3 upload and retention

### Enterprise Phase E1 — Security Hardening
- RBAC: workshop roles (admin/operator/viewer)
- API key rotation: configurable expiry (default 90 days), breach detection (3+ IPs in 5 min)
- Rate limiting: per-tier configurable limits, `X-RateLimit-*` headers, 429 responses
- Data encryption at rest: AES-256-GCM for uploaded images

### Core
- Digital twin 3D visualization (Three.js/R3F): battery fitment, heat zones, wiring routes, measurement tool, QR export, cutaway, before/after toggle
- CLIP zero-shot vehicle classification
- Confidence engine with weighted scoring and safety overrides
- 13-section compliance report generator
- Alembic migrations (001-019)

## [v0.9.0] — 2026-05-15

### Added
- Frontend: history page, analytics dashboard, settings page
- Assessment pipeline: intake → classification → deviation → feasibility → recommendations → report
- FreeCAD worker for STEP/STL CAD export
- OEM data browser with makes/models/generations/trims
- Demo mode with seed data workshop

### Fixed
- CORS configuration for frontend-backend communication
- API key authentication flow
- SSE event fallback from polling
- Container startup ordering with health checks
