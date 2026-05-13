#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${DJANGOBLOG_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ENV_FILE="${DJANGOBLOG_ENV_FILE:-${PROJECT_DIR}/.env}"

if [ -f "${ENV_FILE}" ]; then
  set -a
  # shellcheck disable=SC1090
  . "${ENV_FILE}"
  set +a
else
  echo "Environment file not found: ${ENV_FILE}" >&2
  exit 1
fi

export DJANGOBLOG_PROJECT_DIR="${PROJECT_DIR}"
export DJANGOBLOG_ENV_FILE="${ENV_FILE}"
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-djangoblog.settings}"
export DJANGO_DEBUG="${DJANGO_DEBUG:-False}"
export COMPRESS_ENABLED="${COMPRESS_ENABLED:-False}"
export COMPRESS_OFFLINE="${COMPRESS_OFFLINE:-False}"
