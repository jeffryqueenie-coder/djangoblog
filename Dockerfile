ARG NODE_IMAGE=node:20-alpine
ARG PYTHON_IMAGE=python:3.11-slim-bookworm

FROM ${NODE_IMAGE} AS frontend-builder

WORKDIR /app

COPY frontend/package*.json ./frontend/

RUN cd frontend && \
    npm config set registry https://registry.npmjs.org/ && \
    npm ci

COPY frontend/ ./frontend/
COPY templates/ ./templates/
COPY blog/ ./blog/
COPY accounts/ ./accounts/
COPY comments/ ./comments/
COPY oauth/ ./oauth/

RUN cd frontend && npm run build

FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=djangoblog.settings \
    DJANGO_DEBUG=False \
    COMPRESS_ENABLED=False \
    COMPRESS_OFFLINE=False

WORKDIR /code/djangoblog

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      default-libmysqlclient-dev \
      gettext \
      pkg-config && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn[gevent] && \
    pip cache purge

COPY . .

RUN rm -rf /code/djangoblog/blog/static/blog/dist \
    /code/djangoblog/frontend/node_modules \
    /code/djangoblog/collectedstatic

COPY --from=frontend-builder /app/blog/static/blog/dist /code/djangoblog/blog/static/blog/dist

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "djangoblog.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--worker-class", "gevent", "--access-logfile", "-", "--error-logfile", "-"]

ENTRYPOINT ["/code/djangoblog/deploy/entrypoint.sh"]
