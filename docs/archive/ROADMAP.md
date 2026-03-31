# RiskLens Platform - Development Roadmap

## Vision

Build a production-grade risk control platform for Web3, combining statistical detection (whale-sentry), rule-based decision engine, real-time monitoring, and AI-powered automation.

**Target Users**: Risk control teams at Web3 exchanges, DeFi protocols, and compliance-focused organizations.

**Core Value Proposition**: From detection to decision to action - a complete, auditable, and scalable risk management system.

---

## Architecture Overview

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
│         │                    │                    │          │
│    whale-sentry         Rule Engine          Alert Mgr      │
│    (external lib)       + Scoring Model      + Audit Log    │
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

## Phase Breakdown

### Phase 0: Foundation (Current)
**Status**: ✅ Complete

**Deliverables**:
- whale-sentry detection engine (101 tests passing)
- Sandwich attack detection (O(n log n) optimized)
- Wash trading detection (ROUNDTRIP pattern)
- Data pipeline from Uniswap V3 Subgraph

---

### Phase 1: Decision Engine (Core)
**Goal**: Build a configurable rule engine that converts detection alerts into actionable decisions.

**Key Components**:

#### 1.1 Rule Engine
- **Input**: Alert from whale-sentry (address, pattern, score, features, evidence)
- **Processing**: 
  - Rule matching via Python DSL (similar to Drools)
  - Multi-dimensional risk scoring (not just whale-sentry score)
  - Decision logic (OBSERVE / WARN / FREEZE / ESCALATE)
- **Output**: Decision + rationale + audit trail

**Example Rule**:
```python
IF alert.score > 0.8 
   AND alert.features.counterparty_diversity < 3
   AND alert.features.total_volume_usd > 100000
THEN decision = FREEZE
     confidence = 0.95
     rationale = "High-confidence wash trading with low counterparty diversity"
```

#### 1.2 Risk Scoring Model
Combine multiple signals:
- Detection score (from whale-sentry)
- Address reputation (first-time vs known entity)
- Transaction characteristics (amount, timing, frequency)
- Historical behavior (past alerts, false positive rate)

**Output**: Unified risk score (0-100) with breakdown by dimension.

#### 1.3 Audit Trail
Every decision must be:
- Timestamped
- Linked to input evidence
- Attributed to rule/model version
- Stored in database (PostgreSQL)

**Why**: Regulatory compliance, internal review, model debugging.

#### 1.4 API Layer
FastAPI endpoints:
- `POST /api/v1/evaluate` - Submit alert, get decision
- `GET /api/v1/decisions/{id}` - Retrieve decision history
- `GET /api/v1/rules` - List active rules
- `POST /api/v1/rules` - Add/update rules (admin only)

**Deliverables**:
- [ ] Rule DSL implementation
- [ ] Risk scoring model (weighted combination)
- [ ] PostgreSQL schema for audit trail
- [ ] FastAPI service with 4 core endpoints
- [ ] Unit tests (target: 80%+ coverage)
- [ ] Example rules for sandwich/wash trading scenarios

**Success Criteria**:
- Can process 1000 alerts and produce consistent decisions
- All decisions have complete audit trail
- Rules can be modified without code changes

---

### Phase 2: Real-time Monitoring
**Goal**: Transform from batch analysis to real-time detection and alerting.

**Key Components**:

#### 2.1 Event Ingestion
- Subscribe to on-chain events via Alchemy/Infura webhooks
- Or: Poll Uniswap V3 Subgraph at regular intervals
- Push events to message queue (Kafka or Redis Streams)

#### 2.2 Stream Processing
- Consumer reads from queue
- Runs whale-sentry detection in real-time
- Feeds results to decision engine
- High-priority alerts trigger immediate notifications

