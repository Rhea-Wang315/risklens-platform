"""Tests for risk scoring model."""

import pytest

from risklens.engine.scoring import (
    RiskScorer,
    create_aggressive_scorer,
    create_conservative_scorer,
    create_default_scorer,
)
from risklens.models import Alert, PatternType, RiskLevel


def test_risk_scorer_basic() -> None:
    """Test basic risk score calculation."""
    scorer = create_default_scorer()
    
    alert = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.8,
        time_window_sec=300,
        features={
            "total_volume_usd": 100000,
            "counterparty_diversity": 2,
            "roundtrip_count": 10,
            "self_trade_ratio": 0.9,
        },
    )
    
    risk_score = scorer.calculate_risk_score(alert)
    
    # Should be high risk
    assert risk_score > 60
    assert risk_score <= 100


def test_risk_scorer_weights_validation() -> None:
    """Test that weights must sum to 1.0."""
    with pytest.raises(ValueError, match="Weights must sum to 1.0"):
        RiskScorer(detection_weight=0.5, volume_weight=0.5, behavioral_weight=0.5)


def test_risk_scorer_volume_risk() -> None:
    """Test volume risk calculation."""
    scorer = create_default_scorer()
    
    # High volume
    alert_high = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.5,
        time_window_sec=300,
        features={"total_volume_usd": 1_500_000},
    )
    
    score_high = scorer.calculate_risk_score(alert_high)
    
    # Low volume
    alert_low = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.5,
        time_window_sec=300,
        features={"total_volume_usd": 5_000},
    )
    
    score_low = scorer.calculate_risk_score(alert_low)
    
    # High volume should have higher risk score
    assert score_high > score_low


def test_risk_scorer_behavioral_risk() -> None:
    """Test behavioral risk calculation."""
    scorer = create_default_scorer()
    
    # High behavioral risk (low diversity, many roundtrips, high self-trade)
    alert_high = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.5,
        time_window_sec=300,
        features={
            "total_volume_usd": 50000,
            "counterparty_diversity": 1,
            "roundtrip_count": 25,
            "self_trade_ratio": 0.95,
        },
    )
    
    score_high = scorer.calculate_risk_score(alert_high)
    
    # Low behavioral risk (high diversity, few roundtrips, low self-trade)
    alert_low = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.5,
        time_window_sec=300,
        features={
            "total_volume_usd": 50000,
            "counterparty_diversity": 15,
            "roundtrip_count": 2,
            "self_trade_ratio": 0.3,
        },
    )
    
    score_low = scorer.calculate_risk_score(alert_low)
    
    # High behavioral risk should have higher score
    assert score_high > score_low


def test_risk_scorer_bounded_output() -> None:
    """Test that risk score is always bounded [0, 100]."""
    scorer = create_default_scorer()
    
    # Extreme high values
    alert_extreme = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=1.0,
        time_window_sec=300,
        features={
            "total_volume_usd": 10_000_000,
            "counterparty_diversity": 1,
            "roundtrip_count": 100,
            "self_trade_ratio": 1.0,
        },
    )
    
    score = scorer.calculate_risk_score(alert_extreme)
    assert 0 <= score <= 100


def test_determine_risk_level() -> None:
    """Test risk level determination."""
    scorer = create_default_scorer()
    
    assert scorer.determine_risk_level(90) == RiskLevel.CRITICAL
    assert scorer.determine_risk_level(80) == RiskLevel.CRITICAL
    assert scorer.determine_risk_level(70) == RiskLevel.HIGH
    assert scorer.determine_risk_level(60) == RiskLevel.HIGH
    assert scorer.determine_risk_level(50) == RiskLevel.MEDIUM
    assert scorer.determine_risk_level(40) == RiskLevel.MEDIUM
    assert scorer.determine_risk_level(30) == RiskLevel.LOW
    assert scorer.determine_risk_level(10) == RiskLevel.LOW


def test_conservative_scorer() -> None:
    """Test conservative scorer (higher detection weight)."""
    conservative = create_conservative_scorer()
    default = create_default_scorer()
    
    # Same alert
    alert = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.9,  # High detection score
        time_window_sec=300,
        features={
            "total_volume_usd": 50000,  # Medium volume
            "counterparty_diversity": 5,  # Medium diversity
        },
    )
    
    score_conservative = conservative.calculate_risk_score(alert)
    score_default = default.calculate_risk_score(alert)
    
    # Conservative should weight detection more heavily
    # With high detection score, conservative should be higher
    assert score_conservative >= score_default


