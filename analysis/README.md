# Week 2: Impact Quantification Pack

This folder contains reproducible artifacts for Week 2 case-study work:

- `data/sample_week2_alerts.jsonl`: sample historical alerts with optional labels
- `impact_analysis.ipynb`: notebook workflow for interview demos
- `output/`: generated metrics, decisions, and incident report draft

## Run Analysis

```bash
python scripts/week2_impact_analysis.py \
  --input analysis/data/sample_week2_alerts.jsonl \
  --output-dir analysis/output
```

## Expected Outputs

- `analysis/output/decisions.csv`
- `analysis/output/impact_summary.json`
- `analysis/output/impact_summary.md`
- `analysis/output/incident_report_draft.md`

## Real Data Replacement

Replace `analysis/data/sample_week2_alerts.jsonl` with exported whale-sentry alerts:

1. Keep required alert fields (`address`, `pattern_type`, `score`, `features`).
2. Add optional labels for evaluation quality:
- `is_true_attack` (`true`/`false`)
- `subsequent_transactions_volume_usd` (for prevented-loss estimation)
