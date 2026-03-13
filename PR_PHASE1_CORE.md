# feat: Complete Phase 1 Core - Decision Engine System

## Summary

Implements the complete core decision-making system for RiskLens Platform Phase 1, combining database layer, configurable rule engine, multi-dimensional risk scoring, and comprehensive decision logic. This PR delivers a production-ready system that converts detection alerts (from whale-sentry) into actionable, explainable, auditable decisions.

**93% test coverage with 47 passing tests.**

---

## What's Included

This PR completes the entire Phase 1 core foundation:

### 1. Database Layer (`260e9ac`)
**File**: `src/risklens/db/`

- **DecisionRecord** model with complete audit trail
- PostgreSQL integration with SQLAlchemy 2.0
- JSON fields for flexible evidence and recommendation storage
- Composite indexes for common query patterns:
  - `(address, decided_at)` - Query decisions by address over time
  - `(risk_level, action)` - Filter by severity and action type
  - `(decided_at, action)` - Time-based action queries
- Session management with connection pooling
- Database initialization and migration support

**Why this matters**: Every decision is stored with full context for regulatory compliance and audit trails.

---

### 2. Rule Engine (`6cfbaa2`)
**File**: `src/risklens/engine/rules.py`

- **RuleEvaluator** class for evaluating alerts against configurable rules
- **Python-based DSL** (no external dependencies):
  - Comparison operators: `>`, `<`, `>=`, `<=`, `==`, `!=`
  - Membership operators: `in`, `not_in`
  - Range operator: `between`
- **Nested field access** via dot notation (e.g., `features.counterparty_diversity`)
- **Priority-based matching**: Highest priority rule wins
- **5 default rules** covering common scenarios:
  1. High-confidence wash trading + low diversity → FREEZE (priority 10)
  2. High-confidence sandwich attack + high volume → ESCALATE (priority 10)
  3. Medium-confidence wash trading → WARN (priority 5)
  4. Medium-confidence sandwich attack → WARN (priority 5)
  5. Low-confidence patterns → OBSERVE (priority 1)

**Example rule**:
```python
RuleDefinition(
    name="High-Confidence Wash Trading - Freeze",
    pattern_types=[PatternType.WASH_TRADING],
    conditions={
        "score": {">": 0.8},
        "features.counterparty_diversity": {"<": 3},
        "features.total_volume_usd": {">": 100000},
    },
    action=ActionType.FREEZE,
    priority=10,
)
```

**Why this matters**: Rules can be modified without code changes, enabling rapid response to new attack patterns.

---

### 3. Risk Scoring Model (`6cfbaa2`)
**File**: `src/risklens/engine/scoring.py`

- **Multi-dimensional scoring** combining:
  - Detection score (50%): From whale-sentry's pattern detection
  - Volume risk (30%): Transaction amount relative to thresholds
  - Behavioral risk (20%): Counterparty diversity, roundtrip count, self-trade ratio
- **3 scoring profiles**:
  - **Default** (50/30/20): Balanced approach
  - **Conservative** (70/20/10): Trust detection more, minimize false positives
  - **Aggressive** (40/30/30): Catch more risks, higher false positive tolerance
- **4 risk levels**: CRITICAL (≥80), HIGH (≥60), MEDIUM (≥40), LOW (<40)
- **Explainable**: Each dimension's contribution is tracked

**Why this matters**: Single detection score isn't enough - volume and behavior context are critical for accurate risk assessment.

---

### 4. Decision Engine (`6cfbaa2`)
**File**: `src/risklens/engine/decision.py`

Main orchestrator that produces complete, actionable decisions:

**Inputs**:
- Alert from whale-sentry (address, pattern, score, features, evidence)

**Processing**:
1. Calculate multi-dimensional risk score
2. Evaluate against rules to determine action
3. Calculate confidence based on detection quality and evidence
4. Generate human-readable rationale
5. Identify key evidence fields
6. Generate specific recommendations
7. Document known limitations

