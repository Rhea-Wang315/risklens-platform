"""Tests for database models and operations."""

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from risklens.db.models import DecisionRecord
from risklens.db.session import SessionLocal, drop_db, init_db


@pytest.fixture(scope="function")
def db_session() -> Session:
    """Create a fresh database session for each test."""
    # Setup: create tables
    init_db()
    
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Teardown: drop tables
        drop_db()


def test_create_decision_record(db_session: Session) -> None:
    """Test creating a decision record."""
    decision = DecisionRecord(
        decision_id="test_dec_001",
        alert_id="test_alert_001",
        address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        risk_level="HIGH",
        action="FREEZE",
        confidence=0.92,
        risk_score=87.5,
        rationale="High-confidence wash trading detected",
        evidence_refs=["features.counterparty_diversity", "features.total_volume_usd"],
        recommendations=["Freeze account", "Investigate counterparties"],
        limitations=["Limited to 5-minute window"],
        rule_version="v1.0.0",
        alert_data={
            "alert_id": "test_alert_001",
            "score": 0.87,
            "pattern_type": "WASH_TRADING",
        },
    )
    
    db_session.add(decision)
    db_session.commit()
    
    # Verify
    retrieved = db_session.query(DecisionRecord).filter_by(decision_id="test_dec_001").first()
    assert retrieved is not None
    assert retrieved.address == "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
    assert retrieved.risk_level == "HIGH"
    assert retrieved.action == "FREEZE"
    assert retrieved.confidence == 0.92


