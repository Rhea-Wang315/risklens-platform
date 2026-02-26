"""Tests for decision engine."""

import pytest

from risklens.engine.decision import DecisionEngine
from risklens.engine.rules import RuleEvaluator
from risklens.engine.scoring import RiskScorer
from risklens.models import ActionType, Alert, PatternType, RiskLevel, RuleDefinition


def test_decision_engine_basic() -> None:
    """Test basic decision generation."""
    engine = DecisionEngine()
    
    alert = Alert(
        alert_id="test_001",
        address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        pattern_type=PatternType.WASH_TRADING,
        score=0.87,
        time_window_sec=300,
        features={
            "counterparty_diversity": 2,
            "total_volume_usd": 125000,
            "roundtrip_count": 15,
            "self_trade_ratio": 0.93,
        },
    )
    
    decision = engine.evaluate_alert(alert)
    
    # Verify decision structure
    assert decision.alert_id == "test_001"
    assert decision.address == "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
    assert decision.action in [ActionType.OBSERVE, ActionType.WARN, ActionType.FREEZE, ActionType.ESCALATE]
    assert decision.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
    assert 0 <= decision.confidence <= 1
    assert 0 <= decision.risk_score <= 100
    assert len(decision.rationale) > 0
    assert len(decision.evidence_refs) > 0
    assert len(decision.recommendations) > 0
    assert decision.rule_version == "v1.0.0"


def test_decision_engine_high_risk_freeze() -> None:
    """Test that high-risk wash trading triggers FREEZE."""
    engine = DecisionEngine()
    
    alert = Alert(
        alert_id="test_high_risk",
        address="0xhighrisk",
        pattern_type=PatternType.WASH_TRADING,
        score=0.95,
        time_window_sec=300,
        features={
            "counterparty_diversity": 1,
            "total_volume_usd": 500000,
            "roundtrip_count": 30,
            "self_trade_ratio": 0.98,
        },
    )
    
    decision = engine.evaluate_alert(alert)
    
    assert decision.action == ActionType.FREEZE
    assert decision.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
    assert decision.confidence >= 0.8


def test_decision_engine_low_risk_observe() -> None:
    """Test that low-risk alerts trigger OBSERVE."""
    engine = DecisionEngine()
    
    alert = Alert(
        alert_id="test_low_risk",
        address="0xlowrisk",
        pattern_type=PatternType.WASH_TRADING,
        score=0.3,
        time_window_sec=300,
        features={
            "counterparty_diversity": 20,
            "total_volume_usd": 5000,
            "roundtrip_count": 2,
            "self_trade_ratio": 0.2,
        },
    )
    
    decision = engine.evaluate_alert(alert)
    
    assert decision.action == ActionType.OBSERVE
    assert decision.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]


def test_decision_engine_custom_rules() -> None:
    """Test decision engine with custom rules."""
    # Custom rule: Always freeze sandwich attacks with score > 0.7
    custom_rules = [
        RuleDefinition(
            name="Freeze Sandwich",
            description="Always freeze sandwich attacks",
            pattern_types=[PatternType.SANDWICH_ATTACK],
            conditions={"score": {">": 0.7}},
            action=ActionType.FREEZE,
            priority=100,
        )
    ]
    
    evaluator = RuleEvaluator(custom_rules)
    engine = DecisionEngine(rule_evaluator=evaluator)
    
    alert = Alert(
        alert_id="test_sandwich",
        address="0xsandwich",
        pattern_type=PatternType.SANDWICH_ATTACK,
        score=0.8,
        time_window_sec=300,
    )
    
    decision = engine.evaluate_alert(alert)
    
    assert decision.action == ActionType.FREEZE


def test_decision_engine_custom_scorer() -> None:
    """Test decision engine with custom scorer."""
    # Conservative scorer (high detection weight)
    custom_scorer = RiskScorer(
        detection_weight=0.7,
        volume_weight=0.2,
        behavioral_weight=0.1,
    )
    
    engine = DecisionEngine(risk_scorer=custom_scorer)
    
    alert = Alert(
        alert_id="test_custom_scorer",
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.9,  # High detection score
        time_window_sec=300,
        features={
            "total_volume_usd": 10000,  # Low volume
            "counterparty_diversity": 10,  # High diversity
        },
    )
    
    decision = engine.evaluate_alert(alert)
    
    # With conservative scorer, high detection score should dominate
    assert decision.risk_score > 60


def test_decision_rationale_generation() -> None:
    """Test that rationale is informative."""
    engine = DecisionEngine()
    
    alert = Alert(
        alert_id="test_rationale",
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.85,
        time_window_sec=300,
        features={
            "counterparty_diversity": 2,
            "total_volume_usd": 200000,
            "roundtrip_count": 20,
        },
    )
    
    decision = engine.evaluate_alert(alert)
    
    # Rationale should mention key factors
    rationale_lower = decision.rationale.lower()
    assert "wash trading" in rationale_lower or "wash_trading" in rationale_lower
    assert "0.85" in decision.rationale or "85" in decision.rationale  # Score mentioned
    assert "counterparty" in rationale_lower or "diversity" in rationale_lower


