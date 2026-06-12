# RetroMindAI — Pitch Presentation
## AI-Powered Vehicle Retrofitting Intelligence Platform

---

## Slide 1 — Title Slide

**RetroMindAI**
*Intelligence for the Retrofit Revolution*

AI-native SaaS platform for automotive retrofitting assessment, compliance verification, and workshop intelligence.

---

## Slide 2 — The Problem

**The Global Retrofitting Bottleneck**

- 1.4 billion ICE vehicles on the road — only a fraction will ever be retrofitted
- Each retrofit requires 20–40 hours of manual assessment by certified engineers
- Compliance standards (AIS-123, ECE R100, FMVSS) are complex and vary by jurisdiction
- Workshops operate blind: no standardized diagnostics, no institutional memory, no scalability
- Result: retrofit costs remain high (₹4L–₹12L+), throughput is capped at ~2–3 vehicles/week/workshop

**The gap is not technology — it's intelligence.**

---

## Slide 3 — The Solution

**RetroMindAI: An AI Co-Pilot for Retrofit Workshops**

An end-to-end AI-native platform that ingests vehicle photos, analyzes structural and electrical systems against regulatory standards, and produces a comprehensive compliance report — in under 15 minutes.

**Core value:** Turn a 20–40 hour manual process into a 15-minute AI-assisted workflow.

---

## Slide 4 — How It Works

**1. Capture** — Upload standardised vehicle photos (mobile or batch ZIP)
**2. Analyze** — AI pipeline: image quality → vehicle classification → component detection → deviation analysis → compliance scoring
**3. Report** — Instant assessment with confidence metrics, feasibility score, cost estimation, compliance state
**4. Act** — Share with customers via portal, export PDF/CAD, compare across assessments

---

## Slide 5 — Live Demonstration

**See RetroMindAI in action — end to end**

### Walkthrough

1. **Upload** — Open the dashboard, upload vehicle photos (single or batch ZIP)
2. **Process** — Watch the AI pipeline run in real time (image quality → classification → deviation → compliance → cost)
3. **Report** — Review the generated compliance report: confidence scores, feasibility, risk state, cost estimates
4. **Export** — Download the PDF report, share with the customer via portal link
5. **Compare** — Side-by-side comparison of two assessments with diff highlighting
6. **Batch** — Process 10+ vehicles in parallel from a single ZIP upload

### Pointers for the Presenter

| Stop | What to Show | Key Talking Point |
|------|-------------|-------------------|
| Dashboard | Assessment list, stats cards | "Everything starts from this single view" |
| New assessment | Photo upload form | "Standard phone photos — no special equipment" |
| Processing | Loading state → results page | "Under 15 minutes, usually under 5" |
| Results | Compliance table, deviation list, confidence bars | "Each component scored against AIS-123" |
| PDF export | Generated PDF | "This replaces a 20-page manual report" |
| Customer portal | Share link → customer view with approve/reject | "Customer can review and approve from their phone" |
| Comparison | 2 assessments side by side | "Spot the difference instantly" |
| Batch | ZIP upload → progress dashboard | "Scale from 1 to 500 vehicles" |

**Duration:** 5–7 minutes

---

## Slide 6 — Product Overview

| Layer | Capability |
|-------|-----------|
| **Capture** | Photo ingestion, ZIP batch processing (5–500+ vehicles), quality validation |
| **AI Engine** | CNN classifier, deviation detection, compliance verification, feasibility scoring, battery placement optimisation (Optuna), RL adaptive recommendations |
| **Compliance** | AIS-123 adherence, system-level risk states, per-component compliance, salvage potential |
| **Digital Twin** | 3D model generation (STEP/STL export), FreeCAD integration, retro-DNA matching |
| **Costing** | Real-time INR estimation (low/mid/high ranges), tooling & skills requirements |
| **Sharing** | Customer portal with approve/reject workflow, JWT-secured links |
| **Workshop OS** | Multi-workshop, RBAC (admin/operator/viewer), branding, API keys |

---

## Slide 7 — AI Engine Deep Dive

**Multi-Stage Inference Pipeline**

1. **Image Quality Check** — Lighting, blur, obstruction detection; confidence scoring
2. **Vehicle Classification** — Make, model, year, variant identification
3. **Component Detection** — Battery tray, motor mount, controller, cabling, cooling — deviation from OEM baseline
4. **Feasibility Scoring** — Component-level and system-level feasibility with certainty metrics
5. **Compliance State** — Each component rated: Compliant / Non-Compliant / NeedsReview
6. **System Risk** — Aggregated risk state: Safe / Warning / Critical
7. **Cost Estimation** — ML model trained on actual retrofit data (INR low/mid/high)

