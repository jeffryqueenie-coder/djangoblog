#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/load_env.sh"

cd "${DJANGOBLOG_PROJECT_DIR}"

PYTHON_BIN="${DJANGOBLOG_PYTHON:-python}"
GUNICORN_BIN="${DJANGOBLOG_GUNICORN:-gunicorn}"
NPM_BIN="${DJANGOBLOG_NPM:-npm}"
HOST="${WEB_HOST:-0.0.0.0}"
PORT="${WEB_PORT:-8000}"
WORKERS="${GUNICORN_WORKERS:-2}"
THREADS="${GUNICORN_THREADS:-4}"
WORKER_CLASS="${GUNICORN_WORKER_CLASS:-gevent}"
BUILD_FRONTEND="${BUILD_FRONTEND:-True}"
NPM_REGISTRY="${NPM_REGISTRY:-}"

if [ "${BUILD_FRONTEND}" = "True" ] || [ "${BUILD_FRONTEND}" = "true" ] || [ ! -f "blog/static/blog/dist/.vite/manifest.json" ]; then
  if [ ! -d "frontend/node_modules" ]; then
    if [ -n "${NPM_REGISTRY}" ]; then
      (cd frontend && "${NPM_BIN}" config set registry "${NPM_REGISTRY}")
    fi
    (cd frontend && "${NPM_BIN}" ci --no-audit)
  fi
  (cd frontend && "${NPM_BIN}" run build)
fi

"${PYTHON_BIN}" manage.py migrate --noinput
"${PYTHON_BIN}" manage.py collectstatic --noinput
"${PYTHON_BIN}" manage.py compress --force

exec "${GUNICORN_BIN}" djangoblog.wsgi:application \
  --bind "${HOST}:${PORT}" \
  --workers "${WORKERS}" \
  --threads "${THREADS}" \
  --worker-class "${WORKER_CLASS}" \
  --access-logfile - \
  --error-logfile -
