# Supervisor deployment

This deployment mode runs DjangoBlog directly on the host without Docker. It starts two supervised processes:

- `djangoblog-web`: runs migrations, collects static files, then starts Gunicorn on `${WEB_HOST:-0.0.0.0}:${WEB_PORT:-8000}`.
- `djangoblog-scheduler`: runs migrations, then starts `python manage.py run_collectors --interval ${COLLECTOR_INTERVAL:-1800}`.

## Server setup

Install Python dependencies in your virtualenv or conda env:

```bash
pip install -r requirements.txt
```

Create `/root/project/djangoblog/.env` from `.env.example` and set at least:

```env
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_MYSQL_DATABASE=djangoblog
DJANGO_MYSQL_USER=root
DJANGO_MYSQL_PASSWORD=replace-with-your-password
DJANGO_MYSQL_HOST=127.0.0.1
DJANGO_MYSQL_PORT=3306
WEB_HOST=0.0.0.0
WEB_PORT=8000
DJANGOBLOG_PYTHON=/path/to/venv/bin/python
DJANGOBLOG_GUNICORN=/path/to/venv/bin/gunicorn
BUILD_FRONTEND=True
NPM_REGISTRY=https://registry.npmmirror.com/
COLLECTOR_INTERVAL=1800
```

The env file is loaded by shell scripts, so quote values that contain spaces.

Install the supervisor config:

```bash
ln -sf /root/project/djangoblog/deploy/supervisor/djangoblog.conf /etc/supervisor/conf.d/djangoblog.conf
supervisorctl reread
supervisorctl update
supervisorctl status djangoblog:
```

Restart after config or code changes:

```bash
supervisorctl restart djangoblog:
```

The web process runs `npm ci`, `npm run build`, `collectstatic`, and `compress --force` before Gunicorn when `BUILD_FRONTEND=True` or when the Vite manifest is missing. This is required when serving the app directly from Gunicorn/Supervisor without Docker.

Logs:

```bash
tail -f /var/log/supervisor/djangoblog-web.log
tail -f /var/log/supervisor/djangoblog-web.err.log
tail -f /var/log/supervisor/djangoblog-scheduler.log
tail -f /var/log/supervisor/djangoblog-scheduler.err.log
```