**Optimisation Layer:**
- Optuna hyperparameter tuning on live data
- PyTorch CNN classifier (fine-tuned on retrofit datasets)
- RLlib reinforcement learning for adaptive recommendation improvement
- Generative AI for assessment refinement

---

## Slide 8 — Platform Features (Full Catalogue)

### Assessment & Intelligence
- Single-vehicle assessment with full compliance report
- Batch processing: ZIP upload, parallel processing, real-time dashboard
- Side-by-side comparison (2–6 vehicles): diff highlighting, risk comparison
- Assessment history with full-text search and filters
- PDF export: comprehensive compliance report with all sections
- CAD export: 3D model generation (STEP/STL)
- Data export: full workshop JSON download

### Workshop Management
- Multi-workshop support with workspace switcher
- Role-based access: Admin, Operator, Viewer
- Custom branding: logo, colors, custom domain
- API key management: generation, renewal, breach detection, IP allowlisting
- Feature flags: toggle Optuna, PyTorch, RLlib, GenAI, CAD export per workshop

### Customer Engagement
- Customer portal: JWT-secured assessment sharing
- Customer respond: approve/reject with feedback capture
- Portal session tracking with automatic expiry

### Collaboration
- Team invitations with role assignment
- Member management and role modification
- SSO/OAuth: Google & Azure AD integration

### Business Operations
- Stripe subscription billing (monthly/yearly)
- Usage metering and tracking
- Automated payment receipts
- Daily digest emails

### Monitoring & Administration
- Prometheus metrics (HTTP, jobs, assessment counts)
- Analytics dashboard: monthly trends, confidence, deviations, pass rates
- Admin dashboard: system-wide metrics, user/workshop management
- Audit logging with event-driven capture, filtering, and retention
- Email notification preferences (7 event types)

---

## Slide 9 — Business Model

**SaaS Subscription — Tiered Pricing**

| Tier | Price (Monthly) | Price (Yearly) | Max Users | Max Assessments/Month | Storage | Rate Limit |
|------|----------------|----------------|-----------|----------------------|---------|------------|
| Free | ₹0 | ₹0 | 1 | 10 | 100 MB | 100/min |
| Standard | ₹8,200 | ₹83,000 | 3 | 100 | 5 GB | 500/min |
| Pro | ₹25,000 | ₹2.5L | 10 | 500 | 25 GB | 500/min |
| Enterprise | Custom | Custom | Unlimited | Unlimited | Unlimited | 5000/min |

**Revenue Streams:**
- SaaS subscription fees (recurring, predictable)
- Per-assessment overage pricing (usage metering)
- Enterprise contracts with on-prem deployment option
- CAD export add-on (premium feature)
- White-label / OEM licensing for manufacturers

**Target ICP:** Independent retrofit workshops (50K+ globally), fleet operators, OEM retrofit divisions, government e-mobility programs

---

## Slide 10 — Economic Impact

### Workshop Economics

| Metric | Without RetroMindAI | With RetroMindAI | Impact |
|--------|-------------------|-----------------|--------|
| Assessment time | 20–40 hours | 15 minutes | **98% faster** |
| Throughput | 2–3 cars/week | 20–40 cars/week | **10x–15x more** |
| Cost per assessment | ₹17K–42K | ~₹170–420 (compute) | **99% cost reduction** |
| Engineer skill required | Certified specialist | Junior technician | **Broader talent pool** |
| Compliance confidence | Variable | Standardised + audited | **Reduced liability** |

### Macro Impact (at scale)
- **100 workshops × 500 vehicles/year** = 50,000 additional retrofits annually
- Each retrofit saves ~4 tons CO₂/year → **200,000 tons CO₂ saved per year**
- Supports **50K+ new green jobs** in the retrofit ecosystem

---

## Slide 11 — Market Opportunity

### The Retrofit Addressable Market

| Segment | Size | CAGR |
|---------|------|------|
| Global automotive retrofit market | ₹2.3L Cr (2025) | 22.4% |
| EV conversion kits & services | ₹71K Cr (2025) | 35% |
| Fleet electrification services | ₹1.25L Cr (2025) | 28% |
| Commercial vehicle retrofitting | ₹50K Cr (2025) | 18% |

**TAM (2030):** ~₹7L Cr | **SAM (Workshop SaaS):** ₹21K Cr | **Target (Year 5):** ₹415 Cr ARR

