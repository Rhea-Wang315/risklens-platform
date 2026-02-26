from typing import Any, Dict, List, Optional
"""Rule evaluation engine for risk decisions.

This module implements a lightweight rule engine that evaluates alerts
against configurable rules to determine risk actions.

Design Philosophy:
- Simple Python-based DSL (no external rule engine dependencies)
- Explicit over implicit (every condition is clear)
- Testable (pure functions, no side effects)
- Extensible (easy to add new condition types)
"""

from typing import Any, Dict, List

from risklens.models import ActionType, Alert, PatternType, RuleDefinition


class RuleEvaluator:
    """Evaluates alerts against rules to determine actions.
    
    Supports condition operators:
    - Comparison: >, <, >=, <=, ==, !=
    - Membership: in, not_in
    - Range: between
    
    Example rule:
        {
            "score": {">": 0.8},
            "features.counterparty_diversity": {"<": 3},
            "features.total_volume_usd": {">": 100000}
        }
    """

    def __init__(self, rules: List[RuleDefinition]) -> None:
        """Initialize evaluator with rules.
        
        Args:
            rules: List of rule definitions, sorted by priority (highest first)
        """
        self.rules = sorted(rules, key=lambda r: r.priority, reverse=True)

    def evaluate(self, alert: Alert) -> Optional[ActionType]:
        """Evaluate alert against all rules.
        
        Returns the action from the first matching rule (highest priority).
        Returns None if no rules match.
        
        Args:
            alert: Alert to evaluate
            
        Returns:
            Action to take, or None if no rules match
        """
        for rule in self.rules:
            if not rule.enabled:
                continue
                
            # Check if rule applies to this pattern type
            if alert.pattern_type not in rule.pattern_types:
                continue
                
            # Evaluate all conditions
            if self._evaluate_conditions(alert, rule.conditions):
                return rule.action
                
        return None

    def _evaluate_conditions(self, alert: Alert, conditions: Dict[str, Any]) -> bool:
        """Evaluate all conditions for a rule.
        
        All conditions must be true (AND logic).
        
        Args:
            alert: Alert to evaluate
            conditions: Dictionary of field paths to condition specs
            
        Returns:
            True if all conditions match
        """
        for field_path, condition_spec in conditions.items():
            value = self._get_field_value(alert, field_path)
            
            if not self._evaluate_condition(value, condition_spec):
                return False
                
        return True

    def _get_field_value(self, alert: Alert, field_path: str) -> Any:
        """Get value from alert using dot-notation path.
        
        Examples:
            "score" -> alert.score
            "features.counterparty_diversity" -> alert.features["counterparty_diversity"]
            
        Args:
            alert: Alert object
            field_path: Dot-separated field path
            
        Returns:
            Field value, or None if not found
        """
        parts = field_path.split(".")
        value: Any = alert
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = getattr(value, part, None)
                
            if value is None:
                return None
                
        return value

    def _evaluate_condition(self, value: Any, condition_spec: Dict[str, Any]) -> bool:
        """Evaluate a single condition.
        
        Args:
            value: Actual value from alert
            condition_spec: Condition specification (e.g., {">": 0.8})
            
        Returns:
            True if condition matches
        """
        if value is None:
            return False
            
        for operator, expected in condition_spec.items():
            if operator == ">":
                if not (value > expected):
                    return False
            elif operator == "<":
                if not (value < expected):
                    return False
            elif operator == ">=":
                if not (value >= expected):
                    return False
            elif operator == "<=":
                if not (value <= expected):
                    return False
            elif operator == "==":
                if not (value == expected):
                    return False
            elif operator == "!=":
                if not (value != expected):
                    return False
            elif operator == "in":
                if value not in expected:
                    return False
            elif operator == "not_in":
                if value in expected:
                    return False
            elif operator == "between":
                # expected should be [min, max]
                if not (expected[0] <= value <= expected[1]):
                    return False
            else:
                raise ValueError(f"Unknown operator: {operator}")
                
        return True


def create_default_rules() -> List[RuleDefinition]:
    """Create default rule set for common scenarios.
    
    Returns:
        List of default rules
    """
    return [
        # Rule 1: High-confidence wash trading with large volume -> FREEZE
        RuleDefinition(
            name="High-Confidence Wash Trading - Freeze",
            description="Freeze accounts with high wash trading score and low counterparty diversity",
            pattern_types=[PatternType.WASH_TRADING, PatternType.ROUNDTRIP],
            conditions={
                "score": {">": 0.8},
                "features.counterparty_diversity": {"<": 3},
                "features.total_volume_usd": {">": 100000},
            },
            action=ActionType.FREEZE,
            priority=10,
            enabled=True,
        ),
        
        # Rule 2: High-confidence sandwich attack -> ESCALATE
        RuleDefinition(
            name="High-Confidence Sandwich Attack - Escalate",
            description="Escalate high-confidence sandwich attacks to compliance",
            pattern_types=[PatternType.SANDWICH_ATTACK],
            conditions={
                "score": {">": 0.85},
                "features.total_volume_usd": {">": 50000},
            },
            action=ActionType.ESCALATE,
            priority=10,
            enabled=True,
        ),
        
        # Rule 3: Medium-confidence wash trading -> WARN
        RuleDefinition(
            name="Medium-Confidence Wash Trading - Warn",
            description="Flag accounts with medium wash trading score for review",
            pattern_types=[PatternType.WASH_TRADING, PatternType.ROUNDTRIP],
            conditions={
                "score": {"between": [0.6, 0.8]},
                "features.counterparty_diversity": {"<": 5},
            },
            action=ActionType.WARN,
            priority=5,
            enabled=True,
        ),
        
        # Rule 4: Medium-confidence sandwich attack -> WARN
        RuleDefinition(
            name="Medium-Confidence Sandwich Attack - Warn",
            description="Flag medium-confidence sandwich attacks for review",
            pattern_types=[PatternType.SANDWICH_ATTACK],
            conditions={
                "score": {"between": [0.7, 0.85]},
            },
            action=ActionType.WARN,
            priority=5,
            enabled=True,
        ),
        
        # Rule 5: Low-confidence patterns -> OBSERVE
        RuleDefinition(
            name="Low-Confidence Patterns - Observe",
            description="Monitor low-confidence patterns without action",
            pattern_types=[
                PatternType.WASH_TRADING,
                PatternType.SANDWICH_ATTACK,
                PatternType.ROUNDTRIP,
                PatternType.VOLUME_INFLATION,
                PatternType.BURST_TRADING,
            ],
            conditions={
                "score": {"<": 0.6},
            },
            action=ActionType.OBSERVE,
            priority=1,
            enabled=True,
        ),
    ]
