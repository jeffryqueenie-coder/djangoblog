ARG NODE_IMAGE=docker.m.daocloud.io/library/node:20-alpine
ARG PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.11-slim-bookworm
ARG NPM_REGISTRY=https://registry.npmmirror.com/

FROM ${NODE_IMAGE} AS frontend-builder

ARG NPM_REGISTRY

WORKDIR /app

COPY frontend/package*.json ./frontend/

RUN cd frontend && \
    npm config set registry ${NPM_REGISTRY} && \
    npm ci --no-audit --prefer-offline

COPY frontend/ ./frontend/
COPY templates/ ./templates/
COPY blog/ ./blog/
COPY accounts/ ./accounts/
COPY comments/ ./comments/
COPY oauth/ ./oauth/

RUN cd frontend && npm run build

FROM ${PYTHON_IMAGE} AS runtime

ARG APT_MIRROR=https://mirrors.aliyun.com/debian
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
ARG PIP_DEFAULT_TIMEOUT=120
ARG PIP_RETRIES=10

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=djangoblog.settings \
    DJANGO_DEBUG=False \
    COMPRESS_ENABLED=False \
    COMPRESS_OFFLINE=False \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=${PIP_DEFAULT_TIMEOUT} \
    PIP_RETRIES=${PIP_RETRIES}

WORKDIR /code/djangoblog

RUN if [ -n "${APT_MIRROR}" ] && [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i "s|http://deb.debian.org/debian|${APT_MIRROR}|g; s|http://deb.debian.org/debian-security|${APT_MIRROR}-security|g" /etc/apt/sources.list.d/debian.sources; \
    fi && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      default-libmysqlclient-dev \
      gettext \
      pkg-config && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install \
      --no-cache-dir \
      --index-url "${PIP_INDEX_URL}" \
      --trusted-host "${PIP_TRUSTED_HOST}" \
      -r requirements.txt \
      "gunicorn[gevent]" && \
    pip cache purge

COPY . .

RUN rm -rf /code/djangoblog/blog/static/blog/dist \
    /code/djangoblog/frontend/node_modules \
    /code/djangoblog/collectedstatic

COPY --from=frontend-builder /app/blog/static/blog/dist /code/djangoblog/blog/static/blog/dist

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "djangoblog.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--worker-class", "gevent", "--access-logfile", "-", "--error-logfile", "-"]