**Key Drivers:**
- India: 30M+ commercial ICE vehicles targeted for EV conversion by 2030 (govt policy)
- EU: ICE ban 2035 driving retrofit innovation exemptions
- Africa & SEA: Used ICE vehicle imports + growing EV conversion demand
- US: Inflation Reduction Act incentives for fleet electrification

---

## Slide 12 — Technology Architecture

```
┌─────────────┐    ┌──────────────┐    ┌────────────────┐
│  Frontend   │    │   API Layer  │    │  AI Pipeline   │
│  Next.js    │◄──►│  FastAPI     │◄──►│  RQ Workers    │
│  TypeScript │    │  PostgreSQL  │    │  PyTorch/ONNX  │
│  Tailwind   │    │  Redis       │    │  OpenCV        │
└─────────────┘    │  MinIO S3    │    │  Optuna        │
                   └──────┬───────┘    │  RLlib         │
                          │            └────────────────┘
                          │
                   ┌──────▼───────┐    ┌────────────────┐
                   │  Integrations│    │  Infrastructure│
                   │  Stripe      │    │  Docker Swarm  │
                   │  SMTP        │    │  Prometheus    │
                   │  Google/Azure│    │  Grafana       │
                   │  SSO         │    │  Caddy (TLS)   │
                   │  FreeCAD     │    │  PostgreSQL    │
                   └──────────────┘    └────────────────┘
```

**Key architectural decisions:**
- Async worker queue (Redis RQ) for non-blocking AI inference
- Tier-based rate limiting (slowapi) with automatic breach detection
- JWT-secured customer portal (zero additional auth infra)
- Event-driven audit logging with configurable retention
- Feature flags enable gradual roll-out of premium capabilities

---

## Slide 13 — Security & Compliance

- **API Security:** SHA-256 hashed keys, prefix `rm_` + 20 hex, 90-day auto-expiry
- **Breach Detection:** Auto-revokes if >3 distinct IPs in 5-minute window
- **IP Allowlisting:** Restrict API access to trusted networks
- **RBAC:** Admin / Operator / Viewer with hierarchical permissions
- **Audit:** Full SQLAlchemy event-driven logging — every create/update tracked
- **Data Encryption:** At rest (PostgreSQL TDE) and in transit (TLS via Caddy)
- **SSO:** Google and Azure AD — no password storage
- **Compliance Reports:** Digitally signed, tamper-evident export format

---

## Slide 14 — Competitive Landscape

| Competitor | Approach | Limitations vs RetroMindAI |
|-----------|----------|---------------------------|
| Traditional engineering firms | Manual assessment | Slow, expensive, not scalable |
| Basic EV conversion calculators | Spreadsheet/rule-based | No vision AI, no compliance, no reporting |
| Generic computer vision tools | Off-the-shelf CV models | No vehicle-specific training, no compliance rules |
| In-house workshop tools | Custom-built by each shop | No shared intelligence, no continuous improvement |

**RetroMindAI Differentiators:**
- End-to-end: photo → compliance report (no manual steps)
- Continuous learning: RL feedback loop improves with every assessment
- Multi-workshop intelligence: cross-shop data (privacy-preserving) improves models
- Regulatory-ready: compliance rules engine built for AIS-123 and extensible to ECE, FMVSS
- Not a tool — a platform: billing, portal, team management, analytics, monitoring

---

## Slide 15 — Traction & Validation

- **Workshops onboarded:** N workshops in pilot program
- **Assessments processed:** N+ across N vehicle models
- **Batch capability validated:** N-vehicle batch in under N minutes
- **Compliance accuracy:** N% agreement with certified assessors
- **Customer portal approved:** N% customer approval rate (pilot)
- **Patent status:** N filed / granted (AI compliance assessment methodology)

*(Metrics populated from live deployment data)*

---

## Slide 16 — Development Roadmap

### Phase 1 — Core Platform (Current) ✅
- Single assessment pipeline
- Multi-workshop with RBAC
- PDF export and customer portal
- Stripe billing integration
- Analytics & monitoring

### Phase 2 — Scale & Premium (Q3 2025)
- Batch processing (done)
- SSO/OAuth (done)
- Comparison engine (done)
- CAD export (done)
- Advanced analytics

### Phase 3 — Ecosystem (Q1 2026)
- OEM data marketplace
- Mobile assessment app (iOS/Android)
- Independent assessor certification program
- API marketplace for third-party tools
- Fleet-wide analytics and predictive maintenance