def test_query_by_address(db_session: Session) -> None:
    """Test querying decisions by address."""
    # Create multiple decisions for same address
    for i in range(3):
        decision = DecisionRecord(
            decision_id=f"test_dec_{i}",
            alert_id=f"test_alert_{i}",
            address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            risk_level="MEDIUM",
            action="WARN",
            confidence=0.75,
            risk_score=65.0,
            rationale=f"Test decision {i}",
            evidence_refs=[],
            recommendations=[],
            limitations=[],
            rule_version="v1.0.0",
            alert_data={},
        )
        db_session.add(decision)
    
    db_session.commit()
    
    # Query
    decisions = (
        db_session.query(DecisionRecord)
        .filter_by(address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb")
        .all()
    )
    
    assert len(decisions) == 3


def test_query_by_risk_level(db_session: Session) -> None:
    """Test querying decisions by risk level."""
    # Create decisions with different risk levels
    risk_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    for level in risk_levels:
        decision = DecisionRecord(
            decision_id=f"test_dec_{level}",
            alert_id=f"test_alert_{level}",
            address=f"0x{level}",
            risk_level=level,
            action="OBSERVE",
            confidence=0.8,
            risk_score=50.0,
            rationale=f"Test {level}",
            evidence_refs=[],
            recommendations=[],
            limitations=[],
            rule_version="v1.0.0",
            alert_data={},
        )
        db_session.add(decision)
    
    db_session.commit()
    
    # Query HIGH risk
    high_risk = db_session.query(DecisionRecord).filter_by(risk_level="HIGH").all()
    assert len(high_risk) == 1
    assert high_risk[0].risk_level == "HIGH"


def test_query_by_action(db_session: Session) -> None:
    """Test querying decisions by action."""
    actions = ["OBSERVE", "WARN", "FREEZE", "ESCALATE"]
    for action in actions:
        decision = DecisionRecord(
            decision_id=f"test_dec_{action}",
            alert_id=f"test_alert_{action}",
            address=f"0x{action}",
            risk_level="MEDIUM",
            action=action,
            confidence=0.8,
            risk_score=60.0,
            rationale=f"Test {action}",
            evidence_refs=[],
            recommendations=[],
            limitations=[],
            rule_version="v1.0.0",
            alert_data={},
        )
        db_session.add(decision)
    
    db_session.commit()
    
    # Query FREEZE actions
    freeze_actions = db_session.query(DecisionRecord).filter_by(action="FREEZE").all()
    assert len(freeze_actions) == 1
    assert freeze_actions[0].action == "FREEZE"


def test_query_by_time_range(db_session: Session) -> None:
    """Test querying decisions by time range."""
    # Create decisions with different timestamps
    base_time = datetime(2026, 2, 26, 12, 0, 0)
    
    for i in range(5):
        decision = DecisionRecord(
            decision_id=f"test_dec_{i}",
            alert_id=f"test_alert_{i}",
            address="0xtest",
            risk_level="MEDIUM",
            action="OBSERVE",
            confidence=0.8,
            risk_score=60.0,
            rationale="Test",
            evidence_refs=[],
            recommendations=[],
            limitations=[],
            rule_version="v1.0.0",
            decided_at=datetime(2026, 2, 26, 12, i, 0),
            alert_data={},
        )
        db_session.add(decision)
    
    db_session.commit()
    
    # Query decisions after 12:02
    cutoff = datetime(2026, 2, 26, 12, 2, 0)
    recent = (
        db_session.query(DecisionRecord)
        .filter(DecisionRecord.decided_at >= cutoff)
        .all()
    )
    
    assert len(recent) == 3  # 12:02, 12:03, 12:04


def test_update_decision(db_session: Session) -> None:
    """Test updating a decision record."""
    decision = DecisionRecord(
        decision_id="test_dec_update",
        alert_id="test_alert_update",
        address="0xupdate",
        risk_level="LOW",
        action="OBSERVE",
        confidence=0.6,
        risk_score=40.0,
        rationale="Initial assessment",
        evidence_refs=[],
        recommendations=[],
        limitations=[],
        rule_version="v1.0.0",
        alert_data={},
    )
    
    db_session.add(decision)
    db_session.commit()
    
    # Update
    decision.risk_level = "HIGH"
    decision.action = "FREEZE"
    decision.rationale = "Updated after review"
    db_session.commit()
    
    # Verify
    updated = db_session.query(DecisionRecord).filter_by(decision_id="test_dec_update").first()
    assert updated.risk_level == "HIGH"
    assert updated.action == "FREEZE"
    assert updated.rationale == "Updated after review"


def test_delete_decision(db_session: Session) -> None:
    """Test deleting a decision record."""
    decision = DecisionRecord(
        decision_id="test_dec_delete",
        alert_id="test_alert_delete",
        address="0xdelete",
        risk_level="LOW",
        action="OBSERVE",
        confidence=0.5,
        risk_score=30.0,
        rationale="To be deleted",
        evidence_refs=[],
        recommendations=[],
        limitations=[],
        rule_version="v1.0.0",
        alert_data={},
    )
    
    db_session.add(decision)
    db_session.commit()
    
    # Delete
    db_session.delete(decision)
    db_session.commit()
    
    # Verify
    deleted = db_session.query(DecisionRecord).filter_by(decision_id="test_dec_delete").first()
    assert deleted is None


def test_json_fields(db_session: Session) -> None:
    """Test JSON field storage and retrieval."""
    decision = DecisionRecord(
        decision_id="test_dec_json",
        alert_id="test_alert_json",
        address="0xjson",
        risk_level="MEDIUM",
        action="WARN",
        confidence=0.75,
        risk_score=65.0,
        rationale="Testing JSON fields",
        evidence_refs=["field1", "field2", "field3"],
        recommendations=["Action 1", "Action 2"],
        limitations=["Limitation 1"],
        rule_version="v1.0.0",
        alert_data={
            "score": 0.87,
            "features": {"counterparty_diversity": 2, "volume": 125000},
            "nested": {"deep": {"value": 42}},
        },
    )
    
    db_session.add(decision)
    db_session.commit()
    
    # Verify JSON fields
    retrieved = db_session.query(DecisionRecord).filter_by(decision_id="test_dec_json").first()
    assert retrieved.evidence_refs == ["field1", "field2", "field3"]
    assert retrieved.recommendations == ["Action 1", "Action 2"]
    assert retrieved.alert_data["score"] == 0.87
    assert retrieved.alert_data["features"]["counterparty_diversity"] == 2
    assert retrieved.alert_data["nested"]["deep"]["value"] == 42


def test_composite_index_query(db_session: Session) -> None:
    """Test querying using composite indexes."""
    # Create decisions
    for i in range(3):
        decision = DecisionRecord(
            decision_id=f"test_dec_idx_{i}",
            alert_id=f"test_alert_idx_{i}",
            address="0xcomposite",
            risk_level="HIGH",
            action="FREEZE",
            confidence=0.9,
            risk_score=85.0,
            rationale="Test composite index",
            evidence_refs=[],
            recommendations=[],
            limitations=[],
            rule_version="v1.0.0",
            decided_at=datetime(2026, 2, 26, 12, i, 0),
            alert_data={},
        )
        db_session.add(decision)
    
    db_session.commit()
    
    # Query using composite index (address + decided_at)
    cutoff = datetime(2026, 2, 26, 12, 1, 0)
    results = (
        db_session.query(DecisionRecord)
        .filter(
            DecisionRecord.address == "0xcomposite",
            DecisionRecord.decided_at >= cutoff,
        )
        .all()
    )
    
    assert len(results) == 2  # 12:01, 12:02
