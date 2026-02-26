"""Database models for RiskLens Platform."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, Float, Index, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DecisionRecord(Base):
    """Decision record for audit trail.
    
    Stores all decisions made by the risk engine, including:
    - Input alert data (for reproducibility)
    - Decision output (action, confidence, rationale)
    - Risk assessment (level, score)
    - Evidence and recommendations
    - Rule version (for auditing rule changes)
    """

    __tablename__ = "decisions"

    # Primary key
    decision_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # References
    alert_id = Column(String(255), nullable=False, index=True)
    address = Column(String(42), nullable=False, index=True)  # Ethereum address

    # Risk assessment
    risk_level = Column(String(20), nullable=False, index=True)  # LOW/MEDIUM/HIGH/CRITICAL
    action = Column(String(20), nullable=False, index=True)  # OBSERVE/WARN/FREEZE/ESCALATE
    confidence = Column(Float, nullable=False)  # 0.0 - 1.0
    risk_score = Column(Float, nullable=False)  # 0.0 - 100.0

    # Explanation
    rationale = Column(Text, nullable=False)  # Human-readable explanation
    evidence_refs = Column(JSON, nullable=False)  # List of evidence field references
    recommendations = Column(JSON, nullable=False)  # List of recommended actions
    limitations = Column(JSON, nullable=False)  # Known limitations of assessment

    # Metadata
    rule_version = Column(String(20), nullable=False)  # Version of rules used
    decided_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Full alert data for audit (stored as JSON)
    alert_data = Column(JSON, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<DecisionRecord("
            f"id={self.decision_id}, "
            f"address={self.address}, "
            f"action={self.action}, "
            f"risk_level={self.risk_level}"
            f")>"
        )


# Composite indexes for common queries
Index("idx_address_decided_at", DecisionRecord.address, DecisionRecord.decided_at)
Index("idx_risk_level_action", DecisionRecord.risk_level, DecisionRecord.action)
Index("idx_decided_at_action", DecisionRecord.decided_at, DecisionRecord.action)
