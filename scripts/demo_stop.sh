#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PIDS_FILE="${ROOT_DIR}/.demo/pids"

if [ -f "${PIDS_FILE}" ]; then
  while IFS= read -r pid; do
    if [ -n "${pid}" ] && kill -0 "${pid}" >/dev/null 2>&1; then
      kill "${pid}" >/dev/null 2>&1 || true
    fi
  done <"${PIDS_FILE}"
  rm -f "${PIDS_FILE}" || true
fi

docker-compose -f "${ROOT_DIR}/docker-compose.observability.yml" down >/dev/null 2>&1 || true
docker-compose -f "${ROOT_DIR}/docker-compose.yml" -f "${ROOT_DIR}/docker-compose.dev.yml" down >/dev/null 2>&1 || true

echo "Stopped demo processes and docker-compose stacks."
