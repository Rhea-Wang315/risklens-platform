# Slack Alert Runbook

This runbook covers setup and troubleshooting for RiskLens high-risk Slack alerts.

## Scope

- Source: `python -m risklens.streaming.consumer`
- Trigger: `risk_level in {"HIGH", "CRITICAL"}`
- Delivery: Slack Incoming Webhook (`SLACK_WEBHOOK_URL`)

## Prerequisites

1. A Slack app with Incoming Webhooks enabled
2. A target channel and generated webhook URL
3. Running Kafka + RiskLens API + decision consumer

## Configuration

Set environment variables before starting the consumer:

```bash
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export KAFKA_TOPIC_DECISIONS=risklens.decisions
export KAFKA_CONSUMER_GROUP=risklens-platform
export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/XXX/YYY/ZZZ'
```

## Start Services

```bash
# Infra
docker-compose up -d

# API
risklens serve

# Consumer (new terminal)
python -m risklens.streaming.consumer
```

## Smoke Test

Submit a high-risk alert:

```bash
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "time_window_sec": 300,
    "pattern_type": "WASH_TRADING",
    "score": 0.92,
    "features": {"counterparty_diversity": 2, "total_volume_usd": 150000}
  }'
```

Expected result:

1. Consumer logs a `HIGH RISK ALERT` line
2. Slack channel receives a message with decision ID, action, address, confidence, rationale

## Failure Modes

1. No Slack message
- Check `SLACK_WEBHOOK_URL` is set in the consumer process
- Confirm decision risk level is `HIGH` or `CRITICAL`
- Verify consumer is reading the `risklens.decisions` topic

2. Repeated send failures in logs
- Confirm webhook URL is valid and not revoked
- Confirm outbound network from the host/container to `hooks.slack.com`
- Check Slack app/channel permissions

3. Consumer healthy but no events
- Confirm API can publish to Kafka
- Verify `KAFKA_BOOTSTRAP_SERVERS` and topic names are consistent across API/consumer

## Operational Notes

- Slack send includes bounded retries (`max_retries=2`, total 3 attempts).
- If Slack is not configured, consumer skips Slack send and continues processing.
