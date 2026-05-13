#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/load_env.sh"

cd "${DJANGOBLOG_PROJECT_DIR}"

PYTHON_BIN="${DJANGOBLOG_PYTHON:-python}"
INTERVAL="${COLLECTOR_INTERVAL:-1800}"

"${PYTHON_BIN}" manage.py migrate --noinput

exec "${PYTHON_BIN}" manage.py run_collectors --interval "${INTERVAL}"
