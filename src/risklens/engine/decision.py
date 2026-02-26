"""Decision engine that combines rules and scoring to produce final decisions.

This is the main entry point for risk evaluation. It orchestrates:
1. Rule evaluation (what action to take)
2. Risk scoring (how severe is the risk)
3. Decision generation (structured output with rationale)

Design Philosophy:
- Single responsibility: One function to evaluate an alert
- Explainable: Every decision includes rationale and evidence
- Auditable: All inputs and reasoning are captured
- Testable: Pure function with no side effects
"""

from typing import List, Optional

from risklens.engine.rules import RuleEvaluator, create_default_rules
from risklens.engine.scoring import RiskScorer, create_default_scorer
from risklens.models import ActionType, Alert, Decision


class DecisionEngine:
    """Main decision engine that evaluates alerts and produces decisions.
    
    Combines rule-based logic with risk scoring to make actionable decisions.
    """

    def __init__(
        self,
        rule_evaluator: Optional[RuleEvaluator] = None,
        risk_scorer: Optional[RiskScorer] = None,
        rule_version: str = "v1.0.0",
    ) -> None:
        """Initialize decision engine.
        
        Args:
            rule_evaluator: Rule evaluator (uses default if None)
            risk_scorer: Risk scorer (uses default if None)
            rule_version: Version identifier for rules
        """
        self.rule_evaluator = rule_evaluator or RuleEvaluator(create_default_rules())
        self.risk_scorer = risk_scorer or create_default_scorer()
        self.rule_version = rule_version

    def evaluate_alert(self, alert: Alert) -> Decision:
        """Evaluate an alert and produce a decision.
        
        This is the main entry point for risk evaluation.
        
        Args:
            alert: Alert from detection engine (e.g., whale-sentry)
            
        Returns:
            Decision with action, risk assessment, and rationale
        """
        # Step 1: Calculate risk score
        risk_score = self.risk_scorer.calculate_risk_score(alert)
        risk_level = self.risk_scorer.determine_risk_level(risk_score)
        
        # Step 2: Evaluate rules to determine action
        action = self.rule_evaluator.evaluate(alert)
        
        # Step 3: Default action if no rules match
        if action is None:
            action = self._default_action(risk_score)
        
        # Step 4: Calculate confidence
        confidence = self._calculate_confidence(alert, risk_score)
        
        # Step 5: Generate rationale
        rationale = self._generate_rationale(alert, risk_score, risk_level, action)
        
        # Step 6: Identify evidence
        evidence_refs = self._identify_evidence(alert)
        
        # Step 7: Generate recommendations
        recommendations = self._generate_recommendations(action, alert)
        
        # Step 8: Document limitations
        limitations = self._document_limitations(alert)
        
        # Create decision
        return Decision(
            alert_id=alert.alert_id,
            address=alert.address,
            risk_level=risk_level,
            action=action,
            confidence=confidence,
            risk_score=risk_score,
            rationale=rationale,
            evidence_refs=evidence_refs,
            recommendations=recommendations,
            limitations=limitations,
            rule_version=self.rule_version,
        )

    def _default_action(self, risk_score: float) -> ActionType:
        """Determine default action when no rules match.
        
        Args:
            risk_score: Calculated risk score
            
        Returns:
            Default action based on risk score
        """
        if risk_score >= 80:
            return ActionType.ESCALATE
        elif risk_score >= 60:
            return ActionType.WARN
        else:
            return ActionType.OBSERVE

    def _calculate_confidence(self, alert: Alert, risk_score: float) -> float:
        """Calculate confidence in the decision.
        
        Confidence is based on:
        - Detection score (higher = more confident)
        - Risk score alignment (higher risk = more confident in action)
        - Data quality (more evidence = more confident)
        
        Args:
            alert: Input alert
            risk_score: Calculated risk score
            
        Returns:
            Confidence score (0-1)
        """
        # Base confidence from detection score
        confidence = alert.score
        
        # Boost confidence if risk score is very high or very low (clear cases)
        if risk_score >= 80 or risk_score <= 20:
            confidence = min(1.0, confidence + 0.1)
        
        # Reduce confidence if we have limited evidence
        if len(alert.evidence_samples) < 3:
            confidence = max(0.0, confidence - 0.1)
        
        return round(confidence, 2)

    def _generate_rationale(
        self,
        alert: Alert,
        risk_score: float,
        risk_level: str,
        action: ActionType,
    ) -> str:
        """Generate human-readable rationale for the decision.
        
        Args:
            alert: Input alert
            risk_score: Calculated risk score
            risk_level: Risk level category
            action: Recommended action
            
        Returns:
            Rationale string
        """
        parts = []
        
        # Pattern and score
        parts.append(
            f"{risk_level} risk {alert.pattern_type.value.lower().replace('_', ' ')}: "
            f"detection score={alert.score:.2f}, risk score={risk_score:.1f}"
        )
        
        # Key features
        features = alert.features
        if "counterparty_diversity" in features:
            parts.append(
                f"counterparty diversity={features['counterparty_diversity']}"
            )
        if "total_volume_usd" in features:
            volume = features["total_volume_usd"]
            parts.append(f"volume=${volume:,.0f} USD")
        if "roundtrip_count" in features:
            parts.append(f"roundtrips={features['roundtrip_count']}")
        
        return ", ".join(parts)

    def _identify_evidence(self, alert: Alert) -> List[str]:
        """Identify key evidence fields that support the decision.
        
        Args:
            alert: Input alert
            
        Returns:
            List of evidence field references
        """
        evidence = ["score", "pattern_type"]
        
        # Add significant features
        features = alert.features
        if features.get("counterparty_diversity", 100) < 5:
            evidence.append("features.counterparty_diversity")
        if features.get("total_volume_usd", 0) > 50000:
            evidence.append("features.total_volume_usd")
        if features.get("roundtrip_count", 0) > 5:
            evidence.append("features.roundtrip_count")
        if features.get("self_trade_ratio", 0) > 0.7:
            evidence.append("features.self_trade_ratio")
        
        # Add evidence samples if available
        if alert.evidence_samples:
            evidence.append(f"evidence_samples[0..{len(alert.evidence_samples)-1}]")
        
        return evidence

    def _generate_recommendations(
        self,
        action: ActionType,
        alert: Alert,
    ) -> List[str]:
        """Generate actionable recommendations based on the decision.
        
        Args:
            action: Recommended action
            alert: Input alert
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if action == ActionType.FREEZE:
            recommendations.append("Freeze account pending manual review")
            recommendations.append("Investigate counterparty addresses")
            recommendations.append("Review transaction history for past 30 days")
        elif action == ActionType.ESCALATE:
            recommendations.append("Escalate to compliance team")
            recommendations.append("Prepare evidence package for review")
            recommendations.append("Consider regulatory reporting requirements")
        elif action == ActionType.WARN:
            recommendations.append("Flag account for enhanced monitoring")
            recommendations.append("Set up alerts for future activity")
            recommendations.append("Review if pattern persists over 7 days")
        else:  # OBSERVE
            recommendations.append("Continue monitoring")
            recommendations.append("No immediate action required")
        
        return recommendations

    def _document_limitations(self, alert: Alert) -> List[str]:
        """Document known limitations of the assessment.
        
        Args:
            alert: Input alert
            
        Returns:
            List of limitations
        """
        limitations = []
        
        # Time window limitation
        if alert.time_window_sec < 3600:
            limitations.append(
                f"Analysis limited to {alert.time_window_sec}s time window"
            )
        
        # Single pool limitation
        if alert.pool:
            limitations.append("Analysis limited to single DEX pool")
            limitations.append("Does not check cross-chain or cross-DEX activity")
        
        # Evidence sample limitation
        if len(alert.evidence_samples) < 5:
            limitations.append("Limited evidence samples available")
        
        return limitations


def create_decision_engine(
    rule_version: str = "v1.0.0",
    scorer_profile: str = "default",
) -> DecisionEngine:
    """Factory function to create a decision engine.
    
    Args:
        rule_version: Version identifier for rules
        scorer_profile: Scoring profile ("default", "conservative", "aggressive")
        
    Returns:
        Configured DecisionEngine
    """
    from risklens.engine.scoring import (
        create_aggressive_scorer,
        create_conservative_scorer,
        create_default_scorer,
    )
    
    # Select scorer based on profile
    if scorer_profile == "conservative":
        scorer = create_conservative_scorer()
    elif scorer_profile == "aggressive":
        scorer = create_aggressive_scorer()
    else:
        scorer = create_default_scorer()
    
    return DecisionEngine(
        rule_evaluator=RuleEvaluator(create_default_rules()),
        risk_scorer=scorer,
        rule_version=rule_version,
    )
