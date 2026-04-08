"""Tests for Kafka streaming integration."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from risklens.models import ActionType, Decision, RiskLevel
from risklens.streaming import DecisionProducer, get_producer
from risklens.streaming.consumer import DecisionConsumer
from risklens.streaming.notifications import SlackNotifier


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


def test_slack_notifier_skips_when_webhook_missing():
    """Slack notifier should no-op when webhook is not configured."""
    notifier = SlackNotifier(webhook_url=None)

    assert notifier.notify_high_risk({"decision_id": "d1"}) is False

    notifier.close()


def test_slack_notifier_success():
    """Slack notifier should return True on successful post."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_client.post.return_value = mock_response

    notifier = SlackNotifier(webhook_url="https://hooks.slack.test/abc", client=mock_client)
    sent = notifier.notify_high_risk(
        {
            "decision_id": "d1",
            "risk_level": "HIGH",
            "action": "FREEZE",
            "address": "0xabc",
            "confidence": 0.88,
            "rationale": "wash trading pattern",
        }
    )

    assert sent is True
    mock_client.post.assert_called_once()


def test_slack_notifier_retries_then_fails():
    """Slack notifier should retry and eventually fail on HTTP errors."""
    mock_client = MagicMock()
    mock_client.post.side_effect = httpx.ConnectError("network down")

    notifier = SlackNotifier(
        webhook_url="https://hooks.slack.test/abc",
        max_retries=2,
        retry_backoff_seconds=0,
        client=mock_client,
    )
    sent = notifier.notify_high_risk({"decision_id": "d1"})

    assert sent is False
    assert mock_client.post.call_count == 3


def test_decision_consumer_triggers_slack_for_high_risk():
    """Consumer should trigger notifier for HIGH risk decisions."""
    mock_notifier = MagicMock()

    with patch("risklens.streaming.consumer.KafkaConsumer") as mock_kafka:
        mock_kafka.return_value = MagicMock()
        consumer = DecisionConsumer(notifier=mock_notifier)

    consumer.process_decision(
        {
            "decision_id": "d1",
            "risk_level": "HIGH",
            "action": "FREEZE",
            "address": "0xabc",
            "rationale": "r1",
        }
    )

    mock_notifier.notify_high_risk.assert_called_once()
    consumer.close()


def test_decision_consumer_skips_slack_for_low_risk():
    """Consumer should not trigger notifier for LOW risk decisions."""
    mock_notifier = MagicMock()

    with patch("risklens.streaming.consumer.KafkaConsumer") as mock_kafka:
        mock_kafka.return_value = MagicMock()
        consumer = DecisionConsumer(notifier=mock_notifier)

    consumer.process_decision(
        {
            "decision_id": "d1",
            "risk_level": "LOW",
            "action": "OBSERVE",
            "address": "0xabc",
        }
    )

    mock_notifier.notify_high_risk.assert_not_called()
    consumer.close()
