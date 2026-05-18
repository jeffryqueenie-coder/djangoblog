import os
from pathlib import Path


def _normalise_engine(value):
    return (value or 'mysql').strip().lower()


def _sqlite_path(base_dir, env):
    configured_path = env.get('DJANGO_SQLITE_PATH') or env.get('SQLITE_PATH') or 'db.sqlite3'
    path = Path(configured_path)
    if path.is_absolute():
        return str(path)
    return str(Path(base_dir) / path)


def build_database_config(base_dir, env=None):
    env = env or os.environ
    engine = _normalise_engine(env.get('DJANGO_DATABASE_ENGINE'))

    if engine == 'sqlite':
        return {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': _sqlite_path(base_dir, env),
            'OPTIONS': {
                'timeout': int(env.get('DJANGO_SQLITE_TIMEOUT') or 30),
            },
        }

    if engine == 'mysql':
        return {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': env.get('DJANGO_MYSQL_DATABASE') or 'djangoblog',
            'USER': env.get('DJANGO_MYSQL_USER') or 'root',
            'PASSWORD': env.get('DJANGO_MYSQL_PASSWORD') or 'root',
            'HOST': env.get('DJANGO_MYSQL_HOST') or '127.0.0.1',
            'PORT': int(env.get('DJANGO_MYSQL_PORT') or 3306),
            'OPTIONS': {
                'charset': 'utf8mb4',
            },
        }

    raise ValueError(
        "DJANGO_DATABASE_ENGINE must be either 'mysql' or 'sqlite', "
        f"got {engine!r}."
    )


def configure_sqlite_connection(sender, connection, **kwargs):
    if connection.vendor != 'sqlite':
        return

    with connection.cursor() as cursor:
        cursor.execute('PRAGMA foreign_keys = ON;')
        cursor.execute('PRAGMA journal_mode = WAL;')
        cursor.execute('PRAGMA busy_timeout = 30000;')
