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

from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from risklens.db.models import DecisionRecord
from risklens.db.session import get_db
from risklens.engine.decision import DecisionEngine
from risklens.models import Alert, Decision

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
            alert_data=alert.model_dump(mode='json'),
        )
        
        db.add(record)
        db.commit()
        db.refresh(record)
        
        return decision
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to evaluate alert: {str(e)}"
        )


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
    record = db.query(DecisionRecord).filter(
        DecisionRecord.decision_id == decision_id
    ).first()
    
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Decision {decision_id} not found"
        )
    
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


@app.get("/api/v1/decisions", response_model=List[Decision])
async def list_decisions(
    address: Optional[str] = Query(None, description="Filter by Ethereum address"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level (LOW/MEDIUM/HIGH/CRITICAL)"),
    action: Optional[str] = Query(None, description="Filter by action (OBSERVE/WARN/FREEZE/ESCALATE)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
) -> List[Decision]:
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
        decisions.append(Decision(
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
        ))
    
    return decisions


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
