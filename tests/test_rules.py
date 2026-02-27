"""Tests for rule evaluation engine."""

import pytest

from risklens.engine.rules import RuleEvaluator, create_default_rules
from risklens.models import ActionType, Alert, PatternType, RuleDefinition


def test_rule_evaluator_basic() -> None:
    """Test basic rule evaluation."""
    rules = [
        RuleDefinition(
            name="High Score Freeze",
            description="Freeze on high score",
            pattern_types=[PatternType.WASH_TRADING],
            conditions={"score": {">": 0.8}},
            action=ActionType.FREEZE,
            priority=10,
        )
    ]
    
    evaluator = RuleEvaluator(rules)
    
    # Alert that matches
    alert = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.9,
        time_window_sec=300,
    )
    
    action = evaluator.evaluate(alert)
    assert action == ActionType.FREEZE


def test_rule_evaluator_no_match() -> None:
    """Test when no rules match."""
    rules = [
        RuleDefinition(
            name="High Score Freeze",
            description="Freeze on high score",
            pattern_types=[PatternType.WASH_TRADING],
            conditions={"score": {">": 0.8}},
            action=ActionType.FREEZE,
            priority=10,
        )
    ]
    
    evaluator = RuleEvaluator(rules)
    
    # Alert with low score
    alert = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.5,
        time_window_sec=300,
    )
    
    action = evaluator.evaluate(alert)
    assert action is None


def test_rule_evaluator_priority() -> None:
    """Test that higher priority rules are evaluated first."""
    rules = [
        RuleDefinition(
            name="Low Priority",
            description="Low priority rule",
            pattern_types=[PatternType.WASH_TRADING],
            conditions={"score": {">": 0.5}},
            action=ActionType.OBSERVE,
            priority=1,
        ),
        RuleDefinition(
            name="High Priority",
            description="High priority rule",
            pattern_types=[PatternType.WASH_TRADING],
            conditions={"score": {">": 0.5}},
            action=ActionType.FREEZE,
            priority=10,
        ),
    ]
    
    evaluator = RuleEvaluator(rules)
    
    alert = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.7,
        time_window_sec=300,
    )
    
    # Should match high priority rule
    action = evaluator.evaluate(alert)
    assert action == ActionType.FREEZE


def test_rule_evaluator_pattern_type_filter() -> None:
    """Test that rules only apply to matching pattern types."""
    rules = [
        RuleDefinition(
            name="Sandwich Only",
            description="Only for sandwich attacks",
            pattern_types=[PatternType.SANDWICH_ATTACK],
            conditions={"score": {">": 0.5}},
            action=ActionType.FREEZE,
            priority=10,
        )
    ]
    
    evaluator = RuleEvaluator(rules)
    
    # Wash trading alert (different pattern)
    alert = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.9,
        time_window_sec=300,
    )
    
    action = evaluator.evaluate(alert)
    assert action is None  # Rule doesn't apply


def test_rule_evaluator_multiple_conditions() -> None:
    """Test rule with multiple conditions (AND logic)."""
    rules = [
        RuleDefinition(
            name="Multi-Condition",
            description="Multiple conditions",
            pattern_types=[PatternType.WASH_TRADING],
            conditions={
                "score": {">": 0.8},
                "features.counterparty_diversity": {"<": 3},
                "features.total_volume_usd": {">": 100000},
            },
            action=ActionType.FREEZE,
            priority=10,
        )
    ]
    
    evaluator = RuleEvaluator(rules)
    
    # All conditions match
    alert = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.9,
        time_window_sec=300,
        features={
            "counterparty_diversity": 2,
            "total_volume_usd": 150000,
        },
    )
    
    action = evaluator.evaluate(alert)
    assert action == ActionType.FREEZE
    
    # One condition fails
    alert_fail = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.9,
        time_window_sec=300,
        features={
            "counterparty_diversity": 5,  # Too high
            "total_volume_usd": 150000,
        },
    )
    
    action_fail = evaluator.evaluate(alert_fail)
    assert action_fail is None


def test_rule_evaluator_comparison_operators() -> None:
    """Test all comparison operators."""
    # Greater than
    rule_gt = RuleDefinition(
        name="GT",
        description="Greater than",
        pattern_types=[PatternType.WASH_TRADING],
        conditions={"score": {">": 0.5}},
        action=ActionType.WARN,
        priority=10,
    )
    
    evaluator = RuleEvaluator([rule_gt])
    assert evaluator.evaluate(Alert(address="0x", pattern_type=PatternType.WASH_TRADING, score=0.6, time_window_sec=300)) == ActionType.WARN
    assert evaluator.evaluate(Alert(address="0x", pattern_type=PatternType.WASH_TRADING, score=0.5, time_window_sec=300)) is None
    
    # Less than
    rule_lt = RuleDefinition(
        name="LT",
        description="Less than",
        pattern_types=[PatternType.WASH_TRADING],
        conditions={"score": {"<": 0.5}},
        action=ActionType.OBSERVE,
        priority=10,
    )
    
    evaluator = RuleEvaluator([rule_lt])
    assert evaluator.evaluate(Alert(address="0x", pattern_type=PatternType.WASH_TRADING, score=0.4, time_window_sec=300)) == ActionType.OBSERVE
    assert evaluator.evaluate(Alert(address="0x", pattern_type=PatternType.WASH_TRADING, score=0.5, time_window_sec=300)) is None
    
    # Greater than or equal
    rule_gte = RuleDefinition(
        name="GTE",
        description="Greater than or equal",
        pattern_types=[PatternType.WASH_TRADING],
        conditions={"score": {">=": 0.5}},
        action=ActionType.WARN,
        priority=10,
    )
    
    evaluator = RuleEvaluator([rule_gte])
    assert evaluator.evaluate(Alert(address="0x", pattern_type=PatternType.WASH_TRADING, score=0.5, time_window_sec=300)) == ActionType.WARN
    assert evaluator.evaluate(Alert(address="0x", pattern_type=PatternType.WASH_TRADING, score=0.4, time_window_sec=300)) is None


