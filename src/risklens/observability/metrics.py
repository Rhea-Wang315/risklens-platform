from __future__ import annotations

from prometheus_client import Counter, Histogram

EVALUATE_REQUESTS_TOTAL = Counter(
    "risklens_evaluate_requests_total",
    "Total number of evaluate requests",
    labelnames=("result",),
)

EVALUATE_LATENCY_SECONDS = Histogram(
    "risklens_evaluate_latency_seconds",
    "Latency (seconds) of evaluate endpoint",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

DECISIONS_TOTAL = Counter(
    "risklens_decisions_total",
    "Total decisions generated",
    labelnames=("action", "risk_level"),
)