**Outputs** (Decision object):
- **Action**: OBSERVE / WARN / FREEZE / ESCALATE
- **Risk Level**: LOW / MEDIUM / HIGH / CRITICAL
- **Risk Score**: 0-100 (explainable breakdown)
- **Confidence**: 0-1 (based on detection quality + evidence)
- **Rationale**: Human-readable explanation (e.g., "HIGH risk wash trading: detection score=0.87, risk score=85.3, counterparty diversity=2, volume=$125,000 USD, roundtrips=15")
- **Evidence Refs**: List of supporting data fields
- **Recommendations**: Actionable next steps
- **Limitations**: Known constraints (time window, single pool, etc.)
- **Rule Version**: For audit trail

**Example**:
```python
engine = DecisionEngine()
alert = Alert(
    address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    pattern_type=PatternType.WASH_TRADING,
    score=0.87,
    features={
        "counterparty_diversity": 2,
        "total_volume_usd": 125000,
        "roundtrip_count": 15,
    }
)

decision = engine.evaluate_alert(alert)
# Returns:
# - action: FREEZE
# - risk_level: HIGH
# - confidence: 0.92
# - rationale: "HIGH risk wash trading: detection score=0.87..."
# - recommendations: ["Freeze account pending review", ...]
```

**Why this matters**: Every decision is explainable, auditable, and includes actionable guidance for risk operators.

---

### 5. Comprehensive Test Suite (`601a847`)
**Files**: `tests/test_*.py`

**93% test coverage with 47 passing tests**:

- **Database tests** (9 tests):
  - CRUD operations
  - Query by address, risk level, action, time range
  - JSON field storage and retrieval
  - Composite index queries

- **Rule engine tests** (12 tests):
  - Basic evaluation and priority handling
  - All operators (>, <, in, between, etc.)
  - Pattern type filtering
  - Nested field access
  - Disabled rules
  - Default rule set

- **Risk scoring tests** (13 tests):
  - Multi-dimensional scoring
  - Volume and behavioral risk calculation
  - Weight validation
  - Conservative/aggressive profiles
  - Missing features handling
  - Threshold boundaries

- **Decision engine tests** (13 tests):
  - End-to-end decision generation
  - High/medium/low risk scenarios
  - Custom rules and scorers
  - Rationale generation
  - Evidence identification
  - Recommendations and limitations
  - Confidence calculation
  - Default actions
  - Different pattern types

**Coverage breakdown**:
```
src/risklens/models/__init__.py     100% (65/65)
src/risklens/engine/scoring.py      96%  (67/70)
src/risklens/db/models.py            96%  (26/27)
src/risklens/engine/decision.py     91%  (95/104)
src/risklens/engine/rules.py        85%  (66/76)
src/risklens/config.py              100% (33/33)
src/risklens/db/session.py          79%  (19/23)

TOTAL: 93% (372 statements, 27 missed)
```

**Why this matters**: High test coverage ensures production reliability and makes future changes safe.

---

## Technical Highlights

### Type Safety
- **Pydantic v2** for all data models
- **SQLAlchemy 2.0** for database ORM
- Full type hints throughout codebase

### Explainability
- Every decision includes human-readable rationale
- Evidence references point to specific data fields
- Confidence scores based on data quality

### Auditability
- Complete input (alert) stored with every decision
- Rule version tracking
- Timestamp and immutable records
- JSON fields preserve full context

### Extensibility
- Rules can be added/modified without code changes
- Multiple scoring profiles available
- Custom scorers and evaluators supported via dependency injection

### Production-Ready
- Connection pooling for database
- Composite indexes for query performance
- Comprehensive error handling
- Structured logging support (via config)

---

## Database Schema