def test_rule_evaluator_in_operator() -> None:
    """Test 'in' operator for membership."""
    rules = [
        RuleDefinition(
            name="Pattern In List",
            description="Check pattern in list",
            pattern_types=[PatternType.WASH_TRADING, PatternType.ROUNDTRIP],
            conditions={"pattern_type": {"in": ["WASH_TRADING", "ROUNDTRIP"]}},
            action=ActionType.WARN,
            priority=10,
        )
    ]
    
    evaluator = RuleEvaluator(rules)
    
    alert = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.7,
        time_window_sec=300,
    )
    
    action = evaluator.evaluate(alert)
    assert action == ActionType.WARN


def test_rule_evaluator_between_operator() -> None:
    """Test 'between' operator for range checks."""
    rules = [
        RuleDefinition(
            name="Score Range",
            description="Score in range",
            pattern_types=[PatternType.WASH_TRADING],
            conditions={"score": {"between": [0.5, 0.8]}},
            action=ActionType.WARN,
            priority=10,
        )
    ]
    
    evaluator = RuleEvaluator(rules)
    
    # In range
    alert_in = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.6,
        time_window_sec=300,
    )
    assert evaluator.evaluate(alert_in) == ActionType.WARN
    
    # Out of range (too low)
    alert_low = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.4,
        time_window_sec=300,
    )
    assert evaluator.evaluate(alert_low) is None
    
    # Out of range (too high)
    alert_high = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.9,
        time_window_sec=300,
    )
    assert evaluator.evaluate(alert_high) is None


def test_rule_evaluator_disabled_rule() -> None:
    """Test that disabled rules are skipped."""
    rules = [
        RuleDefinition(
            name="Disabled Rule",
            description="This rule is disabled",
            pattern_types=[PatternType.WASH_TRADING],
            conditions={"score": {">": 0.5}},
            action=ActionType.FREEZE,
            priority=10,
            enabled=False,
        )
    ]
    
    evaluator = RuleEvaluator(rules)
    
    alert = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.9,
        time_window_sec=300,
    )
    
    action = evaluator.evaluate(alert)
    assert action is None  # Rule is disabled


def test_rule_evaluator_nested_field_access() -> None:
    """Test accessing nested fields with dot notation."""
    rules = [
        RuleDefinition(
            name="Nested Field",
            description="Access nested field",
            pattern_types=[PatternType.WASH_TRADING],
            conditions={"features.counterparty_diversity": {"<": 3}},
            action=ActionType.WARN,
            priority=10,
        )
    ]
    
    evaluator = RuleEvaluator(rules)
    
    alert = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.7,
        time_window_sec=300,
        features={"counterparty_diversity": 2},
    )
    
    action = evaluator.evaluate(alert)
    assert action == ActionType.WARN


def test_create_default_rules() -> None:
    """Test that default rules are created correctly."""
    rules = create_default_rules()
    
    assert len(rules) > 0
    assert all(isinstance(r, RuleDefinition) for r in rules)
    assert all(r.enabled for r in rules)
    
    # Check that rules are sorted by priority
    priorities = [r.priority for r in rules]
    assert priorities == sorted(priorities, reverse=True)


def test_rule_evaluator_with_default_rules() -> None:
    """Test evaluator with default rule set."""
    evaluator = RuleEvaluator(create_default_rules())
    
    # High-confidence wash trading
    alert_high = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.9,
        time_window_sec=300,
        features={
            "counterparty_diversity": 2,
            "total_volume_usd": 150000,
        },
    )
    
    action_high = evaluator.evaluate(alert_high)
    assert action_high in [ActionType.FREEZE, ActionType.ESCALATE]
    
    # Low-confidence alert
    alert_low = Alert(
        address="0xtest",
        pattern_type=PatternType.WASH_TRADING,
        score=0.4,
        time_window_sec=300,
        features={
            "counterparty_diversity": 10,
            "total_volume_usd": 5000,
        },
    )
    
    action_low = evaluator.evaluate(alert_low)
    assert action_low in [ActionType.OBSERVE, None]
