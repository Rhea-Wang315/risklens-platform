#!/usr/bin/env bash
set -euo pipefail

export DATABASE_URL="postgresql://risklens:risklens_dev_password@localhost:5433/risklens"

docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

risklens db init

docker-compose -f docker-compose.observability.yml up -d

python -m uvicorn risklens.api.main:app --host 127.0.0.1 --port 8000 >/tmp/risklens_api.log 2>&1 &
API_PID=$!

for _ in $(seq 1 40); do
  curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 && break
  sleep 0.5
done

curl -sf http://127.0.0.1:8000/health >/dev/null
curl -sf http://127.0.0.1:8000/metrics >/dev/null
curl -sf -X POST http://127.0.0.1:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d @examples/example_alert.json \
  >/dev/null

python -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501 \
  >/tmp/risklens_dashboard.log 2>&1 &
DASHBOARD_PID=$!

echo "API: http://localhost:8000/docs"
echo "Metrics: http://localhost:8000/metrics"
echo "Dashboard: http://localhost:8501"
echo "Prometheus: http://localhost:9090"
echo "Grafana: http://localhost:3000 (admin/admin)"
echo "API log: /tmp/risklens_api.log"
echo "Dashboard log: /tmp/risklens_dashboard.log"
echo "To stop: kill ${API_PID} ${DASHBOARD_PID}"

wait
