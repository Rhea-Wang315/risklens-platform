#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SMOKE_DIR="${ROOT_DIR}/.smoke"
PIDS_FILE="${SMOKE_DIR}/pids"
API_LOG="${SMOKE_DIR}/api.log"

mkdir -p "${SMOKE_DIR}"
rm -f "${PIDS_FILE}" >/dev/null 2>&1 || true

export POSTGRES_PORT="${POSTGRES_PORT:-5433}"
export DATABASE_URL="${DATABASE_URL:-postgresql://risklens:risklens_dev_password@localhost:${POSTGRES_PORT}/risklens}"

cleanup() {
  "${ROOT_DIR}/scripts/local_smoke_stop.sh" >/dev/null 2>&1 || true
}

trap cleanup INT TERM

if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
  echo "API already running on :8000; stop it before running local smoke." >&2
  exit 1
fi

docker-compose -f "${ROOT_DIR}/docker-compose.yml" up -d postgres redis zookeeper kafka

risklens db init

python -m uvicorn risklens.api.main:app --host 127.0.0.1 --port 8000 >"${API_LOG}" 2>&1 &
API_PID=$!
echo "${API_PID}" >>"${PIDS_FILE}"

for _ in $(seq 1 40); do
  curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 && break
  sleep 0.5
done

curl -sf http://127.0.0.1:8000/health >/dev/null
curl -sf http://127.0.0.1:8000/metrics >/dev/null

EVALUATE_RESPONSE_FILE="${SMOKE_DIR}/evaluate_response.json"
curl -sf -X POST http://127.0.0.1:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d @"${ROOT_DIR}/examples/example_alert.json" \
  >"${EVALUATE_RESPONSE_FILE}"

python - <<'PY'
import json
from pathlib import Path

response = json.loads(Path(".smoke/evaluate_response.json").read_text())
required_keys = {"decision_id", "action", "risk_level", "risk_score"}
missing = required_keys - response.keys()
if missing:
    raise SystemExit(f"Missing keys in evaluate response: {sorted(missing)}")
print("Smoke check response OK:", response["decision_id"], response["action"], response["risk_level"])
PY

echo "Local smoke workflow passed."
echo "API: http://localhost:8000/docs"
echo "Metrics: http://localhost:8000/metrics"
echo "API log: ${API_LOG}"
echo "Response: ${EVALUATE_RESPONSE_FILE}"
echo "To stop: ./scripts/local_smoke_stop.sh"
