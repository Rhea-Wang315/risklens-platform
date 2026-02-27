"""Risk scoring model for multi-dimensional risk assessment.

Combines multiple risk signals into a unified risk score (0-100).

Scoring Dimensions:
1. Detection Score (from whale-sentry): Base confidence of pattern detection
2. Volume Risk: Transaction volume relative to thresholds
3. Behavioral Risk: Counterparty diversity, time patterns, etc.
4. Historical Risk: Past behavior of the address (future enhancement)

Design Philosophy:
- Weighted combination of multiple signals
- Configurable weights for different use cases
- Explainable (each dimension contributes to final score)
- Bounded output (0-100 scale)
"""

from typing import Any, Dict

from risklens.models import Alert, RiskLevel


class RiskScorer:
    """Multi-dimensional risk scorer.
    
    Combines detection score with behavioral and volume signals
    to produce a unified risk score (0-100).
    """

    def __init__(
        self,
        detection_weight: float = 0.5,
        volume_weight: float = 0.3,
        behavioral_weight: float = 0.2,
    ) -> None:
        """Initialize scorer with dimension weights.
        
        Args:
            detection_weight: Weight for detection score (0-1)
            volume_weight: Weight for volume risk (0-1)
            behavioral_weight: Weight for behavioral risk (0-1)
            
        Note: Weights should sum to 1.0
        """
        total = detection_weight + volume_weight + behavioral_weight
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
            
        self.detection_weight = detection_weight
        self.volume_weight = volume_weight
        self.behavioral_weight = behavioral_weight

    def calculate_risk_score(self, alert: Alert) -> float:
        """Calculate unified risk score from alert.
        
        Args:
            alert: Alert to score
            
        Returns:
            Risk score (0-100)
        """
        # Detection score (already 0-1, scale to 0-100)
        detection_score = alert.score * 100
        
        # Volume risk score
        volume_score = self._calculate_volume_risk(alert.features)
        
        # Behavioral risk score
        behavioral_score = self._calculate_behavioral_risk(alert.features)
        
        # Weighted combination
        risk_score = (
            detection_score * self.detection_weight
            + volume_score * self.volume_weight
            + behavioral_score * self.behavioral_weight
        )
        
        # Ensure bounded [0, 100]
        return max(0.0, min(100.0, risk_score))

    def _calculate_volume_risk(self, features: Dict[str, Any]) -> float:
        """Calculate risk score based on transaction volume.
        
        Higher volume = higher risk (potential for larger impact).
        
        Args:
            features: Alert features dictionary
            
        Returns:
            Volume risk score (0-100)
        """
        volume_usd = features.get("total_volume_usd", 0)
        
        # Volume thresholds (USD)
        if volume_usd >= 1_000_000:  # $1M+
            return 100.0
        elif volume_usd >= 500_000:  # $500K-$1M
            return 80.0
        elif volume_usd >= 100_000:  # $100K-$500K
            return 60.0
        elif volume_usd >= 50_000:  # $50K-$100K
            return 40.0
        elif volume_usd >= 10_000:  # $10K-$50K
            return 20.0
        else:  # < $10K
            return 10.0

    def _calculate_behavioral_risk(self, features: Dict[str, Any]) -> float:
        """Calculate risk score based on behavioral patterns.
        
        Considers:
        - Counterparty diversity (lower = higher risk)
        - Trade frequency (higher = higher risk)
        - Time patterns (burst trading = higher risk)
        
        Args:
            features: Alert features dictionary
            
        Returns:
            Behavioral risk score (0-100)
        """
        risk_score = 0.0
        
        # Counterparty diversity (40% of behavioral score)
        counterparty_diversity = features.get("counterparty_diversity", 10)
        if counterparty_diversity <= 2:
            risk_score += 40.0
        elif counterparty_diversity <= 5:
            risk_score += 25.0
        elif counterparty_diversity <= 10:
            risk_score += 10.0
        
        # Roundtrip count (30% of behavioral score)
        roundtrip_count = features.get("roundtrip_count", 0)
        if roundtrip_count >= 20:
            risk_score += 30.0
        elif roundtrip_count >= 10:
            risk_score += 20.0
        elif roundtrip_count >= 5:
            risk_score += 10.0
        
        # Self-trade ratio (30% of behavioral score)
        self_trade_ratio = features.get("self_trade_ratio", 0.0)
        if self_trade_ratio >= 0.9:
            risk_score += 30.0
        elif self_trade_ratio >= 0.7:
            risk_score += 20.0
        elif self_trade_ratio >= 0.5:
            risk_score += 10.0
        
        return risk_score

    def determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Map risk score to risk level category.
        
        Args:
            risk_score: Risk score (0-100)
            
        Returns:
            Risk level category
        """
        if risk_score >= 80:
            return RiskLevel.CRITICAL
        elif risk_score >= 60:
            return RiskLevel.HIGH
        elif risk_score >= 40:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW


def create_default_scorer() -> RiskScorer:
    """Create scorer with default weights.
    
    Default weights:
    - Detection: 50% (primary signal from whale-sentry)
    - Volume: 30% (impact magnitude)
    - Behavioral: 20% (pattern characteristics)
    
    Returns:
        RiskScorer with default configuration
    """
    return RiskScorer(
        detection_weight=0.5,
        volume_weight=0.3,
        behavioral_weight=0.2,
    )


def create_conservative_scorer() -> RiskScorer:
    """Create scorer with conservative weights (higher detection weight).
    
    Conservative weights:
    - Detection: 70% (trust whale-sentry more)
    - Volume: 20%
    - Behavioral: 10%
    
    Use when you want to minimize false positives.
    
    Returns:
        RiskScorer with conservative configuration
    """
    return RiskScorer(
        detection_weight=0.7,
        volume_weight=0.2,
        behavioral_weight=0.1,
    )


def create_aggressive_scorer() -> RiskScorer:
    """Create scorer with aggressive weights (higher behavioral weight).
    
    Aggressive weights:
    - Detection: 40%
    - Volume: 30%
    - Behavioral: 30% (catch suspicious patterns even with lower detection score)
    
    Use when you want to catch more potential risks (higher false positive rate).
    
    Returns:
        RiskScorer with aggressive configuration
    """
    return RiskScorer(
        detection_weight=0.4,
        volume_weight=0.3,
        behavioral_weight=0.3,
    )
