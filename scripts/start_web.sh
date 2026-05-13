#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/load_env.sh"

cd "${DJANGOBLOG_PROJECT_DIR}"

PYTHON_BIN="${DJANGOBLOG_PYTHON:-python}"
GUNICORN_BIN="${DJANGOBLOG_GUNICORN:-gunicorn}"
HOST="${WEB_HOST:-0.0.0.0}"
PORT="${WEB_PORT:-8000}"
WORKERS="${GUNICORN_WORKERS:-2}"
THREADS="${GUNICORN_THREADS:-4}"
WORKER_CLASS="${GUNICORN_WORKER_CLASS:-gevent}"

"${PYTHON_BIN}" manage.py migrate --noinput
"${PYTHON_BIN}" manage.py collectstatic --noinput

exec "${GUNICORN_BIN}" djangoblog.wsgi:application \
  --bind "${HOST}:${PORT}" \
  --workers "${WORKERS}" \
  --threads "${THREADS}" \
  --worker-class "${WORKER_CLASS}" \
  --access-logfile - \
  --error-logfile -
