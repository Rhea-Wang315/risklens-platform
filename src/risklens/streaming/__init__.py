"""Kafka event streaming integration."""

import json
import logging
from typing import Optional

from kafka import KafkaProducer
from kafka.errors import KafkaError

from risklens.config import get_settings
from risklens.models import Decision

logger = logging.getLogger(__name__)


class DecisionProducer:
    """Kafka producer for publishing decision events."""

    def __init__(self):
        """Initialize Kafka producer."""
        settings = get_settings()
        self.topic = settings.kafka_topic_decisions
        self.producer: Optional[KafkaProducer] = None

        try:
            self.producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",  # Wait for all replicas
                retries=3,
                max_in_flight_requests_per_connection=1,  # Ensure ordering
            )
            logger.info(f"Kafka producer initialized: {settings.kafka_bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            self.producer = None

    def publish_decision(self, decision: Decision) -> bool:
        """Publish a decision to Kafka.

        Args:
            decision: Decision object to publish

        Returns:
            True if published successfully, False otherwise
        """
        if not self.producer:
            logger.warning("Kafka producer not available, skipping publish")
            return False

        try:
            # Convert decision to dict for JSON serialization
            decision_dict = decision.model_dump(mode="json")

            # Send to Kafka
            future = self.producer.send(self.topic, value=decision_dict)

            # Block for 'synchronous' send (optional, can be async)
            record_metadata = future.get(timeout=10)

            logger.info(
                f"Published decision {decision.decision_id} to Kafka "
                f"(topic={record_metadata.topic}, "
                f"partition={record_metadata.partition}, "
                f"offset={record_metadata.offset})"
            )
            return True

        except KafkaError as e:
            logger.error(f"Failed to publish decision to Kafka: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error publishing to Kafka: {e}")
            return False

    def close(self):
        """Close Kafka producer connection."""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Kafka producer closed")


# Global producer instance (singleton pattern)
_producer: Optional[DecisionProducer] = None


def get_producer() -> DecisionProducer:
    """Get or create global Kafka producer instance.

    Returns:
        DecisionProducer instance
    """
    global _producer
    if _producer is None:
        _producer = DecisionProducer()
    return _producer


def close_producer():
    """Close global Kafka producer."""
    global _producer
    if _producer:
        _producer.close()
        _producer = None
