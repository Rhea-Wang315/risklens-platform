"""Data models for RiskLens Platform."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class PatternType(str, Enum):
    """Types of suspicious patterns detected."""

    SANDWICH_ATTACK = "SANDWICH_ATTACK"
    WASH_TRADING = "WASH_TRADING"
    VOLUME_INFLATION = "VOLUME_INFLATION"
    BURST_TRADING = "BURST_TRADING"
    ROUNDTRIP = "ROUNDTRIP"
    UNKNOWN = "UNKNOWN"


class RiskLevel(str, Enum):
    """Risk severity levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionType(str, Enum):
    """Recommended actions for risk mitigation."""

    OBSERVE = "OBSERVE"  # Monitor but take no action
    WARN = "WARN"  # Flag for review
    FREEZE = "FREEZE"  # Freeze account/funds
    ESCALATE = "ESCALATE"  # Escalate to compliance/legal


class DecisionStatus(str, Enum):
    """Triage status for operator workflow."""

    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class Alert(BaseModel):
    """Input alert from detection engine (e.g., whale-sentry)."""

    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    address: str = Field(..., description="Ethereum address under investigation")
    chain: str = Field(default="ethereum", description="Blockchain network")
    pool: Optional[str] = Field(None, description="DEX pool address")
    pair: Optional[str] = Field(None, description="Trading pair (e.g., WETH/USDC)")
    time_window_sec: int = Field(..., description="Detection time window in seconds")
    pattern_type: PatternType = Field(..., description="Type of suspicious pattern")
    score: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    features: dict[str, Any] = Field(
        default_factory=dict, description="Statistical features from detection"
    )
    evidence_samples: list[dict[str, Any]] = Field(
        default_factory=list, description="Sample transactions as evidence"
    )
    detected_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
                "chain": "ethereum",
                "pool": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
                "pair": "WETH/USDC",
                "time_window_sec": 300,
                "pattern_type": "WASH_TRADING",
                "score": 0.87,
                "features": {
                    "counterparty_diversity": 2,
                    "roundtrip_count": 15,
                    "total_volume_usd": 125000,
                    "avg_time_between_trades_sec": 18,
                },
                "evidence_samples": [
                    {
                        "tx_hash": "0xabc123...",
                        "timestamp": "2026-02-25T10:30:00Z",
                        "action": "swap",
                        "amount_usd": 5000,
                    }
                ],
            }
        }


class Decision(BaseModel):
    """Output decision from risk engine."""

    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    alert_id: str = Field(..., description="Reference to input alert")
    address: str = Field(..., description="Address under investigation")
    risk_level: RiskLevel = Field(..., description="Assessed risk severity")
    action: ActionType = Field(..., description="Recommended action")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Decision confidence")
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Unified risk score (0-100)")
    rationale: str = Field(..., description="Human-readable explanation")
    evidence_refs: list[str] = Field(
        default_factory=list, description="References to evidence fields"
    )
    recommendations: list[str] = Field(default_factory=list, description="Actionable next steps")
    limitations: list[str] = Field(
        default_factory=list, description="Known limitations of this assessment"
    )
    rule_version: str = Field(..., description="Version of rules used")
    decided_at: datetime = Field(default_factory=datetime.utcnow)
    decision_status: DecisionStatus = Field(
        default=DecisionStatus.OPEN, description="Operator triage status"
    )
    triage_assignee: Optional[str] = Field(
        default=None, description="Operator assigned to this decision"
    )
    triage_notes: Optional[str] = Field(default=None, description="Latest triage notes")
    triage_updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of latest triage update"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "decision_id": "dec_abc123",
                "alert_id": "alert_xyz789",
                "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
                "risk_level": "HIGH",
                "action": "FREEZE",
                "confidence": 0.92,
                "risk_score": 87.5,
                "rationale": "High-confidence wash trading: score=0.87, low counterparty diversity (2 unique addresses), large volume ($125K USD)",
                "evidence_refs": [
                    "features.counterparty_diversity",
                    "features.total_volume_usd",
                    "samples[0]",
                ],
                "recommendations": [
                    "Freeze account pending manual review",
                    "Investigate counterparty addresses",
                ],
                "limitations": [
                    "Limited to 5-minute time window",
                    "Does not check cross-chain activity",
                ],
                "rule_version": "v1.0.0",
                "decision_status": "OPEN",
                "triage_assignee": "rhea",
                "triage_notes": "Escalated to compliance for same-day review",
            }
        }


class RuleDefinition(BaseModel):
    """Definition of a risk rule."""

    rule_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Human-readable rule name")
    description: str = Field(..., description="What this rule detects")
    pattern_types: list[PatternType] = Field(..., description="Applicable pattern types")
    conditions: dict[str, Any] = Field(..., description="Rule conditions (DSL)")
    action: ActionType = Field(..., description="Action if rule matches")
    priority: int = Field(default=0, description="Rule priority (higher = evaluated first)")
    enabled: bool = Field(default=True, description="Whether rule is active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "High-Confidence Wash Trading",
                "description": "Freeze accounts with high wash trading score and low counterparty diversity",
                "pattern_types": ["WASH_TRADING", "ROUNDTRIP"],
                "conditions": {
                    "score": {">": 0.8},
                    "features.counterparty_diversity": {"<": 3},
                    "features.total_volume_usd": {">": 100000},
                },
                "action": "FREEZE",
                "priority": 10,
            }
        }


class AddressProfile(BaseModel):
    """Aggregated risk profile for an address."""

    address: str = Field(..., description="Address under investigation")
    total_decisions: int = Field(..., ge=0, description="Total decisions for this address")
    avg_risk_score: float = Field(..., ge=0.0, le=100.0, description="Average risk score")
    first_decided_at: Optional[datetime] = Field(
        None, description="Timestamp of earliest decision for this address"
    )
    latest_decided_at: Optional[datetime] = Field(
        None, description="Timestamp of latest decision for this address"
    )
    action_counts: dict[str, int] = Field(default_factory=dict, description="Action distribution")
    risk_level_counts: dict[str, int] = Field(
        default_factory=dict, description="Risk level distribution"
    )
    pattern_type_counts: dict[str, int] = Field(
        default_factory=dict, description="Detected pattern type distribution"
    )
    recent_decisions: list[Decision] = Field(
        default_factory=list, description="Most recent decisions for this address"
    )


class DecisionTriageUpdate(BaseModel):
    """Payload for triage updates on existing decisions."""

    decision_status: DecisionStatus = Field(..., description="Updated triage status")
    triage_assignee: Optional[str] = Field(default=None, description="Assigned operator")
    triage_notes: Optional[str] = Field(default=None, description="Triage notes")


class DecisionTriageBatchUpdate(BaseModel):
    """Payload for batch triage updates."""

    decision_ids: list[str] = Field(
        ..., min_length=1, description="Decision IDs to update in batch"
    )
    decision_status: DecisionStatus = Field(..., description="Updated triage status")
    triage_assignee: Optional[str] = Field(default=None, description="Assigned operator")
    triage_notes: Optional[str] = Field(default=None, description="Triage notes")


class DecisionTriageBatchResult(BaseModel):
    """Response for batch triage updates."""

    updated_count: int = Field(..., ge=0)
    not_found_ids: list[str] = Field(default_factory=list)
    updated_decision_ids: list[str] = Field(default_factory=list)