def test_decision_evidence_refs() -> None:
    """Test that evidence references are populated."""
    engine = DecisionEngine()
    
    alert = Alert(
        alert_id="test_evidence",
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.8,
        time_window_sec=300,
        features={
            "counterparty_diversity": 2,
            "total_volume_usd": 150000,
        },
        evidence_samples=[
            {"tx_hash": "0xabc", "amount_usd": 50000},
            {"tx_hash": "0xdef", "amount_usd": 50000},
        ],
    )
    
    decision = engine.evaluate_alert(alert)
    
    # Should reference key features
    assert len(decision.evidence_refs) > 0
    assert any("score" in ref for ref in decision.evidence_refs)


def test_decision_recommendations() -> None:
    """Test that recommendations are actionable."""
    engine = DecisionEngine()
    
    alert = Alert(
        alert_id="test_recommendations",
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.9,
        time_window_sec=300,
        features={
            "counterparty_diversity": 1,
            "total_volume_usd": 300000,
        },
    )
    
    decision = engine.evaluate_alert(alert)
    
    # Should have recommendations
    assert len(decision.recommendations) > 0
    
    # Recommendations should be strings
    for rec in decision.recommendations:
        assert isinstance(rec, str)
        assert len(rec) > 0


def test_decision_limitations() -> None:
    """Test that limitations are documented."""
    engine = DecisionEngine()
    
    alert = Alert(
        alert_id="test_limitations",
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.8,
        time_window_sec=300,
    )
    
    decision = engine.evaluate_alert(alert)
    
    # Should document limitations
    assert len(decision.limitations) > 0
    
    # Should mention time window
    limitations_text = " ".join(decision.limitations).lower()
    assert "time" in limitations_text or "window" in limitations_text


def test_decision_confidence_calculation() -> None:
    """Test confidence calculation logic."""
    engine = DecisionEngine()
    
    # High confidence case: high score, many evidence samples
    alert_high_conf = Alert(
        alert_id="test_high_conf",
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.95,
        time_window_sec=300,
        evidence_samples=[{"tx": f"0x{i}"} for i in range(10)],
    )
    
    decision_high = engine.evaluate_alert(alert_high_conf)
    
    # Low confidence case: medium score, few evidence samples
    alert_low_conf = Alert(
        alert_id="test_low_conf",
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.6,
        time_window_sec=300,
        evidence_samples=[{"tx": "0x1"}],
    )
    
    decision_low = engine.evaluate_alert(alert_low_conf)
    
    # High confidence should be higher
    assert decision_high.confidence > decision_low.confidence


def test_decision_default_action() -> None:
    """Test default action when no rules match."""
    # Empty rule set
    evaluator = RuleEvaluator([])
    engine = DecisionEngine(rule_evaluator=evaluator)
    
    # High risk score
    alert_high = Alert(
        alert_id="test_default_high",
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.95,
        time_window_sec=300,
        features={
            "total_volume_usd": 1000000,
            "counterparty_diversity": 1,
        },
    )
    
    decision_high = engine.evaluate_alert(alert_high)
    assert decision_high.action in [ActionType.ESCALATE, ActionType.FREEZE]
    
    # Low risk score
    alert_low = Alert(
        alert_id="test_default_low",
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.3,
        time_window_sec=300,
        features={
            "total_volume_usd": 5000,
            "counterparty_diversity": 20,
        },
    )
    
    decision_low = engine.evaluate_alert(alert_low)
    assert decision_low.action == ActionType.OBSERVE


def test_decision_rule_version() -> None:
    """Test that rule version is tracked."""
    engine = DecisionEngine(rule_version="v2.0.0")
    
    alert = Alert(
        alert_id="test_version",
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.8,
        time_window_sec=300,
    )
    
    decision = engine.evaluate_alert(alert)
    
    assert decision.rule_version == "v2.0.0"


def test_decision_different_pattern_types() -> None:
    """Test decisions for different pattern types."""
    engine = DecisionEngine()
    
    patterns = [
        PatternType.WASH_TRADING,
        PatternType.SANDWICH_ATTACK,
        PatternType.VOLUME_INFLATION,
        PatternType.BURST_TRADING,
    ]
    
    for pattern in patterns:
        alert = Alert(
            alert_id=f"test_{pattern.value}",
            address="0xtest",
            pattern_type=pattern,
            score=0.8,
            time_window_sec=300,
        )
        
        decision = engine.evaluate_alert(alert)
        
        # Should produce valid decision for all pattern types
        assert decision.action in [ActionType.OBSERVE, ActionType.WARN, ActionType.FREEZE, ActionType.ESCALATE]
        assert decision.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
