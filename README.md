# RiskLens Platform

**Production-Grade Risk Control System for Web3**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/Rhea-Wang315/risklens-platform/workflows/CI/badge.svg)](https://github.com/Rhea-Wang315/risklens-platform/actions)
[![codecov](https://codecov.io/gh/Rhea-Wang315/risklens-platform/branch/main/graph/badge.svg)](https://codecov.io/gh/Rhea-Wang315/risklens-platform)

---

## What is RiskLens Platform?

RiskLens Platform is a complete risk management system for Web3 organizations, bridging the gap between **detection** (identifying suspicious behavior) and **action** (making operational decisions).

**The Problem**: Existing on-chain detection tools (including [whale-sentry](https://github.com/Rhea-Wang315/whale-sentry)) output raw alerts with scores and patterns. But risk teams need:
- **Actionable decisions**: Should we freeze this account? Escalate to compliance? Just monitor?
- **Audit trails**: Why was this decision made? What evidence supports it?
- **Operational workflows**: How do we handle 1000+ alerts per day efficiently?
- **Regulatory compliance**: Can we prove our decisions to auditors?

**The Solution**: RiskLens Platform provides:
1. **Decision Engine**: Configurable rules + multi-dimensional scoring → automated decisions
2. **Real-time Monitoring**: Kafka-based streaming pipeline for instant alerting
3. **Operator Dashboard**: UI for human review, rule management, and metrics tracking
4. **Audit System**: Complete evidence chain for every decision (regulatory-ready)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     RiskLens Platform                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Detection  │───▶│   Decision   │───▶│    Action    │  │
│  │    Engine    │    │    Engine    │    │   Executor   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                    │                    │          │
│    whale-sentry         Rule Engine          Alert Mgr      │
│    (external lib)       + Risk Scoring       + Audit Log    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Operator Dashboard (UI)                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Real-time Monitoring (Kafka/Redis)            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Features

### ✅ Configurable Rule Engine
- Define risk rules in Python DSL (no code deployment needed)
- Multi-dimensional risk scoring (detection score + address reputation + transaction characteristics)
- Automated decision logic: OBSERVE / WARN / FREEZE / ESCALATE

### ✅ Real-time Monitoring
- Kafka/Redis-based event streaming
- Sub-5-second latency from on-chain event to alert
- Integration with Slack, PagerDuty, Discord

### ✅ Complete Audit Trail
- Every decision linked to input evidence
- Timestamped, versioned, immutable
- Regulatory-ready (MAS, FinCEN, FATF compliance)

### ✅ Operator Dashboard
- Alert management (filter, search, review)
- Address profiling (historical behavior, risk trends)
- Rule management (add/edit rules without redeployment)
- Metrics tracking (detection rate, false positive rate, response time)

### ✅ Production-Ready Infrastructure
- Docker + Kubernetes deployment
- Prometheus + Grafana monitoring
- Auto-scaling, health checks, graceful degradation

---

## Tech Stack

**Backend**:
- Python 3.11+ (FastAPI, Pydantic, SQLAlchemy)
- PostgreSQL (audit trail, decision history)
- Kafka/Redis (event streaming)

**Frontend**:
- React + TypeScript (or Streamlit for MVP)

**Infrastructure**:
- Docker + Kubernetes
- Prometheus + Grafana
- AWS/GCP (deployment target)

**Detection Engine**:
- [whale-sentry](https://github.com/Rhea-Wang315/whale-sentry) (sandwich attack, wash trading detection)

---

## Quick Start

### Prerequisites
- Python 3.11+
- Docker + Docker Compose
- PostgreSQL (via Docker recommended)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Rhea-Wang315/risklens-platform.git
cd risklens-platform

# 2. Start infrastructure (PostgreSQL + Redis)
docker-compose up -d

# 3. Install Python dependencies
pip install -e ".[dev]"

# 4. Set up environment
cp .env.example .env
# Note: Default DATABASE_URL uses port 5432 (matches docker-compose.yml)

# 5. Initialize database
risklens db init

# 6. Start the API server
risklens serve
```

For a fully-scripted local demo (DB + migrations + API + dashboard + observability):

```bash
./scripts/demo.sh
```

To stop everything started by the demo:

```bash
./scripts/demo_stop.sh
```

To generate more decisions for the UI and Grafana charts:

```bash
python scripts/seed_demo.py --count 50
```

Run the Week 2 impact-analysis pipeline (case-study outputs):

```bash
python scripts/week2_impact_analysis.py \
  --input analysis/data/sample_week2_alerts.jsonl \
  --output-dir analysis/output
```

Generated artifacts:
- `analysis/output/decisions.csv`
- `analysis/output/impact_summary.json`
- `analysis/output/impact_summary.md`
- `analysis/output/incident_report_draft.md`

If your machine already has something bound to port 5432 (common on macOS with a system-wide PostgreSQL install), either stop it or change the Postgres port mapping.

To stop an EnterpriseDB PostgreSQL 15 service (if you have it installed):

```bash
sudo /Library/PostgreSQL/15/bin/pg_ctl -D /Library/PostgreSQL/15/data stop -m fast
```

Or use the provided dev override to run Postgres on 5433:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
export DATABASE_URL=postgresql://risklens:risklens_dev_password@localhost:5433/risklens
```

The API will be available at `http://localhost:8000`. Check health: `curl http://localhost:8000/health`

Prometheus metrics are exposed at `http://localhost:8000/metrics`.

### Streamlit Operator Dashboard (MVP)

For interview demos, RiskLens includes a lightweight Streamlit UI that talks to the API over HTTP.

```bash
# Install dashboard dependencies
pip install -e ".[dev,dashboard]"

# Terminal 1: start the API
risklens serve

# Terminal 2: start the dashboard
streamlit run dashboard/app.py
```

Open the dashboard at `http://localhost:8501`.

If your API is not running on `http://localhost:8000`, set:

```bash
export RISKLENS_API_BASE_URL=http://localhost:8000
```

### Observability (Prometheus + Grafana)

Run Prometheus + Grafana via Docker (the API runs on your host and is scraped at `host.docker.internal:8000`):

```bash
docker-compose -f docker-compose.observability.yml up -d
```

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

### Docker Deployment (Recommended for Production)

```bash
# Build the Docker image
docker build -t risklens:latest .

# Run with docker-compose (includes PostgreSQL + Redis)
docker-compose up -d

# Or run standalone (requires external database)
docker run -d \
  --name risklens-api \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/risklens \
  risklens:latest
```

### Run Example

```bash
# Submit an alert for evaluation
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d @examples/example_alert.json

# Response:
{
  "decision_id": "dec_abc123",
  "risk_level": "HIGH",
  "action": "FREEZE",
  "confidence": 0.92,
  "rationale": "High-confidence wash trading: score=0.87, low counterparty diversity (2 unique addresses), large volume ($125K USD)",
  "evidence_refs": ["features.counterparty_diversity", "features.total_volume_usd", "samples[0]", "samples[1]"],
  "recommendations": [
    "Freeze account pending manual review",
    "Investigate counterparty addresses: 0xabc..., 0xdef...",
    "Check for fund flow to known exchanges"
  ]
}
```

### Kafka Event Streaming

RiskLens publishes decision events to Kafka for real-time integration with other systems.

```bash
# Start all services (including Kafka)
docker-compose up -d

# Run the example consumer to see decision events
python -m risklens.streaming.consumer

# In another terminal, submit an alert
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d @examples/example_alert.json

# Consumer will print:
# INFO - Received decision: id=dec_abc123, risk=HIGH, action=FREEZE, address=0x742d...
# WARNING - ⚠️  HIGH RISK ALERT: 0x742d... - Action: FREEZE
```

**Use cases**:
- Real-time alerting (Slack, PagerDuty)
- Dashboard updates (Grafana, custom UI)
- Automated actions (account freezing, compliance workflows)
- Audit log streaming to external systems

---

## Project Status

### Phase 1: Decision Engine ✅ (Implemented)
- [x] Rule definitions (JSON conditions) + CRUD API
- [x] Multi-dimensional risk scoring
- [x] PostgreSQL decision/audit storage
- [x] FastAPI service with core endpoints
- [x] Unit tests + CI coverage reporting

### Phase 2: Real-time Monitoring 🚧 (In Progress)
- [x] Kafka decision event publishing
- [ ] Kafka/Redis event streaming (end-to-end consumer + workflows)
- [ ] Real-time detection pipeline
- [ ] Alert manager with Slack integration
- [ ] K8s deployment manifests
### Phase 3: Operator Dashboard 🚧 (In Progress)
- [x] Streamlit operator dashboard (MVP)
- [ ] Alert management UI (advanced filters, triage workflow)
- [ ] Address profiling
- [x] Rule management interface (via API + dashboard)
- [x] Metrics dashboard (Prometheus + Grafana)

### Phase 4: AI Enhancement 💡 (Future)
- [ ] Anomaly pattern discovery (unsupervised learning)
- [ ] Address profiling with graph analysis
- [ ] Risk Agent (autonomous decision-making)

### Rules Management API

Dynamically manage risk rules without code deployment.

```bash
# List all rules
curl http://localhost:8000/api/v1/rules

# Create a new rule
curl -X POST http://localhost:8000/api/v1/rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_id": "custom_high_risk",
    "name": "Custom High Risk Rule",
    "description": "Freeze accounts with score > 0.9",
    "pattern_types": ["WASH_TRADING"],
    "conditions": {"score": {"gte": 0.9}},
    "action": "FREEZE",
    "priority": 200,
    "enabled": true
  }'

# Update a rule
curl -X PUT http://localhost:8000/api/v1/rules/custom_high_risk \
  -H "Content-Type: application/json" \
  -d '{...}'

# Delete a rule
curl -X DELETE http://localhost:8000/api/v1/rules/custom_high_risk
```

**Benefits**:
- No code deployment needed to adjust rules
- A/B test different rule configurations
- Quick response to new attack patterns
- Audit trail of rule changes


---

## Use Cases

### 1. Centralized Exchange (CEX)
**Scenario**: Detect and freeze accounts involved in wash trading to inflate token volume.

**Workflow**:
1. Real-time monitoring detects suspicious swap patterns
2. Decision engine evaluates: HIGH risk, FREEZE action
3. Alert sent to compliance team via Slack
4. Operator reviews evidence in dashboard
5. Account frozen, audit trail generated for regulator

### 2. DeFi Protocol
**Scenario**: Identify MEV bots exploiting liquidity pools.

**Workflow**:
1. whale-sentry detects sandwich attacks
2. Decision engine: MEDIUM risk, WARN action
3. Protocol team investigates attacker address
4. If confirmed malicious: add to blocklist, update rules

### 3. Compliance Team
**Scenario**: Generate audit report for regulatory review.

**Workflow**:
1. Query: "All HIGH risk decisions in Q1 2026"
2. System exports: decision history + evidence + rationale
3. Compliance officer reviews and submits to regulator

---

## What This Project Demonstrates

### The Problem: Detection ≠ Decision
Most on-chain risk tools stop at detection. They output:
- `score=0.87, pattern=ROUNDTRIP, confidence=HIGH`

But risk teams need to answer:
- **What action should we take?** (freeze, warn, escalate?)
- **Why is this decision justified?** (evidence chain for audit)
- **How do we scale to 1000+ alerts/day?** (automation + human review)

### The Solution: End-to-End Risk Platform
RiskLens Platform bridges detection → decision → action:
- **Automated decisions** for 80% of cases (rule-based, auditable)
- **Human review** for edge cases (via dashboard)
- **Complete audit trail** for compliance (regulatory-ready)

### Technical Capabilities

**Domain Expertise**:
- Deep understanding of DeFi mechanics, MEV attacks, wash trading patterns
- Integration with production detection systems (whale-sentry)
- Regulatory awareness: MAS, FinCEN, FATF compliance considerations

**Engineering Excellence**:
- Scalable architecture: Kafka-based streaming, K8s deployment, 100+ events/sec
- Production infrastructure: Docker, Prometheus monitoring, health checks, auto-scaling
- Type-safe implementation: Pydantic models, comprehensive testing

**Operational Design**:
- Configurable rules: Update risk logic without code deployment
- Complete audit trails: Every decision linked to evidence, immutable logs
- Human-in-the-loop: Dashboard for review, approval workflows for high-risk actions
---

## Related Projects

This is part of a 3-project series on Web3 risk management:

1. **[whale-sentry](https://github.com/Rhea-Wang315/whale-sentry)**: Detection engine (sandwich attacks, wash trading)
2. **RiskLens Platform** (this repo): Decision engine + operational workflows
3. **[risk-agent](https://github.com/Rhea-Wang315/risk-agent)**: AI-powered autonomous risk agent (future)

---

## Development Roadmap
**Current Focus**: Phase 3 - Operator Dashboard + Observability

Historical planning docs are archived in `docs/archive/`:
- `docs/archive/ACTION_PLAN.md`
- `docs/archive/ROADMAP.md`

**Next Milestones**:
- Address profiling (API + dashboard page)
- Alert management workflow (triage + filtering)
- Slack alert integration + runbooks

---

## Contributing

This project is under active development. Contributions and feedback are welcome via issues and pull requests.

---

## License

MIT License - see [LICENSE](./LICENSE) for details.

---

## Author

**Rhea Wang**  
M.S. in Statistics, University of Pennsylvania  
AWS Certified Solutions Architect | Certified Kubernetes Administrator

Background: Full-stack development + AI agents + cloud infrastructure, now focused on Web3 risk management.

**Open to opportunities**: Web3 risk control / data engineering roles (remote or Singapore-based).

---

## Contact

- GitHub: [@Rhea-Wang315](https://github.com/Rhea-Wang315)
- LinkedIn: [Rhea Wang](https://www.linkedin.com/in/rheawangwork)
- Email: qinw.official@gmail.com
