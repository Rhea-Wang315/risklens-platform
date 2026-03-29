from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("template must be a JSON object")
    return value


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base-url", default="http://localhost:8000")
    parser.add_argument("--count", type=int, default=25)
    parser.add_argument("--template", default="examples/example_alert.json")
    args = parser.parse_args()

    if args.count < 1:
        raise SystemExit("--count must be >= 1")

    template_path = Path(args.template)
    template = _load_json(template_path)

    pattern_types = [
        "WASH_TRADING",
        "SANDWICH_ATTACK",
        "VOLUME_INFLATION",
        "BURST_TRADING",
        "ROUNDTRIP",
        "UNKNOWN",
    ]

    with httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        for i in range(args.count):
            payload = copy.deepcopy(template)
            payload["alert_id"] = f"demo_alert_{i:04d}"
            payload["detected_at"] = _now_iso()
            payload["pattern_type"] = pattern_types[i % len(pattern_types)]
            payload["score"] = round(0.2 + (0.8 * (i / max(1, args.count - 1))), 2)

            resp = client.post(f"{args.api_base_url}/api/v1/evaluate", json=payload)
            resp.raise_for_status()

    print(f"Seeded {args.count} decisions via {args.api_base_url}")


if __name__ == "__main__":
    main()
