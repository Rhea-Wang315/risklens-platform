"""FastAPI application for RiskLens Platform.

This is the main entry point for the REST API that provides:
- Alert evaluation endpoint (POST /api/v1/evaluate)
- Decision retrieval endpoints (GET /api/v1/decisions/...)
- Health check endpoint (GET /health)

Design Philosophy:
- RESTful design with clear resource naming
- Comprehensive error handling with proper HTTP status codes
- Dependency injection for database sessions
- Structured logging for observability
- OpenAPI documentation auto-generated
"""

import time
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.orm import Session

from risklens.db.models import DecisionRecord
from risklens.db.session import get_db
from risklens.engine.decision import DecisionEngine
from risklens.engine.rule_store import get_rule_store
from risklens.models import Alert, Decision, RuleDefinition
from risklens.observability.metrics import (
    DECISIONS_TOTAL,
    EVALUATE_LATENCY_SECONDS,
    EVALUATE_REQUESTS_TOTAL,
)
from risklens.streaming import get_producer

# Initialize FastAPI app
app = FastAPI(
    title="RiskLens Platform API",
    description="Production-grade risk control system for Web3",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Initialize decision engine (singleton)
decision_engine = DecisionEngine()


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Status message indicating service health
    """
    return {"status": "ok", "service": "risklens-platform", "version": "0.1.0"}


@app.get("/metrics")
async def metrics() -> Response:
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.post("/api/v1/evaluate", response_model=Decision, status_code=201)
async def evaluate_alert(
    alert: Alert,
    db: Session = Depends(get_db),
) -> Decision:
    """Evaluate an alert and return a decision.

    This is the main entry point for risk evaluation. It:
    1. Runs the alert through the decision engine
    2. Stores the decision in the database for audit
    3. Returns the decision with action, rationale, and recommendations

    Args:
        alert: Alert from detection engine (e.g., whale-sentry)
        db: Database session (injected)

    Returns:
        Decision with action, risk assessment, and rationale

    Raises:
        HTTPException: 400 if alert is invalid, 500 if internal error
    """
    start = time.perf_counter()
    try:
        # Evaluate alert using decision engine
        decision = decision_engine.evaluate_alert(alert)

        # Store decision in database for audit trail
        record = DecisionRecord(
            decision_id=decision.decision_id,
            alert_id=alert.alert_id,
            address=alert.address,
            risk_level=decision.risk_level.value,
            action=decision.action.value,
            confidence=decision.confidence,
            risk_score=decision.risk_score,
            rationale=decision.rationale,
            evidence_refs=decision.evidence_refs,
            recommendations=decision.recommendations,
            limitations=decision.limitations,
            rule_version=decision.rule_version,
            decided_at=decision.decided_at,
            alert_data=alert.model_dump(mode="json"),
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        # Publish decision to Kafka for real-time streaming
        kafka_producer = get_producer()
        kafka_producer.publish_decision(decision)

        EVALUATE_REQUESTS_TOTAL.labels(result="success").inc()
        DECISIONS_TOTAL.labels(
            action=decision.action.value,
            risk_level=decision.risk_level.value,
        ).inc()

        return decision

    except Exception as e:
        EVALUATE_REQUESTS_TOTAL.labels(result="error").inc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to evaluate alert: {str(e)}")

    finally:
        EVALUATE_LATENCY_SECONDS.observe(time.perf_counter() - start)


@app.get("/api/v1/decisions/{decision_id}", response_model=Decision)
async def get_decision(
    decision_id: str,
    db: Session = Depends(get_db),
) -> Decision:
    """Retrieve a decision by ID.

    Args:
        decision_id: Unique decision identifier
        db: Database session (injected)

    Returns:
        Decision object

    Raises:
        HTTPException: 404 if decision not found
    """
    record = db.query(DecisionRecord).filter(DecisionRecord.decision_id == decision_id).first()

    if not record:
        raise HTTPException(status_code=404, detail=f"Decision {decision_id} not found")

    # Reconstruct Decision object from database record
    return Decision(
        decision_id=record.decision_id,
        alert_id=record.alert_id,
        address=record.address,
        risk_level=record.risk_level,
        action=record.action,
        confidence=record.confidence,
        risk_score=record.risk_score,
        rationale=record.rationale,
        evidence_refs=record.evidence_refs,
        recommendations=record.recommendations,
        limitations=record.limitations,
        rule_version=record.rule_version,
        decided_at=record.decided_at,
    )


@app.get("/api/v1/decisions", response_model=list[Decision])
async def list_decisions(
    address: Optional[str] = Query(None, description="Filter by Ethereum address"),
    risk_level: Optional[str] = Query(
        None, description="Filter by risk level (LOW/MEDIUM/HIGH/CRITICAL)"
    ),
    action: Optional[str] = Query(
        None, description="Filter by action (OBSERVE/WARN/FREEZE/ESCALATE)"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
) -> list[Decision]:
    """List decisions with optional filtering.

    Args:
        address: Filter by Ethereum address (optional)
        risk_level: Filter by risk level (optional)
        action: Filter by action type (optional)
        limit: Maximum number of results (default: 100, max: 1000)
        offset: Number of results to skip for pagination (default: 0)
        db: Database session (injected)

    Returns:
        List of Decision objects matching filters
    """
    # Build query with filters
    query = db.query(DecisionRecord)

    if address:
        query = query.filter(DecisionRecord.address == address)
    if risk_level:
        query = query.filter(DecisionRecord.risk_level == risk_level.upper())
    if action:
        query = query.filter(DecisionRecord.action == action.upper())

    # Order by decided_at descending (most recent first)
    query = query.order_by(DecisionRecord.decided_at.desc())

    # Apply pagination
    records = query.offset(offset).limit(limit).all()

    # Convert to Decision objects
    decisions = []
    for record in records:
        decisions.append(
            Decision(
                decision_id=record.decision_id,
                alert_id=record.alert_id,
                address=record.address,
                risk_level=record.risk_level,
                action=record.action,
                confidence=record.confidence,
                risk_score=record.risk_score,
                rationale=record.rationale,
                evidence_refs=record.evidence_refs,
                recommendations=record.recommendations,
                limitations=record.limitations,
                rule_version=record.rule_version,
                decided_at=record.decided_at,
            )
        )

    return decisions


# Rules Management Endpoints


@app.get("/api/v1/rules", response_model=list[RuleDefinition])
async def list_rules(
    enabled_only: bool = Query(False, description="Only return enabled rules"),
) -> list[RuleDefinition]:
    """List all rules.

    Args:
        enabled_only: If True, only return enabled rules

    Returns:
        List of rules sorted by priority
    """
    rule_store = get_rule_store()
    return rule_store.list_all(enabled_only=enabled_only)


@app.post("/api/v1/rules", response_model=RuleDefinition, status_code=201)
async def create_rule(rule: RuleDefinition) -> RuleDefinition:
    """Create a new rule.

    Args:
        rule: Rule definition

    Returns:
        Created rule

    Raises:
        HTTPException: 400 if rule with same ID exists
    """
    try:
        rule_store = get_rule_store()
        return rule_store.create(rule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/rules/{rule_id}", response_model=RuleDefinition)
async def get_rule(rule_id: str) -> RuleDefinition:
    """Get a rule by ID.

    Args:
        rule_id: Rule ID

    Returns:
        Rule definition

    Raises:
        HTTPException: 404 if rule not found
    """
    rule_store = get_rule_store()
    rule = rule_store.get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    return rule


@app.put("/api/v1/rules/{rule_id}", response_model=RuleDefinition)
async def update_rule(rule_id: str, rule: RuleDefinition) -> RuleDefinition:
    """Update an existing rule.

    Args:
        rule_id: Rule ID to update
        rule: New rule definition

    Returns:
        Updated rule

    Raises:
        HTTPException: 400 if validation fails, 404 if not found
    """
    try:
        rule_store = get_rule_store()
        return rule_store.update(rule_id, rule)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/v1/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: str):
    """Delete a rule.

    Args:
        rule_id: Rule ID to delete

    Raises:
        HTTPException: 404 if rule not found
    """
    rule_store = get_rule_store()
    if not rule_store.delete(rule_id):
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle ValueError exceptions (e.g., invalid enum values)."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
