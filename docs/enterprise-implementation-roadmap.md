# RetroMind AI — Enterprise Implementation Roadmap

**30 features across 5 domains, organized into 8 phases.**

---

## Phase E1 — Foundation & Security Hardening
**Effort:** ~2 weeks | **Risk:** Low | **Dependencies:** None (all existing code)

### Features
| # | Feature | Domain | Effort | Key Files | Status |
|---|---------|--------|:------:|-----------|--------|
| 1 | **RBAC within workshop** | Security | 3d | `backend/core/rbac.py`, migration 011, endpoint guards | |
| 2 | **API key rotation policy** | Security | 2d | `core/auth.py`, expiry check middleware, breach detection | ✅ |
| 3 | **Data encryption at rest** | Security | 3d | `core/crypto.py`, S3 encrypt/decrypt, EncryptedType columns | |
| 4 | **Rate limiting per tier** | Security | 2d | `core/limiter.py`, tier-aware key function, headers | ✅ |
| 5 | **CI/CD secrets validation** | DevOps | 1d | `.github/workflows/ci.yml` secrets-check job | |

**Acceptance:** RBAC enforced on all API endpoints. API keys auto-expire after configurable period. All uploaded images encrypted. Rate limits differ by tier. CI fails fast if secrets missing.

**Phase E1 Total: ~11 days**

---

## Phase E2 — Observability & Reliability
**Effort:** ~2 weeks | **Risk:** Low-Medium | **Dependencies:** E1 (infrastructure hardening)

### Features
| # | Feature | Domain | Effort | Key Files | Status |
|---|---------|--------|:------:|-----------|--------|
| 6 | **Deep health checks** | Observability | 2d | `backend/api/v1/endpoints/health.py`, model + queue checks | ✅ |
| 7 | **Structured JSON logging** | Observability | 2d | `backend/core/logging.py`, structlog, correlation ID middleware | |
| 8 | **Distributed tracing** | Observability | 3d | OpenTelemetry auto-instrumentation, span per stage | |
| 9 | **Circuit breakers** | Observability | 3d | `backend/core/circuit_breaker.py`, wrap 4 services | |
| 10 | **Alerting** | Observability | 2d | Prometheus rules, Grafana dashboard, alert webhooks | |
| 11 | **Dependency vulnerability scanning** | DevOps | 1d | pip-audit, npm audit, Dependabot config | ✅ |

**Acceptance:** `/health` checks every dependency. All logs are structured JSON with correlation IDs. Traces flow API→Worker→DB. Circuit breakers prevent cascade failures. Alerts fire on error rate/latency/queue thresholds. CI scans for vulnerabilities.

**Phase E2 Total: ~13 days**

---

## Phase E3 — Multi-Tenancy Core
**Effort:** ~3 weeks | **Risk:** Medium | **Dependencies:** E1 (RBAC foundation)

### Features
| # | Feature | Domain | Effort | Key Files | Status |
|---|---------|--------|:------:|-----------|--------|
| 12 | **Subscription tiers** | Business | 5d | `backend/api/v1/endpoints/billing.py`, Stripe integration, plan enforcement | |
| 13 | **Team management** | Business | 3d | Invitation flow, workspace roles UI, member management API | |
| 14 | **Usage quotas & metering** | Business | 3d | `usage_metering` table, middleware enforcement, usage dashboard | |
| 15 | **OAuth / SSO** | Security | 4d | Google OIDC, Azure AD OIDC, auth endpoints | ✅ |

**Acceptance:** Google/Azure login works end-to-end. Workshops can subscribe, upgrade, downgrade. Admins can invite/remove team members. Usage is tracked per metric and enforced at API layer.

**Phase E3 Total: ~15 days (1/4 complete — SSO shipped; subscriptions, team mgmt, usage metering deferred)**

---

## Phase E4 — Business Features
**Effort:** ~3 weeks | **Risk:** Medium | **Dependencies:** E3 (subscription + team foundation)

### Features
| # | Feature | Domain | Effort | Key Files | Status |
|---|---------|--------|:------:|-----------|--------|
| 16 | **Email notifications** | Business | 3d | `infrastructure/email/`, template rendering, preference management | ✅ |
| 17 | **Customer portal** | Business | 4d | Token-based portal page, approval flow, email reminders | ✅ |
| 18 | **PDF report export** | Business | 4d | Playwright/WeasyPrint worker, S3 storage, email download link | ✅ |
| 19 | **Audit trail depth** | Security | 3d | `audit_events` table, SQLAlchemy event listeners, admin audit UI | ✅ |

**Acceptance:** Emails sent for key events with user-configurable preferences. Vehicle owners can view/approve assessments via portal. PDF reports include all 13 sections with branding. Audit trail captures before/after state on all mutations.

**Phase E4 Total: ~14 days (4/4 features complete)**

---

## Phase E5 — Advanced Business Features
**Effort:** ~2 weeks | **Risk:** Medium | **Dependencies:** E3 (subscription foundation)

### Features
| # | Feature | Domain | Effort | Key Files | Status |
|---|---------|--------|:------:|-----------|--------|
| 20 | **White-labeling** | Business | 3d | Branding JSONB, CSS custom properties, custom domain TLS | ✅ |
| 21 | **Batch operations** | Business | 3d | ZIP upload, parallel intake creation, batch dashboard | ✅ |
| 22 | **Mobile field capture** | Business | 4d | Camera capture UI, offline IndexedDB storage, background sync | ✅ |