### Phase 4 — Autonomous (2027)
- Fully autonomous assessment (no human review for standard cases)
- Regulatory filing automation
- Real-time OBD-II integration for post-retrofit validation
- Global compliance engine (EU, US, ASEAN, Africa)

---

## Slide 17 — Investment Thesis

**Why invest in RetroMindAI?**

1. **Timing:** The retrofit wave is real and accelerating — ICE bans, fleet electrification mandates, and falling conversion costs create a massive pull market
2. **Defensibility:** Regulatory compliance is the hardest moat — our AI learns regulations faster than any competitor
3. **Network Effects:** Every workshop improves our models; every assessment strengthens our compliance database
4. **Capital Efficiency:** SaaS model with predictable revenue; compute-heavy but marginal cost per assessment is ~₹170–420
5. **Mission-Aligned:** Directly reduces CO₂ emissions, extends vehicle life, and democratises EV conversion — ESG-friendly investment

---

## Slide 18 — Use of Funds

| Area | Allocation |
|------|-----------|
| AI R&D (model improvement, new compliance rules) | 35% |
| Go-to-market (sales, workshops outreach, onboarding) | 30% |
| Engineering (mobile app, API marketplace, scaling) | 20% |
| Regulatory & certification (global compliance expansion) | 10% |
| Operations & admin | 5% |

**Target Raise:** ₹16.6 Cr Seed Round (18-month runway)

**Key Milestones:**
- Month 6: 100 paid workshops | Month 12: 500 paid workshops | Month 18: 2,000 paid workshops
- ARR progression: ₹1 Cr → ₹5 Cr → ₹20 Cr

---

## Slide 19 — Team

*(To be populated)*

- **Founder(s):** Background in automotive engineering / AI / SaaS
- **Key Advisors:** EV retrofit industry veterans, compliance experts
- **Engineering:** Full-stack, AI/ML, DevOps capabilities demonstrated in current platform

---

## Slide 20 — Closing

**RetroMindAI — Intelligence for the Retrofit Revolution**

The world's 1.4 billion ICE vehicles will not all be replaced. They must be converted. RetroMindAI gives every workshop the intelligence to do it safely, compliantly, and at scale.

**Let's build the retrofit intelligence layer for the planet.**

---

## Slide 21 — Contact

**RetroMindAI**
Website: retromind.ai
Email: hello@retromind.ai

*"Making every vehicle retrofittable."*

---

## Slide 22 — Appendix: Acronyms & Glossary

| Acronym | Full Meaning |
|---------|-------------|
| AI | Artificial Intelligence |
| AIS-123 | Automotive Industry Standard 123 (EV Retrofit Compliance) |
| API | Application Programming Interface |
| ARR | Annual Recurring Revenue |
| ASEAN | Association of Southeast Asian Nations |
| CAD | Computer-Aided Design |
| CAGR | Compound Annual Growth Rate |
| CNN | Convolutional Neural Network |
| ECE R100 | Economic Commission for Europe Regulation 100 |
| ESG | Environmental, Social, and Governance |
| EU | European Union |
| EV | Electric Vehicle |
| FMVSS | Federal Motor Vehicle Safety Standards |
| GenAI | Generative Artificial Intelligence |
| ICE | Internal Combustion Engine |
| ICP | Ideal Customer Profile |
| INR | Indian Rupee |
| IP | Internet Protocol |
| JWT | JSON Web Token |
| ML | Machine Learning |
| OBD-II | On-Board Diagnostics II |
| OEM | Original Equipment Manufacturer |
| OAuth | Open Authorization |
| ONNX | Open Neural Network Exchange |
| Optuna | Hyperparameter Optimization Framework |
| PDF | Portable Document Format |
| RBAC | Role-Based Access Control |
| RL | Reinforcement Learning |
| RLlib | Reinforcement Learning Library (Ray) |
| RQ | Redis Queue |
| SaaS | Software as a Service |
| SAM | Serviceable Addressable Market |
| SHA-256 | Secure Hash Algorithm 256-bit |
| SMTP | Simple Mail Transfer Protocol |
| SSO | Single Sign-On |
| STEP | Standard for the Exchange of Product Data |
| STL | Stereolithography (3D mesh format) |
| TAM | Total Addressable Market |
| TDE | Transparent Data Encryption |
| TLS | Transport Layer Security |

---

*This presentation is prepared for investor and jury evaluation. All metrics, market data, and projections are based on current analysis and subject to change as the platform matures.*
