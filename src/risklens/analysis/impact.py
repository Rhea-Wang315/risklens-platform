"""Week 2 impact analysis pipeline.

This module evaluates historical alerts with the RiskLens decision engine
and generates quantifiable business impact outputs for demos/interviews:
- decisions CSV
- summary JSON
- summary Markdown
- incident report draft
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from risklens.engine.decision import DecisionEngine
from risklens.models import ActionType, Alert, Decision, PatternType


@dataclass
class AlertRecord:
    """Alert with optional labels used for impact evaluation."""

    alert: Alert
    is_true_attack: bool | None
    subsequent_transactions_volume_usd: float


@dataclass
class EvaluatedAlert:
    """Evaluated alert plus decision and label metadata."""

    record: AlertRecord
    decision: Decision


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y"}:
            return True
        if lowered in {"0", "false", "no", "n"}:
            return False
    return None


def _as_pattern_type(value: Any) -> PatternType:
    if isinstance(value, PatternType):
        return value
    if isinstance(value, str):
        try:
            return PatternType(value.upper())
        except ValueError:
            return PatternType.UNKNOWN
    return PatternType.UNKNOWN


def _as_detected_at(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            pass
    return datetime.now(tz=timezone.utc)


def _extract_features(raw: dict[str, Any]) -> dict[str, Any]:
    features: dict[str, Any] = {}
    raw_features = raw.get("features")
    if isinstance(raw_features, dict):
        features.update(raw_features)

    flat_fields = {
        "counterparty_diversity",
        "roundtrip_count",
        "total_volume_usd",
        "self_trade_ratio",
        "avg_time_between_trades_sec",
    }
    for key in flat_fields:
        if key in raw and key not in features:
            features[key] = raw[key]
    return features


def _build_record(raw: dict[str, Any]) -> AlertRecord:
    features = _extract_features(raw)
    total_volume = _as_float(features.get("total_volume_usd"), default=0.0)
    subsequent_volume = _as_float(raw.get("subsequent_transactions_volume_usd"), default=total_volume)

    evidence_samples = raw.get("evidence_samples")
    if not isinstance(evidence_samples, list):
        evidence_samples = []

    alert_kwargs: dict[str, Any] = {
        "address": str(raw.get("address", "0x0000000000000000000000000000000000000000")),
        "chain": str(raw.get("chain", "ethereum")),
        "pool": raw.get("pool"),
        "pair": raw.get("pair"),
        "time_window_sec": _as_int(raw.get("time_window_sec"), default=300),
        "pattern_type": _as_pattern_type(raw.get("pattern_type")),
        "score": _as_float(raw.get("score"), default=0.0),
        "features": features,
        "evidence_samples": evidence_samples,
        "detected_at": _as_detected_at(raw.get("detected_at")),
    }
    alert_id = raw.get("alert_id")
    if isinstance(alert_id, str) and alert_id.strip():
        alert_kwargs["alert_id"] = alert_id.strip()

    alert = Alert(**alert_kwargs)

    return AlertRecord(
        alert=alert,
        is_true_attack=_as_optional_bool(raw.get("is_true_attack")),
        subsequent_transactions_volume_usd=subsequent_volume,
    )


def _load_json(path: Path) -> list[AlertRecord]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError("JSON input must be an object or a list of objects")

    output: list[AlertRecord] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("JSON list items must be objects")
        output.append(_build_record(item))
    return output


def _load_jsonl(path: Path) -> list[AlertRecord]:
    output: list[AlertRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        item = json.loads(stripped)
        if not isinstance(item, dict):
            raise ValueError("Each JSONL line must be an object")
        output.append(_build_record(item))
    return output


def _load_csv(path: Path) -> list[AlertRecord]:
    output: list[AlertRecord] = []
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            output.append(_build_record(dict(row)))
    return output


def load_alert_records(path: Path) -> list[AlertRecord]:
    """Load alert records from .json, .jsonl or .csv."""
    if path.suffix.lower() == ".json":
        return _load_json(path)
    if path.suffix.lower() == ".jsonl":
        return _load_jsonl(path)
    if path.suffix.lower() == ".csv":
        return _load_csv(path)
    raise ValueError(f"Unsupported input format: {path.suffix}")


def evaluate_alert_records(
    records: list[AlertRecord],
    decision_engine: DecisionEngine | None = None,
) -> list[EvaluatedAlert]:
    """Evaluate records with the RiskLens decision engine."""
    engine = decision_engine or DecisionEngine()
    output: list[EvaluatedAlert] = []
    for record in records:
        decision = engine.evaluate_alert(record.alert)
        output.append(EvaluatedAlert(record=record, decision=decision))
    return output


def summarize_decisions(
    evaluated: list[EvaluatedAlert],
    warn_review_seconds: int = 3600,
) -> dict[str, Any]:
    """Produce Week 2 business-impact summary metrics."""
    action_counts: Counter[str] = Counter()
    risk_level_counts: Counter[str] = Counter()

    prevented_loss_usd = 0.0
    detection_time_saved_seconds = 0

    labeled = 0
    predicted_positive = 0
    false_positives = 0
    true_positives = 0
    actual_true_attacks = 0
    freeze_on_true_attacks = 0

    for item in evaluated:
        action = item.decision.action.value
        risk_level = item.decision.risk_level.value

        action_counts[action] += 1
        risk_level_counts[risk_level] += 1

        if item.decision.action == ActionType.FREEZE:
            prevented_loss_usd += item.record.subsequent_transactions_volume_usd
        if item.decision.action == ActionType.WARN:
            detection_time_saved_seconds += warn_review_seconds

        if item.record.is_true_attack is None:
            continue

        labeled += 1
        if item.record.is_true_attack:
            actual_true_attacks += 1

        is_predicted_positive = item.decision.action != ActionType.OBSERVE
        if is_predicted_positive:
            predicted_positive += 1
            if item.record.is_true_attack:
                true_positives += 1
            else:
                false_positives += 1

        if item.record.is_true_attack and item.decision.action == ActionType.FREEZE:
            freeze_on_true_attacks += 1

    false_positive_rate = (
        float(false_positives / predicted_positive) if predicted_positive > 0 else None
    )
    freeze_recall = (
        float(freeze_on_true_attacks / actual_true_attacks) if actual_true_attacks > 0 else None
    )

    return {
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "total_alerts": len(evaluated),
        "action_counts": dict(action_counts),
        "risk_level_counts": dict(risk_level_counts),
        "estimated_prevented_loss_usd": round(prevented_loss_usd, 2),
        "estimated_detection_time_saved_seconds": detection_time_saved_seconds,
        "estimated_detection_time_saved_hours": round(detection_time_saved_seconds / 3600, 2),
        "labeled_alerts": labeled,
        "predicted_positive_alerts": predicted_positive,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_positive_rate": None if false_positive_rate is None else round(false_positive_rate, 4),
        "actual_true_attacks": actual_true_attacks,
        "freeze_on_true_attacks": freeze_on_true_attacks,
        "freeze_recall": None if freeze_recall is None else round(freeze_recall, 4),
    }


def _write_decisions_csv(path: Path, evaluated: list[EvaluatedAlert]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "alert_id",
                "address",
                "pattern_type",
                "score",
                "decision_id",
                "action",
                "risk_level",
                "confidence",
                "risk_score",
                "is_true_attack",
                "subsequent_transactions_volume_usd",
            ],
        )
        writer.writeheader()
        for item in evaluated:
            writer.writerow(
                {
                    "alert_id": item.record.alert.alert_id,
                    "address": item.record.alert.address,
                    "pattern_type": item.record.alert.pattern_type.value,
                    "score": item.record.alert.score,
                    "decision_id": item.decision.decision_id,
                    "action": item.decision.action.value,
                    "risk_level": item.decision.risk_level.value,
                    "confidence": item.decision.confidence,
                    "risk_score": item.decision.risk_score,
                    "is_true_attack": item.record.is_true_attack,
                    "subsequent_transactions_volume_usd": item.record.subsequent_transactions_volume_usd,
                }
            )


def _write_summary_json(path: Path, summary: dict[str, Any]) -> None:
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def _write_summary_markdown(path: Path, summary: dict[str, Any]) -> None:
    text = f"""# Week 2 Impact Analysis Summary

