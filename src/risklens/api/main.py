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
from collections import Counter
from datetime import datetime
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import case
from sqlalchemy.orm import Session

from risklens.db.models import DecisionRecord
from risklens.db.session import get_db
from risklens.engine.decision import DecisionEngine
from risklens.engine.rule_store import get_rule_store
from risklens.engine.rules import RuleEvaluator
from risklens.models import (
    AddressProfile,
    Alert,
    Decision,
    DecisionStatus,
    DecisionTriageBatchResult,
    DecisionTriageBatchUpdate,
    DecisionTriageUpdate,
    RuleDefinition,
)
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


def _record_to_decision(record: DecisionRecord) -> Decision:
    """Convert a database decision record to API response model."""
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
        decision_status=record.decision_status or DecisionStatus.OPEN,
        triage_assignee=record.triage_assignee,
        triage_notes=record.triage_notes,
        triage_updated_at=record.triage_updated_at or record.decided_at,
    )


def _build_runtime_decision_engine() -> DecisionEngine:
    """Build a decision engine that reflects currently enabled runtime rules.

    If no runtime rules are configured, fall back to the default engine.
    """
    runtime_rules = get_rule_store().list_all(enabled_only=True)
    if not runtime_rules:
        return decision_engine

    return DecisionEngine(
        rule_evaluator=RuleEvaluator(runtime_rules),
        risk_scorer=decision_engine.risk_scorer,
        rule_version="runtime",
    )


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
        # Evaluate alert using currently enabled runtime rules (if any)
        decision = _build_runtime_decision_engine().evaluate_alert(alert)

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
            decision_status=DecisionStatus.OPEN.value,
            triage_assignee=None,
            triage_notes=None,
            triage_updated_at=decision.decided_at,
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
    return _record_to_decision(record)


