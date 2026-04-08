"""Example Kafka consumer for decision events.

This is a standalone consumer that demonstrates how to subscribe to
decision events published by the RiskLens API.

Usage:
    python -m risklens.streaming.consumer
"""

import json
import logging
import signal
import sys
from typing import Optional

from kafka import KafkaConsumer
from kafka.errors import KafkaError

from risklens.config import get_settings
from risklens.streaming.notifications import SlackNotifier

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DecisionConsumer:
    """Kafka consumer for decision events."""

    def __init__(self, notifier: Optional[SlackNotifier] = None):
        """Initialize Kafka consumer."""
        settings = get_settings()
        self.topic = settings.kafka_topic_decisions
        self.running = True
        self.notifier = notifier or SlackNotifier(webhook_url=settings.slack_webhook_url)

        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
                group_id=settings.kafka_consumer_group,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="earliest",  # Start from beginning if no offset
                enable_auto_commit=True,
            )
            logger.info(
                f"Kafka consumer initialized: topic={self.topic}, "
                f"group={settings.kafka_consumer_group}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            raise

    def process_decision(self, decision: dict):
        """Process a decision event.

        This is where you would implement your business logic:
        - Send Slack/PagerDuty alerts for HIGH/CRITICAL risk
        - Update external dashboards
        - Trigger automated actions (e.g., freeze account)
        - Log to external systems

        Args:
            decision: Decision event data
        """
        decision_id = decision.get("decision_id")
        risk_level = decision.get("risk_level")
        action = decision.get("action")
        address = decision.get("address")

        logger.info(
            f"Received decision: id={decision_id}, "
            f"risk={risk_level}, action={action}, address={address}"
        )

        # Alert on high-risk decisions
        if risk_level in ["HIGH", "CRITICAL"]:
            logger.warning(
                f"⚠️  HIGH RISK ALERT: {address} - Action: {action} - "
                f"Rationale: {decision.get('rationale')}"
            )
            self.notifier.notify_high_risk(decision)

        # Example: Log all decisions to external system
        # log_to_external_system(decision)

    def consume(self):
        """Start consuming messages."""
        logger.info(f"Starting to consume from topic: {self.topic}")

        try:
            for message in self.consumer:
                if not self.running:
                    break

                try:
                    decision = message.value
                    self.process_decision(decision)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Continue processing other messages

        except KafkaError as e:
            logger.error(f"Kafka error: {e}")
        finally:
            self.close()

    def close(self):
        """Close consumer connection."""
        logger.info("Closing Kafka consumer...")
        self.consumer.close()
        self.notifier.close()

    def stop(self):
        """Stop consuming (graceful shutdown)."""
        logger.info("Stopping consumer...")
        self.running = False


def main():
    """Main entry point."""
    consumer = DecisionConsumer()

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        consumer.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start consuming
    consumer.consume()


if __name__ == "__main__":
    main()