**Acceptance:** Fleets can brand the platform. 10-vehicle batch upload works end-to-end. Mechanics capture photos via phone camera with offline support.

**Phase E5 Total: ~10 days (3/3 features complete)**

---

## Phase E6 — Backup & DR
**Effort:** ~1 week | **Risk:** Low | **Dependencies:** None

### Features
| # | Feature | Domain | Effort | Key Files |
|---|---------|--------|:------:|-----------|
| 23 | **Backup & DR** | Observability | 3d | `infra/backup/` scripts, S3 upload, restore documentation |
| 24 | **Database migration CI** | DevOps | 1d | `alembic upgrade head` in CI, downgrade test |
| 25 | **Container image signing / CVE scanning** | DevOps | 2d | Trivy in CI, cosign signing, nightly rescan |

**Acceptance:** Automated daily backups of PostgreSQL and Neo4j. Migration CI prevents broken migrations. Container images are signed and CVE-scanned.

**Phase E6 Total: ~6 days**

---

## Phase E7 — Frontend/UX Overhaul
**Effort:** ~3 weeks | **Risk:** Low-Medium | **Dependencies:** E3 (for i18n of subscription/team flows)

### Features
| # | Feature | Domain | Effort | Key Files |
|---|---------|--------|:------:|-----------|
| 26 | **Internationalization (i18n)** | Frontend | 5d | next-intl, locale files, LanguagePicker, CI check |
| 27 | **PWA / offline support** | Frontend | 5d | Service worker, manifest, IndexedDB cache, sync |
| 28 | **Accessibility (a11y)** | Frontend | 4d | WCAG audit, keyboard nav, screen reader, CI check |
| 29 | **Skeleton loading states** | Frontend | 2d | Skeleton components for every page |
| 30 | **Error boundaries** | Frontend | 1d | Per-page ErrorBoundary wrapping |

**Acceptance:** UI available in 6 Indian languages. App works offline for history and photo capture. WCAG 2.1 AA compliance. No blank pages on crash — error boundaries everywhere.

**Phase E7 Total: ~17 days**

---

## Phase E8 — Polish & Hardening
**Effort:** ~1 week | **Risk:** Low | **Dependencies:** All prior phases

### Focus
- End-to-end integration testing for all enterprise features.
- Load testing with Locust at tier boundaries (100/500/5000 rpm).
- Documentation: ops runbook, disaster recovery procedure, SSO setup guide.
- Penetration testing: OWASP Top 10, API key breach detection validation.
- Performance audit: verify PWA load times, PDF generation latency, batch throughput.

**Phase E8 Total: ~5 days**

---

## Summary

| Phase | Focus | Features | Effort | Status |
|-------|-------|:--------:|:------:|:------:|
| E1 | Security Hardening | 5 | ~11d | 2/5 |
| E2 | Observability & Reliability | 6 | ~13d | 2/6 |
| E3 | Multi-Tenancy Core | 4 | ~15d | 1/4 |
| E4 | Business Features | 4 | ~14d | ✅ |
| E5 | Advanced Business | 3 | ~10d | ✅ |
| E6 | Backup & DR | 3 | ~6d | |
| E7 | Frontend/UX Overhaul | 5 | ~17d | |
| E8 | Polish & Hardening | — | ~5d | |
| **Total** | | **30** | **~91 days (~4.5 months)** | **13/30 shipped** |

### Parallelization Strategy

Phases E1 and E6 have no frontend dependencies and can run alongside frontend phases.
- **Track A (Backend-heavy):** E1 → E2 → E3 → E4 → E5
- **Track B (Frontend-heavy):** E7 (starts after E3 for i18n strings)
- **Track C (Infra):** E6 (can start anytime)
- **Convergence:** E8 (everything must be integrated)

### Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|:----------:|:------:|------------|
| Stripe integration complexity | Medium | High | Use Stripe Checkout (hosted page) for initial launch; custom portal later |
| SAML integration per-customer variance | Medium | Medium | Build generic SAML 2.0 adapter; custom mapping per customer as config |
| PWA offline sync conflicts | Low | Medium | CRDT-based conflict resolution for photo sync; last-write-wins for history |
| i18n maintenance burden | High | Low | CI checks for missing keys; translation management platform (Crowdin/Lokalise) |
| PDF rendering inconsistency | Medium | Medium | Snapshot testing for PDF output; use Playwright (renders real browser) for fidelity |
| Circuit breaker tuning | Medium | Low | Start conservative (10 failures, 60s timeout); tune from production data |

### Success Criteria

1. Workshop admin can invite 5 team members with different roles.
2. Fleet operator uploads 10 vehicles in one batch → 10 assessments created.
3. Mechanic captures photos on mobile offline → syncs when online.
4. Vehicle owner receives portal link → views and approves recommendation.
5. API key auto-expires → clear error message with renewal flow.
6. `/health` reports PostgreSQL degradation → alert fires within 5 minutes.
7. Neo4j goes down → circuit breaker opens → heuristic fallback activates → assessment continues.
8. All 354 existing tests + new enterprise tests pass in CI.
9. PDF report generated with branding → emailed to workshop operator.
10. UI renders correctly in Hindi, Tamil, Bengali.
