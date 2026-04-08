"""Notification integrations for streaming consumers."""

import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Send risk alerts to Slack via Incoming Webhook."""

    def __init__(
        self,
        webhook_url: Optional[str],
        timeout_seconds: float = 5.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.5,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.client = client or httpx.Client(timeout=self.timeout_seconds)

    def is_enabled(self) -> bool:
        """Return whether Slack integration is configured."""
        return bool(self.webhook_url)

    def notify_high_risk(self, decision: dict) -> bool:
        """Send a high-risk decision alert to Slack."""
        if not self.is_enabled():
            logger.info("Slack webhook is not configured; skipping Slack alert")
            return False

        payload = {"text": self._build_message(decision)}
        attempts = self.max_retries + 1

        for attempt in range(1, attempts + 1):
            try:
                response = self.client.post(self.webhook_url, json=payload)
                response.raise_for_status()
                logger.info("Sent Slack alert for decision_id=%s", decision.get("decision_id"))
                return True
            except httpx.HTTPError as exc:
                logger.warning(
                    "Slack alert failed for decision_id=%s (attempt %d/%d): %s",
                    decision.get("decision_id"),
                    attempt,
                    attempts,
                    exc,
                )
                if attempt < attempts:
                    time.sleep(self.retry_backoff_seconds * attempt)

        logger.error(
            "Slack alert permanently failed for decision_id=%s", decision.get("decision_id")
        )
        return False

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self.client.close()

    def _build_message(self, decision: dict) -> str:
        decision_id = str(decision.get("decision_id", "unknown"))
        risk_level = str(decision.get("risk_level", "UNKNOWN"))
        action = str(decision.get("action", "UNKNOWN"))
        address = str(decision.get("address", "unknown"))
        rationale = str(decision.get("rationale", "No rationale"))
        confidence = decision.get("confidence")
        confidence_text = f"{confidence:.2f}" if isinstance(confidence, (float, int)) else "N/A"

        return (
            "[RiskLens] High-risk decision triggered\n"
            f"- decision_id: {decision_id}\n"
            f"- risk_level: {risk_level}\n"
            f"- action: {action}\n"
            f"- address: {address}\n"
            f"- confidence: {confidence_text}\n"
            f"- rationale: {rationale}"
        )
