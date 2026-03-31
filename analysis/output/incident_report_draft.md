# Incident Report Draft: Week 2 Case Study

**Date**: 2026-03-31  
**Attack Type**: SANDWICH_ATTACK  
**Primary Address**: 0x7777777777777777777777777777777777777777  
**Recommended Action**: ESCALATE

## Executive Summary

RiskLens processed 10 historical alerts and generated automated decisions with an estimated prevented loss of **$340,000.00**.

## What Happened

Top high-impact case selected from the batch:
- Pattern: SANDWICH_ATTACK
- Address: 0x7777777777777777777777777777777777777777
- Decision action: ESCALATE

## Why RiskLens Chose This Action

HIGH risk sandwich attack: detection score=0.95, risk score=77.5, counterparty diversity=2, volume=$390,000 USD, roundtrips=11

## Quantified Impact

- Prevented loss (estimated): $340,000.00
- Detection-time savings (warn workflow): 3.0 hours
- False positive rate (labeled set): 0.0
- Freeze recall (labeled true attacks): 0.1667

## Assumptions

1. Prevented loss approximates `subsequent_transactions_volume_usd` for FREEZE decisions.
2. Each WARN decision saves a fixed analyst triage time window.
3. Label quality depends on source-data correctness.

## Next Steps

1. Replace sample data with real whale-sentry export.
2. Validate assumptions with operations/compliance stakeholders.
3. Add scenario-specific cost model for per-protocol impact estimation.