- Generated at (UTC): {summary["generated_at_utc"]}
- Alerts evaluated: {summary["total_alerts"]}

## Decision Distribution

- Actions: {summary["action_counts"]}
- Risk levels: {summary["risk_level_counts"]}

## Estimated Business Impact

- Prevented loss (USD): ${summary["estimated_prevented_loss_usd"]:,.2f}
- Detection time saved: {summary["estimated_detection_time_saved_hours"]} hours

## Labeled Set Quality

- Labeled alerts: {summary["labeled_alerts"]}
- Predicted positive alerts: {summary["predicted_positive_alerts"]}
- True positives: {summary["true_positives"]}
- False positives: {summary["false_positives"]}
- False positive rate: {summary["false_positive_rate"]}
- Freeze recall: {summary["freeze_recall"]}
"""
    path.write_text(text, encoding="utf-8")


def _write_incident_report_draft(
    path: Path,
    summary: dict[str, Any],
    evaluated: list[EvaluatedAlert],
) -> None:
    top_case = None
    for item in sorted(
        evaluated,
        key=lambda x: x.record.subsequent_transactions_volume_usd,
        reverse=True,
    ):
        if item.decision.action in {ActionType.FREEZE, ActionType.ESCALATE}:
            top_case = item
            break

    headline = "N/A"
    address = "N/A"
    action = "N/A"
    rationale = "N/A"
    if top_case is not None:
        headline = top_case.record.alert.pattern_type.value
        address = top_case.record.alert.address
        action = top_case.decision.action.value
        rationale = top_case.decision.rationale

    report = f"""# Incident Report Draft: Week 2 Case Study