def test_aggressive_scorer() -> None:
    """Test aggressive scorer (higher volume/behavioral weight)."""
    aggressive = create_aggressive_scorer()
    default = create_default_scorer()
    
    # Alert with high volume but lower detection score
    alert = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.6,  # Medium detection score
        time_window_sec=300,
        features={
            "total_volume_usd": 1_000_000,  # Very high volume
            "counterparty_diversity": 2,  # Low diversity
            "roundtrip_count": 20,
        },
    )
    
    score_aggressive = aggressive.calculate_risk_score(alert)
    score_default = default.calculate_risk_score(alert)
    
    # Aggressive should weight volume/behavioral more heavily
    assert score_aggressive >= score_default


def test_missing_features() -> None:
    """Test handling of missing features."""
    scorer = create_default_scorer()
    
    # Alert with minimal features
    alert = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.7,
        time_window_sec=300,
        features={},  # No features
    )
    
    # Should not crash, should use defaults
    risk_score = scorer.calculate_risk_score(alert)
    assert 0 <= risk_score <= 100


def test_counterparty_diversity_thresholds() -> None:
    """Test counterparty diversity risk thresholds."""
    scorer = create_default_scorer()
    
    # Very low diversity (1-2)
    alert_very_low = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.5,
        time_window_sec=300,
        features={"counterparty_diversity": 2, "total_volume_usd": 50000},
    )
    
    # Low diversity (3-5)
    alert_low = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.5,
        time_window_sec=300,
        features={"counterparty_diversity": 5, "total_volume_usd": 50000},
    )
    
    # Medium diversity (6-10)
    alert_medium = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.5,
        time_window_sec=300,
        features={"counterparty_diversity": 10, "total_volume_usd": 50000},
    )
    
    # High diversity (>10)
    alert_high = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.5,
        time_window_sec=300,
        features={"counterparty_diversity": 20, "total_volume_usd": 50000},
    )
    
    score_very_low = scorer.calculate_risk_score(alert_very_low)
    score_low = scorer.calculate_risk_score(alert_low)
    score_medium = scorer.calculate_risk_score(alert_medium)
    score_high = scorer.calculate_risk_score(alert_high)
    
    # Lower diversity should have higher risk
    assert score_very_low > score_low > score_medium >= score_high


def test_volume_thresholds() -> None:
    """Test volume risk thresholds."""
    scorer = create_default_scorer()
    
    volumes = [5_000, 25_000, 75_000, 250_000, 750_000, 1_500_000]
    scores = []
    
    for volume in volumes:
        alert = Alert(
            address="0xtest",
            pattern_type=PatternType.WASH_TRADING,
            score=0.5,
            time_window_sec=300,
            features={"total_volume_usd": volume},
        )
        scores.append(scorer.calculate_risk_score(alert))
    
    # Scores should increase with volume
    for i in range(len(scores) - 1):
        assert scores[i] <= scores[i + 1]


def test_self_trade_ratio_impact() -> None:
    """Test self-trade ratio impact on risk score."""
    scorer = create_default_scorer()
    
    # High self-trade ratio
    alert_high = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.5,
        time_window_sec=300,
        features={"self_trade_ratio": 0.95, "total_volume_usd": 50000},
    )
    
    # Low self-trade ratio
    alert_low = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.5,
        time_window_sec=300,
        features={"self_trade_ratio": 0.3, "total_volume_usd": 50000},
    )
    
    score_high = scorer.calculate_risk_score(alert_high)
    score_low = scorer.calculate_risk_score(alert_low)
    
    # Higher self-trade ratio should increase risk
    assert score_high > score_low


def test_roundtrip_count_impact() -> None:
    """Test roundtrip count impact on risk score."""
    scorer = create_default_scorer()
    
    # Many roundtrips
    alert_many = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.5,
        time_window_sec=300,
        features={"roundtrip_count": 25, "total_volume_usd": 50000},
    )
    
    # Few roundtrips
    alert_few = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.5,
        time_window_sec=300,
        features={"roundtrip_count": 3, "total_volume_usd": 50000},
    )
    
    score_many = scorer.calculate_risk_score(alert_many)
    score_few = scorer.calculate_risk_score(alert_few)
    
    # More roundtrips should increase risk
    assert score_many > score_few
