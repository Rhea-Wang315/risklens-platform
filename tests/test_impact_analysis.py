from datetime import datetime, timezone
from pathlib import Path

from risklens.analysis.impact import (
    AlertRecord,
    EvaluatedAlert,
    load_alert_records,
    run_impact_analysis,
    summarize_decisions,
)
from risklens.models import ActionType, Alert, Decision, PatternType, RiskLevel


def _make_alert(alert_id: str, score: float) -> Alert:
    return Alert(
        alert_id=alert_id,
        address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        chain="ethereum",
        pool=None,
        pair="WETH/USDC",
        time_window_sec=300,
        pattern_type=PatternType.WASH_TRADING,
        score=score,
        features={"total_volume_usd": 100000, "counterparty_diversity": 2, "roundtrip_count": 8},
        evidence_samples=[],
        detected_at=datetime.now(tz=timezone.utc),
    )


def _make_decision(alert_id: str, action: ActionType) -> Decision:
    return Decision(
        alert_id=alert_id,
        address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        risk_level=RiskLevel.HIGH,
        action=action,
        confidence=0.9,
        risk_score=85.0,
        rationale="test rationale",
        evidence_refs=["score"],
        recommendations=["test"],
        limitations=[],
        rule_version="v1.0.0",
    )


def test_load_alert_records_jsonl(tmp_path: Path) -> None:
    input_path = tmp_path / "alerts.jsonl"
    input_path.write_text(
        "\n".join(
            [
                '{"alert_id":"a1","address":"0x1","pattern_type":"WASH_TRADING","score":0.8,"time_window_sec":300,"features":{"total_volume_usd":1000},"is_true_attack":true,"subsequent_transactions_volume_usd":1200}',
                '{"address":"0x2","pattern_type":"UNKNOWN","score":0.2,"time_window_sec":300,"features":{"total_volume_usd":500}}',
            ]
        ),
        encoding="utf-8",
    )

    records = load_alert_records(input_path)
    assert len(records) == 2
    assert records[0].is_true_attack is True
    assert records[0].subsequent_transactions_volume_usd == 1200
    assert records[1].alert.address == "0x2"


def test_summarize_decisions_with_labeled_metrics() -> None:
    evaluated = [
        EvaluatedAlert(
            record=AlertRecord(
                alert=_make_alert("a1", 0.9),
                is_true_attack=True,
                subsequent_transactions_volume_usd=2000,
            ),
            decision=_make_decision("a1", ActionType.FREEZE),
        ),
        EvaluatedAlert(
            record=AlertRecord(
                alert=_make_alert("a2", 0.5),
                is_true_attack=False,
                subsequent_transactions_volume_usd=300,
            ),
            decision=_make_decision("a2", ActionType.WARN),
        ),
    ]

    summary = summarize_decisions(evaluated, warn_review_seconds=1800)

    assert summary["total_alerts"] == 2
    assert summary["estimated_prevented_loss_usd"] == 2000.0
    assert summary["estimated_detection_time_saved_seconds"] == 1800
    assert summary["false_positives"] == 1
    assert summary["false_positive_rate"] == 0.5
    assert summary["freeze_recall"] == 1.0


def test_run_impact_analysis_generates_outputs(tmp_path: Path) -> None:
    input_path = tmp_path / "alerts.jsonl"
    output_dir = tmp_path / "out"
    input_path.write_text(
        '{"alert_id":"a1","address":"0x1","pattern_type":"WASH_TRADING","score":0.9,"time_window_sec":300,"features":{"total_volume_usd":1000,"counterparty_diversity":2,"roundtrip_count":9},"is_true_attack":true,"subsequent_transactions_volume_usd":1500}',
        encoding="utf-8",
    )

    outputs = run_impact_analysis(input_path=input_path, output_dir=output_dir)
    for path in outputs.values():
        assert path.exists()
