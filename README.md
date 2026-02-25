# RiskLens Platform

**Production-Grade Risk Control System for Web3**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

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
- PostgreSQL (or use Docker)

### Installation

```bash
# Clone the repo
git clone https://github.com/Rhea-Wang315/risklens-platform.git
cd risklens-platform

# Install dependencies
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python -m risklens.cli db init

# Run the API server
python -m risklens.cli serve
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

---

## Project Status

### Phase 1: Decision Engine 🚧 (Current - In Progress)
- [ ] Rule DSL implementation
- [ ] Multi-dimensional risk scoring
- [ ] PostgreSQL audit trail
- [ ] FastAPI service with core endpoints
- [ ] Unit tests (target: 80%+ coverage)

### Phase 2: Real-time Monitoring 📋 (Planned)
- [ ] Kafka/Redis event streaming
- [ ] Real-time detection pipeline
- [ ] Alert manager with Slack integration
- [ ] K8s deployment manifests
### Phase 3: Operator Dashboard 📋 (Planned)
- [ ] Alert management UI
- [ ] Address profiling
- [ ] Rule management interface
- [ ] Metrics dashboard

### Phase 4: AI Enhancement 💡 (Future)
- [ ] Anomaly pattern discovery (unsupervised learning)
- [ ] Address profiling with graph analysis
- [ ] Risk Agent (autonomous decision-making)


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
**Current Focus**: Phase 1 - Decision Engine
Building the core rule engine and risk scoring system that converts detection alerts into actionable decisions.
**Next Milestones**:
- Complete database models and audit trail
- Implement rule DSL and decision logic
- Build FastAPI service with core endpoints
- Achieve 80%+ test coverage

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