```sql
CREATE TABLE decisions (
    decision_id VARCHAR(36) PRIMARY KEY,
    alert_id VARCHAR(255) NOT NULL,
    address VARCHAR(42) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    action VARCHAR(20) NOT NULL,
    confidence FLOAT NOT NULL,
    risk_score FLOAT NOT NULL,
    rationale TEXT NOT NULL,
    evidence_refs JSON NOT NULL,
    recommendations JSON NOT NULL,
    limitations JSON NOT NULL,
    rule_version VARCHAR(20) NOT NULL,
    decided_at TIMESTAMP NOT NULL,
    alert_data JSON NOT NULL
);

CREATE INDEX idx_address_decided_at ON decisions(address, decided_at);
CREATE INDEX idx_risk_level_action ON decisions(risk_level, action);
CREATE INDEX idx_decided_at_action ON decisions(decided_at, action);
```

---

## How to Test

### 1. Run all tests
```bash
pytest tests/ -v --cov=risklens --cov-report=term-missing

# Expected: 47 passed, 93% coverage
```

### 2. Test database connection
```bash
# Start PostgreSQL
docker start risklens-db

# Run database tests
pytest tests/test_db.py -v
```

### 3. Manual test
```python
from risklens.engine.decision import DecisionEngine
from risklens.models import Alert, PatternType

engine = DecisionEngine()

alert = Alert(
    address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    pattern_type=PatternType.WASH_TRADING,
    score=0.87,
    time_window_sec=300,
    features={
        "counterparty_diversity": 2,
        "total_volume_usd": 125000,
        "roundtrip_count": 15,
        "self_trade_ratio": 0.93,
    }
)

decision = engine.evaluate_alert(alert)
print(decision.model_dump_json(indent=2))
```

---

## What's Next? (Phase 1 Remaining)

After this PR is merged, the next steps are:

1. **FastAPI Service** (Day 2-3):
   - `POST /api/v1/evaluate` endpoint
   - `GET /api/v1/decisions/{id}` endpoint
   - Integration with whale-sentry
   - API tests

2. **Streamlit Dashboard** (Day 4-5):
   - Upload whale-sentry results
   - Visualize decisions
   - Filter/search interface
   - Deploy to Streamlit Cloud

3. **Case Study** (Day 6-7):
   - Use real whale-sentry data ($46.8M attacks detected)
   - Quantify business impact
   - Create incident report
   - Demo video

---

## Files Changed

```
src/risklens/
├── db/
│   ├── models.py           # Database schema (NEW)
│   └── session.py          # Connection management (NEW)
├── engine/
│   ├── rules.py            # Rule evaluation engine (NEW)
│   ├── scoring.py          # Risk scoring model (NEW)
│   └── decision.py         # Decision orchestrator (NEW)
└── models/__init__.py      # Pydantic models (ENHANCED)

tests/
├── test_db.py              # Database tests (NEW)
├── test_rules.py           # Rule engine tests (NEW)
├── test_scoring.py         # Scoring tests (NEW)
└── test_decision.py        # Decision engine tests (NEW)

.gitignore                  # Ignore internal docs (UPDATED)
PR_RULE_ENGINE.md           # PR documentation (NEW)
```

---

## Checklist

- [x] Database models implemented and tested
- [x] Rule engine with Python DSL
- [x] Multi-dimensional risk scoring
- [x] Decision engine with full output
- [x] 93% test coverage (47 passing tests)
- [x] Type-safe with Pydantic + SQLAlchemy
- [x] Explainable decisions (rationale + evidence)
- [x] Auditable (full context stored)
- [x] Production-ready code quality
- [x] Comprehensive documentation

---

## Breaking Changes

None (initial implementation).

---

## Performance Considerations

- Database connection pooling configured (pool_size=10, max_overflow=20)
- Composite indexes for common queries
- All rule evaluation is O(n) where n = number of rules
- Risk scoring is O(1)
- Decision generation is O(1)

Expected performance: <10ms per decision (excluding database I/O).

---

**Ready for review and merge!** 🚀