**Date**: {datetime.now(tz=timezone.utc).date().isoformat()}  
**Attack Type**: {headline}  
**Primary Address**: {address}  
**Recommended Action**: {action}

## Executive Summary

RiskLens processed {summary["total_alerts"]} historical alerts and generated automated decisions with an estimated prevented loss of **${summary["estimated_prevented_loss_usd"]:,.2f}**.

## What Happened

Top high-impact case selected from the batch:
- Pattern: {headline}
- Address: {address}
- Decision action: {action}

## Why RiskLens Chose This Action

{rationale}

## Quantified Impact

- Prevented loss (estimated): ${summary["estimated_prevented_loss_usd"]:,.2f}
- Detection-time savings (warn workflow): {summary["estimated_detection_time_saved_hours"]} hours
- False positive rate (labeled set): {summary["false_positive_rate"]}
- Freeze recall (labeled true attacks): {summary["freeze_recall"]}

## Assumptions

1. Prevented loss approximates `subsequent_transactions_volume_usd` for FREEZE decisions.
2. Each WARN decision saves a fixed analyst triage time window.
3. Label quality depends on source-data correctness.

## Next Steps

1. Replace sample data with real whale-sentry export.
2. Validate assumptions with operations/compliance stakeholders.
3. Add scenario-specific cost model for per-protocol impact estimation.
"""
    path.write_text(report, encoding="utf-8")


def run_impact_analysis(
    input_path: Path,
    output_dir: Path,
    warn_review_seconds: int = 3600,
) -> dict[str, Path]:
    """Run full Week 2 impact analysis and generate outputs."""
    records = load_alert_records(input_path)
    evaluated = evaluate_alert_records(records)
    summary = summarize_decisions(evaluated, warn_review_seconds=warn_review_seconds)

    output_dir.mkdir(parents=True, exist_ok=True)

    decisions_csv = output_dir / "decisions.csv"
    summary_json = output_dir / "impact_summary.json"
    summary_md = output_dir / "impact_summary.md"
    incident_report = output_dir / "incident_report_draft.md"

    _write_decisions_csv(decisions_csv, evaluated)
    _write_summary_json(summary_json, summary)
    _write_summary_markdown(summary_md, summary)
    _write_incident_report_draft(incident_report, summary, evaluated)

    return {
        "decisions_csv": decisions_csv,
        "summary_json": summary_json,
        "summary_md": summary_md,
        "incident_report": incident_report,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Week 2 impact analysis for RiskLens.")
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to alerts file (.json/.jsonl/.csv).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis/output"),
        help="Directory for generated outputs.",
    )
    parser.add_argument(
        "--warn-review-seconds",
        type=int,
        default=3600,
        help="Assumed analyst review time saved per WARN decision.",
    )
    args = parser.parse_args()

    outputs = run_impact_analysis(
        input_path=args.input,
        output_dir=args.output_dir,
        warn_review_seconds=args.warn_review_seconds,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
