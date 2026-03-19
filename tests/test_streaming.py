"""Tests for Kafka streaming integration."""

from unittest.mock import MagicMock, patch

import pytest

from risklens.models import ActionType, Decision, RiskLevel
from risklens.streaming import DecisionProducer, get_producer


@pytest.fixture
def sample_decision():
    """Create a sample decision for testing."""
    return Decision(
        decision_id="test_dec_001",
        alert_id="test_alert_001",
        address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        risk_level=RiskLevel.HIGH,
        action=ActionType.FREEZE,
        confidence=0.92,
        risk_score=87.5,
        rationale="High-confidence wash trading detected",
        evidence_refs=["features.score", "features.counterparty_diversity"],
        recommendations=["Freeze account", "Investigate counterparties"],
        limitations=["Limited to 5-minute window"],
        rule_version="v1.0.0",
    )


def test_producer_initialization_success():
    """Test successful Kafka producer initialization."""
    with patch("risklens.streaming.KafkaProducer") as mock_kafka:
        mock_kafka.return_value = MagicMock()
        producer = DecisionProducer()
        assert producer.producer is not None
        assert producer.topic == "risklens.decisions"


def test_producer_initialization_failure():
    """Test Kafka producer initialization failure handling."""
    with patch("risklens.streaming.KafkaProducer", side_effect=Exception("Connection failed")):
        producer = DecisionProducer()
        assert producer.producer is None


def test_publish_decision_success(sample_decision):
    """Test successful decision publishing."""
    with patch("risklens.streaming.KafkaProducer") as mock_kafka:
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_future.get.return_value = MagicMock(
            topic="risklens.decisions", partition=0, offset=123
        )
        mock_producer.send.return_value = mock_future
        mock_kafka.return_value = mock_producer

        producer = DecisionProducer()
        result = producer.publish_decision(sample_decision)

        assert result is True
        mock_producer.send.assert_called_once()


def test_publish_decision_no_producer(sample_decision):
    """Test publishing when producer is not available."""
    with patch("risklens.streaming.KafkaProducer", side_effect=Exception("No Kafka")):
        producer = DecisionProducer()
        result = producer.publish_decision(sample_decision)
        assert result is False


def test_publish_decision_kafka_error(sample_decision):
    """Test publishing with Kafka error."""
    with patch("risklens.streaming.KafkaProducer") as mock_kafka:
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_future.get.side_effect = Exception("Kafka timeout")
        mock_producer.send.return_value = mock_future
        mock_kafka.return_value = mock_producer

        producer = DecisionProducer()
        result = producer.publish_decision(sample_decision)

        assert result is False


def test_producer_close():
    """Test producer close."""
    with patch("risklens.streaming.KafkaProducer") as mock_kafka:
        mock_producer = MagicMock()
        mock_kafka.return_value = mock_producer

        producer = DecisionProducer()
        producer.close()

        mock_producer.flush.assert_called_once()
        mock_producer.close.assert_called_once()


def test_get_producer_singleton():
    """Test get_producer returns singleton instance."""
    with patch("risklens.streaming.KafkaProducer"):
        producer1 = get_producer()
        producer2 = get_producer()
        assert producer1 is producer2