@app.get("/api/v1/decisions", response_model=list[Decision])
async def list_decisions(
    address: Optional[str] = Query(None, description="Filter by Ethereum address"),
    risk_level: Optional[str] = Query(
        None, description="Filter by risk level (LOW/MEDIUM/HIGH/CRITICAL)"
    ),
    action: Optional[str] = Query(
        None, description="Filter by action (OBSERVE/WARN/FREEZE/ESCALATE)"
    ),
    decision_status: Optional[str] = Query(
        None, description="Filter by triage status (OPEN/IN_REVIEW/RESOLVED/FALSE_POSITIVE)"
    ),
    triage_assignee: Optional[str] = Query(None, description="Filter by triage assignee"),
    min_risk_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum risk score"),
    max_risk_score: Optional[float] = Query(None, ge=0, le=100, description="Maximum risk score"),
    decided_after: Optional[datetime] = Query(
        None, description="Filter decisions made at/after this UTC timestamp (ISO-8601)"
    ),
    decided_before: Optional[datetime] = Query(
        None, description="Filter decisions made at/before this UTC timestamp (ISO-8601)"
    ),
    sort_by: Literal["decided_at", "triage_updated_at", "risk_score", "priority"] = Query(
        "decided_at", description="Sort key for decision list"
    ),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort direction"),
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
    if decision_status:
        query = query.filter(DecisionRecord.decision_status == decision_status.upper())
    if triage_assignee:
        query = query.filter(DecisionRecord.triage_assignee == triage_assignee)
    if min_risk_score is not None:
        query = query.filter(DecisionRecord.risk_score >= min_risk_score)
    if max_risk_score is not None:
        query = query.filter(DecisionRecord.risk_score <= max_risk_score)
    if decided_after:
        query = query.filter(DecisionRecord.decided_at >= decided_after)
    if decided_before:
        query = query.filter(DecisionRecord.decided_at <= decided_before)

    if sort_by == "priority":
        status_priority = case(
            (DecisionRecord.decision_status == "OPEN", 3),
            (DecisionRecord.decision_status == "IN_REVIEW", 2),
            (DecisionRecord.decision_status == "RESOLVED", 1),
            (DecisionRecord.decision_status == "FALSE_POSITIVE", 0),
            else_=0,
        )
        risk_priority = case(
            (DecisionRecord.risk_level == "CRITICAL", 4),
            (DecisionRecord.risk_level == "HIGH", 3),
            (DecisionRecord.risk_level == "MEDIUM", 2),
            (DecisionRecord.risk_level == "LOW", 1),
            else_=0,
        )
        query = query.order_by(
            status_priority.desc(),
            risk_priority.desc(),
            DecisionRecord.triage_updated_at.desc(),
            DecisionRecord.decided_at.desc(),
        )
    else:
        sort_columns = {
            "decided_at": DecisionRecord.decided_at,
            "triage_updated_at": DecisionRecord.triage_updated_at,
            "risk_score": DecisionRecord.risk_score,
        }
        selected_column = sort_columns[sort_by]
        query = query.order_by(
            selected_column.asc() if sort_order == "asc" else selected_column.desc()
        )

    # Apply pagination
    records = query.offset(offset).limit(limit).all()

    # Convert to Decision objects
    return [_record_to_decision(record) for record in records]


@app.patch("/api/v1/decisions/{decision_id}/triage", response_model=Decision)
async def update_decision_triage(
    decision_id: str,
    triage: DecisionTriageUpdate,
    db: Session = Depends(get_db),
) -> Decision:
    """Update triage metadata for an existing decision."""
    record = db.query(DecisionRecord).filter(DecisionRecord.decision_id == decision_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Decision {decision_id} not found")

    record.decision_status = triage.decision_status.value
    record.triage_assignee = triage.triage_assignee
    record.triage_notes = triage.triage_notes
    record.triage_updated_at = datetime.utcnow()

    db.add(record)
    db.commit()
    db.refresh(record)
    return _record_to_decision(record)


@app.patch("/api/v1/decisions/triage/batch", response_model=DecisionTriageBatchResult)
async def update_decisions_triage_batch(
    triage: DecisionTriageBatchUpdate,
    db: Session = Depends(get_db),
) -> DecisionTriageBatchResult:
    """Update triage metadata for multiple decisions."""
    records = (
        db.query(DecisionRecord).filter(DecisionRecord.decision_id.in_(triage.decision_ids)).all()
    )

    found_ids = {record.decision_id for record in records}
    not_found_ids = [
        decision_id for decision_id in triage.decision_ids if decision_id not in found_ids
    ]

    now = datetime.utcnow()
    for record in records:
        record.decision_status = triage.decision_status.value
        record.triage_assignee = triage.triage_assignee
        record.triage_notes = triage.triage_notes
        record.triage_updated_at = now
        db.add(record)

    db.commit()

    updated_decision_ids = [record.decision_id for record in records]
    return DecisionTriageBatchResult(
        updated_count=len(updated_decision_ids),
        not_found_ids=not_found_ids,
        updated_decision_ids=updated_decision_ids,
    )


@app.get("/api/v1/addresses/{address}/profile", response_model=AddressProfile)
async def get_address_profile(
    address: str,
    recent_limit: int = Query(
        20, ge=1, le=200, description="Number of recent decisions to include"
    ),
    db: Session = Depends(get_db),
) -> AddressProfile:
    """Build a lightweight profile summary for a single address."""
    records = (
        db.query(DecisionRecord)
        .filter(DecisionRecord.address == address)
        .order_by(DecisionRecord.decided_at.desc())
        .all()
    )

    if not records:
        raise HTTPException(status_code=404, detail=f"No decisions found for address {address}")

    action_counts: Counter[str] = Counter()
    risk_level_counts: Counter[str] = Counter()
    pattern_type_counts: Counter[str] = Counter()

    total_score = 0.0
    for record in records:
        action_counts[record.action] += 1
        risk_level_counts[record.risk_level] += 1
        total_score += record.risk_score

        pattern_type = "UNKNOWN"
        if isinstance(record.alert_data, dict):
            raw_pattern = record.alert_data.get("pattern_type")
            if isinstance(raw_pattern, str) and raw_pattern:
                pattern_type = raw_pattern
        pattern_type_counts[pattern_type] += 1

    recent_records = records[:recent_limit]

    # Records are sorted desc; first item is latest and last is earliest.
    latest_decided_at = records[0].decided_at
    first_decided_at = records[-1].decided_at

    return AddressProfile(
        address=address,
        total_decisions=len(records),
        avg_risk_score=round(total_score / len(records), 2),
        first_decided_at=first_decided_at,
        latest_decided_at=latest_decided_at,
        action_counts=dict(action_counts),
        risk_level_counts=dict(risk_level_counts),
        pattern_type_counts=dict(pattern_type_counts),
        recent_decisions=[_record_to_decision(record) for record in recent_records],
    )


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