#### 2.3 Alert Manager
- Deduplication (don't spam same alert)
- Priority routing (CRITICAL → PagerDuty, MEDIUM → Slack)
- Rate limiting (max N alerts per hour)
- Integration with Slack/Discord/PagerDuty

#### 2.4 Infrastructure
- Docker containers for each service
- Kubernetes deployment (use your CKA cert!)
- Prometheus + Grafana for monitoring
- Health checks and auto-restart

**Deliverables**:
- [ ] Kafka/Redis setup with producer/consumer
- [ ] Real-time detection pipeline (latency < 5s)
- [ ] Alert manager with Slack integration
- [ ] Docker Compose for local dev
- [ ] K8s manifests for production deployment
- [ ] Prometheus metrics + Grafana dashboard

**Success Criteria**:
- Can process 100+ events per second
- Alert latency < 5 seconds from event to notification
- System uptime > 99% (simulated over 24h test)

---

### Phase 3: Operator Dashboard
**Goal**: Provide a UI for risk operators to review alerts, manage rules, and track metrics.

**Key Features**:

#### 3.1 Alert Management
- List view: All alerts with filters (status, risk level, time range)
- Detail view: Full alert context + decision rationale + evidence
- Actions: Approve/reject decision, add notes, escalate

#### 3.2 Address Profile
- Search by address
- View: Historical alerts, risk score trend, transaction summary
- Visualize: Address relationship graph (if connected to known entities)

#### 3.3 Rule Management
- CRUD operations for rules
- Test rule against historical data before activation
- Version control (track rule changes)

#### 3.4 Analytics Dashboard
- Daily metrics: Total alerts, detection rate, false positive rate
- Performance: Processing latency, system health
- Trends: Attack patterns over time

**Tech Stack Options**:
- **Option A (Fast)**: Streamlit - Python-native, quick to build
- **Option B (Professional)**: React + TypeScript - Better UX, more impressive

**Deliverables**:
- [ ] Alert list + detail pages
- [ ] Address profile page
- [ ] Rule management interface
- [ ] Analytics dashboard with key metrics
- [ ] User authentication (basic auth or JWT)

**Success Criteria**:
- Non-technical users can operate the system
- All CRUD operations work without touching code
- Dashboard loads in < 2 seconds

---

### Phase 4: AI Enhancement (Optional but High-Impact)
**Goal**: Use AI to discover new patterns and assist human operators.

**Key Components**:

#### 4.1 Anomaly Pattern Discovery
**Problem**: whale-sentry rules are manually defined. How to find new attack patterns?

**Approach**:
1. Collect "suspicious but undetected" cases (from human review)
2. Apply unsupervised learning (Isolation Forest, Autoencoder)
3. Cluster similar behaviors
4. Use LLM to generate hypotheses ("These transactions share X characteristic...")
5. Human validates → Convert to new rule → Deploy

**Tech**: scikit-learn, OpenAI API, human-in-the-loop workflow

#### 4.2 Address Profiling
**Problem**: Is this address a first-time offender or repeat attacker?

**Approach**:
1. Fetch address history (Etherscan API)
2. Feature engineering:
   - Transaction frequency, amount distribution
   - Counterparty diversity
   - Holding patterns (governance tokens, stablecoins)
   - Proximity to known blacklisted addresses
3. Train simple classifier (Logistic Regression or Decision Tree for interpretability)
4. Output: Risk profile + confidence + explanation

**Tech**: pandas, scikit-learn, Neo4j (for graph analysis)

#### 4.3 Graph Analysis
**Problem**: Attackers use multiple addresses. How to find connections?

**Approach**:
1. Build address relationship graph (shared counterparties, fund flows)
2. Store in Neo4j
3. Query: "Find all addresses within 2 hops of known attacker"
4. Visualize in dashboard (Cytoscape.js)

**Tech**: Neo4j, Cytoscape.js

**Deliverables**:
- [ ] Anomaly detection module (unsupervised learning)
- [ ] LLM-assisted hypothesis generation
- [ ] Address profiling model (interpretable ML)
- [ ] Neo4j graph database + query API
- [ ] Graph visualization in dashboard

**Success Criteria**:
- Discover at least 1 new pattern not covered by existing rules
- Address profiling accuracy > 85% on test set
- Graph queries return in < 1 second

---

### Phase 5: Risk Agent (Advanced)
**Goal**: Build an autonomous agent that can handle routine risk decisions with human oversight.

**See separate repo**: `risk-agent` (to be created)

**Integration Point**: Risk Agent calls RiskLens Platform APIs for decision execution.

---

## Technical Stack Summary

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Detection | whale-sentry (Python) | Already built, proven |
| Decision Engine | Python + Pydantic | Type safety, fast iteration |
| Database | PostgreSQL | ACID compliance for audit trail |
| Message Queue | Kafka or Redis Streams | Real-time event processing |
| API | FastAPI | Modern, async, auto-docs |
| Orchestration | Docker + K8s | Production-grade deployment |
| Monitoring | Prometheus + Grafana | Industry standard |
| Dashboard | Streamlit or React | TBD based on time budget |
| ML | scikit-learn | Interpretable models |
| Graph DB | Neo4j | Address relationship analysis |
| LLM | OpenAI API | Hypothesis generation |

---

## Non-Functional Requirements

### Performance
- Alert processing latency: < 5 seconds (P50), < 10 seconds (P99)
- API response time: < 500ms (P95)
- Dashboard load time: < 2 seconds
- Throughput: 100+ alerts per second

### Reliability
- System uptime: > 99.9% (excluding planned maintenance)
- Data durability: All decisions persisted to database
- Graceful degradation: If whale-sentry fails, queue alerts for retry

### Security
- API authentication (JWT or API keys)
- Role-based access control (admin vs operator)
- Audit log immutability (append-only)
- Secrets management (environment variables, not hardcoded)

### Scalability
- Horizontal scaling: Add more workers to process queue
- Database partitioning: By time range (monthly tables)
- Caching: Frequently accessed data (Redis)

### Observability
- Structured logging (JSON format)
- Distributed tracing (optional: Jaeger)
- Metrics: Request rate, error rate, latency
- Alerts: System health, queue backlog, error spikes

---

## Development Principles

### 1. Incremental Delivery
Each phase produces a working system. No "big bang" integration.

### 2. Evidence-Based
Every decision must be traceable to input data. No black boxes.

### 3. Interpretability Over Accuracy
A 90% accurate interpretable model beats a 95% accurate black box.

### 4. Production-Minded
Write code as if it will run in production tomorrow. Tests, docs, error handling.

### 5. Avoid Over-Engineering
Use the simplest solution that works. Optimize only when necessary.

---

## Success Metrics (For Job Search)

### Technical Metrics
- [ ] 80%+ test coverage across all modules
- [ ] < 5s alert processing latency
- [ ] 0 critical security vulnerabilities (via `safety` scan)
- [ ] Clean type checking (mypy strict mode)

### Demo Metrics
- [ ] Can process 1000+ real alerts and show results in dashboard
- [ ] Can demonstrate rule modification without code change
- [ ] Can show real-time alert flowing through system
- [ ] Can explain every decision with evidence trail

### Documentation Metrics
- [ ] README with clear problem statement and architecture
- [ ] API documentation (auto-generated via FastAPI)
- [ ] Deployment guide (Docker Compose + K8s)
- [ ] Demo video (5-10 minutes)

---

## Interview Talking Points

### For Risk Control Roles
> "I built an end-to-end risk control platform for Web3. It starts with statistical detection (whale-sentry), applies configurable business rules, and outputs actionable decisions with full audit trails. The system is production-ready with real-time monitoring, operator dashboard, and K8s deployment."

### For Data Science Roles
> "I combined statistical modeling, unsupervised learning, and LLM-assisted analysis to detect on-chain anomalies. The key challenge was balancing accuracy with interpretability - every decision must be explainable to compliance teams."

### For DevOps/Infrastructure Roles
> "I designed a scalable event-driven architecture using Kafka, Docker, and Kubernetes. The system handles 100+ events per second with sub-5-second latency, full observability via Prometheus/Grafana, and automated deployment pipelines."

### For AI/ML Roles
> "I built a hybrid system where rules handle known patterns and ML discovers new ones. Used unsupervised learning to cluster anomalies, then LLM to generate hypotheses for human validation. This human-in-the-loop approach ensures we catch evolving attack patterns while maintaining control."

---

## Risk Mitigation

### Risk: Scope Creep
**Mitigation**: Stick to phase boundaries. Phase N+1 only starts when Phase N is demo-ready.

### Risk: Over-Engineering
**Mitigation**: Use simplest tech that works. PostgreSQL before Neo4j. Streamlit before React.

### Risk: Perfectionism
**Mitigation**: 80% complete and demo-able beats 100% complete and not shipped.

### Risk: Losing Focus
**Mitigation**: Every feature must answer: "Will this impress a hiring manager?" If no, defer.

---

## Next Steps

1. **Read this roadmap thoroughly**
2. **Set up risklens-platform repo structure**
3. **Start Phase 1: Decision Engine**
4. **Commit early, commit often** (show progress on GitHub)
5. **Update README as you build** (keep it fresh for visitors)

---

**Remember**: The goal is not to build a perfect system. The goal is to demonstrate you can ship production-grade software that solves real problems. Ship fast, iterate, and get feedback.
